"""BL-17: profile-scoped proposals, resumable navigation and a verified audit chain.

This store never writes to the catalog. Accepted evidence is still not an executable
input: only an implemented, approved profile with a dimensional contract may use it.
"""
from __future__ import annotations

from typing import Literal
from pydantic import Field

from backend.app import units, workspace
from backend.app.nasa.provenance.log import utc_now
from backend.app.simulation import bridge
from backend.app.simulation.registry import FDS_PHENOMENA

STATES = ("OPEN", "IN_PROGRESS", "SOURCE_SUBMITTED", "ASSUMPTION_PROPOSED", "UNDER_REVIEW", "RESOLVED_FOR_PROFILE", "BLOCKED")
ORDER = ["sample_length", "sample_holder_substrate", "duct_geometry", "ambient_pressure", "ambient_temperature",
         "inlet_flow_profile", "anemometer_location", "ignition_procedure", "pmma_pyrolysis_properties",
         "o2_time_profile", "measurement_uncertainty", "flame_front_tracking_method"]
WHY = {
    "sample_length": "Define a extensão do sólido e o espaço disponível para a chama se propagar.",
    "sample_holder_substrate": "O suporte troca calor com a amostra e altera seu aquecimento e a propagação da chama.",
    "duct_geometry": "Define o domínio e as paredes que condicionam o escoamento ao redor da amostra.",
    "ambient_pressure": "A pressão participa da densidade do gás e das condições de combustão.",
    "ambient_temperature": "Define o estado térmico inicial do gás e da amostra.",
    "inlet_flow_profile": "Uma velocidade pontual não descreve como o ar entra em todo o duto ao longo do tempo.",
    "anemometer_location": "Permite interpretar onde a velocidade publicada foi medida e avaliar a fidelidade do contorno.",
    "ignition_procedure": "A fonte e a duração de ignição determinam como o aquecimento e a chama começam.",
    "pmma_pyrolysis_properties": "O FDS precisa de um modelo de degradação térmica e propriedades consistentes do material.",
    "o2_time_profile": "Descreve a disponibilidade de oxigênio ao longo do ensaio; os valores inicial e final são apenas extremos.",
    "measurement_uncertainty": "Permite avaliar se a diferença entre resultado calculado e medição é significativa.",
    "flame_front_tracking_method": "Define como extrair do cálculo e do vídeo uma medida de avanço comparável.",
}
RELATED = {
    "sample_length": ["width", "thickness", "material"], "duct_geometry": ["width", "thickness", "airflow_velocity"],
    "inlet_flow_profile": ["airflow_velocity"], "anemometer_location": ["airflow_velocity"],
    "o2_time_profile": ["o2_initial", "o2_final"], "pmma_pyrolysis_properties": ["material", "thickness"],
    "sample_holder_substrate": ["material", "thickness"], "ignition_procedure": ["material", "flame_spread_rate"],
    "measurement_uncertainty": ["flame_spread_rate", "airflow_velocity", "o2_initial"],
    "flame_front_tracking_method": ["flame_spread_rate"],
}
SCALARS = {"sample_length": "m", "ambient_pressure": "Pa", "ambient_temperature": "K"}
MODEL_MESSAGE = "Os dados podem ser preparados, mas este modelo ainda não pode ser executado. É necessária a implementação e aprovação do perfil físico."


class Proposal(bridge.Strict):
    value: float | None = Field(default=None, strict=True)
    unit: str = Field(min_length=1, max_length=32)
    details: str = Field(default="", max_length=6000)
    source: str = Field(min_length=10, max_length=1000)
    location: str = Field(min_length=2, max_length=300)
    evidence: str = Field(min_length=10, max_length=6000)
    author: str = Field(min_length=2, max_length=100)
    justification: str = Field(default="", max_length=2000)
    limitations: str = Field(default="", max_length=2000)


class DecisionInput(bridge.Strict):
    expected_revision: int = Field(ge=0)
    action: Literal["DRAFT", "SOURCE", "ASSUMPTION", "NOT_FOUND", "DEFER", "REQUEST_REVIEW", "ACCEPT", "REJECT"]
    author: str = Field(min_length=2, max_length=100)
    notes: str = Field(default="", max_length=2000)
    draft: dict[str, str] | None = None
    proposal: Proposal | None = None
    next_gap_id: str | None = None


class CursorInput(bridge.Strict):
    expected_revision: int = Field(ge=0)
    gap_id: str


def _path(eid, pid):
    return workspace.area("guided_reviews") / workspace.safe_id(eid) / f"{workspace.safe_id(pid)}.json"


def _load(eid, pid):
    path = _path(eid, pid)
    if not path.exists():
        return {"events": []}
    log = workspace.read_json(path)
    if not isinstance(log, dict) or not isinstance(log.get("events"), list):
        raise ValueError("Histórico de revisão ilegível; restaure uma cópia íntegra.")
    prev = None
    for i, event in enumerate(log["events"], 1):
        body = {k: v for k, v in event.items() if k != "sha256"}
        if event.get("revision") != i or event.get("previous_sha256") != prev or bridge.digest(body) != event.get("sha256"):
            raise ValueError("A integridade do histórico de revisão não pôde ser confirmada.")
        if event.get("case_id"):
            try:
                case = bridge.load(event["case_id"], event["case_version"])
            except (ValueError, KeyError):
                raise ValueError("A versão do caso vinculada ao histórico não está íntegra.") from None
            snapshot = case["content"].get("guided_review", {}).get("decision")
            captured = {k: v for k, v in event.items() if k not in {"case_id", "case_version", "case_sha256", "revision", "at", "previous_sha256", "sha256"}}
            if case["content_sha256"] != event.get("case_sha256") or snapshot != captured:
                raise ValueError("O vínculo entre decisão e versão do caso foi alterado.")
        prev = event["sha256"]
    return log


def _profile(exp, pid):
    profile = next((p for p in bridge.profiles() if p["model_id"] == pid), None)
    if profile is None or profile["independent_only"]:
        raise ValueError("Escolha um perfil físico do experimento. O caso de propano é independente dos dados NASA.")
    return profile


def _supported(exp, profile):
    return bool(set(exp.get("phenomena", [])) & set(profile["phenomena"]) & FDS_PHENOMENA)


def _latest(log, gid):
    return next((e for e in reversed(log["events"]) if e.get("gap_id") == gid and e["action"] != "NAVIGATE"), None)


def _append(log, eid, pid, event):
    event.update(revision=len(log["events"]) + 1, at=utc_now(), previous_sha256=log["events"][-1]["sha256"] if log["events"] else None)
    event["sha256"] = bridge.digest(event)
    log["events"].append(event)
    workspace.write_json(_path(eid, pid), log)


def _scalar_value(parameter, proposal, exp):
    target = SCALARS.get(parameter)
    if not target:
        if proposal.value is not None or proposal.unit != "n/a" or len(proposal.details) < 10:
            raise ValueError("Este parâmetro exige documentação estruturada, sem valor escalar; descreva o método, geometria ou propriedades e use unidade n/a.")
        return {"kind": "DOCUMENT", "details": proposal.details, "physical_validation": "REQUIRES_SPECIALIST_SCHEMA"}
    if proposal.value is None:
        raise ValueError("Informe um valor numérico e sua unidade.")
    q = units.normalize(proposal.value, proposal.unit)
    expected = units.normalize(1, target)
    if q is None or q.dimension != expected.dimension:
        raise ValueError("A unidade não corresponde à grandeza solicitada.")
    if q.value <= 0:
        raise ValueError("O valor deve ser fisicamente positivo (temperaturas acima do zero absoluto).")
    # A submitted length cannot be shorter than the documented sample thickness.
    if parameter == "sample_length":
        for p in exp["parameters"]:
            o = p.get("original") or {}
            if p["parameter"] == "thickness" and isinstance(o.get("value"), (int, float)):
                thickness = units.normalize(o["value"], o.get("unit"))
                if thickness and thickness.dimension == "length" and q.value <= thickness.value:
                    raise ValueError("O comprimento deve exceder a espessura documentada da amostra; confirme a dimensão e a fonte.")
    return {"kind": "SCALAR", "value": q.value, "unit": q.unit, "dimension": q.dimension, "physical_validation": "BASIC_DOMAIN_ONLY"}


def _eligible(event, profile, exp):
    """No resolution without a reviewed, version-matched, executable profile contract."""
    if not event or event.get("review_state") != "ACCEPTED" or not profile["approved"] or not profile["implemented"]:
        return False
    if event.get("profile_sha256") != bridge.digest(profile) or event.get("normalized", {}).get("kind") != "SCALAR":
        return False
    if event.get("catalog_sha256") != bridge.digest(exp):
        return False
    spec = next((p for p in profile.get("parameters", []) if p["name"] == event["parameter"]), None)
    if not spec or (event["proposal_kind"] == "ASSUMPTION" and not spec.get("assumption_allowed")):
        return False
    q = event["normalized"]
    expected, zero = units.normalize(1, spec["unit"]), units.normalize(0, spec["unit"])
    if not expected or q["dimension"] != expected.dimension:
        return False
    value = (q["value"] - zero.value) / (expected.value - zero.value)
    return spec["min"] <= value <= spec["max"]


@bridge.serialized
def view(exp, pid):
    profile = _profile(exp, pid)
    log = _load(exp["experiment_id"], pid)
    resolved = bridge.resolve(exp)
    gaps = sorted(resolved["gaps"], key=lambda g: (ORDER.index(g["parameter"]) if g["parameter"] in ORDER else len(ORDER), g["parameter"], g["gap_id"]))
    requirements = {r["parameter"]: r for r in profile.get("requirements", [])} if _supported(exp, profile) else {}
    tasks = []
    for g in gaps:
        current = _latest(log, g["gap_id"])
        state = current["state"] if current else "OPEN"
        if state == "RESOLVED_FOR_PROFILE" and not _eligible(current, profile, exp):
            state = "UNDER_REVIEW"
        req = requirements.get(g["parameter"])
        comparison = "QUANTITATIVE_COMPARISON" in g.get("categories", [])
        impact = "Impede comparação quantitativa; não é uma entrada de execução." if comparison else "Bloqueia a construção do modelo físico." if req else "Limita a fidelidade ao ensaio; não é requisito de construção deste perfil."
        allowed = bool(req and req.get("assumption_allowed") and g["parameter"] in SCALARS and _supported(exp, profile))
        tasks.append({**g, "why_pt": WHY.get(g["parameter"], "Permite avaliar se a descrição científica atende aos requisitos do perfil selecionado."),
                      "impact_pt": impact, "required": bool(req), "state": state, "current": current,
                      "assumption_allowed": allowed,
                      "assumption_reason_pt": "Pode ser proposta para avaliação exploratória; o perfil PMMA permanece sem aprovação para uso." if allowed else "Este perfil não permite usar uma hipótese neste campo: falta contrato físico validado ou a física não é suportada. Registre evidência científica ou adie.",
                      "schema": {"kind": "SCALAR" if g["parameter"] in SCALARS else "DOCUMENT", "unit": SCALARS.get(g["parameter"], "n/a")},
                      "known": [p for p in exp["parameters"] if p["parameter"] in RELATED.get(g["parameter"], [])],
                      "history": [e for e in log["events"] if e.get("gap_id") == g["gap_id"] and e["action"] != "NAVIGATE"]})
    conditions = {p["parameter"] for p in resolved["conditions"]}
    satisfied = [r for r in requirements if r in conditions or any(t["parameter"] == r and t["state"] == "RESOLVED_FOR_PROFILE" for t in tasks)]
    pending = [r for r in requirements if r not in satisfied]
    cursor = next((e.get("cursor") for e in reversed(log["events"]) if e.get("cursor")), None)
    if cursor not in {t["gap_id"] for t in tasks}:
        cursor = None
    return {"experiment_id": exp["experiment_id"], "title": exp["label"], "profile": profile, "revision": len(log["events"]),
            "tasks": tasks, "cursor": cursor or (tasks[0]["gap_id"] if tasks else None),
            "recorded": sum(t["current"] is not None for t in tasks), "resolved": sum(t["state"] == "RESOLVED_FOR_PROFILE" for t in tasks),
            "readiness": {"supported": _supported(exp, profile), "generator_approved": profile["approved"] and profile["implemented"],
                          "satisfied": satisfied, "pending": pending, "additional": profile.get("additional_requirements", []),
                          "can_execute": False, "message_pt": MODEL_MESSAGE if _supported(exp, profile) else "A física deste experimento não é suportada por este perfil FDS. A revisão documental continua disponível."},
            "history": log["events"]}


@bridge.serialized
def navigate(exp, pid, req: CursorInput):
    data = view(exp, pid)
    if req.expected_revision != data["revision"]:
        raise ValueError("A revisão mudou em outra janela. Recarregue antes de salvar.")
    if req.gap_id not in {t["gap_id"] for t in data["tasks"]}:
        raise ValueError("Pendência não pertence a este experimento.")
    log = _load(exp["experiment_id"], pid)
    _append(log, exp["experiment_id"], pid, {"action": "NAVIGATE", "cursor": req.gap_id})
    return view(exp, pid)


@bridge.serialized
def decide(exp, pid, gid, req: DecisionInput, catalog):
    data = view(exp, pid)
    task = next((t for t in data["tasks"] if t["gap_id"] == gid), None)
    if not task:
        raise ValueError("Pendência não pertence a este experimento.")
    if req.expected_revision != data["revision"]:
        raise ValueError("A revisão mudou em outra janela. Recarregue antes de salvar.")
    if req.next_gap_id and req.next_gap_id not in {t["gap_id"] for t in data["tasks"]}:
        raise ValueError("Destino de navegação inválido.")
    if req.author.casefold().startswith(("codex", "gemini", "claude", "llm", "ai ", "ia ")):
        raise ValueError("Identifique a pessoa responsável pelo registro.")
    profile = data["profile"]
    old = task["current"] or {}
    event = {"gap_id": gid, "parameter": task["parameter"], "action": req.action, "author": req.author,
             "notes": req.notes, "cursor": req.next_gap_id or gid, "profile_sha256": bridge.digest(profile),
             "profile_version": profile["version"], "profile_id": pid, "catalog_sha256": bridge.digest(exp)}
    if req.action == "DRAFT":
        allowed = {"value", "unit", "source", "location", "evidence", "author", "justification", "limitations", "details", "action", "notes"}
        if not req.draft or set(req.draft) - allowed or any(len(v) > 6000 for v in req.draft.values()):
            raise ValueError("Rascunho inválido.")
        event.update(state="IN_PROGRESS", draft=req.draft, review_state="DRAFT_UNVALIDATED")
    elif req.action in {"SOURCE", "ASSUMPTION"}:
        if req.proposal is None or req.proposal.author.casefold() != req.author.casefold():
            raise ValueError("Informe a proposta e o mesmo responsável pelo registro.")
        norm = _scalar_value(task["parameter"], req.proposal, exp)
        assumption = None
        if req.action == "ASSUMPTION":
            if not task["assumption_allowed"]:
                raise ValueError(task["assumption_reason_pt"])
            a = req.proposal
            assumption = bridge.Assumption(parameter=task["parameter"], value=a.value, unit=a.unit, source=a.source,
                                           source_type="EXTERNAL_LITERATURE", justification=a.justification,
                                           author=a.author, limitations=a.limitations).model_dump()
        event.update(state="SOURCE_SUBMITTED" if req.action == "SOURCE" else "ASSUMPTION_PROPOSED",
                     proposal=req.proposal.model_dump(), normalized=norm, proposal_kind=req.action,
                     assumption=assumption, review_state="PENDING")
    elif req.action in {"NOT_FOUND", "DEFER"}:
        if len(req.notes) < 5:
            raise ValueError("Registre onde procurou ou o motivo do adiamento.")
        event.update(state="BLOCKED" if req.action == "NOT_FOUND" else "OPEN", review_state="NOT_REVIEWED",
                     draft=old.get("draft"), proposal=old.get("proposal"))
    else:
        if req.action == "REQUEST_REVIEW":
            if old.get("state") not in {"SOURCE_SUBMITTED", "ASSUMPTION_PROPOSED"}:
                raise ValueError("Envie uma proposta antes de solicitar revisão.")
        else:
            if old.get("state") != "UNDER_REVIEW" or len(req.notes) < 5:
                raise ValueError("Solicite revisão e registre o parecer antes da decisão independente.")
            if req.author.casefold() == old["proposal"]["author"].casefold():
                raise ValueError("A revisão deve ser feita por outra pessoa, independente do autor.")
        event.update({k: old[k] for k in ("proposal", "normalized", "proposal_kind", "assumption") if k in old})
        event.update(state="UNDER_REVIEW", review_state="ACCEPTED" if req.action == "ACCEPT" else "REJECTED" if req.action == "REJECT" else "PENDING")
        if req.action == "REJECT":
            event["state"] = "IN_PROGRESS"
        elif req.action == "ACCEPT" and _eligible(event, profile, exp) and data["readiness"]["supported"]:
            event["state"] = "RESOLVED_FOR_PROFILE"
    # Immutable BL-16 case version captures the decisions, never inputs to a generator.
    log = _load(exp["experiment_id"], pid)
    previous_case = next((e.get("case_id") for e in reversed(log["events"]) if e.get("case_id")), None)
    snapshot = {"previous_audit_sha256": log["events"][-1]["sha256"] if log["events"] else None,
                "decision": event, "usage": "DOCUMENTATION_ONLY_NOT_GENERATOR_INPUT"}
    case = bridge.create(bridge.CaseInput(profile_id=pid, profile_version=profile["version"], experiment_id=exp["experiment_id"],
                                         title=exp["label"][:80]), catalog, previous_case, review_snapshot=snapshot)
    event.update(case_id=case["content"]["case_id"], case_version=case["content"]["version"], case_sha256=case["content_sha256"])
    _append(log, exp["experiment_id"], pid, event)
    return view(exp, pid)
