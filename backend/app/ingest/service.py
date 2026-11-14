"""Importação de artigos em PDF: recebe, calcula o hash, identifica, consulta fontes NASA,
verifica a procedência e (se a IA estiver ligada) propõe parâmetros para revisão.

Cada etapa grava seu estado real em `var/imports/<id>/import.json`. A consulta NASA e a IA
são opcionais: se falharem, a etapa fica FAILED/SKIPPED e o artigo continua disponível.
"""

from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Any, BinaryIO, Callable

from backend.app import workspace
from backend.app.assistant.provider import LLMProvider, ProviderError
from backend.app.catalog.service import PROVENANCE_LABELS, Catalog
from backend.app.dataset.store import DatasetStore
from backend.app.ingest import extraction
from backend.app.ingest.pdf import (
    MAX_UPLOAD_BYTES, PdfRejected, inspect_pdf, looks_like_pdf, page_texts, sha256_bytes_file,
)
from backend.app.nasa.clients.http import SourceError, Transport
from backend.app.nasa.enrichment.service import EnrichmentService
from backend.app.nasa.models import EnrichmentReport, MatchState
from backend.app.nasa.provenance.log import utc_now

STEPS = [
    ("RECEIVE", "Recebimento do arquivo"),
    ("HASH", "Cálculo do SHA-256"),
    ("PARSE", "Leitura do PDF e identificação"),
    ("NASA_LOOKUP", "Consulta às fontes NASA"),
    ("PROVENANCE", "Verificação de procedência NASA"),
    ("EXTRACT", "Extração de parâmetros"),
]
NTRS_FILE_MAX = 200 * 1024 * 1024


def verify_provenance(transport: Transport, report: EnrichmentReport | None, local_sha256: str) -> dict[str, Any]:
    """Procedência NASA: só é VERIFIED quando o arquivo é idêntico ao que o NTRS distribui.
    Texto ou aparência do PDF nunca bastam."""
    ntrs = next((m for m in (report.matches if report else []) if m.source == "NTRS"), None)
    base = {"checked_at": utc_now(), "ntrs_id": None, "ntrs_url": None, "local_sha256": local_sha256}
    if ntrs is None or ntrs.state not in (MatchState.MATCH_CONFIRMED, MatchState.MATCH_CANDIDATE):
        reason = ("O NTRS não respondeu." if ntrs and ntrs.state == MatchState.SOURCE_UNAVAILABLE
                  else "Nenhum registro correspondente foi localizado no NTRS.")
        return {**base, "state": "PENDING", "label_pt": PROVENANCE_LABELS["PENDING"],
                "reasons_pt": [reason, "O documento não é tratado como publicação NASA validada."]}
    base.update(ntrs_id=ntrs.source_record_id, ntrs_url=ntrs.source_url)
    links = [d.get("pdf") for d in ntrs.metadata.get("downloads") or [] if d.get("pdf")]
    link = next((l for l in links if re.fullmatch(r"/api/citations/\d+/downloads/[A-Za-z0-9_.\-]+", l)), None)
    reasons = list(ntrs.reasons_pt)
    if not link:
        return {**base, "state": "CANDIDATE", "label_pt": PROVENANCE_LABELS["CANDIDATE"],
                "reasons_pt": reasons + ["O registro do NTRS não oferece arquivo para comparação."]}
    try:
        remote, size = transport.stream_sha256("https://ntrs.nasa.gov" + link, 300.0, NTRS_FILE_MAX)
    except SourceError as exc:
        return {**base, "state": "CANDIDATE", "label_pt": PROVENANCE_LABELS["CANDIDATE"],
                "reasons_pt": reasons + [f"Não foi possível baixar o arquivo do NTRS para comparar ({exc.kind})."]}
    same = remote == local_sha256
    state = "VERIFIED" if same else "MISMATCH"
    reasons.append(
        f"SHA-256 do arquivo distribuído pelo NTRS ({size} bytes): {remote}. "
        + ("É idêntico ao arquivo importado." if same else "É diferente do arquivo importado.")
    )
    return {**base, "state": state, "label_pt": PROVENANCE_LABELS[state], "reasons_pt": reasons,
            "ntrs_file": link, "ntrs_sha256": remote, "mode": transport.mode.value}


class ImportService:
    def __init__(self, store: DatasetStore, transport_factory: Callable[[], Transport],
                 provider: LLMProvider | None, run_async: bool = True):
        self._store = store
        self._transport_factory = transport_factory
        self._provider = provider
        self._async = run_async
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- armazenamento
    @staticmethod
    def _dir(import_id: str) -> Path:
        return workspace.area("imports") / workspace.safe_id(import_id)

    def get(self, import_id: str) -> dict[str, Any] | None:
        return workspace.read_json(self._dir(import_id) / "import.json")

    def list(self) -> list[dict[str, Any]]:
        items = [workspace.read_json(p / "import.json") for p in sorted(workspace.area("imports").iterdir())]
        return [i for i in items if i]

    def _save(self, record: dict[str, Any]) -> None:
        with self._lock:
            workspace.write_json(self._dir(record["import_id"]) / "import.json", record)

    def _step(self, record: dict[str, Any], key: str, state: str, detail: str | None = None) -> None:
        for step in record["steps"]:
            if step["key"] == key:
                step.update(state=state, detail_pt=detail, at=utc_now())
        self._save(record)

    # ---------------------------------------------------------------- entrada
    @staticmethod
    def _write_upload(stream: BinaryIO, tmp: Path) -> None:
        error: PdfRejected | None = None
        with tmp.open("wb") as out:
            head = stream.read(8)
            if not looks_like_pdf(head):
                error = PdfRejected("NOT_A_PDF", "O arquivo enviado não é um PDF.")
            else:
                out.write(head)
                size = len(head)
                while chunk := stream.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        error = PdfRejected("FILE_TOO_LARGE", "O arquivo excede o limite de 120 MB.")
                        break
                    out.write(chunk)
        if error:
            raise error

    def create(self, filename: str, stream: BinaryIO) -> dict[str, Any]:
        tmp = workspace.area("incoming") / f"{threading.get_ident()}-{utc_now().replace(':', '')}.part"
        try:
            self._write_upload(stream, tmp)
            sha = sha256_bytes_file(tmp)
            info = inspect_pdf(tmp)
            size = tmp.stat().st_size
        except PdfRejected:
            tmp.unlink(missing_ok=True)
            raise
        import_id = "IMP-" + sha[:12]
        folder = self._dir(import_id)
        folder.mkdir(parents=True, exist_ok=True)
        tmp.replace(folder / "source.pdf")

        curated = next((d for d in self._store.documents.values() if d.sha256 == sha), None)
        document_id = curated.document_id if curated else "DOC-" + sha[:12]
        display = re.sub(r"[^\w .()\-]", "_", Path(filename or "arquivo.pdf").name)[:120]
        record = {
            "import_id": import_id, "filename": display, "size_bytes": size, "sha256": sha,
            "received_at": utc_now(), "status": "PROCESSING",
            "steps": [{"key": k, "label_pt": label, "state": "PENDING", "detail_pt": None, "at": None}
                      for k, label in STEPS],
            "document": {
                "document_id": document_id, "curated": curated is not None,
                "title": curated.title if curated else info.title, "page_count": info.page_count,
                "has_text_layer": info.has_text_layer, "year": info.year,
                "identifiers": {"report_numbers": info.report_numbers, "ntrs_ids": info.ntrs_ids,
                                "dois": info.dois},
            },
            "nasa_provenance": None, "experiments": [], "extraction": None, "warnings_pt": [],
        }
        self._step(record, "RECEIVE", "DONE", f"{size} bytes recebidos.")
        self._step(record, "HASH", "DONE", sha)
        found = info.report_numbers + info.ntrs_ids + info.dois
        self._step(record, "PARSE", "DONE",
                   f"{info.page_count} páginas. " + (f"Identificadores no texto: {', '.join(found)}."
                                                     if found else "Nenhum identificador forte no texto."))
        if self._async:
            threading.Thread(target=self._pipeline, args=(record,), daemon=True).start()
        else:
            self._pipeline(record)
        return record

    # ---------------------------------------------------------------- etapas opcionais
    def _pipeline(self, record: dict[str, Any]) -> None:
        try:
            report = self._nasa_lookup(record)
            self._provenance(record, report)
            self._extract(record)
            record["status"] = "DONE"
        except Exception:  # noqa: BLE001 — falha inesperada fica registrada, sem derrubar o servidor
            record["status"] = "FAILED"
            record["warnings_pt"].append("Falha inesperada no processamento; consulte os logs do servidor.")
        self._save(record)

    def _nasa_lookup(self, record: dict[str, Any]) -> EnrichmentReport | None:
        self._step(record, "NASA_LOOKUP", "RUNNING")
        catalog = Catalog(self._store)
        document_id = record["document"]["document_id"]
        meta = catalog.document_meta(document_id)
        report = EnrichmentService(self._transport_factory()).enrich(meta, catalog.flat_parameters(document_id))
        workspace.write_json(workspace.area("enrichment") / f"{document_id}.json", report.model_dump(mode="json"))
        down = [m.source for m in report.matches if m.state == MatchState.SOURCE_UNAVAILABLE]
        found = [f"{m.source}: {m.source_record_id}" for m in report.matches
                 if m.state in (MatchState.MATCH_CONFIRMED, MatchState.MATCH_CANDIDATE)]
        if down and len(down) == len(report.matches):
            self._step(record, "NASA_LOOKUP", "FAILED",
                       "Fontes NASA indisponíveis. Você pode prosseguir com os dados do artigo.")
        else:
            detail = ("Correspondências: " + "; ".join(found) + ".") if found else "Nenhuma correspondência encontrada."
            if down:
                detail += f" Indisponíveis: {', '.join(down)}."
            self._step(record, "NASA_LOOKUP", "DONE", detail)
        ntrs = next((m for m in report.matches if m.source == "NTRS"), None)
        if ntrs and ntrs.title and not record["document"]["curated"] and not record["document"]["title"]:
            record["document"]["title"] = ntrs.title
        return report

    def _provenance(self, record: dict[str, Any], report: EnrichmentReport | None) -> None:
        self._step(record, "PROVENANCE", "RUNNING")
        result = verify_provenance(self._transport_factory(), report, record["sha256"])
        record["nasa_provenance"] = result
        workspace.write_json(workspace.area("provenance") / f"{record['document']['document_id']}.json", result)
        self._step(record, "PROVENANCE", "DONE" if result["state"] == "VERIFIED" else "FAILED"
                   if result["state"] == "MISMATCH" else "DONE", result["label_pt"])

    def _extract(self, record: dict[str, Any]) -> None:
        doc = record["document"]
        if doc["curated"]:
            self._step(record, "EXTRACT", "SKIPPED",
                       "Documento já presente no dataset curado; os registros existentes são usados.")
            return
        if not doc["has_text_layer"]:
            self._step(record, "EXTRACT", "SKIPPED", "O PDF não tem camada de texto (OCR não é feito nesta versão).")
            return
        if self._provider is None:
            self._step(record, "EXTRACT", "SKIPPED",
                       "IA desligada ou não configurada. O artigo fica disponível sem parâmetros extraídos.")
            return
        self._step(record, "EXTRACT", "RUNNING")
        pages = page_texts(self._dir(record["import_id"]) / "source.pdf", 1, extraction.MAX_PAGES_SENT)
        try:
            result = extraction.run_extraction(self._provider, pages, doc["document_id"], utc_now())
        except ProviderError as exc:
            self._step(record, "EXTRACT", "FAILED", f"A IA não respondeu ({exc.kind.value}). Nenhum valor foi criado.")
            return
        record["experiments"] = result["experiments"]
        record["extraction"] = {k: result[k] for k in ("model", "pages_sent", "rejected", "prompt_version")
                                if k in result}
        accepted = sum(len(e["parameters"]) for e in result["experiments"])
        if doc["page_count"] > len(result["pages_sent"]):
            record["warnings_pt"].append(
                f"A extração leu {len(result['pages_sent'])} de {doc['page_count']} páginas nesta versão.")
        self._step(record, "EXTRACT", "DONE",
                   f"{len(result['experiments'])} experimento(s), {accepted} parâmetro(s) com citação literal "
                   f"conferida, {len(result['rejected'])} proposta(s) descartada(s). Tudo aguarda revisão humana.")
