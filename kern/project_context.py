#!/usr/bin/env python3
"""Small, client-neutral project capsule and bounded code probe.

The capsule is evidence, not an architecture guess: Git state, tracked-file
distribution and declared entry points. Semantic knowledge stays in Brainlehr
and is curated only after a caller has verified the current code or a test.
"""
from __future__ import annotations

import ast
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


def _git_at(root: Path, revision: str, path: str) -> str:
    return _git(root, "show", f"{revision}:{path}")


def _python_import_edges(root: Path, revision: str, observed_at: str) -> tuple[list[dict], list[dict]]:
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
                    names.append((base, node.lineno))
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
    return list(edges.values()), ambiguous


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
    base_edges, base_ambiguous = _python_import_edges(root, resolved_base, observed_at)
    head_edges, head_ambiguous = _python_import_edges(root, resolved_head, observed_at)
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
        "coverage_status": ("complete_for_static_python_imports"
                            if all(file.endswith(".py") for file in changed)
                            and not base_ambiguous and not head_ambiguous
                            else "coverage_gap"),
    }
