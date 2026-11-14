"""Smoke test REAL do Gemini (acionamento explícito; não faz parte do pytest).

Uso (PowerShell, na raiz do repositório):
    .\\.venv\\Scripts\\python.exe scripts\\smoke_gemini.py

- Lê GEMINI_API_KEY e FLAMELAB_LLM_MODEL do ambiente / .env da raiz (caminho explícito).
- Usa SOMENTE evidência SINTÉTICA (TEST-01). Não valida conteúdo científico BASS-II.
- Passa todas as respostas pelo verificador V1–V8.
- Sem chave/modelo → NOT_RUN (nunca PASS). Erro do provedor → PROVIDER_ERROR com o tipo.
- Grava relatório sem credenciais em docs/evidence/smoke_gemini_<UTC>.json.
"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.assistant.cards import GapInput, RecordInput, gap_card, record_card  # noqa: E402
from backend.app.assistant.config import load_settings  # noqa: E402
from backend.app.assistant.gemini_provider import GeminiProvider  # noqa: E402
from backend.app.assistant.provider import ProviderError  # noqa: E402
from backend.app.assistant.retrieval import InMemoryEvidenceSource  # noqa: E402
from backend.app.assistant.schemas import AskRequest  # noqa: E402
from backend.app.assistant.service import AssistantService  # noqa: E402


def synthetic_source() -> InMemoryEvidenceSource:
    def rec(param, label, value, unit=None, role="CONDICAO"):
        return record_card(RecordInput(
            record_id=f"TEST-01.{param}", test_uid="TEST-01", test_label="TEST-01", investigation_id="SYN-INV",
            parameter=param, label_pt=label, role=role, nature="OBSERVADO", status="CONFERIDO_FONTE",
            original={"value": value, "unit": unit}, document_id="SYN-DOC", synthetic=True))

    return InMemoryEvidenceSource([
        rec("material", "Material", "PMMA", role="METADADO"),
        rec("thickness", "Espessura da amostra", 1, "mm"),
        rec("airflow_velocity", "Velocidade do ar", 9, "cm/s"),
        gap_card(GapInput(gap_id="GAP-TEST-01-pressure", test_uid="TEST-01", test_label="TEST-01",
                          investigation_id="SYN-INV", parameter="pressure", label_pt="Pressão",
                          keywords=["pressão", "pressao", "pressure"],
                          explanation_pt="A pressão não foi informada.", synthetic=True)),
    ])


CASES = [
    ("A_extracao", "Qual material foi utilizado e qual sua espessura?"),
    ("B_abstencao", "Qual era a pressão do experimento?"),
    ("J_extrapolacao", "Qual seria a propagação da chama na atmosfera de Marte?"),
]


def judge(case: str, ans) -> str:
    if ans.mode.value != "LIVE":
        return "PROVIDER_ERROR" if ans.provider_error else "FAIL"
    texts = " ".join(c.text_pt for c in ans.claims)
    if case == "A_extracao":
        ok = (not ans.abstained and "PMMA" in texts
              and any(abs(n.value - 1) < 1e-9 and (n.unit or "").lower() in ("mm",) for c in ans.claims for n in c.numbers))
    elif case == "B_abstencao":
        ok = ans.abstained and all(not c.numbers for c in ans.claims)
    else:
        ok = ans.abstained and "MARTE" in ans.extrapolation_flags and all(not c.numbers for c in ans.claims)
    return "PASS" if ok else "FAIL"


def main() -> int:
    settings = load_settings()
    now = datetime.now(timezone.utc)
    report: dict = {
        "kind": "SMOKE_TEST_REAL_GEMINI_EVIDENCIA_SINTETICA",
        "warning": "Evidência sintética (TEST-01). Não valida conteúdo científico BASS-II/NASA.",
        "executed_at_utc": now.isoformat(),
        "provider": "gemini",
        "model": settings.model,
        "key_present": settings.gemini_api_key is not None,
        "cases": [],
    }
    try:
        import google.genai as genai
        report["sdk_google_genai"] = genai.__version__
    except Exception:  # noqa: BLE001
        report["sdk_google_genai"] = None

    if not settings.gemini_api_key or not settings.model:
        report["overall"] = "NOT_RUN"
        report["reason"] = "GEMINI_API_KEY ou FLAMELAB_LLM_MODEL ausente"
    else:
        provider = GeminiProvider(settings.gemini_api_key.get_secret_value(), settings.model,
                                  max_attempts=settings.max_attempts, total_budget_s=settings.total_budget_s)
        with tempfile.TemporaryDirectory() as tmp:
            live = settings.model_copy(update={"mode": "live", "cache_dir": Path(tmp)})
            svc = AssistantService(live, synthetic_source(), provider)
            for case, question in CASES:
                try:
                    ans = svc.ask(AskRequest(question=question, scope={"test_uids": ["TEST-01"]}))
                except ProviderError as err:  # não esperado: o serviço já trata
                    report["cases"].append({"case": case, "status": "PROVIDER_ERROR", "error": err.kind.value})
                    continue
                report["cases"].append({
                    "case": case, "question": question, "status": judge(case, ans),
                    "mode": ans.mode.value, "abstained": ans.abstained,
                    "abstain_reason": ans.abstain_reason.value if ans.abstain_reason else None,
                    "provider_error": ans.provider_error, "extrapolation_flags": ans.extrapolation_flags,
                    "latency_ms": ans.latency_ms,
                    "approved_claims": [c.model_dump(mode="json") for c in ans.claims],
                    "blocked_claims": [b.model_dump(mode="json") for b in ans.blocked_claims],
                })
        statuses = {c["status"] for c in report["cases"]}
        report["overall"] = ("PASS" if statuses == {"PASS"} else
                             "PROVIDER_ERROR" if "PROVIDER_ERROR" in statuses and "FAIL" not in statuses else "FAIL")

    out_dir = ROOT / "docs" / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"smoke_gemini_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if settings.gemini_api_key and settings.gemini_api_key.get_secret_value() in text:
        raise SystemExit("ABORTADO: credencial detectada no relatório")
    out.write_text(text, encoding="utf-8")
    print(f"overall={report['overall']} model={report['model']} report={out.relative_to(ROOT)}")
    for c in report["cases"]:
        print(f"  {c['case']}: {c['status']} mode={c.get('mode')} abstained={c.get('abstained')} "
              f"approved={len(c.get('approved_claims', []))} blocked={len(c.get('blocked_claims', []))}")
    return 0 if report["overall"] in ("PASS", "NOT_RUN") else 1


if __name__ == "__main__":
    raise SystemExit(main())
