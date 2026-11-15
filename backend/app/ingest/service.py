"""Importação de artigos em PDF: recebe, identifica, verifica a origem NASA, lê, extrai (em lotes),
pesquisa fontes complementares, compara e prepara o relatório de análise.

Cada etapa grava seu estado REAL em `var/imports/<id>/import.json`, com resumo legível, detalhes
técnicos, limitação (se houver) e tempo medido. Não há percentuais inventados. A consulta NASA e a
IA são opcionais: se falharem, a etapa fica FAILED/SKIPPED e o artigo continua disponível.
"""

from __future__ import annotations

import os
import re
import threading
import time
from pathlib import Path
from typing import Any, BinaryIO, Callable

from backend.app import workspace
from backend.app.analysis import build_analysis, coverage_summary
from backend.app.assistant.provider import LLMProvider
from backend.app.catalog.service import PROVENANCE_LABELS, Catalog
from backend.app.dataset.store import DatasetStore
from backend.app.ingest import extraction
from backend.app.ingest.pdf import (
    MAX_UPLOAD_BYTES, PdfRejected, inspect_pdf, looks_like_pdf, page_texts, sha256_bytes_file,
)
from backend.app.nasa.clients.http import SourceError, Transport
from backend.app.nasa.enrichment.service import EnrichmentService
from backend.app.nasa.models import MatchState, MatchType, SourceMatch
from backend.app.nasa.provenance.log import utc_now

STEPS = [
    ("RECEIVE", "Arquivo recebido"),
    ("IDENTIFY", "Identificando o documento"),
    ("ORIGIN", "Verificando a origem NASA"),
    ("READ", "Lendo o PDF"),
    ("EXTRACT", "Extraindo experimentos e parâmetros"),
    ("SOURCES", "Pesquisando fontes complementares NASA"),
    ("COMPARE", "Comparando informações"),
    ("REPORT", "Preparando o relatório de análise"),
]
NTRS_FILE_MAX = 200 * 1024 * 1024


def max_batches_from_env() -> int:
    try:
        return max(1, min(40, int(os.environ.get("FLAMELAB_EXTRACT_MAX_BATCHES", extraction.DEFAULT_MAX_BATCHES))))
    except ValueError:
        return extraction.DEFAULT_MAX_BATCHES


def verify_provenance(transport: Transport, ntrs: SourceMatch | None, local_sha256: str) -> dict[str, Any]:
    """Procedência NASA: só é VERIFIED quando o arquivo é idêntico ao que o NTRS distribui.
    Texto ou aparência do PDF nunca bastam."""
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
    def __init__(self, store: "DatasetStore | Callable[[], DatasetStore]", transport_factory: Callable[[], Transport],
                 provider: LLMProvider | None, run_async: bool = True,
                 compat: Callable[[str], dict | None] | None = None, max_batches: int | None = None,
                 quota_wait_s: float = extraction.QUOTA_RETRY_WAIT_S):
        self._store_src = store if callable(store) else (lambda: store)
        self._transport_factory = transport_factory
        self._provider = provider
        self._async = run_async
        self._compat = compat or (lambda _id: None)
        self._max_batches = max_batches if max_batches is not None else max_batches_from_env()
        self._quota_wait_s = quota_wait_s
        self._lock = threading.Lock()
        self._t0: dict[tuple[str, str], float] = {}

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

    def _step(self, record: dict[str, Any], key: str, state: str, summary: str | None = None,
              technical: list[str] | None = None, limitation: str | None = None,
              duration_ms: int | None = None) -> None:
        """Atualiza uma etapa. O tempo é medido entre RUNNING e o estado final (ou informado)."""
        for step in record["steps"]:
            if step["key"] != key:
                continue
            tk = (record["import_id"], key)
            if state == "RUNNING":
                if step["state"] != "RUNNING":  # atualizações de resumo não reiniciam o cronômetro
                    self._t0[tk] = time.monotonic()
                    step["started_at"] = utc_now()
                    step["finished_at"] = None
                    step["duration_ms"] = None
            elif state in ("DONE", "FAILED", "SKIPPED"):
                t0 = self._t0.pop(tk, None)
                if duration_ms is None and t0 is not None:
                    duration_ms = int((time.monotonic() - t0) * 1000)
                step["finished_at"] = utc_now()
                step["duration_ms"] = duration_ms if duration_ms is not None else step.get("duration_ms") or 0
                step["started_at"] = step.get("started_at") or step["finished_at"]
            step["state"] = state
            if summary is not None:
                step["summary_pt"] = summary
            if technical is not None:
                step["technical"] = technical
            step["limitation_pt"] = limitation
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
        t_start = time.monotonic()
        tmp = workspace.area("incoming") / f"{threading.get_ident()}-{utc_now().replace(':', '')}.part"
        try:
            self._write_upload(stream, tmp)
            receive_ms = int((time.monotonic() - t_start) * 1000)
            t1 = time.monotonic()
            sha = sha256_bytes_file(tmp)
            info = inspect_pdf(tmp)
            identify_ms = int((time.monotonic() - t1) * 1000)
            size = tmp.stat().st_size
        except PdfRejected:
            tmp.unlink(missing_ok=True)
            raise
        import_id = "IMP-" + sha[:12]
        folder = self._dir(import_id)
        folder.mkdir(parents=True, exist_ok=True)
        tmp.replace(folder / "source.pdf")

        store = self._store_src()
        curated = next((d for d in store.documents.values() if d.sha256 == sha), None)
        document_id = curated.document_id if curated else "DOC-" + sha[:12]
        display = re.sub(r"[^\w .()\-]", "_", Path(filename or "arquivo.pdf").name)[:120]
        record = {
            "import_id": import_id, "filename": display, "size_bytes": size, "sha256": sha,
            "received_at": utc_now(), "status": "PROCESSING",
            "steps": [{"key": k, "label_pt": label, "state": "PENDING", "summary_pt": None, "technical": [],
                       "limitation_pt": None, "started_at": None, "finished_at": None, "duration_ms": None}
                      for k, label in STEPS],
            "document": {
                "document_id": document_id, "curated": curated is not None,
                "title": curated.title if curated else info.title, "page_count": info.page_count,
                "has_text_layer": info.has_text_layer, "year": info.year,
                "identifiers": {"report_numbers": info.report_numbers, "ntrs_ids": info.ntrs_ids, "dois": info.dois},
            },
            "nasa_provenance": None, "experiments": [], "extraction": None, "coverage": None,
            "warnings_pt": [], "metrics": {"started_at": utc_now(), "total_ms": None},
        }
        self._step(record, "RECEIVE", "DONE", f"Arquivo recebido: {display} ({size / 1e6:.1f} MB).",
                   [f"nome: {display}", f"tamanho: {size} bytes", f"limite de upload: {MAX_UPLOAD_BYTES} bytes"],
                   duration_ms=receive_ms)
        found = info.report_numbers + info.ntrs_ids + info.dois
        title = record["document"]["title"]
        self._step(record, "IDENTIFY", "DONE",
                   (f"Título: {title}. " if title else "Título não identificado. ")
                   + (f"Identificadores no texto: {', '.join(found)}." if found else "Nenhum identificador NASA no texto."),
                   [f"SHA-256: {sha}", f"{info.page_count} páginas", f"camada de texto: {'sim' if info.has_text_layer else 'não'}",
                    f"identificadores: {', '.join(found) or 'nenhum'}",
                    "O SHA-256 é a impressão digital do arquivo: dois arquivos iguais têm o mesmo valor."],
                   duration_ms=identify_ms)
        if self._async:
            threading.Thread(target=self._pipeline, args=(record, t_start), daemon=True).start()
        else:
            self._pipeline(record, t_start)
        return record

    # ---------------------------------------------------------------- pipeline
    def _pipeline(self, record: dict[str, Any], t_start: float) -> None:
        try:
            session = self._origin(record)
            pages = self._read(record)
            self._extract(record, pages)
            self._sources(record, session)
            report = self._compare(record, session)
            self._report(record, report)
            record["status"] = "DONE"
        except Exception:  # noqa: BLE001 - falha inesperada fica registrada, sem derrubar o servidor
            record["status"] = "FAILED"
            record["warnings_pt"].append("Falha inesperada no processamento; consulte os logs do servidor.")
        record["metrics"]["total_ms"] = int((time.monotonic() - t_start) * 1000)
        record["metrics"]["finished_at"] = utc_now()
        record["metrics"]["per_step_ms"] = {s["key"]: s["duration_ms"] for s in record["steps"]}
        self._save(record)

    def _catalog(self) -> Catalog:
        return Catalog(self._store_src)

    def _origin(self, record: dict[str, Any]):
        self._step(record, "ORIGIN", "RUNNING", "Consultando o NTRS e comparando o arquivo com o publicado…")
        meta = self._catalog().document_meta(record["document"]["document_id"])
        transport = self._transport_factory()
        session = EnrichmentService(transport).session(meta)
        ntrs = session.origin()
        prov = verify_provenance(transport, ntrs, record["sha256"])
        record["nasa_provenance"] = prov
        workspace.write_json(workspace.area("provenance") / f"{record['document']['document_id']}.json", prov)
        by_id = ntrs.match_type == MatchType.IDENTIFIER and ntrs.state in (MatchState.MATCH_CONFIRMED, MatchState.MATCH_CANDIDATE)
        if ntrs.title and not record["document"]["curated"] and (by_id or not record["document"]["title"]):
            # título lido do PDF pode ter erro de OCR; o registro do NTRS, achado por identificador, é a fonte melhor
            record["document"]["title_read_from_pdf"] = record["document"]["title"]
            record["document"]["title"] = ntrs.title
        state = "FAILED" if prov["state"] == "MISMATCH" else "DONE"
        limitation = None if prov["state"] == "VERIFIED" else (
            "A origem NASA NÃO foi verificada; o documento não é tratado como publicação NASA validada.")
        self._step(record, "ORIGIN", state, prov["label_pt"], prov["reasons_pt"], limitation)
        return session

    def _read(self, record: dict[str, Any]) -> dict[int, str] | None:
        self._step(record, "READ", "RUNNING", "Extraindo o texto de cada página…")
        doc = record["document"]
        pages = page_texts(self._dir(record["import_id"]) / "source.pdf")
        with_text = sum(1 for t in pages.values() if t.strip())
        doc["pages_with_text"] = with_text
        if not doc["has_text_layer"] or with_text == 0:
            self._step(record, "READ", "DONE", f"{len(pages)} páginas; nenhuma com texto selecionável.",
                       [f"{len(pages)} páginas, {with_text} com texto"],
                       "O PDF não tem camada de texto (OCR não é feito nesta versão): nada pode ser extraído.")
            return None
        empty = len(pages) - with_text
        self._step(record, "READ", "DONE", f"{len(pages)} páginas lidas; {with_text} com texto."
                   + (f" {empty} sem texto (figuras ou imagens)." if empty else ""),
                   [f"{len(pages)} páginas, {with_text} com texto, {sum(len(t) for t in pages.values())} caracteres"],
                   None if not empty else f"{empty} página(s) sem texto não podem ser lidas (sem OCR).")
        return pages

    def _extract(self, record: dict[str, Any], pages: dict[int, str] | None) -> None:
        doc = record["document"]
        total = doc["page_count"]
        if doc["curated"]:
            record["coverage"] = None
            self._step(record, "EXTRACT", "SKIPPED",
                       "Este documento já está no dataset curado; os registros da equipe são usados.",
                       ["Nenhuma chamada à IA foi feita para este documento."])
            return
        if pages is None:
            record["coverage"] = self._none_coverage(total, "o PDF não tem camada de texto")
            self._step(record, "EXTRACT", "SKIPPED", "Sem texto para ler.", None, "Nada foi extraído.")
            return
        if self._provider is None:
            record["coverage"] = self._none_coverage(total, "IA desligada ou não configurada")
            self._step(record, "EXTRACT", "SKIPPED",
                       "IA desligada ou não configurada. O artigo fica disponível sem parâmetros extraídos.", None,
                       "Nenhuma página foi lida por IA.")
            return
        self._step(record, "EXTRACT", "RUNNING", "Preparando os lotes de páginas…")

        def on_batch(i: int, n: int, numbers: list[int]) -> None:
            record["extract_progress"] = {"completed": i - 1, "total": n}  # lotes já concluídos, para o indicador de progresso
            self._step(record, "EXTRACT", "RUNNING",
                       f"Lote {i} de {n}: IA lendo as páginas {extraction.ranges(numbers)}…")

        def on_wait(i: int, seconds: float) -> None:
            self._step(record, "EXTRACT", "RUNNING",
                       f"Lote {i}: limite de uso da IA atingido; aguardando {seconds:.0f} s antes de tentar de novo…")

        result = extraction.run_batched(self._provider, pages, doc["document_id"], utc_now(),
                                        max_batches=self._max_batches, on_batch=on_batch, on_wait=on_wait,
                                        quota_wait_s=self._quota_wait_s)
        cov = result["coverage"]
        cov["summary_pt"] = coverage_summary(cov)
        record["coverage"] = cov
        record["experiments"] = result["experiments"]
        record["extraction"] = {k: result[k] for k in ("model", "rejected", "prompt_version", "batches",
                                                         "batches_planned_total")}
        accepted = sum(len(e["parameters"]) for e in result["experiments"])
        technical = [f"modelo: {result['model']}", f"prompt: {result['prompt_version']}",
                     f"lotes: {len(result['batches'])} executado(s) de {result['batches_planned_total']} planejado(s)"]
        for b in result["batches"]:
            tok = (b.get("usage") or {}).get("total_tokens")
            technical.append(
                f"lote {b['batch']}: páginas {b['pages']}, {b['chars']} caracteres, {b['duration_ms']} ms, "
                f"{b['accepted']} aceito(s), {b['rejected']} descartado(s)"
                + (f", {tok} tokens" if tok else "") + (f", esperou {b['waited_s']:.0f} s (limite de uso)" if b.get("waited_s") else "")
                + (f", ERRO {b['error']}" if b.get("error") else ""))
        technical.append(f"descartes: {len(result['rejected'])} (citação não literal, valor fora da citação ou página inválida)")
        limitation = cov["summary_pt"] if cov["mode"] != "AI_FULL" else None
        state = "FAILED" if cov["mode"] == "NONE" else "DONE"
        self._step(record, "EXTRACT", state,
                   f"{len(result['experiments'])} experimento(s) e {accepted} parâmetro(s) com citação literal "
                   f"conferida pelo código; {len(result['rejected'])} proposta(s) descartada(s). {cov['summary_pt']} "
                   "Tudo aguarda revisão humana.", technical, limitation)
        if cov["mode"] == "AI_PARTIAL":
            record["warnings_pt"].append(cov["summary_pt"])

    @staticmethod
    def _none_coverage(total: int, why: str) -> dict[str, Any]:
        return {"mode": "NONE", "total_pages": total, "pages_processed": [], "processed_ranges": "",
                "pages_not_processed": [], "not_processed_ranges": "", "pages_without_text": [],
                "without_text_ranges": "", "reasons_pt": [why], "batches": [],
                "summary_pt": f"A IA não leu nenhuma página ({why})."}

    def _sources(self, record: dict[str, Any], session) -> None:
        self._step(record, "SOURCES", "RUNNING", "Pesquisando documentos relacionados, o PSI e o TechPort…")
        session.sources()
        names = {"PSI": session.psi_match, "TechPort": session.techport_match}
        down = [n for n, m in names.items() if m.state == MatchState.SOURCE_UNAVAILABLE]
        parts = [f"{n}: {m.state.value}" + (f" ({m.source_record_id})" if m.source_record_id else "")
                 for n, m in names.items()]
        summary = "; ".join(parts) + f"; {len(session.related)} documento(s) possivelmente relacionado(s)."
        technical = [r for m in names.values() for r in m.reasons_pt] + [f"{len(session.log.operations)} chamada(s) de API"]
        if len(down) == len(names):
            self._step(record, "SOURCES", "FAILED", "Fontes NASA indisponíveis.", technical,
                       "Você pode prosseguir com os dados do artigo; a consulta pode ser repetida.")
        else:
            self._step(record, "SOURCES", "DONE", summary, technical,
                       f"Indisponíveis: {', '.join(down)}." if down else None)

    def _compare(self, record: dict[str, Any], session):
        self._step(record, "COMPARE", "RUNNING", "Comparando metadados e parâmetros entre as fontes…")
        catalog = self._catalog()
        report = session.compare(catalog.flat_parameters(record["document"]["document_id"]))
        workspace.write_json(workspace.area("enrichment") / f"{record['document']['document_id']}.json",
                             report.model_dump(mode="json"))
        conflicts = [r for r in report.records if r.state == MatchState.CONFLICT]
        compared = [r for r in report.records if r.scope == "DOCUMENT_METADATA"]
        self._step(record, "COMPARE", "DONE",
                   f"{len(compared)} campo(s) de metadados comparado(s); {len(conflicts)} divergência(s). "
                   "Os valores do artigo não foram alterados nem promovidos.",
                   [f"{r.label_pt}: {r.divergence_pt}" for r in conflicts] or ["sem divergências de metadados"],
                   None)
        return report

    def _report(self, record: dict[str, Any], _report) -> None:
        self._step(record, "REPORT", "RUNNING", "Consolidando o resumo da análise…")
        self._save(record)  # o resumo lê o registro do disco
        analysis = build_analysis(self._catalog(), record["document"]["document_id"], self._compat)
        if analysis is not None:
            workspace.write_json(workspace.area("analysis") / f"{record['document']['document_id']}.json", analysis)
        self._step(record, "REPORT", "DONE", "Resumo da análise pronto.",
                   [f"documento: {record['document']['document_id']}"])
