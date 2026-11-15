"""API do protótipo v2: catálogo, importação, enriquecimento NASA e simulação.

Os singletons ficam em `Services` para que os testes troquem transporte, IA e executor
sem tocar em rede, no Gemini ou no FDS.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Literal

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.app import workspace
from backend.app.analysis import build_analysis
from backend.app.api.assistant import get_assistant_service, get_dataset_store
from backend.app.assistant.config import load_settings
from backend.app.assistant.service import build_provider
from backend.app.catalog.service import Catalog
from backend.app.dataset.review import ReviewRejected
from backend.app.dataset.store import DEFAULT_DATA_DIR, DatasetStore
from backend.app.ingest.pdf import PdfRejected
from backend.app.review_service import ReviewService, events_for
from backend.app.ingest.service import ImportService
from backend.app.nasa.clients.fixtures import FixtureTransport
from backend.app.nasa.clients.http import Transport, UrllibTransport
from backend.app.nasa.enrichment.service import EnrichmentService
from backend.app.paths import REPO_ROOT
from backend.app.simulation.case_builder import CaseValidationError
from backend.app.simulation.executor import Executor, LocalFdsExecutor
from backend.app.simulation.service import SimulationService

router = APIRouter(prefix="/api", tags=["platform"])

FIXTURE_DIR = REPO_ROOT / "backend" / "tests" / "fixtures" / "nasa"


class Services:
    """Contêiner substituível. `reset()` descarta tudo (usado pelos testes)."""

    transport_factory: Callable[[], Transport] | None = None
    executor: Executor | None = None
    provider: Any = "unset"
    run_async: bool = True
    quota_wait_s: float | None = None  # testes usam 0 (sem espera real)
    # Testes de revisão usam um dataset sintético em diretório temporário (nunca o data/ real).
    dataset_dirs: tuple[Path, Path] | None = None
    curation_log_dir: Path | None = None
    _store_cache: Any = None
    _catalog: Catalog | None = None
    _imports: ImportService | None = None
    _sim: SimulationService | None = None
    _review: ReviewService | None = None

    @classmethod
    def reset(cls) -> None:
        if cls._sim:
            cls._sim.stop()
        cls._store_cache = cls._catalog = cls._imports = cls._sim = cls._review = None

    @classmethod
    def store(cls):
        if cls.dataset_dirs:
            if cls._store_cache is None:
                cls._store_cache = DatasetStore.load(*cls.dataset_dirs)
            return cls._store_cache
        return get_dataset_store()

    @classmethod
    def reload_dataset(cls) -> None:
        """Depois de uma revisão curada o servidor relê e revalida o dataset (fail-fast)."""
        cls._store_cache = None
        get_dataset_store.cache_clear()
        get_assistant_service.cache_clear()
        cls.store()

    @classmethod
    def transport(cls) -> Transport:
        if cls.transport_factory:
            return cls.transport_factory()
        mode = os.environ.get("FLAMELAB_NASA_MODE", "online").lower()
        return FixtureTransport(FIXTURE_DIR) if mode == "fixture" else UrllibTransport()

    @classmethod
    def catalog(cls) -> Catalog:
        if cls._catalog is None:
            cls._catalog = Catalog(cls.store)
        return cls._catalog

    @classmethod
    def llm(cls):
        if cls.provider != "unset":
            return cls.provider
        return build_provider(load_settings())

    @classmethod
    def imports(cls) -> ImportService:
        if cls._imports is None:
            cls._imports = ImportService(cls.store, cls.transport, cls.llm(), run_async=cls.run_async,
                                         compat=lambda eid: cls.sim().compatibility(eid),
                                         **({} if cls.quota_wait_s is None else {"quota_wait_s": cls.quota_wait_s}))
        return cls._imports

    @classmethod
    def sim(cls) -> SimulationService:
        if cls._sim is None:
            executor = cls.executor or LocalFdsExecutor()
            cls._sim = SimulationService(executor, cls.catalog)
        return cls._sim

    @classmethod
    def review(cls) -> ReviewService:
        if cls._review is None:
            dirs = cls.dataset_dirs or (DEFAULT_DATA_DIR, REPO_ROOT)
            cls._review = ReviewService(cls.store, cls.reload_dataset, dirs[0], dirs[1], cls.curation_log_dir)
        return cls._review


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _wrap(data: Any, **extra: Any) -> dict[str, Any]:
    return {"data": data, "dataset_version": Services.store().dataset_version, **extra}


# ------------------------------------------------------------------ catálogo
@router.get("/documents")
def list_documents() -> dict:
    return _wrap(Services.catalog().documents())


@router.get("/documents/{document_id}")
def get_document(document_id: str) -> dict:
    try:
        doc = Services.catalog().document(workspace.safe_id(document_id))
    except workspace.InvalidId:
        raise _err(422, "INVALID_ID", "Identificador inválido.") from None
    if doc is None:
        raise _err(404, "DOCUMENT_NOT_FOUND", "Documento não encontrado.")
    return _wrap(doc)


@router.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: str) -> dict:
    try:
        exp = Services.catalog().experiment(workspace.safe_id(experiment_id))
    except workspace.InvalidId:
        raise _err(422, "INVALID_ID", "Identificador inválido.") from None
    if exp is None:
        raise _err(404, "EXPERIMENT_NOT_FOUND", "Experimento não encontrado.")
    return _wrap(exp)


@router.get("/experiments/{experiment_id}/compatibility")
def get_compatibility(experiment_id: str) -> dict:
    try:
        result = Services.sim().compatibility(workspace.safe_id(experiment_id))
    except workspace.InvalidId:
        raise _err(422, "INVALID_ID", "Identificador inválido.") from None
    if result is None:
        raise _err(404, "EXPERIMENT_NOT_FOUND", "Experimento não encontrado.")
    return _wrap(result)


# ------------------------------------------------------------------ importação
@router.post("/imports", status_code=202)
def create_import(file: UploadFile = File(...)) -> dict:
    try:
        record = Services.imports().create(file.filename or "arquivo.pdf", file.file)
    except PdfRejected as exc:
        raise _err(422, exc.code, exc.message_pt) from None
    return _wrap(record)


@router.get("/imports")
def list_imports() -> dict:
    return _wrap(Services.imports().list())


@router.get("/imports/{import_id}")
def get_import(import_id: str) -> dict:
    try:
        rec = Services.imports().get(import_id)
    except workspace.InvalidId:
        raise _err(422, "INVALID_ID", "Identificador inválido.") from None
    if rec is None:
        raise _err(404, "IMPORT_NOT_FOUND", "Importação não encontrada.")
    return _wrap(rec)


# ------------------------------------------------------------------ enriquecimento
@router.get("/documents/{document_id}/enrichment")
def get_enrichment(document_id: str) -> dict:
    try:
        document_id = workspace.safe_id(document_id)
    except workspace.InvalidId:
        raise _err(422, "INVALID_ID", "Identificador inválido.") from None
    saved = workspace.read_json(workspace.area("enrichment") / f"{document_id}.json")
    if saved is None:
        raise _err(404, "ENRICHMENT_NOT_RUN", "O enriquecimento ainda não foi executado para este documento.")
    return _wrap(saved)


@router.post("/documents/{document_id}/enrichment")
def run_enrichment(document_id: str) -> dict:
    """Opcional e repetível. Falhas de fonte viram avisos; a resposta é sempre 200."""
    try:
        document_id = workspace.safe_id(document_id)
    except workspace.InvalidId:
        raise _err(422, "INVALID_ID", "Identificador inválido.") from None
    catalog = Services.catalog()
    meta = catalog.document_meta(document_id)
    if meta is None:
        raise _err(404, "DOCUMENT_NOT_FOUND", "Documento não encontrado.")
    report = EnrichmentService(Services.transport()).enrich(meta, catalog.flat_parameters(document_id))
    data = report.model_dump(mode="json")
    workspace.write_json(workspace.area("enrichment") / f"{document_id}.json", data)
    return _wrap(data)


@router.get("/documents/{document_id}/file")
def get_document_file(document_id: str):
    """PDF local, para conferência humana. O caminho é decidido pelo servidor."""
    try:
        path = Services.catalog().local_file(workspace.safe_id(document_id))
    except workspace.InvalidId:
        raise _err(422, "INVALID_ID", "Identificador inválido.") from None
    if path is None:
        raise _err(404, "FILE_NOT_AVAILABLE", "O arquivo não está disponível nesta instalação.")
    return FileResponse(path, media_type="application/pdf", filename="documento.pdf",
                        headers={"Content-Disposition": "inline; filename=documento.pdf"})


@router.get("/documents/{document_id}/analysis")
def get_analysis(document_id: str) -> dict:
    """Resumo consolidado: procedência × revisão × enriquecimento, cobertura de leitura e prontidão FDS."""
    try:
        data = build_analysis(Services.catalog(), workspace.safe_id(document_id),
                              lambda eid: Services.sim().compatibility(eid))
    except workspace.InvalidId:
        raise _err(422, "INVALID_ID", "Identificador inválido.") from None
    if data is None:
        raise _err(404, "DOCUMENT_NOT_FOUND", "Documento não encontrado.")
    return _wrap(data)


# ------------------------------------------------------------------ revisão humana
class ReviewRequest(BaseModel):
    action: Literal["CONFIRM", "DOUBT", "DIVERGENCE"]
    reviewer: str = Field(max_length=80)
    observed_value: str | None = Field(default=None, max_length=120)
    observed_unit: str | None = Field(default=None, max_length=30)
    observed_page_pdf: int | None = Field(default=None, ge=1, le=100000)
    notes: str | None = Field(default=None, max_length=1000)
    checked_pdf: bool = False


@router.post("/records/{record_id}/review")
def review_record(record_id: str, req: ReviewRequest) -> dict:
    """Mesma política do `scripts/review_record.py`. A identidade do revisor é declarada, não autenticada."""
    try:
        result = Services.review().submit(record_id, req.action, req.reviewer, req.observed_value,
                                          req.observed_unit, req.observed_page_pdf, req.notes, req.checked_pdf)
    except workspace.InvalidId:
        raise _err(422, "INVALID_ID", "Identificador inválido.") from None
    except ReviewRejected as exc:
        raise _err(404 if exc.code == "RECORD_NOT_FOUND" else 422, exc.code, str(exc)) from None
    return _wrap(result)


@router.get("/records/{record_id}/events")
def record_events(record_id: str) -> dict:
    try:
        return _wrap(events_for(workspace.safe_id(record_id)))
    except workspace.InvalidId:
        raise _err(422, "INVALID_ID", "Identificador inválido.") from None


# ------------------------------------------------------------------ simulação
class ExperimentChange(BaseModel):
    parameter: str = Field(max_length=80)
    value: float


class ExperimentScenarioRequest(BaseModel):
    changes: list[ExperimentChange] = Field(min_length=1, max_length=20)
    title: str | None = Field(default=None, max_length=80)
    hypothesis: str | None = Field(default=None, max_length=500)


@router.post("/experiments/{experiment_id}/scenarios", status_code=201)
def create_experiment_scenario(experiment_id: str, req: ExperimentScenarioRequest) -> dict:
    """Cenário derivado de HIPÓTESE sobre as condições do experimento. O original não é alterado."""
    try:
        sc = Services.sim().create_experiment_scenario(
            workspace.safe_id(experiment_id), [c.model_dump() for c in req.changes], req.title, req.hypothesis)
    except workspace.InvalidId:
        raise _err(422, "INVALID_ID", "Identificador inválido.") from None
    except CaseValidationError as exc:
        raise _err(422, "SCENARIO_INVALID", "; ".join(exc.errors)) from None
    except KeyError:
        raise _err(404, "EXPERIMENT_NOT_FOUND", "Experimento não encontrado.") from None
    return _wrap(sc.model_dump(mode="json"))


class ScenarioRequest(BaseModel):
    model_id: str = Field(max_length=80)
    values: dict[str, float] = Field(default_factory=dict)
    title: str | None = Field(default=None, max_length=80)
    experiment_id: str | None = Field(default=None, max_length=96)


class RunRequest(BaseModel):
    scenario_id: str = Field(max_length=40)


@router.get("/simulation/status")
def simulation_status() -> dict:
    return _wrap(Services.sim().status())


@router.get("/simulation/models")
def simulation_models() -> dict:
    return _wrap(Services.sim().models())


@router.post("/scenarios", status_code=201)
def create_scenario(req: ScenarioRequest) -> dict:
    try:
        sc = Services.sim().create_scenario(req.model_id, req.values, req.title, req.experiment_id)
    except CaseValidationError as exc:
        raise _err(422, "SCENARIO_INVALID", "; ".join(exc.errors)) from None
    except KeyError as exc:
        raise _err(404, str(exc.args[0]), "Modelo ou experimento não encontrado.") from None
    return _wrap(sc.model_dump(mode="json"))


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str) -> dict:
    try:
        sc = Services.sim().get_scenario(scenario_id)
    except workspace.InvalidId:
        raise _err(422, "INVALID_ID", "Identificador inválido.") from None
    if sc is None:
        raise _err(404, "SCENARIO_NOT_FOUND", "Cenário não encontrado.")
    return _wrap(sc)


@router.post("/simulations", status_code=202)
def submit_simulation(req: RunRequest) -> dict:
    """Enfileira um cenário APROVADO. O servidor gera o .fds; o cliente nunca envia FDS."""
    try:
        run = Services.sim().submit(workspace.safe_id(req.scenario_id))
    except workspace.InvalidId:
        raise _err(422, "INVALID_ID", "Identificador inválido.") from None
    except KeyError:
        raise _err(404, "SCENARIO_NOT_FOUND", "Cenário não encontrado.") from None
    return _wrap(run.model_dump(mode="json"))


@router.get("/simulations")
def list_simulations() -> dict:
    return _wrap(Services.sim().list_runs())


@router.get("/simulations/{run_id}")
def get_simulation(run_id: str) -> dict:
    try:
        run = Services.sim().get_run(run_id)
    except workspace.InvalidId:
        raise _err(422, "INVALID_ID", "Identificador inválido.") from None
    if run is None:
        raise _err(404, "RUN_NOT_FOUND", "Execução não encontrada.")
    return _wrap(run)


_MEDIA = {".mp4": "video/mp4", ".png": "image/png", ".csv": "text/csv", ".fds": "text/plain", ".log": "text/plain",
          ".ssf": "text/plain"}


@router.get("/simulations/{run_id}/artifacts/{name}")
def get_artifact(run_id: str, name: str):
    try:
        path = Services.sim().artifact_path(workspace.safe_id(run_id), name)
    except workspace.InvalidId:
        raise _err(422, "INVALID_ID", "Identificador inválido.") from None
    if path is None:
        raise _err(404, "ARTIFACT_NOT_FOUND", "Artefato não encontrado.")
    return FileResponse(path, media_type=_MEDIA.get(Path(name).suffix, "application/octet-stream"))
