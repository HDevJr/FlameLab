"""Ponto de entrada da Vercel (função Python): expõe o FastAPI do FlameLab.

Publicação pública = demonstração SOMENTE LEITURA (FLAMELAB_READ_ONLY=true, ver backend/app/readonly.py)."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# padrões seguros caso as variáveis não estejam definidas no projeto da Vercel
os.environ.setdefault("FLAMELAB_READ_ONLY", "true")
os.environ.setdefault("FLAMELAB_LLM_MODE", "cache")
os.environ.setdefault("FLAMELAB_AI_CACHE_WRITE", "false")
os.environ.setdefault("FLAMELAB_NASA_MODE", "fixture")

from backend.app.main import app  # noqa: E402,F401  (a Vercel procura o objeto `app`)
