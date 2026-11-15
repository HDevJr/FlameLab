"""BL-02.12 — Verificação cruzada AUTOMÁTICA da curadoria contra a camada de texto do PDF.

NÃO substitui a revisão humana e NÃO altera estados. Para cada evidência:
- TABLE_CELL da Tabela 5.1: localiza a linha (ex.: "M1") na página indicada e compara a célula
  da coluna registrada com `original.raw_text` do registro → MATCH / MISMATCH / NOT_FOUND.
- PAGE: verifica se o trecho citado aparece na página indicada → MATCH / NOT_FOUND.
Grava docs/evidence/crosscheck_<UTC>.json. Requer o PDF local (PDF tratado como dado).
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pymupdf  # noqa: E402

from backend.app.dataset.store import DatasetStore  # noqa: E402

# ordem das colunas de dados (após "Test no."), conforme o cabeçalho da Tabela 5.1 (p. 57)
TABLE_SPECS = {
    ("NASA-TM-20210011385", "5.1"): ["Thickness, mm", "Width, cm", "One or two sides burning", "Velocity, cm/s",
                                     "Spread rate, mm/s", "Burn time, min", "Initial O2, vol%", "Final O2, vol%"],
}


def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^0-9a-z.%]+", " ", unicodedata.normalize("NFKC", s).lower()).split())


def main() -> int:
    store = DatasetStore.load()
    now = datetime.now(timezone.utc)
    pdfs: dict[str, pymupdf.Document] = {}
    rows = []
    for rec in sorted(store.records.values(), key=lambda r: r.record_id):
        for eid in rec.evidence_ids:
            ev = store.evidence[eid]
            doc = store.documents[ev.document_id]
            path = ROOT / (doc.local_path or "")
            if not path.is_file():
                rows.append({"record_id": rec.record_id, "evidence_id": eid, "result": "PDF_MISSING"})
                continue
            pdf = pdfs.setdefault(doc.document_id, pymupdf.open(path))
            text = pdf[ev.locator.page_pdf_index - 1].get_text()
            if ev.locator.precision == "TABLE_CELL":
                cols = TABLE_SPECS.get((ev.document_id, ev.locator.table or ""))
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                if not cols or ev.locator.row_label not in lines or ev.locator.column_label not in cols:
                    rows.append({"record_id": rec.record_id, "evidence_id": eid, "result": "NOT_FOUND"})
                    continue
                start = lines.index(ev.locator.row_label) + 1
                cell = lines[start + cols.index(ev.locator.column_label)]
                expected = rec.original.raw_text if rec.original else None
                rows.append({"record_id": rec.record_id, "evidence_id": eid, "pdf_cell": cell,
                             "curated_raw_text": expected, "result": "MATCH" if cell == expected else "MISMATCH"})
            else:
                quote = (ev.quote or "").rstrip(". ").removesuffix("...").strip()
                ok = bool(quote) and _norm(quote) in _norm(text)
                rows.append({"record_id": rec.record_id, "evidence_id": eid, "result": "MATCH" if ok else "NOT_FOUND"})
    report = {"executed_at_utc": now.isoformat(), "kind": "AUTOMATIC_TEXT_LAYER_CROSSCHECK",
              "warning": "Verificação automática; não equivale a CONFERIDO_FONTE.",
              "dataset_version": store.dataset_version, "rows": rows}
    out = ROOT / "docs" / "evidence" / f"crosscheck_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for r in rows:
        print(f"{r['result']:>11}  {r['record_id']:<28} {r['evidence_id']}  {r.get('pdf_cell', '')}")
    print(f"-> {out.relative_to(ROOT)}")
    return 0 if all(r["result"] == "MATCH" for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
