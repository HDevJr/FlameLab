"""Avaliação de compatibilidade de um experimento com os motores de simulação integrados.

Genérica: usa apenas fenômenos, papéis, estados de revisão e lacunas do experimento.
A análise, a comparação e a exportação não dependem deste resultado.
"""

from __future__ import annotations

from typing import Any

from backend.app import units
from backend.app.simulation.models import Compatibility
from backend.app.simulation.registry import FDS_PHENOMENA, MODELS

APPROVED = frozenset({"CONFERIDO_FONTE", "APROVADO_MODELO"})
ALIASES = {"material_pyrolysis_properties": "pmma_pyrolysis_properties"}


def is_editable(p: dict[str, Any]) -> bool:
    """Condição de entrada numérica com unidade conhecida (para poder validar faixas).
    Resultados observados e metadados nunca são editáveis."""
    o = p.get("original") or {}
    return (p["role"] == "CONDICAO" and isinstance(o.get("value"), (int, float))
            and not isinstance(o.get("value"), bool) and units.canonical_unit(o.get("unit")) is not None)


def range_rule(unit: str | None) -> tuple[str, float | None, float | None]:
    """Regra física genérica por dimensão. Devolve (texto, mínimo exclusivo, máximo inclusivo) na unidade dada."""
    canon = units.canonical_unit(unit)
    q = units.normalize(1.0, unit)
    dim = q.dimension if q else None
    if dim == "temperature":  # limite = zero absoluto, expresso na MESMA unidade (exclusivo)
        floor = {"K": 0.0, "degC": -273.15, "degF": -459.67}.get(canon or "", 0.0)
        return f"acima do zero absoluto ({floor:g} {units.display_unit(canon)})", floor, None
    if dim in ("length", "velocity", "time", "pressure", "volume", "mass", "area", "frequency", "power"):
        return "maior que zero", 0.0, None
    if dim == "fraction":
        top = 100.0 if units.canonical_unit(unit) == "%" else 1.0
        return f"entre 0 (exclusivo) e {top:g}", 0.0, top
    return "maior ou igual a zero", None, None


def editable_entry(p: dict[str, Any]) -> dict[str, Any]:
    o = p["original"]
    rule, _, _ = range_rule(o.get("unit"))
    return {"parameter": p["parameter"], "label_pt": p["label_pt"], "value": o["value"], "unit": o.get("unit"),
            "status": p["status"], "rule_pt": rule,
            "source_pt": "; ".join(e.get("locator_pt") or "" for e in p.get("evidence") or [] if e.get("locator_pt"))
            or None}


def assess(experiment: dict[str, Any], executor_available: bool) -> dict[str, Any]:
    phenomena = set(experiment.get("phenomena") or [])
    params = {ALIASES.get(p["parameter"], p["parameter"]): p for p in experiment.get("parameters") or []}
    gaps = experiment.get("gaps") or []
    observables = [
        {"parameter": p["parameter"], "label_pt": p["label_pt"], "status": p["status"]}
        for p in params.values() if p["role"] == "OBSERVAVEL"
    ]
    editable_detail = [editable_entry(p) for p in params.values() if is_editable(p)]
    editable = [e["parameter"] for e in editable_detail]
    base = {
        "experiment_id": experiment["experiment_id"], "engine": "FDS", "model_id": None,
        "missing": [], "unreviewed": [], "reasons_pt": [], "reference_observables": observables,
        "editable_conditions": editable, "editable": editable_detail, "executor_available": executor_available,
        "actions": {"analyze": True, "prepare": bool(params), "alter": bool(editable), "simulate": False},
    }
    if observables:
        base["reasons_pt"].append(
            "Resultados observados (" + ", ".join(o["label_pt"] for o in observables) + ") são referência de "
            "comparação, nunca condição de entrada da simulação.")

    if not phenomena:
        return {**base, "status": Compatibility.REQUIRES_REVIEW.value,
                "reasons_pt": ["O fenômeno físico do experimento não foi classificado; é preciso revisão."]
                + base["reasons_pt"]}
    if not phenomena & FDS_PHENOMENA:
        return {**base, "status": Compatibility.UNSUPPORTED_PHYSICS.value,
                "reasons_pt": [f"Fenômenos do experimento ({', '.join(sorted(phenomena))}) não são tratados pelo "
                               "FDS, que modela incêndio e transporte de fumaça. Nenhum caso será gerado.",
                               "Análise, comparação de fontes e exportação continuam disponíveis."]
                + base["reasons_pt"]}

    model = next((m for m in MODELS.values() if m.purpose == "REPRODUCTION" and set(m.phenomena) & phenomena), None)
    if model is None:
        return {**base, "status": Compatibility.UNSUPPORTED_PHYSICS.value,
                "reasons_pt": ["Nenhum modelo de reprodução cobre estes fenômenos."] + base["reasons_pt"]}

    base["model_id"] = model.model_id
    required_inputs = [ALIASES.get(name, name) for name in model.required_inputs]
    missing = [name for name in required_inputs if name not in params]
    blocking_gaps = [ALIASES.get(g["parameter"], g["parameter"]) for g in gaps
                     if ALIASES.get(g["parameter"], g["parameter"]) in required_inputs]
    missing = sorted(set(missing) | set(blocking_gaps))
    # "Revisado" exige: conferido, integridade OK e revisão que cobriu a INTERPRETAÇÃO (não só número e unidade).
    unreviewed = sorted(name for name in required_inputs if name in params and (
        params[name]["status"] not in APPROVED
        or (params[name].get("integrity") or {}).get("status") == "INCONSISTENT"
        or (params[name].get("review_scope") not in (None, "FULL"))))
    reasons = []
    if missing:
        reasons.append(f"Faltam {len(missing)} informações necessárias ao modelo (lacunas registradas).")
    if unreviewed:
        reasons.append(f"{len(unreviewed)} condições existem na fonte, mas ainda não foram conferidas por humano.")
    if not model.implemented:
        reasons.append("O gerador do modelo de reprodução ainda não foi implementado e aprovado.")
    if not executor_available:
        reasons.append("O executor FDS não está disponível nesta instalação.")
    status = (Compatibility.MISSING_PARAMETERS if missing
              else Compatibility.REQUIRES_REVIEW if (unreviewed or not model.implemented)
              else Compatibility.COMPATIBLE if executor_available else Compatibility.REQUIRES_REVIEW)
    base["actions"]["simulate"] = status == Compatibility.COMPATIBLE
    return {**base, "status": status.value, "missing": missing, "unreviewed": unreviewed,
            "reasons_pt": reasons + base["reasons_pt"]}


def with_readiness(experiment: dict[str, Any], compat: dict[str, Any], executor_available: bool) -> dict[str, Any]:
    """Acrescenta as CINCO dimensões de prontidão e só mantém `simulate` se a prontidão para execução estiver satisfeita."""
    from backend.app.readiness import build

    r = build(experiment, compat, executor_available)
    compat = {**compat, "readiness": r}
    compat["actions"] = {**compat["actions"], "simulate": bool(compat["actions"]["simulate"] and r["can_simulate"])}
    return compat
