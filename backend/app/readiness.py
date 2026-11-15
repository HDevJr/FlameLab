"""Prontidão de um experimento em CINCO dimensões independentes.

Nenhuma dimensão substitui outra: parâmetros todos conferidos NÃO habilitam a simulação.
  1. INTEGRIDADE DA EXTRAÇÃO   grandeza, unidade e condição sustentadas pela fonte?
  2. REVISÃO CIENTÍFICA        conferido por pessoa — e a INTERPRETAÇÃO, não só o número?
  3. COBERTURA                 o que falta (lacunas e entradas exigidas por um modelo)
  4. COMPATIBILIDADE FDS       a física do experimento é a do FDS (e há modelo)?
  5. PRONTIDÃO PARA EXECUÇÃO   só quando 1–4 estão satisfeitos e há executor
"""

from __future__ import annotations

from typing import Any

from backend.app.integrity import SEV_BLOCKING
from backend.app.simulation.registry import MODELS
from backend.app.simulation.compatibility import ALIASES


def _dim(key: str, label: str, status: str, tone: str, summary: str, items: list[str] | None = None) -> dict[str, Any]:
    return {"key": key, "label_pt": label, "status": status, "tone": tone, "summary_pt": summary, "items": items or []}


def build(exp: dict[str, Any], compat: dict[str, Any], executor_available: bool) -> dict[str, Any]:
    params = exp.get("parameters") or []
    gaps = exp.get("gaps") or []
    n = len(params)

    # 1. integridade da extração
    inconsistent = [p for p in params if (p.get("integrity") or {}).get("status") == "INCONSISTENT"]
    attention = [p for p in params if (p.get("integrity") or {}).get("status") == "ATTENTION"]
    items = [f"{p['label_pt']}: " + "; ".join(f["title_pt"] for f in p["integrity"]["findings"] if f["severity"] == SEV_BLOCKING)
             for p in inconsistent]
    if not n:
        d1 = _dim("extraction_integrity", "Integridade da extração", "SEM_PARAMETROS", "muted", "Nenhum parâmetro extraído.")
    elif inconsistent:
        d1 = _dim("extraction_integrity", "Integridade da extração", "INCONSISTENTE", "bad",
                  f"{len(inconsistent)} de {n} parâmetro(s) com inconsistência de grandeza, unidade ou condição.", items)
    elif attention:
        d1 = _dim("extraction_integrity", "Integridade da extração", "ATENCAO", "warn", f"{len(attention)} parâmetro(s) com ressalvas.")
    else:
        d1 = _dim("extraction_integrity", "Integridade da extração", "OK", "ok", f"{n} parâmetro(s) sem inconsistências detectadas.")

    # 2. revisão científica
    confirmed = [p for p in params if p["status"] in ("CONFERIDO_FONTE", "APROVADO_MODELO")]
    full = [p for p in confirmed if p.get("review_scope") == "FULL"]
    legacy = [p for p in confirmed if p.get("review_scope") != "FULL"]
    bad_confirmed = [p for p in confirmed if p in inconsistent]
    pending = n - len(confirmed)
    if not n:
        d2 = _dim("scientific_review", "Revisão científica", "SEM_PARAMETROS", "muted", "Nada a revisar.")
    elif not confirmed:
        d2 = _dim("scientific_review", "Revisão científica", "NAO_INICIADA", "warn", f"0 de {n} conferidos por uma pessoa.")
    elif pending:
        d2 = _dim("scientific_review", "Revisão científica", "PARCIAL", "warn", f"{len(confirmed)} de {n} conferidos; {pending} pendente(s).")
    elif legacy or bad_confirmed:
        why = []
        if legacy:
            why.append(f"{len(legacy)} com revisão anterior à confirmação da interpretação (só número/unidade foram comparados)")
        if bad_confirmed:
            why.append(f"{len(bad_confirmed)} conferido(s) com inconsistência de integridade")
        d2 = _dim("scientific_review", "Revisão científica", "COMPLETA_COM_RESSALVAS", "warn",
                  f"Todos os {n} foram conferidos, mas há ressalvas: " + "; ".join(why) + ". Nova revisão humana recomendada.",
                  [p["label_pt"] for p in (legacy + bad_confirmed)])
    else:
        d2 = _dim("scientific_review", "Revisão científica", "COMPLETA", "ok", f"Todos os {n} conferidos (número, unidade e interpretação).")

    # 3. cobertura
    open_gaps = [g for g in gaps if (g.get("decision") or {}).get("decision") != "COVERED"]
    missing = compat.get("missing") or []
    model = MODELS.get(compat.get("model_id"))
    required = {ALIASES.get(name, name) for name in model.required_inputs} if model else set()
    input_gaps = [g for g in open_gaps if ALIASES.get(g["parameter"], g["parameter"]) in required]
    labels = {ALIASES.get(g["parameter"], g["parameter"]): g["label_pt"] for g in gaps}
    input_labels = list(dict.fromkeys([g["label_pt"] for g in input_gaps] + [labels.get(name, name.replace("_", " ")) for name in missing]))
    if compat.get("status") == "UNSUPPORTED_PHYSICS":
        d3 = _dim("coverage", "Cobertura dos parâmetros", "SEM_MODELO", "muted",
                  f"Sem modelo FDS aplicável, não há lista de entradas exigidas. {len(open_gaps)} lacuna(s) registrada(s).",
                  [g["label_pt"] for g in open_gaps])
    elif input_gaps or missing:
        d3 = _dim("coverage", "Cobertura dos parâmetros", "INCOMPLETA", "warn",
                  f"{len(input_labels)} informações exigidas pelo perfil precisam de revisão. Lacunas de fidelidade e comparação são avaliadas separadamente.",
                  input_labels)
    else:
        d3 = _dim("coverage", "Cobertura dos parâmetros", "COMPLETA", "ok", "Entradas exigidas pelo perfil presentes; outras lacunas podem limitar fidelidade e comparação.")

    # 4. compatibilidade com o FDS
    cs = compat.get("status")
    tone = {"COMPATIBLE": "ok", "MISSING_PARAMETERS": "warn", "REQUIRES_REVIEW": "warn", "UNSUPPORTED_PHYSICS": "bad"}.get(cs or "", "muted")
    reasons = [r for r in (compat.get("reasons_pt") or []) if "observados" not in r][:3]
    d4 = _dim("fds_compatibility", "Compatibilidade com o motor FDS", cs or "NAO_AVALIADA", tone,
              {"COMPATIBLE": "Há modelo e a física é compatível.", "UNSUPPORTED_PHYSICS": "A física do experimento não é a do FDS (incêndio e fumaça); nenhum caso será gerado.",
               "MISSING_PARAMETERS": "Há modelo, mas faltam parâmetros.", "REQUIRES_REVIEW": "Há modelo, mas depende de revisão ou de aprovação do gerador."}.get(cs or "", "Não avaliada."),
              reasons)

    # 5. prontidão para execução — só com 1–4 satisfeitos
    blockers = []
    if cs != "COMPATIBLE":
        blockers.append("compatibilidade com o FDS não satisfeita")
    if d1["status"] != "OK":
        blockers.append("integridade da extração não está OK")
    if d2["status"] != "COMPLETA":
        blockers.append("revisão científica não está completa")
    if d3["status"] != "COMPLETA":
        blockers.append("cobertura incompleta")
    if not executor_available:
        blockers.append("executor FDS indisponível")
    if blockers:
        d5 = _dim("execution_readiness", "Prontidão para execução", "BLOQUEADA", "bad",
                  "A simulação NÃO está habilitada. Conferir os parâmetros não basta: " + "; ".join(blockers) + ".", blockers)
    else:
        d5 = _dim("execution_readiness", "Prontidão para execução", "PRONTA", "ok", "Todas as condições estão satisfeitas.")
    return {"dimensions": [d1, d2, d3, d4, d5], "can_simulate": not blockers}
