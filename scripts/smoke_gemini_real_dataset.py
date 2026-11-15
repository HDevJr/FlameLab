"""Smoke REAL do Gemini sobre o dataset REAL (data/), acionamento explícito.

Mostra o comportamento do assistente com a curadoria no estado atual (registros não
conferidos são inelegíveis; lacunas são elegíveis). Grava docs/evidence/smoke_real_dataset_<UTC>.json
sem credenciais. Sem chave/modelo → NOT_RUN.
"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.assistant.config import load_settings  # noqa: E402
from backend.app.assistant.gemini_provider import GeminiProvider  # noqa: E402
from backend.app.assistant.schemas import AskRequest  # noqa: E402
from backend.app.assistant.service import AssistantService  # noqa: E402
from backend.app.dataset.adapter import DatasetEvidenceSource  # noqa: E402
from backend.app.dataset.store import DatasetStore  # noqa: E402

QUESTIONS = [
    "Qual era a pressão no ensaio M1?",
    "Qual foi a velocidade de propagação da chama no ensaio M1?",
]


def main() -> int:
    s = load_settings()
    now = datetime.now(timezone.utc)
    store = DatasetStore.load()
    report = {"kind": "SMOKE_REAL_GEMINI_REAL_DATASET", "executed_at_utc": now.isoformat(), "model": s.model,
              "dataset_version": store.dataset_version,
              "record_statuses": sorted({r.status for r in store.records.values()}), "cases": []}
    if not s.gemini_api_key or not s.model:
        report["overall"] = "NOT_RUN"
    else:
        provider = GeminiProvider(s.gemini_api_key.get_secret_value(), s.model, s.max_attempts, s.total_budget_s)
        with tempfile.TemporaryDirectory() as tmp:
            svc = AssistantService(s.model_copy(update={"mode": "live", "cache_dir": Path(tmp)}),
                                   DatasetEvidenceSource(store), provider)
            for q in QUESTIONS:
                a = svc.ask(AskRequest(question=q, scope={"investigation_id": "PSI-25", "test_uids": ["BASS2-M1"]}))
                report["cases"].append({
                    "question": q, "mode": a.mode.value, "abstained": a.abstained,
                    "abstain_reason": a.abstain_reason.value if a.abstain_reason else None,
                    "provider_error": a.provider_error, "latency_ms": a.latency_ms,
                    "retrieved_kinds": sorted({r.kind.value for r in a.retrieved}),
                    "approved_claims": [c.model_dump(mode="json") for c in a.claims],
                    "blocked_claims": [b.model_dump(mode="json") for b in a.blocked_claims],
                    "numbers_published": [n.model_dump() for c in a.claims for n in c.numbers],
                    "warnings": a.warnings,
                })
        ok = all(c["mode"] == "LIVE" and c["abstained"] and not c["numbers_published"] for c in report["cases"])
        report["overall"] = "PASS" if ok else (
            "PROVIDER_ERROR" if any(c["provider_error"] for c in report["cases"]) else "FAIL")
        report["pass_criterion"] = "Antes da revisão humana: LIVE, abstenção e nenhum número publicado."
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if s.gemini_api_key and s.gemini_api_key.get_secret_value() in text:
        raise SystemExit("ABORTADO: credencial detectada")
    out = ROOT / "docs" / "evidence" / f"smoke_real_dataset_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(text + "\n", encoding="utf-8")
    print(f"overall={report['overall']} -> {out.relative_to(ROOT)}")
    for c in report["cases"]:
        print(f"  {c['question']} | {c['mode']} abst={c['abstained']} {c['abstain_reason']} "
              f"approved={len(c['approved_claims'])} blocked={len(c['blocked_claims'])}")
    return 0 if report["overall"] in ("PASS", "NOT_RUN") else 1


if __name__ == "__main__":
    raise SystemExit(main())
