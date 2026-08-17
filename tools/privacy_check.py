#!/usr/bin/env python3
"""Prüft die versionierbare Positivliste auf offensichtliche private Artefakte."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAD_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".log", ".dump", ".bak", ".pem", ".key", ".p12", ".pfx", ".p8"}
BAD_NAMES = {".env", "knowledge.db"}
PATTERNS = {
    "absolute-path": re.compile(r"/(?:Users|Volumes)/"),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}"),
    "token": re.compile("(?:gh" + "p_|sk" + "-|AKIA)[A-Za-z0-9_-]{16,}"),
    "key-material": re.compile("-----BEGIN (?:[A-Z ]+" + "KEY)-----"),
    "internal-id": re.compile("(?:L" + "-|A-)[0-9a-f]{6,}"),
    "operator-text": re.compile("betreiber" + "_weisung|operator" + " instruction", re.I),
}


def files():
    listed = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True, text=True, capture_output=True)
    for name in listed.stdout.splitlines():
        yield ROOT / name


def main():
    findings = []
    for path in files():
        relative = path.relative_to(ROOT)
        if path.name in BAD_NAMES or path.suffix.lower() in BAD_SUFFIXES or ".env" in path.name:
            findings.append(("forbidden-file", relative))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(("binary", relative))
            continue
        for category, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append((category, relative))
    for category, path in findings:
        print(f"{category}: {path}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
