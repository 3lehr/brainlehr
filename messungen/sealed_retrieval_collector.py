"""Consume a score report without reopening sealed queries; fail closed for P103."""
from __future__ import annotations

import hashlib
import json

try:
    from .sealed_retrieval_contract import freeze_manifest
except ImportError:  # direct `python messungen/...` execution
    from sealed_retrieval_contract import freeze_manifest


def collect(manifest: dict, raw: dict, *, raw_sha256: str) -> dict:
    """Classify only report metadata; missing sealed evidence is never inferred."""
    frozen = freeze_manifest(manifest)
    missing = []
    expected = 7 * 4
    if raw.get("matrix_count") != expected:
        missing.append("all_de_en_code_signature_consumer_matrices")
    if raw.get("schema") != 4 or not raw.get("model"):
        missing.append("model_and_score_provenance")
    if "prose_control" not in raw:
        missing.append("bge_identical_prose_control")
    if "splits" not in raw or "dev_choice" not in raw or raw.get("test_runs") != 1:
        missing.append("sealed_train_dev_test_once")
    if raw.get("loro_runs", 0) < 3:
        missing.append("leave_one_repo_out")
    if set(raw.get("ablations", ())) != {"stripped", "comments_only", "combined", "generated_annotation"}:
        missing.append("comment_annotation_ablations")
    if set(raw.get("fallbacks", ())) != {"model_missing", "model_stale", "index_stale"}:
        missing.append("missing_stale_bge_fallbacks")
    if not all(key in raw for key in ("latency_seconds", "max_rss")):
        missing.append("time_ram")
    return {
        "schema": 1,
        "manifest_sha256": frozen["sha256"],
        "raw_sha256": raw_sha256,
        "status": "PASS" if not missing else "FAIL",
        "hypothesis": "H0" if not missing else "UNDECIDED",
        "active_channel": "bge_annotation",
        "missing": missing,
    }


def hash_report(raw: dict) -> str:
    return hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
