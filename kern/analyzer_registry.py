"""Optional local analyzer registry: explicit commands, timeout and no fallback."""
from __future__ import annotations

import os
import shutil
import subprocess
import hashlib
import tempfile
from pathlib import Path

try:  # POSIX only; unsupported hosts remain an explicit coverage gap.
    import resource
except ImportError:  # pragma: no cover - Windows
    resource = None

from evidence_adapters import unavailable_record


DEFAULTS = {
    "tree_sitter": "/Volumes/daten/brainlehr-tool-cache/node_modules/.bin/tree-sitter",
    "scip": "/Volumes/daten/brainlehr-tool-cache/node_modules/.bin/scip-python",
    "joern": "/Volumes/daten/brainlehr-tool-cache/joern/install/joern-cli/bin/joern-parse",
    "otlp": "otlp-file",
    "semgrep": "semgrep",
}
TIMEOUT_SECONDS = 30
MAX_OUTPUT_BYTES = 4096
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_MEMORY_BYTES = 2 * 1024 * 1024 * 1024
SAFE_ENV = ("PATH", "LANG", "LC_ALL", "SYSTEMROOT", "WINDIR")


def executable(kind: str) -> str | None:
    if kind not in DEFAULTS:
        raise ValueError("unsupported analyzer")
    candidate = os.environ.get("BRAINLEHR_" + kind.upper() + "_BIN", DEFAULTS[kind])
    return candidate if shutil.which(candidate) else None


def _limits() -> None:
    """Child-only POSIX limit; no-op hosts are surfaced to the caller."""
    if resource is None:  # pragma: no cover - platform dependent
        return
    for limit, values in (
        (resource.RLIMIT_CPU, (TIMEOUT_SECONDS, TIMEOUT_SECONDS + 1)),
        (resource.RLIMIT_FSIZE, (MAX_FILE_BYTES, MAX_FILE_BYTES)),
        (resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES)),
    ):
        try:
            resource.setrlimit(limit, values)
        except (OSError, ValueError):
            # Host support differs; the caller retains a visible host gap.
            continue


def _digest(path: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(64 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return {"sha256": digest.hexdigest(), "bytes": size}


def run(kind: str, args: list[str], *, revision: str, timeout: int = TIMEOUT_SECONDS) -> dict:
    """Run an explicitly selected local command; return a gap on outage only."""
    command = executable(kind)
    if command is None:
        return unavailable_record(kind, revision, f"{kind} executable unavailable")
    safe_env = {key: os.environ[key] for key in SAFE_ENV if key in os.environ}
    with tempfile.TemporaryDirectory(prefix="brainlehr-analyzer-") as directory:
        stdout_path, stderr_path = Path(directory) / "stdout", Path(directory) / "stderr"
        try:
            with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
                result = subprocess.run([command, *args], stdout=stdout, stderr=stderr,
                                        timeout=min(max(timeout, 1), TIMEOUT_SECONDS), check=False,
                                        env=safe_env, preexec_fn=_limits if resource is not None else None)
        except subprocess.TimeoutExpired:
            return unavailable_record(kind, revision, f"{kind} timeout")
        output = {"stdout": _digest(stdout_path), "stderr": _digest(stderr_path)}
    if result.returncode:
        return unavailable_record(kind, revision, f"{kind} exited {result.returncode}")
    # Raw tool output can contain source, paths, or credentials.  Keep only a
    # bounded digest and size; artifacts must be supplied separately to an
    # adapter if they are needed for evidence.
    return {"status": "completed", "kind": kind, "revision": revision,
            "command": [command, *args],
            "output": {"stdout_sha256": output["stdout"]["sha256"],
                       "stderr_sha256": output["stderr"]["sha256"],
                       "stdout_bytes": output["stdout"]["bytes"],
                       "stderr_bytes": output["stderr"]["bytes"]},
            "sandbox": {"environment": "allowlist", "cpu_seconds": TIMEOUT_SECONDS,
                        "memory_bytes": MAX_MEMORY_BYTES if resource is not None else None,
                        "file_bytes": MAX_FILE_BYTES if resource is not None else None,
                        "network": "host-not-enforced"},
            "coverage_gaps": ["network isolation is not enforced by this host"]}
