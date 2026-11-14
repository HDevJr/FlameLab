"""Área de trabalho local em JSON (`var/`). Identificadores são validados antes de virar
nome de arquivo, e a escrita é atômica (arquivo temporário + troca)."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from backend.app.paths import var_dir

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,95}$")


class InvalidId(ValueError):
    pass


def safe_id(value: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value) or ".." in value:
        raise InvalidId("identificador inválido")
    return value


def area(name: str) -> Path:
    path = var_dir() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    for attempt in range(25):  # Windows: a troca falha se outro thread estiver lendo o destino
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == 24:
                raise
            time.sleep(0.02)


def read_json(path: Path) -> Any | None:
    for attempt in range(25):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None
        except PermissionError:
            time.sleep(0.02)
    return None
