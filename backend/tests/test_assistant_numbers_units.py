import pytest

from backend.app import units
from backend.app.assistant.numbers import extract_numbers


@pytest.mark.parametrize(
    "value,unit,si,si_unit",
    [(1, "mm", 0.001, "m"), (2.2, "cm", 0.022, "m"), (9, "cm/s", 0.09, "m/s"),
     (0.071, "mm/s", 7.1e-5, "m/s"), (6.4, "min", 384, "s"), (22.2, "%", 0.222, "fraction")],
)
def test_t07_unit_normalization(value, unit, si, si_unit):
    q = units.normalize(value, unit)
    assert q is not None and q.unit == si_unit
    assert q.value == pytest.approx(si, rel=1e-12)


def test_unknown_unit_is_not_approximated():
    assert units.normalize(101.3, "kPa") is None


def _vals(text):
    return [(m.value, m.unit) for m in extract_numbers(text)]


def test_pt_en_and_scientific_notation():
    assert _vals("0,071 mm/s") == [(0.071, "mm/s")]
    assert _vals("0.071 mm/s") == [(0.071, "mm/s")]
    for t in ("7,1×10⁻⁵ m/s", "7.1e-5 m/s", "7,1 x 10^-5 m/s"):
        (v, u), = _vals(t)
        assert v == pytest.approx(7.1e-5) and u == "m/s"
    assert _vals("1.234,5 s") == [(1234.5, "s")]


def test_identifiers_and_references_are_masked():
    assert _vals("Ensaio M1 (BASS2-M1), TEST-01, PSI-25, O2, Tabela 5.1, seção 5.3, página 57, FDS 6.11.1") == []


def test_thousand_separator_ambiguity_is_flagged():
    (m,) = extract_numbers("1,000 mm")
    assert m.ambiguous and m.value is None
