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


@app.middleware("http")
async def read_only_guard(request, call_next):
    """Demonstração pública: bloqueia toda escrita. GET/HEAD/OPTIONS e POST /api/ask passam."""
    from fastapi.responses import JSONResponse

    from backend.app.readonly import READ_ONLY_ALLOWED_POSTS, is_read_only

    if is_read_only() and request.method not in ("GET", "HEAD", "OPTIONS") and request.url.path not in READ_ONLY_ALLOWED_POSTS:
        return JSONResponse(status_code=403, content={"error": {
            "code": "READ_ONLY_DEMO", "message": "Esta é uma demonstração pública somente leitura: importar, revisar e simular ficam desativados.", "details": {}}})
    return await call_next(request)
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


@app.get("/api/status", tags=["system"])
def status() -> dict:
    """Estado operacional para a barra superior. Nunca devolve credenciais; saúde da API não implica validade científica."""
    from backend.app.assistant.config import load_settings

    s = load_settings()
    return {"data": {
        "api": "ok", "read_only": __import__("backend.app.readonly", fromlist=["is_read_only"]).is_read_only(),
        "dataset_version": get_dataset_store().dataset_version,
        "assistant": {"mode": s.mode, "provider": s.provider, "model": s.model, "live_ready": s.live_ready},
    }}


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    """Não implica que IA, dados ou FDS estejam disponíveis."""
    return {"status": "ok", "stage": "F00"}
