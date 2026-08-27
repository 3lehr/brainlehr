"""Opt-in, fail-closed gate for AI-owned staged edits (P99/P104).

The manifest is a small JSON binding.  It contains no source, comments,
secrets or proof text; a successful check returns only a receipt digest.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

from ai_comment_policy import PolicyViolation, validate_ai_result, validate_machine_directive


SCHEMA = 1
POLICY_VERSION = "brainlehr-ai-edit-v1"
MANIFEST_KEYS = frozenset({
    "schema", "policy_version", "base_revision", "revision",
    "staged_diff_sha256", "ai_owned_paths", "human_comment_inventory_sha256",
    "accepted_anchor_ids",
})
_HEX = re.compile(r"^[0-9a-f]{7,64}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git(root: Path, *args: str, check: bool = True) -> bytes:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    if check and result.returncode:
        raise ValueError(f"git failed: {' '.join(args)}")
    return result.stdout


def _head(root: Path) -> str:
    value = _git(root, "rev-parse", "HEAD").decode().strip()
    if not _HEX.fullmatch(value):
        raise ValueError("cannot determine base revision")
    return value


def _diff(root: Path) -> bytes:
    return _git(root, "diff", "--cached", "--binary", "--no-color", "--no-ext-diff")


def _changed_paths(root: Path) -> list[str]:
    raw = _git(root, "diff", "--cached", "--name-only", "--diff-filter=ACDMRTUXB")
    return sorted(path for path in raw.decode().splitlines() if path)


def _added_lines(root: Path) -> dict[str, list[bytes]]:
    raw = _git(root, "diff", "--cached", "--unified=0", "--no-color", "--no-ext-diff")
    result: dict[str, list[bytes]] = {}
    path = None
    for line in raw.splitlines(keepends=True):
        if line.startswith(b"diff --git b"):
            path = None
        elif line.startswith(b"+++ b/"):
            path = line[6:].rstrip(b"\r\n").decode("utf-8", "surrogateescape")
            result.setdefault(path, [])
        elif path and line.startswith(b"+") and not line.startswith(b"+++"):
            result[path].append(line[1:])
    return result


def _file_at(root: Path, revision: str, path: str, *, staged: bool = False) -> bytes:
    ref = ":" if staged else f"{revision}:"
    result = _git(root, "show", f"{ref}{path}", check=False)
    return result


def _comment_payload(line: bytes) -> str | None:
    text = line.decode("utf-8", "surrogateescape").rstrip("\r\n").lstrip()
    for marker in ("#", "//", "--", "/*", "*"):
        if text.startswith(marker):
            return text[len(marker):].strip().rstrip("*/").strip()
    return None


def _comment_inventory(root: Path, revision: str, *, paths: list[str],
                       remove_hashes: Mapping[str, list[str]] | None = None,
                       staged: bool = False) -> str:
    rows: list[dict[str, object]] = []
    remove_hashes = remove_hashes or {}
    for path in paths:
        content = _file_at(root, revision, path, staged=staged)
        removed = set(remove_hashes.get(path, ()))
        for line in content.splitlines(keepends=True):
            payload = _comment_payload(line)
            if payload is not None and _hash(line) not in removed:
                rows.append({"path": path, "line": payload})
    return _hash(_json(rows).encode("utf-8"))


def _validate_paths(value: object) -> dict[str, list[str]]:
    if not isinstance(value, Mapping):
        raise ValueError("ai_owned_paths must be an object")
    result: dict[str, list[str]] = {}
    for path, hashes in value.items():
        if not isinstance(path, str) or PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts:
            raise ValueError("invalid AI-owned path")
        if not isinstance(hashes, list) or not all(isinstance(item, str) and _HEX64.fullmatch(item) for item in hashes):
            raise ValueError("AI-owned paths require exact added hashes")
        result[path] = hashes
    return result


def build_manifest(root: str | Path, *, registry: object, accepted_anchor_ids: list[str],
                   base_revision: str | None = None,
                   ai_owned_paths: Mapping[str, list[str]] | None = None) -> dict:
    """Build deterministic manifest from current staged tree; never writes it."""
    root = Path(root)
    revision = base_revision or _head(root)
    paths = _changed_paths(root)
    additions = _added_lines(root)
    owned = dict(ai_owned_paths or {path: [_hash(line) for line in additions.get(path, [])] for path in paths})
    if set(owned) != set(paths):
        raise ValueError("AI-owned paths must cover exactly staged paths")
    return {
        "schema": SCHEMA, "policy_version": POLICY_VERSION,
        "base_revision": revision, "revision": revision,
        "staged_diff_sha256": _hash(_diff(root)), "ai_owned_paths": dict(sorted(owned.items())),
        "human_comment_inventory_sha256": _comment_inventory(root, revision, paths=paths),
        "accepted_anchor_ids": sorted(accepted_anchor_ids),
    }


def _check_comments(additions: Mapping[str, list[bytes]], *, registry: object,
                    accepted: set[str]) -> None:
    for lines in additions.values():
        for line in lines:
            payload = _comment_payload(line)
            if payload is None:
                continue
            if payload in {"NONE", "shebang", "encoding", "license", "linter", "type_pragma",
                           "framework", "docgen", "generated"}:
                if payload != "NONE":
                    validate_machine_directive(payload)
                else:
                    validate_ai_result(payload, registry)
                continue
            if not payload.startswith("brainlehr:link "):
                raise PolicyViolation("freeform AI comment")
            try:
                result = json.loads(payload[len("brainlehr:link "):])
            except (TypeError, json.JSONDecodeError) as error:
                raise PolicyViolation("invalid brainlehr link") from error
            result = dict(result) if isinstance(result, Mapping) else result
            if isinstance(result, dict):
                result.setdefault("kind", "brainlehr:link")
            normalized = validate_ai_result(result, registry)
            if normalized.get("anchor_id") not in accepted:
                raise PolicyViolation("anchor not accepted by manifest")


def validate_manifest(manifest: Mapping[str, object] | None, root: str | Path, *, registry: object) -> dict[str, str]:
    """Validate opt-in manifest; generic (None) flow is deliberately bypassed."""
    if manifest is None:
        return {"status": "bypass"}
    if not isinstance(manifest, Mapping) or set(manifest) != MANIFEST_KEYS:
        raise ValueError("strict AI-edit manifest fields required")
    if manifest["schema"] != SCHEMA or manifest["policy_version"] != POLICY_VERSION:
        raise ValueError("stale AI-edit policy")
    root = Path(root)
    revision = _head(root)
    if manifest["base_revision"] != revision or manifest["revision"] != revision:
        raise ValueError("stale AI-edit revision")
    diff_hash = manifest["staged_diff_sha256"]
    if not isinstance(diff_hash, str) or not _HEX64.fullmatch(diff_hash) or diff_hash != _hash(_diff(root)):
        raise ValueError("stale staged diff")
    owned = _validate_paths(manifest["ai_owned_paths"])
    additions = _added_lines(root)
    expected = {path: [_hash(line) for line in lines] for path, lines in additions.items()}
    if set(owned) != set(_changed_paths(root)) or owned != expected:
        raise ValueError("AI-owned added hashes do not match staged diff")
    accepted = manifest["accepted_anchor_ids"]
    if not isinstance(accepted, list) or accepted != sorted(set(accepted)) or not all(isinstance(item, str) for item in accepted):
        raise ValueError("invalid accepted anchor IDs")
    if getattr(registry, "revision", revision) != revision:
        raise ValueError("stale anchor registry")
    for anchor_id in accepted:
        resolved = registry.resolve([anchor_id], budget=1)
        if resolved.gaps or len(resolved.anchors) != 1:
            raise ValueError("invented anchor ID")
    inventory = manifest["human_comment_inventory_sha256"]
    if not isinstance(inventory, str) or not _HEX64.fullmatch(inventory):
        raise ValueError("invalid human comment inventory")
    remove = {path: hashes for path, hashes in expected.items()}
    current = _comment_inventory(root, revision, paths=_changed_paths(root), remove_hashes=remove, staged=True)
    baseline = _comment_inventory(root, revision, paths=_changed_paths(root))
    if inventory != baseline or current != inventory:
        raise ValueError("human comment inventory changed")
    _check_comments(additions, registry=registry, accepted=set(accepted))
    receipt = {key: manifest[key] for key in sorted(MANIFEST_KEYS)}
    return {"status": "PASS", "receipt_sha256": _hash(_json(receipt).encode("utf-8"))}
