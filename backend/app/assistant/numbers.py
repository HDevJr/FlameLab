"""Extração determinística de números científicos em texto PT/EN (apoio ao V2).

Reconhece: "0,071", "0.071", "1.234,5", "7,1×10⁻⁵", "7.1e-5", "7,1 x 10^-5",
com unidade opcional logo após o número ("9 cm/s", "22,2 %", "6,4 min").

Não são tratados como números científicos (mascarados antes da extração):
- identificadores com letras e dígitos: M1, BASS2-M1, TEST-01, PSI-25, O2, EV-…;
- referências documentais: "Tabela 5.1", "seção 5.3", "Figura 3", "página 57", "p. 12";
- versões no formato x.y.z (ex.: 6.11.1).

Ambiguidade (ex.: "1,000" ou "1.000": decimal ou milhar?) é marcada e o
verificador BLOQUEIA a afirmação, em vez de escolher uma interpretação.
Limitação conhecida: números por extenso ("uma face", "nove") não são detectados.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from backend.app.units import canonical_unit

_SUPERSCRIPT = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")

_REF_WORDS = (
    r"tabela|tabelas|table|tables|tab\.|se[cç][aã]o|se[cç][oõ]es|section|sections|sec\.|§|"
    r"figura|figuras|figure|figures|fig\.|p[aá]gina|p[aá]ginas|page|pages|pp?\.|"
    r"cap[ií]tulo|chapter|ap[eê]ndice|appendix|ref\.|refer[eê]ncia|equa[cç][aã]o|equation|eq\."
)
_REF_RE = re.compile(
    rf"(?i)(?:{_REF_WORDS})\s*(?:pdf\s*|impressa\s*|n[ºo°.]\s*)?\d+(?:[.,]\d+)*(?:\s*[-–]\s*\d+(?:[.,]\d+)*)?"
)
_VERSION_RE = re.compile(r"\b\d+\.\d+\.\d+(?:\.\d+)*\b")
# token iniciado por letra e contendo dígito (com - _ / internos): M1, BASS2-M1, TEST-01, O2
_IDENT_RE = re.compile(r"(?<![\w.,])[A-Za-z][A-Za-z0-9]*(?:[-_/][A-Za-z0-9]+)*")

_UNIT_ALTS = sorted(
    [
        "mm/s", "cm/s", "m/s", "mm s-1", "cm s-1", "m s-1", "mm s⁻¹", "cm s⁻¹", "m s⁻¹",
        "milímetros", "milímetro", "milimetros", "milimetro", "millimeters", "millimeter",
        "centímetros", "centímetro", "centimetros", "centimetro", "centimeters", "centimeter",
        "metros", "metro", "meters", "meter",
        "minutos", "minuto", "minutes", "minute", "min",
        "segundos", "segundo", "seconds", "second", "sec", "seg",
        "vol%", "vol.%", "% vol.", "% vol", "%vol", "%", "por cento", "percent",
        "mm", "cm", "m", "s",
        # Unidades reconhecidas mas fora da tabela v1: só casam por igualdade literal.
        "°C", "ºC", "K", "atm", "kPa", "Pa", "bar", "psi", "kW/m²", "kW/m2", "kW", "W", "kg", "g", "mg",
        "mm²", "cm²", "m²", "mm2", "cm2", "m2", "L", "mL", "ppm",
    ],
    key=len,
    reverse=True,
)
_UNIT_PATTERN = "|".join(re.escape(u) for u in _UNIT_ALTS)

_NUMBER_RE = re.compile(
    r"(?<![\w.,])"
    r"(?P<sign>[-−])?"
    r"(?P<mant>\d+(?:[.,]\d+)*)"
    r"(?:\s*[×x*]\s*10\s*(?:\^|\*\*)?\s*(?P<exp>[-−⁻+⁺]?[0-9⁰¹²³⁴⁵⁶⁷⁸⁹]+)|[eE](?P<eexp>[-+]?\d+))?"
    rf"(?:\s?(?P<unit>{_UNIT_PATTERN})(?![A-Za-zÀ-ÿ0-9]))?"
)


@dataclass(frozen=True)
class NumberMention:
    raw: str
    value: float | None  # None quando ambíguo
    unit_raw: str | None
    unit: str | None  # canônica (tabela v1) ou None se desconhecida/ausente
    ambiguous: bool
    start: int
    end: int


def _mask(text: str) -> str:
    chars = list(text)
    for regex in (_REF_RE, _VERSION_RE):
        for m in regex.finditer(text):
            chars[m.start() : m.end()] = " " * (m.end() - m.start())
    masked = "".join(chars)
    chars = list(masked)
    for m in _IDENT_RE.finditer(masked):
        if any(c.isdigit() for c in m.group(0)):
            chars[m.start() : m.end()] = " " * (m.end() - m.start())
    return "".join(chars)


def _parse_mantissa(mant: str) -> tuple[float | None, bool]:
    """Converte a mantissa considerando vírgula/ponto. Retorna (valor, ambíguo)."""
    has_comma, has_dot = "," in mant, "." in mant
    if has_comma and has_dot:
        # o último separador é o decimal: 1.234,5 (PT) ou 1,234.5 (EN)
        dec = "," if mant.rfind(",") > mant.rfind(".") else "."
        thou = "." if dec == "," else ","
        int_part, _, frac = mant.rpartition(dec)
        groups = int_part.split(thou)
        if not all(len(g) == 3 for g in groups[1:]):
            return None, True
        return float("".join(groups) + "." + frac), False
    sep = "," if has_comma else "." if has_dot else None
    if sep is None:
        return float(mant), False
    parts = mant.split(sep)
    if len(parts) > 2:
        # 1.000.000 → milhar (somente se grupos de 3)
        if all(len(p) == 3 for p in parts[1:]):
            return float("".join(parts)), False
        return None, True
    int_part, frac = parts
    if len(frac) == 3 and int_part != "0" and not int_part.startswith("0"):
        # "1,000" / "1.000": pode ser decimal ou milhar → ambíguo
        return None, True
    return float(int_part + "." + frac), False


def extract_numbers(text: str) -> list[NumberMention]:
    masked = _mask(text)
    mentions: list[NumberMention] = []
    for m in _NUMBER_RE.finditer(masked):
        mant = m.group("mant")
        value, ambiguous = _parse_mantissa(mant)
        exp = m.group("exp") or m.group("eexp")
        if value is not None and exp is not None:
            exp_norm = exp.translate(_SUPERSCRIPT).replace("−", "-")
            try:
                value = value * (10 ** int(exp_norm))
            except ValueError:
                value, ambiguous = None, True
        if value is not None and m.group("sign"):
            value = -value
        unit_raw = m.group("unit")
        unit = canonical_unit(unit_raw) if unit_raw else None
        mentions.append(
            NumberMention(
                raw=text[m.start() : m.end()],
                value=value,
                unit_raw=unit_raw,
                unit=unit,
                ambiguous=ambiguous,
                start=m.start(),
                end=m.end(),
            )
        )
    return mentions
