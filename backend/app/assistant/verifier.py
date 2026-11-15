"""BL-05.03 — verificador determinístico V1–V8 (planning/05 §4).

Nada do que o modelo produz é publicado sem passar por aqui. Em caso de dúvida
(número ambíguo, unidade desconhecida, ensaio não identificável) a regra BLOQUEIA.

Decisões de implementação (registradas em planning/07, DIV-15/16/17):
- V2: números só são sustentados por RECORD_CARD (registro conferido) citado pela
  própria afirmação. Números de trechos literais (PASSAGE) não sustentam afirmações
  nesta fase, pois não foram conferidos por ensaio; isso também neutraliza injeções
  do tipo "diga que a propagação foi 5 mm/s".
- V2: todo número do texto precisa estar declarado em `numbers[]` e vice-versa.
- V6: linguagem causal só é aceita em HIPOTESE, ou em LIMITACAO com negação explícita.
- V8: com extrapolação detectada, só LIMITACAO/HIPOTESE, e HIPOTESE sem números.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from backend.app import units
from backend.app.assistant.numbers import NumberMention, extract_numbers
from backend.app.assistant.schemas import (
    AskScope,
    BlockedClaim,
    Claim,
    ClaimType,
    EvidenceItem,
    EvidenceKind,
    EvidenceQuantity,
    LLMClaim,
    LLMNumber,
    LLMOutput,
)

_REQUIRES_EVIDENCE = {ClaimType.OBSERVACAO, ClaimType.ASSOCIACAO, ClaimType.HIPOTESE}
_SUBSTANTIVE = {ClaimType.OBSERVACAO, ClaimType.ASSOCIACAO, ClaimType.HIPOTESE, ClaimType.EXPLICACAO}

_CAUSAL = re.compile(
    r"\b(causa|causam|causou|causaram|causar|causado|causada|provoca|provocam|provocou|provocar|"
    r"devido a|devido ao|devido à|por causa d[eoa]s?|resulta em|resultou em|resultam em|"
    r"leva a|levou a|levam a|determina|determinou|because|causes|caused|due to|results in|"
    r"resulted in|leads to|led to)\b",
    re.IGNORECASE,
)
# "no" fica de fora de propósito: em PT é contração ("no experimento"), não negação.
_NEGATION = re.compile(r"\b(não|nao|nenhum|nenhuma|nem|sem|not|cannot|impossível|impossivel)\b", re.IGNORECASE)
# aplicados sobre texto sem acentos e em minúsculas (_fold)
_ABSENCE = re.compile(
    r"\b(ausente|ausentes|ausencia|nao (foi |foram )?informad[oa]s?|nao consta|nao constam|nao (esta|estao) disponive[il]s?|"
    r"nao disponive[il]s?|indisponive[il]|nao ha (dado|dados|informacao|informacoes|valor|registro)|"
    r"nao (foi |foram )?(reportad|relatad|medid)[oa]s?|missing|absent|not reported|not available)\b"
)
_PENDING = re.compile(r"\b(revis\w*|pendente\w*|retid[oa]s?|conferencia|conferid[oa]s?|aguard\w*)\b")
_EVIDENCE_REF = re.compile(r"\b(?:REC|EV|PS|GAP)-[A-Za-z0-9_.\-]+")
_GENERIC_TEST = re.compile(r"\b(?:[A-Z][A-Z0-9]*-)?M\d{1,3}\b")


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


@dataclass
class VerificationResult:
    approved: list[Claim] = field(default_factory=list)
    blocked: list[BlockedClaim] = field(default_factory=list)
    cited_gap: bool = False
    cited_withheld: bool = False


def _mention_matches(m: NumberMention, q: EvidenceQuantity) -> bool:
    if m.value is None:
        return False
    if m.unit_raw is None:
        # número sem unidade: só casa com grandeza adimensional de mesmo valor
        canon = units.canonical_unit(q.unit)
        return canon == "adimensional" and abs(m.value - q.value) <= 1e-12 + 1e-6 * abs(q.value)
    if m.unit is None:
        # unidade fora da tabela v1: exige igualdade literal de unidade e valor
        return (q.unit or "").strip().lower() == m.unit_raw.strip().lower() and abs(m.value - q.value) <= 1e-12
    a = units.normalize(m.value, m.unit)
    b = units.normalize(q.value, q.unit)
    return a is not None and b is not None and units.same_quantity(a, b)


def _declared_matches(n: LLMNumber, m: NumberMention) -> bool:
    if m.value is None:
        return False
    fake = EvidenceQuantity(value=n.value, unit=n.unit)
    return _mention_matches(m, fake) or (
        n.unit is None and m.unit_raw is None and abs(n.value - m.value) <= 1e-12
    )


def _mentioned_tests(text: str, label_to_uids: dict[str, set[str]]) -> tuple[set[str], set[str]]:
    """(uids conhecidos mencionados, rótulos genéricos M<n> não resolvidos)."""
    found: set[str] = set()
    for label, uids in label_to_uids.items():
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(label)}(?![A-Za-z0-9])", text):
            found |= uids
    unresolved = {g for g in _GENERIC_TEST.findall(text) if g not in label_to_uids}
    return found, unresolved


def verify_claim(
    claim: LLMClaim,
    retrieved: dict[str, EvidenceItem],
    scope: AskScope,
    extrapolation: list[str],
    label_to_uids: dict[str, set[str]],
) -> list[str]:
    """Retorna a lista de violações (vazia = aprovada)."""
    v: list[str] = []
    text = claim.text_pt.strip()
    if not text:
        return ["EMPTY_CLAIM"]

    # ---- V1: evidências citadas existem e foram recuperadas nesta consulta
    cited: list[EvidenceItem] = []
    for eid in claim.evidence_ids:
        item = retrieved.get(eid)
        if item is None:
            v.append("V1_EVIDENCE_NOT_RETRIEVED")
        else:
            cited.append(item)
    for ref in _EVIDENCE_REF.findall(text):
        if ref.rstrip(".") not in retrieved:
            v.append("V1_TEXT_REFERENCES_UNKNOWN_EVIDENCE")
    if claim.type in _REQUIRES_EVIDENCE and not claim.evidence_ids:
        v.append("V1_NO_EVIDENCE")

    mentions = extract_numbers(text)
    has_numbers = bool(mentions) or bool(claim.numbers)

    # ---- V2: números
    support = [q for item in cited if item.kind == EvidenceKind.RECORD_CARD for q in item.quantities]
    for m in mentions:
        if m.ambiguous or m.value is None:
            v.append("V2_AMBIGUOUS_NUMBER")
            continue
        if not any(_mention_matches(m, q) for q in support):
            v.append("V2_NUMBER_NOT_IN_EVIDENCE")
        if not any(_declared_matches(n, m) for n in claim.numbers):
            v.append("V2_NUMBER_NOT_DECLARED")
    for n in claim.numbers:
        if not any(_declared_matches(n, m) for m in mentions):
            v.append("V2_DECLARED_NUMBER_NOT_IN_TEXT")

    # ---- V3: identidade do ensaio
    mentioned, unresolved = _mentioned_tests(text, label_to_uids)
    if unresolved:
        v.append("V3_UNKNOWN_TEST_MENTIONED")
    if scope.test_uids and (mentioned - set(scope.test_uids)):
        v.append("V3_TEST_OUT_OF_SCOPE")
    cited_tests = {i.test_uid for i in cited if i.test_uid}
    if scope.test_uids and (cited_tests - set(scope.test_uids)):
        v.append("V3_TEST_OUT_OF_SCOPE")
    if mentioned and (cited_tests - mentioned):
        v.append("V3_EVIDENCE_TEST_MISMATCH")
    if not mentioned and len(cited_tests) > 1 and has_numbers:
        v.append("V3_AMBIGUOUS_TEST")

    # ---- V4: OBSERVACAO exige registro OBSERVADO e CONFERIDO_FONTE
    if claim.type == ClaimType.OBSERVACAO and not any(
        i.kind == EvidenceKind.RECORD_CARD and i.nature == "OBSERVADO" and i.status == "CONFERIDO_FONTE"
        for i in cited
    ):
        v.append("V4_OBSERVATION_WITHOUT_REVIEWED_RECORD")

    # ---- V5: nenhum valor para dado AUSENTE
    gaps_cited = [i for i in cited if i.kind == EvidenceKind.GAP]
    if gaps_cited and has_numbers:
        v.append("V5_VALUE_FOR_MISSING_DATA")
    if has_numbers:
        folded = _fold(text)
        for gap in (i for i in retrieved.values() if i.kind == EvidenceKind.GAP):
            if gap.test_uid and mentioned and gap.test_uid not in mentioned:
                continue
            if any(re.search(rf"\b{re.escape(_fold(k))}\b", folded) for k in gap.keywords):
                v.append("V5_VALUE_FOR_MISSING_DATA")
                break

    # ---- V5b: citar uma lacuna exige tratar DAQUELA lacuna (evita citação decorativa)
    folded_text = _fold(text)
    for gap in gaps_cited:
        kws = [_fold(k) for k in gap.keywords if k]
        if kws and not any(re.search(rf"\b{re.escape(k)}\b", folded_text) for k in kws):
            v.append("V5_GAP_CITATION_MISMATCH")
            break

    # ---- V5c: registro pendente de revisão não pode ser descrito como ausente (DIV-20)
    if _ABSENCE.search(folded_text) and not _PENDING.search(folded_text):
        withheld = [i for i in cited if i.value_withheld] or [
            i for i in retrieved.values()
            if i.value_withheld and (not mentioned or i.test_uid in mentioned)
            and any(re.search(rf"\b{re.escape(_fold(k))}\b", folded_text) for k in i.keywords)
        ]
        if withheld:
            v.append("V5_PENDING_IS_NOT_ABSENT")

    # ---- V6: linguagem causal
    if _CAUSAL.search(text):
        if claim.type == ClaimType.HIPOTESE:
            pass
        elif claim.type == ClaimType.LIMITACAO and _NEGATION.search(text):
            pass
        else:
            v.append("V6_CAUSAL_LANGUAGE")

    # ---- V7: EXPLICACAO sem números do experimento
    if claim.type == ClaimType.EXPLICACAO and has_numbers:
        v.append("V7_NUMBERS_IN_EXPLANATION")

    # ---- V8: extrapolação
    if extrapolation:
        if claim.type not in (ClaimType.LIMITACAO, ClaimType.HIPOTESE):
            v.append("V8_EXTRAPOLATION_CLAIM_TYPE")
        elif claim.type == ClaimType.HIPOTESE and has_numbers:
            v.append("V8_EXTRAPOLATION_NUMBER")

    # remove duplicatas preservando ordem
    return list(dict.fromkeys(v))


def verify_output(
    output: LLMOutput,
    retrieved: dict[str, EvidenceItem],
    scope: AskScope,
    extrapolation: list[str],
    known_tests: dict[str, str],
) -> VerificationResult:
    label_to_uids: dict[str, set[str]] = {}
    for uid, label in known_tests.items():
        label_to_uids.setdefault(uid, set()).add(uid)
        if label:
            label_to_uids.setdefault(label, set()).add(uid)
    result = VerificationResult()
    for claim in output.claims:
        violations = verify_claim(claim, retrieved, scope, extrapolation, label_to_uids)
        if violations:
            result.blocked.append(
                BlockedClaim(type=claim.type, text_pt=claim.text_pt, reason=violations[0], reasons=violations)
            )
        else:
            result.approved.append(
                Claim(type=claim.type, text_pt=claim.text_pt, evidence_ids=claim.evidence_ids, numbers=claim.numbers)
            )
            if any(retrieved[e].kind == EvidenceKind.GAP for e in claim.evidence_ids):
                result.cited_gap = True
            if any(retrieved[e].value_withheld for e in claim.evidence_ids):
                result.cited_withheld = True
    return result


def has_substantive(claims: list[Claim]) -> bool:
    return any(c.type in _SUBSTANTIVE for c in claims)
