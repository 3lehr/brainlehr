#!/usr/bin/env python3
"""Check explicit CodeQL eligibility; this helper never downloads or scans."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "kern"))
from codeql_policy import eligibility


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accept", action="store_true", help="record that the user explicitly requested eligibility")
    parser.add_argument("--public-osi", action="store_true")
    parser.add_argument("--github-code-security-entitled", action="store_true")
    parser.add_argument("--version", default="")
    args = parser.parse_args()
    print(json.dumps(eligibility(source_is_public_osi=args.public_osi,
                                  github_code_security_entitled=args.github_code_security_entitled,
                                  accepted_by_user=args.accept, version=args.version)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
