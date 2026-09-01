#!/usr/bin/env python3
"""Run local P42 analyzers, normalize only typed evidence, never write Brainlehr."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path("/Volumes/daten/brainlehr-tool-cache")
PYTHON = Path("/opt/homebrew/bin/python3.14")
NODE = "/usr/local/bin/node" if Path("/usr/local/bin/node").exists() else "node"
TREE_MODULES = CACHE / "python"
SCIP = CACHE / "node_modules/.bin/scip-python"
SEMGREP = "/opt/homebrew/bin/semgrep"
SCIP_PROTO = CACHE / "node_modules/@scip-code/scip"
BUF_PROTO = CACHE / "node_modules/@bufbuild/protobuf"

sys.path.insert(0, str(ROOT))
from kern.evidence_adapters import normalize_record, unavailable_record  # noqa: E402


def available() -> bool:
    return all(path.exists() for path in (PYTHON, TREE_MODULES / "tree_sitter",
                                           TREE_MODULES / "tree_sitter_python", SCIP,
                                           Path(SEMGREP), SCIP_PROTO, BUF_PROTO))


def _run(command: list[str], *, timeout: int = 30) -> str:
    env = {key: value for key, value in os.environ.items() if key in {"PATH", "LANG", "LC_ALL"}}
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout,
                            env=env, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"exited {result.returncode}")
    return result.stdout


def _tree_sitter(source: Path, revision: str) -> dict:
    language = {".py": "python", ".js": "javascript"}.get(source.suffix)
    if language is None:
        return unavailable_record("tree_sitter", revision, "unsupported tree-sitter language")
    code = (
        "import json,sys;sys.path.insert(0,sys.argv[1]);"
        "from tree_sitter import Language,Parser;"
        "import tree_sitter_python as py,tree_sitter_javascript as js;"
        "m={'python':py,'javascript':js}[sys.argv[2]];"
        "root=Parser(Language(m.language())).parse(open(sys.argv[3],'rb').read()).root_node;"
        "print(json.dumps({'root':root.type,'children':[n.type for n in root.children]}))"
    )
    parsed = json.loads(_run([str(PYTHON), "-c", code, str(TREE_MODULES), language, str(source)]))
    name = source.relative_to(ROOT).as_posix()
    payload = {"source": f"tree-sitter-{language}", "revision": revision,
               "tool_version": "tree-sitter-0.25.2", "language": language,
               "node": {"name": name},
               "edges": [{"from": name, "to": f"{name}:{node}", "type": "contains"}
                         for node in sorted(set(parsed["children"]))]}
    return normalize_record("tree_sitter", payload)


def _scip(source: Path, revision: str) -> dict:
    relative = source.relative_to(ROOT).as_posix()
    with tempfile.TemporaryDirectory(prefix="brainlehr-scip-", dir=CACHE) as directory:
        index = Path(directory) / "index.scip"
        _run([str(SCIP), "index", "--cwd", str(ROOT), "--target-only", relative,
              "--output", str(index), "--quiet"])
        code = (
            "const fs=require('fs');const {fromBinary}=require(process.argv[1]);"
            "const {IndexSchema}=require(process.argv[2]);const i=fromBinary(IndexSchema,fs.readFileSync(process.argv[3]));"
            "const r=process.argv[4];const d=i.documents[0];"
            "console.log(JSON.stringify({documents:[{relative_path:r,language:'python',symbols:d.symbols.map(s=>({symbol:s.symbol,kind:'definition'}))}],"
            "occurrences:d.occurrences.filter(o=>o.symbol).map(o=>({symbol:o.symbol}))}))"
        )
        parsed = json.loads(_run([NODE, "-e", code, str(BUF_PROTO), str(SCIP_PROTO), str(index), relative]))
    return normalize_record("scip", {"source": "scip-python-0.6.6", "revision": revision,
                                      "tool_version": "0.6.6", **parsed})


def _semgrep(source: Path, revision: str) -> dict:
    relative = source.relative_to(ROOT).as_posix()
    rule = """rules:\n- id: local-import-evidence\n  languages: [python]\n  message: import\n  severity: INFO\n  pattern: import $MODULE\n"""
    with tempfile.TemporaryDirectory(prefix="brainlehr-semgrep-", dir=CACHE) as directory:
        config = Path(directory) / "rule.yaml"
        config.write_text(rule, encoding="utf-8")
        parsed = json.loads(_run([SEMGREP, "scan", "--config", str(config), "--json", relative]))
    results = [{"check_id": item.get("check_id", "unknown"),
                "path": item.get("path", relative)} for item in parsed.get("results", [])]
    version = _run([SEMGREP, "--version"]).strip()
    return normalize_record("semgrep", {"source": "semgrep-local-rule", "revision": revision,
                                         "tool_version": version, "results": results})


def run(kind: str, source: Path, *, revision: str) -> dict:
    """Return a normalized local fragment or an explicit coverage gap."""
    if not available():
        return unavailable_record(kind, revision, "P42 local analyzer dependency unavailable")
    if not source.is_file() or ROOT not in source.resolve().parents:
        return unavailable_record(kind, revision, "P42 source must be a tracked repository file")
    try:
        return {"tree_sitter": _tree_sitter, "scip": _scip, "semgrep": _semgrep}[kind](source, revision)
    except (KeyError, OSError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        return unavailable_record(kind, revision, f"{kind} local run failed: {type(error).__name__}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("tree_sitter", "scip", "semgrep"))
    parser.add_argument("source", type=Path)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.kind, args.source, revision=args.revision), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
