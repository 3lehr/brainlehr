#!/usr/bin/env python3
"""Run local Joern CPG parse/export; emit only normalized, revision-bound evidence."""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "kern") not in os.sys.path:
    os.sys.path.insert(0, str(ROOT / "kern"))

from analyzer_registry import MAX_FILE_BYTES, TIMEOUT_SECONDS, unavailable_record
from evidence_adapters import joern_dot_payload, normalize_record

try:
    import resource
except ImportError:  # pragma: no cover - Windows
    resource = None

DEFAULT_BIN = Path("/Volumes/daten/brainlehr-tool-cache/joern/install/joern-cli/bin/joern-parse")
SHIM_DIR = "/Volumes/daten/brainlehr-tool-cache/joern/bin"
SANDBOX_EXEC = Path("/usr/bin/sandbox-exec")
SANDBOX_PROFILE = "(version 1) (allow default) (deny network*)"
# Measured C fixture RSS: 201,523,200 B.  1 GiB is a configurable five-fold cap.
RSS_LIMIT_BYTES = int(os.environ.get("BRAINLEHR_JOERN_RSS_LIMIT_BYTES", 1024 * 1024 * 1024))


def _joern_limits() -> None:
    """Limit CPU and output; JVM virtual-address size is host-dependent."""
    if resource is None:  # pragma: no cover - Windows
        return
    for limit, values in ((resource.RLIMIT_CPU, (TIMEOUT_SECONDS, TIMEOUT_SECONDS + 1)),
                          (resource.RLIMIT_FSIZE, (MAX_FILE_BYTES, MAX_FILE_BYTES))):
        try:
            resource.setrlimit(limit, values)
        except (OSError, ValueError):
            pass


def _group_rss_bytes(pgid: int) -> int | None:
    """Best-effort recursive process-group RSS on macOS; never trusts tool output."""
    result = subprocess.run(["ps", "-o", "rss=", "-g", str(pgid)], text=True,
                            capture_output=True, timeout=1, check=False)
    values = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if result.returncode or not values or any(not value.isdigit() for value in values):
        return None
    return sum(int(value) * 1024 for value in values)


def _run(command: list[str], *, env: dict[str, str]) -> None:
    """Enforce timeout and aggregate process-group RSS without capturing raw streams."""
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               env=env, preexec_fn=_joern_limits, start_new_session=True)
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while process.poll() is None:
        rss = _group_rss_bytes(process.pid)
        if rss is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise OSError("Joern process-group RSS is not measurable")
        if rss > RSS_LIMIT_BYTES or time.monotonic() >= deadline:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise subprocess.TimeoutExpired(command, TIMEOUT_SECONDS)
        time.sleep(0.05)
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, command)


def run(source: Path, *, revision: str, language: str = "C") -> dict:
    if not source.is_file() or source.stat().st_size > MAX_FILE_BYTES:
        return unavailable_record("joern", revision, "Joern input missing or exceeds byte limit")
    parser = Path(os.environ.get("BRAINLEHR_JOERN_BIN", str(DEFAULT_BIN)))
    exporter = parser.with_name("joern-export")
    if not parser.is_file() or not exporter.is_file():
        return unavailable_record("joern", revision, "Joern local distribution unavailable")
    if not SANDBOX_EXEC.is_file():
        return unavailable_record("joern", revision, "macOS network sandbox unavailable")
    env = {"PATH": SHIM_DIR + os.pathsep + os.environ.get("PATH", ""), "LANG": "C", "LC_ALL": "C"}
    try:
        with tempfile.TemporaryDirectory(prefix="brainlehr-joern-", dir="/Volumes/daten/brainlehr-tool-cache/joern") as work:
            root = Path(work)
            cpg, exported = root / "fixture.cpg.bin", root / "dot"
            prefix = [str(SANDBOX_EXEC), "-p", SANDBOX_PROFILE]
            _run([*prefix, str(parser), "--language", language, "--output", str(cpg), str(source)], env=env)
            _run([*prefix, str(exporter), str(cpg), "--repr", "cpg", "--format", "dot", "--out", str(exported)], env=env)
            dot = "\n".join(path.read_text(encoding="utf-8") for path in sorted(exported.rglob("*.dot"))
                            if path.is_file())
    except subprocess.CalledProcessError as error:
        return unavailable_record("joern", revision, f"Joern parse/export exited {error.returncode}")
    except subprocess.TimeoutExpired:
        return unavailable_record("joern", revision, "Joern parse/export timed out")
    except OSError:
        return unavailable_record("joern", revision, "Joern parse/export unavailable")
    record = normalize_record("joern", joern_dot_payload(dot, revision=revision,
                                                           source="joern-cpg-local"))
    if not record["nodes"] or not record["edges"]:
        return unavailable_record("joern", revision, "Joern export contains no normalized CPG evidence")
    record["sandbox"] = {"environment": "allowlist", "cpu_seconds": TIMEOUT_SECONDS,
                         "file_bytes": MAX_FILE_BYTES, "rss_limit_bytes": RSS_LIMIT_BYTES,
                         "network": "sandbox-exec deny network"}
    record["coverage_gaps"] = ["sandbox-exec profile permits host filesystem paths required by JVM"]
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--language", default="C")
    args = parser.parse_args()
    print(json.dumps(run(args.source, revision=args.revision, language=args.language), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
