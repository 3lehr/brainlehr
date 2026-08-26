"""Small, atomic JSON store for revision-bound graph envelopes.

The store is intentionally file based: it is a cache/fixture boundary, not a
second knowledge database.  Every non-tombstone envelope carries a hash of
its canonical payload so partial or hand-edited files fail closed.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path


SCHEMA = 1


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _envelope(payload: dict, *, revision: str, analyzer_version: str) -> dict:
    if not isinstance(payload, dict) or not revision or not analyzer_version:
        raise ValueError("payload, revision and analyzer_version are required")
    body = {"schema": SCHEMA, "status": "active", "revision": revision,
            "analyzer_version": analyzer_version, "payload": payload}
    body["content_hash"] = hashlib.sha256(_canonical(body)).hexdigest()
    return body


def _write(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(document, handle, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def save(path: str | Path, payload: dict, *, revision: str,
         analyzer_version: str) -> dict:
    document = _envelope(payload, revision=revision, analyzer_version=analyzer_version)
    _write(Path(path), document)
    return document


def delete(path: str | Path, *, reason: str = "deleted") -> dict:
    if not reason:
        raise ValueError("reason is required")
    tombstone = {"schema": SCHEMA, "status": "deleted", "reason": reason}
    tombstone["content_hash"] = hashlib.sha256(_canonical(tombstone)).hexdigest()
    _write(Path(path), tombstone)
    return tombstone


def load(path: str | Path) -> dict | None:
    target = Path(path)
    if not target.exists():
        return None
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("graph envelope is unreadable") from exc
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise ValueError("unsupported graph envelope schema")
    content_hash = document.get("content_hash")
    unsigned = {key: value for key, value in document.items() if key != "content_hash"}
    if not isinstance(content_hash, str) or hashlib.sha256(_canonical(unsigned)).hexdigest() != content_hash:
        raise ValueError("graph envelope content hash mismatch")
    if document.get("status") == "active" and not isinstance(document.get("payload"), dict):
        raise ValueError("active graph envelope has no payload")
    if document.get("status") == "deleted" and not document.get("reason"):
        raise ValueError("tombstone has no reason")
    if document.get("status") not in {"active", "deleted"}:
        raise ValueError("unknown graph envelope status")
    return document
