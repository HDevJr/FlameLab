"""Executores de simulação.

`LocalFdsExecutor` roda FDS, Smokeview e FFmpeg com lista fixa de executáveis, diretório
isolado por execução, argumentos montados pelo servidor, tempo máximo e ambiente mínimo.
`FakeExecutor` existe só para testes: tudo que produz é marcado `demo=True`.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from backend.app.simulation.models import RenderedArtifact, RunState

FDS_ROOT_CANDIDATES = [Path(r"C:\Program Files\firemodels")]
SMV_FRAME_STEP = 2
MAX_FRAMES = 300


class ExecutionError(Exception):
    def __init__(self, state: RunState, reason: str):
        self.state, self.reason = state, reason
        super().__init__(reason)


@dataclass
class ToolVersions:
    fds: str | None = None
    smokeview: str | None = None
    ffmpeg: str | None = None


@dataclass
class ExecutionResult:
    artifacts: list[RenderedArtifact] = field(default_factory=list)
    results: dict = field(default_factory=dict)
    log_tail: list[str] = field(default_factory=list)
    versions: ToolVersions = field(default_factory=ToolVersions)


Progress = Callable[[RunState], None]


class Executor(Protocol):
    name: str
    demo: bool

    def available(self) -> tuple[bool, str]: ...

    def versions(self) -> ToolVersions: ...

    def run(self, run_dir: Path, chid: str, fds_text: str, t_end: float, timeout_s: float,
            progress: Progress) -> ExecutionResult: ...


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _artifact(kind: str, path: Path, **meta) -> RenderedArtifact:
    return RenderedArtifact(kind=kind, name=path.name, sha256=_sha(path), size_bytes=path.stat().st_size, meta=meta)


def _minimal_env(extra_path: list[Path]) -> dict[str, str]:
    base = {k: v for k, v in os.environ.items() if k.upper() in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP", "COMSPEC")}
    base["PATH"] = os.pathsep.join(str(p) for p in extra_path) + os.pathsep + os.path.join(
        base.get("SYSTEMROOT", r"C:\Windows"), "System32")
    return base


class LocalFdsExecutor:
    name = "local-windows-fds"
    demo = False

    def __init__(self, root: Path | None = None, ffmpeg: Path | None = None, threads: int = 4):
        self._root = root or next((c for c in FDS_ROOT_CANDIDATES if (c / "FDS6" / "bin" / "fds.exe").is_file()), None)
        self._ffmpeg = ffmpeg or self._find_ffmpeg()
        self._threads = threads
        self._versions: ToolVersions | None = None

    @staticmethod
    def _find_ffmpeg() -> Path | None:
        try:
            import imageio_ffmpeg

            return Path(imageio_ffmpeg.get_ffmpeg_exe())
        except Exception:  # noqa: BLE001
            found = shutil.which("ffmpeg")
            return Path(found) if found else None

    @property
    def _fds(self) -> Path | None:
        return self._root / "FDS6" / "bin" / "fds.exe" if self._root else None

    @property
    def _smv(self) -> Path | None:
        return self._root / "SMV6" / "smokeview.exe" if self._root else None

    def _tool_paths(self) -> dict[str, Path | None]:
        return {"fds": self._fds, "smokeview": self._smv, "ffmpeg": self._ffmpeg}

    def available(self) -> tuple[bool, str]:
        missing = [n for n, p in self._tool_paths().items() if not (p and p.is_file())]
        return (not missing, "ok" if not missing else "ausente: " + ", ".join(missing))

    def _env(self) -> dict[str, str]:
        assert self._root
        env = _minimal_env([self._root / "FDS6" / "bin" / "mpi", self._root / "FDS6" / "bin"])
        env["I_MPI_ROOT"] = str(self._root / "FDS6" / "bin" / "mpi")
        env["OMP_NUM_THREADS"] = str(self._threads)
        return env

    def versions(self) -> ToolVersions:
        if self._versions:
            return self._versions
        v = ToolVersions()
        ok, _ = self.available()
        if ok:
            try:
                out = subprocess.run([str(self._fds)], input="\n", capture_output=True, text=True, timeout=30,
                                     env=self._env(), cwd=str(Path(os.environ.get("TEMP", "."))))
                m = re.search(r"Revision\s*:\s*(\S+)", out.stdout + out.stderr)
                v.fds = m.group(1) if m else None
                out = subprocess.run([str(self._smv), "-version"], capture_output=True, text=True, timeout=30,
                                     env=self._env())
                m = re.search(r"Revision\s*:\s*(\S+)", out.stdout)
                v.smokeview = m.group(1) if m else None
                out = subprocess.run([str(self._ffmpeg), "-version"], capture_output=True, text=True, timeout=30)
                m = re.search(r"ffmpeg version (\S+)", out.stdout)
                v.ffmpeg = m.group(1) if m else None
            except (subprocess.SubprocessError, OSError):
                pass
        self._versions = v
        return v

    # ---------------------------------------------------------------- execução
    def run(self, run_dir: Path, chid: str, fds_text: str, t_end: float, timeout_s: float,
            progress: Progress) -> ExecutionResult:
        ok, why = self.available()
        if not ok:
            raise ExecutionError(RunState.BLOCKED, f"Executor indisponível ({why}).")
        result = ExecutionResult(versions=self.versions())
        deadline = time.monotonic() + timeout_s
        fds_file = run_dir / f"{chid}.fds"
        fds_file.write_text(fds_text, encoding="utf-8")
        result.artifacts.append(_artifact("FDS_INPUT", fds_file))

        # 1) FDS
        progress(RunState.RUNNING_FDS)
        log = run_dir / "fds.log"
        self._run([str(self._fds), fds_file.name], run_dir, log, deadline, "FDS")
        out_file = run_dir / f"{chid}.out"
        out_text = out_file.read_text(errors="replace") if out_file.exists() else ""
        if "STOP: FDS completed successfully" not in out_text:
            tail = [l for l in out_text.splitlines() if l.strip()][-3:]
            raise ExecutionError(RunState.FAILED, "O FDS não terminou com sucesso. " + " | ".join(tail))
        wall = re.search(r"Total Elapsed Wall Clock Time \(s\):\s*([\d.]+)", out_text)
        result.results["fds_wall_clock_s"] = float(wall.group(1)) if wall else None
        result.results["fds_completed"] = True
        result.log_tail = [l for l in out_text.splitlines() if l.strip()][-6:]

        # 2) resultados numéricos
        progress(RunState.PROCESSING_RESULTS)
        for csv in sorted(run_dir.glob(f"{chid}_hrr.csv")) + sorted(run_dir.glob(f"{chid}_devc.csv")):
            result.artifacts.append(_artifact("CSV", csv))
        hrr = run_dir / f"{chid}_hrr.csv"
        if hrr.exists():
            result.results["hrr_series"] = _read_series(hrr, "Time", "HRR")
        devc = run_dir / f"{chid}_devc.csv"
        if devc.exists():
            result.results["devc_series"] = _read_devc(devc)
        smv_log = run_dir / "fds.log"
        result.artifacts.append(_artifact("LOG", smv_log))

        # 3) Smokeview → quadros
        progress(RunState.RENDERING)
        frames_dir = run_dir / "frames"
        frames_dir.mkdir(exist_ok=True)
        ssf = run_dir / f"{chid}.ssf"
        ssf.write_text(f"RENDERDIR\n frames\nLOAD3DSMOKE\n SOOT DENSITY\nLOAD3DSMOKE\n HRRPUV\n"
                       f"RENDERALL\n {SMV_FRAME_STEP}\n frame\nEXIT\n", encoding="ascii")
        result.artifacts.append(_artifact("SMV_SCRIPT", ssf))
        self._run([str(self._smv), "-runscript", chid], run_dir, run_dir / "smokeview.log", deadline, "Smokeview")
        frames = sorted(frames_dir.glob("frame_*.png"))[:MAX_FRAMES]
        if not frames:
            raise ExecutionError(RunState.FAILED, "O Smokeview não produziu quadros; nenhum vídeo foi gerado.")
        expected = [f"frame_{i:04d}.png" for i in range(len(frames))]
        if [f.name for f in frames] != expected:
            raise ExecutionError(RunState.FAILED, "A sequência de quadros está incompleta ou fora de ordem.")
        result.results["frame_count"] = len(frames)
        result.artifacts.append(_artifact("FRAME_PNG", frames[len(frames) // 2], index=len(frames) // 2,
                                          note="quadro representativo"))

        # 4) FFmpeg → MP4
        fps = 10
        mp4 = run_dir / "result.mp4"
        self._run([str(self._ffmpeg), "-y", "-loglevel", "error", "-framerate", str(fps), "-i",
                   "frames/frame_%04d.png", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264",
                   "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4.name],
                  run_dir, run_dir / "ffmpeg.log", deadline, "FFmpeg")
        if not mp4.is_file() or mp4.stat().st_size < 1000:
            raise ExecutionError(RunState.FAILED, "O FFmpeg não produziu um vídeo válido.")
        result.artifacts.append(_artifact(
            "VIDEO_MP4", mp4, frames=len(frames), fps=fps, duration_s=round(len(frames) / fps, 2),
            codec="h264/yuv420p", frame_step=SMV_FRAME_STEP,
            simulated_time_s=t_end, source="Smokeview RENDERALL sobre SOOT DENSITY e HRRPUV"))
        return result

    def _run(self, args: list[str], cwd: Path, log_path: Path, deadline: float, label: str) -> None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ExecutionError(RunState.FAILED, f"Tempo máximo excedido antes de {label}.")
        with log_path.open("wb") as log:
            try:
                proc = subprocess.run(args, cwd=str(cwd), stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                      timeout=remaining, env=self._env(), shell=False)
            except subprocess.TimeoutExpired:
                raise ExecutionError(RunState.FAILED, f"{label} excedeu o tempo máximo e foi interrompido.") from None
            except OSError:
                raise ExecutionError(RunState.FAILED, f"{label} não pôde ser iniciado.") from None
        if proc.returncode != 0 and label != "FDS":
            raise ExecutionError(RunState.FAILED, f"{label} terminou com código {proc.returncode}.")


def _read_series(path: Path, x: str, y: str) -> dict:
    lines = path.read_text(errors="replace").splitlines()
    if len(lines) < 3:
        return {}
    header = [h.strip().strip('"') for h in lines[1].split(",")]
    if x not in header or y not in header:
        return {}
    xi, yi = header.index(x), header.index(y)
    pts = []
    for line in lines[2:]:
        cols = line.split(",")
        try:
            pts.append((float(cols[xi]), float(cols[yi])))
        except (ValueError, IndexError):
            continue
    step = max(1, len(pts) // 200)
    return {"x": "t", "x_unit": lines[0].split(",")[xi].strip().strip('"'), "y": y,
            "y_unit": lines[0].split(",")[yi].strip().strip('"'), "points": pts[::step]}


def _read_devc(path: Path) -> dict:
    lines = path.read_text(errors="replace").splitlines()
    if len(lines) < 3:
        return {}
    units = [u.strip().strip('"') for u in lines[0].split(",")]
    names = [n.strip().strip('"') for n in lines[1].split(",")]
    cols = {n: [] for n in names}
    for line in lines[2:]:
        parts = line.split(",")
        for n, v in zip(names, parts):
            try:
                cols[n].append(float(v))
            except ValueError:
                pass
    time_col = cols.get("Time", [])
    step = max(1, len(time_col) // 200)
    return {"unit": dict(zip(names, units)),
            "series": {n: list(zip(time_col[::step], cols[n][::step])) for n in names if n != "Time"}}


class FakeExecutor:
    """Executor de TESTE: não roda FDS. Tudo é rotulado como demonstrativo."""

    name = "fake-test-executor"
    demo = True

    def __init__(self, fail_at: RunState | None = None, available: bool = True):
        self._fail_at, self._available = fail_at, available
        self.calls: list[str] = []

    def available(self) -> tuple[bool, str]:
        return self._available, "ok" if self._available else "executor simulado indisponível"

    def versions(self) -> ToolVersions:
        return ToolVersions(fds="FAKE", smokeview="FAKE", ffmpeg="FAKE")

    def run(self, run_dir: Path, chid: str, fds_text: str, t_end: float, timeout_s: float,
            progress: Progress) -> ExecutionResult:
        self.calls.append(chid)
        res = ExecutionResult(versions=self.versions())
        f = run_dir / f"{chid}.fds"
        f.write_text(fds_text, encoding="utf-8")
        res.artifacts.append(_artifact("FDS_INPUT", f))
        for state in (RunState.RUNNING_FDS, RunState.PROCESSING_RESULTS, RunState.RENDERING):
            progress(state)
            if self._fail_at == state:
                raise ExecutionError(RunState.FAILED, f"falha simulada em {state.value}")
        res.results = {"fds_completed": False, "note": "execução simulada de teste"}
        return res
