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


def read_manifests(root: str | Path) -> list[dict[str, Any]]:
    """Parse pyproject.toml and requirements*.txt without network access."""
    root = Path(root)
    nodes: list[dict[str, Any]] = []
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        import tomllib
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        project = data.get("project", {})
        for scope, values in (("runtime", project.get("dependencies", [])),):
            for value in values:
                match = _REQ.match(value.strip())
                if match:
                    nodes.append(_node(match.group(1), match.group(3), scope, "pyproject.toml"))
        for scope, values in project.get("optional-dependencies", {}).items():
            for value in values:
                match = _REQ.match(value.strip())
                if match:
                    nodes.append(_node(match.group(1), match.group(3), scope, "pyproject.toml"))
    for path in sorted(root.glob("requirements*.txt")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            match = _REQ.match(line) if line and not line.startswith(("-", "http")) else None
            if match:
                nodes.append(_node(match.group(1), match.group(3), "runtime", path.name))
    return sorted(nodes, key=lambda item: (item["name"], item["scope"], item["source"]))


def evidence(root: str | Path, *, current: list[dict[str, Any]] | None = None,
             candidate: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    current = read_manifests(root) if current is None else current
    candidate = current if candidate is None else candidate
    old = {(n["name"], n["scope"]): n["version"] for n in current}
    new = {(n["name"], n["scope"]): n["version"] for n in candidate}
    delta = [{"name": name, "scope": scope, "from": old.get((name, scope)), "to": version}
             for (name, scope), version in sorted(new.items()) if old.get((name, scope)) != version]
    body = {"schema": 1, "network": "disabled", "nodes": current, "candidate_nodes": candidate,
            "delta": delta, "advisory": {"status": "not_checked", "source": None},
            "rollback": {"required": bool(delta), "basis": "restore_previous_manifest"}}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    body["sha256"] = hashlib.sha256(encoded).hexdigest()
    return body
