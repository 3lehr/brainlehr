"""Small deterministic contracts for client and project lifecycle edges."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Mapping


def knowledge_only_flow(*, mode: str, knowledge: Mapping[str, object] | None = None) -> dict:
    """Return bounded knowledge metadata; knowledge mode never touches a project."""
    if mode not in {"knowledge", "code"}:
        raise ValueError("mode must be knowledge or code")
    if mode == "code":
        return {"mode": "code", "code_path": "enabled", "knowledge_count": len(knowledge or {})}
    return {
        "mode": "knowledge", "knowledge_count": len(knowledge or {}),
        "code_path": "bypassed", "durable_writes": 0,
        "operations": [],
        "coverage_gaps": [],
        "must_not": ["git-discovery", "overlay", "analyzer", "commit-gate", "code-embedding"],
    }


class ProjectLifecycle:
    """Idempotent local attach/detach registry with append-only audit metadata."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _read(self) -> dict:
        if not self.path.exists():
            return {"schema": 1, "projects": {}, "audit": []}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("lifecycle store is unreadable") from exc
        if not isinstance(value, dict) or not isinstance(value.get("projects"), dict):
            raise ValueError("lifecycle store is invalid")
        value.setdefault("schema", 1)
        value.setdefault("audit", [])
        return value

    def _write(self, value: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        temporary.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)

    @staticmethod
    def _fingerprint(project_id: str, revision: str, capsule: Mapping[str, object]) -> str:
        encoded = json.dumps({"project_id": project_id, "revision": revision,
                              "capsule": dict(capsule)}, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode()).hexdigest()

    def attach(self, *, project_id: str, revision: str, capsule: Mapping[str, object], owner: str) -> dict:
        if not all(str(value).strip() for value in (project_id, revision, owner)):
            raise ValueError("project_id, revision and owner are required")
        value = self._read()
        current = value["projects"].get(project_id)
        if current and current["owner"] != owner:
            return {"status": "denied", "reason": "foreign_project_owner"}
        row = {"project_id": project_id, "revision": revision, "capsule": dict(capsule), "owner": owner,
               "fingerprint": self._fingerprint(project_id, revision, capsule)}
        status = "attached" if current != row else "unchanged"
        if status == "attached":
            value["projects"][project_id] = row
            value["audit"].append({"action": "attach", "project_id": project_id,
                                   "revision": revision, "fingerprint": row["fingerprint"]})
            self._write(value)
        return {"status": status, "project": row}

    def detach(self, *, project_id: str, owner: str) -> dict:
        value = self._read()
        current = value["projects"].get(project_id)
        if current is None:
            return {"status": "unknown_project", "project_id": project_id}
        if current["owner"] != owner:
            return {"status": "denied", "reason": "foreign_project_owner"}
        del value["projects"][project_id]
        value["audit"].append({"action": "detach", "project_id": project_id,
                               "revision": current["revision"], "fingerprint": current["fingerprint"]})
        self._write(value)
        return {"status": "detached", "project_id": project_id, "revision": current["revision"]}

    def context(self, project_id: str) -> dict | None:
        return self._read()["projects"].get(project_id)


_RECOVERY = {
    "current": ("current", "continue"),
    "stale": ("stale", "refresh_context"),
    "timeout": ("timeout", "retry"),
    "empty": ("empty", "request_context"),
}


def recovery_envelope(client: str, state: str) -> dict:
    """Return the same bounded machine state for every supported client."""
    if client not in {"CODEX", "CLAUDE", "HERMES", "IDE"}:
        raise ValueError("unsupported client")
    if state not in _RECOVERY:
        raise ValueError("state must be current, stale, timeout or empty")
    identity, action = _RECOVERY[state]
    return {"status": identity, "recovery": identity, "next_action": action,
            "message": {"current": "Context ready", "stale": "Refresh context",
                         "timeout": "Retry request", "empty": "Request context"}[state],
            "text_limit": 80, "durable_writes": 0,
            "coverage_gaps": [] if state == "current" else [f"{state}_context"]}


def as_evidence_witness(result: Mapping[str, object], *, witness_id: str, requirement_id: str,
                        independence_group: str = "client-lifecycle", lineage_id: str = "client-lifecycle") -> dict:
    """Project a P77/P78/P79 local result into non-normative P98 metadata."""
    if requirement_id not in {"P77", "P78", "P79"}:
        raise ValueError("unsupported lifecycle requirement")
    encoded = json.dumps(dict(result), sort_keys=True, separators=(",", ":"), default=str).encode()
    digest = hashlib.sha256(encoded).hexdigest()
    status = "pass" if result.get("status") in {"attached", "unchanged", "detached", "current"} or result.get("mode") == "knowledge" else "unknown"
    return {"id": witness_id, "requirement_ids": [requirement_id], "kind": "client_lifecycle",
            "tool": "client_lifecycle", "tool_version": "1", "revision": digest,
            "config_hash": digest, "artifact_hash": digest, "verdict": status,
            "independence_group": independence_group, "lineage_id": lineage_id, "freshness": "current",
            "evidence_rank": "deterministic_fixture", "confidence": 1.0 if status == "pass" else 0.0,
            "gaps": result.get("coverage_gaps", [])}
