"""Cenários, fila e execução. Um único worker (thread) consome a fila; as execuções são
independentes do processo que atende requisições HTTP."""

from __future__ import annotations

import queue
import re
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from backend.app import workspace
from backend.app.nasa.provenance.log import utc_now
from backend.app.simulation.case_builder import CaseValidationError, build_case, validate_values
from backend.app.simulation.compatibility import assess
from backend.app.simulation.executor import ExecutionError, Executor
from backend.app.simulation.models import (
    TERMINAL, ParameterChange, RunState, Scenario, SimulationRun,
)
from backend.app.simulation.registry import MODELS

LIMITS = {"wall_clock_s": 900, "max_frames": 300, "threads": 4, "max_t_end_s": 60,
          "note_pt": "Limite de tempo por execução; processo isolado em diretório próprio."}
LOG_LIMIT = 40


class SimulationService:
    def __init__(self, executor: Executor, catalog, start_worker: bool = True, timeout_s: float = LIMITS["wall_clock_s"]):
        self._executor = executor
        self._catalog = catalog
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
        exp = self._catalog.experiment(experiment_id)
        if exp is None:
            return None
        return assess(exp, self._executor.available()[0])

    # ---------------------------------------------------------------- cenários
    @staticmethod
    def _sdir() -> Path:
        return workspace.area("scenarios")

    def create_scenario(self, model_id: str, values: dict[str, float], title: str | None,
                        experiment_id: str | None = None) -> Scenario:
        model = MODELS.get(model_id)
        if model is None:
            raise KeyError("MODEL_NOT_FOUND")
        if experiment_id is not None and self._catalog.experiment(experiment_id) is None:
            raise KeyError("EXPERIMENT_NOT_FOUND")
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
            experiment_id=experiment_id,
            title_pt=label or ("Cenário derivado" if changes else "Caso-base"),
            changes=changes, values=clean, executable=model.implemented and not reasons,
            blocked_reasons_pt=reasons, created_at=utc_now(),
            note_pt=("Hipótese computacional derivada do caso-base; não é dado experimental. "
                     if changes else "Caso-base do modelo, sem alterações. ") + model.label_pt,
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
        return workspace.read_json(workspace.area("runs") / workspace.safe_id(run_id) / "run.json")

    def _save(self, run: SimulationRun) -> None:
        with self._lock:
            workspace.write_json(self._run_dir(run.run_id) / "run.json", run.model_dump(mode="json"))

    def submit(self, scenario_id: str) -> SimulationRun:
        sc = self.get_scenario(scenario_id)
        if sc is None:
            raise KeyError("SCENARIO_NOT_FOUND")
        model = MODELS[sc["model_id"]]
        run_id = "RUN-" + time.strftime("%Y%m%d%H%M%S", time.gmtime()) + "-" + secrets.token_hex(2)
        run = SimulationRun(
            run_id=run_id, scenario_id=scenario_id, model_id=model.model_id, purpose=model.purpose,
            label_pt=model.label_pt, state=RunState.QUEUED, demo=self._executor.demo,
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
        run = SimulationRun(**data)
        sc = self.get_scenario(run.scenario_id)
        model = MODELS[run.model_id]
        self._transition(run, RunState.VALIDATING)
        chid = "fl_" + run_id.split("-", 1)[1].replace("-", "")
        try:
            text, sha = build_case(model, sc["values"], chid)
        except CaseValidationError as exc:
            run.failure_reason = "Validação falhou: " + "; ".join(exc.errors)
            self._transition(run, RunState.BLOCKED)
            return
        run.fds_sha256 = sha
        v = self._executor.versions()
        run.fds_version, run.smokeview_version, run.ffmpeg_version = v.fds, v.smokeview, v.ffmpeg
        self._save(run)
        run_dir = self._run_dir(run_id)
        try:
            result = self._executor.run(run_dir, chid, text, sc["values"]["t_end"], self._timeout,
                                        lambda s: self._transition(run, s))
        except ExecutionError as exc:
            run.failure_reason = exc.reason
            self._transition(run, exc.state)
            return
        run.artifacts, run.results, run.log_tail = result.artifacts, result.results, result.log_tail[-LOG_LIMIT:]
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
