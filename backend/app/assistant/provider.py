"""Abstração de provedor de LLM (BL-05.04). Somente Gemini é implementado no MVP."""

from __future__ import annotations

from enum import Enum
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ProviderErrorKind(str, Enum):
    AUTH = "AUTH"  # 401/403: chave inválida ou sem permissão
    QUOTA = "QUOTA"  # 429: cota/limite de taxa
    UNAVAILABLE = "UNAVAILABLE"  # 5xx ou falha de transporte
    TIMEOUT = "TIMEOUT"
    INVALID_RESPONSE = "INVALID_RESPONSE"  # JSON ausente/fora do schema
    BAD_REQUEST = "BAD_REQUEST"  # 400/404: modelo inexistente, parâmetro inválido
    CONFIG = "CONFIG"  # provedor não configurado
    UNKNOWN = "UNKNOWN"


RETRYABLE = frozenset({ProviderErrorKind.UNAVAILABLE, ProviderErrorKind.TIMEOUT})


class ProviderError(Exception):
    """Erro saneado: a mensagem é genérica e NUNCA contém a credencial ou o corpo bruto."""

    def __init__(self, kind: ProviderErrorKind, status_code: int | None = None, attempts: int = 1):
        self.kind = kind
        self.status_code = status_code
        self.attempts = attempts
        super().__init__(f"provider error: {kind.value} (status={status_code}, attempts={attempts})")


class LLMProvider(Protocol):
    name: str
    model: str

    def generate_json(self, system: str, user: str, schema: type[T], timeout: float) -> T:
        """Gera e valida JSON contra `schema`. Lança `ProviderError` em qualquer falha."""
        ...
