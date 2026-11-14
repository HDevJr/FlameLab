"""FlameLab API — F00 + assistente científico (BL-05). Sem acesso NASA/FDS."""

from fastapi import FastAPI

from backend.app.api.assistant import router as assistant_router
from backend.app.api.errors import install_error_handlers

app = FastAPI(title="FlameLab API", version="0.1.0-bl05")
install_error_handlers(app)
app.include_router(assistant_router)


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    """Não implica que IA, dados ou FDS estejam disponíveis."""
    return {"status": "ok", "stage": "F00"}
