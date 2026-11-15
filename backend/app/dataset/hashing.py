"""Verificação de integridade dos documentos-fonte (SHA-256).

O hash esperado nunca é reescrito por este código: divergências são reportadas.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

HashStatus = Literal["MATCH", "MISMATCH", "FILE_MISSING", "NOT_COMPUTED", "PATH_REJECTED"]


@dataclass(frozen=True)
class SourceCheck:
    document_id: str
    status: HashStatus
    expected_sha256: str | None
    actual_sha256: str | None
    size_bytes: int | None
    path: str | None


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def verify_source(document_id: str, local_path: str | None, expected: str | None, root: Path) -> SourceCheck:
    if not local_path:
        return SourceCheck(document_id, "NOT_COMPUTED", expected, None, None, None)
    root = root.resolve()
    path = (root / local_path).resolve()
    if not path.is_relative_to(root):
        return SourceCheck(document_id, "PATH_REJECTED", expected, None, None, local_path)
    if not path.is_file():
        return SourceCheck(document_id, "FILE_MISSING", expected, None, None, local_path)
    actual = sha256_file(path)
    size = path.stat().st_size
    if expected is None:
        return SourceCheck(document_id, "NOT_COMPUTED", None, actual, size, local_path)
    return SourceCheck(document_id, "MATCH" if actual == expected else "MISMATCH", expected, actual, size, local_path)
