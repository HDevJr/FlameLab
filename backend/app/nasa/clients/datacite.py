"""DataCite — API pública documentada (https://support.datacite.org/docs/api).

O NASA PSI não publica uma API documentada e estável. O que o PSI expõe de forma verificável
são os DOIs que ele registra no DataCite (publicador "NASA PSI"), cujo campo `url` aponta para
a página da investigação. Este cliente consulta só o DataCite; nada é pedido a psi.nasa.gov.
"""

from __future__ import annotations

import re
from typing import Any

from backend.app.nasa.clients.http import SourceClient

BASE = "https://api.datacite.org"
PSI_PUBLISHER = "NASA PSI"


def doi_summary(item: dict[str, Any]) -> dict[str, Any]:
    a = item.get("attributes") or {}
    titles = a.get("titles") or []
    url = a.get("url")
    m = re.search(r"/investigations/([A-Za-z0-9\-]+)$", url or "")
    return {
        "doi": a.get("doi"),
        "publisher": a.get("publisher"),
        "title": next((t.get("title") for t in titles if not t.get("titleType")), None),
        "subtitles": [t.get("title") for t in titles if t.get("titleType")],
        "creators": [c.get("name") for c in a.get("creators") or [] if c.get("name")],
        "publication_year": a.get("publicationYear"),
        "url": url,
        "investigation_id": m.group(1) if m else None,
        "resource_type": (a.get("types") or {}).get("resourceTypeGeneral"),
        "rights": [r.get("rights") for r in a.get("rightsList") or []],
        "subjects": [s.get("subject") for s in a.get("subjects") or []],
        "description": next((d.get("description") for d in a.get("descriptions") or []), None),
        "related_identifiers": a.get("relatedIdentifiers") or [],
        "version": a.get("version"),
    }


class DataCiteClient(SourceClient):
    source = "DATACITE"

    def get_doi(self, doi: str) -> dict[str, Any]:
        if not re.fullmatch(r"10\.\d{4,9}/[^\s?#]+", doi):
            raise ValueError("DOI inválido")
        return doi_summary(self._get_json(f"{BASE}/dois/{doi}").get("data") or {})

    def search_psi(self, title_phrase: str, size: int = 10) -> list[dict[str, Any]]:
        """Datasets registrados pelo NASA PSI cujo título contém as palavras dadas."""
        words = [w for w in re.findall(r"[A-Za-z0-9]+", title_phrase) if len(w) > 2][:6]
        if not words:
            return []
        query = f'publisher:"{PSI_PUBLISHER}" AND titles.title:({" AND ".join(words)})'
        data = self._get_json(f"{BASE}/dois", {"query": query, "page[size]": str(max(1, min(size, 25)))})
        return [doi_summary(i) for i in data.get("data") or []]
