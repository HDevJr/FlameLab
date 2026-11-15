"""Integridade CIENTÍFICA de um parâmetro: a grandeza, a unidade e a condição estão sustentadas pela fonte?

Separa o que costuma ser confundido numa conferência:
  1. valor localizado no PDF (o número aparece literalmente no trecho?)
  2. valor interpretado pela IA (nome/papel)           — ver `semantic.py`
  3. unidade                                           — estado + se o trecho a sustenta
  4. grandeza física                                   — dimensão esperada pelo nome × dimensão da unidade
  5. condição associada                                — "70 ° AT 20 °C": o valor depende de 20 °C
  6. confirmação humana / estado da revisão            — ver `review_service.py`

Regras determinísticas; nenhuma inventa unidade, condição ou significado. Gravidade:
  BLOCKING  — impede CONFERIDO_FONTE (e marca como INCONSISTENTE um registro já conferido)
  ATTENTION — informa, não impede
"""

from __future__ import annotations

import re
from typing import Any

from backend.app import units
from backend.app.quantities import clean_text, fmt_number
from backend.app.semantic import _NUM, _value_re

_DIM_TOKENS = {
    "temperature": "temperature", "angle": "angle", "pressure": "pressure", "velocity": "velocity", "speed": "velocity",
    "time": "time", "duration": "time", "period": "time", "mass": "mass", "volume": "volume", "area": "area",
    "frequency": "frequency", "power": "power", "length": "length", "width": "length", "thickness": "length",
    "diameter": "length", "radius": "length", "height": "length", "depth": "length", "distance": "length",
    "wavelength": "length",
}
_DIMENSIONLESS = {"index", "ratio", "coefficient", "factor", "count", "number", "faces"}
_IDENTIFIER = {"code", "id", "identifier", "serial"}
_UNREADABLE_SYMBOLS = "*~¬�"  # o que a camada de texto (OCR) costuma devolver no lugar de "°"

SEV_BLOCKING, SEV_ATTENTION = "BLOCKING", "ATTENTION"


def _tokens(name: str | None) -> set[str]:
    return set(re.findall(r"[a-z]+", (name or "").lower().replace("_", " ")))


def expected_dimension(parameter: str) -> str | None:
    """Dimensão que o NOME do parâmetro implica (ex.: contact_angle → angle). None se não há ou é ambígua."""
    toks = _tokens(parameter)
    dims = {_DIM_TOKENS[t] for t in toks if t in _DIM_TOKENS}
    if len(dims) == 1:
        return dims.pop()
    if not dims and toks & (_DIMENSIONLESS | _IDENTIFIER):
        return "dimensionless"
    return None


def is_identifier(parameter: str) -> bool:
    return bool(_tokens(parameter) & _IDENTIFIER)


# ---------------------------------------------------------------- unidade lida do texto
_SKIP = re.compile(rf"^\s*(?:,|;|\band\b|\bor\b|\bto\b|\bthrough\b|–|—)\s*(?:even\s+)?{_NUM}\b")
_UNIT_PATTERNS = [
    re.compile(r"^\s*(°\s?[CFKcfk])(?![A-Za-z])"), re.compile(r"^\s*(º\s?[CFKcfk])(?![A-Za-z])"),
    re.compile(r"^\s*(deg(?:rees?)?\s+[CFKcfk])(?![A-Za-z])", re.I), re.compile(r"^\s*(°|º|˚)"),
    re.compile(r"^\s*(deg(?:rees?)?)(?![A-Za-z])", re.I),
    re.compile(r"^\s*([A-Za-zµμ%]+(?:\s?/\s?[A-Za-z]+)?[²³]?)", re.I),
]


def _read_unit(after: str) -> tuple[str | None, str | None, int]:
    """(texto da unidade, canônica, posição do fim) logo no início de `after`; (None, None, 0) se nada reconhecível."""
    for pat in _UNIT_PATTERNS:
        m = pat.match(after)
        if m:
            canon = units.canonical_unit(m.group(1).strip())
            if canon is not None and canon != "adimensional":
                return m.group(1).strip(), canon, m.end(1)
    return None, None, 0


def unit_in_quotes(value: float, canon: str, quotes: list[str]) -> dict[str, Any]:
    """O trecho sustenta a unidade `canon` ao lado do valor (inclusive unidade compartilhada em intervalo/lista)?"""
    vre = re.compile(_value_re(value))
    saw_value = garbled = False
    for raw in quotes:
        q = clean_text(raw)
        for m in vre.finditer(q):
            saw_value = True
            pos = m.end()
            for _ in range(7):
                after = q[pos: pos + 40]
                text, found, _end = _read_unit(after)
                if found == canon:
                    return {"source": "QUOTE", "matched": f"{fmt_number(value)} {text}", "value_found": True}
                if after.lstrip()[:1] and after.lstrip()[0] in _UNREADABLE_SYMBOLS:
                    garbled = True
                    break
                skip = _SKIP.match(after)
                if not skip:
                    break
                pos += skip.end()
    if garbled:
        return {"source": "SYMBOL_UNREADABLE", "matched": None, "value_found": True}
    return {"source": "NOT_FOUND", "matched": None, "value_found": saw_value}


def condition_candidates(value: float, quotes: list[str]) -> list[dict[str, Any]]:
    """Condições de referência citadas logo após o valor: "70 ° AT 20 °C" → condição 20 °C."""
    vre = re.compile(_value_re(value))
    out: list[dict[str, Any]] = []
    for raw in quotes:
        q = clean_text(raw)
        for m in vre.finditer(q):
            _text, _canon, end = _read_unit(q[m.end(): m.end() + 40])
            tail = q[m.end() + end: m.end() + end + 60]
            c = re.match(rf"^\s*(?:\([^)]{{1,12}}\)\s*)?((?:at|@|under|for)\s+({_NUM})\s*(°\s?[CFK]\b|[A-Za-z%]{{1,4}})?)", tail, re.I)
            if c:
                num = float(c.group(2).replace(",", "."))
                unit = (c.group(3) or "").strip() or None
                canon = units.canonical_unit(unit) if unit else None
                cand = {"text": c.group(1).strip(), "value": num, "unit": unit, "dimension": units.dimension_of(canon) if canon else None}
                if cand not in out:
                    out.append(cand)
    return out


# ---------------------------------------------------------------- avaliação
def _finding(code: str, severity: str, field: str, title: str, detail: str, terms: list[str] | None = None) -> dict[str, Any]:
    return {"code": code, "severity": severity, "field": field, "title_pt": title, "detail_pt": detail, "terms": terms or []}


def unit_info(parameter: str, original: dict[str, Any] | None) -> dict[str, Any]:
    """Estado da unidade — leituras DISTINTAS para o que antes aparecia tudo como "—"."""
    o = original or {}
    value, raw = o.get("value"), o.get("unit")
    expected = expected_dimension(parameter)
    base = {"raw": raw, "canonical": None, "display": None, "dimension": None, "dimension_pt": None, "supported": True,
            "has_unit": False, "expected_dimension": expected,
            "expected_dimension_pt": units.DIMENSION_PT.get(expected) if expected else None}
    if value is None or isinstance(value, str):
        return {**base, "state": "NOT_APPLICABLE"}  # valor textual: unidade não se aplica
    canon = units.canonical_unit(raw) if raw is not None else "adimensional"
    if canon is None:
        return {**base, "state": "UNSUPPORTED", "supported": False}
    if canon == "adimensional":
        explicit = units.unit_key(raw) in {"adimensional", "dimensionless", "sem unidade", "1"}
        dimensionless = expected == "dimensionless" or (expected is None and explicit)
        return {**base, "state": "DIMENSIONLESS" if dimensionless else "MISSING"}
    dim = units.dimension_of(canon)
    return {**base, "state": "PHYSICAL", "canonical": canon, "display": units.display_unit(canon), "has_unit": True,
            "dimension": dim, "dimension_pt": units.DIMENSION_PT.get(dim)}


def assess(*, parameter: str, role: str, original: dict[str, Any] | None, quotes: list[str], method: str | None,
           condition: dict[str, Any] | None, review: dict[str, Any] | None) -> dict[str, Any]:
    """Integridade do parâmetro: estado da unidade, localização do valor no PDF, condição e achados."""
    info = unit_info(parameter, original)
    value = (original or {}).get("value")
    findings: list[dict[str, Any]] = []
    out: dict[str, Any] = {"unit_info": info, "condition_candidates": [], "pdf_value": {"found": None, "literal": None}}
    numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
    text_check = method == "LLM"  # citações de texto livre; tabelas curadas trazem a unidade no cabeçalho da coluna

    if numeric:
        vre = re.compile(_value_re(float(value)))
        hit = next((m for q in quotes for m in [vre.search(clean_text(q))] if m), None)
        out["pdf_value"] = {"found": bool(hit) if quotes else None, "literal": hit.group(0) if hit else None}
        if quotes and not hit and text_check:
            findings.append(_finding("VALUE_NOT_IN_QUOTE", SEV_BLOCKING, "value", "O valor não aparece literalmente no trecho",
                                     f"O número {fmt_number(float(value))} não foi localizado no texto citado."))

    if info["state"] == "MISSING":
        known_quantity = info["expected_dimension"] is not None
        findings.append(_finding(
            "UNIT_MISSING_FOR_QUANTITY" if known_quantity else "UNIT_UNCLASSIFIED",
            SEV_BLOCKING if known_quantity else SEV_ATTENTION, "unit", "Grandeza física sem unidade" if known_quantity else "Unidade ausente; grandeza não classificada",
            (f"O nome do parâmetro indica {info['expected_dimension_pt']}, mas o registro não tem unidade. "
             "Não é adimensional por si: a unidade precisa vir da fonte.") if known_quantity else
            "Sem unidade explícita e sem dimensão reconhecida no nome, não é possível concluir que o valor é adimensional.",
            [fmt_number(float(value))]))
    elif info["state"] == "UNSUPPORTED":
        findings.append(_finding("UNIT_UNSUPPORTED", SEV_BLOCKING, "unit", "Unidade fora da tabela de unidades",
                                 f"A unidade “{info['raw']}” não é suportada: a conferência automática e a conversão não são possíveis."))
    elif info["state"] == "PHYSICAL":
        exp = info["expected_dimension"]
        if exp and exp != info["dimension"]:
            findings.append(_finding(
                "UNIT_DIMENSION_MISMATCH", SEV_BLOCKING, "unit", "A unidade mede outra grandeza",
                f"O nome do parâmetro indica {info['expected_dimension_pt']}, mas a unidade {info['display']} é "
                f"{info['dimension_pt']}.", [info["display"] or ""]))
        if text_check and quotes and numeric:
            ev = unit_in_quotes(float(value), info["canonical"], quotes)
            out["unit_source"] = ev["source"]
            if ev["source"] == "SYMBOL_UNREADABLE":
                human_ok = bool((review or {}).get("components", {}).get("unit_verified_in_pdf"))
                if not human_ok:
                    findings.append(_finding(
                        "UNIT_SYMBOL_UNREADABLE", SEV_BLOCKING, "unit", "A unidade não é legível na camada de texto",
                        f"Depois do número aparece um símbolo ilegível (por exemplo “*”) no lugar da unidade; a IA assumiu "
                        f"{info['display']}. É preciso ver o PDF e confirmar a unidade explicitamente.", ["*"]))
            elif ev["source"] == "NOT_FOUND":
                findings.append(_finding(
                    "UNIT_NOT_IN_EVIDENCE", SEV_BLOCKING, "unit", "A unidade não aparece no trecho",
                    f"A unidade {info['display']} não está ao lado do valor no texto citado; pode ter sido inferida pela IA. "
                    "Não se inventa unidade: corrija a extração ou confirme-a no PDF.", [info["display"] or ""]))
        elif not text_check:
            out["unit_source"] = "NOT_CHECKED"
    if numeric and quotes:
        cands = condition_candidates(float(value), quotes)
        out["condition_candidates"] = cands
        relevant = [c for c in cands if c["dimension"] != expected_dimension(parameter)]
        if relevant and not condition:
            c = relevant[0]
            findings.append(_finding(
                "CONDITION_NOT_RECORDED", SEV_BLOCKING, "condition", "O valor depende de uma condição que não foi registrada",
                f"O trecho associa o valor a “{c['text']}”. Sem registrar a condição, o parâmetro pode ser lido como valor geral. "
                "Use “Corrigir extração” para registrar a condição.", [c["text"]]))
        elif relevant:
            cv = condition.get("value")
            recorded = units.normalize(float(cv), condition.get("unit")) if isinstance(cv, (int, float)) and not isinstance(cv, bool) else None
            matches = any(recorded is not None and (candidate := units.normalize(c["value"], c["unit"])) is not None
                          and units.same_quantity(recorded, candidate) for c in relevant)
            if not matches:
                findings.append(_finding(
                    "CONDITION_MISMATCH", SEV_BLOCKING, "condition", "A condição registrada diverge da fonte",
                    "A condição deve preservar o valor e a unidade associados ao parâmetro no trecho citado. "
                    "Preencher apenas um texto ou uma condição diferente não resolve a lacuna.", [c["text"] for c in relevant]))
    if numeric and is_identifier(parameter):
        findings.append(_finding("IDENTIFIER_AS_NUMBER", SEV_ATTENTION, "value", "Identificador guardado como número",
                                 "Códigos e identificadores devem ser textos; como número podem perder zeros à esquerda e não têm unidade."))
    blocking = [f for f in findings if f["severity"] == SEV_BLOCKING]
    out["findings"] = findings
    out["status"] = "INCONSISTENT" if blocking else "ATTENTION" if findings else "OK"
    return out
