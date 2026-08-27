"""Schema adapter: validate V8 bindings, normalize only schema for V3 metrics."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from messungen.sealed_retrieval_v3_collector import collect as collect_v3, hash_report
from messungen.sealed_retrieval_v8_score import ROOT, validate_manifest


def _resolved(manifest: dict[str, Any]) -> dict[str, Any]:
    corpus = manifest["corpus"]
    payload = (ROOT / corpus["path"]).read_bytes()
    if hashlib.sha256(payload).hexdigest() != corpus["sha256"]:
        raise ValueError("sealed corpus hash mismatch")
    resolved = json.loads(payload)
    if resolved.get("schema") != 2 or len(resolved.get("cases", ())) != corpus["case_count"]:
        raise ValueError("sealed corpus shape mismatch")
    return {**resolved, "schema": 3}


def collect(manifest: dict[str, Any], raw: dict[str, Any], *, raw_sha256: str) -> dict[str, Any]:
    try:
        validate_manifest(manifest)
        resolved = _resolved(manifest)
    except (KeyError, OSError, TypeError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        return {"schema": 8, "manifest_sha256": hash_report(manifest), "raw_sha256": raw_sha256,
                "status": "FAIL", "hypothesis": "UNDECIDED", "active_channel": "bge_m3",
                "missing": ["sealed_manifest"], "error": str(error)}
    if hash_report(raw) != raw_sha256:
        return {"schema": 8, "manifest_sha256": hash_report(resolved), "seal_sha256": hash_report(manifest),
                "raw_sha256": raw_sha256, "status": "FAIL", "hypothesis": "UNDECIDED",
                "active_channel": "bge_m3", "missing": ["raw_hash"]}
    if raw.get("schema") != 8:
        return {"schema": 8, "manifest_sha256": hash_report(resolved), "seal_sha256": hash_report(manifest),
                "raw_sha256": raw_sha256, "status": "FAIL", "hypothesis": "UNDECIDED",
                "active_channel": "bge_m3", "missing": ["runner_schema"]}
    normalized = {**raw, "schema": 6}
    report = collect_v3(resolved, normalized, raw_sha256=hash_report(normalized))
    return {**report, "schema": 8, "seal_sha256": hash_report(manifest), "raw_sha256": raw_sha256}
