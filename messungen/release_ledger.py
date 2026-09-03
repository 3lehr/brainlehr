#!/usr/bin/env python3
"""Release Ledger fuer BDW-P67 AC1.

Erzeugt eine maschinenlesbare JSON-Datei mit dem Status aller BDW-Gates
aus dem Root-Katalog, inklusive Commit-Hash der letzten Aenderung und
Test-Command fuer reproduzierbare Pruefung.
"""
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

KATALOG = Path("docs/REQUIREMENTS_BRAINLEHR.md")
LEDGER = Path("runs/release_ledger.json")


def git_log_for_line(line_num: int) -> dict:
    """Letzter Commit, der diese Zeile geaendert hat."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%H|%ci|%s", f"-L{line_num},{line_num}:{KATALOG}"],
            capture_output=True, text=True, check=True
        )
        parts = out.stdout.strip().split("|", 2)
        if len(parts) == 3:
            return {"hash": parts[0][:8], "date": parts[1], "subject": parts[2]}
    except Exception:
        pass
    return {"hash": None, "date": None, "subject": None}


def extract_backtick_command(gate_text: str) -> str | None:
    """Erster nachfahrbarer Befehl in Backticks aus der Gate-Spalte."""
    m = re.search(r"`([^`]+)`", gate_text)
    return m.group(1) if m else None


def main() -> None:
    text = KATALOG.read_text(encoding="utf-8")
    lines = text.splitlines()

    ledger = {
        "erzeugt_am": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "quelle": str(KATALOG),
        "gesamt_gates": 0,
        "pass": 0,
        "teilweise": 0,
        "offen": 0,
        "deferred": 0,
        "future": 0,
        "gates": [],
    }

    for i, line in enumerate(lines, 1):
        if not line.startswith("| BDW-"):
            continue

        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 10:
            continue

        bdw_id = parts[1]
        name = parts[2]
        norm = parts[4]
        status = parts[5]
        gate_text = parts[9]

        # Gate-Status klassifizieren
        if "PASS:" in gate_text:
            gate_status = "PASS"
            ledger["pass"] += 1
        elif "TEILWEISE:" in gate_text:
            gate_status = "TEILWEISE"
            ledger["teilweise"] += 1
        elif "DEFERRED" in gate_text or "DEFERRED" in status:
            gate_status = "DEFERRED"
            ledger["deferred"] += 1
        elif "FUTURE" in gate_text:
            gate_status = "FUTURE"
            ledger["future"] += 1
        else:
            gate_status = "NOT RUN"
            ledger["offen"] += 1

        commit_info = git_log_for_line(i)
        test_cmd = extract_backtick_command(gate_text)

        ledger["gates"].append({
            "bdw_id": bdw_id,
            "name": name,
            "norm": norm,
            "decision_status": status,
            "gate_status": gate_status,
            "test_command": test_cmd,
            "last_commit_hash": commit_info["hash"],
            "last_commit_date": commit_info["date"],
            "last_commit_subject": commit_info["subject"],
        })
        ledger["gesamt_gates"] += 1

    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"geschrieben: {LEDGER}")
    print(f"Gesamt: {ledger['gesamt_gates']}, PASS: {ledger['pass']}, "
          f"TEILWEISE: {ledger['teilweise']}, OFFEN: {ledger['offen']}, "
          f"DEFERRED: {ledger['deferred']}, FUTURE: {ledger['future']}")


if __name__ == "__main__":
    main()
