"""Resource monitor for the sole V9 score; only critical pressure aborts it."""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from messungen.sealed_retrieval_v7_launcher import RESOURCE_ENV


def sample(pid: int) -> dict[str, int]:
    text = subprocess.run(["memory_pressure"], text=True, capture_output=True, check=True).stdout
    values = {name: int(value) for name, value in re.findall(r"(Pages throttled|Swapouts):\s*(\d+)", text)}
    free = re.search(r"System-wide memory free percentage:\s*(\d+)%", text)
    rss = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], text=True, capture_output=True, check=True).stdout.strip()
    return {"free_pct": int(free.group(1)) if free else 0, "swapouts": values.get("Swapouts", 0),
            "throttled": values.get("Pages throttled", 0), "rss_kb": int(rss or 0)}


def abort_reason(current: dict[str, int], baseline: dict[str, int]) -> str | None:
    if current["free_pct"] < 25:
        return "critical_free_memory"
    if current["swapouts"] > baseline["swapouts"]:
        return "swapout_increase"
    if current["throttled"] > 0:
        return "throttled_pages"
    if current["rss_kb"] > 8 * 1024 * 1024:
        return "rss_over_8gb"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path(__file__).resolve().parents[1] / "tests/fixtures/sealed_code_retrieval_v9.json")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    result = Path(manifest["test_once"]["result"])
    env = {**os.environ, **RESOURCE_ENV, "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
    stdout, stderr, monitor = (result.with_suffix(".stdout"), result.with_suffix(".stderr"), result.with_suffix(".monitor.jsonl"))
    with stdout.open("w") as out, stderr.open("w") as err, monitor.open("w") as trace:
        child = subprocess.Popen([manifest["runtime"]["python"], "-m", "messungen.sealed_retrieval_v8_score", "--manifest", str(args.manifest)], env=env, stdout=out, stderr=err)
        baseline, reason = sample(child.pid), None
        while child.poll() is None:
            current = sample(child.pid)
            trace.write(json.dumps(current, sort_keys=True) + "\n"); trace.flush()
            if reason := abort_reason(current, baseline):
                child.send_signal(signal.SIGTERM)
                break
            time.sleep(2)
        returncode = child.wait()
    print(json.dumps({"status": returncode, "abort": reason}, sort_keys=True))
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
