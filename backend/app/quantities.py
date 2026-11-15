"""Parsing seguro de valores e comparação ESTRUTURADA, campo a campo, para a revisão humana.

Princípios (correção do VALUE_MISMATCH de 15/11/2026):
- Valor e unidade são campos separados. Se o revisor digitar "20.0 °C" no campo de valor, o número
  e a unidade são separados explicitamente (e isso é declarado no diagnóstico), nunca descartados.
- "20", "20.0" e "20,0" são o mesmo número. Formatos ambíguos ("1,234", "1.234,5", "20 to 80") não
  são adivinhados: são recusados como ambíguos.
- Igualdade física é decidida pela tabela de unidades (dimensão + conversão, com deslocamento para
  temperatura), nunca por comparação de texto de unidade.
- Unidade não suportada ⇒ erro específico (UNIT_UNSUPPORTED), sem conversão improvisada.
- Toda recusa diz QUAL campo falhou (valor, unidade ou página) e por quê.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from backend.app import units

_NUM = r"[+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+)(?:[eE][+-]?\d+)?"
_FULL = re.compile(rf"^(?P<num>{_NUM})(?:\s*(?P<rest>.*))?$", re.S)
_OK = frozenset({"MATCH", "CONVERTIBLE", "NOT_APPLICABLE"})


def clean_text(raw: str | None) -> str:
    """NFKC, espaços especiais → espaço, menos Unicode → '-', espaços colapsados."""
    if raw is None:
        return ""
    return " ".join(units.pre_normalize(raw).split())


def fmt_number(v: float | int | None) -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e15:
        return str(int(v))
    return format(v, ".12g")


@dataclass
class ParsedValue:
    status: str  # OK | EMPTY | UNREADABLE | AMBIGUOUS
    value: float | None = None
    embedded_unit: str | None = None
    detail_pt: str | None = None


def _to_float(num: str) -> tuple[float | None, str | None]:
    mant = re.split(r"[eE]", num, maxsplit=1)[0]
    if "," in mant and "." in mant:
        return None, "contém vírgula e ponto (milhar ou decimal?)"
    if mant.count(",") > 1 or mant.count(".") > 1:
        return None, "contém mais de um separador (milhar ou decimal?)"
    if "," in mant:
        ip, fp = mant.lstrip("+-").split(",", 1)
        if len(fp) == 3 and ip not in ("", "0") and len(ip) <= 3:
            return None, "a vírgula pode ser separador de milhar ou decimal (ex.: 1,234)"
        num = num.replace(",", ".")
    try:
        v = float(num)
    except ValueError:
        return None, "não é um número"
    return (v, None) if math.isfinite(v) else (None, "valor fora do intervalo numérico")


def parse_value_input(raw: str | None) -> ParsedValue:
    s = clean_text(raw)
    if not s:
        return ParsedValue("EMPTY", detail_pt="nenhum valor informado")
    m = _FULL.match(s)
    if not m:
        return ParsedValue("UNREADABLE", detail_pt="não foi possível ler um número (digite apenas o número no campo de valor)")
    value, problem = _to_float(m.group("num"))
    if value is None:
        return ParsedValue("AMBIGUOUS" if problem and "mil" in problem else "UNREADABLE", detail_pt=problem)
    rest = (m.group("rest") or "").strip()
    if not rest:
        return ParsedValue("OK", value)
    if re.match(r"^[.,]\d", rest):  # "1.234,5", "1,2,3": mais de um separador
        return ParsedValue("AMBIGUOUS", detail_pt="contém mais de um separador (milhar ou decimal?)")
    if units.canonical_unit(rest) is None and re.search(r"(?:^|[\s(–-])\d", rest):
        return ParsedValue("AMBIGUOUS", detail_pt=f"o campo contém mais de um número ({s!r}); informe um único valor")
    return ParsedValue("OK", value, embedded_unit=rest)


def _row(field: str, expected: Any, received: Any, status: str, detail: str | None = None, **extra: Any) -> dict[str, Any]:
    return {"field": field, "label_pt": {"value": "Valor", "unit": "Unidade", "page": "Página"}[field],
            "expected": expected, "received": received, "status": status, "detail_pt": detail, **extra}


def _norm_text(t: str | None) -> str:
    return clean_text(t).lower()


def compare_fields(*, original_value: Any, original_unit: str | None, evidence_pages: set,
                   observed_value: str | None, observed_unit: str | None,
                   observed_page: int | None) -> dict[str, Any]:
    """Compara o que o revisor informou com o registro. Devolve `accepted`, `code`, `message_pt`,
    `comparisons` (valor, unidade, página) — o backend é a autoridade final da aceitação."""
    pages = sorted(p for p in evidence_pages if p is not None)
    page_row = _page_row(pages, observed_page)

    if isinstance(original_value, str):  # texto (material, rótulo): sem unidade
        got = clean_text(observed_value)
        if not got:
            val = _row("value", original_value, None, "MISSING", "nenhum valor informado")
        elif _norm_text(got) in _norm_text(original_value):
            val = _row("value", original_value, got, "MATCH")
        else:
            val = _row("value", original_value, got, "MISMATCH", "o texto informado não consta no valor extraído")
        unit = _row("unit", None, clean_text(observed_unit) or None, "NOT_APPLICABLE", "valor textual, sem unidade")
        return _verdict([val, unit, page_row], original_value, original_unit, got, observed_unit)

    parsed = parse_value_input(observed_value)
    field_unit = clean_text(observed_unit) or None
    embedded = parsed.embedded_unit
    received_unit = field_unit or embedded
    from_value_field = bool(embedded) and not field_unit
    conflict = False
    if field_unit and embedded:
        a, b = units.canonical_unit(field_unit), units.canonical_unit(embedded)
        conflict = not (a is not None and a == b)

    exp_text = clean_text(original_unit) or None
    exp_canon = units.canonical_unit(original_unit) if original_unit is not None else "adimensional"
    exp_has_unit = exp_canon not in (None, "adimensional")
    recv_canon = units.canonical_unit(received_unit) if received_unit else None
    exp_disp = units.display_unit(exp_canon) if exp_canon and exp_canon != "adimensional" else (exp_text if exp_canon is None else None)

    # ---- unidade
    if exp_canon is None:
        unit = _row("unit", exp_text, received_unit, "UNSUPPORTED",
                    f"a unidade do registro ({exp_text}) não é suportada pela tabela de unidades; "
                    "a conferência automática não é possível")
    elif received_unit and recv_canon is None:
        unit = _row("unit", exp_disp, received_unit, "UNSUPPORTED",
                    f"a unidade informada ({received_unit}) não é suportada pela tabela de unidades")
    elif exp_has_unit and not received_unit:
        unit = _row("unit", exp_disp, None, "MISSING", f"o registro está em {exp_disp}; informe a unidade")
    elif not exp_has_unit and received_unit and recv_canon != "adimensional":
        unit = _row("unit", None, received_unit, "UNEXPECTED", "o registro não tem unidade, mas uma unidade foi informada")
    elif not exp_has_unit:
        unit = _row("unit", None, None, "MATCH", "sem unidade")
    else:
        d_exp, d_rec = units.dimension_of(exp_canon), units.dimension_of(recv_canon)
        recv_disp = units.display_unit(recv_canon)
        if d_exp != d_rec:
            unit = _row("unit", exp_disp, received_unit, "INCOMPATIBLE",
                        f"{exp_disp} é {units.DIMENSION_PT.get(d_exp, d_exp)}; {recv_disp} é "
                        f"{units.DIMENSION_PT.get(d_rec, d_rec)}: grandezas incompatíveis")
        elif exp_canon == recv_canon:
            unit = _row("unit", exp_disp, recv_disp, "MATCH",
                        "unidade lida do campo de valor" if from_value_field else None, from_value_field=from_value_field)
        else:
            unit = _row("unit", exp_disp, recv_disp, "CONVERTIBLE", f"{recv_disp} convertida para {exp_disp} na comparação")

    # ---- valor
    exp_val = float(original_value)
    if parsed.status == "EMPTY":
        val = _row("value", fmt_number(exp_val), None, "MISSING", parsed.detail_pt)
    elif conflict:
        val = _row("value", fmt_number(exp_val), clean_text(observed_value), "AMBIGUOUS",
                   f"a unidade do valor ({embedded}) difere da unidade do campo ({field_unit})")
    elif parsed.status != "OK":
        val = _row("value", fmt_number(exp_val), clean_text(observed_value), parsed.status, parsed.detail_pt)
    else:
        got = parsed.value
        both_known = unit["status"] in ("MATCH", "CONVERTIBLE")
        if both_known and exp_has_unit:
            qa, qb = units.normalize(exp_val, original_unit), units.normalize(got, received_unit)
            same = qa is not None and qb is not None and units.same_quantity(qa, qb, rel_tol=1e-9, abs_tol=1e-12)
            detail = None
            extra: dict[str, Any] = {}
            if qa and qb and (unit["status"] == "CONVERTIBLE" or qa.dimension == "temperature"):
                extra = {"expected_si": f"{fmt_number(qa.value)} {qa.unit}", "received_si": f"{fmt_number(qb.value)} {qb.unit}"}
                detail = f"na comparação: {extra['expected_si']} (registro) × {extra['received_si']} (informado)"
            val = _row("value", fmt_number(exp_val), fmt_number(got), "MATCH" if same else "MISMATCH",
                       detail if (same or detail) else None, **extra)
        else:
            same = math.isclose(exp_val, got, rel_tol=1e-9, abs_tol=1e-12)
            val = _row("value", fmt_number(exp_val), fmt_number(got), "MATCH" if same else "MISMATCH",
                       None if same else "valores numéricos diferentes")
            if unit["status"] in ("MISSING", "INCOMPATIBLE", "UNSUPPORTED", "UNEXPECTED"):
                val["detail_pt"] = (f"o número {'coincide' if same else 'também difere'}, mas a unidade impede a conferência")
    return _verdict([val, unit, page_row], original_value, original_unit, observed_value, observed_unit)


def _page_row(pages: list[int], observed: int | None) -> dict[str, Any]:
    expected = ", ".join(str(p) for p in pages)
    if observed is None:
        return _row("page", expected, None, "MISSING", "nenhuma página informada")
    if observed in pages:
        return _row("page", expected, observed, "MATCH")
    return _row("page", expected, observed, "MISMATCH", f"a página {observed} não corresponde a nenhuma evidência do registro ({expected})")


_CODE = {  # (campo, status) -> código; a ordem de _PRIORITY define qual aparece primeiro
    ("value", "UNREADABLE"): "VALUE_UNREADABLE", ("value", "AMBIGUOUS"): "VALUE_AMBIGUOUS",
    ("value", "MISSING"): "OBSERVED_REQUIRED",
    ("unit", "UNSUPPORTED"): "UNIT_UNSUPPORTED", ("unit", "INCOMPATIBLE"): "UNIT_INCOMPATIBLE",
    ("unit", "MISSING"): "UNIT_MISSING", ("unit", "UNEXPECTED"): "UNIT_UNEXPECTED",
    ("value", "MISMATCH"): "VALUE_MISMATCH",
    ("page", "MISSING"): "OBSERVED_REQUIRED", ("page", "MISMATCH"): "PAGE_MISMATCH",
}
_PRIORITY = [("value", "UNREADABLE"), ("value", "AMBIGUOUS"), ("value", "MISSING"), ("unit", "UNSUPPORTED"),
             ("unit", "INCOMPATIBLE"), ("unit", "MISSING"), ("unit", "UNEXPECTED"), ("value", "MISMATCH"),
             ("page", "MISSING"), ("page", "MISMATCH")]


def _verdict(rows: list[dict[str, Any]], original_value, original_unit, observed_value, observed_unit) -> dict[str, Any]:
    failing = {(r["field"], r["status"]): r for r in rows if r["status"] not in _OK}
    for key in _PRIORITY:
        if key in failing:
            code, row = _CODE[key], failing[key]
            return {"accepted": False, "code": code, "message_pt": _message(code, row, rows),
                    "comparisons": rows, "failed_fields": sorted({k[0] for k in failing})}
    return {"accepted": True, "code": None, "message_pt": None, "comparisons": rows, "failed_fields": []}


def _message(code: str, row: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    by = {r["field"]: r for r in rows}
    if code == "VALUE_MISMATCH":
        u_rec = by["unit"]["received"] or ""
        u_exp = by["unit"]["expected"] or ""
        return (f"valor lido ({by['value']['received']} {u_rec}".rstrip() + f") diverge do registro "
                f"({by['value']['expected']} {u_exp}".rstrip() + "); registro NÃO promovido")
    if code == "PAGE_MISMATCH":
        return f"página do PDF informada ({by['page']['received']}) não corresponde a nenhuma evidência do registro ({by['page']['expected']})"
    if code == "OBSERVED_REQUIRED":
        return "informe o valor, a unidade e a página que você leu no PDF"
    prefix = {"UNIT_MISSING": "unidade ausente", "UNIT_INCOMPATIBLE": "unidade incompatível",
              "UNIT_UNSUPPORTED": "unidade não suportada", "UNIT_UNEXPECTED": "unidade inesperada",
              "VALUE_UNREADABLE": "valor ilegível", "VALUE_AMBIGUOUS": "valor ambíguo"}[code]
    return f"{prefix}: {row['detail_pt']}"
