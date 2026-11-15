"""Transporte HTTP mínimo e restrito para as fontes NASA.

- Só GET, só HTTPS, só hosts da lista permitida (sem redirecionamento para outros hosts).
- Timeout e limite de tamanho por resposta.
- Nenhuma credencial é enviada. Erros viram `SourceError` com mensagem curta.
"""

from __future__ import annotations

from collections.abc import Callable

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Protocol

from backend.app.nasa.models import AccessMode
from backend.app.nasa.provenance.log import OperationLog

ALLOWED_HOSTS = frozenset({"ntrs.nasa.gov", "techport.nasa.gov", "api.datacite.org"})
MAX_BYTES = 8 * 1024 * 1024
USER_AGENT = "flamelab-research-prototype/0.3"


class SourceError(Exception):
    def __init__(self, kind: str, status: int | None = None):
        self.kind = kind  # TIMEOUT | HTTP_ERROR | NETWORK | TOO_LARGE | INVALID_JSON | HOST_NOT_ALLOWED
        self.status = status
        super().__init__(f"{kind} (status={status})")


class Transport(Protocol):
    mode: AccessMode

    def get(self, url: str, params: dict[str, str] | None, timeout: float) -> tuple[int, bytes]: ...

    def stream_sha256(self, url: str, timeout: float, max_bytes: int, progress: "Callable[[int, int | None], None] | None" = None) -> tuple[str, int]: ...


class _NoRedirectAway(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).hostname not in ALLOWED_HOSTS:
            raise SourceError("HOST_NOT_ALLOWED")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class UrllibTransport:
    mode = AccessMode.ONLINE

    def __init__(self) -> None:
        self._opener = urllib.request.build_opener(_NoRedirectAway())

    def get(self, url: str, params: dict[str, str] | None, timeout: float) -> tuple[int, bytes]:
        full = url + ("?" + urllib.parse.urlencode(params) if params else "")
        req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with self._opener.open(req, timeout=timeout) as resp:
                body = resp.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    raise SourceError("TOO_LARGE", resp.status)
                return resp.status, body
        except urllib.error.HTTPError as exc:
            raise SourceError("HTTP_ERROR", exc.code) from None
        except TimeoutError:
            raise SourceError("TIMEOUT") from None
        except urllib.error.URLError as exc:
            kind = "TIMEOUT" if isinstance(exc.reason, TimeoutError) else "NETWORK"
            raise SourceError(kind) from None
        except OSError:
            raise SourceError("NETWORK") from None


    def stream_sha256(self, url: str, timeout: float, max_bytes: int, progress=None) -> tuple[str, int]:
        """SHA-256 e tamanho de um arquivo remoto, sem guardá-lo em disco. `progress(bytes_lidos, total|None)` é opcional."""
        if urllib.parse.urlsplit(url).scheme != "https" or urllib.parse.urlsplit(url).hostname not in ALLOWED_HOSTS:
            raise SourceError("HOST_NOT_ALLOWED")
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        digest, size = hashlib.sha256(), 0
        try:
            with self._opener.open(req, timeout=timeout) as resp:
                declared = int(resp.headers.get("Content-Length") or 0) or None
                while chunk := resp.read(1024 * 1024):
                    size += len(chunk)
                    if progress:
                        progress(size, declared)
                    if size > max_bytes:
                        raise SourceError("TOO_LARGE", resp.status)
                    digest.update(chunk)
        except urllib.error.HTTPError as exc:
            raise SourceError("HTTP_ERROR", exc.code) from None
        except (TimeoutError, urllib.error.URLError, OSError):
            raise SourceError("NETWORK") from None
        return digest.hexdigest(), size


class SourceClient:
    """Base dos clientes: valida host, mede tempo e registra cada operação."""

    source = "?"

    def __init__(self, transport: Transport, log: OperationLog, timeout: float = 15.0):
        self._transport = transport
        self._log = log
        self._timeout = timeout

    def _record(self, shown: str, status: int | None, body: bytes | None, error: str | None,
                elapsed: int | None) -> None:
        self._log.record(source=self.source, method="GET", url=shown, mode=self._transport.mode,
                         status=status, body=body, error=error, elapsed_ms=elapsed)

    def _get_json(self, url: str, params: dict[str, str] | None = None) -> Any:
        parts = urllib.parse.urlsplit(url)
        shown = url + ("?" + urllib.parse.urlencode(params) if params else "")
        if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
            self._record(shown, None, None, "HOST_NOT_ALLOWED", None)
            raise SourceError("HOST_NOT_ALLOWED")
        t0 = time.monotonic()
        try:
            status, body = self._transport.get(url, params, self._timeout)
        except SourceError as exc:
            self._record(shown, exc.status, None, exc.kind, int((time.monotonic() - t0) * 1000))
            raise
        elapsed = int((time.monotonic() - t0) * 1000)
        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._record(shown, status, body, "INVALID_JSON", elapsed)
            raise SourceError("INVALID_JSON", status) from None
        self._record(shown, status, body, None, elapsed)
        return data
