"""BL-17 / BL-17.2: profile-scoped proposals, resumable navigation and a verified audit chain.

This store never writes to the catalog. Accepted evidence is still not an executable
input: only an implemented, approved profile with a dimensional contract may use it.

BL-17.2 adds typed data contracts (`gap_contracts`), a deterministic preview of what will be
saved, auditable edits, per-requirement checks that separate missing data, pending review and
missing physical model, and an isolated TEST mode (`workspace.use_mode("TEST")`).
"""
from __future__ import annotations

from typing import Any, Literal
from pydantic import Field

from backend.app import gap_contracts as contracts, units, workspace
from backend.app.nasa.provenance.log import utc_now
from backend.app.simulation import bridge
from backend.app.simulation.registry import FDS_PHENOMENA

STATES = ("OPEN", "IN_PROGRESS", "SOURCE_SUBMITTED", "ASSUMPTION_PROPOSED", "EXPLORATORY_DRAFT", "UNDER_REVIEW",
          "RESOLVED_FOR_PROFILE", "BLOCKED")
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
REQUIREMENT_LABEL = {"material": "Material", "thickness": "Espessura", "width": "Largura", "airflow_velocity": "Velocidade do ar",
                     "o2_initial": "Oxigênio inicial", "gravity_vector": "Vetor de gravidade", "mesh_convergence": "Convergência de malha",
                     "reaction_model": "Modelo de reação", "material_model_review": "Revisão do modelo de material"}
ADDITIONAL_PT = {
    "gravity_vector": "Gravidade/microgravidade e orientação precisam ser definidas no gerador do perfil.",
    "mesh_convergence": "Exige estudo de convergência de malha do caso gerado.",
    "reaction_model": "Exige modelo de reação na fase gasosa revisado.",
    "material_model_review": "Exige revisão por especialista do modelo de material (pirólise).",
}
MODEL_MESSAGE = "Os dados podem ser preparados, mas este modelo ainda não pode ser executado. É necessária a implementação e aprovação do perfil físico."
HYPOTHESIS_ACTIONS = {"ASSUMPTION", "EXPLORATORY_DRAFT"}
PROPOSAL_ACTIONS = {"SOURCE"} | HYPOTHESIS_ACTIONS
TEXT_KEYS = ("details", "source", "location", "evidence", "justification", "limitations")
KIND_TIER = {"SOURCE": "EVIDENCE_SUBMITTED", "ASSUMPTION": "HYPOTHESIS_PROPOSED", "EXPLORATORY_DRAFT": "EXPLORATORY_DRAFT"}
TIER_PT = {"OPEN": "Ainda não tratada", "DRAFT": "Rascunho de formulário (não enviado)", "NOT_FOUND": "Mantida em aberto: não encontrada",
           "CORRECTIONS_REQUESTED": "Correções solicitadas pelo revisor", "TEST_CONTENT": "Registro com conteúdo de teste (não conta)",
           "EVIDENCE_SUBMITTED": "Evidência complementar submetida", "HYPOTHESIS_PROPOSED": "Hipótese computacional proposta",
           "EXPLORATORY_DRAFT": "Rascunho exploratório não aprovado", "REVIEWED": "Revisada por pessoa independente",
           "REQUIREMENT_SATISFIED": "Requisito satisfeito para o perfil", "PUBLISHED_VERIFIED": "Dado publicado e conferido",
           "MISSING": "Sem dado conferido", "MODEL_DEVELOPMENT": "Depende de desenvolvimento do modelo físico"}
EVIDENCE_TIERS = {"EVIDENCE_SUBMITTED", "HYPOTHESIS_PROPOSED", "EXPLORATORY_DRAFT", "REVIEWED", "REQUIREMENT_SATISFIED"}


class Proposal(bridge.Strict):
    value: float | None = Field(default=None, strict=True)
    unit: str = Field(default="n/a", min_length=1, max_length=32)
    details: str = Field(default="", max_length=6000)
    structured: dict[str, Any] | None = None
    basis: Literal["EXTERNAL_LITERATURE", "ENGINEERING_ASSUMPTION"] = "EXTERNAL_LITERATURE"
    source: str = Field(min_length=10, max_length=1000)
    location: str = Field(min_length=2, max_length=300)
    evidence: str = Field(min_length=10, max_length=6000)
    author: str = Field(min_length=2, max_length=100)
    justification: str = Field(default="", max_length=2000)
    limitations: str = Field(default="", max_length=2000)


class DecisionInput(bridge.Strict):
    expected_revision: int = Field(ge=0)
    action: Literal["DRAFT", "SOURCE", "ASSUMPTION", "EXPLORATORY_DRAFT", "NOT_FOUND", "DEFER", "REQUEST_REVIEW", "ACCEPT", "REJECT"]
    author: str = Field(min_length=2, max_length=100)
    notes: str = Field(default="", max_length=2000)
    draft: dict[str, str] | None = None
    proposal: Proposal | None = None
    change_reason: str = Field(default="", max_length=2000)
    next_gap_id: str | None = None


class CursorInput(bridge.Strict):
    expected_revision: int = Field(ge=0)
    gap_id: str


class PreviewInput(bridge.Strict):
    action: Literal["SOURCE", "ASSUMPTION", "EXPLORATORY_DRAFT"]
    proposal: dict[str, Any] = Field(default_factory=dict)
    change_reason: str = Field(default="", max_length=2000)


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


def _published(exp):
    """SI quantities of numeric published values (read-only)."""
    out = {}
    for p in exp.get("parameters", []):
        o = p.get("original") or {}
        if isinstance(o.get("value"), (int, float)) and not isinstance(o.get("value"), bool):
            q = units.normalize(o["value"], o.get("unit"))
            if q is not None:
                out[p["parameter"]] = q
    return out


def _eligible(event, profile, exp):
    """No resolution without a reviewed, version-matched, executable profile contract."""
    if not event or event.get("mode") == "TEST" or event.get("review_state") != "ACCEPTED" or not profile["approved"] or not profile["implemented"]:
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


# ------------------------------------------------------------------ policy, flags, tiers and checks
def _policy(contract, req, supported, role, profile):
    dev = contract["development_needed_pt"]
    if not supported:
        return {"mode": "NOT_AVAILABLE", "development_needed_pt": dev,
                "reason_pt": "A física deste experimento não é suportada por este perfil FDS; registre evidência documental ou mantenha a pendência em aberto."}
    if contract["kind"] == "DOCUMENT":
        return {"mode": "NOT_AVAILABLE", "development_needed_pt": dev,
                "reason_pt": "Não existe contrato de dados para esta informação, então uma hipótese não pode ser estruturada nem verificada. Registre evidência documental ou mantenha em aberto."}
    if req and req.get("assumption_allowed") and contract["hypothesis"] == "ALLOWED":
        return {"mode": "ALLOWED", "development_needed_pt": dev,
                "reason_pt": "A hipótese será registrada como proposta exploratória sem aprovação, vinculada a este perfil. Só poderá ser entrada FDS após revisão independente e com um perfil físico implementado e aprovado."}
    if req:
        reason = f"O perfil {profile['title_pt']} não permite hipótese nesta informação: ela exige base física revisada."
    elif role == "COMPARISON_ONLY":
        reason = "Esta informação serve apenas para comparação quantitativa e não é entrada FDS."
    else:
        reason = "Esta informação limita a fidelidade ao ensaio e não é requisito de construção do perfil."
    return {"mode": "DRAFT_ONLY", "development_needed_pt": dev,
            "reason_pt": reason + " Você pode salvar um rascunho exploratório explicitamente NÃO APROVADO, que nunca será usado como entrada FDS."}


def _flags(current, contract, duplicates):
    if not current:
        return []
    flags = []
    if current.get("mode") == "TEST":
        flags.append({"code": "TEST_MODE", "severity": "info", "message_pt": "Registro do modo de teste: dado sintético em área isolada; nunca vira dado NASA nem aprovação."})
    else:
        texts = contracts.test_like_texts({"proposal": current.get("proposal"), "draft": current.get("draft")})
        if texts:
            flags.append({"code": "TEST_LIKE_CONTENT", "severity": "warning",
                          "message_pt": f"Texto típico de preenchimento de teste na área científica (ex.: “{texts[0]}”). Não trate este registro como fonte; edite-o com a informação real (o histórico é preservado) ou use o modo de teste."})
    norm = current.get("normalized") or {}
    if norm.get("kind") == "DOCUMENT" and contract["kind"] != "DOCUMENT":
        flags.append({"code": "LEGACY_UNSTRUCTURED", "severity": "warning",
                      "message_pt": "Registro anterior à BL-17.2, em texto livre. Reenvie pelo formulário estruturado para que campos, unidades e consistência sejam verificáveis."})
    dup = duplicates.get(current.get("gap_id"))
    if dup:
        flags.append({"code": "DUPLICATE_ACROSS_GAPS", "severity": "warning",
                      "message_pt": f"O mesmo texto descritivo foi registrado em: {', '.join(dup)}. Confirme se ele descreve esta informação."})
    return flags


def _duplicates(log, tasks_by_gap):
    seen: dict[str, list[str]] = {}
    for g, t in tasks_by_gap.items():
        cur = _latest(log, g)
        details = ((cur or {}).get("proposal") or {}).get("details") or ""
        if len(details.strip()) >= 30:
            seen.setdefault(" ".join(details.split()).casefold(), []).append(g)
    out = {}
    for gaps in seen.values():
        if len(gaps) > 1:
            for g in gaps:
                out[g] = [tasks_by_gap[o]["label_pt"] for o in gaps if o != g]
    return out


def _tier(current, state, flags):
    if not current or state == "OPEN":
        return "OPEN"
    if state == "RESOLVED_FOR_PROFILE":
        return "REQUIREMENT_SATISFIED"
    if state == "BLOCKED":
        return "NOT_FOUND"
    if current.get("review_state") == "REJECTED":
        return "CORRECTIONS_REQUESTED"
    if state == "IN_PROGRESS":
        return "DRAFT"
    if any(f["code"] == "TEST_LIKE_CONTENT" for f in flags):
        return "TEST_CONTENT"
    if current.get("review_state") == "ACCEPTED":
        return "REVIEWED"
    return KIND_TIER.get(current.get("proposal_kind"), "EVIDENCE_SUBMITTED")


def _checks(ctx, current, tier, flags):
    """Ordered verifications: DATA (resolvable here), REVIEW (another person), PHYSICS (model development)."""
    profile, contract, role = ctx["profile"], ctx["contract"], ctx["role"]
    norm = (current or {}).get("normalized") or {}
    has = tier in EVIDENCE_TIERS
    completeness = norm.get("completeness") or {}
    missing = completeness.get("missing_pt") or []
    structured = has and norm.get("kind") in ("SCALAR", "STRUCTURED") and not missing
    if not has:
        detail = {"TEST_CONTENT": "O registro atual parece conteúdo de teste e não conta como informação científica.",
                  "DRAFT": "Há apenas um rascunho de formulário, ainda não enviado.",
                  "NOT_FOUND": "Marcada como não encontrada nas fontes consultadas.",
                  "CORRECTIONS_REQUESTED": "O revisor solicitou correções; reenvie a proposta."}.get(tier, "Nenhuma evidência ou hipótese registrada.")
    else:
        detail = "Registrada."
    if not has:
        sdetail = "Depende do registro da informação."
    elif norm.get("kind") == "DOCUMENT":
        sdetail = "Registro em texto livre: campos e unidades não verificáveis." if contract["kind"] != "DOCUMENT" else "Sem contrato de dados para este parâmetro."
    elif missing:
        sdetail = "Faltam: " + ", ".join(missing) + "."
    else:
        sdetail = "Campos obrigatórios e unidades verificados."
    reviewed = (current or {}).get("review_state") == "ACCEPTED"
    state = (current or {}).get("state")
    checks = [
        {"code": "DATA_PROVIDED", "category": "DATA", "label_pt": "Informação registrada com fonte ou hipótese declarada", "done": has, "detail_pt": detail},
        {"code": "CONTRACT_COMPLETE", "category": "DATA", "label_pt": "Campos do contrato completos e com unidades", "done": structured, "detail_pt": sdetail},
        {"code": "INDEPENDENT_REVIEW", "category": "REVIEW", "label_pt": "Parecer favorável de outra pessoa", "done": reviewed,
         "detail_pt": "Parecer favorável registrado." if reviewed else "Aguardando parecer de outra pessoa." if state == "UNDER_REVIEW" else "Revisão ainda não solicitada."},
    ]
    if (current or {}).get("mode") == "TEST":
        checks.insert(0, {"code": "SCIENTIFIC_RECORD", "category": "DATA", "label_pt": "Registro científico (não é teste)", "done": False,
                          "detail_pt": "Registro do modo de teste: nunca satisfaz requisitos."})
    if role == "CONSTRUCTION_INPUT":
        spec = next((p for p in profile.get("parameters", []) if p["name"] == ctx["parameter"]), None)
        if (current or {}).get("proposal_kind") == "EXPLORATORY_DRAFT":
            checks.append({"code": "HYPOTHESIS_PERMITTED", "category": "PHYSICS", "label_pt": "Perfil permite hipótese neste campo", "done": False,
                           "detail_pt": "Rascunho exploratório não aprovado: o perfil não permite usar hipótese aqui."})
        checks.append({"code": "PROFILE_MAPPING", "category": "PHYSICS", "label_pt": "Perfil define faixa e uso deste campo no FDS",
                       "done": bool(spec) and norm.get("kind") == "SCALAR",
                       "detail_pt": "Definido pelo perfil." if spec else f"O perfil {profile['title_pt']} não define como este campo vira entrada FDS. " + contract["development_needed_pt"][0]})
        approved = profile["approved"] and profile["implemented"]
        checks.append({"code": "GENERATOR_APPROVED", "category": "PHYSICS", "label_pt": "Gerador FDS do perfil implementado e aprovado", "done": approved,
                       "detail_pt": "Gerador aprovado." if approved else "O gerador deste perfil não está implementado nem aprovado; nenhum dado vira entrada FDS."})
    elif role == "COMPARISON_ONLY":
        checks.append({"code": "COMPARISON_PIPELINE", "category": "PHYSICS", "label_pt": "Comparação quantitativa implementada", "done": False,
                       "detail_pt": "Não é entrada FDS. " + contract["development_needed_pt"][0]})
    else:
        checks.append({"code": "FIDELITY_USE", "category": "PHYSICS", "label_pt": "Perfil consome esta informação de fidelidade", "done": False,
                       "detail_pt": "Não é requisito de construção. " + contract["development_needed_pt"][0]})
    return checks


def _next_step(tier, checks, state, contract, flags):
    if tier == "REQUIREMENT_SATISFIED":
        return {"category": "DONE", "text_pt": "Requisito satisfeito para este perfil."}
    if tier == "OPEN":
        return {"category": "DATA", "text_pt": "Escolha um caminho: registrar evidência encontrada, preparar hipótese exploratória ou manter a pendência em aberto."}
    if tier == "DRAFT":
        return {"category": "DATA", "text_pt": "Complete os campos obrigatórios e envie: o rascunho de formulário não é uma submissão."}
    if tier == "CORRECTIONS_REQUESTED":
        return {"category": "DATA", "text_pt": "Edite a proposta conforme o parecer e reenvie, registrando o motivo da alteração."}
    if tier == "NOT_FOUND":
        return {"category": "DATA", "text_pt": "Pendência mantida em aberto sem fonte. Retome quando houver nova referência."}
    if tier == "TEST_CONTENT":
        return {"category": "DATA", "text_pt": "Edite a proposta com a informação científica real (o histórico é preservado) ou refaça o teste no modo de teste."}
    pending = [c for c in checks if not c["done"]]
    first = pending[0] if pending else None
    if first and first["category"] == "DATA":
        if any(f["code"] == "LEGACY_UNSTRUCTURED" for f in flags):
            return {"category": "DATA", "text_pt": "Reenvie esta informação pelo formulário estruturado (editar proposta)."}
        return {"category": "DATA", "text_pt": first["detail_pt"] + " Edite a proposta para completá-la."}
    if first and first["category"] == "REVIEW":
        return {"category": "REVIEW", "text_pt": "Aguardando parecer de outra pessoa, independente do autor." if state == "UNDER_REVIEW"
                else "Solicite revisão: uma segunda pessoa deve conferir fonte, valores e unidades."}
    return {"category": "PHYSICS", "text_pt": "Nada mais a fazer nesta tela. Falta desenvolvimento do modelo físico: " + contract["development_needed_pt"][0]}


def _consequences(ctx, kind, mode, checks, satisfied):
    label, role, profile = ctx["label"], ctx["role"], ctx["profile"]
    saved = {"SOURCE": "Evidência complementar submetida — ainda não revisada.",
             "ASSUMPTION": "Hipótese computacional proposta — sem aprovação.",
             "EXPLORATORY_DRAFT": "Rascunho exploratório NÃO APROVADO — nunca será entrada FDS neste perfil."}.get(kind, "Registro documental.")
    if mode == "TEST":
        saved = "TESTE — dado sintético em armazenamento isolado. " + saved
    if role == "CONSTRUCTION_INPUT":
        req = f"Pode atender ao requisito «{label}» do perfil {profile['title_pt']}, somente após as verificações pendentes."
    elif role == "COMPARISON_ONLY":
        req = "Não é requisito de construção do modelo: serve para comparação quantitativa entre cálculo e ensaio."
    else:
        req = "Não é requisito de construção do modelo: documenta a fidelidade da simulação ao ensaio."
    pending = [c for c in checks if not c["done"]]
    fds = ("Pode ser usado pelo perfil como entrada." if satisfied
           else "Não pode ser usado como entrada FDS agora: " + "; ".join(c["label_pt"][0].lower() + c["label_pt"][1:] + " — pendente" for c in pending) + ".")
    if role != "CONSTRUCTION_INPUT":
        fds = "Não é entrada FDS em nenhum caso; " + fds[0].lower() + fds[1:]
    return {"saved_as_pt": saved, "requirement_pt": req, "fds_use_pt": fds,
            "original_pt": "Os dados publicados e conferidos permanecem inalterados.", "pending": pending}


# ------------------------------------------------------------------ proposal evaluation (preview and decide)
def _error(field, code, message):
    return {"field": field, "code": code, "message_pt": message}


def _stored_proposal(contract, proposal, values):
    stored = {k: proposal.get(k, f.default) for k, f in Proposal.model_fields.items()}
    if contract["kind"] == "QUANTITY" and values.get("quantity"):
        stored["value"], stored["unit"] = values["quantity"]["value"], values["quantity"]["unit"]
    return stored


def _evaluate(exp, task, profile, action, proposal, old, change_reason):
    contract = contracts.contract_for(task["parameter"])
    errors, warnings = [], []
    mode = task["policy"]["mode"]
    if action == "ASSUMPTION" and mode != "ALLOWED":
        errors.append(_error("action", "HYPOTHESIS_NOT_ALLOWED", task["policy"]["reason_pt"]))
    if action == "EXPLORATORY_DRAFT" and mode != "DRAFT_ONLY":
        errors.append(_error("action", "DRAFT_NOT_APPLICABLE", "Rascunho exploratório só se aplica quando o perfil não permite hipótese neste campo."
                             if mode == "ALLOWED" else task["policy"]["reason_pt"]))
    structured = proposal.get("structured")
    if contract["kind"] == "QUANTITY":
        payload = structured if isinstance(structured, dict) else {"quantity": {"value": proposal.get("value"), "unit": proposal.get("unit")}}
    elif contract["kind"] == "DOCUMENT":
        payload = structured if isinstance(structured, dict) else {"description": proposal.get("details")}
    else:
        payload = structured if isinstance(structured, dict) else None
        if payload is None:
            errors.append(_error("structured", "STRUCTURED_REQUIRED", f"{contract['title_pt']} usa formulário estruturado ({contract['kind_pt'].lower()}); "
                                 "texto livre não é aceito como registro científico. Preencha os campos do formulário."))
    result = contracts.validate(contract, payload) if payload is not None else {"errors": [], "warnings": [], "conversions": [], "values": {}, "completeness": None}
    errors += result["errors"]
    warnings += result["warnings"]
    ce, cw = contracts.context_checks(task["parameter"], result["values"], _published(exp))
    errors += ce
    warnings += cw
    for key, n, label in (("author", 2, "Responsável pelo registro"), ("source", 10, "Fonte científica ou referência"),
                          ("location", 2, "Página ou localização"), ("evidence", 10, "Evidência ou trecho de apoio")):
        v = proposal.get(key)
        if not isinstance(v, str) or len(v.strip()) < n:
            errors.append(_error(key, "REQUIRED", f"{label}: mínimo de {n} caracteres."))
    if action in HYPOTHESIS_ACTIONS:
        for key, label in (("justification", "Justificativa"), ("limitations", "Limites de validade")):
            v = proposal.get(key)
            if not isinstance(v, str) or len(v.strip()) < 5:
                errors.append(_error(key, "REQUIRED", f"{label}: obrigatório para hipóteses e rascunhos exploratórios (mín. 5 caracteres)."))
    if workspace.current_mode() == "SCIENTIFIC":
        found = contracts.test_like_texts({**{k: proposal.get(k) for k in TEXT_KEYS}, "structured": payload})
        if found:
            errors.append(_error("source", "TEST_CONTENT_IN_SCIENTIFIC_MODE",
                                 f"O texto “{found[0]}” parece conteúdo de teste. No modo científico registre a fonte real; para testar a interface, use o modo de teste (armazenamento isolado)."))
    values = result["values"]
    if contract["kind"] == "QUANTITY" and values.get("quantity"):
        q = values["quantity"]
        normalized = {"kind": "SCALAR", "value": q["si_value"], "unit": q["si_unit"], "dimension": q["dimension"], "physical_validation": "BASIC_DOMAIN_ONLY"}
    elif contract["kind"] == "DOCUMENT":
        normalized = {"kind": "DOCUMENT", "details": values.get("description", ""), "physical_validation": "REQUIRES_SPECIALIST_SCHEMA"}
    else:
        normalized = {"kind": "STRUCTURED", "values": values, "completeness": result["completeness"], "physical_validation": contract["physical_validation"]}
    normalized["contract"] = {"parameter": task["parameter"], "kind": contract["kind"], "version": contract["version"]}
    normalized["summary_pt"] = contracts.summary_pt(contract, values)
    stored = _stored_proposal(contract, proposal, values)
    revision_of = old.get("revision") if old.get("proposal") and old.get("normalized") else None
    changes = []
    if revision_of:
        changes = contracts.diff(old.get("proposal"), stored)
        if old.get("proposal_kind") != action:
            changes.append({"field": "proposal_kind", "before": old.get("proposal_kind"), "after": action})
        if len(change_reason.strip()) < 5:
            errors.append(_error("change_reason", "CHANGE_REASON_REQUIRED", "Esta pendência já tem um registro: explique o motivo da alteração (mín. 5 caracteres). O registro anterior será preservado no histórico."))
        if not changes:
            errors.append(_error("change_reason", "NO_CHANGE", "Nada foi alterado em relação ao registro atual."))
    return {"errors": errors, "warnings": warnings, "conversions": result["conversions"], "normalized": normalized,
            "stored": stored, "revises_revision": revision_of, "diff": changes, "contract": contract}


# ------------------------------------------------------------------ view
def _ctx(g, profile, requirements, supported):
    req = requirements.get(g["parameter"])
    comparison = "QUANTITATIVE_COMPARISON" in g.get("categories", [])
    role = "CONSTRUCTION_INPUT" if req else "COMPARISON_ONLY" if comparison else "FIDELITY_CONTEXT"
    contract = contracts.contract_for(g["parameter"])
    return {"parameter": g["parameter"], "label": g.get("label_pt") or g["parameter"], "req": req, "role": role,
            "contract": contract, "profile": profile, "supported": supported}


def _requirement_rows(exp, profile, resolved, tasks, supported):
    if not supported:
        return []
    conditions = {p["parameter"]: p for p in resolved["conditions"]}
    labels = {p["parameter"]: p["label_pt"] for p in exp.get("parameters", [])}
    by_param = {t["parameter"]: t for t in tasks}
    rows = []
    for r in profile.get("requirements", []):
        name = r["parameter"]
        t = by_param.get(name)
        if name in conditions:
            p = conditions[name]
            ev = (p.get("evidence") or [{}])[0]
            rows.append({"parameter": name, "label_pt": labels.get(name, REQUIREMENT_LABEL.get(name, name)), "category": "DATA_INPUT",
                         "tier": "PUBLISHED_VERIFIED", "tier_pt": TIER_PT["PUBLISHED_VERIFIED"], "satisfied": True, "gap_id": None,
                         "original": {"value": (p.get("original") or {}).get("value"), "unit": (p.get("original") or {}).get("unit"),
                                      "record_id": p["record_id"], "status": p["status"], "page_pdf": ev.get("page_pdf"), "locator_pt": ev.get("locator_pt")},
                         "proposal": None, "checks": [], "reason_pt": "Valor publicado e conferido por uma pessoa (dado original preservado).",
                         "next_step_pt": None})
        elif t:
            cur = t["current"] or {}
            prop = None
            if cur.get("proposal") or cur.get("draft"):
                prop = {"revision": cur.get("revision"), "action": cur.get("action"), "kind": cur.get("proposal_kind"), "state": t["state"],
                        "author": (cur.get("proposal") or {}).get("author") or cur.get("author"), "at": cur.get("at"), "mode": cur.get("mode", "SCIENTIFIC"),
                        "summary_pt": ((cur.get("normalized") or {}).get("summary_pt") or (cur.get("proposal") or {}).get("details")
                                       or ("Rascunho de formulário" if cur.get("draft") else "")),
                        "origin_pt": {"SOURCE": "Evidência complementar", "ASSUMPTION": "Hipótese proposta", "EXPLORATORY_DRAFT": "Rascunho exploratório"}.get(cur.get("proposal_kind"), "Rascunho"),
                        "source": (cur.get("proposal") or {}).get("source")}
            pending = [c for c in t["checks"] if not c["done"]]
            rows.append({"parameter": name, "label_pt": t["label_pt"], "category": "DATA_INPUT", "tier": t["tier"], "tier_pt": TIER_PT[t["tier"]],
                         "satisfied": t["state"] == "RESOLVED_FOR_PROFILE", "gap_id": t["gap_id"], "original": None,
                         "original_pt": t.get("explanation_pt"), "proposal": prop, "checks": t["checks"], "quality_flags": t["quality_flags"],
                         "reason_pt": pending[0]["detail_pt"] if pending else "Satisfeito.", "next_step_pt": t["next_step"]["text_pt"]})
        else:
            rows.append({"parameter": name, "label_pt": labels.get(name, REQUIREMENT_LABEL.get(name, name)), "category": "DATA_INPUT", "tier": "MISSING",
                         "tier_pt": TIER_PT["MISSING"], "satisfied": False, "gap_id": None, "original": None, "proposal": None, "checks": [],
                         "reason_pt": "Não há valor conferido nem pendência registrada; revise os parâmetros na fonte.", "next_step_pt": "Revisar parâmetros na fonte."})
    for name in profile.get("additional_requirements", []):
        rows.append({"parameter": name, "label_pt": REQUIREMENT_LABEL.get(name, name), "category": "MODEL_DEVELOPMENT", "tier": "MODEL_DEVELOPMENT",
                     "tier_pt": TIER_PT["MODEL_DEVELOPMENT"], "satisfied": False, "gap_id": None, "original": None, "proposal": None, "checks": [],
                     "reason_pt": ADDITIONAL_PT.get(name, "Exige desenvolvimento do perfil físico."),
                     "next_step_pt": "Fora desta tela: desenvolvimento e aprovação do perfil físico."})
    return rows


def _summary(tasks, rows, profile, supported):
    data_rows = [r for r in rows if r["category"] == "DATA_INPUT"]
    count = lambda tier: sum(t["tier"] == tier for t in tasks)
    handled = [t for t in tasks if t["tier"] in EVIDENCE_TIERS or t["tier"] == "NOT_FOUND"]
    construction = [t for t in tasks if t["role"] == "CONSTRUCTION_INPUT"]
    hyps = [t for t in tasks if (t["current"] or {}).get("proposal_kind") in HYPOTHESIS_ACTIONS and t["tier"] in EVIDENCE_TIERS]
    pyro = next((t for t in tasks if t["parameter"] == "pmma_pyrolysis_properties"), None)
    completeness = (((pyro or {}).get("current") or {}).get("normalized") or {}).get("completeness") if pyro and pyro["tier"] in EVIDENCE_TIERS else None
    approved = profile["approved"] and profile["implemented"]
    satisfied = sum(r["satisfied"] for r in data_rows)
    ladder = [
        {"key": "PUBLISHED_VERIFIED", "label_pt": "Dados publicados e conferidos", "count": sum(r["tier"] == "PUBLISHED_VERIFIED" for r in data_rows), "of": len(data_rows), "unit_pt": "requisitos do perfil"},
        {"key": "EVIDENCE_SUBMITTED", "label_pt": "Evidência complementar submetida", "count": count("EVIDENCE_SUBMITTED"), "of": len(tasks), "unit_pt": "pendências"},
        {"key": "HYPOTHESIS_PROPOSED", "label_pt": "Hipóteses e rascunhos exploratórios propostos", "count": count("HYPOTHESIS_PROPOSED") + count("EXPLORATORY_DRAFT"), "of": len(tasks), "unit_pt": "pendências"},
        {"key": "REVIEWED", "label_pt": "Revisados por pessoa independente", "count": count("REVIEWED") + count("REQUIREMENT_SATISFIED"), "of": len(tasks), "unit_pt": "pendências"},
        {"key": "REQUIREMENT_SATISFIED", "label_pt": "Requisitos satisfeitos para o perfil", "count": satisfied, "of": len(data_rows), "unit_pt": "requisitos do perfil"},
        {"key": "MODEL_APPROVED", "label_pt": "Modelo físico aprovado para execução", "count": int(approved), "of": 1, "unit_pt": "perfil"},
    ]
    with_record = sum(t["tier"] in EVIDENCE_TIERS for t in construction)
    stages = [
        {"key": "DOCUMENT_PREPARATION", "label_pt": "Preparação documental",
         "status": "COMPLETE" if construction and with_record == len(construction) else "IN_PROGRESS" if with_record else "NOT_STARTED",
         "detail_pt": f"{with_record} de {len(construction)} informações de construção com evidência ou hipótese registrada; {satisfied} de {len(data_rows)} requisitos de dados satisfeitos."},
        {"key": "HYPOTHESIS_BUILDING", "label_pt": "Construção de hipóteses",
         "status": "IN_PROGRESS" if hyps else "NOT_STARTED",
         "detail_pt": f"{len(hyps)} hipótese(s) ou rascunho(s) exploratório(s); {sum(t['tier'] in ('REVIEWED', 'REQUIREMENT_SATISFIED') and t in hyps for t in tasks)} revisado(s). Nenhuma é aprovada automaticamente."},
        {"key": "MATERIAL_MODEL_VALIDATION", "label_pt": "Validação do modelo de material", "status": "BLOCKED",
         "detail_pt": ("Propriedades registradas: " + (f"{len(completeness['present'])} de {len(completeness['required'])}; faltam " + ", ".join(completeness["missing_pt"]) if completeness and completeness["required"] else "modelo sem conjunto definido")
                       if completeness else "Nenhuma propriedade de pirólise registrada.") + " A revisão do modelo de material não existe nesta versão."},
        {"key": "GENERATOR_VALIDATION", "label_pt": "Validação do gerador FDS", "status": "COMPLETE" if approved else "NOT_IMPLEMENTED",
         "detail_pt": "Gerador implementado e aprovado." if approved else f"O gerador do perfil {profile['title_pt']} não está implementado nem aprovado."},
        {"key": "EXECUTION_AUTHORIZATION", "label_pt": "Autorização de execução", "status": "BLOCKED",
         "detail_pt": "Bloqueada: depende das etapas anteriores e de um perfil físico aprovado." if supported else "Física não suportada por este perfil."},
    ]
    return {"gaps_total": len(tasks), "gaps_handled": len(handled), "gaps_drafts": count("DRAFT"), "gaps_untouched": count("OPEN"),
            "gaps_test_content": count("TEST_CONTENT"), "requirements_total": len(data_rows), "requirements_satisfied": satisfied,
            "model_checks_total": len(rows) - len(data_rows), "ladder": ladder, "stages": stages}


@bridge.serialized
def view(exp, pid):
    profile = _profile(exp, pid)
    log = _load(exp["experiment_id"], pid)
    resolved = bridge.resolve(exp)
    gaps = sorted(resolved["gaps"], key=lambda g: (ORDER.index(g["parameter"]) if g["parameter"] in ORDER else len(ORDER), g["parameter"], g["gap_id"]))
    supported = _supported(exp, profile)
    requirements = {r["parameter"]: r for r in profile.get("requirements", [])} if supported else {}
    duplicates = _duplicates(log, {g["gap_id"]: g for g in gaps})
    tasks = []
    for g in gaps:
        ctx = _ctx(g, profile, requirements, supported)
        contract, req, role = ctx["contract"], ctx["req"], ctx["role"]
        current = _latest(log, g["gap_id"])
        state = current["state"] if current else "OPEN"
        if state == "RESOLVED_FOR_PROFILE" and not _eligible(current, profile, exp):
            state = "UNDER_REVIEW"
        policy = _policy(contract, req, supported, role, profile)
        impact = ("Impede comparação quantitativa; não é uma entrada de execução." if role == "COMPARISON_ONLY"
                  else "Bloqueia a construção do modelo físico." if req else "Limita a fidelidade ao ensaio; não é requisito de construção deste perfil.")
        flags = _flags(current, contract, duplicates)
        tier = _tier(current, state, flags)
        checks = _checks(ctx, current, tier, flags)
        task = {**g, "why_pt": WHY.get(g["parameter"], "Permite avaliar se a descrição científica atende aos requisitos do perfil selecionado."),
                "impact_pt": impact, "required": bool(req), "role": role, "state": state, "current": current,
                "assumption_allowed": policy["mode"] == "ALLOWED", "assumption_reason_pt": policy["reason_pt"], "policy": policy,
                "schema": {"kind": "SCALAR" if contract["kind"] == "QUANTITY" else "DOCUMENT" if contract["kind"] == "DOCUMENT" else "STRUCTURED",
                           "unit": units.display_unit(units.si_unit_of(contract["fields"][0]["dimension"])) if contract["kind"] == "QUANTITY" else "n/a"},
                "contract": contracts.export(contract),
                "known": [p for p in exp["parameters"] if p["parameter"] in RELATED.get(g["parameter"], [])],
                "history": [e for e in log["events"] if e.get("gap_id") == g["gap_id"] and e["action"] != "NAVIGATE"],
                "quality_flags": flags, "tier": tier, "tier_pt": TIER_PT[tier], "checks": checks,
                "next_step": _next_step(tier, checks, state, contract, flags)}
        task["consequences"] = (_consequences(ctx, current.get("proposal_kind"), current.get("mode", "SCIENTIFIC"), checks, state == "RESOLVED_FOR_PROFILE")
                                if current and current.get("proposal_kind") else None)
        tasks.append(task)
    conditions = {p["parameter"] for p in resolved["conditions"]}
    satisfied = [r for r in requirements if r in conditions or any(t["parameter"] == r and t["state"] == "RESOLVED_FOR_PROFILE" for t in tasks)]
    pending = [r for r in requirements if r not in satisfied]
    cursor = next((e.get("cursor") for e in reversed(log["events"]) if e.get("cursor")), None)
    if cursor not in {t["gap_id"] for t in tasks}:
        cursor = None
    rows = _requirement_rows(exp, profile, resolved, tasks, supported)
    actionable = next((t for t in tasks if t["next_step"]["category"] in ("DATA", "REVIEW")), None)
    next_step = ({"gap_id": actionable["gap_id"], "text_pt": f"{actionable['label_pt']}: {actionable['next_step']['text_pt']}"} if actionable
                 else {"gap_id": None, "text_pt": "Todos os registros possíveis nesta tela foram feitos. O bloqueio restante é o modelo físico (perfil sem gerador implementado e aprovado)."})
    return {"experiment_id": exp["experiment_id"], "title": exp["label"], "profile": profile, "revision": len(log["events"]),
            "mode": workspace.current_mode(), "tasks": tasks, "cursor": cursor or (tasks[0]["gap_id"] if tasks else None),
            "recorded": sum(t["current"] is not None for t in tasks), "resolved": sum(t["state"] == "RESOLVED_FOR_PROFILE" for t in tasks),
            "readiness": {"supported": supported, "generator_approved": profile["approved"] and profile["implemented"],
                          "satisfied": satisfied, "pending": pending, "additional": profile.get("additional_requirements", []),
                          "can_execute": False, "message_pt": MODEL_MESSAGE if supported else "A física deste experimento não é suportada por este perfil FDS. A revisão documental continua disponível."},
            "requirements": rows, "summary": _summary(tasks, rows, profile, supported), "next_step": next_step,
            "history": log["events"]}


@bridge.serialized
def navigate(exp, pid, req: CursorInput):
    data = view(exp, pid)
    if req.expected_revision != data["revision"]:
        raise ValueError("A revisão mudou em outra janela. Recarregue antes de salvar.")
    if req.gap_id not in {t["gap_id"] for t in data["tasks"]}:
        raise ValueError("Pendência não pertence a este experimento.")
    log = _load(exp["experiment_id"], pid)
    _append(log, exp["experiment_id"], pid, {"action": "NAVIGATE", "cursor": req.gap_id, "mode": workspace.current_mode()})
    return view(exp, pid)


@bridge.serialized
def preview(exp, pid, gid, req: PreviewInput):
    """Deterministic dry run: what would be saved, which requirement it may satisfy and why it is (not) an FDS input."""
    data = view(exp, pid)
    task = next((t for t in data["tasks"] if t["gap_id"] == gid), None)
    if not task:
        raise ValueError("Pendência não pertence a este experimento.")
    ev = _evaluate(exp, task, data["profile"], req.action, req.proposal, task["current"] or {}, req.change_reason)
    mode = workspace.current_mode()
    would = {"proposal_kind": req.action, "mode": mode, "normalized": ev["normalized"], "review_state": "PENDING",
             "state": {"SOURCE": "SOURCE_SUBMITTED", "ASSUMPTION": "ASSUMPTION_PROPOSED"}.get(req.action, "EXPLORATORY_DRAFT")}
    ctx = _ctx(task, data["profile"], {r["parameter"]: r for r in data["profile"].get("requirements", [])} if data["readiness"]["supported"] else {}, data["readiness"]["supported"])
    tier = KIND_TIER[req.action]
    checks = _checks(ctx, would, tier, [])
    return {"ok": not ev["errors"], "errors": ev["errors"], "warnings": ev["warnings"], "conversions": ev["conversions"],
            "summary_pt": ev["normalized"]["summary_pt"], "completeness": ev["normalized"].get("completeness"),
            "revises_revision": ev["revises_revision"], "diff": ev["diff"], "will_be_state": would["state"], "tier": tier, "tier_pt": TIER_PT[tier],
            "checks": checks, "consequences": _consequences(ctx, req.action, mode, checks, False), "mode": mode}


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
    mode = workspace.current_mode()
    old = task["current"] or {}
    event = {"gap_id": gid, "parameter": task["parameter"], "action": req.action, "author": req.author,
             "notes": req.notes, "cursor": req.next_gap_id or gid, "profile_sha256": bridge.digest(profile),
             "profile_version": profile["version"], "profile_id": pid, "catalog_sha256": bridge.digest(exp), "mode": mode}
    if req.action == "DRAFT":
        allowed = {"value", "unit", "source", "location", "evidence", "author", "justification", "limitations", "details", "action", "notes",
                   "structured_json", "basis", "change_reason"}
        if not req.draft or set(req.draft) - allowed or any(len(v) > (40000 if k == "structured_json" else 6000) for k, v in req.draft.items()):
            raise ValueError("Rascunho inválido.")
        event.update(state="IN_PROGRESS", draft=req.draft, review_state="DRAFT_UNVALIDATED")
    elif req.action in PROPOSAL_ACTIONS:
        if req.proposal is None or req.proposal.author.casefold() != req.author.casefold():
            raise ValueError("Informe a proposta e o mesmo responsável pelo registro.")
        ev = _evaluate(exp, task, profile, req.action, req.proposal.model_dump(), old, req.change_reason)
        if ev["errors"]:
            raise ValueError(" ".join(e["message_pt"] for e in ev["errors"][:4]))
        stored, norm = ev["stored"], ev["normalized"]
        assumption = hypothesis = None
        if req.action == "ASSUMPTION" and norm["kind"] == "SCALAR":
            a = req.proposal
            assumption = bridge.Assumption(parameter=task["parameter"], value=float(stored["value"]), unit=stored["unit"], source=a.source,
                                           source_type=a.basis, justification=a.justification,
                                           author=a.author, limitations=a.limitations).model_dump()
        if req.action in HYPOTHESIS_ACTIONS:
            hypothesis = {"parameter": task["parameter"], "basis": req.proposal.basis, "profile_id": pid, "profile_version": profile["version"],
                          "contract_version": ev["contract"]["version"],
                          "usage": "EXPLORATORY_HYPOTHESIS_NOT_APPROVED" if req.action == "ASSUMPTION" else "EXPLORATORY_DRAFT_NOT_APPROVED_NEVER_FDS_INPUT"}
        event.update(state={"SOURCE": "SOURCE_SUBMITTED", "ASSUMPTION": "ASSUMPTION_PROPOSED"}.get(req.action, "EXPLORATORY_DRAFT"),
                     proposal=stored, normalized=norm, proposal_kind=req.action, assumption=assumption, hypothesis=hypothesis,
                     review_state="PENDING", warnings=[w["message_pt"] for w in ev["warnings"]], conversions=ev["conversions"],
                     contract_version=ev["contract"]["version"])
        if ev["revises_revision"]:
            event.update(revises_revision=ev["revises_revision"], change_reason=req.change_reason.strip(), diff=ev["diff"])
    elif req.action in {"NOT_FOUND", "DEFER"}:
        if len(req.notes) < 5:
            raise ValueError("Registre onde procurou ou o motivo do adiamento.")
        event.update(state="BLOCKED" if req.action == "NOT_FOUND" else "OPEN", review_state="NOT_REVIEWED",
                     draft=old.get("draft"), proposal=old.get("proposal"))
    else:
        if req.action == "REQUEST_REVIEW":
            if old.get("state") not in {"SOURCE_SUBMITTED", "ASSUMPTION_PROPOSED", "EXPLORATORY_DRAFT"}:
                raise ValueError("Envie uma proposta antes de solicitar revisão.")
        else:
            if old.get("state") != "UNDER_REVIEW" or len(req.notes) < 5:
                raise ValueError("Solicite revisão e registre o parecer antes da decisão independente.")
            if req.author.casefold() == old["proposal"]["author"].casefold():
                raise ValueError("A revisão deve ser feita por outra pessoa, independente do autor.")
        event.update({k: old[k] for k in ("proposal", "normalized", "proposal_kind", "assumption", "hypothesis", "contract_version") if k in old})
        event.update(state="UNDER_REVIEW", review_state="ACCEPTED" if req.action == "ACCEPT" else "REJECTED" if req.action == "REJECT" else "PENDING")
        if req.action == "REJECT":
            event["state"] = "IN_PROGRESS"
        elif req.action == "ACCEPT" and _eligible(event, profile, exp) and data["readiness"]["supported"]:
            event["state"] = "RESOLVED_FOR_PROFILE"
    # Immutable BL-16 case version captures the decisions, never inputs to a generator.
    log = _load(exp["experiment_id"], pid)
    previous_case = next((e.get("case_id") for e in reversed(log["events"]) if e.get("case_id")), None)
    snapshot = {"previous_audit_sha256": log["events"][-1]["sha256"] if log["events"] else None,
                "decision": event, "usage": "TEST_ONLY_SYNTHETIC_NOT_SCIENTIFIC" if mode == "TEST" else "DOCUMENTATION_ONLY_NOT_GENERATOR_INPUT"}
    case = bridge.create(bridge.CaseInput(profile_id=pid, profile_version=profile["version"], experiment_id=exp["experiment_id"],
                                         title=exp["label"][:80]), catalog, previous_case, review_snapshot=snapshot)
    event.update(case_id=case["content"]["case_id"], case_version=case["content"]["version"], case_sha256=case["content_sha256"])
    _append(log, exp["experiment_id"], pid, event)
    return view(exp, pid)
