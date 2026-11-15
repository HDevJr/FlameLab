"""BL-16: versioned scientific preparation; never modifies the scientific catalog."""
from __future__ import annotations

import hashlib
import json
import secrets
import threading
from functools import wraps
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app import units, workspace
from backend.app.nasa.provenance.log import utc_now
from backend.app.simulation.case_builder import build_case, validate_values, CaseValidationError
from backend.app.simulation.registry import INTEGRATION, FLAME_SPREAD, FDS_PHENOMENA

VERSION = "1.0.0"


class PreparationState(str, Enum):
    DOCUMENTED = "DOCUMENTED"
    MISSING_INPUTS = "MISSING_INPUTS"
    MODEL_UNSUPPORTED = "MODEL_UNSUPPORTED"
    MODEL_NOT_APPROVED = "MODEL_NOT_APPROVED"
    EXPLORATORY_READY = "EXPLORATORY_READY"
    EXECUTION_READY = "EXECUTION_READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
_lock = threading.RLock()


def serialized(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        with _lock:
            return fn(*args, **kwargs)
    return wrapped
LABEL = "Exploração técnica independente — não é reprodução de experimento NASA"
COMPARISON = {"status": "UNAVAILABLE", "message_pt": "Comparação quantitativa não disponível para este perfil.",
              "method": None, "uncertainties": None, "limitations": [LABEL]}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class Assumption(Strict):
    parameter: str = Field(min_length=1, max_length=80)
    value: float = Field(strict=True)
    unit: str = Field(min_length=1, max_length=32)
    source: str = Field(min_length=3, max_length=1000)
    source_type: Literal["NASA_EXPERIMENT", "NASA_RELATED", "EXTERNAL_LITERATURE", "ENGINEERING_ASSUMPTION", "SOFTWARE_DEFAULT"]
    justification: str = Field(min_length=5, max_length=2000)
    author: str = Field(min_length=2, max_length=100)
    limitations: str = Field(min_length=5, max_length=2000)


class CaseInput(Strict):
    profile_id: str = INTEGRATION.model_id
    profile_version: str = VERSION
    experiment_id: str | None = None
    title: str = Field(default="Exploração independente", min_length=1, max_length=80)
    assumptions: list[Assumption] = Field(default_factory=list, max_length=30)


class ReviewInput(Strict):
    reviewer: str = Field(min_length=2, max_length=100)
    notes: str = Field(min_length=5, max_length=2000)
    accepted_defaults: Literal[True]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def profiles():
    technical = {**INTEGRATION.model_dump(mode="json"), "version": VERSION, "approved": True,
                 "independent_only": True, "surface_type": "PRESCRIBED_HRRPUA", "reaction": "PROPANE",
                 "degradation_model": None, "produced_observables": ["T_ceiling", "T_door_top"],
                 "limitations": [LABEL, "Sem previsão de propagação em PMMA"], "max_cells": 20736,
                 "max_frames": 300, "max_threads": 4, "max_wall_clock_s": 900,
                 "comparison": COMPARISON, "approval_basis": {
                     **INTEGRATION.template_source,
                     "source_sha256": "e64834c1f96f3e4cf26f9a05d2bdcff7a5cd01c7ee92e768240c67c91d3505ba",
                     "controlled_changes": "T_END=5..30 s; fixed DEVC and NFRAMES=10*T_END; server CHID",
                 },
                 "template_constants": {"mesh_ijk": [36,24,24], "domain_m": [0,3.6,0,2.4,0,2.4],
                                        "burner_area_m2":0.16, "fuel":"PROPANE", "gravity":"FDS default earth gravity; not microgravity",
                                        "ambient":"FDS defaults; independent test, not NASA conditions",
                                        "boundaries":"Closed compartment with fixed OPEN door and prescribed burner"}}
    for p in technical["parameters"]:
        if p["name"] == "t_end": p.update(default=5.0, max=30.0)
        p.update(required=True, assumption_allowed=True, domain="INDEPENDENT_ONLY")
    pmma = {**FLAME_SPREAD.model_dump(mode="json"), "version": VERSION, "approved": False,
            "independent_only": False, "surface_type": "SOLID_PYROLYSIS", "reaction": None,
            "degradation_model": None, "comparison": COMPARISON,
            "limitations": ["Modelo físico e material PMMA não aprovados; nenhuma execução autorizada"],
            "additional_requirements": ["gravity_vector", "mesh_convergence", "reaction_model", "material_model_review"]}
    input_units = {"material": None, "thickness":"m", "width":"m", "sample_length":"m", "airflow_velocity":"m/s",
                   "o2_initial":"fraction", "ambient_pressure":"Pa", "ambient_temperature":"K",
                   "duct_geometry":"m", "inlet_flow_profile":"m/s", "sample_holder_substrate":None,
                   "ignition_procedure":None, "pmma_pyrolysis_properties":None}
    pmma["requirements"] = [{"parameter":name, "unit":unit, "required":True,
                             "assumption_allowed": name != "pmma_pyrolysis_properties",
                             "domain":"Requires solid-fuel model review; not executable"} for name,unit in input_units.items()]
    return [technical, pmma]


def resolve(exp):
    conditions, ambiguous, observables = [], [], []
    for p in exp["parameters"]:
        if p["role"] == "OBSERVAVEL": observables.append(p); continue
        valid = (p["nature"] == "OBSERVADO" and p.get("original") is not None and bool(p.get("evidence"))
                 and p["status"] in ("CONFERIDO_FONTE", "APROVADO_MODELO") and p.get("review_scope") == "FULL"
                 and (p.get("integrity") or {}).get("status") != "INCONSISTENT"
                 and not any(f["severity"] == "BLOCKING" for f in p.get("semantic_flags", [])))
        (conditions if valid else ambiguous).append(p)
    construction = {"sample_length", "duct_geometry", "sample_holder_substrate", "ambient_pressure", "ambient_temperature",
                    "inlet_flow_profile", "ignition_procedure", "pmma_pyrolysis_properties"}
    gaps = []
    for gap in exp.get("gaps", []):
        categories = ["FIDELITY"]
        if gap["parameter"] in construction: categories += ["CONSTRUCTION", "ASSUMPTION_REQUIRED"]
        if "QUANTITATIVE_COMPARISON" in gap.get("purpose_blocked", []): categories += ["QUANTITATIVE_COMPARISON"]
        gaps.append({**gap, "categories": categories, "required": gap["parameter"] in construction,
                     "assumption_allowed": gap["parameter"] not in {"pmma_pyrolysis_properties"},
                     "impact_pt": "Assumir este valor altera a fidelidade ao ensaio; não fecha a lacuna publicada."})
    supported = bool(set(exp.get("phenomena", [])) & FDS_PHENOMENA)
    names = {p["parameter"] for p in conditions}
    missing = [r["parameter"] for r in profiles()[1]["requirements"] if r["parameter"] not in names]
    return {"experiment_id": exp["experiment_id"], "state": "MODEL_NOT_APPROVED" if supported else "MODEL_UNSUPPORTED", "conditions": conditions,
            "missing_inputs": missing, "input_state": "MISSING_INPUTS" if missing else "DOCUMENTED",
            "ambiguous": ambiguous, "observables": observables, "gaps": gaps,
            "profile_id": FLAME_SPREAD.model_id, "profile_version": VERSION,
            "aliases": {"material_pyrolysis_properties": "pmma_pyrolysis_properties"},
            "blockers": ["Perfil PMMA sem gerador físico aprovado", "Propriedades de pirólise e domínio sem revisão"] if supported else ["Fenômeno sem perfil FDS compatível"],
            "comparison": COMPARISON, "reproduction_ready": False}


def _path(cid, version):
    if not isinstance(version, int) or version < 1: raise ValueError("VERSION_INVALID")
    return workspace.area("cases") / workspace.safe_id(cid) / f"v{version}.json"


def load(cid, version=1):
    data = workspace.read_json(_path(cid, version))
    if data is None: raise KeyError("CASE_NOT_FOUND")
    content = data["content"]
    if digest(content) != data["content_sha256"]: raise ValueError("CASE_HASH_MISMATCH")
    return data


@serialized
def create(req: CaseInput, catalog, cid=None, review_snapshot=None):
    if req.profile_version != VERSION: raise ValueError("PROFILE_VERSION_UNSUPPORTED")
    if req.profile_id not in {INTEGRATION.model_id, FLAME_SPREAD.model_id}: raise ValueError("MODEL_UNSUPPORTED")
    if req.experiment_id and catalog.experiment(req.experiment_id) is None: raise KeyError("EXPERIMENT_NOT_FOUND")
    if req.profile_id == INTEGRATION.model_id and req.experiment_id: raise ValueError("INDEPENDENT_PROFILE_ONLY")
    if cid:
        original = load(cid, 1)["content"]
        if original["experiment_id"] != req.experiment_id: raise ValueError("CASE_LINEAGE_MISMATCH")
    cid = workspace.safe_id(cid) if cid else "CASE-" + secrets.token_hex(6)
    folder = _path(cid, 1).parent
    version = max([int(p.stem[1:]) for p in folder.glob("v*.json") if p.stem[1:].isdigit()] or [0]) + 1
    entries = [a.model_dump() for a in req.assumptions]
    if len({a["parameter"] for a in entries}) != len(entries): raise ValueError("DUPLICATE_INPUT")
    if req.profile_id == INTEGRATION.model_id:
        specs = {p["name"]: p for p in profiles()[0]["parameters"]}
        values = {}
        for a in entries:
            if a["parameter"] not in specs: raise ValueError("INPUT_NOT_ALLOWED")
            if a["source_type"] not in {"ENGINEERING_ASSUMPTION", "EXTERNAL_LITERATURE"}: raise ValueError("INDEPENDENT_SOURCE_ONLY")
            spec = specs[a["parameter"]]
            # kg/kg is a mass ratio; keep it dimensionless without changing scientific units globally.
            source_unit = "adimensional" if a["unit"] == "kg/kg" else a["unit"]
            target_unit = "adimensional" if spec["unit"] == "kg/kg" else spec["unit"]
            q, target = units.normalize(a["value"], source_unit), units.normalize(1, target_unit)
            if q is None or target is None or q.dimension != target.dimension: raise ValueError("UNIT_INCOMPATIBLE")
            zero = units.normalize(0, target_unit)
            a["original_value"], a["original_unit"] = a["value"], a["unit"]
            a["value"] = (q.value-zero.value)/(target.value-zero.value)
            a["unit"] = spec["unit"]
            values[a["parameter"]] = a["value"]
        for name, spec in specs.items():
            if name not in values:
                values[name] = spec["default"]
                entries.append({"parameter": name, "value": spec["default"], "unit": spec["unit"],
                                "source": f"FlameLab controlled profile {req.profile_id}@{VERSION}; {INTEGRATION.template_source['origin']}",
                                "source_type": "SOFTWARE_DEFAULT", "justification": "Default do perfil técnico, aceitação explícita necessária",
                                "author": "FlameLab profile maintainers", "limitations": LABEL})
        validate_values(INTEGRATION, values)
        if not 5 <= values["t_end"] <= 30: raise ValueError("RESOURCE_LIMIT")
    else:
        values = {}
        if entries: raise ValueError("PMMA_PROFILE_NOT_APPROVED")
    for a in entries: a.update(version=version, variant_id=cid, applies_to=a["parameter"], created_at=utc_now(), review_state="PENDING")
    content = {**req.model_dump(exclude={"assumptions"}), "case_id": cid, "version": version, "values": values, "assumptions": entries,
               "resolved": resolve(catalog.experiment(req.experiment_id)) if req.experiment_id else None,
               "profile_sha256": digest(next(p for p in profiles() if p["model_id"] == req.profile_id)),
               "label_pt": LABEL if not req.experiment_id else "Experimento documentado — execução bloqueada", "comparison": COMPARISON}
    if review_snapshot is not None:
        content["guided_review"] = review_snapshot
    record = {"content": content, "content_sha256": digest(content), "created_at": utc_now()}
    workspace.write_json(_path(cid, version), record)
    return record


@serialized
def review(cid, version, req: ReviewInput):
    case = load(cid, version)
    reviewer = req.reviewer.strip()
    if reviewer.lower().startswith(("claude", "gemini", "codex", "llm", "ai ")): raise ValueError("HUMAN_REVIEW_REQUIRED")
    if any(a["author"].strip().casefold() == reviewer.casefold() for a in case["content"]["assumptions"]): raise ValueError("INDEPENDENT_REVIEW_REQUIRED")
    approval = {**req.model_dump(), "reviewer": reviewer, "at": utc_now(), "content_sha256": case["content_sha256"]}
    path = _path(cid, version).with_suffix(".review.json")
    if path.exists(): raise ValueError("ALREADY_REVIEWED")
    workspace.write_json(path, approval)
    return approval


def validate(cid, version, available=True):
    case = load(cid, version); c = case["content"]
    profile = next((p for p in profiles() if p["model_id"] == c["profile_id"] and p["version"] == c["profile_version"]), None)
    blockers = []
    state = "EXPLORATORY_READY"
    if profile is None or digest(profile) != c["profile_sha256"]: blockers += ["PROFILE_CHANGED"]; state = "MODEL_NOT_APPROVED"
    elif not profile["approved"]: blockers += ["MODEL_NOT_APPROVED"]; state = "MODEL_NOT_APPROVED"
    if c["experiment_id"]: blockers += ["EXPERIMENT_PROFILE_NOT_EXECUTABLE"]; state = "MODEL_NOT_APPROVED"
    approval = workspace.read_json(_path(cid, version).with_suffix(".review.json"))
    if not approval or approval["content_sha256"] != case["content_sha256"]: blockers += ["INDEPENDENT_REVIEW_REQUIRED"]
    if not available: blockers += ["EXECUTOR_UNAVAILABLE"]
    if not blockers: state = "EXECUTION_READY"
    return {"state": state, "blockers": blockers, "reproduction_ready": False, "case": case, "approval": approval}


def build(cid, version):
    result = validate(cid, version)
    if result["blockers"]: raise ValueError("; ".join(result["blockers"]))
    case = result["case"]; c = case["content"]
    computational_id = digest({"profile_sha256": c["profile_sha256"], "values": c["values"]})[:24]
    text, sha = build_case(INTEGRATION, c["values"], "case_" + computational_id)
    manifest = {**case, "approval": result["approval"], "fds_sha256": sha,
                "profile": profiles()[0], "computational_id": computational_id,
                "scientific_validity": "NOT_VALIDATED", "comparison": COMPARISON}
    return text, sha, manifest
