"""Configuração do assistente a partir de variáveis de ambiente e do `.env` da raiz.

- O `.env` é lido por CAMINHO EXPLÍCITO (raiz do repositório), sem `load_dotenv()`
  implícito, que falha quando o código roda via `python -` ou a partir de outro cwd.
- `os.environ` tem precedência sobre o `.env` e não é modificado.
- A ausência de chave/modelo NÃO impede os modos `off` e `cache`.
- A chave é guardada como `SecretStr` e não aparece em repr, logs ou respostas.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Mapping

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, SecretStr

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENV_FILE = REPO_ROOT / ".env"
DEFAULT_CACHE_DIR = REPO_ROOT / "data" / "ai_cache"

Mode = Literal["live", "cache", "off"]


class AssistantSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: Mode = "off"
    provider: str = "none"
    model: str | None = None
    gemini_api_key: SecretStr | None = None
    timeout_s: float = 20.0
    max_attempts: int = 2
    total_budget_s: float = 45.0
    cache_dir: Path = DEFAULT_CACHE_DIR
    cache_write: bool = True
    config_warnings: tuple[str, ...] = ()

    @property
    def live_ready(self) -> bool:
        return (
            self.provider == "gemini"
            and bool(self.model)
            and self.gemini_api_key is not None
            and bool(self.gemini_api_key.get_secret_value())
        )


def _float(raw: str | None, default: float, lo: float, hi: float, name: str, warns: list[str]) -> float:
    if raw in (None, ""):
        return default
    try:
        return min(max(float(raw), lo), hi)
    except ValueError:
        warns.append(f"{name} inválido; usando {default}")
        return default


def load_settings(
    env: Mapping[str, str] | None = None,
    env_file: Path | None = DEFAULT_ENV_FILE,
) -> AssistantSettings:
    """Monta a configuração. `env=None` usa `os.environ`; `env_file=None` ignora o `.env`."""
    values: dict[str, str] = {}
    if env_file is not None and Path(env_file).is_file():
        values.update({k: v for k, v in dotenv_values(env_file).items() if v is not None})
    values.update(dict(os.environ if env is None else env))

    warns: list[str] = []
    mode_raw = (values.get("FLAMELAB_LLM_MODE") or "off").strip().lower()
    if mode_raw not in ("live", "cache", "off"):
        warns.append("FLAMELAB_LLM_MODE inválido; usando off")
        mode_raw = "off"
    provider = (values.get("FLAMELAB_LLM_PROVIDER") or "none").strip().lower()
    if provider not in ("gemini", "none"):
        warns.append("FLAMELAB_LLM_PROVIDER não suportado; somente gemini está implementado")
        provider = "none"
    key = (values.get("GEMINI_API_KEY") or "").strip()
    attempts_raw = values.get("FLAMELAB_LLM_MAX_ATTEMPTS")
    try:
        attempts = min(max(int(attempts_raw), 1), 3) if attempts_raw else 2
    except ValueError:
        warns.append("FLAMELAB_LLM_MAX_ATTEMPTS inválido; usando 2")
        attempts = 2
    cache_dir = values.get("FLAMELAB_AI_CACHE_DIR")
    return AssistantSettings(
        mode=mode_raw,  # type: ignore[arg-type]
        provider=provider,
        model=(values.get("FLAMELAB_LLM_MODEL") or "").strip() or None,
        gemini_api_key=SecretStr(key) if key else None,
        timeout_s=_float(values.get("FLAMELAB_LLM_TIMEOUT_S"), 20.0, 1.0, 120.0, "FLAMELAB_LLM_TIMEOUT_S", warns),
        max_attempts=attempts,
        total_budget_s=_float(values.get("FLAMELAB_LLM_TOTAL_BUDGET_S"), 45.0, 1.0, 300.0, "FLAMELAB_LLM_TOTAL_BUDGET_S", warns),
        cache_dir=Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR,
        cache_write=(values.get("FLAMELAB_AI_CACHE_WRITE") or "true").strip().lower() != "false",
        config_warnings=tuple(warns),
    )
