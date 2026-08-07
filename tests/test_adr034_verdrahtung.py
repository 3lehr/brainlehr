"""Tests fuer ADR-034 (Verdrahtungspunkte der Bausteine): fuenf Bausteine,
die vorher gebaut aber nie erreichbar waren, werden hier je an genau den
Schreibvorgang angeschlossen, dem sie zugeordnet sind -- kein Sammellauf.

    kettenerklaerung                       -> neues MCP-Werkzeug kettenerklaerung_erklaeren
    ankerverfahren.rueckstand              -> kettenerklaerung_erklaeren(anker=...)
    einschleusung.find_injection_suspects  -> knowledge_add/knowledge_update/lesson_record/lesson_update
    normrang                               -> knowledge_add (norm_rang faellt aus source)
    lesson_recorder.cmd_auto_rules         -> kms._bump_lesson bei Eskalation (occurrences>=3)

Rot-vor-gruen ist hier, mangels Vorher/Nachher-Codestand im selben Lauf,
als Vorher/Nachher-ZUSTAND innerhalb desselben Tests gebaut (gleiches Muster
wie test_kettenerklaerung.py::test_rewrite_then_explanation_...): erst der
Zustand OHNE den Schreibvorgang, der den Baustein ausloest, dann MIT --
nie ein Test, der von Anfang an gruen war.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


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


def _log3(n: int = 3):
    conn = kms.get_db()
    for i in range(n):
        kms.log_access(conn, f"/x/{i}", "read", query=f"q{i}")
    conn.close()


# ─── kettenerklaerung: Werkzeug erreichbar ───────────────────────────────────

def test_kettenerklaerung_erklaeren_ist_als_werkzeug_erreichbar(temp_db):
    """Rot: kettenerklaerung.py existierte, aber TOOLS kannte es nicht -- ein
    Aufrufer konnte den Bruch nicht per Werkzeug erklaeren. Gruen: das
    Werkzeug ist registriert und create_explanation() feuert durch es."""
    assert "kettenerklaerung_erklaeren" in kms.TOOLS

    _log3(2)
    ids = [r[0] for r in sqlite3.connect(str(temp_db)).execute("SELECT id FROM access_log ORDER BY id")]
    bruch_id = ids[0]
    conn = sqlite3.connect(str(temp_db))
    conn.execute("UPDATE access_log SET query = 'umgeschrieben' WHERE id = ?", (bruch_id,))
    conn.commit()
    conn.close()

    # VORHER: kein chain_explanations-Eintrag.
    vorher = sqlite3.connect(str(temp_db)).execute("SELECT COUNT(*) FROM chain_explanations").fetchone()[0]
    assert vorher == 0

    ergebnis = kms.TOOLS["kettenerklaerung_erklaeren"]["handler"](
        {"access_log_id": bruch_id, "grund": "ADR-034-Testfall"}
    )
    assert "error" not in ergebnis, ergebnis

    # NACHHER: genau ein Eintrag, ausgeloest durch den Werkzeugaufruf.
    nachher = sqlite3.connect(str(temp_db)).execute("SELECT COUNT(*) FROM chain_explanations").fetchone()[0]
    assert nachher == 1
