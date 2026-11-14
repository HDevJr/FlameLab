"""Avaliação de compatibilidade de um experimento com os motores de simulação integrados.

Genérica: usa apenas fenômenos, papéis, estados de revisão e lacunas do experimento.
A análise, a comparação e a exportação não dependem deste resultado.
"""

from __future__ import annotations

from typing import Any

from backend.app.simulation.models import Compatibility
from backend.app.simulation.registry import FDS_PHENOMENA, MODELS

APPROVED = frozenset({"CONFERIDO_FONTE", "APROVADO_MODELO"})


def assess(experiment: dict[str, Any], executor_available: bool) -> dict[str, Any]:
    phenomena = set(experiment.get("phenomena") or [])
    params = {p["parameter"]: p for p in experiment.get("parameters") or []}
    gaps = experiment.get("gaps") or []
    observables = [
        {"parameter": p["parameter"], "label_pt": p["label_pt"], "status": p["status"]}
        for p in params.values() if p["role"] == "OBSERVAVEL"
    ]
    editable = [p["parameter"] for p in params.values()
                if p["role"] == "CONDICAO" and isinstance((p.get("original") or {}).get("value"), (int, float))]
    base = {
        "experiment_id": experiment["experiment_id"], "engine": "FDS", "model_id": None,
        "missing": [], "unreviewed": [], "reasons_pt": [], "reference_observables": observables,
        "editable_conditions": editable, "executor_available": executor_available,
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
    missing = [name for name in model.required_inputs if name not in params]
    blocking_gaps = [g["parameter"] for g in gaps if "FDS_REPRODUCTION" in (g.get("purpose_blocked") or [])]
    missing = sorted(set(missing) | set(blocking_gaps))
    unreviewed = sorted(name for name in model.required_inputs if name in params
                        and params[name]["status"] not in APPROVED)
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
