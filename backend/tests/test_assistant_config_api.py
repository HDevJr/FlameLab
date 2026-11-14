"""Configuração e endpoint POST /api/ask. Nenhum teste lê o .env real nem chama o Gemini."""

from fastapi.testclient import TestClient

from backend.app.api.assistant import get_assistant_service
from backend.app.assistant.config import load_settings
from backend.app.assistant.provider import ProviderError, ProviderErrorKind
from backend.app.assistant.retrieval import EmptyEvidenceSource
from backend.app.assistant.service import AssistantService, build_provider
from backend.app.main import app
from backend.tests.assistant_fixtures import FakeProvider, claim, output, settings, synthetic_test01_source

SECRET = "AIza-FAKE-SECRET-NEVER-RETURN-456"


# ---------------------------------------------------------------- configuração
def test_env_file_loaded_by_explicit_path_and_env_overrides(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(f"FLAMELAB_LLM_MODE=live\nFLAMELAB_LLM_PROVIDER=gemini\n"
                        f"FLAMELAB_LLM_MODEL=gemini-x\nGEMINI_API_KEY={SECRET}\n", encoding="utf-8")
    s = load_settings(env={"FLAMELAB_LLM_MODE": "cache"}, env_file=env_file)
    assert s.mode == "cache" and s.model == "gemini-x" and s.live_ready
    assert SECRET not in repr(s) and SECRET not in s.model_dump_json()


def test_missing_key_does_not_break_off_or_cache(tmp_path):
    for mode in ("off", "cache"):
        s = load_settings(env={"FLAMELAB_LLM_MODE": mode}, env_file=None)
        assert s.mode == mode and not s.live_ready and build_provider(s) is None


def test_invalid_mode_falls_back_to_off_with_warning():
    s = load_settings(env={"FLAMELAB_LLM_MODE": "turbo"}, env_file=None)
    assert s.mode == "off" and s.config_warnings


def test_live_without_key_builds_no_provider():
    s = load_settings(env={"FLAMELAB_LLM_MODE": "live", "FLAMELAB_LLM_PROVIDER": "gemini",
                           "FLAMELAB_LLM_MODEL": "m"}, env_file=None)
    assert build_provider(s) is None


# ---------------------------------------------------------------- API
def _client(service):
    app.dependency_overrides[get_assistant_service] = lambda: service
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_ask_contract_with_synthetic_evidence(tmp_path):
    fake = FakeProvider(output(claim("OBSERVACAO", "No experimento TEST-01 o material foi PMMA.",
                                     ["REC-TEST-01.material"])))
    c = _client(AssistantService(settings(tmp_path), synthetic_test01_source(), fake))
    r = c.post("/api/ask", json={"question": "Qual material?", "scope": {"test_uids": ["TEST-01"]}, "lang": "pt"})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"data", "dataset_version", "warnings"}
    d = body["data"]
    for f in ("answer_id", "question", "scope", "mode", "abstained", "abstain_reason", "extrapolation_flags",
              "claims", "blocked_claims", "retrieved", "provider", "model", "prompt_version",
              "dataset_version", "created_at", "latency_ms"):
        assert f in d
    assert d["mode"] == "LIVE" and d["claims"][0]["type"] == "OBSERVACAO"


def test_default_service_with_empty_dataset_abstains(tmp_path):
    s = settings(tmp_path, "live", gemini_api_key=SECRET)
    fake = FakeProvider(ProviderError(ProviderErrorKind.UNKNOWN))
    c = _client(AssistantService(s, EmptyEvidenceSource(), fake))
    r = c.post("/api/ask", json={"question": "Qual material foi utilizado no experimento?",
                                 "scope": {"investigation_id": "PSI-25", "test_uids": ["BASS2-M1"]}, "lang": "pt"})
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["mode"] == "DETERMINISTIC" and d["abstained"] and d["abstain_reason"] == "NO_ELIGIBLE_EVIDENCE"
    assert SECRET not in r.text and not fake.calls


def test_provider_failure_returns_200_structured_without_secret(tmp_path):
    s = settings(tmp_path, "live", gemini_api_key=SECRET)
    c = _client(AssistantService(s, synthetic_test01_source(), FakeProvider(ProviderError(ProviderErrorKind.UNAVAILABLE, 503))))
    r = c.post("/api/ask", json={"question": "Qual material?", "scope": {"test_uids": ["TEST-01"]}})
    assert r.status_code == 200 and r.json()["data"]["provider_error"] == "UNAVAILABLE"
    assert SECRET not in r.text


def test_invalid_requests_return_422_envelope(tmp_path):
    c = _client(AssistantService(settings(tmp_path, "off"), EmptyEvidenceSource(), None))
    bad = [
        {"question": "x" * 1001},
        {"question": "ok?"[:2]},
        {"question": "Pergunta válida?", "extra": 1},
        {"question": "Pergunta válida?", "lang": "en"},
        {"question": "Pergunta válida?", "scope": {"test_uids": ["../../etc/passwd"]}},
        {"question": "Pergunta válida?", "scope": {"test_uids": ["A", "B", "C", "D", "E"]}},
        {"question": "Pergunta válida?", "scope": {"file": "x"}},
    ]
    for payload in bad:
        r = c.post("/api/ask", json=payload)
        assert r.status_code == 422, payload
        err = r.json()["error"]
        assert err["code"] == "INVALID_REQUEST"
        assert "passwd" not in r.text


def test_off_mode_api_keeps_working(tmp_path):
    c = _client(AssistantService(settings(tmp_path, "off"), synthetic_test01_source(), None))
    r = c.post("/api/ask", json={"question": "Qual material?", "scope": {"test_uids": ["TEST-01"]}})
    d = r.json()["data"]
    assert r.status_code == 200 and d["mode"] == "UNAVAILABLE" and d["unavailable_reason"] == "MODE_OFF"
