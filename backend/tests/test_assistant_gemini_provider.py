"""Adaptador Gemini com CLIENTE SIMULADO (sem rede). Teste G: timeout e 503."""

import json
import logging

import httpx
import pytest
from google.genai import errors

from backend.app.assistant.gemini_provider import GeminiProvider
from backend.app.assistant.provider import ProviderError, ProviderErrorKind
from backend.app.assistant.schemas import LLMOutput

SECRET = "AIza-FAKE-SECRET-NEVER-LOG-123"


class _Resp:
    def __init__(self, text):
        self.text = text


class _Models:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def generate_content(self, model, contents, config):
        self.calls.append((model, config))
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return _Resp(item)


class _Client:
    def __init__(self, script):
        self.models = _Models(script)


def _provider(script, attempts=2, budget=45.0):
    sleeps = []
    p = GeminiProvider(api_key=SECRET, model="gemini-test", max_attempts=attempts, total_budget_s=budget,
                       client=_Client(script), sleep=sleeps.append)
    return p, sleeps


def _server_503():
    return errors.ServerError(503, {"error": {"code": 503, "message": f"overloaded key={SECRET}", "status": "UNAVAILABLE"}})


VALID = json.dumps({"claims": [], "abstain": True, "abstain_reason": "sem evidência"})


def test_valid_json_is_parsed_and_config_is_structured():
    p, _ = _provider([VALID])
    out = p.generate_json("sys", "user", LLMOutput, timeout=5)
    assert out.abstain is True
    model, config = p._client.models.calls[0]
    assert model == "gemini-test" and config.response_mime_type == "application/json"
    assert config.http_options.timeout == 5000 and config.temperature == 0.0
    schema = config.response_json_schema
    assert schema == LLMOutput.provider_json_schema()
    assert "anyOf" not in json.dumps(schema) and "$defs" not in json.dumps(schema)


def test_503_retries_with_backoff_then_succeeds():
    p, sleeps = _provider([_server_503(), VALID])
    assert p.generate_json("s", "u", LLMOutput, 5).abstain
    assert sleeps == [1.0]


def test_503_persistent_is_bounded_and_sanitized(caplog):
    caplog.set_level(logging.DEBUG)
    p, sleeps = _provider([_server_503(), _server_503(), _server_503()], attempts=2)
    with pytest.raises(ProviderError) as ei:
        p.generate_json("s", "u", LLMOutput, 5)
    err = ei.value
    assert err.kind == ProviderErrorKind.UNAVAILABLE and err.status_code == 503 and err.attempts == 2
    assert len(p._client.models.calls) == 2 and sleeps == [1.0]
    assert SECRET not in str(err) and SECRET not in caplog.text
    assert err.__cause__ is None


def test_timeout_is_mapped_and_retried():
    p, _ = _provider([httpx.ReadTimeout("t"), httpx.ReadTimeout("t")])
    with pytest.raises(ProviderError) as ei:
        p.generate_json("s", "u", LLMOutput, 5)
    assert ei.value.kind == ProviderErrorKind.TIMEOUT and ei.value.attempts == 2


@pytest.mark.parametrize("code,kind", [(401, ProviderErrorKind.AUTH), (403, ProviderErrorKind.AUTH),
                                       (429, ProviderErrorKind.QUOTA), (404, ProviderErrorKind.BAD_REQUEST)])
def test_non_retryable_errors_fail_fast(code, kind):
    p, sleeps = _provider([errors.ClientError(code, {"error": {"code": code, "message": SECRET}})])
    with pytest.raises(ProviderError) as ei:
        p.generate_json("s", "u", LLMOutput, 5)
    assert ei.value.kind == kind and sleeps == [] and SECRET not in str(ei.value)


@pytest.mark.parametrize("text", ["não é json", json.dumps({"claims": [{"type": "INVENTADO", "text_pt": "x"}]}), ""])
def test_invalid_json_or_schema_is_rejected(text):
    p, sleeps = _provider([text])
    with pytest.raises(ProviderError) as ei:
        p.generate_json("s", "u", LLMOutput, 5)
    assert ei.value.kind == ProviderErrorKind.INVALID_RESPONSE and sleeps == []


def test_total_budget_limits_attempts():
    clock = iter([0.0, 0.0, 10.0, 10.0, 10.0])
    p = GeminiProvider(api_key=SECRET, model="m", max_attempts=3, total_budget_s=5.0,
                       client=_Client([_server_503(), VALID]), sleep=lambda s: None,
                       monotonic=lambda: next(clock))
    with pytest.raises(ProviderError):
        p.generate_json("s", "u", LLMOutput, 5)
    assert len(p._client.models.calls) == 1


def test_missing_key_or_model_is_config_error():
    with pytest.raises(ProviderError) as ei:
        GeminiProvider(api_key="", model="m")
    assert ei.value.kind == ProviderErrorKind.CONFIG
    with pytest.raises(ProviderError):
        GeminiProvider(api_key="k", model="")
