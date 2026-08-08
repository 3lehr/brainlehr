"""Tests fuer endgueltig_entfernen.py (Auftrag 2026-08-06, Luecke "kein
Loeschweg fuer die KI"). Menschlicher Gegenpart zu knowledge_zurueckziehen:
echtes DELETE, nur von Hand, nicht ueber ein MCP-Werkzeug erreichbar."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import endgueltig_entfernen as ee  # type: ignore  # noqa: E402
import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path):
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, anlass, norm_entscheidung) "
        "VALUES ('n1', '/x', 'shared', 'Titel', 'Summary', 'Inhalt', 0, 'quelle', 'unbekannt', 'keine_norm')"
    )
    conn.commit()
    conn.close()
    return db_path


# ─── e) Der Mensch-Weg: ohne Bestaetigung nichts, mit Bestaetigung weg ─────

def test_e_ohne_bestaetigung_passiert_nichts(temp_db):
    res = ee.delete_node(temp_db, "n1", "irgendwas anderes")
    assert res["status"] == "abgebrochen", res
    conn = sqlite3.connect(str(temp_db))
    assert conn.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE id='n1'").fetchone()[0] == 1
    conn.close()


def test_e_mit_bestaetigung_zeile_weg_und_sicherung_da(temp_db):
    res = ee.delete_node(temp_db, "n1", ee.REQUIRED_CONFIRMATION)
    assert res["status"] == "geloescht", res
    assert Path(res["backup"]).exists(), "Sicherung fehlt"

    conn = sqlite3.connect(str(temp_db))
    assert conn.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE id='n1'").fetchone()[0] == 0
    logged = conn.execute(
        "SELECT COUNT(*) FROM access_log WHERE action='endgueltig_entfernen'"
    ).fetchone()[0]
    conn.close()
    assert logged == 1, "Loeschung fehlt im access_log"


def test_unbekannter_knoten_wird_nicht_stillschweigend_akzeptiert(temp_db):
    res = ee.delete_node(temp_db, "existiert-nicht", ee.REQUIRED_CONFIRMATION)
    assert res["status"] == "abgebrochen", res


# ─── f) Nicht ueber knowledge_mcp_server.py erreichbar ─────────────────────

def test_f_kein_tool_ruft_endgueltig_entfernen():
    for name, spec in kms.TOOLS.items():
        assert "endgueltig" not in name, f"Werkzeug {name} macht endgueltig_entfernen erreichbar"

    # Ein Kommentar/Docstring, der auf das Skript VERWEIST (Abgrenzung
    # erklaeren), ist erlaubt -- ein IMPORT oder AUFRUF waere die eigentliche
    # Luecke. Beides erkennbar an eigener Codezeile, kein Text drumherum.
    server_source = (SHARED_KNOWLEDGE / "knowledge_mcp_server.py").read_text(encoding="utf-8")
    verboten = ("import endgueltig_entfernen", "endgueltig_entfernen.delete_node",
                "endgueltig_entfernen(", "subprocess")
    for muster in verboten:
        assert muster not in server_source, (
            f"knowledge_mcp_server.py enthaelt {muster!r} -- "
            "damit waere der Mensch-Weg ueber das MCP-Werkzeug erreichbar"
        )
