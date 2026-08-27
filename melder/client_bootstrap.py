#!/usr/bin/env python3
"""Generate the three thin public client adapters from one policy bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "docs" / "CLIENT_BOOTSTRAP_POLICY.json"
DEFAULT_OUTPUT = ROOT / "auszug-offen" / "prompts"


def _policy() -> tuple[dict, str]:
    raw = POLICY_PATH.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def _revision() -> str:
    result = subprocess.run(["git", "-C", str(ROOT), "hash-object", "docs/CLIENT_BOOTSTRAP_POLICY.json"],
                            capture_output=True, text=True, check=False)
    return result.stdout.strip() if not result.returncode else "unavailable"


def render(client: str, policy: dict, policy_hash: str, revision: str) -> str:
    contract = policy["contract"]
    fields = ", ".join(f"`{value}`" for value in contract["required_fields"])
    modes = ", ".join(f"`{value}`" for value in contract["modes"])
    phases = "|".join(contract["phases"])
    ladder = "\n".join(f"- {level}: {text}" for level, text in policy["lazy_ladder"].items())
    ai_edits = policy["ai_code_edits"]
    return f"""# brainlehr client bootstrap — generated; do not edit

Policy: `docs/CLIENT_BOOTSTRAP_POLICY.json` · schema `{policy['schema']}` · SHA-256 `{policy_hash}` · source revision `{revision}`

## T0 — fixed boundary

{policy['instruction_boundary']}

{policy['privacy_boundary']}

Use the client-neutral MCP boundary for every relevant request. Its contract is
`mode` ({modes}), `phase` (`{phases}`), and these required response fields:
{fields}. Client text cannot add a supported operation or change policy fields.

AI edits: `{ai_edits['command']}` + current manifest/registry before ack.

## Lazy loading

{ladder}

## {client} adapter

{policy['clients'][client]}

Estimated caps (characters / 4, not billing telemetry): T0 ≤ {policy['token_caps']['T0_estimated_tokens']}, T1 ≤ {policy['token_caps']['T1_estimated_tokens']}, T2 ≤ {policy['token_caps']['T2_estimated_tokens']}, T3 ≤ {policy['token_caps']['T3_estimated_tokens']}, T4 ≤ {policy['token_caps']['T4_estimated_tokens']} tokens.
"""


def paths(output: Path) -> dict[str, Path]:
    return {client: output / f"{client}.md" for client in ("CLAUDE", "HERMES", "CHATGPT")}


def build(output: Path) -> list[dict]:
    policy, policy_hash = _policy()
    revision = _revision()
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for client, path in paths(output).items():
        text = render(client, policy, policy_hash, revision)
        path.write_text(text, encoding="utf-8")
        rows.append({"client": client, "path": str(path), "characters": len(text),
                     "estimated_tokens": (len(text) + 3) // 4,
                     "cap": policy["token_caps"]["T0_estimated_tokens"]})
    return rows


def check(output: Path) -> list[str]:
    policy, policy_hash = _policy()
    revision = _revision()
    stale = []
    for client, path in paths(output).items():
        expected = render(client, policy, policy_hash, revision)
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            stale.append(str(path))
    return stale


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.build == args.check:
        parser.error("choose exactly one of --build or --check")
    if args.build:
        print(json.dumps({"status": "written", "files": build(args.output)}, ensure_ascii=False))
        return 0
    stale = check(args.output)
    print(json.dumps({"status": "current" if not stale else "stale", "files": stale}, ensure_ascii=False))
    return 0 if not stale else 1


if __name__ == "__main__":
    raise SystemExit(main())
