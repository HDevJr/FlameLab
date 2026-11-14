"""Recuperação de evidências (planning/02 §8, passos 1–3) e análise da pergunta.

Elegibilidade (determinística, antes de qualquer pontuação):
- RECORD_CARD somente com estado CONFERIDO_FONTE e natureza OBSERVADO.
  EXTRAIDO_NAO_REVISADO, INFERIDO, CALCULADO e APROVADO_MODELO ficam FORA nesta fase.
- GAP (AUSENTE) é elegível para informar lacunas.
- PASSAGE é elegível como contexto qualitativo.
- Escopo: investigação e ensaios do pedido. Itens de outro ensaio nunca entram.

Pontuação: BM25 simples, implementado aqui (sem dependências), sobre texto + parâmetro.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Protocol

from backend.app.assistant.schemas import AskScope, EvidenceItem, EvidenceKind

TOP_K_PASSAGES = 6
MAX_ITEMS = 24
MIN_SCORE = 1e-9  # exige ao menos um termo em comum quando não há ensaio no escopo

_STOP = set(
    "a o as os de da do das dos e em no na nos nas um uma uns umas por para com sem que qual quais "
    "foi era sao são ser como sobre ao aos à às se sua seu suas seus este esta isso isto ou mais menos "
    "the of and in on at to for with is was were be what which a an by from as it this that or "
    "experimento ensaio experiment test teste".split()
)


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", _fold(text)) if t not in _STOP and (len(t) > 1 or t.isdigit())]


# ------------------------------------------------------------------ fonte de evidências
class EvidenceSource(Protocol):
    @property
    def dataset_version(self) -> str | None: ...

    def items(self) -> list[EvidenceItem]: ...

    def known_tests(self) -> dict[str, str]:
        """test_uid → rótulo curto (ex.: BASS2-M1 → M1)."""
        ...


class EmptyEvidenceSource:
    """Fonte padrão enquanto a curadoria BL-02 não existir: nenhuma evidência."""

    dataset_version = None

    def items(self) -> list[EvidenceItem]:
        return []

    def known_tests(self) -> dict[str, str]:
        return {}


class InMemoryEvidenceSource:
    """Contêiner genérico. Em execução normal só deve receber dados curados (BL-02);
    fixtures sintéticas são restritas a testes e ao smoke test, com `synthetic=True`."""

    def __init__(self, items: list[EvidenceItem]):
        ids = [i.evidence_id for i in items]
        if len(ids) != len(set(ids)):
            raise ValueError("evidence_id duplicado na fonte")
        self._items = list(items)
        canon = json.dumps([i.model_dump(mode="json") for i in items], sort_keys=True, ensure_ascii=False)
        self._version = "sha256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()

    @property
    def dataset_version(self) -> str | None:
        return self._version

    def items(self) -> list[EvidenceItem]:
        return list(self._items)

    def known_tests(self) -> dict[str, str]:
        return {i.test_uid: (i.test_label or i.test_uid) for i in self._items if i.test_uid}


# ------------------------------------------------------------------ análise da pergunta
_EXTRAPOLATION_PATTERNS: list[tuple[str, str]] = [
    ("MARTE", r"\bmarte\b|\bmarcian[oa]s?\b|\bmars\b|\bmartian\b"),
    ("LUA", r"\blua\b|\blunar(es)?\b|\bmoon\b"),
    ("GRAVIDADE_PARCIAL", r"gravidade (parcial|reduzida|fracionaria)|partial gravity|reduced gravity|hipogravidade"),
    ("OUTRO_CORPO_CELESTE", r"\bvenus\b|\btita\b|\btitan\b|\bjupiter\b|outro planeta|another planet|exoplaneta"),
]


def detect_extrapolation(question: str) -> list[str]:
    folded = _fold(question)
    return [flag for flag, pat in _EXTRAPOLATION_PATTERNS if re.search(pat, folded)]


# ------------------------------------------------------------------ recuperação
def _eligible(item: EvidenceItem) -> bool:
    if item.kind == EvidenceKind.RECORD_CARD:
        if item.value_withheld:
            # registro pendente: elegível só como AVISO de existência, sem valor (DIV-20)
            return not item.quantities and item.status == "EXTRAIDO_NAO_REVISADO"
        return item.status == "CONFERIDO_FONTE" and item.nature == "OBSERVADO"
    if item.kind == EvidenceKind.GAP:
        return item.status == "AUSENTE"
    return item.kind == EvidenceKind.PASSAGE


def _in_scope(item: EvidenceItem, scope: AskScope) -> bool:
    if scope.investigation_id and item.investigation_id not in (None, scope.investigation_id):
        return False
    if scope.test_uids:
        return item.test_uid is None or item.test_uid in scope.test_uids
    return True


def _bm25(query: list[str], docs: list[list[str]], k1: float = 1.5, b: float = 0.75) -> list[float]:
    if not docs:
        return []
    n = len(docs)
    avg = sum(len(d) for d in docs) / n or 1.0
    df: dict[str, int] = {}
    for d in docs:
        for t in set(d):
            df[t] = df.get(t, 0) + 1
    scores = []
    for d in docs:
        tf: dict[str, int] = {}
        for t in d:
            tf[t] = tf.get(t, 0) + 1
        s = 0.0
        for q in set(query):
            if q not in tf:
                continue
            idf = math.log(1 + (n - df[q] + 0.5) / (df[q] + 0.5))
            s += idf * tf[q] * (k1 + 1) / (tf[q] + k1 * (1 - b + b * len(d) / avg))
        scores.append(s)
    return scores


@dataclass
class RetrievalResult:
    items: list[EvidenceItem]
    scores: dict[str, float]
    sufficient: bool
    reason: str | None
    warnings: list[str] = field(default_factory=list)
    excluded_ineligible: int = 0

    def by_id(self) -> dict[str, EvidenceItem]:
        return {i.evidence_id: i for i in self.items}


def retrieve(source: EvidenceSource, question: str, scope: AskScope) -> RetrievalResult:
    all_items = source.items()
    warnings: list[str] = list(getattr(source, "warnings", []) or [])  # ex.: registros omitidos por hash divergente
    if not all_items:
        return RetrievalResult([], {}, False, "NO_ELIGIBLE_EVIDENCE",
                               ["Nenhum dataset curado carregado (dependência BL-02 pendente)."])

    known = source.known_tests()
    unknown = [u for u in scope.test_uids if u not in known]
    if unknown:
        warnings.append("Ensaios fora do dataset curado: " + ", ".join(unknown))

    scoped = [i for i in all_items if _in_scope(i, scope)]
    eligible = [i for i in scoped if _eligible(i)]
    excluded = len(scoped) - len(eligible)
    if excluded:
        warnings.append(f"{excluded} registro(s) no escopo excluído(s) por estado não elegível (ex.: não conferido).")
    withheld = sum(1 for i in eligible if i.value_withheld)
    if withheld:
        warnings.append(f"{withheld} registro(s) com valor retido: extraído(s) da fonte, aguardando revisão humana.")
    if not eligible:
        return RetrievalResult([], {}, False, "NO_ELIGIBLE_EVIDENCE", warnings, excluded)

    q = tokenize(question)
    raw = _bm25(q, [tokenize(f"{i.text} {i.parameter or ''} {' '.join(i.keywords)}") for i in eligible])
    scores = {i.evidence_id: round(s, 6) for i, s in zip(eligible, raw)}

    in_focus = [u for u in scope.test_uids if u in known]
    selected: list[EvidenceItem] = []
    if in_focus:
        # ensaios em foco: todas as fichas e lacunas do ensaio entram (são poucas e decisivas)
        selected += [i for i in eligible if i.kind != EvidenceKind.PASSAGE and i.test_uid in in_focus]
    else:
        selected += sorted(
            (i for i in eligible if i.kind != EvidenceKind.PASSAGE and scores[i.evidence_id] > MIN_SCORE),
            key=lambda i: -scores[i.evidence_id],
        )
    passages = sorted(
        (i for i in eligible if i.kind == EvidenceKind.PASSAGE and scores[i.evidence_id] > MIN_SCORE),
        key=lambda i: -scores[i.evidence_id],
    )[:TOP_K_PASSAGES]
    selected = (selected + passages)[:MAX_ITEMS]

    if not selected:
        return RetrievalResult([], scores, False, "INSUFFICIENT_EVIDENCE", warnings, excluded)
    if not any(i.kind != EvidenceKind.PASSAGE for i in selected) and not in_focus:
        warnings.append("Somente trechos textuais recuperados; valores numéricos não podem ser afirmados.")
    return RetrievalResult(selected, {i.evidence_id: scores[i.evidence_id] for i in selected}, True, None,
                           warnings, excluded)
