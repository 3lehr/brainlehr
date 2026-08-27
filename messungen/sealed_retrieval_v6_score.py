"""P103-v6 score entry point: validate seal before one claimed execution."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from messungen.sealed_retrieval_v4_score import ROOT, preflight
from messungen.sealed_retrieval_v5_score import score as _score


def ready(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate module/seal/model inputs without lock creation or encode."""
    if manifest.get("schema") != 6:
        raise RuntimeError("P103-v6 manifest schema required")
    for key in ("runner", "source_views", "collector", "scorer", "launcher"):
        item = manifest.get(key, {})
        path = ROOT / item.get("path", "")
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item.get("sha256"):
            raise RuntimeError(f"sealed {key} hash mismatch")
    corpus = ROOT / manifest["corpus"]["path"]
    if hashlib.sha256(corpus.read_bytes()).hexdigest() != manifest["corpus"]["sha256"]:
        raise RuntimeError("sealed corpus hash mismatch")
    return preflight(manifest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "tests/fixtures/sealed_code_retrieval_v6.json")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    ready(manifest)
    if args.preflight:
        print("READY_BEFORE_LOCK")
        return 0
    print(json.dumps(_score(manifest), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
