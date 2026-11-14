"""API do protótipo v2: catálogo, importação, enriquecimento NASA e simulação.

Os singletons ficam em `Services` para que os testes troquem transporte, IA e executor
sem tocar em rede, no Gemini ou no FDS.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.app import workspace
from backend.app.api.assistant import get_dataset_store
from backend.app.assistant.config import load_settings
from backend.app.assistant.service import build_provider
from backend.app.catalog.service import Catalog
from backend.app.ingest.pdf import PdfRejected
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
    _catalog: Catalog | None = None
    _imports: ImportService | None = None
    _sim: SimulationService | None = None

    @classmethod
    def reset(cls) -> None:
        if cls._sim:
            cls._sim.stop()
        cls._catalog = cls._imports = cls._sim = None

    @classmethod
    def transport(cls) -> Transport:
        if cls.transport_factory:
            return cls.transport_factory()
        mode = os.environ.get("FLAMELAB_NASA_MODE", "online").lower()
        return FixtureTransport(FIXTURE_DIR) if mode == "fixture" else UrllibTransport()

    @classmethod
    def catalog(cls) -> Catalog:
        if cls._catalog is None:
            cls._catalog = Catalog(get_dataset_store())
        return cls._catalog

    @classmethod
    def llm(cls):
        if cls.provider != "unset":
            return cls.provider
        return build_provider(load_settings())

    @classmethod
    def imports(cls) -> ImportService:
        if cls._imports is None:
            cls._imports = ImportService(get_dataset_store(), cls.transport, cls.llm(), run_async=cls.run_async)
        return cls._imports

    @classmethod
    def sim(cls) -> SimulationService:
        if cls._sim is None:
            executor = cls.executor or LocalFdsExecutor()
            cls._sim = SimulationService(executor, cls.catalog())
        return cls._sim


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _wrap(data: Any, **extra: Any) -> dict[str, Any]:
    return {"data": data, "dataset_version": get_dataset_store().dataset_version, **extra}


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


# ------------------------------------------------------------------ simulação
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
