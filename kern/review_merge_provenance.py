"""Small, offline review/merge provenance contract (P83)."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


def review_merge_provenance(*, reviewed_revision: str, review_role: str,
                            review_result: str, merge_commit: str | None,
                            merge_revision: str, independent: bool = True,
                            stale: bool = False) -> dict[str, Any]:
    """Return PASS, UNKNOWN (gap), or FAIL without retaining review content."""
    gaps: list[str] = []
    if not all(isinstance(value, str) and value.strip()
               for value in (reviewed_revision, merge_revision)):
        gaps.append("revision_missing")
    if not isinstance(review_role, str) or not review_role.strip():
        gaps.append("review_role_missing")
    if not isinstance(merge_commit, str) or not merge_commit.strip():
        gaps.append("merge_commit_missing")
    if stale:
        gaps.append("review_stale")
    if not independent:
        gaps.append("review_not_independent")
    if review_result not in {"approved", "rejected"}:
        gaps.append("review_result_missing")
    if review_result == "rejected":
        gaps.append("review_negative")
    if reviewed_revision != merge_revision:
        gaps.append("reviewed_revision_mismatch")
    status = "PASS" if not gaps else ("FAIL" if "review_negative" in gaps or "reviewed_revision_mismatch" in gaps else "UNKNOWN")
    payload = {"schema": 1, "status": status, "network": "disabled",
               "review": {"revision": reviewed_revision, "role": review_role,
                           "result": review_result, "independent": independent},
               "merge": {"commit": merge_commit, "revision": merge_revision},
               "coverage_gaps": sorted(gaps)}
    payload["provenance_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return payload


def as_evidence_witness(result: Mapping[str, Any], *, witness_id: str,
                        independence_group: str = "review-merge",
                        lineage_id: str = "review-merge") -> dict[str, Any]:
    review = result.get("review", {})
    if not isinstance(review, Mapping) or not review.get("revision"):
        raise ValueError("review provenance lacks revision")
    verdict = str(result.get("status", "UNKNOWN")).lower()
    return {"id": witness_id, "requirement_ids": ["P83"], "kind": "review_merge",
            "tool": "review_merge_provenance", "tool_version": "1",
            "revision": review["revision"], "config_hash": "unknown", "artifact_hash": "unknown",
            "verdict": verdict if verdict in {"pass", "fail", "unknown"} else "unknown",
            "independence_group": independence_group, "lineage_id": lineage_id,
            "freshness": "stale" if "review_stale" in result.get("coverage_gaps", []) else "current",
            "evidence_rank": "local_review_metadata", "confidence": 1.0 if verdict == "pass" else 0.0,
            "gaps": result.get("coverage_gaps", [])}
