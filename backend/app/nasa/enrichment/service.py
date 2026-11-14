"""Enriquecimento NASA: descoberta de fontes por identificadores e metadados do artigo.

Regras:
- É opcional. Qualquer fonte pode falhar (`SOURCE_UNAVAILABLE`) sem interromper as demais.
- Nunca substitui valores do artigo nem promove registros (`promoted_records` é sempre 0).
- Correspondência de projeto/documento ≠ concordância de medições: parâmetros de ensaio só
  são comparados quando a fonte complementar expõe a mesma grandeza do mesmo ensaio.
- Não há correspondências fixas: tudo é calculado a partir de `DocumentMeta`.
"""

from __future__ import annotations

from typing import Any

from backend.app.nasa.clients.datacite import PSI_PUBLISHER, DataCiteClient
from backend.app.nasa.clients.http import SourceError, Transport
from backend.app.nasa.clients.ntrs import NtrsClient
from backend.app.nasa.clients.techport import TechPortClient
from backend.app.nasa.matching.matcher import (
    TITLE_COHERENT, TITLE_STRONG, author_overlap, key_words, title_similarity, title_tokens,
)
from backend.app.nasa.models import (
    DocumentMeta, EnrichmentRecord, EnrichmentReport, MatchState, MatchType, SourceMatch,
)
from backend.app.nasa.provenance.log import OperationLog, utc_now

PSI_NO_API_NOTE = (
    "O NASA PSI não publica API documentada. A descoberta usa o registro de DOI no DataCite; "
    "os arquivos de dados da investigação exigem consulta manual ao portal."
)


def _unavailable(source: str, exc: SourceError) -> SourceMatch:
    return SourceMatch(source=source, state=MatchState.SOURCE_UNAVAILABLE,
                       reasons_pt=[f"A fonte não respondeu ({exc.kind}). O processamento continua sem ela."])


class EnrichmentService:
    def __init__(self, transport: Transport, timeout: float = 15.0):
        self._transport = transport
        self._timeout = timeout

    def enrich(self, meta: DocumentMeta, parameters: list[dict[str, Any]] | None = None) -> EnrichmentReport:
        log = OperationLog()
        ntrs = NtrsClient(self._transport, log, self._timeout)
        datacite = DataCiteClient(self._transport, log, self._timeout)
        techport = TechPortClient(self._transport, log, self._timeout)
        warnings: list[str] = []
        records: list[EnrichmentRecord] = []

        ntrs_match, citation = self._ntrs(meta, ntrs)
        title = meta.title or (citation or {}).get("title")
        authors = meta.authors or (citation or {}).get("authors") or []
        authors_source = "artigo" if meta.authors else ("NTRS" if citation else None)
        doc_tokens = title_tokens(title)

        related = self._related(ntrs, title, citation, warnings) if title else []
        psi_match, psi = self._psi(meta, datacite, title, doc_tokens, authors)
        techport_match = self._techport(techport, title, doc_tokens)
        matches = [ntrs_match, psi_match, techport_match]

        if citation:
            records += self._metadata_records(meta, citation)
        if psi:
            records += self._psi_records(psi, authors, authors_source)
        for p in parameters or []:
            records.append(EnrichmentRecord(
                field=p["parameter"], label_pt=p.get("label_pt") or p["parameter"],
                scope="EXPERIMENT_PARAMETER", experiment_id=p.get("experiment_id"),
                original_value=p.get("value"), original_source=p.get("source"),
                state=MatchState.NOT_FOUND, review_status=p.get("status") or "NAO_REVISADO",
                divergence_pt=None,
                curation_decision="PENDENTE",
            ))
        if parameters:
            warnings.append(
                "Nenhuma fonte consultada expõe valores por ensaio em API documentada; os parâmetros "
                "do artigo não puderam ser confrontados com medições de outra fonte."
            )
        for m in matches:
            if m.state == MatchState.SOURCE_UNAVAILABLE:
                warnings.append(f"{m.source} indisponível; você pode prosseguir com os dados do artigo.")

        return EnrichmentReport(
            document_id=meta.document_id, generated_at=utc_now(), mode=self._transport.mode,
            document=meta, matches=matches, records=records, related_documents=related,
            operations=log.operations, warnings_pt=warnings, promoted_records=0,
        )

    # ---------- NTRS ----------
    def _ntrs(self, meta: DocumentMeta, ntrs: NtrsClient) -> tuple[SourceMatch, dict[str, Any] | None]:
        doc_tokens = title_tokens(meta.title)
        try:
            if meta.ntrs_id:
                c = ntrs.get_citation(meta.ntrs_id)
                sim = title_similarity(doc_tokens, title_tokens(c["title"])) if meta.title else None
                if sim is not None and sim < TITLE_COHERENT:
                    return SourceMatch(
                        source="NTRS", state=MatchState.CONFLICT, match_type=MatchType.IDENTIFIER,
                        source_record_id=c["ntrs_id"], source_url=c["url"], title=c["title"], score=sim,
                        reasons_pt=[f"O ID NTRS {meta.ntrs_id} foi encontrado no artigo, mas o título do "
                                    f"registro difere do título do artigo (semelhança {sim})."],
                    ), None
                reasons = [f"O ID NTRS {meta.ntrs_id} consta do artigo e existe no NTRS."]
                if sim is not None:
                    reasons.append(f"O título do registro é coerente com o do artigo (semelhança {sim}).")
                return SourceMatch(
                    source="NTRS", state=MatchState.MATCH_CONFIRMED, match_type=MatchType.IDENTIFIER,
                    source_record_id=c["ntrs_id"], source_url=c["url"], title=c["title"], score=sim,
                    reasons_pt=reasons, metadata=_ntrs_meta(c),
                    note_pt="Confirma a identidade do registro, não o conteúdo do arquivo nem medições.",
                ), c
            if not meta.title:
                return SourceMatch(source="NTRS", state=MatchState.NOT_QUERIED,
                                   reasons_pt=["O artigo não tem ID NTRS nem título identificado."]), None
            scored = []
            for c in ntrs.search(title=meta.title, size=10):
                scored.append((title_similarity(doc_tokens, title_tokens(c["title"])), c))
            scored.sort(key=lambda x: -x[0])
            rejected = [{"id": c["ntrs_id"], "title": c["title"], "score": s} for s, c in scored[:5]]
            if scored and scored[0][0] >= TITLE_STRONG:
                sim, c = scored[0]
                shared, _ = author_overlap(meta.authors, c["authors"])
                reasons = [f"Busca por título no NTRS: semelhança {sim} com o registro {c['ntrs_id']}."]
                if shared:
                    reasons.append(f"Autores em comum: {', '.join(shared)}.")
                reasons.append("Sem identificador forte no artigo: a correspondência exige revisão humana.")
                return SourceMatch(
                    source="NTRS", state=MatchState.MATCH_CANDIDATE,
                    match_type=MatchType.TITLE_AUTHORS if shared else MatchType.TITLE_ONLY,
                    source_record_id=c["ntrs_id"], source_url=c["url"], title=c["title"], score=sim,
                    reasons_pt=reasons, metadata=_ntrs_meta(c), rejected_candidates=rejected[1:],
                ), c
            return SourceMatch(source="NTRS", state=MatchState.NOT_FOUND, rejected_candidates=rejected,
                               reasons_pt=["Nenhum registro do NTRS tem título suficientemente semelhante."]), None
        except SourceError as exc:
            return _unavailable("NTRS", exc), None

    def _related(self, ntrs: NtrsClient, title: str, citation: dict[str, Any] | None,
                 warnings: list[str]) -> list[dict[str, Any]]:
        try:
            own = (citation or {}).get("ntrs_id")
            return [
                {"source": "NTRS", "ntrs_id": c["ntrs_id"], "title": c["title"], "sti_type": c["sti_type"],
                 "url": c["url"], "state": MatchState.ADDITIONAL_DATA_FOUND.value,
                 "note_pt": "Resultado de busca textual; relação com o artigo não verificada."}
                for c in ntrs.search(q=" ".join(key_words(title, 4)), size=6) if c["ntrs_id"] != own
            ][:5]
        except SourceError:
            warnings.append("Busca de documentos relacionados no NTRS indisponível.")
            return []

    # ---------- PSI (via DataCite) ----------
    def _psi(self, meta: DocumentMeta, datacite: DataCiteClient, title: str | None, doc_tokens: frozenset[str],
             authors: list[str]) -> tuple[SourceMatch, dict[str, Any] | None]:
        try:
            if meta.doi:
                d = datacite.get_doi(meta.doi)
                if d.get("publisher") == PSI_PUBLISHER:
                    return SourceMatch(
                        source="PSI", state=MatchState.MATCH_CONFIRMED, match_type=MatchType.IDENTIFIER,
                        source_record_id=d["investigation_id"] or d["doi"], source_url=d["url"],
                        title=d["title"], metadata=_psi_meta(d), note_pt=PSI_NO_API_NOTE,
                        reasons_pt=[f"O DOI {meta.doi} consta do artigo e foi registrado pelo NASA PSI."],
                    ), d
            words = key_words(title, 3)
            if not words:
                return SourceMatch(source="PSI", state=MatchState.NOT_QUERIED, note_pt=PSI_NO_API_NOTE,
                                   reasons_pt=["Sem título para pesquisar."]), None
            scored = []
            for d in datacite.search_psi(" ".join(words)):
                cand = title_tokens(d["title"], *d["subtitles"])
                scored.append((title_similarity(doc_tokens, cand), d))
            scored.sort(key=lambda x: -x[0])
            rejected = [{"id": d["investigation_id"] or d["doi"], "title": d["title"], "score": s}
                        for s, d in scored[:5]]
            if scored and scored[0][0] >= TITLE_STRONG:
                sim, d = scored[0]
                shared, _ = author_overlap(authors, d["creators"])
                reasons = [
                    f"DataCite: dataset do publicador \"{PSI_PUBLISHER}\" com título semelhante ao do "
                    f"artigo (semelhança {sim}).",
                ]
                if shared:
                    reasons.append(f"Pessoas em comum entre autores e criadores: {', '.join(shared)}.")
                reasons.append("Os dois registros não citam um ao outro por identificador: é candidato "
                               "até revisão humana.")
                return SourceMatch(
                    source="PSI", state=MatchState.MATCH_CANDIDATE,
                    match_type=MatchType.TITLE_AUTHORS if shared else MatchType.TITLE_ONLY,
                    source_record_id=d["investigation_id"] or d["doi"], source_url=d["url"],
                    title=d["title"], score=sim, reasons_pt=reasons, metadata=_psi_meta(d),
                    rejected_candidates=rejected[1:], note_pt=PSI_NO_API_NOTE,
                ), d
            return SourceMatch(source="PSI", state=MatchState.NOT_FOUND, rejected_candidates=rejected,
                               note_pt=PSI_NO_API_NOTE,
                               reasons_pt=["Nenhum dataset do NASA PSI no DataCite corresponde ao título."]), None
        except SourceError as exc:
            m = _unavailable("PSI", exc)
            m.note_pt = PSI_NO_API_NOTE
            return m, None

    # ---------- TechPort ----------
    def _techport(self, techport: TechPortClient, title: str | None, doc_tokens: frozenset[str]) -> SourceMatch:
        if not title:
            return SourceMatch(source="TECHPORT", state=MatchState.NOT_QUERIED,
                               reasons_pt=["Sem título para pesquisar."])
        words = key_words(title, 3)
        try:
            scored = [(title_similarity(doc_tokens, title_tokens(p["title"])), p)
                      for p in techport.search_projects(" ".join(words))]
        except SourceError as exc:
            return _unavailable("TECHPORT", exc)
        scored.sort(key=lambda x: -x[0])
        rejected = [{"id": p["project_id"], "title": p["title"], "score": s} for s, p in scored[:5]]
        if scored and scored[0][0] >= TITLE_STRONG:
            sim, p = scored[0]
            return SourceMatch(
                source="TECHPORT", state=MatchState.MATCH_CANDIDATE, match_type=MatchType.TITLE_ONLY,
                source_record_id=str(p["project_id"]), source_url=p["url"], title=p["title"], score=sim,
                rejected_candidates=rejected[1:],
                reasons_pt=[f"Projeto com título semelhante (semelhança {sim}). Projeto TechPort é um "
                            "registro de portfólio, não o experimento: exige revisão humana."],
            )
        return SourceMatch(
            source="TECHPORT", state=MatchState.NOT_FOUND, rejected_candidates=rejected,
            reasons_pt=["Nenhum projeto do TechPort tem título correspondente ao do artigo. "
                        "Projetos de tema parecido não são tratados como equivalentes."],
        )

    # ---------- registros por campo ----------
    def _metadata_records(self, meta: DocumentMeta, c: dict[str, Any]) -> list[EnrichmentRecord]:
        out = []
        if meta.title:
            same = title_tokens(meta.title) == title_tokens(c["title"])
            out.append(EnrichmentRecord(
                field="title", label_pt="Título", scope="DOCUMENT_METADATA",
                original_value=meta.title, original_source="artigo",
                complementary_value=c["title"], complementary_source="NTRS",
                complementary_source_id=c["ntrs_id"], match_type=MatchType.IDENTIFIER,
                state=MatchState.MATCH_CONFIRMED if same else MatchState.CONFLICT,
                divergence_pt=None if same else "Os títulos diferem em palavras distintivas.",
            ))
        if meta.authors:
            shared, near = author_overlap(meta.authors, c["authors"])
            only = len({*meta.authors}) - len(shared)
            out.append(EnrichmentRecord(
                field="authors", label_pt="Autores", scope="DOCUMENT_METADATA",
                original_value=meta.authors, original_source="artigo",
                complementary_value=c["authors"], complementary_source="NTRS",
                complementary_source_id=c["ntrs_id"],
                state=MatchState.CONFLICT if (near or only) else MatchState.MATCH_CONFIRMED,
                divergence_pt=_author_divergence(near, only),
            ))
        for field, label, value in (
            ("keywords", "Palavras-chave", c["keywords"]),
            ("report_numbers", "Números de relatório", c["report_numbers"]),
            ("publication_date", "Data de publicação", c["publication_date"]),
            ("subject_categories", "Categorias de assunto", c["subject_categories"]),
            ("fulltext", "Texto completo no NTRS", [d.get("pdf") for d in c["downloads"]]),
        ):
            if value:
                out.append(EnrichmentRecord(
                    field=field, label_pt=label, scope="DOCUMENT_METADATA",
                    complementary_value=value, complementary_source="NTRS",
                    complementary_source_id=c["ntrs_id"], state=MatchState.ADDITIONAL_DATA_FOUND,
                ))
        return out

    def _psi_records(self, d: dict[str, Any], authors: list[str], authors_source: str | None) -> list[EnrichmentRecord]:
        sid = d["investigation_id"] or d["doi"]
        out = []
        if authors:
            shared, near = author_overlap(authors, d["creators"])
            differs = bool(near) or len(shared) < len(set(authors)) or len(shared) < len(set(d["creators"]))
            out.append(EnrichmentRecord(
                field="people", label_pt="Autores × criadores do dataset", scope="DOCUMENT_METADATA",
                original_value=authors, original_source=authors_source,
                complementary_value=d["creators"], complementary_source="PSI (DataCite)",
                complementary_source_id=sid, match_type=MatchType.TITLE_AUTHORS,
                state=MatchState.CONFLICT if differs else MatchState.MATCH_CONFIRMED,
                divergence_pt=_author_divergence(near, len(set(authors)) - len(shared)) if differs else None,
            ))
        for field, label, value in (
            ("investigation_url", "Página da investigação", d["url"]),
            ("investigation_doi", "DOI da investigação", d["doi"]),
            ("data_license", "Licença dos dados", d["rights"]),
            ("investigation_description", "Descrição da investigação (objetivos e variáveis)", d["description"]),
        ):
            if value:
                out.append(EnrichmentRecord(
                    field=field, label_pt=label, scope="DOCUMENT_METADATA",
                    complementary_value=value, complementary_source="PSI (DataCite)",
                    complementary_source_id=sid, state=MatchState.ADDITIONAL_DATA_FOUND,
                ))
        return out


def _author_divergence(near: list[tuple[str, str]], only_in_original: int) -> str | None:
    parts = []
    if near:
        parts.append("grafias diferentes: " + "; ".join(f"{a} × {b}" for a, b in near))
    if only_in_original > len(near):
        parts.append("as listas de pessoas não coincidem")
    return "; ".join(parts) or None


def _ntrs_meta(c: dict[str, Any]) -> dict[str, Any]:
    return {k: c[k] for k in ("sti_type", "authors", "center", "publication_date", "report_numbers",
                              "keywords", "distribution", "downloads", "related")}


def _psi_meta(d: dict[str, Any]) -> dict[str, Any]:
    return {k: d[k] for k in ("doi", "publisher", "subtitles", "creators", "publication_year",
                              "resource_type", "rights", "related_identifiers", "version")}
