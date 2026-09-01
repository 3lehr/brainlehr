"""Small, offline analyzer trust envelope (P95/P98).

Only hashes and bounded metadata leave this module.  It never executes tools
and never promotes an unverifiable SBOM or advisory result.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import PurePath
from typing import Any

SCHEMA = 1
NETWORK_MODES = {"disabled", "isolated", "host-not-enforced"}
_HEX = re.compile(r"^[0-9a-fA-F]{64}$")
_SECRET = re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|private[_-]?key)")


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _check_paths(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _SECRET.search(str(key)):
                raise ValueError("secrets are not accepted in attestation metadata")
            _check_paths(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _check_paths(item)
    elif isinstance(value, str):
        path = value.replace("\\", "/")
        if path.startswith("/") or re.match(r"^[A-Za-z]:/", path) or PurePath(path).is_absolute():
            raise ValueError("absolute paths are not accepted")


def _digest_output(output: Any) -> str:
    if isinstance(output, Mapping):
        if any(key in output for key in ("report", "raw", "stdout", "stderr", "content")):
            raise ValueError("raw analyzer report is not accepted")
        value = output.get("sha256", output.get("hash"))
    else:
        value = output
    if not isinstance(value, (str, bytes, bytearray)):
        raise ValueError("output must be a digest or bytes")
    if isinstance(value, str) and _HEX.fullmatch(value):
        return value.lower()
    return hashlib.sha256(value if isinstance(value, (bytes, bytearray)) else value.encode()).hexdigest()


def _tree_digest(value: Any) -> str:
    """Input is already a tree digest or relative-path -> digest map, never source."""
    if isinstance(value, str) and _HEX.fullmatch(value):
        return value.lower()
    if not isinstance(value, Mapping) or not value:
        raise ValueError("input tree must be a digest or relative digest map")
    normalized = {}
    for path, digest in value.items():
        if not isinstance(path, str) or not path or path.startswith(("/", "\\")) or ".." in path.split("/"):
            raise ValueError("input tree path must be relative")
        if not isinstance(digest, str) or not _HEX.fullmatch(digest):
            raise ValueError("input tree entries must be sha256 digests")
        normalized[path] = digest.lower()
    return _hash(normalized)


def attest(*, tool: Mapping[str, Any] | None = None, input_tree: Any = None,
           config: Any = None, policy: Any = None, network_mode: str,
           exit_code: int, output: Any, revision: str,
           advisory_db: Mapping[str, Any] | None = None,
           sbom: Mapping[str, Any] | None = None, sandbox: Mapping[str, Any] | None = None,
           requirement_ids: list[str] | None = None, witness_id: str = "w-p95") -> dict[str, Any]:
    """Build a deterministic attestation; invalid or unverifiable inputs fail closed."""
    if network_mode not in NETWORK_MODES:
        raise ValueError("invalid network mode")
    if not isinstance(revision, str) or not revision or len(revision) > 160:
        raise ValueError("revision must be a bounded identifier")
    if not isinstance(exit_code, int) or isinstance(exit_code, bool):
        raise ValueError("exit_code must be an integer")
    _check_paths(input_tree)
    _check_paths(config)
    _check_paths(policy)
    _check_paths(tool)
    _check_paths(advisory_db)
    _check_paths(sbom)
    _check_paths(sandbox)
    gaps: list[str] = []
    if not isinstance(tool, Mapping) or not tool.get("binary") or not tool.get("version") or not tool.get("sha256"):
        gaps.append("tool identity unavailable")
        tool_row = {"binary": None, "version": None, "sha256": None}
    else:
        tool_row = {"binary": str(tool["binary"]), "version": str(tool["version"]), "sha256": str(tool["sha256"]).lower()}
        if not _HEX.fullmatch(tool_row["sha256"]):
            raise ValueError("tool hash must be sha256")
    advisory = {"status": "not_checked", "fresh": False}
    if advisory_db is not None:
        status = advisory_db.get("status")
        if status not in {"fresh", "stale", "not_checked"}:
            raise ValueError("invalid advisory status")
        advisory = {"status": status, "fresh": status == "fresh", "sha256": _hash(advisory_db)}
        if status != "fresh":
            gaps.append("advisory database stale" if status == "stale" else "advisory database not checked")
    else:
        gaps.append("advisory database not checked")
    if sbom is not None and not isinstance(sbom, Mapping):
        raise ValueError("SBOM must be normalized metadata")
    if network_mode == "host-not-enforced":
        gaps.append("network isolation is not enforced")
    if not isinstance(sandbox, Mapping) or not sandbox:
        gaps.append("sandbox evidence missing")
    input_tree_sha256 = _tree_digest(input_tree)
    sbom_row = {"status": "not_checked", "sha256": None}
    if sbom is not None:
        status, digest = sbom.get("status"), sbom.get("sha256")
        if status not in {"fresh", "stale"} or not isinstance(digest, str) or not _HEX.fullmatch(digest):
            raise ValueError("SBOM must contain fresh/stale status and sha256")
        sbom_row = {"status": status, "sha256": digest.lower()}
        if status != "fresh":
            gaps.append("SBOM stale")
    row = {
        "schema": SCHEMA, "status": "pass" if not gaps and exit_code == 0 else "coverage_gap",
        "revision": revision, "tool": tool_row, "input_tree_sha256": input_tree_sha256,
        "config_policy_sha256": _hash({"config": config, "policy": policy}),
        "network_mode": network_mode, "exit_code": exit_code,
        "sandbox_sha256": _hash(sandbox) if isinstance(sandbox, Mapping) else None,
        "output_sha256": _digest_output(output), "advisory_db": advisory, "sbom": sbom_row,
        "coverage_gaps": sorted(set(gaps)),
    }
    if exit_code != 0:
        row["coverage_gaps"].append(f"analyzer exited {exit_code}")
        row["coverage_gaps"] = sorted(set(row["coverage_gaps"]))
    row["attestation_sha256"] = _hash(row)
    row["witness"] = {"id": witness_id, "requirement_ids": requirement_ids or ["P95"],
                      "kind": "analyzer_attestation", "tool": tool_row["binary"] or "unavailable",
                      "tool_version": tool_row["version"] or "unknown", "artifact_hash": row["output_sha256"],
                      "revision": revision, "config_hash": row["config_policy_sha256"],
                      "verdict": "pass" if row["status"] == "pass" else "unknown",
                      "independence_group": "analyzer:" + (tool_row["binary"] or "unavailable"),
                      "lineage_id": row["attestation_sha256"], "freshness": "current",
                      "evidence_rank": "attested_analyzer", "confidence": 1.0 if row["status"] == "pass" else 0.0,
                      "gaps": row["coverage_gaps"], "conflict": False, "observed_at": ""}
    return row


analyzer_attestation = attest
build_attestation = attest
create_attestation = attest
