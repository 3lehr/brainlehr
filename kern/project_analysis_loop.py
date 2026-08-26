"""Small in-memory cadence controller for revision-bound code analysis.

This is deliberately not a file watcher, daemon, or persistence layer.  A
client invokes it after a completed edit batch and before a verification step.
It coalesces only technical Git fingerprints; source text, chat and tool output
never enter its state.  The caller remains responsible for the post-commit
``project_change`` receipt.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import project_context


SCHEMA = 1
ANALYZER_VERSION = "static-python-imports-v1"
DEBOUNCE_SECONDS = 1.0
MAX_RERUNS = 3


def _git_bytes(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                            timeout=15, check=False)
    if result.returncode:
        raise ValueError(f"cannot read working tree for {root}")
    return result.stdout


def working_tree_overlay(path: str | Path) -> dict:
    """Fingerprint the tracked working overlay without staging or writing it.

    Untracked files are named but not content-hashed: they remain an explicit
    coverage gap until a client stages them for the separate pre-commit pass.
    """
    root = project_context.project_root(path)
    base = project_context._git(root, "rev-parse", "HEAD")
    patch = _git_bytes(root, "diff", "--binary", "--no-ext-diff")
    changed = project_context._git(root, "diff", "--name-only").splitlines()
    untracked = project_context._git(root, "ls-files", "--others", "--exclude-standard").splitlines()
    digest = hashlib.sha256()
    digest.update(patch)
    digest.update(b"\0")
    digest.update("\n".join(sorted(untracked)).encode("utf-8"))
    return {
        "schema": SCHEMA,
        "repo": str(root),
        "base_commit": base,
        "tree_hash": digest.hexdigest(),
        "analyzer_version": ANALYZER_VERSION,
        "changed_files": sorted(name for name in changed if name),
        "untracked_files": sorted(name for name in untracked if name),
        "coverage_gaps": (["untracked file contents require staged analysis"] if untracked else []),
    }


def _key(snapshot: dict) -> tuple[str, str, str, str]:
    return (snapshot["repo"], snapshot["base_commit"], snapshot["tree_hash"],
            snapshot["analyzer_version"])


def _idempotency_key(snapshot: dict, origin: str, correlation_id: str) -> str:
    payload = [*_key(snapshot), origin, correlation_id]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode("utf-8")).hexdigest()


class AnalysisLoop:
    """One client-local, latest-wins analysis queue; it never writes a DB."""

    def __init__(self, *, debounce_seconds: float = DEBOUNCE_SECONDS,
                 max_reruns: int = MAX_RERUNS) -> None:
        self.debounce_seconds = debounce_seconds
        self.max_reruns = max_reruns
        self.pending: dict | None = None
        self.active: dict | None = None
        self.latest_key: tuple[str, str, str, str] | None = None
        self.completed_key: tuple[str, str, str, str] | None = None
        self.completed_commits: set[str] = set()
        self.reruns = 0

    def task_start(self, *, mode: str, capsule_hash: str | None = None) -> dict:
        if mode == "knowledge":
            return {"status": "bypass", "durable_writes": 0,
                    "must_not": "scan or analyze project code"}
        if mode not in {"code", "mixed"}:
            return {"status": "unknown", "durable_writes": 0,
                    "must": "request explicit code or mixed mode"}
        return {"status": "context_required", "durable_writes": 0,
                "capsule_hash": capsule_hash, "next": "load current project context"}

    def edit_completed(self, path: str | Path, *, mode: str, origin: str,
                       correlation_id: str, now: float) -> dict:
        if mode == "knowledge":
            return {"status": "bypass", "durable_writes": 0}
        if mode not in {"code", "mixed"}:
            raise ValueError("edit analysis requires code or mixed mode")
        if origin.startswith("brainlehr_generated"):
            return {"status": "ignored_generated", "durable_writes": 0,
                    "coverage_gaps": ["generated Brainlehr artifact is not source analysis input"]}
        if not correlation_id.strip():
            raise ValueError("correlation_id is required")
        snapshot = working_tree_overlay(path)
        if snapshot["untracked_files"]:
            return {"status": "coverage_gap", "snapshot": snapshot, "durable_writes": 0,
                    "coverage_gaps": snapshot["coverage_gaps"]}
        key = _key(snapshot)
        if key == self.completed_key:
            return {"status": "current", "snapshot": snapshot, "durable_writes": 0}
        self.latest_key = key
        self.pending = {
            "snapshot": snapshot, "key": key, "origin": origin,
            "correlation_id": correlation_id,
            "idempotency_key": _idempotency_key(snapshot, origin, correlation_id),
            "due": now + self.debounce_seconds,
        }
        if self.active and self.active["key"] != key:
            self.active["cancelled"] = True
        return {"status": "coalesced", "snapshot": snapshot,
                "idempotency_key": self.pending["idempotency_key"], "durable_writes": 0}

    def begin_due(self, *, now: float) -> dict:
        if not self.pending:
            return {"status": "current", "durable_writes": 0}
        if now < self.pending["due"]:
            return {"status": "debouncing", "durable_writes": 0}
        if self.reruns >= self.max_reruns:
            self.pending = None
            return {"status": "circuit_open", "durable_writes": 0,
                    "coverage_gaps": ["analysis rerun limit reached; request explicit retry"]}
        self.active, self.pending = self.pending, None
        self.reruns += 1
        return {"status": "analyze", "snapshot": self.active["snapshot"],
                "idempotency_key": self.active["idempotency_key"], "durable_writes": 0}

    def finish(self, idempotency_key: str) -> dict:
        if not self.active or self.active["idempotency_key"] != idempotency_key:
            return {"status": "discarded_stale", "durable_writes": 0}
        active, self.active = self.active, None
        if active.get("cancelled") or active["key"] != self.latest_key:
            return {"status": "discarded_stale", "durable_writes": 0}
        self.completed_key = active["key"]
        self.reruns = 0
        return {"status": "current", "snapshot": active["snapshot"], "durable_writes": 0}

    def before_verification(self, path: str | Path, *, mode: str, now: float) -> dict:
        if mode == "knowledge":
            return {"status": "bypass", "durable_writes": 0}
        snapshot = working_tree_overlay(path)
        if snapshot["untracked_files"]:
            return {"status": "coverage_gap", "snapshot": snapshot, "durable_writes": 0,
                    "coverage_gaps": snapshot["coverage_gaps"]}
        if _key(snapshot) == self.completed_key:
            return {"status": "current", "snapshot": snapshot, "durable_writes": 0}
        self.latest_key = _key(snapshot)
        self.pending = {"snapshot": snapshot, "key": self.latest_key, "origin": "verification",
                        "correlation_id": "verification", "due": now,
                        "idempotency_key": _idempotency_key(snapshot, "verification", "verification")}
        return self.begin_due(now=now)

    def precommit(self, path: str | Path) -> dict:
        """Return the separate index snapshot; never confuse it with the overlay."""
        staged = project_context._staged_snapshot(project_context.project_root(path))
        return {"status": "analyze_staged" if staged["files"] else "pass",
                "snapshot": staged, "durable_writes": 0,
                "must": "run staged impact/gate before commit" if staged["files"] else None}

    def postcommit(self, *, commit: str, graph_hash: str, mode: str) -> dict:
        if mode == "knowledge":
            return {"status": "bypass", "durable_writes": 0}
        if commit in self.completed_commits:
            return {"status": "current", "commit": commit, "durable_writes": 0}
        self.completed_commits.add(commit)
        return {"status": "record_receipt", "commit": commit, "graph_hash": graph_hash,
                "durable_writes": 1,
                "next": "call project_change once with verified checks"}

    def timing_trace(self, *, verified: bool, source_revision: str,
                     tree_hash: str | None) -> dict:
        if not verified or not source_revision or not tree_hash:
            return {"status": "coverage_gap", "durable_writes": 0,
                    "coverage_gaps": ["timing evidence requires a verified revision and tree hash"]}
        return {"status": "verified_timing", "source_revision": source_revision,
                "tree_hash": tree_hash, "durable_writes": 0}
