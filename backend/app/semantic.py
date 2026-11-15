"""Verificação SEMÂNTICA de um parâmetro: o trecho sustenta o CONCEITO atribuído ao número?

Uma correspondência numérica não basta. Exemplo real (15/11/2026): `initial_temperature = 20 °C` com o
trecho "The temperature was then cycled from 20 to 80 °C in increments of 20 °C" — o número 20 está
no texto, mas como INÍCIO DE UM INTERVALO/CICLO (e também como incremento), não como "temperatura
inicial" afirmada pela fonte.

Regras determinísticas (sem IA, sem inventar contexto):
- INITIAL_FROM_RANGE / FINAL_FROM_RANGE / ENDPOINT_MISMATCH (BLOQUEIAM a confirmação)
- INCREMENT_AS_ABSOLUTE (BLOQUEIA): o número é um incremento (diferença), não um valor absoluto
- VALUE_ALSO_INCREMENT, VALUE_FROM_LIST, MULTIPLE_VALUES_IN_QUOTE, APPROXIMATE_VALUE (informativas)

Sinalizar não é decidir: a pessoa corrige a extração ou mantém pendente. Nenhuma sinalização promove
ou rebaixa um registro automaticamente.
"""

from __future__ import annotations

import re
from typing import Any

from backend.app import units
from backend.app.quantities import clean_text, fmt_number

_NUM = r"\d+(?:[.,]\d+)?"
_UNIT_AFTER = r"(?:\s*(?:°\s?[CFK]?|%|[A-Za-z]{1,4}(?:/[A-Za-z]{1,3})?))?"
_LOW = {"initial", "initially", "start", "starting", "begin", "beginning", "baseline", "inicial", "inicio", "início", "min", "minimum", "lower", "minimo", "mínimo"}
_HIGH = {"final", "end", "ending", "peak", "max", "maximum", "upper", "top", "maximo", "máximo", "pico"}
_INC_LABEL = {"increment", "increments", "step", "steps", "delta", "interval", "incremento", "passo", "variacao", "variação", "diff", "difference"}
_CONFIRM_LOW = re.compile(r"(?i)\b(initial(?:ly)?|start(?:ed|ing)?|began|begin(?:ning)?|baseline|at the start|at t\s?=\s?0)\b")
_CONFIRM_HIGH = re.compile(r"(?i)\b(final(?:ly)?|peak|maximum|max|reached|achieved|up to|end(?:ed)?)\b")
_APPROX = re.compile(r"(?i)\b(approximately|approx\.?|about|around|roughly|nearly|circa)\b|~")


def _value_re(v: float) -> str:
    if float(v).is_integer():
        n = int(v)
        body = rf"{n}(?:[.,]0+)?"
    else:
        body = re.escape(fmt_number(v)).replace(r"\.", r"[.,]")
    return rf"(?<![\d.,]){body}(?![\d]|[.,]\d)"


def _ranges(text: str) -> list[tuple[float, float]]:
    out = []
    for m in re.finditer(rf"(?P<lo>{_NUM}){_UNIT_AFTER}\s*(?:to|and|through|–|—)\s*(?P<hi>{_NUM})", text):
        try:
            out.append((float(m.group("lo").replace(",", ".")), float(m.group("hi").replace(",", "."))))
        except ValueError:
            continue
    return out


def _tokens(*names: str) -> set[str]:
    out: set[str] = set()
    for n in names:
        out |= set(re.findall(r"[a-zà-ÿ]+", (n or "").lower().replace("_", " ")))
    return out


def semantic_flags(*, parameter: str, label: str | None, value: Any, unit: str | None,
                   quotes: list[str], method: str | None = None, label_source: str | None = None) -> list[dict[str, Any]]:
    """Sinalizações semânticas do parâmetro frente às suas citações. `value` numérico; texto → [].
    Se o rótulo foi definido por uma pessoa (`label_source="HUMANO"`), só ele conta: o nome técnico original
    da IA deixa de influenciar a interpretação."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return []
    v = float(value)
    toks = _tokens("" if label_source == "HUMANO" else parameter, label or "")
    flags: dict[str, dict[str, Any]] = {}

    def add(code: str, severity: str, title: str, detail: str, terms: list[str]) -> None:
        if code not in flags:
            flags[code] = {"code": code, "severity": severity, "title_pt": title, "detail_pt": detail, "terms": terms}

    vre = re.compile(_value_re(v))
    for raw in quotes:
        q = clean_text(raw)
        if not q or not vre.search(q):
            continue
        rngs = [r for r in _ranges(q) if r[0] != r[1]]
        as_lo = [r for r in rngs if math_eq(r[0], v)]
        as_hi = [r for r in rngs if math_eq(r[1], v)]
        rng_text = lambda r: f"{fmt_number(r[0])} a {fmt_number(r[1])}"  # noqa: E731
        is_inc = bool(re.search(rf"(?i)\b(?:increments?|steps?|step size|intervals?)\s+of\s+(?:about\s+)?{_value_re(v)}", q)
                      or re.search(rf"(?i){_value_re(v)}{_UNIT_AFTER}\s+(?:increments?|steps?)\b", q))
        low_label, high_label = bool(toks & _LOW), bool(toks & _HIGH)

        if low_label and as_lo and not _CONFIRM_LOW.search(q):
            add("INITIAL_FROM_RANGE", "BLOCKING", "O trecho não afirma um valor inicial",
                f"O número {fmt_number(v)} aparece como início do intervalo {rng_text(as_lo[0])}, não como condição inicial "
                "declarada pela fonte. Um ciclo ou variação que começa em um valor não prova que o experimento partiu dele.",
                [fmt_number(v), "from", "to", "cycled"])
        if high_label and as_hi and not _CONFIRM_HIGH.search(q):
            add("FINAL_FROM_RANGE", "BLOCKING", "O trecho não afirma um valor final ou máximo",
                f"O número {fmt_number(v)} é o limite superior do intervalo {rng_text(as_hi[0])}; o trecho não diz que foi o "
                "valor final, máximo ou alcançado.", [fmt_number(v), "to"])
        if (low_label and as_hi and not as_lo) or (high_label and as_lo and not as_hi):
            add("ENDPOINT_MISMATCH", "BLOCKING", "O número está na extremidade oposta do intervalo",
                f"O parâmetro sugere {'início/mínimo' if low_label else 'fim/máximo'}, mas {fmt_number(v)} é a outra extremidade "
                f"do intervalo {rng_text((as_hi or as_lo)[0])}.", [fmt_number(v)])
        if is_inc and not (toks & _INC_LABEL):
            if rngs and (as_lo or as_hi):
                add("VALUE_ALSO_INCREMENT", "INFO", "O mesmo número também aparece como incremento",
                    f"{fmt_number(v)} aparece como extremidade de intervalo e como incremento (diferença) no mesmo trecho; "
                    "confirme a qual dos dois o parâmetro se refere.", [fmt_number(v), "increments"])
            else:
                add("INCREMENT_AS_ABSOLUTE", "BLOCKING", "O número é um incremento, não um valor absoluto",
                    f"No trecho, {fmt_number(v)} é o tamanho de um passo/incremento (uma diferença), não um valor absoluto "
                    "da grandeza.", [fmt_number(v), "increments", "steps"])
        listed = _list_members(q)
        if listed and any(math_eq(x, v) for x in listed) and len(listed) >= 3:
            add("VALUE_FROM_LIST", "INFO", "O número é um dos elementos de uma lista",
                f"{fmt_number(v)} é um entre vários valores listados ({', '.join(fmt_number(x) for x in listed)}); "
                "confirme que o parâmetro se refere a este elemento e não ao conjunto.", [fmt_number(x) for x in listed])
        if method == "LLM":
            others = _other_values(q, v)
            if others:
                add("MULTIPLE_VALUES_IN_QUOTE", "INFO", "O trecho cita outros valores",
                    "O trecho também menciona " + ", ".join(others) + ". Confirme que " + fmt_number(v) + " é o valor do parâmetro e "
                    "não de outra condição.", [fmt_number(v)] + [o.split()[0] for o in others])
        if _APPROX.search(q):
            add("APPROXIMATE_VALUE", "INFO", "O texto indica valor aproximado",
                "O trecho usa um termo como “aproximadamente”: o valor não é exato.", ["approximately", "about"])
    return list(flags.values())


def _list_members(q: str) -> list[float]:
    """Valores de uma lista "40, 60, 80, 90 and even 95 °C" (três ou mais números separados por vírgula/and/or)."""
    m = re.search(rf"{_NUM}(?:\s*,\s*{_NUM}){{1,}}(?:\s*,?\s*(?:and|or|e|ou)\s+(?:even\s+)?{_NUM})?", q)
    if not m:
        return []
    vals = []
    for t in re.findall(_NUM, m.group(0)):
        try:
            vals.append(float(t.replace(",", ".")))
        except ValueError:
            pass
    return vals


def math_eq(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


def _other_values(q: str, v: float) -> list[str]:
    seen: list[str] = []
    for m in re.finditer(rf"(?P<n>{_NUM})(?P<u>\s*(?:°\s?[CFK]?|%|[A-Za-z]{{1,4}}(?:/[A-Za-z]{{1,3}})?))?", q):
        u = (m.group("u") or "").strip()
        if not u or units.canonical_unit(u) in (None, "adimensional"):
            continue
        try:
            n = float(m.group("n").replace(",", "."))
        except ValueError:
            continue
        if math_eq(n, v):
            continue
        text = f"{fmt_number(n)} {u}"
        if text not in seen:
            seen.append(text)
    return seen[:5]


def blocking(flags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [f for f in flags if f["severity"] == "BLOCKING"]
