"""Adaptador Google Gemini (SDK oficial `google-genai`).

- Saída JSON estruturada (`response_mime_type=application/json` + `response_schema`),
  validada novamente com Pydantic.
- Timeout por chamada; retries do SDK desligados; retry próprio apenas para
  UNAVAILABLE/TIMEOUT, com no máximo `max_attempts`, espera progressiva e orçamento total.
- Erros mapeados para `ProviderErrorKind`; nenhuma mensagem bruta do SDK é propagada.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, ValidationError

from backend.app.assistant.provider import RETRYABLE, ProviderError, ProviderErrorKind

log = logging.getLogger("flamelab.assistant.gemini")
T = TypeVar("T", bound=BaseModel)


def _classify(exc: BaseException) -> tuple[ProviderErrorKind, int | None]:
    from google.genai import errors

    if isinstance(exc, errors.APIError):
        code = getattr(exc, "code", None)
        if code in (401, 403):
            return ProviderErrorKind.AUTH, code
        if code == 429:
            return ProviderErrorKind.QUOTA, code
        if code in (408,):
            return ProviderErrorKind.TIMEOUT, code
        if code is not None and 500 <= code < 600:
            return ProviderErrorKind.UNAVAILABLE, code
        if code in (400, 404):
            return ProviderErrorKind.BAD_REQUEST, code
        return ProviderErrorKind.UNKNOWN, code
    if isinstance(exc, TimeoutError) or "timeout" in type(exc).__name__.lower():
        return ProviderErrorKind.TIMEOUT, None
    name = type(exc).__name__.lower()
    if any(k in name for k in ("connect", "network", "transport", "protocol", "readerror", "remote")):
        return ProviderErrorKind.UNAVAILABLE, None
    return ProviderErrorKind.UNKNOWN, None


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        max_attempts: int = 2,
        total_budget_s: float = 45.0,
        backoff_s: float = 1.0,
        client: Any | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        if not model:
            raise ProviderError(ProviderErrorKind.CONFIG)
        self.model = model
        self._max_attempts = max(1, min(max_attempts, 3))
        self._budget = total_budget_s
        self._backoff = backoff_s
        self._sleep = sleep
        self._monotonic = monotonic
        if client is None:
            if not api_key:
                raise ProviderError(ProviderErrorKind.CONFIG)
            from google import genai
            from google.genai import types

            # retry_options=None → SDK não repete; o controle de tentativas é deste adaptador.
            client = genai.Client(api_key=api_key, http_options=types.HttpOptions(retry_options=None))
        self._client = client
        self._local = threading.local()

    def _call_once(self, system: str, user: str, schema: type[T], timeout: float) -> T:
        from google.genai import types

        schema_fn = getattr(schema, "provider_json_schema", None)
        json_schema = schema_fn() if callable(schema_fn) else schema.model_json_schema()
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=json_schema,
            temperature=0.0,
            http_options=types.HttpOptions(timeout=int(timeout * 1000)),
        )
        response = self._client.models.generate_content(model=self.model, contents=user, config=config)
        meta = getattr(response, "usage_metadata", None)
        self._local.usage = None if meta is None else {
            "input_tokens": getattr(meta, "prompt_token_count", None),
            "output_tokens": getattr(meta, "candidates_token_count", None),
            "total_tokens": getattr(meta, "total_token_count", None)}
        text = getattr(response, "text", None)
        if not text:
            raise ProviderError(ProviderErrorKind.INVALID_RESPONSE)
        try:
            return schema.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError, TypeError):
            raise ProviderError(ProviderErrorKind.INVALID_RESPONSE) from None

    def last_usage(self) -> dict | None:
        """Tokens da última chamada desta thread (informado pelo SDK; não é custo em dinheiro)."""
        return getattr(self._local, "usage", None)

    def generate_json(self, system: str, user: str, schema: type[T], timeout: float) -> T:
        start = self._monotonic()
        last: ProviderError | None = None
        for attempt in range(1, self._max_attempts + 1):
            remaining = self._budget - (self._monotonic() - start)
            if remaining <= 0:
                break
            try:
                return self._call_once(system, user, schema, min(timeout, remaining))
            except ProviderError as err:
                err.attempts = attempt
                last = err
            except Exception as exc:  # noqa: BLE001 — o SDK pode lançar diversos tipos
                kind, code = _classify(exc)
                last = ProviderError(kind, code, attempt)
            log.warning("gemini attempt %d failed: %s", attempt, last.kind.value)
            if last.kind not in RETRYABLE or attempt == self._max_attempts:
                break
            wait = self._backoff * (2 ** (attempt - 1))
            if (self._monotonic() - start) + wait >= self._budget:
                break
            self._sleep(wait)
        raise last or ProviderError(ProviderErrorKind.TIMEOUT)
