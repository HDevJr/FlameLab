"""Fixtures SINTÉTICAS para testes do assistente.

Nada aqui é dado NASA. Todos os itens têm `synthetic=True`. O ensaio TEST-01 e os
"ensaios" SYN-M1/SYN-M2 existem apenas para exercitar o verificador; os números
foram escolhidos para coincidir com exemplos do prompt da tarefa, não com a curadoria.
"""

from __future__ import annotations

from typing import Callable

from backend.app.assistant.cards import GapInput, LocatorInput, PassageInput, RecordInput, gap_card, passage_item, record_card
from backend.app.assistant.config import AssistantSettings
from backend.app.assistant.provider import ProviderError
from backend.app.assistant.retrieval import InMemoryEvidenceSource
from backend.app.assistant.schemas import EvidenceItem, LLMClaim, LLMNumber, LLMOutput

INV = "SYN-INV"


def rec(test_uid: str, label: str, parameter: str, label_pt: str, value, unit=None, role="CONDICAO",
        status="CONFERIDO_FONTE", nature="OBSERVADO") -> EvidenceItem:
    return record_card(RecordInput(
        record_id=f"{test_uid}.{parameter}", test_uid=test_uid, test_label=label, investigation_id=INV,
        parameter=parameter, label_pt=label_pt, role=role, nature=nature, status=status,
        original={"value": value, "unit": unit}, document_id="SYN-DOC",
        locator=LocatorInput(table="X", row_label=label, page_pdf_index=1, precision="TABLE_CELL"),
        synthetic=True,
    ))


def gap(test_uid: str, label: str, parameter: str, label_pt: str, keywords: list[str]) -> EvidenceItem:
    return gap_card(GapInput(
        gap_id=f"GAP-{test_uid}-{parameter}", test_uid=test_uid, test_label=label, investigation_id=INV,
        parameter=parameter, label_pt=label_pt, keywords=keywords,
        explanation_pt="A evidência sintética declara que o valor não foi informado.", synthetic=True,
    ))


def passage(pid: str, text: str, test_uid: str | None = None) -> EvidenceItem:
    return passage_item(PassageInput(passage_id=pid, document_id="SYN-DOC", investigation_id=INV,
                                     test_uid=test_uid, text=text, synthetic=True))


def synthetic_test01_source() -> InMemoryEvidenceSource:
    """Evidência sintética do prompt: TEST-01, PMMA, 1 mm, 9 cm/s, pressão não informada."""
    return InMemoryEvidenceSource([
        rec("TEST-01", "TEST-01", "material", "Material", "PMMA", role="METADADO"),
        rec("TEST-01", "TEST-01", "thickness", "Espessura da amostra", 1, "mm"),
        rec("TEST-01", "TEST-01", "airflow_velocity", "Velocidade do ar", 9, "cm/s"),
        gap("TEST-01", "TEST-01", "pressure", "Pressão", ["pressão", "pressao", "pressure"]),
    ])


def two_tests_source(extra: list[EvidenceItem] | None = None) -> InMemoryEvidenceSource:
    return InMemoryEvidenceSource([
        rec("SYN-M1", "M1", "flame_spread_rate", "Velocidade de propagação", 0.071, "mm/s", role="OBSERVAVEL"),
        rec("SYN-M1", "M1", "thickness", "Espessura", 1, "mm"),
        rec("SYN-M2", "M2", "flame_spread_rate", "Velocidade de propagação", 0.05, "mm/s", role="OBSERVAVEL"),
        rec("SYN-M2", "M2", "thickness", "Espessura", 0.5, "mm",
            status="EXTRAIDO_NAO_REVISADO"),
        gap("SYN-M1", "M1", "pmma_pyrolysis_properties", "Propriedades de pirólise",
            ["pirólise", "pirolise", "pyrolysis"]),
        *(extra or []),
    ])


def claim(type_: str, text: str, ids: list[str], numbers: list[tuple[float, str | None]] = ()) -> LLMClaim:
    return LLMClaim(type=type_, text_pt=text, evidence_ids=ids,
                    numbers=[LLMNumber(value=v, unit=u) for v, u in numbers])


def output(*claims: LLMClaim, abstain: bool = False, reason: str | None = None) -> LLMOutput:
    return LLMOutput(claims=list(claims), abstain=abstain, abstain_reason=reason)


class FakeProvider:
    """Provedor injetável. NÃO representa chamada real ao Gemini."""

    name = "fake"
    model = "fake-model"

    def __init__(self, result: LLMOutput | Callable[[str, str], LLMOutput] | ProviderError):
        self._result = result
        self.calls: list[tuple[str, str]] = []

    def generate_json(self, system, user, schema, timeout):
        self.calls.append((system, user))
        if isinstance(self._result, ProviderError):
            raise self._result
        if callable(self._result):
            return self._result(system, user)
        return self._result


def settings(tmp_path, mode: str = "live", **kw) -> AssistantSettings:
    """Configuração de teste: nunca lê o .env real e grava cache apenas em tmp_path."""
    return AssistantSettings(mode=mode, provider="gemini", model="fake-model",
                             cache_dir=tmp_path / "ai_cache", **kw)
