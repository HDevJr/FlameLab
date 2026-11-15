"""Modo de demonstração pública SOMENTE LEITURA (FLAMELAB_READ_ONLY=true).

Usado na publicação na Vercel: o disco é somente leitura e qualquer pessoa pode abrir o link. Nenhuma rota grava
dados (importar PDF, revisar, decidir lacunas, criar cenários, executar simulação). A única exceção é `POST /api/ask`,
que não grava nada (e só deve responder do cache quando `FLAMELAB_LLM_MODE=cache`)."""

from __future__ import annotations

import os

READ_ONLY_ALLOWED_POSTS = frozenset({"/api/ask"})


def is_read_only() -> bool:
    return os.environ.get("FLAMELAB_READ_ONLY", "").strip().lower() in ("1", "true", "yes", "on")
