"""FlameLab API — assistente (BL-05), dataset (BL-02) e protótipo v2: importação, enriquecimento NASA, simulação."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.api.assistant import get_dataset_store, router as assistant_router
from backend.app.api.errors import install_error_handlers
from backend.app.api.platform import router as platform_router
from backend.app.version import APP_VERSION, CAPABILITIES


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Fail-fast (planning/02 §12): dataset inválido impede o servidor de subir.
    get_dataset_store()
    yield


app = FastAPI(title="FlameLab API", version=APP_VERSION, lifespan=lifespan)
install_error_handlers(app)
app.include_router(assistant_router)
app.include_router(platform_router)
from backend.app.api.cases import router as cases_router
app.include_router(cases_router)
from backend.app.api.guided_review import router as guided_review_router
app.include_router(guided_review_router)


@app.get("/api/version", tags=["system"])
def version() -> dict:
    """Versão e capacidades: permite ao frontend avisar quando o backend em execução está desatualizado."""
    return {"app_version": APP_VERSION, "capabilities": CAPABILITIES}


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    """Não implica que IA, dados ou FDS estejam disponíveis."""
    return {"status": "ok", "stage": "F00"}
