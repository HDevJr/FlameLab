"""Additive BL-16 API; reuse existing worker."""
from fastapi import APIRouter, HTTPException
from backend.app.api.platform import Services, _wrap
from backend.app.simulation import bridge
from backend.app import workspace

router = APIRouter(prefix="/api", tags=["scientific-cases"])


def invoke(fn, *args):
    try: return _wrap(fn(*args))
    except KeyError as exc: raise HTTPException(404, detail={"code": str(exc.args[0]), "message": "Caso ou experimento não encontrado"}) from None
    except ValueError as exc: raise HTTPException(422, detail={"code": "CASE_INVALID", "message": str(exc)}) from None


@router.get("/simulation/profiles")
def profiles(): return _wrap(bridge.profiles())


@router.get("/experiments/{eid}/simulation-preparation")
def preparation(eid: str):
    exp = Services.catalog().experiment(eid)
    if exp is None: raise HTTPException(404, "EXPERIMENT_NOT_FOUND")
    from backend.app.guided_review import view
    resolved = bridge.resolve(exp)
    return _wrap({**resolved, "guided_review": view(exp, resolved["profile_id"])})


@router.post("/cases", status_code=201)
def create(req: bridge.CaseInput): return invoke(bridge.create, req, Services.catalog())


@router.get("/cases/{cid}")
def get(cid: str, version: int = 1): return invoke(bridge.validate, cid, version, Services.sim()._executor.available()[0])


@router.post("/cases/{cid}/versions", status_code=201)
def revision(cid: str, req: bridge.CaseInput): return invoke(bridge.create, req, Services.catalog(), cid)


@router.post("/cases/{cid}/review")
def review(cid: str, req: bridge.ReviewInput, version: int = 1): return invoke(bridge.review, cid, version, req)


@router.post("/cases/{cid}/validate")
def validate(cid: str, version: int = 1):
    def compute():
        result = bridge.validate(cid, version, Services.sim()._executor.available()[0])
        if not result["blockers"]:
            text, sha, manifest = bridge.build(cid, version)
            result.update(fds_text=text, fds_sha256=sha, manifest=manifest)
        return result
    return invoke(compute)


def submit_case(cid, version):
    _, _, manifest = bridge.build(cid, version)
    content = manifest["content"]
    scenario = Services.sim().create_scenario(content["profile_id"], content["values"], content["title"])
    data = scenario.model_dump(mode="json")
    data.update(case_id=cid, case_version=version)
    workspace.write_json(Services.sim()._sdir() / f"{scenario.scenario_id}.json", data)
    return Services.sim().submit(scenario.scenario_id)
