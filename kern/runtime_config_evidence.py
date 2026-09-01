"""Hash-only runtime configuration evidence (P82)."""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


_HASH = re.compile(r"[0-9a-f]{64}\Z")
_REVISION = re.compile(r"[0-9A-Za-z_.-]{1,96}\Z")
_FORBIDDEN = {"value", "values", "secret", "token", "password", "path", "endpoint", "url"}


def runtime_config_evidence(observed: Mapping[str, Any], *, revision: str, config_hash: str,
                            environment_hash: str) -> dict[str, Any]:
    """Compare opaque configuration identifiers without retaining configuration values."""
    if not _REVISION.fullmatch(revision) or not all(_HASH.fullmatch(value) for value in (config_hash, environment_hash)):
        raise ValueError("revision and configuration hashes are invalid")
    if set(observed) & _FORBIDDEN:
        raise ValueError("runtime configuration values are not accepted")
    gaps: list[str] = []
    if observed.get("revision") != revision:
        gaps.append("runtime_revision_mismatch")
    if observed.get("config_hash") != config_hash:
        gaps.append("runtime_config_stale")
    if observed.get("environment_hash") != environment_hash:
        gaps.append("runtime_environment_mismatch")
    state = observed.get("state")
    if state not in {"current", "missing"}:
        gaps.append("runtime_config_state_unknown")
    if state == "missing":
        gaps.append("runtime_config_missing")
    return {"schema": 1, "status": "PASS" if not gaps else "UNKNOWN", "coverage_gaps": sorted(gaps),
            "metadata": {"revision": revision, "config_hash": config_hash,
                         "environment_hash": environment_hash, "state": state}}


def as_evidence_witness(result: Mapping[str, Any], *, witness_id: str,
                        independence_group: str = "runtime-config", lineage_id: str = "runtime-config") -> dict[str, Any]:
    metadata = result.get("metadata", {})
    if not isinstance(metadata, Mapping):
        raise ValueError("runtime configuration metadata missing")
    verdict = str(result.get("status", "UNKNOWN")).lower()
    return {"id": witness_id, "requirement_ids": ["P82"], "kind": "runtime_configuration",
            "tool": "runtime_config_evidence", "tool_version": "1", "revision": metadata.get("revision", "unknown"),
            "config_hash": metadata.get("config_hash", "unknown"), "artifact_hash": metadata.get("environment_hash", "unknown"),
            "verdict": verdict if verdict in {"pass", "fail", "unknown"} else "unknown",
            "independence_group": independence_group, "lineage_id": lineage_id, "freshness": "current",
            "evidence_rank": "local_runtime_metadata", "confidence": 1.0 if verdict == "pass" else 0.0,
            "gaps": result.get("coverage_gaps", [])}
