"""Registra a REVISÃO HUMANA de um registro científico (uso exclusivo de integrante da equipe).

Abra o PDF (sources/NASA-TM-20210011385.pdf), localize o valor e execute, por exemplo:

    .\\.venv\\Scripts\\python.exe scripts\\review_record.py --record BASS2-M1.thickness `
        --reviewer "Nome Sobrenome" --observed-value 1 --observed-unit mm --page-pdf 65 --i-checked-the-pdf

O valor/unidade/página que VOCÊ leu precisa coincidir com o registro; caso contrário, nada é alterado.
Para material: --observed-value PMMA (sem unidade) e --page-pdf 64.
Cada revisão é anexada a docs/curation/BASS2-M1_curation_log.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.dataset.review import ReviewRejected, apply_review  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--record", required=True)
    ap.add_argument("--reviewer", required=True)
    ap.add_argument("--observed-value", required=True)
    ap.add_argument("--observed-unit", default=None)
    ap.add_argument("--page-pdf", type=int, required=True)
    ap.add_argument("--notes", default=None)
    ap.add_argument("--i-checked-the-pdf", action="store_true",
                    help="declaração obrigatória de que o valor foi lido no PDF original")
    args = ap.parse_args()
    if not args.i_checked_the_pdf:
        print("RECUSADO: declare --i-checked-the-pdf após conferir o PDF original.")
        return 2
    try:
        res = apply_review(args.record, args.reviewer, args.observed_value, args.observed_unit,
                           args.page_pdf, args.notes)
    except ReviewRejected as exc:
        print(f"RECUSADO: {exc}")
        return 1
    log = ROOT / "docs" / "curation" / "BASS2-M1_curation_log.md"
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"| {res.reviewed_at} | {res.record_id} | CONFERIDO_FONTE | {res.reviewer} | "
                 f"valor lido: {args.observed_value} {args.observed_unit or ''} · PDF p. {args.page_pdf} | "
                 f"sha256 {res.checked_document_sha256[:12]}… | {args.notes or ''} |\n")
    print(f"OK: {res.record_id} → CONFERIDO_FONTE por {res.reviewer} em {res.reviewed_at}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
