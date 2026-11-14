"""BL-05.07 — POST /api/ask.

- Abstenção e indisponibilidade da IA são ESTADOS da resposta (HTTP 200).
- Requisição inválida → 422 com envelope de erro (sem ecoar a entrada).
- A fonte de evidências padrão é vazia até a curadoria BL-02 existir: em execução
  normal o endpoint se abstém, sem inventar dados NASA.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends

from backend.app.assistant.config import load_settings
from backend.app.assistant.retrieval import EmptyEvidenceSource
from backend.app.assistant.schemas import AskRequest
from backend.app.assistant.service import AssistantService, build_provider

router = APIRouter(prefix="/api", tags=["assistant"])


@lru_cache(maxsize=1)
def get_assistant_service() -> AssistantService:
    settings = load_settings()
    return AssistantService(settings=settings, source=EmptyEvidenceSource(), provider=build_provider(settings))


@router.post("/ask")
def ask(req: AskRequest, service: AssistantService = Depends(get_assistant_service)) -> dict:
    answer = service.ask(req)
    return {
        "data": answer.model_dump(mode="json"),
        "dataset_version": answer.dataset_version,
        "warnings": answer.warnings,
    }
