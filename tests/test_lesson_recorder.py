"""Tests fuer lesson_recorder.py -- Aehnlichkeits-Erkennung + same_as-Eskalation.

Befund vor diesem Fix: die CLI (lesson_recorder.py) verglich Dubletten nur ueber
byte-identische description -- zwei Formulierungen desselben Vorfalls sind nie
zeichengleich, darum stand occurrences bei allen 366 damals aktiven Lessons auf 1
und die Eskalation ab RULE_THRESHOLD=3 (existiert bereits im Code) lief nie an.
find_similar() erkannte zwar Aehnliches (Keyword-Overlap), legte aber trotzdem
immer eine neue Zeile an -- Hinweis ohne Wirkung.

Fix: lesson_recorder.py koppelt sich an die in knowledge_mcp_server.py bereits
kalibrierte Erkennung (kms._find_similar_lesson, Wortmengen-Jaccard mit
Stoppwortfilter, SIMILARITY_THRESHOLD=0.18) statt sie neu zu erfinden. same_as
bleibt der einzige Weg, tatsaechlich zusammenzufuehren -- der Aehnlichkeits-Fund
bleibt ein Hinweis, kein Auto-Merge (falsche Zusammenlegung ist teurer als eine
verpasste, siehe HFACS-Reliabilitaetsbefund im Auftrag).
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import sqlite3
import sys
import types
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import lesson_recorder as lr  # type: ignore  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Frische Test-DB mit dem echten Schema, DB_PATH umgebogen. NIE gegen brainlehr.db.

    PROJECTS ebenfalls umgebogen (ADR-034, Auto-Regel-Anschluss in
    kms._auto_rule_fuer_lesson): ohne das schriebe eine Eskalation in diesem
    Test echte Dateien nach hub/aka/bebetter .github/instructions/ --
    lesson_recorder.write_rules_to_instructions() kennt nur das Modul-Dict
    PROJECTS, kein Parameter dafuer. (conftest.py biegt das inzwischen fuer
    die ganze Suite um; hier zusaetzlich explizit, damit diese Datei
    unabhaengig lesbar bleibt.)"""
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    monkeypatch.setattr(lr, "DB_PATH", db_path)
    monkeypatch.setattr(lr, "PROJECTS", {"shared": tmp_path / "shared_proj"})
    return db_path


def _row(db_path: Path, lesson_id: str) -> dict | None:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM lessons_learned WHERE id = ?", (lesson_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def _all_ids(db_path: Path) -> list[str]:
    conn = sqlite3.connect(str(db_path))
    ids = [r[0] for r in conn.execute("SELECT id FROM lessons_learned").fetchall()]
    conn.close()
    return ids


def _record_args(**kw) -> types.SimpleNamespace:
    defaults = dict(type="antipattern", desc="", cause=None, fix=None, prevent=None,
                     severity="medium", projects="shared", same_as="")
    defaults.update(kw)
    return types.SimpleNamespace(**defaults)


# --- Test 1: gleiche Sache, anders formuliert -> wird erkannt, occurrences steigt

def test_recognized_paraphrase_bumps_via_same_as(temp_db, capsys):
    lr.cmd_record(_record_args(
        desc="Reuse-Waechter reserviert Dateien aller Agenten ueber die TABU-Liste des ersten Spawns."))
    first_id = _all_ids(temp_db)[0]

    # Umformulierte Fassung desselben Vorfalls: Hinweis muss erscheinen.
    lr.cmd_record(_record_args(
        desc="Erneut aufgetreten: derselbe Reuse-Waechter-Konflikt, TABU-Liste blockt wieder alle Agenten."))
    out = capsys.readouterr().out
    assert "Ähnliches Lesson gefunden" in out
    assert first_id in out
    # Ohne same_as bleibt es bei zwei getrennten Zeilen -- kein Auto-Merge.
    assert len(_all_ids(temp_db)) == 2

    # Aufrufer folgt dem Hinweis: same_as erhoeht den Vorgaenger statt einer dritten Zeile.
    lr.cmd_record(_record_args(
        desc="Drittes Mal: wieder derselbe Reuse-Waechter-Konflikt.", same_as=first_id))
    row = _row(temp_db, first_id)
    assert row["occurrences"] == 2
    assert len(_all_ids(temp_db)) == 2


# --- Test 2 (wichtiger): verschiedene Sachen, aehnliche Woerter -> NICHT gemergt

def test_different_topics_similar_words_not_merged(temp_db, capsys):
    lr.cmd_record(_record_args(
        type="insight",
        desc="fahrtenbuch_legacy: Kalender-Export-Mechanismus nutzt MethodChannel de.begod.fahrtenbuch fuer den ICS-Export."))
    lr.cmd_record(_record_args(
        type="insight",
        desc="fahrtenbuch_legacy: Play Console verlangt Google Play Billing Library >=8.0.0, App nutzte noch 7.1.1."))
    out = capsys.readouterr().out
    # Score 0.118 < SIMILARITY_THRESHOLD 0.18 (gemessen) -- kein Hinweis, keine Zusammenlegung.
    assert "Ähnliches Lesson gefunden" not in out
    assert len(_all_ids(temp_db)) == 2


# --- Test 3: same_as rueckwaertskompatibel ------------------------------------

def test_same_as_unknown_id_errors_no_silent_new_entry(temp_db):
    with pytest.raises(SystemExit):
        lr.cmd_record(_record_args(desc="Verweist auf nichts.", same_as="L-nichtvorhanden"))
    assert _all_ids(temp_db) == []


def test_same_as_appends_repetition_text(temp_db):
    lr.cmd_record(_record_args(desc="Basisfehler fuer Text-Anhang-Test."))
    first_id = _all_ids(temp_db)[0]
    lr.cmd_record(_record_args(desc="Wiederholungsmarker-1", same_as=first_id))
    row = _row(temp_db, first_id)
    assert "Wiederholungsmarker-1" in row["description"]
    assert "Basisfehler fuer Text-Anhang-Test." in row["description"]


# --- Test 4: Schwelle erreicht -> Eskalation loest aus, erzeugt Vorschlag ----

def test_threshold_reached_escalates_to_proposal(temp_db, capsys):
    """ADR-034: die Eskalation selbst (kms._bump_lesson, Aufrufpfad hier ueber
    lr.cmd_record) loest jetzt SOFORT kms._auto_rule_fuer_lesson() aus --
    das frueher noetige manuelle 'auto-rules'-CLI ist fuer diesen Kandidaten
    bereits erledigt, bevor er dort ueberhaupt ankommt (auto_rule_generated=1,
    WHERE auto_rule_generated = 0 findet ihn also nicht mehr)."""
    lr.cmd_record(_record_args(desc="Basisfehler fuer Eskalationstest."))
    first_id = _all_ids(temp_db)[0]
    lr.cmd_record(_record_args(desc="Wiederholung Nr. 1.", same_as=first_id))
    lr.cmd_record(_record_args(desc="Wiederholung Nr. 2.", same_as=first_id))
    out = capsys.readouterr().out
    assert "⚡" in out

    row = _row(temp_db, first_id)
    assert row["occurrences"] == 3
    assert row["status"] == "escalated_to_rule"
    assert row["auto_rule_generated"] == 1

    # auto-rules (das alte manuelle CLI) findet keinen Kandidaten mehr -- der
    # Schreibvorgang hat die Regel bereits erzeugt.
    lr.cmd_auto_rules(types.SimpleNamespace(dry_run=True))
    out2 = capsys.readouterr().out
    assert first_id not in out2
    assert "Keine Rule-Kandidaten" in out2
