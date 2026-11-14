"""Enriquecimento NASA — por fixtures de respostas reais gravadas em 14/11/2026 (sem rede)."""

import json
from pathlib import Path

from backend.app.nasa.clients.fixtures import FixtureTransport
from backend.app.nasa.clients.http import SourceError
from backend.app.nasa.enrichment.service import EnrichmentService
from backend.app.nasa.matching.matcher import author_overlap, key_words, title_similarity, title_tokens
from backend.app.nasa.models import AccessMode, DocumentMeta, MatchState

FIX = Path(__file__).parent / "fixtures" / "nasa"
BASS = DocumentMeta(document_id="D-A", title="Burning and Suppression of Solids—II (BASS—II) Summary Report",
                    ntrs_id="20210011385")
OTHER = DocumentMeta(document_id="D-B", authors=["D. Langbein", "M. Weislogel"],
                     title="Dynamics of Liquids in Edges and Corners (DYLCO) IML-2 Experiment for the BDPU")


def _state(report, source):
    return next(m for m in report.matches if m.source == source)


def test_reference_case_ntrs_confirmed_psi_candidate_techport_not_found():
    r = EnrichmentService(FixtureTransport(FIX)).enrich(BASS)
    assert r.mode == AccessMode.FIXTURE
    assert _state(r, "NTRS").state == MatchState.MATCH_CONFIRMED
    psi = _state(r, "PSI")
    assert psi.state == MatchState.MATCH_CANDIDATE  # sem citação cruzada por identificador
    assert psi.source_record_id == "PSI-25"
    assert any("candidato" in x for x in psi.reasons_pt)
    tp = _state(r, "TECHPORT")
    assert tp.state == MatchState.NOT_FOUND  # TechPort 13543 (Saffire) não é equivalente
    assert all(c["id"] != 13543 for c in tp.rejected_candidates)


def test_enrichment_never_promotes_or_overrides_and_flags_spelling_conflict():
    r = EnrichmentService(FixtureTransport(FIX)).enrich(BASS)
    assert r.promoted_records == 0
    people = next(x for x in r.records if x.field == "people")
    assert people.state == MatchState.CONFLICT and "bhattacharjee" in people.divergence_pt
    assert all(x.curation_decision == "PENDENTE" for x in r.records)
    assert any(x.state == MatchState.ADDITIONAL_DATA_FOUND for x in r.records)


def test_other_document_without_psi_still_enriches_and_does_not_invent_matches():
    r = EnrichmentService(FixtureTransport(FIX)).enrich(OTHER)
    assert _state(r, "PSI").state == MatchState.NOT_FOUND
    assert _state(r, "TECHPORT").state == MatchState.NOT_FOUND
    ntrs = _state(r, "NTRS")
    assert ntrs.state == MatchState.MATCH_CANDIDATE and ntrs.source_record_id == "19980232607"
    assert not any(x.complementary_source == "PSI (DataCite)" for x in r.records)


def test_source_failure_is_a_warning_not_an_error():
    r = EnrichmentService(FixtureTransport(FIX, fail_hosts=frozenset({"api.datacite.org", "techport.nasa.gov"}))).enrich(BASS)
    assert _state(r, "PSI").state == MatchState.SOURCE_UNAVAILABLE
    assert _state(r, "NTRS").state == MatchState.MATCH_CONFIRMED
    assert any("PSI indisponível" in w for w in r.warnings_pt)


def test_all_sources_down_continues():
    down = frozenset({"ntrs.nasa.gov", "api.datacite.org", "techport.nasa.gov"})
    r = EnrichmentService(FixtureTransport(FIX, fail_hosts=down)).enrich(BASS)
    assert {m.state for m in r.matches} == {MatchState.SOURCE_UNAVAILABLE}
    assert r.records == [] and r.promoted_records == 0


def test_unrecorded_url_fails_closed_never_invented():
    t = FixtureTransport(FIX)
    try:
        t.get("https://ntrs.nasa.gov/api/citations/1", None, 5)
        assert False
    except SourceError as e:
        assert e.kind == "NETWORK"


def test_every_operation_is_logged_with_mode_and_hash():
    r = EnrichmentService(FixtureTransport(FIX)).enrich(BASS)
    assert r.operations and all(o.mode == AccessMode.FIXTURE and o.response_sha256 for o in r.operations)


def test_conflicting_identifier_is_not_confirmed():
    wrong = DocumentMeta(document_id="D-C", title="Completely unrelated thermal vacuum chamber study", ntrs_id="20210011385")
    r = EnrichmentService(FixtureTransport(FIX)).enrich(wrong)
    assert _state(r, "NTRS").state == MatchState.CONFLICT


def test_matcher_units():
    a = title_tokens("Burning and Suppression of Solids—II (BASS—II) Summary Report")
    b = title_tokens("Burning and Suppression of Solids - II", "BASS-II")
    assert title_similarity(a, b) >= 0.85
    # o dataset irmão (BASS, sem "II") não pode ser confundido com o BASS-II
    assert title_similarity(a, title_tokens("Burning and Suppression of Solids", "BASS")) < 0.85
    shared, near = author_overlap(["Bhattacharjee, S."], ["Bhattachjee, Subrata"])
    assert near and not shared
    assert key_words("The Dynamics of Liquids", 2) == ["dynamics", "liquids"]


def test_fixture_files_are_valid_json():
    for f in FIX.glob("*.json"):
        json.loads(f.read_text(encoding="utf-8"))
