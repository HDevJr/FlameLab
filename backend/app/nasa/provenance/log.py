"""Registro das operações de API realmente executadas (online ou por fixture)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from backend.app.nasa.models import AccessMode, ApiOperation


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class OperationLog:
    def __init__(self) -> None:
        self.operations: list[ApiOperation] = []

    def record(self, *, source: str, method: str, url: str, mode: AccessMode, status: int | None,
               body: bytes | None, error: str | None, elapsed_ms: int | None) -> None:
        self.operations.append(ApiOperation(
            source=source, method=method, url=url, mode=mode, http_status=status,
            ok=error is None and status is not None and 200 <= status < 300, error=error,
            response_sha256=hashlib.sha256(body).hexdigest() if body is not None else None,
            response_bytes=len(body) if body is not None else None,
            at=utc_now(), elapsed_ms=elapsed_ms,
        ))
