#!/usr/bin/env python3
"""Small, client-neutral project capsule and bounded code probe.

The capsule is evidence, not an architecture guess: Git state, tracked-file
distribution and declared entry points. Semantic knowledge stays in Brainlehr
and is curated only after a caller has verified the current code or a test.
"""
from __future__ import annotations

import ast
import hashlib
import html
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover - package requires Python 3.11
    tomllib = None


SCHEMA = 1
MANIFEST = ".brainlehr.json"
MAX_SELECTED = 3
MAX_CODE_HITS = 8
MAX_BOUNDARY_EVIDENCE = 4
MAX_ACK_REASON = 240
COMMIT_GATE_TOOL = "project-commit-gate"
COMMIT_ACKS = ".brainlehr-commit-acks.jsonl"
IMPACT_GRAPH_SCHEMA = 2
CLIENT_POLICY_SCHEMA = 1
CLIENT_POLICY_RELATIVE_PATH = "docs/CLIENT_BOOTSTRAP_POLICY.json"
BOUNDARY_MODES = {"auto", "knowledge", "code", "mixed"}
BOUNDARY_PHASES = ("plan", "read", "edit", "build", "test", "commit")

_STOPWORDS = {
    "aber", "auch", "code", "eine", "einen", "einer", "fuer", "für",
    "haben", "hier", "how", "into", "kann", "mit", "oder", "project",
    "projekt", "soll", "the", "this", "und", "von", "was", "werden",
    "what", "wie", "with",
}


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True,
        timeout=15, check=False,
    )
    if result.returncode:
        raise ValueError(f"not a readable Git project: {root}")
    return result.stdout.strip()


def project_root(path: str | Path) -> Path:
    candidate = Path(path).expanduser().resolve()
    return Path(_git(candidate, "rev-parse", "--show-toplevel")).resolve()


def _project_id(root: Path) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", root.name.lower()).strip("-")
    return slug or "project"


def _tracked_files(root: Path) -> list[str]:
    return [p for p in _git(root, "ls-files").splitlines() if p]


def capsule(path: str | Path) -> dict:
    root = project_root(path)
    files = _tracked_files(root)
    extensions = Counter(Path(name).suffix.lower() or "[no extension]" for name in files)
    top = Counter(name.split("/", 1)[0] for name in files)
    return {
        "schema": SCHEMA,
        "head": _git(root, "rev-parse", "HEAD"),
        "tracked_files": len(files),
        "extensions": dict(extensions.most_common(10)),
        "top_level": dict(top.most_common(10)),
        "declared_tools": _declared_tools(root),
    }


def _declared_tools(root: Path) -> list[dict]:
    tools: list[dict] = []
    pyproject = root / "pyproject.toml"
    if pyproject.exists() and tomllib is not None:
        try:
            scripts = tomllib.loads(pyproject.read_text(encoding="utf-8")).get(
                "project", {}).get("scripts", {})
        except (OSError, ValueError):
            scripts = {}
        for name in sorted(scripts):
            tools.append({
                "id": name,
                "capability": name.replace("-", " ").replace("_", " "),
                "status": "available",
                "command": name,
                "source": "pyproject.toml [project.scripts]",
            })

    package = root / "package.json"
    if package.exists():
        try:
            scripts = json.loads(package.read_text(encoding="utf-8")).get("scripts", {})
        except (OSError, ValueError):
            scripts = {}
        for name in sorted(scripts):
            tools.append({
                "id": f"npm:{name}",
                "capability": name.replace("-", " ").replace("_", " "),
                "status": "available",
                "command": f"npm run {name}",
                "source": "package.json scripts",
            })
    return tools


def _validate_tool(tool: dict) -> dict:
    if not isinstance(tool, dict):
        raise ValueError("tool reference must be an object")
    required = ("id", "capability", "status")
    if any(not str(tool.get(key, "")).strip() for key in required):
        raise ValueError("tool reference requires id, capability and status")
    status = tool["status"]
    if status not in {"available", "planned"}:
        raise ValueError("tool status must be available or planned")
    if status == "available" and not str(tool.get("command", "")).strip():
        raise ValueError("available tool requires command")
    if status == "planned":
        if tool.get("command"):
            raise ValueError("planned tool must not expose a command")
        if not str(tool.get("reference", "")).strip():
            raise ValueError("planned tool requires a plan reference")
    for key in ("covers", "edge_types"):
        if key in tool and (not isinstance(tool[key], list)
                            or any(not str(value).strip() for value in tool[key])):
            raise ValueError(f"{key} must be a non-empty string list")
    allowed = {"id", "capability", "status", "command", "source", "reference", "when",
               "covers", "edge_types", "artifact"}
    return {key: tool[key] for key in allowed if key in tool and tool[key] not in (None, "")}


def _merge_tools(discovered: list[dict], existing: list[dict], added: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for raw in [*discovered, *existing, *added]:
        tool = _validate_tool(raw)
        merged[tool["id"]] = tool
    return [merged[key] for key in sorted(merged)]


def all_tools(manifest: dict, capsule_data: dict) -> list[dict]:
    """Merge generated entry points with explicit project registrations.

    Explicit registrations win: a project may deliberately replace a native
    discovery with a richer capability reference.  The generated entries stay
    in the capsule so a new entry point does not churn the tracked manifest.
    """
    return _merge_tools([], capsule_data.get("declared_tools", []),
                        manifest.get("tools", []))


def inspect_manifest(path: str | Path) -> dict:
    root = project_root(path)
    target = root / MANIFEST
    if not target.exists():
        return {"state": "missing", "root": str(root), "manifest_path": str(target)}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"state": "partial", "root": str(root), "manifest_path": str(target)}
    if not isinstance(data, dict) or not data.get("project_id") or not isinstance(data.get("tools"), list):
        return {"state": "partial", "root": str(root), "manifest_path": str(target), "manifest": data}
    if data.get("schema") != SCHEMA:
        state = "stale"
    else:
        state = "current"
    return {"state": state, "root": str(root), "manifest_path": str(target), "manifest": data}


def ensure_manifest(path: str | Path, *, project_id: str | None = None,
                    tools: list[dict] | None = None) -> dict:
    before = inspect_manifest(path)
    root = Path(before["root"])
    old = before.get("manifest") if isinstance(before.get("manifest"), dict) else {}
    generated_sources = {"pyproject.toml [project.scripts]", "package.json scripts"}
    existing_tools = [tool for tool in old.get("tools", [])
                      if tool.get("source") not in generated_sources]
    manifest = {
        "schema": SCHEMA,
        "project_id": project_id or old.get("project_id") or _project_id(root),
        "tools": _merge_tools([], existing_tools, tools or []),
    }
    encoded = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    target = root / MANIFEST
    previous = target.read_text(encoding="utf-8") if target.exists() else None
    if previous != encoded:
        target.write_text(encoded, encoding="utf-8")
    return {
        "before": before["state"],
        "after": "current",
        "changed": previous != encoded,
        "root": str(root),
        "manifest_path": str(target),
        "manifest": manifest,
        "capsule": capsule(root),
    }


def task_terms(task: str) -> list[str]:
    terms = []
    for term in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9_]+", task.lower()):
        if len(term) < 4 or term in _STOPWORDS or term in terms:
            continue
        terms.append(term)
    return terms[:6]


def relevant_tools(manifest: dict, task: str) -> list[dict]:
    wanted = set(task_terms(task))
    result = []
    for tool in manifest.get("tools", []):
        haystack = " ".join(str(value) for value in tool.values()).lower()
        if wanted and not any(term in haystack for term in wanted):
            continue
        item = dict(tool)
        item["callable"] = item["status"] == "available"
        if not item["callable"]:
            item.pop("command", None)
        result.append(item)
    return result


def code_probe(path: str | Path, task: str, *, limit: int = MAX_CODE_HITS) -> list[dict]:
    root = project_root(path)
    terms = task_terms(task)
    if not terms:
        return []
    command = ["git", "-C", str(root), "grep", "-n", "-I", "-i"]
    for term in terms:
        command += ["-e", term]
    command.append("--")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               text=True)
    hits = []
    try:
        assert process.stdout is not None
        for line in process.stdout:
            parts = line.rstrip("\n").split(":", 2)
            if len(parts) != 3:
                continue
            hits.append({"path": parts[0], "line": int(parts[1]), "excerpt": parts[2].strip()[:240]})
            if len(hits) >= min(max(1, limit), MAX_CODE_HITS):
                process.terminate()
                break
    finally:
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
    return hits


def selection_contract(depth: str, selected: list[str]) -> dict:
    if depth not in {"summary", "relations", "full"}:
        raise ValueError("depth must be summary, relations or full")
    if depth != "summary" and not selected:
        raise ValueError(f"{depth} requires explicitly selected node IDs")
    if len(selected) > MAX_SELECTED:
        raise ValueError(f"select at most {MAX_SELECTED} node IDs")
    if depth == "summary":
        return {
            "must": "select only task-relevant IDs before loading more",
            "may": ["relations for selected IDs", "full text for selected IDs"],
            "must_not": "recursively load a branch or all search hits",
        }
    return {
        "must": "verify returned evidence against current primary code or tests",
        "may": ["curate a reusable finding with commit and path:line source"],
        "must_not": "store raw source files or an unverified inference as knowledge",
    }


def _staged_snapshot(root: Path) -> dict:
    """Read only the index; the digest invalidates an acknowledgement on any change."""
    base = _git(root, "rev-parse", "HEAD")
    names = [name for name in _git(root, "diff", "--cached", "--name-only").splitlines() if name]
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--cached", "--binary", "--no-ext-diff"],
        capture_output=True, timeout=15, check=False)
    if result.returncode:
        raise ValueError(f"cannot read staged diff for {root}")
    untracked = [name for name in _git(root, "ls-files", "--others", "--exclude-standard").splitlines()
                 if name and name != COMMIT_ACKS]
    digest = hashlib.sha256(result.stdout)
    for name in sorted(untracked):
        candidate = root / name
        if candidate.is_file():
            digest.update(name.encode("utf-8") + b"\0")
            digest.update(candidate.read_bytes())
    return {
        "base": base,
        "files": [*names, *untracked],
        "tree_hash": digest.hexdigest(),
        "untracked_files": untracked,
    }


def _boundary_next(phase: str) -> list[str]:
    return list(BOUNDARY_PHASES[BOUNDARY_PHASES.index(phase) + 1:])[:3]


def _analysis_cadence(mode: str, phase: str) -> dict:
    """Expose the bounded client cadence without starting a watcher or daemon."""
    if mode == "knowledge":
        return {"status": "bypass", "durable_writes": 0,
                "must_not": "scan or analyze project code"}
    if mode not in {"code", "mixed"}:
        return {"status": "unknown", "durable_writes": 0}
    steps = {
        "plan": "task_start: load capsule and current context",
        "read": "before_first_code_action: load current context",
        "edit": "after_completed_tool_batch: coalesce latest working-tree overlay",
        "build": "recompute only when working-tree hash changed",
        "test": "recompute only when working-tree hash changed",
        "commit": "analyze staged tree and require the opt-in gate",
    }
    return {
        "status": "ephemeral_overlay",
        "step": steps[phase],
        "post_commit": "append one project_change receipt for the committed revision",
        "must_not": "write a durable receipt for an edit batch or auto-edit source",
    }


def client_policy_metadata() -> dict:
    """Return only the tracked policy identity, never instructions from data."""
    root = Path(__file__).resolve().parents[1]
    policy_path = root / CLIENT_POLICY_RELATIVE_PATH
    try:
        raw = policy_path.read_bytes()
        source_revision = _git(root, "hash-object", CLIENT_POLICY_RELATIVE_PATH)
    except (OSError, ValueError):
        return {"policy_schema": CLIENT_POLICY_SCHEMA, "policy_hash": "unavailable",
                "source_revision": "unavailable", "coverage_gaps": ["policy bundle unavailable"]}
    return {"policy_schema": CLIENT_POLICY_SCHEMA, "policy_hash": hashlib.sha256(raw).hexdigest(),
            "source_revision": source_revision}


def boundary_contract(*, mode: str = "auto", phase: str = "plan",
                      operation: str | None = None,
                      project_path: str | Path | None = None) -> dict:
    """Classify one request without prompt capture, profile state or code search.

    `project_path` is examined only for the server-verifiable staged-tree
    signal.  A repository, manifest or cwd alone is deliberately `unknown`.
    """
    if mode not in BOUNDARY_MODES:
        raise ValueError("mode must be auto, knowledge, code or mixed")
    if phase not in BOUNDARY_PHASES:
        raise ValueError("phase must be plan, read, edit, build, test or commit")
    operations = {"knowledge_search": "knowledge", "knowledge_read": "knowledge",
                  "lesson_query": "knowledge", "project_context": "mixed",
                  "project_change": "code"}
    if operation is not None and operation not in operations:
        raise ValueError("operation is not a supported Brainlehr operation")

    evidence: list[str] = []
    if mode != "auto":
        resolved, reason = mode, "explicit mode"
        evidence.append(f"override:{mode}")
    else:
        staged = None
        if project_path is not None:
            staged = _staged_snapshot(project_root(project_path))
        if staged and staged["files"]:
            resolved, reason = "code", "verified staged tree"
            evidence.append("staged_tree")
        elif operation:
            resolved, reason = operations[operation], f"operation:{operation}"
            evidence.append(f"operation:{operation}")
        else:
            resolved, reason = "unknown", "no verified action or operation"

    code = resolved in {"code", "mixed"}
    knowledge = resolved in {"knowledge", "mixed"}
    must, may, must_not, gaps = [], [], [], []
    if knowledge:
        must.append("keep knowledge retrieval summary-first")
        may.append("select direct relations or full text explicitly")
        must_not.append("store raw chat, thinking or a user profile")
    if code:
        must.append("load current project context before code action")
        may.append("record verified impact after commit")
        must_not.append("treat static imports as runtime data flow")
        gaps.append("runtime, build and timing evidence require a registered tool")
    if resolved == "unknown":
        must.append("request an explicit mode or supported operation")
        must_not.append("infer code work from cwd, repo or manifest")
    if resolved == "knowledge":
        must_not.extend(["scan repository code", "run code retrieval or commit gate"])
    return {
        "mode": resolved,
        "reason": reason,
        "evidence": evidence[:MAX_BOUNDARY_EVIDENCE],
        "must": must[:4], "may": may[:4], "must_not": must_not[:4],
        "coverage_gaps": gaps[:4], "allowed_next": _boundary_next(phase),
        "analysis": _analysis_cadence(resolved, phase),
        **client_policy_metadata(),
    }


def _commit_gate_enabled(root: Path) -> bool:
    inspected = inspect_manifest(root)
    manifest = inspected.get("manifest") or {}
    return any(tool.get("id") == COMMIT_GATE_TOOL and tool.get("status") == "available"
               for tool in manifest.get("tools", []))


def _ack_path(root: Path) -> Path:
    return root / COMMIT_ACKS


def _matching_ack(root: Path, snapshot: dict) -> dict | None:
    path = _ack_path(root)
    if not path.exists():
        return None
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("base") == snapshot["base"] and row.get("tree_hash") == snapshot["tree_hash"]:
            return row
    return None


def staged_commit_gate(path: str | Path, *, acknowledge_reason: str | None = None) -> dict:
    """Check or append one local acknowledgement for an opt-in staged tree.

    The acknowledgement file is deliberately local and append-only: it is an
    operator receipt, not source material and not a replacement for the
    post-commit `project_change` evidence.
    """
    root = project_root(path)
    if not _commit_gate_enabled(root):
        return {"status": "not_enabled", "must_not": "treat this as a security boundary"}
    snapshot = _staged_snapshot(root)
    if not snapshot["files"]:
        return {"status": "pass", "snapshot": snapshot, "coverage_gaps": []}
    gaps = ["staged tree has no verified post-commit impact receipt"]
    non_python = [name for name in snapshot["files"] if not name.endswith(".py")]
    if non_python:
        gaps.append("static Python analyzer does not cover: " + ", ".join(non_python[:4]))
    if acknowledge_reason is not None:
        reason = acknowledge_reason.strip()
        if not reason or len(reason) > MAX_ACK_REASON:
            raise ValueError(f"acknowledgement reason must contain 1..{MAX_ACK_REASON} characters")
        receipt = {"schema": 1, "observed_at": datetime.now(timezone.utc).isoformat(),
                   "base": snapshot["base"], "tree_hash": snapshot["tree_hash"],
                   "files": snapshot["files"], "reason": reason, "coverage_gaps": gaps}
        with _ack_path(root).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n")
        return {"status": "acknowledged", "snapshot": snapshot, "receipt": receipt,
                "coverage_gaps": gaps,
                "next": "commit, then run project_change with the verified checks"}
    ack = _matching_ack(root, snapshot)
    if ack:
        return {"status": "acknowledged", "snapshot": snapshot, "receipt": ack,
                "coverage_gaps": gaps,
                "next": "commit, then run project_change with the verified checks"}
    return {"status": "blocked", "snapshot": snapshot, "coverage_gaps": gaps,
            "next": f"project-boundary --project-root {root} --ack 'non-secret reason'"}


def _git_at(root: Path, revision: str, path: str) -> str:
    return _git(root, "show", f"{revision}:{path}")


def _python_import_edges(root: Path, revision: str, observed_at: str) -> tuple[list[dict], list[dict], list[dict]]:
    """Return proven static import edges as (provider, consumer).

    This is intentionally not called a data-flow graph. Imports prove module
    dependency, not that a value reaches a sink (L-503687).
    """
    files = [p for p in _git(root, "ls-tree", "-r", "--name-only", revision).splitlines()
             if p.endswith(".py")]
    modules: dict[str, set[str]] = {}
    for path in files:
        module = path[:-3].replace("/", ".")
        if module.endswith(".__init__"):
            module = module[:-9]
        variants = {module, Path(path).stem}
        for prefix in ("src.", "lib."):
            if module.startswith(prefix):
                variants.add(module[len(prefix):])
        for variant in variants:
            modules.setdefault(variant, set()).add(path)

    edges: dict[tuple[str, str], dict] = {}
    ambiguous: list[dict] = []
    unsupported: list[dict] = []
    for consumer in files:
        try:
            tree = ast.parse(_git_at(root, revision, consumer), filename=consumer)
        except (SyntaxError, ValueError):
            continue
        consumer_module = consumer[:-3].replace("/", ".")
        package = consumer_module.rsplit(".", 1)[0] if "." in consumer_module else ""
        names: list[tuple[str, int]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend((alias.name, node.lineno) for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    parts = package.split(".") if package else []
                    keep = max(0, len(parts) - node.level + 1)
                    base = ".".join([*parts[:keep], base]).strip(".")
                if base:
                    for alias in node.names:
                        if alias.name == "*":
                            unsupported.append({
                                "consumer": consumer, "form": "star_import",
                                "source_ref": f"{consumer}:{node.lineno}",
                                "observed_commit": revision,
                            })
                        else:
                            names.append((f"{base}.{alias.name}", node.lineno))
                    names.append((base, node.lineno))
            elif isinstance(node, ast.Call):
                func = node.func
                dynamic = (isinstance(func, ast.Name) and func.id == "__import__") or (
                    isinstance(func, ast.Attribute) and func.attr == "import_module")
                if dynamic:
                    unsupported.append({
                        "consumer": consumer, "form": "dynamic_import",
                        "source_ref": f"{consumer}:{node.lineno}",
                        "observed_commit": revision,
                    })
        for name, line in names:
            candidates = [name]
            while "." in candidates[-1]:
                candidates.append(candidates[-1].rsplit(".", 1)[0])
            matches = next((modules[c] for c in candidates if c in modules), set())
            if len(matches) > 1:
                ambiguous.append({
                    "consumer": consumer, "import": name,
                    "candidates": sorted(matches), "source_ref": f"{consumer}:{line}",
                    "observed_commit": revision,
                })
                continue
            provider = next(iter(matches), None)
            if provider and provider != consumer:
                edges[(provider, consumer)] = {
                    "from": provider,
                    "to": consumer,
                    "edge_type": "static_import",
                    "source_ref": f"{consumer}:{line}",
                    "observed_commit": revision,
                    "observed_at": observed_at,
                    "evidence": f"Python AST import {name}",
                }
    return list(edges.values()), ambiguous, unsupported


def changed_files(path: str | Path, base: str, head: str = "HEAD") -> list[str]:
    root = project_root(path)
    rows = _git(root, "diff", "--name-status", "--find-renames",
                "--diff-filter=ACMRD", f"{base}..{head}").splitlines()
    changed: list[str] = []
    for row in rows:
        fields = row.split("\t")
        if len(fields) < 2:
            continue
        # Renames carry old and new paths.  Both are impact roots because the
        # base graph may still have consumers of the old provider.
        changed.extend(fields[1:] if fields[0].startswith(("R", "C")) else fields[1:2])
    return list(dict.fromkeys(changed))


def impact_chain(path: str | Path, base: str, head: str = "HEAD") -> dict:
    """Compute every statically proven downstream Python importer by distance."""
    root = project_root(path)
    observed_at = datetime.now(timezone.utc).isoformat()
    resolved_base = _git(root, "rev-parse", base)
    resolved_head = _git(root, "rev-parse", head)
    changed = changed_files(root, resolved_base, resolved_head)
    base_edges, base_ambiguous, base_unsupported = _python_import_edges(root, resolved_base, observed_at)
    head_edges, head_ambiguous, head_unsupported = _python_import_edges(root, resolved_head, observed_at)
    edges_by_pair = {(edge["from"], edge["to"]): edge for edge in base_edges}
    edges_by_pair.update({(edge["from"], edge["to"]): edge for edge in head_edges})
    edges = list(edges_by_pair.values())
    consumers: dict[str, set[str]] = {}
    providers: dict[str, set[str]] = {}
    evidence_by_pair = {}
    for edge in edges:
        provider, consumer = edge["from"], edge["to"]
        consumers.setdefault(provider, set()).add(consumer)
        providers.setdefault(consumer, set()).add(provider)
        evidence_by_pair[(provider, consumer)] = edge

    distances: dict[str, int] = {}
    frontier = list(changed)
    visited = set(changed)
    distance = 0
    impact_edges = []
    while frontier:
        distance += 1
        next_frontier = []
        for current in frontier:
            for consumer in sorted(consumers.get(current, ())):
                if consumer in visited:
                    continue
                visited.add(consumer)
                distances[consumer] = distance
                impact_edges.append(evidence_by_pair[(current, consumer)])
                next_frontier.append(consumer)
        frontier = next_frontier
    by_distance: dict[str, list[str]] = {}
    for file, hop in sorted(distances.items(), key=lambda item: (item[1], item[0])):
        by_distance.setdefault(str(hop), []).append(file)
    return {
        "base": resolved_base,
        "head": resolved_head,
        "observed_at": observed_at,
        "changed_files": changed,
        "input_dependencies": {
            file: sorted(providers.get(file, ())) for file in changed if providers.get(file)
        },
        "consumers_by_distance": by_distance,
        "consumer_count": len(distances),
        "impact_edges": impact_edges,
        "edge_type": "static_import",
        "not_proven": ["runtime data flow", "call flow", "I/O timing", "non-Python dependencies"],
        "unsupported_changed_files": [file for file in changed if not file.endswith(".py")],
        "ambiguous_imports": [*base_ambiguous, *head_ambiguous],
        "unsupported_static_forms": [*base_unsupported, *head_unsupported],
        "coverage_status": (
            "coverage_gap" if (not all(file.endswith(".py") for file in changed)
                               or base_ambiguous or head_ambiguous)
            else "static_python_imports_with_known_unsupported_forms"
            if base_unsupported or head_unsupported
            else "static_python_imports_complete"
        ),
    }


def impact_graph(path: str | Path, impact: dict, verification: list[str]) -> dict:
    """Make one revision-bound, typed impact graph without source-code copies.

    Caller-supplied verification remains labelled as such; runtime and timing
    become evidence only through an explicitly registered project tool.
    """
    root = project_root(path)
    inspected = inspect_manifest(root)
    manifest = inspected.get("manifest") or {}
    tools = manifest.get("tools", []) if isinstance(manifest, dict) else []
    evidence_tools = [
        {key: tool[key] for key in ("id", "artifact", "covers", "edge_types") if key in tool}
        for tool in tools
        if tool.get("status") == "available" and set(tool.get("covers", []))
        & {"test", "runtime", "timing", "contract"}
    ]
    evidence_tools.sort(key=lambda tool: tool["id"])
    nodes = [{"id": name, "kind": "changed", "distance": 0}
             for name in sorted(impact["changed_files"])]
    nodes.extend({"id": name, "kind": "consumer", "distance": int(distance)}
                 for distance, names in sorted(impact["consumers_by_distance"].items(), key=lambda item: int(item[0]))
                 for name in names)
    gaps = list(impact["not_proven"])
    if impact["unsupported_changed_files"]:
        gaps.append("non-Python changed files")
    if impact["ambiguous_imports"]:
        gaps.append("ambiguous static imports")
    if impact["unsupported_static_forms"]:
        gaps.append("known unsupported static forms")
    if not any("timing" in tool.get("covers", []) for tool in evidence_tools):
        gaps.append("no registered timing evidence")
    graph = {
        "schema": IMPACT_GRAPH_SCHEMA,
        "analyzer": "static-python-imports-v1",
        "base_revision": impact["base"],
        "source_revision": impact["head"],
        "nodes": nodes,
        "edges": [{key: edge[key] for key in
                   ("from", "to", "edge_type", "source_ref", "observed_commit", "evidence")}
                  for edge in sorted(impact["impact_edges"], key=lambda edge: (
                      edge["from"], edge["to"], edge["source_ref"]))],
        "evidence": [{
            "source_kind": "python_ast_import", "source_ref": edge["source_ref"],
            "strength": "static", "revision": impact["head"],
            "analyzer_version": "static-python-imports-v1", "status": "observed",
            "observed_at": "commit:" + impact["head"],
        } for edge in sorted(impact["impact_edges"], key=lambda edge: edge["source_ref"])],
        "conflicts": [],
        "caller_verification": verification[:20],
        "registered_evidence_tools": evidence_tools,
        "coverage_status": impact["coverage_status"],
        "coverage_gaps": gaps,
    }
    encoded = json.dumps(graph, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    graph["content_hash"] = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return graph


def impact_mermaid(graph: dict) -> str:
    """Deterministic human projection of a typed graph; never a second analyzer."""
    ids = {node["id"]: f"n{index}" for index, node in enumerate(graph["nodes"])}
    lines = ["flowchart TD"]
    for node in graph["nodes"]:
        label = node["id"].replace('"', "'")
        lines.append(f'  {ids[node["id"]]}["{label} · {node["kind"]} d{node["distance"]}"]')
    for edge in graph["edges"]:
        if edge["from"] in ids and edge["to"] in ids:
            lines.append(f'  {ids[edge["from"]]} -->|{edge["edge_type"]}| {ids[edge["to"]]}')
    return "\n".join(lines) + "\n"


def impact_visualization_ref(graph: dict) -> dict:
    """State the deterministic renderers which read the canonical graph only."""
    return {
        "source_graph_schema": graph["schema"],
        "source_revision": graph["source_revision"],
        "content_hash": graph["content_hash"],
        "available_formats": ["mermaid", "cytoscape", "metroviz"],
        "views": ["impact_distance", "base_head_edge_delta", "test_evidence",
                  "timing_sequence", "coverage_gaps"],
        "metroviz": {"status": "available", "source": "evidence_projections.metroviz_projection"},
        "must_not": "treat this projection as a second analyzer or source of truth",
    }


def impact_cytoscape_html(graph: dict) -> str:
    """Deterministic offline HTML shell; Cytoscape reads only this graph JSON.

    A caller must place the MIT-licensed local ``cytoscape.min.js`` beside the
    saved HTML (the CLI does not fetch a CDN or create a second graph).
    """
    # Keep the offline view bounded while retaining a deterministic nearby slice.
    nodes = list(graph.get("nodes", []))
    projection_gap = None
    if len(nodes) > 500:
        selected = sorted(nodes, key=lambda n: (n.get("distance", 999999), n.get("id", "")))[:500]
        selected_ids = {n.get("id") for n in selected}
        projection_gap = f"coverage_gap: graph exceeds 500 nodes; rendered 500-node filtered subgraph of {len(nodes)}."
        graph = {**graph, "nodes": selected,
                 "edges": [e for e in graph.get("edges", [])
                           if e.get("from") in selected_ids and e.get("to") in selected_ids],
                 "projection": {"kind": "filtered_subgraph", "limit": 500,
                                "full_node_count": len(nodes), "coverage_gap": projection_gap}}
    encoded = json.dumps(graph, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    encoded = encoded.replace("<", "\\u003c")
    revision = html.escape(str(graph["source_revision"]), quote=True)
    digest = html.escape(str(graph["content_hash"]), quote=True)
    options = "".join(f'<option value="{view}">{view}</option>' for view in
                      ("impact_distance", "base_head_edge_delta", "test_evidence",
                       "timing_sequence", "coverage_gaps"))
    gap = f'<p role="alert">{html.escape(projection_gap)}</p>' if projection_gap else ""
    return f'''<!doctype html>
<html lang="en" data-source-revision="{revision}" data-content-hash="{digest}">
<meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'">
<title>Brainlehr impact evidence</title>
<style>body{{font:14px system-ui;margin:1rem}}#cy{{height:65vh;border:1px solid #888}}header{{display:flex;gap:1rem;align-items:center;flex-wrap:wrap}}</style>
<header><strong>Revision-bound impact evidence</strong><label for="view">View</label><select id="view" aria-label="Impact evidence view">{options}</select><code>{revision[:12]} · {digest[:12]}</code></header>{gap}
<div id="cy" role="img" aria-label="Impact evidence graph"></div>
<script src="cytoscape.min.js"></script><script>
const graph={encoded}; const elements=[...graph.nodes.map(n=>({{data:{{id:n.id,label:n.id}}}})),...graph.edges.map((e,i)=>({{data:{{id:'e'+i,source:e.from,target:e.to,label:e.edge_type||e.type}}}}))];
if(window.cytoscape) cytoscape({{container:document.getElementById('cy'),elements,style:[{{selector:'node',style:{{label:'data(label)'}}}},{{selector:'edge',style:{{label:'data(label)',width:2}}}}],layout:{{name:'breadthfirst'}}}}); else document.getElementById('cy').textContent='Missing local cytoscape.min.js; graph provenance remains above.';
</script></html>\n'''
