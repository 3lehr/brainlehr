"""Hash-only local/private/public release distribution evidence (P84)."""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

_HASH = re.compile(r"[0-9a-f]{64}\Z")
_CHANNELS = {"local", "private", "public"}


def distribution_provenance(*, artifact_sha256: str | None, target: str | None,
                            published_revision: str | None,
                            release_revision: str, channel: str) -> dict[str, Any]:
    gaps: list[str] = []
    if not isinstance(artifact_sha256, str) or not _HASH.fullmatch(artifact_sha256):
        gaps.append("artifact_evidence_missing")
    if not isinstance(target, str) or not target.strip():
        gaps.append("distribution_target_missing")
    if not isinstance(published_revision, str) or not published_revision.strip():
        gaps.append("published_revision_missing")
    if not isinstance(release_revision, str) or not release_revision.strip():
        gaps.append("release_revision_missing")
    if channel not in _CHANNELS:
        gaps.append("distribution_channel_unknown")
    if published_revision and release_revision != published_revision:
        gaps.append("published_revision_mismatch")
    status = "PASS" if not gaps else ("FAIL" if "published_revision_mismatch" in gaps else "UNKNOWN")
    result = {"schema": 1, "status": status, "network": "disabled",
              "distribution": {"channel": channel, "target": target,
                                "artifact_sha256": artifact_sha256,
                                "published_revision": published_revision,
                                "release_revision": release_revision},
              "coverage_gaps": sorted(gaps)}
    result["provenance_sha256"] = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return result


def as_evidence_witness(result: Mapping[str, Any], *, witness_id: str,
                        independence_group: str = "release-distribution",
                        lineage_id: str = "release-distribution") -> dict[str, Any]:
    dist = result.get("distribution", {})
    if not isinstance(dist, Mapping):
        raise ValueError("distribution metadata missing")
    verdict = str(result.get("status", "UNKNOWN")).lower()
    return {"id": witness_id, "requirement_ids": ["P84"], "kind": "release_distribution",
            "tool": "release_distribution_provenance", "tool_version": "1",
            "revision": dist.get("release_revision", "unknown"), "config_hash": "unknown",
            "artifact_hash": dist.get("artifact_sha256", "unknown"),
            "verdict": verdict if verdict in {"pass", "fail", "unknown"} else "unknown",
            "independence_group": independence_group, "lineage_id": lineage_id,
            "freshness": "current", "evidence_rank": "local_distribution_receipt",
            "confidence": 1.0 if verdict == "pass" else 0.0, "gaps": result.get("coverage_gaps", [])}
