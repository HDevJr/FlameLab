"""Comparação determinística e explicável entre um artigo e registros de fontes NASA.

Nada aqui conhece um documento específico: só títulos, autores e identificadores.
"""

from __future__ import annotations

import difflib
import re
import unicodedata

_STOP = frozenset("the of and in for a an on to with from at by".split())
_GENERIC = frozenset("summary report final technical memorandum".split())

TITLE_STRONG = 0.85  # semelhança mínima de título para um candidato
TITLE_COHERENT = 0.5  # coerência mínima quando há identificador forte


def _ascii(text: str) -> str:
    text = re.sub(r"[‐-―−]", "-", text)
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def title_tokens(*titles: str | None) -> frozenset[str]:
    out: set[str] = set()
    for title in titles:
        if not title:
            continue
        for raw in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", _ascii(title).lower()):
            # "solids-ii" → {"solids", "ii"}; siglas compostas também ficam inteiras
            parts = raw.split("-")
            for tok in ([raw] if len(parts) > 1 else []) + parts:
                if tok and tok not in _STOP and tok not in _GENERIC:
                    out.add(tok)
    return frozenset(out)


def title_similarity(a: frozenset[str], b: frozenset[str]) -> float:
    """Jaccard sobre palavras distintivas, ignorando formas compostas ausentes de um dos lados."""
    if not a or not b:
        return 0.0
    simple_a = {t for t in a if "-" not in t}
    simple_b = {t for t in b if "-" not in t}
    inter = len(simple_a & simple_b)
    union = len(simple_a | simple_b)
    return round(inter / union, 3) if union else 0.0


def surname(name: str) -> str:
    name = _ascii(name).strip()
    base = name.split(",")[0] if "," in name else (name.split()[-1] if name.split() else "")
    return re.sub(r"[^a-z]", "", base.lower())


def author_overlap(a: list[str], b: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
    """Devolve (sobrenomes em comum, pares quase iguais — possível erro de grafia)."""
    sa = {surname(x) for x in a} - {""}
    sb = {surname(x) for x in b} - {""}
    shared = sorted(sa & sb)
    near = []
    for x in sorted(sa - sb):
        for y in sorted(sb - sa):
            if difflib.SequenceMatcher(None, x, y).ratio() >= 0.85:
                near.append((x, y))
    return shared, near


def key_words(title: str | None, n: int) -> list[str]:
    """Primeiras `n` palavras distintivas do título, na ordem em que aparecem (para consultas)."""
    out: list[str] = []
    for tok in re.findall(r"[a-z]+", _ascii(title or "").lower()):
        if len(tok) > 3 and tok not in _STOP and tok not in _GENERIC and tok not in out:
            out.append(tok)
    return out[:n]
