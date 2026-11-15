"""Resumo consolidado da análise de um documento (genérico: nada aqui conhece um artigo específico).

Separa três coisas que o usuário costuma confundir:
- PROCEDÊNCIA: o arquivo é o publicado pela NASA? (hash)
- REVISÃO: os números foram conferidos por uma pessoa na fonte?
- ENRIQUECIMENTO: o que outras fontes NASA dizem sobre o mesmo trabalho? (nunca valida números)
"""

from __future__ import annotations

from typing import Any, Callable

from backend.app import workspace
from backend.app.catalog.service import Catalog
from backend.app.nasa.provenance.log import utc_now

COMPAT_PT = {
    "COMPATIBLE": "compatível com o FDS",
    "MISSING_PARAMETERS": "faltam parâmetros para o FDS",
    "UNSUPPORTED_PHYSICS": "física fora do alcance do FDS",
    "REQUIRES_REVIEW": "requer revisão antes de qualquer simulação",
}
MATCH_PT = {
    "MATCH_CONFIRMED": "confirmada", "MATCH_CANDIDATE": "candidata (precisa de revisão humana)",
    "NOT_FOUND": "não encontrada", "CONFLICT": "em conflito", "SOURCE_UNAVAILABLE": "indisponível",
    "NOT_QUERIED": "não consultada",
}


def _pages(n: int) -> str:
    return f"{n} página" + ("" if n == 1 else "s")


def build_analysis(catalog: Catalog, document_id: str, compat: Callable[[str], dict | None]) -> dict[str, Any] | None:
    doc = catalog.document(document_id)
    if doc is None:
        return None
    imp = catalog.import_for_document(document_id)
    enrichment = workspace.read_json(workspace.area("enrichment") / f"{workspace.safe_id(document_id)}.json")
    coverage = _coverage(doc, imp)

    experiments = []
    for summary in doc["experiments"]:
        exp = catalog.experiment(summary["experiment_id"])
        if exp is None:
            continue
        c = compat(exp["experiment_id"]) or {}
        experiments.append({
            "experiment_id": exp["experiment_id"], "label": exp["label"], "phenomena": exp["phenomena"],
            "origin": exp["origin"], "parameters": exp["review"]["total"], "reviewed": exp["review"]["reviewed"],
            "pending": exp["review"]["pending"], "gaps": exp["review"]["gaps"],
            "fds": {"status": c.get("status"), "label_pt": COMPAT_PT.get(c.get("status", ""), "não avaliado"),
                    "reasons_pt": (c.get("reasons_pt") or [])[:3], "can_simulate": bool((c.get("actions") or {}).get("simulate"))},
        })
    totals = {k: sum(e[k] for e in experiments) for k in ("parameters", "reviewed", "pending", "gaps")}
    totals["experiments"] = len(experiments)

    matches = (enrichment or {}).get("matches") or []
    sources = [{"source": m["source"], "state": m["state"], "state_pt": MATCH_PT.get(m["state"], m["state"]),
                "record_id": m.get("source_record_id"), "url": m.get("source_url"), "title": m.get("title")}
               for m in matches]
    divergences = [{"field": r["field"], "label_pt": r["label_pt"], "divergence_pt": r["divergence_pt"],
                    "complementary_source": r.get("complementary_source")}
                   for r in (enrichment or {}).get("records") or [] if r["state"] == "CONFLICT"]
    prov = doc["nasa_provenance"]

    conclusions = [_provenance_sentence(prov), coverage["summary_pt"]]
    if experiments:
        conclusions.append(f"Foram identificados {totals['experiments']} experimento(s) com {totals['parameters']} "
                           f"parâmetro(s) e {totals['gaps']} lacuna(s).")
    else:
        conclusions.append("Nenhum experimento foi extraído. O artigo continua disponível para consulta e fontes NASA.")
    if totals["parameters"]:
        conclusions.append(f"{totals['reviewed']} parâmetro(s) foram conferidos por uma pessoa; "
                           f"{totals['pending']} aguardam revisão.")
    if sources:
        conclusions.append("Fontes NASA: " + "; ".join(
            f"{s['source']} {s['state_pt']}" + (f" ({s['record_id']})" if s["record_id"] else "") for s in sources) + ".")
    elif enrichment is None:
        conclusions.append("A consulta às fontes NASA ainda não foi executada para este documento.")
    if divergences:
        conclusions.append(f"{len(divergences)} divergência(s) de metadados entre fontes (não são divergências de medição).")
    sim = [e for e in experiments if e["fds"]["can_simulate"]]
    conclusions.append(
        "Simulação FDS disponível para " + ", ".join(e["label"] for e in sim) + "." if sim
        else "Nenhum experimento está pronto para simulação no FDS; os motivos estão em cada experimento.")

    return {
        "generated_at": utc_now(),
        "document": {"document_id": document_id, "title": doc["title"], "origin": doc["origin"],
                     "import_id": doc.get("import_id"), "sha256": doc.get("sha256"),
                     "pages": (imp or {}).get("document", {}).get("page_count") or coverage.get("total_pages"),
                     "url": doc.get("url")},
        "provenance": prov, "coverage": coverage, "experiments": experiments, "totals": totals,
        "sources": sources, "divergences": divergences,
        "enrichment": {"available": enrichment is not None, "mode": (enrichment or {}).get("mode"),
                       "generated_at": (enrichment or {}).get("generated_at"),
                       "warnings_pt": (enrichment or {}).get("warnings_pt") or [],
                       "related_count": len((enrichment or {}).get("related_documents") or [])},
        "conclusions_pt": conclusions,
        "not_validated_pt": [
            "Procedência verificada não significa números conferidos: a procedência diz que o arquivo é o publicado; "
            "a revisão diz que uma pessoa conferiu cada valor na fonte.",
            "Fontes NASA relacionadas contextualizam o trabalho; elas não validam os números do artigo.",
            "Experimentos propostos pela IA são hipóteses de leitura até a revisão humana.",
        ],
        "metrics": (imp or {}).get("metrics"),
        "steps": (imp or {}).get("steps"),
    }


def _coverage(doc: dict[str, Any], imp: dict[str, Any] | None) -> dict[str, Any]:
    cov = (imp or {}).get("coverage")
    if cov:
        return cov
    if doc["origin"] == "CURATED":
        return {"mode": "CURATED", "total_pages": (imp or {}).get("document", {}).get("page_count"),
                "pages_processed": [], "processed_ranges": "", "pages_not_processed": [], "not_processed_ranges": "",
                "pages_without_text": [], "without_text_ranges": "", "reasons_pt": [], "batches": [],
                "summary_pt": "Os valores vêm do dataset curado pela equipe (leitura assistida de trechos "
                              "específicos do relatório, com página e tabela de cada valor). O PDF completo "
                              "não foi lido automaticamente por IA."}
    return {"mode": "NONE", "total_pages": (imp or {}).get("document", {}).get("page_count"), "pages_processed": [],
            "processed_ranges": "", "pages_not_processed": [], "not_processed_ranges": "", "pages_without_text": [],
            "without_text_ranges": "", "reasons_pt": [], "summary_pt": "Nenhuma leitura automática foi feita."}


def _provenance_sentence(prov: dict[str, Any]) -> str:
    state = prov["state"]
    if state == "VERIFIED":
        return "Origem NASA verificada: o arquivo é idêntico ao publicado no NTRS (mesmo SHA-256)."
    if state == "MISMATCH":
        return "Atenção: o arquivo difere do publicado no NTRS. Não o trate como a publicação original."
    if state == "CANDIDATE":
        return "Um registro NASA correspondente foi encontrado, mas o arquivo não foi comparado com o original; origem NÃO verificada."
    return "Origem NASA não confirmada: o documento não é tratado como publicação NASA validada."


def coverage_summary(cov: dict[str, Any]) -> str:
    """Frase de cobertura (usada também ao fim da extração)."""
    total = cov.get("total_pages") or 0
    done = len(cov.get("pages_processed") or [])
    if cov["mode"] == "AI_FULL":
        return f"A IA leu todas as páginas com texto ({cov['processed_ranges']}; {_pages(done)} de {total})."
    if cov["mode"] == "AI_PARTIAL":
        text = f"Leitura parcial: a IA leu {_pages(done)} de {total} ({cov['processed_ranges']})"
        if cov.get("not_processed_ranges"):
            text += f"; NÃO leu {cov['not_processed_ranges']}"
        if cov.get("reasons_pt"):
            text += " — " + "; ".join(cov["reasons_pt"])
        return text + "."
    return "A IA não leu nenhuma página; nenhum parâmetro foi extraído por ela."
