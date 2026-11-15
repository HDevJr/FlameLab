"""NASA NTRS — API pública documentada em https://ntrs.nasa.gov/api/openapi/ (sem autenticação).

Operações usadas (todas constam da especificação): GET /citations/{id} e GET /citations/search.
"""

from __future__ import annotations

from typing import Any

from backend.app.nasa.clients.http import SourceClient

BASE = "https://ntrs.nasa.gov/api"


def citation_summary(c: dict[str, Any]) -> dict[str, Any]:
    authors = [a.get("meta", {}).get("author", {}).get("name") for a in c.get("authorAffiliations") or []]
    pubs = c.get("publications") or []
    downloads = [
        {"name": d.get("name"), "pdf": d.get("links", {}).get("pdf"), "fulltext": d.get("links", {}).get("fulltext")}
        for d in c.get("downloads") or []
    ]
    return {
        "ntrs_id": str(c.get("id")),
        "title": c.get("title"),
        "sti_type": c.get("stiType"),
        "authors": [a for a in authors if a],
        "center": (c.get("center") or {}).get("name"),
        "publication_date": (pubs[0].get("publicationDate") or "")[:10] if pubs else None,
        "report_numbers": c.get("otherReportNumbers") or [],
        "keywords": c.get("keywords") or [],
        "subject_categories": c.get("subjectCategories") or [],
        "funding_numbers": [f.get("number") for f in c.get("fundingNumbers") or []],
        "distribution": c.get("distribution"),
        "related": c.get("related") or [],
        "downloads": downloads,
        "abstract": c.get("abstract"),
        "url": f"https://ntrs.nasa.gov/citations/{c.get('id')}",
    }


class NtrsClient(SourceClient):
    source = "NTRS"

    def get_citation(self, ntrs_id: str) -> dict[str, Any]:
        if not ntrs_id.isdigit():
            raise ValueError("ntrs_id deve ser numérico")
        return citation_summary(self._get_json(f"{BASE}/citations/{ntrs_id}"))

    def search(self, *, q: str | None = None, title: str | None = None, size: int = 10) -> list[dict[str, Any]]:
        params = {"page.size": str(max(1, min(size, 25)))}
        if q:
            params["q"] = q
        if title:
            params["title"] = title
        data = self._get_json(f"{BASE}/citations/search", params)
        return [citation_summary(r) for r in data.get("results") or []]
