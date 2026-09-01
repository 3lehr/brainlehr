"""CLI entry point for the client-neutral, request-local boundary contract."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import project_context
except ModuleNotFoundError:  # installed wheel keeps core modules in ./kern
    sys.path.insert(0, str(Path(__file__).resolve().parent / "kern"))
    import project_context


def main() -> int:
    parser = argparse.ArgumentParser(description="Print a compact Brainlehr request boundary contract.")
    parser.add_argument("--project-root")
    parser.add_argument("--mode", default="auto")
    parser.add_argument("--phase", default="plan")
    parser.add_argument("--operation")
    parser.add_argument("--ack", metavar="REASON")
    parser.add_argument("--actor")
    parser.add_argument("--ack-signature", metavar="BASE64")
    args = parser.parse_args()
    try:
        if args.ack is not None:
            if not args.project_root:
                raise ValueError("--ack requires --project-root")
            result = project_context.staged_commit_gate(
                args.project_root, acknowledge_reason=args.ack,
                actor=args.actor, signature=args.ack_signature)
        else:
            result = project_context.boundary_contract(
                mode=args.mode, phase=args.phase, operation=args.operation,
                project_path=args.project_root)
            if args.project_root and result["mode"] in {"code", "mixed"}:
                result["commit_gate"] = project_context.staged_commit_gate(args.project_root)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    except ValueError as error:
        print(f"project-boundary: {error}", file=sys.stderr)
        return 2
    return 1 if result.get("status") == "blocked" else 0
