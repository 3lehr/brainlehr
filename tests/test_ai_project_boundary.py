from __future__ import annotations

import sys
import json
from pathlib import Path

import pytest

sys.path[:0] = ["tool"]
import ai_project_boundary as boundary


def test_invalid_gate_never_delegates(monkeypatch):
    called = []
    monkeypatch.setattr(boundary, "gate_main", lambda: 1)
    monkeypatch.setattr(boundary, "boundary_main", lambda: called.append(True) or 0)
    monkeypatch.setattr(sys, "argv", ["gate", "--manifest", "m", "--registry", "r", "--", "--project-root", "."])
    assert boundary.main() == 1
    assert called == []


def test_valid_gate_delegates_once(monkeypatch):
    called = []
    monkeypatch.setattr(boundary, "gate_main", lambda: 0)
    monkeypatch.setattr(boundary, "boundary_main", lambda: called.append(True) or 0)
    monkeypatch.setattr(sys, "argv", ["gate", "--manifest", "m", "--registry", "r", "--", "--project-root", "."])
    assert boundary.main() == 0
    assert called == [True]


def test_generated_client_policy_requires_the_supported_ai_boundary():
    root = Path(__file__).resolve().parents[1]
    policy = json.loads((root / "docs" / "CLIENT_BOOTSTRAP_POLICY.json").read_text())
    assert policy["ai_code_edits"]["command"] == "python3 tool/ai_project_boundary.py"
    assert "manifest" in policy["ai_code_edits"]["requirement"]
