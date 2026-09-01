"""Small cross-process leases for Git worktrees (P92)."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class LeaseError(RuntimeError):
    pass


class LeaseCollision(LeaseError):
    pass


class LeaseConflict(LeaseError):
    pass


@dataclass(frozen=True)
class Lease:
    owner: str
    task: str
    worktree: str
    branch: str
    tree_hash: str
    expiry: float


def _confined(root: Path, path: Path) -> Path:
    root, path = root.resolve(), path.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("lease path escapes repository") from exc
    return path


def _read(path: Path) -> Lease:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Lease(**data)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise LeaseError(f"invalid lease: {path}") from exc


def _write_atomic(path: Path, lease: Lease) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(asdict(lease), stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


@contextmanager
def _lease_lock(path: Path):
    """Serialize replace/recovery with an adjacent, stdlib-only lock file."""
    lock = path.with_suffix(path.suffix + ".lock")
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise LeaseCollision("lease operation already in progress") from exc
    try:
        os.write(fd, str(os.getpid()).encode("ascii"))
        os.fsync(fd)
        yield
    finally:
        os.close(fd)
        lock.unlink(missing_ok=True)


class WorktreeLeaseStore:
    def __init__(self, root: str | Path, directory: str | Path = ".worktree-leases"):
        self.root = Path(root).resolve()
        self.directory = _confined(self.root, self.root / directory)

    def path(self, worktree: str | Path) -> Path:
        name = Path(worktree).name
        if not name or name in {".", ".."} or Path(worktree).name != str(worktree):
            raise ValueError("worktree lease key must be a single path component")
        return _confined(self.directory, self.directory / f"{name}.json")

    def acquire(self, *, owner: str, task: str, worktree: str, branch: str,
                tree_hash: str, expiry: float, now: float | None = None) -> Lease:
        if any(not isinstance(value, str) or not value or len(value) > 160 or "\n" in value
               for value in (owner, task, worktree, branch, tree_hash)):
            raise ValueError("lease fields must be bounded one-line identifiers")
        lease = Lease(owner, task, worktree, branch, tree_hash, float(expiry))
        path = self.path(worktree)
        path.parent.mkdir(parents=True, exist_ok=True)
        with _lease_lock(path):
            if path.exists():
                raise LeaseCollision(f"worktree already leased: {worktree}")
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    json.dump(asdict(lease), stream, sort_keys=True, separators=(",", ":"))
                    stream.write("\n")
                    stream.flush()
                    os.fsync(stream.fileno())
            except BaseException:
                path.unlink(missing_ok=True)
                raise
        return lease

    def renew(self, worktree: str, *, owner: str, expiry: float,
              tree_hash: str | None = None, now: float | None = None) -> Lease:
        path = self.path(worktree)
        with _lease_lock(path):
            current = _read(path)
            if current.owner != owner:
                raise LeaseConflict("lease owner mismatch")
            if (now if now is not None else time.time()) >= current.expiry:
                raise LeaseConflict("lease expired")
            updated = Lease(current.owner, current.task, current.worktree, current.branch,
                            tree_hash if tree_hash is not None else current.tree_hash, float(expiry))
            _write_atomic(path, updated)
        return updated

    def release(self, worktree: str, *, owner: str) -> None:
        path = self.path(worktree)
        with _lease_lock(path):
            current = _read(path)
            if current.owner != owner:
                raise LeaseConflict("lease owner mismatch")
            path.unlink()

    def audit(self, *, now: float | None = None, recover: bool = False) -> list[dict[str, Any]]:
        clock = now if now is not None else time.time()
        self.directory.mkdir(parents=True, exist_ok=True)
        result = []
        for path in sorted(self.directory.glob("*.json")):
            try:
                # A hard process exit can leave the tiny operation lock.  It is
                # recoverable only when the lease itself is already expired.
                lock = path.with_suffix(path.suffix + ".lock")
                if recover and lock.exists():
                    locked = _read(path)
                    if locked.expiry <= clock:
                        lock.unlink(missing_ok=True)
                with _lease_lock(path):
                    lease = _read(path)
                    stale = lease.expiry <= clock
                    record = {"worktree": lease.worktree, "owner": lease.owner,
                              "expiry": lease.expiry, "stale": stale}
                    if stale and recover:
                        path.unlink(missing_ok=True)
                        record["recovered"] = True
                    else:
                        record["recovered"] = False
            except LeaseCollision:
                record = {"lease_key": path.name, "stale": False, "recovered": False,
                          "gap": "lease_operation_in_progress"}
            except LeaseError as exc:
                record = {"lease_key": path.name, "stale": True, "recovered": False,
                          "gap": "invalid_lease", "error": str(exc)}
            result.append(record)
        return result


def git_worktrees(root: str | Path) -> list[dict[str, str]]:
    raw = subprocess.check_output(["git", "-C", str(root), "worktree", "list", "--porcelain", "-z"])
    records, current = [], {}
    for field in raw.split(b"\0"):
        if not field:
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = field.decode().partition(" ")
        current[key] = value
    if current:
        records.append(current)
    return records


def git_status(root: str | Path) -> list[str]:
    raw = subprocess.check_output(["git", "-C", str(root), "status", "--porcelain=v2", "-z"])
    return [item.decode(errors="replace") for item in raw.split(b"\0") if item]


def witness(lease: Lease, *, verdict: str = "pass", gaps: list[str] | None = None) -> dict[str, Any]:
    """Return metadata accepted by ``kern.project_context.witness_envelope``."""
    import hashlib
    binding = hashlib.sha256(json.dumps(asdict(lease), sort_keys=True).encode()).hexdigest()
    return {"id": f"p92-{binding[:16]}", "requirement_ids": ["P92"], "kind": "lease",
            "tool": "worktree_lease", "tool_version": "1", "revision": lease.tree_hash,
            "config_hash": binding, "artifact_hash": binding, "verdict": verdict,
            "independence_group": "worktree-lease", "lineage_id": binding,
            "freshness": "current", "evidence_rank": "registered_runtime",
            "confidence": 1.0 if verdict == "pass" else 0.0, "gaps": gaps or [],
            "conflict": False, "observed_at": ""}


as_evidence_witness = witness


def witness_envelope(lease: Lease, *, verdict: str = "pass",
                     gaps: list[str] | None = None) -> dict[str, Any]:
    """Build the bounded, non-normative P98 envelope used by project context."""
    from .project_context import witness_envelope as _envelope
    return _envelope(witnesses=[witness(lease, verdict=verdict, gaps=gaps)])
