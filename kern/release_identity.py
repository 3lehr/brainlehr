"""Offline, deterministic release identity evidence.

This module only fingerprints local inputs.  It never resolves, installs, or
publishes dependencies; missing locks are reported as a coverage gap.
"""
from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _manifest_hash(root: Path) -> str:
    files = sorted(p for p in root.iterdir() if p.name in {"pyproject.toml", "setup.cfg", "setup.py"})
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def config_hash(root: str | Path) -> str:
    """Public, local digest for tracked build configuration."""
    return _manifest_hash(Path(root).resolve())


def _git(root: Path, *args: str) -> str | None:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def artifact_manifest(root: str | Path, *, artifact: str | Path, revision: str,
                      tree_hash: str, config_sha256: str, build_command: list[str],
                      variant: str, launched_artifact_sha256: str | None = None,
                      launched_revision: str | None = None) -> dict[str, Any]:
    """Bind one local build artifact to one source variant; no self-attestation trust."""
    root, artifact = Path(root).resolve(), Path(artifact).resolve()
    gaps: list[str] = []
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,96}", variant):
        return {"status": "UNKNOWN", "coverage_gaps": ["invalid_variant"]}
    if not artifact.is_file():
        return {"status": "UNKNOWN", "coverage_gaps": ["artifact_missing"]}
    actual_revision = _git(root, "rev-parse", "HEAD")
    actual_tree = _git(root, "rev-parse", "HEAD^{tree}")
    dirty = _git(root, "status", "--porcelain")
    actual_config = _manifest_hash(root)
    if actual_revision is None or actual_tree is None:
        gaps.append("source_not_a_readable_git_revision")
    if actual_revision and revision != actual_revision:
        gaps.append("revision_mismatch")
    if actual_tree and tree_hash != actual_tree:
        gaps.append("tree_hash_mismatch")
    if config_sha256 != actual_config:
        gaps.append("config_hash_mismatch")
    if dirty:
        gaps.append("dirty_source")
    digest = _sha256(artifact)
    if launched_artifact_sha256 is not None and launched_artifact_sha256 != digest:
        gaps.append("launched_artifact_mismatch")
    if launched_revision is not None and launched_revision != revision:
        gaps.append("launched_revision_mismatch")
    if launched_artifact_sha256 is None or launched_revision is None:
        gaps.append("launched_identity_unobserved")
    command_digest = hashlib.sha256("\0".join(build_command).encode()).hexdigest()
    result = {
        "schema": 1, "status": "PASS" if not gaps else "FAIL", "network": "disabled",
        "subject": {"variant": variant, "artifact_name": artifact.name, "artifact_sha256": digest},
        "source": {"revision": revision, "tree_hash": tree_hash, "config_sha256": config_sha256},
        "build": {"command_sha256": command_digest, "platform": platform.system(),
                  "architecture": platform.machine(), "python": platform.python_version()},
        "launched": {"artifact_sha256": launched_artifact_sha256,
                     "revision": launched_revision, "observable": launched_artifact_sha256 is not None
                     and launched_revision is not None},
        "coverage_gaps": sorted(gaps),
    }
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    result["artifact_manifest_sha256"] = hashlib.sha256(encoded).hexdigest()
    return result


def as_evidence_witness(result: dict[str, Any], *, witness_id: str,
                        requirement_ids: list[str], independence_group: str,
                        lineage_id: str) -> dict[str, Any]:
    """Create a P98 metadata witness; the manifest remains non-normative."""
    source, subject = result.get("source"), result.get("subject")
    if not isinstance(source, dict) or not isinstance(subject, dict):
        raise ValueError("artifact manifest lacks bound source/subject")
    verdict = str(result.get("status", "UNKNOWN")).lower()
    return {
        "id": witness_id, "requirement_ids": requirement_ids, "kind": "build_artifact",
        "tool": "release_identity", "tool_version": "3", "revision": source["revision"],
        "config_hash": source["config_sha256"], "artifact_hash": subject["artifact_sha256"],
        "verdict": verdict if verdict in {"pass", "fail", "unknown"} else "unknown",
        "independence_group": independence_group, "lineage_id": lineage_id,
        "freshness": "current", "evidence_rank": "local_artifact", "confidence": 1.0 if verdict == "pass" else 0.0,
        "gaps": result.get("coverage_gaps", []),
    }


def deployment_gate(*, current: dict[str, str], candidate: dict[str, str],
                    compatibility: dict[str, Any], canary: dict[str, Any],
                    rollback: dict[str, Any]) -> dict[str, Any]:
    """Fail closed when a release identity changed outside its declared window."""
    changed = sorted(key for key in ("schema", "api", "event", "deploy")
                     if current.get(key) != candidate.get(key))
    supported = compatibility.get("supported", {})
    incompatible = [key for key in changed if key in supported and candidate.get(key) not in supported[key]]
    unspecified = [key for key in changed if key not in supported]
    gaps = []
    if incompatible:
        gaps.append("incompatible_" + ",".join(incompatible))
    if unspecified:
        gaps.append("compatibility_missing_" + ",".join(unspecified))
    if changed and not canary.get("id"):
        gaps.append("canary_missing")
    if changed and not rollback.get("strategy"):
        gaps.append("rollback_missing")
    return {"schema": 1, "network": "disabled", "changed": changed,
            "allowed": not gaps, "coverage_gaps": gaps,
            "canary": canary, "rollback": rollback}


def identity(root: str | Path, *, artifact: str | Path | None = None,
             schema: str | None = None, api: str | None = None,
             event: str | None = None, deploy: str | None = None,
             compatibility: dict[str, Any] | None = None,
             canary: dict[str, Any] | None = None,
             rollback: dict[str, Any] | None = None, sbom: str | Path | None = None,
             signature: dict[str, Any] | None = None,
             source_revision: str | None = None,
             tool_versions: dict[str, str] | None = None) -> dict[str, Any]:
    """Return release/build identity from local files and explicit metadata."""
    root = Path(root).resolve()
    locks = sorted(p.name for p in root.iterdir()
                   if p.is_file() and (p.name.endswith((".lock", ".lockfile"))
                                       or p.name in {"poetry.lock", "Pipfile.lock", "uv.lock"}))
    gaps = [] if locks else ["lockfile_missing"]
    artifact_path = Path(artifact).resolve() if artifact else None
    sbom_path = Path(sbom).resolve() if sbom else None
    if sbom_path and not sbom_path.is_file():
        gaps.append("sbom_missing")
    if not signature:
        gaps.append("signature_unverified")
    result: dict[str, Any] = {
        "schema": 1,
        "network": "disabled",
        "source": {"root": str(root), "manifest_sha256": _manifest_hash(root)},
        "build": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                  "platform": platform.platform(), "executable": Path(sys.executable).name},
        "locks": [{"path": name, "sha256": _sha256(root / name)} for name in locks],
        "artifact": ({"path": str(artifact_path), "sha256": _sha256(artifact_path)}
                     if artifact_path and artifact_path.is_file() else None),
        "sbom": ({"path": str(sbom_path), "sha256": _sha256(sbom_path)}
                 if sbom_path and sbom_path.is_file() else None),
        "signature": signature or {"status": "not_verified"},
        "provenance": {"tool": "brainlehr.release_identity", "version": "2",
                       "source_revision": source_revision,
                       "tool_versions": tool_versions or {}},
        "compatibility": compatibility or {},
        "identity": {"schema": schema, "api": api, "event": event, "deploy": deploy},
        "canary": canary or {}, "rollback": rollback or {}, "coverage_gaps": gaps,
    }
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    result["sha256"] = hashlib.sha256(encoded).hexdigest()
    return result
