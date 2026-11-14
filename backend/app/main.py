"""FlameLab API — F00 + assistente científico (BL-05) + dataset científico (BL-02). Sem FDS."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.api.assistant import get_dataset_store, router as assistant_router
from backend.app.api.errors import install_error_handlers


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Fail-fast (planning/02 §12): dataset inválido impede o servidor de subir.
    get_dataset_store()
    yield


app = FastAPI(title="FlameLab API", version="0.2.0-bl02", lifespan=lifespan)
install_error_handlers(app)
app.include_router(assistant_router)


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    """Não implica que IA, dados ou FDS estejam disponíveis."""
    return {"status": "ok", "stage": "F00"}
