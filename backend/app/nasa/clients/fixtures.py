"""Transporte por fixture: respostas reais gravadas, reproduzidas sem rede.

`RecordingTransport` grava cada resposta de um transporte real; `FixtureTransport` as devolve.
Uma URL não gravada falha como rede indisponível — nunca é inventada.
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
from pathlib import Path

from backend.app.nasa.clients.http import SourceError, Transport
from backend.app.nasa.models import AccessMode


def _key(url: str, params: dict[str, str] | None) -> str:
    return url + ("?" + urllib.parse.urlencode(params) if params else "")


class FixtureTransport:
    mode = AccessMode.FIXTURE

    def __init__(self, directory: Path, fail_hosts: frozenset[str] = frozenset()):
        self._dir = directory
        index = directory / "index.json"
        self._index: dict[str, str] = json.loads(index.read_text(encoding="utf-8")) if index.exists() else {}
        self._fail_hosts = fail_hosts

    def get(self, url: str, params: dict[str, str] | None, timeout: float) -> tuple[int, bytes]:
        if urllib.parse.urlsplit(url).hostname in self._fail_hosts:
            raise SourceError("TIMEOUT")
        name = self._index.get(_key(url, params))
        if name is None:
            raise SourceError("NETWORK")
        return 200, (self._dir / name).read_bytes()

    def stream_sha256(self, url: str, timeout: float, max_bytes: int) -> tuple[str, int]:
        entry = self._index.get("sha256::" + url)
        if urllib.parse.urlsplit(url).hostname in self._fail_hosts or entry is None:
            raise SourceError("NETWORK")
        digest, size = entry.split(":")
        return digest, int(size)


class RecordingTransport:
    def __init__(self, inner: Transport, directory: Path):
        self._inner = inner
        self.mode = inner.mode
        self._dir = directory
        directory.mkdir(parents=True, exist_ok=True)
        index = directory / "index.json"
        self._index: dict[str, str] = json.loads(index.read_text(encoding="utf-8")) if index.exists() else {}

    def get(self, url: str, params: dict[str, str] | None, timeout: float) -> tuple[int, bytes]:
        status, body = self._inner.get(url, params, timeout)
        key = _key(url, params)
        name = hashlib.sha1(key.encode()).hexdigest()[:16] + ".json"
        (self._dir / name).write_bytes(body)
        self._index[key] = name
        (self._dir / "index.json").write_text(json.dumps(self._index, indent=1, sort_keys=True), encoding="utf-8")
        return status, body

    def stream_sha256(self, url: str, timeout: float, max_bytes: int) -> tuple[str, int]:
        digest, size = self._inner.stream_sha256(url, timeout, max_bytes)
        self._index["sha256::" + url] = f"{digest}:{size}"
        (self._dir / "index.json").write_text(json.dumps(self._index, indent=1, sort_keys=True), encoding="utf-8")
        return digest, size
