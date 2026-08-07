"""Autouse-Schutz fuer die gesamte Testsuite (ADR-034, Verdrahtungspunkte).

kms.knowledge_add/knowledge_update/lesson_record/lesson_update rufen
kms._check_injection_suspects() auf, die per Vorgabe in
shared-knowledge/injection_suspect_log.jsonl anhaengt (echte Datei im Repo).
Jeder Test, der einen dieser vier Schreibpfade beruehrt -- nicht nur die
neuen ADR-034-Tests --, muss den Pfad umbiegen, sonst leakt ein
Testfund in die echte Datei (Fund 2026-08-07, u.a. aus
test_knowledge_add_source.py, die einen absichtlichen Injection-Text als
Fixture nutzt; von Hand entfernt). Autouse statt Einzel-Fixture, weil der
Fehlerpfad nicht an einer Testdatei haengt, sondern an jedem Test, der einen
dieser vier Schreibpfade beruehrt."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


@pytest.fixture(autouse=True)
def _keine_echten_seiteneffekt_dateien(tmp_path, monkeypatch):
    monkeypatch.setattr(kms, "INJECTION_SUSPECT_LOG", tmp_path / "injection_suspect_log.jsonl")
