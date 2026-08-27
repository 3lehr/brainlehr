"""P103-v5 pointer-manifest collector, fail-closed before metric gates."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from messungen.sealed_retrieval_v3_collector import collect as _collect, hash_report

ROOT = Path(__file__).resolve().parents[1]


def resolve_manifest(manifest: Mapping[str, object]) -> dict[str, object]:
    """Resolve only a hash-bound local v2 corpus for a v4/v5 pointer seal."""
    if manifest.get("schema") not in (4, 5):
        raise ValueError("P103 v4/v5 manifest schema required")
    corpus = manifest.get("corpus")
    if not isinstance(corpus, Mapping) or not isinstance(corpus.get("path"), str):
        raise ValueError("sealed corpus pointer required")
    path = Path(corpus["path"])
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("sealed corpus path must be repository-relative")
    payload = (ROOT / path).read_bytes()
    if hashlib.sha256(payload).hexdigest() != corpus.get("sha256"):
        raise ValueError("sealed corpus hash mismatch")
    resolved = json.loads(payload)
    if resolved.get("schema") != 2 or len(resolved.get("cases", ())) != corpus.get("case_count"):
        raise ValueError("sealed corpus shape mismatch")
    return {**resolved, "schema": 3}


def collect(manifest: Mapping[str, object], raw: Mapping[str, object], *, raw_sha256: str) -> dict[str, object]:
    try:
        resolved = resolve_manifest(manifest)
    except (AttributeError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        return {"schema": manifest.get("schema", 5), "manifest_sha256": hash_report(manifest),
                "raw_sha256": raw_sha256, "status": "FAIL", "hypothesis": "UNDECIDED",
                "active_channel": "bge_m3", "missing": ["sealed_manifest"], "error": str(error)}
    try:
        result = _collect(resolved, raw, raw_sha256=raw_sha256)
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        return {"schema": manifest["schema"], "manifest_sha256": hash_report(resolved),
                "seal_sha256": hash_report(manifest), "raw_sha256": raw_sha256,
                "status": "FAIL", "hypothesis": "UNDECIDED", "active_channel": "bge_m3",
                "missing": ["raw_schema"], "error": str(error)}
    return {**result, "schema": manifest["schema"], "seal_sha256": hash_report(manifest)}
