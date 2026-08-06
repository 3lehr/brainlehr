"""Rot-vor-gruen fuer den Befund 2026-08-06: eine bestehende Datenbank ohne
die Spalte anlass liess knowledge_add mit einem rohen SQLite-Fehler
abbrechen (schreibpruefstand/demo/schreibpruefstand.db). Fix: ensure_schema()
holt die Spalte je Verbindung nach (siehe _ensure_anlass_columns), additiv,
mit WAL-Checkpoint + Sicherungskopie davor (Lehre L-218f1e).
"""
from __future__ import annotations

import re
import sqlite3
import sys
import time
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


def _old_schema_without_anlass() -> str:
    """Wie migrate_anlass.py::_selftest() -- echtes schema.sql, anlass-Block
    an beiden Tabellen herausgeschnitten, damit die Alt-DB nicht von Hand
    nachgebaut werden muss und garantiert synchron mit dem echten Schema
    bleibt."""
    schema_sql = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    # abgeleitet_von TEXT.*?\n\); statt eines festen Endes: nicht-gierig bis
    # zur naechsten schliessenden Klammer, damit spaeter additiv angehaengte
    # Spalten (z.B. zurueckgezogen*, Auftrag 2026-08-06 Zuruecknahme) hier
    # automatisch mitentfernt werden, ohne dieses Muster jedes Mal
    # nachzuziehen -- alte DBs vor dem anlass-Feld kannten auch diese nicht.
    old_schema, n1 = re.subn(
        r",\n    -- Anlass \(Auftrag 2026-08-06\).*?anlass TEXT NOT NULL DEFAULT 'unbekannt',\n"
        r"(    -- abgeleitet_von.*?\n)*    abgeleitet_von TEXT.*?\n\);",
        "\n);", schema_sql, count=1, flags=re.DOTALL,
    )
    assert n1 == 1, "Anlass-Block an knowledge_nodes nicht wie erwartet gefunden"
    old_schema, n2 = re.subn(
        r",(\s*-- 1 wenn bereits Regel generiert\n)"
        r"    anlass TEXT NOT NULL DEFAULT 'unbekannt'  -- siehe Kommentar an knowledge_nodes\.anlass\n\);",
        r"\1);", old_schema, count=1,
    )
    assert n2 == 1, "Anlass-Spalte an lessons_learned nicht wie erwartet gefunden"
    # Die beiden anlass-Zusicherungs-Trigger (Auftrag 2026-08-06, DB-Trigger
    # fuer Rohschreibzugriffe) referenzieren NEW.anlass -- ohne die Spalte
    # waere jedes INSERT/UPDATE ein "no such column: NEW.anlass", nicht der
    # hier zu simulierende Alt-Zustand. Mitentfernen, gleiche Regel-Idee wie
    # oben: alte DB kannte weder die Spalte noch den Trigger.
    old_schema, n3 = re.subn(
        r"CREATE TRIGGER IF NOT EXISTS knowledge_nodes_anlass_check_b[iu]\n"
        r"BEFORE (?:INSERT|UPDATE) ON knowledge_nodes\n"
        r"FOR EACH ROW WHEN NEW\.anlass NOT IN \([^)]*\)\nBEGIN\n"
        r"    SELECT RAISE\(ABORT, '[^']*'\);\nEND;\n\n?",
        "", old_schema, flags=re.DOTALL,
    )
    assert n3 == 2, f"anlass-Check-Trigger nicht wie erwartet gefunden (n={n3})"
    return old_schema


@pytest.fixture()
def old_db(tmp_path, monkeypatch):
    db_path = tmp_path / "alt_ohne_anlass.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_old_schema_without_anlass())
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source) "
        "VALUES ('n1', '/x', 'shared', 'Bestandsknoten', 'x', 'x', 0, 'x')"
    )
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description) VALUES ('L-1', 'insight', 'Bestandslehre')"
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def test_rot_vor_fix_alte_db_wirft_rohen_sqlite_fehler(old_db):
    """Beweis, dass die Luecke real ist: OHNE den Nachzug (ensure_schema
    umgangen, Verbindung wie vor dem Fix von Hand aufgebaut) bricht INSERT
    mit dem rohen Fehlertext ab, den ein Betreiber nicht einordnen kann."""
    conn = sqlite3.connect(str(old_db))
    with pytest.raises(sqlite3.OperationalError, match="has no column named anlass"):
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, "
            "content, level, tags, source, created_at, updated_at, norm_rang, gilt_ab, gilt_bis, anlass) "
            "VALUES ('n2','/y',NULL,'shared','t','s','c',0,'[]','src','now','now',NULL,NULL,NULL,'unbekannt')"
        )
    conn.close()


def test_knowledge_add_auf_alter_db_zieht_spalte_automatisch_nach(old_db):
    res = kms.knowledge_add("/", "Neuer Knoten", "Zusammenfassung", source="test")
    assert res.get("status") == "created", res

    conn = sqlite3.connect(str(old_db))
    cols = {row[1] for row in conn.execute("PRAGMA table_info(knowledge_nodes)")}
    assert "anlass" in cols
    row = conn.execute("SELECT anlass FROM knowledge_nodes WHERE id = ?", (res["id"],)).fetchone()
    conn.close()
    assert row == ("unbekannt",), row


def test_lesson_record_auf_alter_db_zieht_lessons_spalte_nach(old_db):
    res = kms.lesson_record("insight", "Neuer Fund auf alter DB")
    assert res.get("status") == "recorded", res
    conn = sqlite3.connect(str(old_db))
    row = conn.execute("SELECT anlass FROM lessons_learned WHERE id = ?", (res["id"],)).fetchone()
    conn.close()
    assert row == ("unbekannt",), row


def test_nachzug_verliert_keine_bestandszeile(old_db):
    """Gegenprobe: Bestandszeile (vor dem Nachzug ohne anlass eingefuegt)
    bleibt nach dem automatischen ALTER TABLE erhalten und bekommt den
    Vorgabewert."""
    conn = sqlite3.connect(str(old_db))
    vorher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()
    assert vorher == 1

    kms.knowledge_add("/", "Ausloeser fuer den Nachzug", "x", source="test")

    conn = sqlite3.connect(str(old_db))
    nachher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    row = conn.execute("SELECT title, anlass FROM knowledge_nodes WHERE id = 'n1'").fetchone()
    conn.close()
    assert nachher == vorher + 1, (vorher, nachher)
    assert row == ("Bestandsknoten", "unbekannt"), row


def test_backup_datei_entsteht_vor_dem_nachzug(old_db):
    kms.knowledge_add("/", "Loest Sicherung aus", "x", source="test")
    backups = list(old_db.parent.glob(f"{old_db.name}.bak-*"))
    assert len(backups) == 1, backups


def test_zweiter_lauf_auf_bereits_migrierter_db_ist_ein_reiner_noop(old_db):
    """Negativfall: vollstaendige DB (Spalte schon da) -> kein weiterer
    Nachzug, kein zweites Backup, Verhalten unveraendert."""
    kms.knowledge_add("/", "Erster Aufruf zieht nach", "x", source="test")
    backups_after_first = list(old_db.parent.glob(f"{old_db.name}.bak-*"))
    assert len(backups_after_first) == 1

    kms.knowledge_add("/", "Zweiter Aufruf auf bereits migrierter DB", "x", source="test")
    backups_after_second = list(old_db.parent.glob(f"{old_db.name}.bak-*"))
    assert len(backups_after_second) == 1, "zweiter Nachzug haette kein weiteres Backup erzeugen duerfen"


def test_kosten_pro_verbindung_bei_bereits_vollstaendiger_db(tmp_path, monkeypatch):
    """Kostenmessung fuer den Normalfall (Spalte vorhanden, wie bei jeder
    schon migrierten DB) -- PRAGMA table_info x2 pro Verbindung, kein Scan."""
    db_path = tmp_path / "vollstaendig.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript((SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)

    n = 200
    start = time.perf_counter()
    for _ in range(n):
        conn = kms.get_db()
        conn.close()
    elapsed_ms = (time.perf_counter() - start) * 1000 / n
    print(f"\nKosten je get_db()-Aufruf (inkl. ensure_schema, Spalte bereits vorhanden): {elapsed_ms:.3f} ms")
    assert elapsed_ms < 20, f"ensure_schema verzoegert jede Verbindung um {elapsed_ms:.3f} ms -- zu teuer"
