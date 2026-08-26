"""Offline, deterministic release identity evidence.

This module only fingerprints local inputs.  It never resolves, installs, or
publishes dependencies; missing locks are reported as a coverage gap.
"""
from __future__ import annotations

import hashlib
import json
import platform
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


def identity(root: str | Path, *, artifact: str | Path | None = None,
             schema: str | None = None, api: str | None = None,
             event: str | None = None, deploy: str | None = None,
             compatibility: dict[str, Any] | None = None,
             canary: dict[str, Any] | None = None,
             rollback: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return release/build identity from local files and explicit metadata."""
    root = Path(root).resolve()
    locks = sorted(p.name for p in root.iterdir()
                   if p.is_file() and (p.name.endswith((".lock", ".lockfile"))
                                       or p.name in {"poetry.lock", "Pipfile.lock", "uv.lock"}))
    gaps = [] if locks else ["lockfile_missing"]
    artifact_path = Path(artifact).resolve() if artifact else None
    result: dict[str, Any] = {
        "schema": 1,
        "network": "disabled",
        "source": {"root": str(root), "manifest_sha256": _manifest_hash(root)},
        "build": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                  "platform": platform.platform(), "executable": Path(sys.executable).name},
        "locks": locks,
        "artifact": ({"path": str(artifact_path), "sha256": _sha256(artifact_path)}
                     if artifact_path and artifact_path.is_file() else None),
        "provenance": {"tool": "brainlehr.release_identity", "version": "1"},
        "compatibility": compatibility or {},
        "identity": {"schema": schema, "api": api, "event": event, "deploy": deploy},
        "canary": canary or {}, "rollback": rollback or {}, "coverage_gaps": gaps,
    }
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    result["sha256"] = hashlib.sha256(encoded).hexdigest()
    return result
