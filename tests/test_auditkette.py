"""Tests fuer die Auditkette ueber access_log (Auftrag 2026-08-06).

Rot-vor-gruen-Beleg fuer knowledge_mcp_server.py::log_access() (schreibt
zeilen_hash/ketten_hash, siehe Spaltenkommentar an access_log in schema.sql)
und knowledge_lint.py::find_broken_chain() (rein lesende Pruefung, Kategorie
12). NIE gegen die echte knowledge.db -- immer frische Temp-DB aus schema.sql.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402
import knowledge_lint as lint  # type: ignore  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Frische Test-DB mit dem echten Schema, DB_PATH auf beiden Modulen
    umgebogen -- log_access() schreibt ueber kms.get_db(), find_broken_chain()
    liest read-only ueber lint.get_ro_conn()."""
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _log3(n: int = 3) -> None:
    conn = kms.get_db()
    for i in range(n):
        kms.log_access(conn, f"/x/{i}", "read", query=f"q{i}")
    conn.close()


def _lint(db_path: Path) -> dict:
    conn = lint.get_ro_conn(db_path)
    try:
        return lint.find_broken_chain(conn)
    finally:
        conn.close()


def test_chain_heil_after_writes(temp_db):
    _log3(3)
    result = _lint(temp_db)
    assert result["heil"] is True
    assert result["erster_bruch"] is None
    assert result["geprueft_zeilen"] == 3
    assert result["ungedeckter_zeitraum_zeilen"] == 0


def test_tamper_in_middle_detected_exactly(temp_db):
    """Rot-vor-gruen: vor der Manipulation heil, danach genau die
    manipulierte Zeile als erster Bruch gemeldet -- gegen den heutigen
    Stand (vor Tamper) ist nichts zu sehen, das belegt beides."""
    _log3(3)
    before = _lint(temp_db)
    assert before["heil"] is True

    conn = sqlite3.connect(str(temp_db))
    ids = [r[0] for r in conn.execute("SELECT id FROM access_log ORDER BY id")]
    middle_id = ids[1]
    # Direktes SQL, am log_access()-Weg vorbei -- simuliert nachtraegliche
    # Manipulation. Nur das Feld aendern, den gespeicherten ketten_hash NICHT
    # neu rechnen (genau das macht eine Manipulation sichtbar).
    conn.execute("UPDATE access_log SET query = 'manipuliert' WHERE id = ?", (middle_id,))
    conn.commit()
    conn.close()

    after = _lint(temp_db)
    assert after["heil"] is False
    assert after["erster_bruch"]["id"] == middle_id
    # Zeilen VOR der Manipulation bleiben unauffaellig -- geprueft_zeilen
    # zaehlt nur bis zum ersten Bruch (bricht dort ab), erster_bruch zeigt
    # exakt die manipulierte, nicht eine der beiden Nachbarzeilen.
    assert after["geprueft_zeilen"] == 2


def test_append_correctly_chained_row_stays_heil(temp_db):
    """Gegenprobe 1/2: eine am Ende korrekt angehaengte Zeile bricht nichts."""
    _log3(3)
    _log3(n=1)  # eine weitere, korrekt ueber log_access() angehaengte Zeile
    result = _lint(temp_db)
    assert result["heil"] is True
    assert result["geprueft_zeilen"] == 4


def test_append_incorrectly_chained_row_breaks_at_end(temp_db):
    """Gegenprobe 2/2: eine am Ende FALSCH verkettete Zeile wird als Bruch
    an genau dieser (letzten) Stelle erkannt -- eine Pruefung, die nur die
    Mitte sieht, waere hier blind."""
    _log3(3)
    fake_hash = "deadbeef" + "0" * 56
    conn = sqlite3.connect(str(temp_db))
    conn.execute(
        "INSERT INTO access_log (node_path, action, query, timestamp, zeilen_hash, ketten_hash) "
        "VALUES ('/end', 'read', 'falsch', '2026-08-06T00:00:00+01:00', NULL, ?)",
        (fake_hash,),
    )
    conn.commit()
    last_id = conn.execute("SELECT id FROM access_log ORDER BY id DESC LIMIT 1").fetchone()[0]
    conn.close()

    result = _lint(temp_db)
    assert result["heil"] is False
    assert result["erster_bruch"]["id"] == last_id


def test_legacy_rows_without_hash_are_not_a_break(temp_db):
    """Der ungedeckte Zeitraum (Altbestand vor migrate_auditkette.py) darf
    NIE als Bruch erscheinen -- nur getrennt gezaehlt."""
    conn = sqlite3.connect(str(temp_db))
    for i in range(5):
        conn.execute(
            "INSERT INTO access_log (node_path, action, timestamp) VALUES (?, 'read', ?)",
            (f"/legacy/{i}", f"2020-01-0{i+1}T00:00:00+01:00"),
        )
    conn.commit()
    conn.close()

    legacy_only = _lint(temp_db)
    assert legacy_only["heil"] is True
    assert legacy_only["geprueft_zeilen"] == 0
    assert legacy_only["ungedeckter_zeitraum_zeilen"] == 5

    _log3(2)
    mixed = _lint(temp_db)
    assert mixed["heil"] is True
    assert mixed["geprueft_zeilen"] == 2
    assert mixed["ungedeckter_zeitraum_zeilen"] == 5


def test_zeilen_hash_null_for_read_and_present_for_write(temp_db):
    """browse/read/search haben nichts geaendert -- zeilen_hash bleibt NULL.
    knowledge_add schreibt einen Knoten -- zeilen_hash ist gesetzt."""
    conn = kms.get_db()
    kms.log_access(conn, "/x", "read", query="nur lesen")
    conn.close()
    row = sqlite3.connect(str(temp_db)).execute(
        "SELECT zeilen_hash FROM access_log WHERE action='read'"
    ).fetchone()
    assert row[0] is None

    kms.knowledge_add(
        parent_path="/", title="Testknoten", summary="s", content="c",
        project_id="shared", source="Test",
    )
    row2 = sqlite3.connect(str(temp_db)).execute(
        "SELECT zeilen_hash FROM access_log WHERE action='add' AND status='completed'"
    ).fetchone()
    assert row2[0] is not None


def test_deletion_leaves_zeilen_hash_null(temp_db):
    """Bei Loeschung ist zeilen_hash NULL -- eigener, gueltiger Zustand,
    kein Fehler (Auftrag)."""
    lesson = kms.lesson_record(type_="insight", description="Wird gleich geloescht.")
    kms.lesson_update(lesson_id=lesson["id"], delete=True)
    row = sqlite3.connect(str(temp_db)).execute(
        "SELECT zeilen_hash FROM access_log WHERE action='lesson_delete'"
    ).fetchone()
    assert row[0] is None


def test_transaction_abort_leaves_neither_write_nor_log(temp_db):
    """Transaktionsgrenze: bricht der Prozess zwischen der Datenaenderung
    und dem log_access()-Aufruf ab (hier simuliert durch Schliessen der
    Verbindung ohne commit), landet WEDER die Datenzeile NOCH der
    Log-Eintrag in der DB -- beide haengen an derselben offenen Transaktion,
    die erst log_access() per conn.commit() abschliesst. Das ist die
    ehrliche Grenze dieses Tests: er beweist die Transaktionszugehoerigkeit
    auf SQL-Ebene (kein Commit vor log_access() => nichts persistiert), er
    stellt keinen echten Prozessabsturz mitten im Python-Aufruf nach."""
    conn = kms.get_db()
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, content, level, tags, source, created_at, updated_at, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
        "VALUES ('crash1', '/crash', '/', 'shared', 'Crash', 's', 'c', 0, '[]', 'Test', '2026-08-06T00:00:00+01:00', '2026-08-06T00:00:00+01:00', 'keine_norm', 'skript:test', 'Testvorrichtung')"
    )
    # Abbruch VOR log_access()/commit -- Verbindung schliessen rollt die
    # offene Transaktion zurueck (Python-sqlite3-Default).
    conn.close()

    check = sqlite3.connect(str(temp_db))
    node = check.execute("SELECT 1 FROM knowledge_nodes WHERE id='crash1'").fetchone()
    log_row = check.execute("SELECT 1 FROM access_log WHERE node_path='/crash'").fetchone()
    check.close()
    assert node is None, "Datenzeile haette bei Abbruch vor commit nicht persistieren duerfen"
    assert log_row is None, "Log-Zeile haette bei Abbruch vor commit nicht persistieren duerfen"

    # Gegenprobe: derselbe Ablauf bis zum Ende (log_access() commitet) --
    # jetzt sind BEIDE da, nie nur eine Haelfte.
    conn2 = kms.get_db()
    conn2.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, content, level, tags, source, created_at, updated_at, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
        "VALUES ('ok1', '/ok', '/', 'shared', 'Ok', 's', 'c', 0, '[]', 'Test', '2026-08-06T00:00:00+01:00', '2026-08-06T00:00:00+01:00', 'keine_norm', 'skript:test', 'Testvorrichtung')"
    )
    kms.log_access(conn2, "/ok", "add", affected_row={"id": "ok1"})
    conn2.close()

    check2 = sqlite3.connect(str(temp_db))
    node2 = check2.execute("SELECT 1 FROM knowledge_nodes WHERE id='ok1'").fetchone()
    log_row2 = check2.execute("SELECT 1 FROM access_log WHERE node_path='/ok'").fetchone()
    check2.close()
    assert node2 is not None
    assert log_row2 is not None
