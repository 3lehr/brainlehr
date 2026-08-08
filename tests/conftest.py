"""Autouse-Schutz fuer die gesamte Testsuite (ADR-034, Verdrahtungspunkte).

Zwei Bausteine schreiben jetzt LIVE am Schreibvorgang, mit Vorgabe-Pfaden,
die auf echte Dateien im Repo zeigen -- jeder Test, der ueber diese
Schreibpfade laeuft, muss beide umbiegen, nicht nur die neuen ADR-034-Tests:

1. kms.knowledge_add/knowledge_update/lesson_record/lesson_update rufen
   kms._check_injection_suspects() auf, die per Vorgabe in
   shared-knowledge/injection_suspect_log.jsonl anhaengt.
2. kms._bump_lesson() loest ab occurrences>=3 jetzt SOFORT
   lesson_recorder.write_rules_to_instructions() aus (nicht mehr nur der
   manuelle 'auto-rules'-CLI-Lauf) -- dessen PROJECTS-Dict zeigt per Vorgabe
   auf die ECHTEN Repo-Wurzeln (hub/AKA2026/BEBETTER).

Beides ist beim Bau dieses Anschlusses tatsaechlich passiert (Fund
2026-08-07: ein echter Log-Eintrag aus test_knowledge_add_source.py UND
echte Dateien in hub/AKA2026/BEBETTER, alle von Hand entfernt). Autouse
statt Einzel-Fixture, weil der Fehlerpfad nicht an einer einzigen Testdatei
haengt, sondern an jedem Test, der einen dieser beiden Schreibpfade beruehrt."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402
import lesson_recorder  # type: ignore  # noqa: E402


@pytest.fixture(autouse=True)
def _keine_echten_seiteneffekt_dateien(tmp_path, monkeypatch):
    monkeypatch.setattr(kms, "INJECTION_SUSPECT_LOG", tmp_path / "injection_suspect_log.jsonl")
    monkeypatch.setattr(lesson_recorder, "PROJECTS", {"shared": tmp_path / "auto_rule_projects"})


@pytest.fixture(autouse=True)
def _norm_entscheidung_test_default(monkeypatch):
    """norm_entscheidung ist seit Auftrag 2026-08-08 PFLICHT bei
    kms.knowledge_add() (schema.sql-Trigger knowledge_nodes_norm_entscheidung_
    pflicht_bi lehnt 'offen' bei INSERT ab). Die meisten bestehenden Tests in
    diesem Verzeichnis pruefen etwas anderes (anlass, source, Pfad-Logik,
    Embeddings, ...) und kennen dieses Feld nicht -- ohne diesen Default
    wuerden sie alle mit demselben, fuer sie irrelevanten Fehler abbrechen.
    Default nur, wenn der Aufrufer das Keyword GAR NICHT mitgibt (kwargs-
    Check VOR dem Aufruf, nicht Pythons eigener Parameter-Default) -- ein
    explizit gesetzter Wert (auch None, um die Ablehnung selbst zu pruefen)
    bleibt unangetastet. Die echte Durchsetzung inklusive Rot-vor-Gruen-Beleg
    steht in tests/test_norm_entscheidung.py, gegen die per Modul-Kopf VOR
    diesem Fixture-Lauf gesicherte Original-Funktion, nicht gegen diesen
    Wrapper."""
    original = kms.knowledge_add

    def _mit_default(*args, **kwargs):
        kwargs.setdefault("norm_entscheidung", "keine_norm")
        # norm_entschieden_grund (Nachtrag 2026-08-08): dieselbe Testbequemlichkeit
        # wie norm_entscheidung oben -- Pflicht seit dem Nachtrag, fuer diese
        # norm-fernen Tests irrelevant.
        kwargs.setdefault("norm_entschieden_grund", "Testvorrichtung, keine echte Norm-Pruefung")
        return original(*args, **kwargs)

    monkeypatch.setattr(kms, "knowledge_add", _mit_default)
