"""NASA TechPort — especificação OpenAPI em https://techport.nasa.gov/api/specification.

Observado em 14/11/2026: a especificação declara o esquema `bearerAuth` (JWT), mas nenhuma
operação o exige, e as leituras usadas aqui responderam sem token. Como isso pode mudar, uma
resposta 401/403 é tratada como `SOURCE_UNAVAILABLE`, nunca como erro fatal, e nenhum token
de sessão é armazenado.

Operações usadas: GET /api/projects/search?query=… e GET /api/projects/{projectId}.
"""

from __future__ import annotations

import re
from typing import Any

from backend.app.nasa.clients.http import SourceClient

BASE = "https://techport.nasa.gov/api"


def _text(html: str | None) -> str | None:
    return re.sub(r"<[^>]+>", " ", html).strip() if html else None


class TechPortClient(SourceClient):
    source = "TECHPORT"

    def search_projects(self, query: str) -> list[dict[str, Any]]:
        data = self._get_json(f"{BASE}/projects/search", {"query": query})
        out = []
        for r in (data.get("results") or [])[:25]:
            pid = r.get("projectId") or r.get("project_id")
            out.append({"project_id": pid, "title": r.get("title"),
                        "url": f"https://techport.nasa.gov/projects/{pid}"})
        return out

    def get_project(self, project_id: int) -> dict[str, Any]:
        p = self._get_json(f"{BASE}/projects/{int(project_id)}").get("project") or {}
        return {"project_id": p.get("projectId"), "title": p.get("title"), "acronym": p.get("acronym"),
                "start": p.get("startDate"), "end": p.get("endDate"),
                "description": _text(p.get("description")),
                "url": f"https://techport.nasa.gov/projects/{p.get('projectId')}"}
