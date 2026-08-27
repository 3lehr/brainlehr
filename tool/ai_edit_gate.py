"""Run the opt-in AI edit manifest gate without touching generic human commits."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from kern.ai_edit_gate import validate_manifest
from kern.anchor_registry import Anchor, AnchorRegistry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.registry.read_text())
    registry = AnchorRegistry.empty(data["revision"])
    for row in data["anchors"]:
        registry = registry.register(Anchor.create(row["anchor_id"], row["revision"], row["contract"], row.get("edges", ())))
    print(json.dumps(validate_manifest(json.loads(args.manifest.read_text()), args.repo, registry=registry), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
