"""Small in-memory cadence controller for revision-bound code analysis.

This is deliberately not a file watcher, daemon, or persistence layer.  A
client invokes it after a completed edit batch and before a verification step.
It coalesces only technical Git fingerprints; source text, chat and tool output
never enter its state.  The caller remains responsible for the post-commit
``project_change`` receipt.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

import project_context


SCHEMA = 1
ANALYZER_VERSION = "static-python-imports-v1"
DEBOUNCE_SECONDS = 1.0
MAX_RERUNS = 3
MAX_WORKING_NODES = 64
MAX_WORKING_EDGES = 128
MACHINE_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}")


def _machine_identifier(value: str, field: str) -> str:
    if not isinstance(value, str) or not MACHINE_IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field} must be a 1..64 character machine identifier")
    return value


def _git_bytes(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                            timeout=15, check=False)
    if result.returncode:
        raise ValueError(f"cannot read working tree for {root}")
    return result.stdout


def _owned_untracked(root: Path, requested: list[str] | None) -> list[str]:
    """Validate the caller's relative allowlist; never read outside the repo."""
    untracked = set(project_context._git(root, "ls-files", "--others", "--exclude-standard").splitlines())
    owned: list[str] = []
    for raw in requested or []:
        candidate = Path(raw)
        if candidate.is_absolute() or ".." in candidate.parts or not str(raw).strip():
            raise ValueError("agent-owned paths must be relative and non-upward")
        name = candidate.as_posix()
        if name not in untracked:
            raise ValueError("agent-owned path is not an untracked project file")
        owned.append(name)
    return sorted(set(owned))


def _owned_tracked_changes(root: Path, requested: list[str] | None) -> list[str]:
    """Narrow a shadow run to explicit agent-owned modified tracked files."""
    changed = {name for name in project_context._git(
        root, "diff", "HEAD", "--name-only", "--find-renames").splitlines() if name}
    owned: list[str] = []
    for raw in requested or []:
        candidate = Path(raw)
        if candidate.is_absolute() or ".." in candidate.parts or not str(raw).strip():
            raise ValueError("agent-owned tracked paths must be relative and non-upward")
        name = candidate.as_posix()
        if name not in changed:
            raise ValueError("agent-owned tracked path is not a modified tracked file")
        owned.append(name)
    return sorted(set(owned))


def _working_import_edges(root: Path, files: list[str]) -> tuple[list[dict], list[str]]:
    modules: dict[str, set[str]] = {}
    for name in files:
        if not name.endswith(".py"):
            continue
        module = name[:-3].replace("/", ".")
        if module.endswith(".__init__"):
            module = module[:-9]
        for variant in {module, Path(name).stem}:
            modules.setdefault(variant, set()).add(name)
    edges: dict[tuple[str, str], dict] = {}
    gaps: list[str] = []
    for consumer in files:
        if not consumer.endswith(".py"):
            continue
        try:
            tree = ast.parse((root / consumer).read_text(encoding="utf-8"), filename=consumer)
        except (OSError, SyntaxError, UnicodeError):
            gaps.append(f"unreadable or invalid Python: {consumer}")
            continue
        package = consumer[:-3].replace("/", ".").rsplit(".", 1)[0]
        names: list[tuple[str, int]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend((alias.name, node.lineno) for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                base = node.module
                if node.level:
                    parts = package.split(".") if package else []
                    base = ".".join(parts[:max(0, len(parts) - node.level + 1)] + [base]).strip(".")
                names.append((base, node.lineno))
        for imported, line in names:
            candidates = [imported]
            while "." in candidates[-1]:
                candidates.append(candidates[-1].rsplit(".", 1)[0])
            matches = next((modules[name] for name in candidates if name in modules), set())
            if len(matches) > 1:
                gaps.append("ambiguous static import")
                continue
            provider = next(iter(matches), None)
            if provider and provider != consumer:
                edges[(provider, consumer)] = {
                    "from": provider, "to": consumer, "edge_type": "static_import",
                    "source_ref": f"{consumer}:{line}", "evidence": "Python AST import",
                }
    return list(edges.values()), gaps


def _working_graph(root: Path, snapshot: dict) -> dict:
    files = [name for name in project_context._git(root, "ls-files").splitlines() if name]
    files.extend(name for name in snapshot["owned_untracked_files"] if name not in files)
    files = [name for name in files if (root / name).is_file()]
    edges, gaps = _working_import_edges(root, files)
    # Keep consumers of deleted/renamed providers visible using the immutable
    # baseline.  Current files still win when the same edge exists.
    baseline, _, baseline_gaps = project_context._python_import_edges(
        root, snapshot["base_commit"], snapshot["base_commit"])
    edges_by_pair = {(edge["from"], edge["to"]): edge for edge in baseline}
    edges_by_pair.update({(edge["from"], edge["to"]): edge for edge in edges})
    edges = list(edges_by_pair.values())
    # Baseline analyzer gaps may contain source references.  WORKING context
    # needs the limitation class, never every underlying source location.
    for gap in baseline_gaps:
        if isinstance(gap, dict):
            gaps.append("baseline unsupported static form: " + str(gap.get("form", "unknown")))
        else:
            gaps.append("baseline static-analysis coverage gap")
    roots = set(snapshot["changed_files"]) | set(snapshot["owned_untracked_files"])
    consumers: dict[str, set[str]] = {}
    evidence = {(edge["from"], edge["to"]): edge for edge in edges}
    for edge in edges:
        consumers.setdefault(edge["from"], set()).add(edge["to"])
    distance: dict[str, int] = {}
    frontier = sorted(roots)
    visited = set(frontier)
    impact_edges: list[dict] = []
    hop = 0
    while frontier:
        hop += 1
        following: list[str] = []
        for source in frontier:
            for consumer in sorted(consumers.get(source, ())):
                # Keep every proven ingress edge, even when another root has
                # already reached the same consumer at this distance.  The
                # breadth-first distance is singular; the evidence is not.
                impact_edges.append(evidence[(source, consumer)])
                if consumer in visited:
                    continue
                visited.add(consumer)
                distance[consumer] = hop
                following.append(consumer)
        frontier = following
    nodes = [{"id": name, "kind": "changed", "distance": 0} for name in sorted(roots)]
    nodes.extend({"id": name, "kind": "consumer", "distance": distance[name]} for name in sorted(distance))
    if len(nodes) > MAX_WORKING_NODES:
        gaps.append(f"working graph output bounded at {MAX_WORKING_NODES} nodes")
        nodes = nodes[:MAX_WORKING_NODES]
    node_ids = {node["id"] for node in nodes}
    graph_edges = []
    seen_edges = set()
    for edge in sorted(impact_edges, key=lambda e: (e["from"], e["to"])):
        key = (edge["from"], edge["to"], edge["source_ref"])
        if key not in seen_edges and edge["from"] in node_ids and edge["to"] in node_ids:
            seen_edges.add(key)
            graph_edges.append(edge)
    if len(graph_edges) > MAX_WORKING_EDGES:
        gaps.append(f"working graph output bounded at {MAX_WORKING_EDGES} edges")
        graph_edges = graph_edges[:MAX_WORKING_EDGES]
    graph = {"schema": 1, "state": "WORKING", "base_revision": snapshot["base_commit"],
             "working_hash": snapshot["tree_hash"], "analyzer_version": ANALYZER_VERSION,
             "nodes": nodes, "edges": graph_edges,
             "coverage_gaps": sorted(set(gaps)), "durable_writes": 0}
    encoded = json.dumps(graph, sort_keys=True, separators=(",", ":"))
    graph["content_hash"] = hashlib.sha256(encoded.encode()).hexdigest()
    return graph


def working_tree_overlay(path: str | Path, *, agent_owned_untracked_paths: list[str] | None = None,
                         agent_owned_tracked_paths: list[str] | None = None) -> dict:
    """Fingerprint the tracked working overlay without staging or writing it.

    Only explicitly agent-owned untracked files are content-bound; all other
    untracked files remain excluded.
    """
    root = project_context.project_root(path)
    base = project_context._git(root, "rev-parse", "HEAD")
    owned_tracked = _owned_tracked_changes(root, agent_owned_tracked_paths)
    selected = ("--", *owned_tracked) if agent_owned_tracked_paths is not None else ()
    patch = _git_bytes(root, "diff", "HEAD", "--binary", "--no-ext-diff", *selected)
    statuses = project_context._git(root, "diff", "HEAD", "--name-status", "--find-renames", *selected).splitlines()
    changed = [field for row in statuses for field in row.split("\t")[1:]]
    untracked = project_context._git(root, "ls-files", "--others", "--exclude-standard").splitlines()
    owned = _owned_untracked(root, agent_owned_untracked_paths)
    digest = hashlib.sha256()
    digest.update(patch)
    digest.update(b"\0")
    for name in owned:
        digest.update(name.encode("utf-8")); digest.update(b"\0")
        digest.update((root / name).read_bytes()); digest.update(b"\0")
    snapshot = {
        "schema": SCHEMA,
        "base_commit": base,
        "tree_hash": digest.hexdigest(),
        "analyzer_version": ANALYZER_VERSION,
        "changed_files": sorted(name for name in changed if name),
        "owned_tracked_files": owned_tracked,
        "untracked_count": len(untracked),
        "owned_untracked_files": owned,
        "coverage_gaps": (["unowned untracked files excluded"] if set(untracked) - set(owned) else []),
    }
    snapshot["working_graph"] = _working_graph(root, snapshot)
    return snapshot


def shadow_ledger(path: str | Path, *, agent_owned_tracked_paths: list[str],
                  agent_owned_untracked_paths: list[str], verified_paths: list[str]) -> dict:
    """Compare a current owner-scoped impact prediction with a hash-only ledger."""
    root = project_context.project_root(path)
    snapshot = working_tree_overlay(
        root, agent_owned_tracked_paths=agent_owned_tracked_paths,
        agent_owned_untracked_paths=agent_owned_untracked_paths)
    actual = []
    for raw in verified_paths:
        candidate = Path(raw)
        if candidate.is_absolute() or ".." in candidate.parts or not str(raw).strip():
            raise ValueError("verified ledger paths must be relative and non-upward")
        actual.append(candidate.as_posix())
    predicted = sorted({node["id"] for node in snapshot["working_graph"]["nodes"]
                        if str(node.get("id", "")).startswith("tests/")})
    actual = sorted(set(actual))
    false_negatives = sorted(set(actual) - set(predicted))
    ledger_hash = hashlib.sha256(json.dumps({"predicted": predicted, "actual": actual},
                                             sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "schema": 1, "base_revision": snapshot["base_commit"],
        "working_hash": snapshot["tree_hash"], "graph_hash": snapshot["working_graph"]["content_hash"],
        "prediction_count": len(predicted), "verified_count": len(actual),
        "false_negative_count": len(false_negatives), "ledger_hash": ledger_hash,
        "complete": False, "durable_writes": 0,
        "coverage_gaps": sorted(set(snapshot["working_graph"]["coverage_gaps"] + [
            "shadow ledger is static evidence, not complete runtime coverage"
        ])),
    }


def _key(snapshot: dict) -> tuple[str, str, str, str]:
    return ("working", snapshot["base_commit"], snapshot["tree_hash"],
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

    def edit_batch_complete(self, path: str | Path, *, mode: str = "code",
                            event_source: str = "client", batch_id: str | None = None,
                            agent_owned_untracked_paths: list[str] | None = None,
                            now: float = 0.0) -> dict:
        """Accept one client-neutral machine event; state remains in memory only."""
        event_source = _machine_identifier(event_source, "event_source")
        correlation_id = _machine_identifier(batch_id or event_source, "batch_id")
        return self.edit_completed(
            path, mode=mode, origin=event_source, correlation_id=correlation_id,
            now=now, agent_owned_untracked_paths=agent_owned_untracked_paths)

    def edit_completed(self, path: str | Path, *, mode: str, origin: str,
                       correlation_id: str, now: float,
                       agent_owned_untracked_paths: list[str] | None = None) -> dict:
        if mode == "knowledge":
            return {"status": "bypass", "durable_writes": 0}
        if mode not in {"code", "mixed"}:
            raise ValueError("edit analysis requires code or mixed mode")
        if origin.startswith("brainlehr_generated"):
            return {"status": "ignored_generated", "durable_writes": 0,
                    "coverage_gaps": ["generated Brainlehr artifact is not source analysis input"]}
        origin = _machine_identifier(origin, "event_source")
        correlation_id = _machine_identifier(correlation_id, "batch_id")
        snapshot = working_tree_overlay(path, agent_owned_untracked_paths=agent_owned_untracked_paths)
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
