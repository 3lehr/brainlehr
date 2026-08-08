"""Gegenprobe fuer den Nebenbefund 2026-08-06: drei UPDATE-Stellen in
knowledge_mcp_server.py ziehen updated_at/last_seen NICHT mit -- geprueft und
ABSICHTLICH so belassen (Kommentare an den jeweiligen Stellen im Code).

Leitfrage aus dem Auftrag: bedeutet updated_at 'inhaltlich geaendert' oder
'irgendetwas an der Zeile hat sich bewegt'? konfidenz.py::gerechnete_konfidenz
setzt zwingend Ersteres voraus (Modul-Docstring dort: 'updated_at ist bereits
der Bezugszeitpunkt der letzten Aenderung/Bestaetigung'). Alle drei Stellen
sind Nebenwirkungen (Migrations-Backfill, Lesezugriff, Folge-Update im selben
Aufruf), keine inhaltliche Aenderung/Bestaetigung -- deshalb bleibt updated_at/
last_seen dort unveraendert. Keine dieser drei Stellen wird durch diesen
Auftrag im VERHALTEN geaendert (Punkt b, rot-vor-gruen, entfaellt daher
komplett -- reine Gegenprobe fuer eine bewusste Nichtaenderung, Punkt c).
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402
import konfidenz  # type: ignore  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


# ─── Stelle 1: source-Backfill (_ensure_node_constraint_triggers) ──────────

def test_source_backfill_laesst_updated_at_unveraendert(temp_db):
    """Alte Bestands-DB ohne die Zusicherungs-Trigger nachbauen (die Trigger
    lehnen ein leeres source sonst schon beim INSERT ab): Trigger droppen,
    eine Zeile mit leerem source und einem bekannten, alten updated_at
    einfuegen, dann den Nachzug direkt aufrufen. source wird befuellt,
    updated_at bleibt exakt der alte Wert."""
    alt_updated_at = "2020-01-01T00:00:00+01:00"
    conn = sqlite3.connect(str(temp_db))
    conn.executescript("""
        DROP TRIGGER IF EXISTS knowledge_nodes_source_check_bi;
        DROP TRIGGER IF EXISTS knowledge_nodes_source_check_bu;
        DROP TRIGGER IF EXISTS knowledge_nodes_parent_check_bi;
        DROP TRIGGER IF EXISTS knowledge_nodes_parent_check_bu;
        DROP TRIGGER IF EXISTS knowledge_nodes_anlass_check_bi;
        DROP TRIGGER IF EXISTS knowledge_nodes_anlass_check_bu;
    """)
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, "
        "source, created_at, updated_at, anlass, norm_entscheidung) "
        "VALUES ('n1', '/x', 'shared', 'Titel', 'Summary', 'Inhalt', 0, '', ?, ?, 'unbekannt', 'keine_norm')",
        (alt_updated_at, alt_updated_at),
    )
    conn.commit()
    conn.close()

    conn = sqlite3.connect(str(temp_db))
    kms._ensure_node_constraint_triggers(conn)
    conn.commit()
    row = conn.execute("SELECT source, updated_at FROM knowledge_nodes WHERE id = 'n1'").fetchone()
    conn.close()

    assert row[0] == kms.SOURCE_BACKFILL_PLACEHOLDER, "source haette befuellt werden muessen"
    assert row[1] == alt_updated_at, (
        "updated_at haette beim reinen source-Backfill NICHT mitziehen duerfen", row[1]
    )


# ─── Stelle 2: access_count-Increment (knowledge_read) ─────────────────────

def test_access_count_erhoehung_laesst_updated_at_unveraendert(temp_db):
    node = kms.knowledge_add(
        "/", "Lesehaeufigkeits-Testknoten", "Zusammenfassung",
        content="Inhalt", source="erzeugt aus Test (Stand 2026-08-06)",
    )
    assert node.get("status") == "created", node

    conn = sqlite3.connect(str(temp_db))
    updated_at_vorher = conn.execute(
        "SELECT updated_at FROM knowledge_nodes WHERE id = ?", (node["id"],)
    ).fetchone()[0]
    conn.close()

    for _ in range(5):
        kms.knowledge_read(node["id"])

    conn = sqlite3.connect(str(temp_db))
    row = conn.execute(
        "SELECT updated_at, access_count FROM knowledge_nodes WHERE id = ?", (node["id"],)
    ).fetchone()
    conn.close()

    assert row[1] == 5, f"access_count haette 5x erhoeht werden muessen, ist {row[1]}"
    assert row[0] == updated_at_vorher, (
        "updated_at haette durch reines Lesen NICHT mitziehen duerfen", row[0], updated_at_vorher
    )


# ─── Stelle 3: Eskalations-UPDATE in _bump_lesson ──────────────────────────

def test_eskalation_setzt_last_seen_nicht_erneut(temp_db, monkeypatch):
    """_bump_lesson setzt last_seen bereits im occurrences-UPDATE (auf den
    now_iso()-Wert zum Zeitpunkt DIESES Aufrufs). Das Eskalations-UPDATE
    direkt danach greift last_seen nicht nochmal an -- belegt, indem now_iso()
    zwischen den beiden internen UPDATEs auf einen ANDEREN Wert springen
    wuerde, wenn die Eskalation es setzte, es aber nicht tut."""
    lesson = kms.lesson_record("pattern", "Eskalations-Testlesson", anlass="unbekannt")
    assert lesson["status"] == "recorded", lesson
    lesson_id = lesson["id"]

    conn = sqlite3.connect(str(temp_db))
    conn.execute("UPDATE lessons_learned SET occurrences = 2 WHERE id = ?", (lesson_id,))
    conn.commit()
    conn.close()

    fixed_now = "2030-01-01T12:00:00+01:00"
    monkeypatch.setattr(kms, "now_iso", lambda: fixed_now)

    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    result = kms._bump_lesson(conn, lesson_id, "", "Eskalations-Testlesson")
    conn.close()

    assert result["occurrences"] == 3
    assert result["escalated"] is True, result

    conn = sqlite3.connect(str(temp_db))
    row = conn.execute(
        "SELECT status, last_seen FROM lessons_learned WHERE id = ?", (lesson_id,)
    ).fetchone()
    conn.close()
    assert row[0] == "escalated_to_rule", row
    # last_seen traegt GENAU den now_iso()-Wert aus dem occurrences-Update --
    # kein zweiter, spaeterer Zeitstempel aus dem Eskalations-UPDATE.
    assert row[1] == fixed_now, row


# ─── d) Wirkung auf den Konfidenzverfall: unveraendert ─────────────────────

def test_d_access_count_veraendert_gerechnete_konfidenz_nicht(temp_db):
    alter_zeitpunkt = "2020-01-01T00:00:00+01:00"
    node = kms.knowledge_add(
        "/", "Konfidenz-Testknoten", "Zusammenfassung",
        content="Inhalt", source="erzeugt aus Test (Stand 2026-08-06)",
    )
    assert node.get("status") == "created", node
    conn = sqlite3.connect(str(temp_db))
    conn.execute(
        "UPDATE knowledge_nodes SET updated_at = ?, confidence = 0.8 WHERE id = ?",
        (alter_zeitpunkt, node["id"]),
    )
    conn.commit()
    conn.close()

    def _row():
        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row
        r = conn.execute(
            "SELECT confidence, updated_at, norm_rang, path, source FROM knowledge_nodes WHERE id = ?",
            (node["id"],),
        ).fetchone()
        conn.close()
        return r

    from datetime import datetime, timezone
    jetzt = datetime.now(timezone.utc)

    row_vorher = _row()
    konfidenz_vorher = konfidenz.gerechnete_konfidenz(
        row_vorher["confidence"], row_vorher["updated_at"], row_vorher["norm_rang"],
        row_vorher["path"], row_vorher["source"], jetzt,
    )

    for _ in range(10):
        kms.knowledge_read(node["id"])

    row_nachher = _row()
    assert row_nachher["updated_at"] == alter_zeitpunkt  # Gegenprobe von oben, hier nochmal fuer den Beleg
    konfidenz_nachher = konfidenz.gerechnete_konfidenz(
        row_nachher["confidence"], row_nachher["updated_at"], row_nachher["norm_rang"],
        row_nachher["path"], row_nachher["source"], jetzt,
    )

    print(f"gerechnete Konfidenz vorher: {konfidenz_vorher}")
    print(f"gerechnete Konfidenz nachher (10x gelesen): {konfidenz_nachher}")
    assert konfidenz_vorher == konfidenz_nachher, (
        "10x Lesen (access_count 0->10) haette die gerechnete Konfidenz "
        "NICHT veraendern duerfen", konfidenz_vorher, konfidenz_nachher
    )
