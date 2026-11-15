"""Serve the built UI and real API against a disposable BL-17 workspace.

No LLM, no NASA network calls, no real FDS execution. Run from the repository root.
"""
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SANDBOX = Path(tempfile.mkdtemp(prefix="bl17-browser-workspace-", dir=ROOT / "tmp"))
os.environ["FLAMELAB_VAR_DIR"] = str(SANDBOX)
os.environ["FLAMELAB_LLM_MODE"] = "off"
os.environ["FLAMELAB_NASA_MODE"] = "fixture"

for name in ("audit", "enrichment", "provenance"):
    original = ROOT / "var" / name
    target = SANDBOX / name
    if original.exists() and not target.exists():
        shutil.copytree(original, target)

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from backend.app.api.platform import Services
from backend.app.main import app
from backend.app.simulation.executor import FakeExecutor

Services.executor = FakeExecutor()
Services.provider = None
app.mount("/assets", StaticFiles(directory=ROOT / "frontend/dist/assets"))


@app.get("/{path:path}")
def frontend(path: str):
    if path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(404)
    return FileResponse(ROOT / "frontend/dist/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=18017)
