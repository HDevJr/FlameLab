"""O núcleo genérico não pode depender de BASS-II, PSI-25 nem do documento de referência."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app"
GENERIC = ["nasa", "ingest", "catalog", "simulation", "workspace.py", "api/platform.py"]
FORBIDDEN = re.compile(r"BASS2?[-_ ]?(II|M\d)|PSI-25|20210011385|TM-20210011385", re.I)


def test_no_hardcoded_reference_identifiers_in_generic_modules():
    offenders = []
    for item in GENERIC:
        base = ROOT / item
        files = [base] if base.is_file() else sorted(base.rglob("*.py"))
        for f in files:
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if FORBIDDEN.search(line):
                    offenders.append(f"{f.relative_to(ROOT)}:{n}: {line.strip()[:80]}")
    assert not offenders, offenders
