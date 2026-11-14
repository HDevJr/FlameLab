"""BL-05.06 — cache de respostas geradas pelo provedor.

- Chave = sha256(pergunta normalizada + escopo + dataset_version + prompt_version).
  Mudou o dataset ou o prompt → outra chave → nenhum reaproveitamento indevido.
- Guarda a SAÍDA BRUTA do modelo (LLMOutput) e os metadados de geração. Na leitura,
  a saída é REVERIFICADA contra a recuperação atual antes de ser servida como CACHE.
- O nome do arquivo é sempre o hash hexadecimal; nenhum caminho vem da requisição.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ValidationError

from backend.app.assistant.schemas import AskScope, LLMOutput

log = logging.getLogger("flamelab.assistant.cache")


class CacheEntry(BaseModel):
    key: str
    question: str
    scope: AskScope
    dataset_version: str | None
    prompt_version: str
    provider: str
    model: str
    created_at: datetime
    output: LLMOutput


def _norm_question(q: str) -> str:
    q = unicodedata.normalize("NFKC", q).lower()
    return " ".join(q.split()).rstrip("?!. ")


def cache_key(question: str, scope: AskScope, dataset_version: str | None, prompt_version: str) -> str:
    payload = {
        "q": _norm_question(question),
        "inv": scope.investigation_id,
        "tests": sorted(scope.test_uids),
        "dataset_version": dataset_version,
        "prompt_version": prompt_version,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


class AnswerCache:
    def __init__(self, directory: Path):
        self._dir = Path(directory)

    def _path(self, key: str) -> Path:
        if len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
            raise ValueError("chave de cache inválida")
        return self._dir / f"{key}.json"

    def get(self, key: str) -> CacheEntry | None:
        path = self._path(key)
        if not path.is_file():
            return None
        try:
            entry = CacheEntry.model_validate_json(path.read_text(encoding="utf-8"))
        except (ValidationError, OSError, ValueError):
            log.warning("entrada de cache ilegível ignorada: %s", path.name)
            return None
        return entry if entry.key == key else None

    def put(self, entry: CacheEntry) -> None:
        path = self._path(entry.key)
        self._dir.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self._dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(entry.model_dump_json(indent=2))
            os.replace(tmp, path)
        except OSError:
            log.warning("falha ao gravar cache %s", path.name)
            try:
                os.unlink(tmp)
            except OSError:
                pass
