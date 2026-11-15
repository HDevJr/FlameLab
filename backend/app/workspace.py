"""Área de trabalho local em JSON (`var/`). Identificadores são validados antes de virar
nome de arquivo, e a escrita é atômica (arquivo temporário + troca)."""

from __future__ import annotations

import json
import os
import re
import time
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Iterator

from backend.app.paths import var_dir
from backend.app.readonly import is_read_only

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,95}$")

# BL-17.2: modo de teste da interface. Revisões guiadas e versões de caso criadas em modo TESTE
# ficam em `var/test_mode/`, nunca nas áreas científicas; demais áreas (importações, catálogo) são
# apenas lidas. O modo vale para o contexto da requisição (contextvars), não para o processo.
MODES = ("SCIENTIFIC", "TEST")
TEST_ROOT = "test_mode"
_ISOLATED_IN_TEST = frozenset({"guided_reviews", "cases"})
_MODE: ContextVar[str] = ContextVar("flamelab_workspace_mode", default="SCIENTIFIC")


def current_mode() -> str:
    return _MODE.get()


@contextmanager
def use_mode(mode: str) -> Iterator[None]:
    if mode not in MODES:
        raise ValueError("Modo de trabalho inválido.")
    token = _MODE.set(mode)
    try:
        yield
    finally:
        _MODE.reset(token)


class InvalidId(ValueError):
    pass


def safe_id(value: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value) or ".." in value:
        raise InvalidId("identificador inválido")
    return value


def area(name: str) -> Path:
    base = var_dir()
    if _MODE.get() == "TEST" and name in _ISOLATED_IN_TEST:
        base = base / TEST_ROOT
    path = base / name
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        if not is_read_only():  # disco somente leitura só é aceito na demonstração pública
            raise
    return path


def write_json(path: Path, data: Any) -> None:
    if is_read_only():
        return  # demonstração pública: nada é gravado (análises calculadas na hora não são persistidas)
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
