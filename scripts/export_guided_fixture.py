"""Regenera `frontend/src/fixtures/guided_review_m1.json` a partir da resposta REAL do backend.

Usa uma área `var/` temporária e vazia (nenhum registro do `var/` real), fontes NASA de fixture
e IA desligada. O arquivo resultante é o contrato de fio conferido por
`backend/tests/test_guided_review.py::test_frontend_fixture_matches_live_wire_contract`.

    $env:PYTHONPATH=(Get-Location).Path
    .\\.venv\\Scripts\\python.exe scripts/export_guided_fixture.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

with tempfile.TemporaryDirectory(prefix="flamelab-fixture-") as tmp:
    os.environ["FLAMELAB_VAR_DIR"] = str(Path(tmp) / "var")
    os.environ["FLAMELAB_NASA_MODE"] = "fixture"
    os.environ["FLAMELAB_LLM_MODE"] = "off"
    from fastapi.testclient import TestClient
    from backend.app.api.platform import Services
    from backend.app.main import app
    from backend.app.simulation.executor import FakeExecutor

    Services.executor = FakeExecutor()
    Services.provider = None
    Services.run_async = False
    response = TestClient(app).get("/api/experiments/BASS2-M1/guided-review")
    response.raise_for_status()
    data = response.json()["data"]
    assert data["revision"] == 0 and not data["history"], "a fixture deve vir de uma área vazia"
    target = ROOT / "frontend" / "src" / "fixtures" / "guided_review_m1.json"
    target.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    Services.reset()
    print(f"{target.relative_to(ROOT)}: {len(data['tasks'])} pendências, {len(data['requirements'])} requisitos")
