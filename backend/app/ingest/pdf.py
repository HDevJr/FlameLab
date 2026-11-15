"""Leitura defensiva de PDFs importados. O arquivo é conteúdo NÃO confiável:
só o texto é lido (PyMuPDF), nada é executado e nada do PDF vira caminho ou comando."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

MAX_UPLOAD_BYTES = 120 * 1024 * 1024
MAX_PAGES = 800

_DASH = r"[-‐-―−]"
# formato novo (o número é o ID NTRS, 11 dígitos) e formato antigo (ano-número)
# aceita "NASA/TM-2021-0011385", "NASA-CR-191109" e "NASA CR 191109" (relatórios antigos têm só o número)
_SEP = rf"(?:\s*(?:/|{_DASH})\s*|\s+)"
_REPORT = re.compile(rf"NASA{_SEP}(TM|TP|CR|SP|TN|CP){_SEP}(\d{{4}}\s*{_DASH}\s*\d{{4,7}}|20\d{{9}}|\d{{5,7}})\b", re.I)
_DOI = re.compile(r"\b10\.\d{4,9}/[^\s\"<>]+", re.I)


class PdfRejected(Exception):
    def __init__(self, code: str, message_pt: str):
        self.code = code
        self.message_pt = message_pt
        super().__init__(code)


@dataclass
class PdfInfo:
    page_count: int
    has_text_layer: bool
    title: str | None
    report_numbers: list[str] = field(default_factory=list)
    ntrs_ids: list[str] = field(default_factory=list)
    dois: list[str] = field(default_factory=list)
    year: int | None = None


def sha256_bytes_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def looks_like_pdf(head: bytes) -> bool:
    return head.startswith(b"%PDF-")


def _open(path: Path):
    import pymupdf

    try:
        # abre a partir da memória: não deixa o arquivo preso (Windows) se a leitura falhar
        doc = pymupdf.open(stream=path.read_bytes(), filetype="pdf")
    except Exception:  # noqa: BLE001 — qualquer falha de leitura é rejeição
        raise PdfRejected("PDF_UNREADABLE", "O arquivo não pôde ser lido como PDF.") from None
    if doc.needs_pass:
        doc.close()
        raise PdfRejected("PDF_ENCRYPTED", "PDF protegido por senha não é aceito.")
    if doc.page_count == 0 or doc.page_count > MAX_PAGES:
        doc.close()
        raise PdfRejected("PDF_PAGE_LIMIT", f"O PDF precisa ter entre 1 e {MAX_PAGES} páginas.")
    return doc


def page_texts(path: Path, first: int = 1, last: int | None = None, on_page=None) -> dict[int, str]:
    """Texto por página (1 = primeira página do visualizador)."""
    doc = _open(path)
    last = min(last or doc.page_count, doc.page_count)
    try:
        out: dict[int, str] = {}
        for i in range(first, last + 1):
            out[i] = doc[i - 1].get_text()
            if on_page:
                on_page(i - first + 1, last - first + 1)
        return out
    finally:
        doc.close()


def page_text(path: Path, number: int) -> str | None:
    """Texto de UMA página (1 = primeira). Abre pelo caminho (sem ler o arquivo todo em memória)."""
    import pymupdf

    try:
        doc = pymupdf.open(path)
    except Exception:  # noqa: BLE001
        return None
    try:
        return doc[number - 1].get_text() if 1 <= number <= doc.page_count else None
    finally:
        doc.close()


def _title_from_first_page(page) -> str | None:
    spans = [
        (round(s["size"], 1), s["text"].strip())
        for b in page.get_text("dict").get("blocks", [])
        for line in b.get("lines", [])
        for s in line.get("spans", [])
        if s["text"].strip()
    ]
    if not spans:
        return None
    biggest = max(size for size, _ in spans)
    title = " ".join(text for size, text in spans if size == biggest)
    title = re.sub(r"\s+", " ", title).strip()
    return title[:300] if 8 <= len(title) else None


_CATALOG = re.compile(r"\(NASA[-/ ]\w+[-/ ]\d+\)\s+(.{8,200}?)\s+(?:Final Report|Technical (?:Report|Memorandum|Paper)|Interim|Annual|Contractor Report|\(|\d+\s*pb)", re.I)


def _title_from_catalog_block(flat: str) -> str | None:
    """Capas NTRS têm um bloco "(NASA-CR-n) TÍTULO Final Report (Empresa) …". É só um candidato de título,
    sujeito a erros de OCR; a identidade do documento vem da busca por número de relatório, não daqui."""
    m = _CATALOG.search(flat)
    if not m:
        return None
    t = m.group(1).strip()
    return (t.title() if t.isupper() else t)[:300]


def inspect_pdf(path: Path) -> PdfInfo:
    doc = _open(path)
    try:
        return _inspect(doc)
    finally:
        doc.close()


def _inspect(doc) -> PdfInfo:
    head = "\n".join(doc[i].get_text() for i in range(min(3, doc.page_count)))
    flat = re.sub(r"\s+", " ", head)  # capa escaneada: uma palavra por linha também casa
    meta_title = (doc.metadata or {}).get("title") or ""
    title = meta_title.strip() if len(meta_title.strip()) >= 8 else _title_from_first_page(doc[0])
    title = title or _title_from_catalog_block(flat)
    reports, ntrs_ids = [], []
    for m in _REPORT.finditer(flat):
        number = re.sub(r"\s+", "", m.group(2))
        number = re.sub(_DASH, "-", number)
        reports.append(f"NASA/{m.group(1).upper()}-{number}")
        if re.fullmatch(r"20\d{9}", number):
            ntrs_ids.append(number)
    years = [int(y) for y in re.findall(r"\b(19[5-9]\d|20[0-4]\d)\b", doc[0].get_text())]
    return PdfInfo(
        page_count=doc.page_count,
        has_text_layer=len(head.strip()) > 50,
        title=title,
        report_numbers=sorted(set(reports)),
        ntrs_ids=sorted(set(ntrs_ids)),
        dois=sorted({d.rstrip(".,;)") for d in _DOI.findall(head)}),
        year=years[-1] if years else None,
    )
