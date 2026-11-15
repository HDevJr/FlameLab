"""Recalcula o SHA-256 dos documentos-fonte e compara com data/documents.json e data/source_manifest.json.

Não altera hashes esperados. Grava o resultado em docs/evidence/source_hash_check_<UTC>.json.
Saída 0 = todos MATCH; 1 = divergência; 2 = arquivo ausente.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.dataset.hashing import verify_source  # noqa: E402
from backend.app.dataset.store import DatasetStore  # noqa: E402


def main() -> int:
    now = datetime.now(timezone.utc)
    store = DatasetStore.load(verify_hashes=False)
    manifest = json.loads((ROOT / "data" / "source_manifest.json").read_text(encoding="utf-8-sig"))
    results = []
    for doc in store.documents.values():
        chk = verify_source(doc.document_id, doc.local_path, doc.sha256, ROOT)
        man = manifest.get("sha256") if manifest.get("source_id") == doc.document_id else None
        results.append({
            "document_id": doc.document_id, "path": chk.path, "status": chk.status,
            "expected_sha256_documents_json": doc.sha256, "expected_sha256_source_manifest": man,
            "manifest_agrees_with_documents_json": (man == doc.sha256) if man else None,
            "actual_sha256": chk.actual_sha256, "size_bytes": chk.size_bytes,
            "expected_size_bytes": doc.size_bytes,
        })
    report = {"executed_at_utc": now.isoformat(), "results": results}
    out = ROOT / "docs" / "evidence" / f"source_hash_check_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for r in results:
        print(f"{r['document_id']}: {r['status']} (manifest concorda: {r['manifest_agrees_with_documents_json']}) "
              f"-> {out.relative_to(ROOT)}")
    statuses = {r["status"] for r in results}
    return 0 if statuses <= {"MATCH"} else 2 if "FILE_MISSING" in statuses else 1


if __name__ == "__main__":
    raise SystemExit(main())
