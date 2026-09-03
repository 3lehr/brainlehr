"""Tests fuer BDW-P67 Release Ledger.

BDW-P67-AC1: isolierter Testledger, reproduzierbarer Pfad-Hygiene-Befund.
"""
import json
from pathlib import Path

LEDGER = Path(__file__).resolve().parents[1] / "runs" / "release_ledger.json"


def test_ledger_exists_and_is_valid_json():
    assert LEDGER.exists(), f"Release Ledger fehlt: {LEDGER}"
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert "erzeugt_am" in data
    assert "gates" in data
    assert isinstance(data["gates"], list)
    assert len(data["gates"]) > 0


def test_ledger_sums_match():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    total = data["gesamt_gates"]
    counted = data["pass"] + data["teilweise"] + data["offen"] + data["deferred"] + data["future"]
    assert counted == total, f"Summe stimmt nicht: {counted} != {total}"


def test_pass_gates_have_test_command():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    pass_gates = [g for g in data["gates"] if g["gate_status"] == "PASS"]
    missing = [g["bdw_id"] for g in pass_gates if not g["test_command"]]
    assert not missing, f"PASS-Gates ohne Test-Command: {missing}"


def test_pass_gates_have_commit_hash():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    pass_gates = [g for g in data["gates"] if g["gate_status"] == "PASS"]
    missing = [g["bdw_id"] for g in pass_gates if not g["last_commit_hash"]]
    assert not missing, f"PASS-Gates ohne Commit-Hash: {missing}"


def test_teilweise_gates_are_documented():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    teilweise = [g for g in data["gates"] if g["gate_status"] == "TEILWEISE"]
    for g in teilweise:
        assert g["test_command"] or "offen" in (g.get("last_commit_subject") or "").lower(), \
            f"TEILWEISE-Gate {g['bdw_id']} ohne Hinweis was offen ist"
