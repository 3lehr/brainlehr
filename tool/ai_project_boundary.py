"""Supported AI-edit boundary: validate receipt before delegating unchanged gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_edit_gate import main as gate_main
from project_boundary import main as boundary_main


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("boundary", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.boundary:
        parser.error("boundary arguments required after --")
    import sys
    old = sys.argv
    try:
        sys.argv = ["ai-edit-gate", "--manifest", args.manifest, "--registry", args.registry]
        if gate_main():
            return 1
        sys.argv = ["project-boundary", *args.boundary]
        return boundary_main()
    finally:
        sys.argv = old


if __name__ == "__main__":
    raise SystemExit(main())
