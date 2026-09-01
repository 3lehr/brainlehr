"""Small, offline dependency evidence reader.

It deliberately reads local manifests only; resolution and vulnerability lookup
belong to an explicitly selected external tool.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


_REQ = re.compile(r"^([A-Za-z0-9_.-]+)\s*(?:([<>=!~]+)\s*([^;\s]+))?")


def _node(name: str, version: str | None, scope: str, source: str) -> dict[str, Any]:
    return {"name": name.lower().replace("_", "-"), "version": version or "unknown",
            "scope": scope, "source": source}


def _requirements(values: list[str], scope: str, source: str) -> list[dict[str, Any]]:
    nodes = []
    for value in values:
        match = _REQ.match(value.strip())
        if match:
            nodes.append(_node(match.group(1), match.group(3), scope, source))
    return nodes


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_lockfile(path: str | Path) -> list[dict[str, Any]]:
    """Read uv's already-resolved package identities; never resolve or download."""
    path = Path(path)
    if not path.exists():
        return []
    import tomllib
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return sorted((_node(p["name"], p.get("version"), "transitive", path.name)
                   for p in data.get("package", []) if p.get("name") != "brainlehr"),
                  key=lambda item: item["name"])


def lock_packages(root: str | Path) -> list[dict[str, Any]]:
    return read_lockfile(Path(root) / "uv.lock")


def lock_delta(current_lock: str | Path, candidate_lock: str | Path,
               consumers: dict[str, list[str]] | None = None) -> dict[str, Any]:
    """Compare two already-written locks; update/install is deliberately absent."""
    current_path, candidate_path = Path(current_lock), Path(candidate_lock)
    old = {node["name"]: node["version"] for node in read_lockfile(current_path)}
    new = {node["name"]: node["version"] for node in read_lockfile(candidate_path)}
    changes = [{"name": name, "from": old.get(name), "to": new.get(name),
                "consumers": sorted((consumers or {}).get(name, []))}
               for name in sorted(set(old) | set(new)) if old.get(name) != new.get(name)]
    body = {"schema": 1, "network": "disabled",
            "current": {"path": current_path.name, "sha256": _sha256(current_path)},
            "candidate": {"path": candidate_path.name, "sha256": _sha256(candidate_path)},
            "changes": changes,
            "rollback": {"required": bool(changes), "command": "restore_previous_lock"}}
    body["sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return body


def sbom_packages(path: str | Path) -> list[dict[str, Any]]:
    """Normalize SPDX package names/licenses from a supplied local SBOM."""
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    return sorted(({
        "name": str(item.get("name", "unknown")).lower(),
        "version": str(item.get("versionInfo") or "unknown"),
        "license": item.get("licenseConcluded") or item.get("licenseDeclared") or "NOASSERTION",
        "source": source.name,
    } for item in data.get("packages", []) if item.get("name")), key=lambda item: item["name"])


def read_manifests(root: str | Path) -> list[dict[str, Any]]:
    """Parse pyproject.toml and requirements*.txt without network access."""
    root = Path(root)
    nodes: list[dict[str, Any]] = []
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        import tomllib
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        project = data.get("project", {})
        nodes.extend(_requirements(project.get("dependencies", []), "runtime", "pyproject.toml"))
        for scope, values in project.get("optional-dependencies", {}).items():
            nodes.extend(_requirements(values, scope, "pyproject.toml"))
        for scope, values in data.get("dependency-groups", {}).items():
            nodes.extend(_requirements(values, scope, "pyproject.toml"))
    for path in sorted(root.glob("requirements*.txt")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            match = _REQ.match(line) if line and not line.startswith(("-", "http")) else None
            if match:
                nodes.append(_node(match.group(1), match.group(3), "runtime", path.name))
    return sorted(nodes, key=lambda item: (item["name"], item["scope"], item["source"]))


def evidence(root: str | Path, *, current: list[dict[str, Any]] | None = None,
             candidate: list[dict[str, Any]] | None = None,
             sbom: str | Path | None = None, advisory: dict[str, Any] | None = None,
             consumers: dict[str, list[str]] | None = None) -> dict[str, Any]:
    current = read_manifests(root) if current is None else current
    candidate = current if candidate is None else candidate
    old = {(n["name"], n["scope"]): n["version"] for n in current}
    new = {(n["name"], n["scope"]): n["version"] for n in candidate}
    delta = [{"name": name, "scope": scope, "from": old.get((name, scope)), "to": version}
             for (name, scope), version in sorted(new.items()) if old.get((name, scope)) != version]
    root_path = Path(root)
    lock = root_path / "uv.lock"
    sbom_path = Path(sbom) if sbom else None
    body = {"schema": 2, "network": "disabled", "nodes": current, "candidate_nodes": candidate,
            "lock_nodes": lock_packages(root_path), "delta": delta,
            "consumers": consumers or {},
            "inputs": {"lock_sha256": _sha256(lock) if lock.exists() else None,
                       "sbom_sha256": _sha256(sbom_path) if sbom_path and sbom_path.exists() else None},
            "sbom": sbom_packages(sbom_path) if sbom_path and sbom_path.exists() else [],
            "advisory": advisory or {"status": "not_checked", "source": None},
            "rollback": {"required": bool(delta), "basis": "restore_previous_manifest"}}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    body["sha256"] = hashlib.sha256(encoded).hexdigest()
    return body
