"""Caminhos do projeto. `var/` é a área de trabalho local (não versionada):
uploads, resultados de enriquecimento, cenários, fila e execuções."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CASES_DIR = REPO_ROOT / "fds" / "cases"


def var_dir() -> Path:
    raw = os.environ.get("FLAMELAB_VAR_DIR")
    path = Path(raw) if raw else REPO_ROOT / "var"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        if os.environ.get("FLAMELAB_READ_ONLY", "").strip().lower() not in ("1", "true", "yes", "on"):
            raise
    return path
