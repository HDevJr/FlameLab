"""Relações e decisões sobre LACUNAS (informação que a fonte não traz) × PARÂMETROS extraídos.

Problema real (DYLCO, 15/11): a lacuna `cell_dihedral_angle`, sugerida pela IA ao ler as páginas 1–12, coexiste com o
parâmetro `dihedral_angle = 65 °`, extraído da p. 18. Eram lotes diferentes; ninguém reconciliou. O sistema:
  1. DETECTA a sobreposição (mesma grandeza, escopo possivelmente diferente) — nunca funde nem apaga sozinho;
  2. EXPLICA na interface;
  3. registra a DECISÃO humana (COVERED | PARTIAL | DISTINCT) com revisor, data e motivo, sem apagar o histórico.
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

from backend.app import workspace
from backend.app.nasa.provenance.log import utc_now

DECISIONS = ("COVERED", "PARTIAL", "DISTINCT")
_lock = threading.Lock()
# palavras de ESCOPO (a que objeto o valor se refere), não de grandeza
_SCOPE = {"cell", "cells", "vessel", "vessels", "container", "containers", "test", "sample", "samples", "all", "each",
          "principal", "exact", "initial", "final", "total"}
_STOP = {"of", "the", "a", "and", "level"}


def _core(name: str) -> set[str]:
    toks = set(re.findall(r"[a-z]+", (name or "").lower().replace("_", " ")))
    return toks - _SCOPE - _STOP


def _file() -> Path:
    return workspace.area("audit") / "gap_decisions.jsonl"


def decisions() -> list[dict[str, Any]]:
    path = _file()
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def latest(gap_id: str) -> dict[str, Any] | None:
    mine = [d for d in decisions() if d.get("gap_id") == gap_id]
    return mine[-1] if mine else None


def record_decision(gap_id: str, decision: str, reviewer: str, notes: str, record_id: str | None) -> dict[str, Any]:
    if decision not in DECISIONS:
        raise ValueError("DECISION_INVALID")
    entry = {"at": utc_now(), "gap_id": gap_id, "decision": decision, "reviewer": reviewer.strip(), "notes": notes.strip(),
             "record_id": record_id}
    with _lock, _file().open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def relations(gap: dict[str, Any], params: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parâmetros que tratam da MESMA grandeza que a lacuna. O escopo pode divergir: quem decide é uma pessoa."""
    core_g = _core(gap["parameter"])
    out = []
    for p in params:
        core_p = _core(p["parameter"])
        shared = core_g & core_p
        if len(shared) < 2 or not (core_g <= core_p or core_p <= core_g):
            continue
        scope_differs = set(re.findall(r"[a-z]+", gap["parameter"].replace("_", " "))) != set(re.findall(r"[a-z]+", p["parameter"].replace("_", " ")))
        ev = (p.get("evidence") or [{}])[0]
        o = p.get("original") or {}
        out.append({
            "record_id": p["record_id"], "label_pt": p.get("label_pt"), "value": o.get("value"), "unit": o.get("unit"),
            "page": ev.get("page_pdf"), "quote": ev.get("quote"), "scope_differs": scope_differs,
            "relation": "SAME_QUANTITY_SCOPE_TO_CONFIRM" if scope_differs else "SAME_QUANTITY",
            "explanation_pt": (
                f"Mesma grandeza (“{' '.join(sorted(shared))}”). A lacuna cita um escopo (“{gap['parameter'].replace('_', ' ')}”) e o parâmetro "
                f"“{p['parameter'].replace('_', ' ')}” traz um valor pontual (p. {ev.get('page_pdf')}). Verifique se o valor cobre TODOS os objetos "
                "a que a lacuna se refere; se cobrir só parte, a cobertura é parcial e a lacuna continua aberta."),
        })
    return out
