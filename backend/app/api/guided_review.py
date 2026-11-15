"""Additive guided review API. No network lookup, promotion or execution side effects."""
from fastapi import APIRouter, HTTPException
from backend.app.api.platform import Services, _wrap
from backend.app import guided_review as service, workspace
from backend.app.simulation.registry import FLAME_SPREAD

router = APIRouter(prefix="/api/experiments", tags=["guided-review"])


def invoke(eid, pid, fn, *args):
    try:
        exp = Services.catalog().experiment(workspace.safe_id(eid))
        if exp is None:
            raise HTTPException(404, detail="Experimento não encontrado.")
        return _wrap(fn(exp, pid, *args))
    except ValueError as exc:
        raise HTTPException(409 if "outra janela" in str(exc) else 422,
                            detail={"code": "GUIDED_REVIEW_INVALID", "message": str(exc)}) from None


@router.get("/{eid}/guided-review")
def get(eid: str, profile_id: str = FLAME_SPREAD.model_id):
    return invoke(eid, profile_id, service.view)


@router.post("/{eid}/guided-review/cursor")
def cursor(eid: str, req: service.CursorInput, profile_id: str = FLAME_SPREAD.model_id):
    return invoke(eid, profile_id, service.navigate, req)


@router.post("/{eid}/guided-review/{gid}")
def decide(eid: str, gid: str, req: service.DecisionInput, profile_id: str = FLAME_SPREAD.model_id):
    return invoke(eid, profile_id, service.decide, gid, req, Services.catalog())
