"""Cenários, fila e execução. Um único worker (thread) consome a fila; as execuções são
independentes do processo que atende requisições HTTP."""

from __future__ import annotations

import queue
import re
import secrets
import threading
import time
from pathlib import Path
from typing import Any, Callable

from backend.app import workspace
from backend.app.nasa.provenance.log import utc_now
from backend.app.simulation.case_builder import CaseValidationError, build_case, validate_values
from backend.app import units
from backend.app.simulation.compatibility import assess, is_editable, range_rule, with_readiness
from backend.app.simulation.executor import ExecutionError, Executor
from backend.app.simulation.models import (
    TERMINAL, ParameterChange, RunState, Scenario, SimulationRun,
)
from backend.app.simulation.registry import MODELS

_FDS_LOG_TIME = re.compile(r"Simulation Time:\s*([\d.]+)\s*s")

LIMITS = {"wall_clock_s": 900, "max_frames": 300, "threads": 4, "max_t_end_s": 60,
          "note_pt": "Limite de tempo por execução; processo isolado em diretório próprio."}
LOG_LIMIT = 40


class SimulationService:
    def __init__(self, executor: Executor, catalog, start_worker: bool = True, timeout_s: float = LIMITS["wall_clock_s"]):
        self._executor = executor
        self._catalog_src = catalog if callable(catalog) else (lambda: catalog)
        self._queued_at: dict[str, float] = {}
        self._timeout = timeout_s
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        if start_worker:
            self.start()

    # ---------------------------------------------------------------- ciclo de vida
    def start(self) -> None:
        self._recover()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="flamelab-sim-worker")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _recover(self) -> None:
        """Execuções interrompidas por um reinício do servidor não ficam 'rodando' para sempre."""
        for run in self.list_runs():
            if run["state"] not in {s.value for s in TERMINAL}:
                run["state"] = RunState.FAILED.value
                run["failure_reason"] = "Interrompida por reinício do servidor."
                workspace.write_json(self._run_dir(run["run_id"]) / "run.json", run)

    # ---------------------------------------------------------------- executor / modelos
    def status(self) -> dict[str, Any]:
        ok, why = self._executor.available()
        v = self._executor.versions() if ok else None
        return {"executor": self._executor.name, "available": ok, "detail": why, "demo": self._executor.demo,
                "versions": {"fds": v.fds, "smokeview": v.smokeview, "ffmpeg": v.ffmpeg} if v else None,
                "limits": LIMITS}

    def models(self) -> list[dict[str, Any]]:
        return [m.model_dump(mode="json") for m in MODELS.values()]

    def compatibility(self, experiment_id: str) -> dict[str, Any] | None:
        exp = self._catalog_src().experiment(experiment_id)
        if exp is None:
            return None
        ok = self._executor.available()[0]
        return with_readiness(exp, assess(exp, ok), ok)

    # ---------------------------------------------------------------- cenários
    @staticmethod
    def _sdir() -> Path:
        return workspace.area("scenarios")

    def create_scenario(self, model_id: str, values: dict[str, float], title: str | None,
                        experiment_id: str | None = None) -> Scenario:
        model = MODELS.get(model_id)
        if model is None:
            raise KeyError("MODEL_NOT_FOUND")
        if experiment_id is not None:
            if self._catalog_src().experiment(experiment_id) is None:
                raise KeyError("EXPERIMENT_NOT_FOUND")
            if model.purpose == "INTEGRATION_TEST":
                # O caso genérico é independente de qualquer artigo: nunca é associado a um experimento.
                raise CaseValidationError([
                    "o caso de integração é uma demonstração técnica independente e não pode ser "
                    "vinculado a um experimento NASA"])
        reasons: list[str] = []
        if not model.implemented:
            reasons.append("O modelo ainda não tem gerador de caso aprovado.")
        clean = validate_values(model, values) if model.implemented else {}
        base = {p.name: p.default for p in model.parameters}
        changes = [ParameterChange(name=p.name, from_value=base[p.name], to_value=clean[p.name], unit=p.unit)
                   for p in model.parameters if model.implemented and clean[p.name] != base[p.name]]
        sid = "SCN-" + secrets.token_hex(5)
        label = re.sub(r"[^\w .,()\-–—]", "", title or "")[:80].strip()
        scenario = Scenario(
            scenario_id=sid, kind="DERIVED" if changes else "BASE", model_id=model_id,
            experiment_id=experiment_id, scope="EXPERIMENT" if experiment_id else "DEMO",
            title_pt=label or ("Cenário derivado" if changes else "Caso-base"),
            changes=changes, values=clean, executable=model.implemented and not reasons,
            blocked_reasons_pt=reasons, created_at=utc_now(),
            note_pt=("Hipótese computacional derivada do caso-base; não é dado experimental. "
                     if changes else "Caso-base do modelo, sem alterações. ") + model.label_pt,
        )
        workspace.write_json(self._sdir() / f"{sid}.json", scenario.model_dump(mode="json"))
        return scenario

    def create_experiment_scenario(self, experiment_id: str, changes: list[dict[str, Any]],
                                   title: str | None, hypothesis: str | None) -> Scenario:
        """Cenário derivado de HIPÓTESE sobre as condições de um experimento (valor original preservado).
        Só altera condições numéricas com unidade conhecida; resultados observados nunca são entradas.
        É executável apenas se o experimento tiver modelo compatível; caso contrário, o motivo é gravado."""
        exp = self._catalog_src().experiment(experiment_id)
        if exp is None:
            raise KeyError("EXPERIMENT_NOT_FOUND")
        params = {p["parameter"]: p for p in exp["parameters"]}
        out: list[ParameterChange] = []
        errors: list[str] = []
        seen: set[str] = set()
        for ch in changes:
            name = ch.get("parameter")
            p = params.get(name)
            if p is None:
                errors.append(f"parâmetro inexistente: {name}")
                continue
            if name in seen:
                errors.append(f"{name}: alterado mais de uma vez")
                continue
            seen.add(name)
            if p["role"] == "OBSERVAVEL":
                errors.append(f"{p['label_pt']}: é um resultado observado, não uma condição de entrada")
                continue
            if not is_editable(p):
                errors.append(f"{p['label_pt']}: não é uma condição numérica com unidade conhecida")
                continue
            value = ch.get("value")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value or abs(value) == float("inf"):
                errors.append(f"{p['label_pt']}: valor numérico inválido")
                continue
            unit = p["original"].get("unit")
            rule, lo, hi = range_rule(unit)
            if (lo is not None and value <= lo) or (lo is None and value < 0) or (hi is not None and value > hi):
                errors.append(f"{p['label_pt']}: {value} {unit or ''} fora da faixa ({rule})")
                continue
            orig = float(p["original"]["value"])
            if value == orig:
                continue  # sem alteração real
            out.append(ParameterChange(name=name, from_value=orig, to_value=float(value), unit=unit or "",
                                       label_pt=p["label_pt"], base_status=p["status"]))
        if errors:
            raise CaseValidationError(errors)
        if not out:
            raise CaseValidationError(["nenhuma alteração: informe ao menos um valor diferente do original"])
        ok = self._executor.available()[0]
        compat = with_readiness(exp, assess(exp, ok), ok)
        reasons = [] if compat["actions"]["simulate"] else list(compat["reasons_pt"])
        sid = "SCN-" + secrets.token_hex(5)
        label = re.sub(r"[^\w .,()\-–—]", "", title or "")[:80].strip()
        hyp = re.sub(r"\s+", " ", hypothesis or "").strip()[:500] or None
        scenario = Scenario(
            scenario_id=sid, kind="DERIVED", model_id=compat.get("model_id"), experiment_id=experiment_id,
            scope="EXPERIMENT", hypothesis_pt=hyp, title_pt=label or f"Hipótese sobre {exp['label']}",
            changes=out, values={c.name: c.to_value for c in out}, executable=compat["actions"]["simulate"],
            blocked_reasons_pt=reasons, created_at=utc_now(),
            note_pt=("Hipótese computacional sobre o experimento; o experimento original não foi alterado. "
                     "Não é dado experimental."),
        )
        workspace.write_json(self._sdir() / f"{sid}.json", scenario.model_dump(mode="json"))
        return scenario

    def get_scenario(self, scenario_id: str) -> dict[str, Any] | None:
        return workspace.read_json(self._sdir() / f"{workspace.safe_id(scenario_id)}.json")

    def list_scenarios(self) -> list[dict[str, Any]]:
        items = [workspace.read_json(p) for p in sorted(self._sdir().glob("SCN-*.json"))]
        return [i for i in items if i]

    # ---------------------------------------------------------------- execuções
    @staticmethod
    def _run_dir(run_id: str) -> Path:
        path = workspace.area("runs") / workspace.safe_id(run_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def list_runs(self) -> list[dict[str, Any]]:
        items = [workspace.read_json(p / "run.json") for p in sorted(workspace.area("runs").iterdir())]
        return [i for i in items if i]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        run = workspace.read_json(workspace.area("runs") / workspace.safe_id(run_id) / "run.json")
        if run is not None:
            run["progress"] = self._progress(run)
        return run

    def _progress(self, run: dict[str, Any]) -> dict[str, Any] | None:
        """Progresso REAL do cálculo: o tempo físico que o FDS informa em seu log. Não é estimativa de
        tempo restante (o custo por passo varia). Só existe enquanto o FDS executa."""
        if run.get("state") != RunState.RUNNING_FDS.value:
            return None
        log = self._run_dir(run["run_id"]) / "fds.log"
        try:
            size = log.stat().st_size
            with log.open("rb") as fh:
                fh.seek(max(0, size - 4096))
                tail = fh.read().decode("utf-8", errors="replace")
        except OSError:
            return None
        found = _FDS_LOG_TIME.findall(tail)
        t_end = (run.get("parameters") or {}).get("t_end")
        if not found or not t_end:
            return None
        sim = float(found[-1])
        return {"simulated_time_s": sim, "t_end_s": t_end, "fraction": round(min(sim / t_end, 1.0), 4),
                "source": "log do FDS (Simulation Time)"}

    def _save(self, run: SimulationRun) -> None:
        with self._lock:
            workspace.write_json(self._run_dir(run.run_id) / "run.json", run.model_dump(mode="json"))

    def submit(self, scenario_id: str) -> SimulationRun:
        sc = self.get_scenario(scenario_id)
        if sc is None:
            raise KeyError("SCENARIO_NOT_FOUND")
        if sc.get("case_id"):
            from backend.app.simulation.bridge import build
            build(sc["case_id"], sc["case_version"])
        model = MODELS[sc["model_id"]]
        run_id = "RUN-" + time.strftime("%Y%m%d%H%M%S", time.gmtime()) + "-" + secrets.token_hex(2)
        run = SimulationRun(
            case_id=sc.get("case_id"), case_version=sc.get("case_version"),
            run_id=run_id, scenario_id=scenario_id, model_id=model.model_id, purpose=model.purpose,
            label_pt=model.label_pt, state=RunState.QUEUED, demo=self._executor.demo, scope=sc.get("scope", "DEMO"),
            parameters=sc["values"], changes=[ParameterChange(**c) for c in sc["changes"]],
            timestamps={"QUEUED": utc_now()}, limits=LIMITS,
        )
        blocked = list(sc.get("blocked_reasons_pt") or [])
        ok, why = self._executor.available()
        if not sc["executable"]:
            run.state, run.failure_reason = RunState.BLOCKED, " ".join(blocked) or "Cenário não executável."
        elif not ok:
            run.state, run.failure_reason = RunState.BLOCKED, f"Executor indisponível ({why})."
        self._save(run)
        if run.state == RunState.QUEUED:
            self._queued_at[run_id] = time.monotonic()
            self._queue.put(run_id)
        return run

    def _transition(self, run: SimulationRun, state: RunState) -> None:
        run.state = state
        run.timestamps[state.value] = utc_now()
        self._save(run)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                run_id = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._execute(run_id)
            except Exception:  # noqa: BLE001 — o worker nunca morre por uma execução
                run = self.get_run(run_id)
                if run and run["state"] not in {s.value for s in TERMINAL}:
                    run["state"], run["failure_reason"] = RunState.FAILED.value, "Erro interno do worker."
                    workspace.write_json(self._run_dir(run_id) / "run.json", run)

    def _execute(self, run_id: str) -> None:
        data = self.get_run(run_id)
        data.pop("progress", None)
        run = SimulationRun(**data)
        t_start = time.monotonic()
        queued = self._queued_at.pop(run_id, None)
        run.timings_ms["queue_wait"] = int((t_start - queued) * 1000) if queued else None
        sc = self.get_scenario(run.scenario_id)
        model = MODELS[run.model_id]
        self._transition(run, RunState.VALIDATING)
        chid = "fl_" + run_id.split("-", 1)[1].replace("-", "")
        try:
            manifest = None
            if run.case_id:
                from backend.app.simulation.bridge import build
                text, sha, manifest = build(run.case_id, run.case_version)
                chid = "case_" + manifest["computational_id"]
                run.parameters = manifest["content"]["values"]
                sc["values"] = run.parameters
            else:
                text, sha = build_case(model, sc["values"], chid)
        except (CaseValidationError, ValueError, KeyError) as exc:
            run.failure_reason = "Validação falhou: " + str(exc)
            self._transition(run, RunState.BLOCKED)
            return
        run.fds_sha256 = sha
        v = self._executor.versions()
        run.fds_version, run.smokeview_version, run.ffmpeg_version = v.fds, v.smokeview, v.ffmpeg
        run.timings_ms["preparation"] = int((time.monotonic() - t_start) * 1000)
        self._save(run)
        run_dir = self._run_dir(run_id)
        if manifest:
            import hashlib
            from backend.app.simulation.models import RenderedArtifact
            workspace.write_json(run_dir / "manifest.json", manifest)
            raw = (run_dir / "manifest.json").read_bytes()
            provenance = RenderedArtifact(kind="MANIFEST_JSON", name="manifest.json", sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
            run.artifacts.append(provenance)
            self._save(run)
        try:
            result = self._executor.run(run_dir, chid, text, sc["values"]["t_end"], self._timeout,
                                        lambda s: self._transition(run, s))
        except ExecutionError as exc:
            run.failure_reason = exc.reason
            run.timings_ms["total"] = int((time.monotonic() - t_start) * 1000)
            self._transition(run, exc.state)
            return
        run.artifacts, run.results, run.log_tail = result.artifacts, result.results, result.log_tail[-LOG_LIMIT:]
        if manifest:
            run.artifacts.append(provenance)
            run.results["comparison"] = manifest["comparison"]
        run.timings_ms.update(result.timings_ms)
        run.timings_ms["total"] = int((time.monotonic() - t_start) * 1000)
        self._transition(run, RunState.COMPLETED)

    def artifact_path(self, run_id: str, name: str) -> Path | None:
        """Só entrega arquivos listados nos artefatos da execução (nunca caminhos do cliente)."""
        run = self.get_run(run_id)
        if not run or run["state"] != RunState.COMPLETED.value:
            return None
        if name not in {a["name"] for a in run["artifacts"]}:
            return None
        path = self._run_dir(run_id) / workspace.safe_id(name)
        return path if path.is_file() else None

    def wait(self, run_id: str, timeout: float = 5.0) -> dict[str, Any] | None:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            run = self.get_run(run_id)
            if run and run["state"] in {s.value for s in TERMINAL}:
                return run
            time.sleep(0.05)
        return self.get_run(run_id)
