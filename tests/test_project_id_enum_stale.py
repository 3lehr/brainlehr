"""Belegt Abweichung Doku vs. Verhalten bei project_id (Lehre L-e107ee, 2026-08-07).

Werkzeugbeschreibung von knowledge_add nannte project_id als geschlossenes
Enum "shared|begod|aka|bebetter". Der Server validiert das nicht -- Bestand
(gemessen 2026-08-07) enthaelt bereits 'stadtwerke' und 'openlehr' ausserhalb
dieses Enums, neben 25+ Projektverzeichnissen im Verbund. Entscheidung: der
Enum war veraltet, nicht das Verhalten -- project_id ist ein freier
Projekt-Slug. Diese Tests belegen a) dass die Beschreibung das nicht mehr als
geschlossenes Enum behauptet, b) dass beliebige, leere und fehlende
project_id-Werte weiterhin angenommen bzw. korrekt defaulten.
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
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", str(db_path))
    return db_path


def test_tool_description_does_not_claim_closed_enum():
    """ROT VOR GRUEN: Beschreibung nannte "shared|begod|aka|bebetter" als
    abschliessende Werteliste, obwohl der Server jeden String annimmt."""
    desc = kms.TOOLS["knowledge_add"]["inputSchema"]["properties"]["project_id"]["description"]
    assert "shared|begod|aka|bebetter" not in desc, (
        "Beschreibung behauptet noch ein geschlossenes Enum, das der Server nicht durchsetzt"
    )


def test_project_filter_description_does_not_claim_closed_enum():
    desc = kms.TOOLS["knowledge_browse"]["inputSchema"]["properties"]["project_filter"]["description"]
    assert "shared|begod|aka|bebetter" not in desc


def test_arbitrary_project_id_is_accepted(temp_db):
    """Negativfall Richtung 'zulaessig bleibt zulaessig': ein Projekt ausserhalb
    des alten 4-Werte-Enums (wie im echten Bestand 'stadtwerke', 'openlehr')
    wird weiterhin angenommen."""
    result = kms.knowledge_add(
        parent_path="/", title="t", summary="s", project_id="stadtwerke",
        source="test", neuer_ast=True,
    )
    assert "error" not in result
    conn = sqlite3.connect(str(temp_db))
    row = conn.execute("SELECT project_id FROM knowledge_nodes WHERE title='t'").fetchone()
    conn.close()
    assert row[0] == "stadtwerke"


def test_empty_project_id_is_accepted_as_literal_value(temp_db):
    """Grenzfall: leerer String wird nicht abgelehnt und nicht stillschweigend
    durch den Default ersetzt -- er ist ein bewusst uebergebener Wert."""
    result = kms.knowledge_add(
        parent_path="/", title="t2", summary="s", project_id="",
        source="test", neuer_ast=True,
    )
    assert "error" not in result
    conn = sqlite3.connect(str(temp_db))
    row = conn.execute("SELECT project_id FROM knowledge_nodes WHERE title='t2'").fetchone()
    conn.close()
    assert row[0] == ""


def test_missing_project_id_defaults_to_shared(temp_db):
    """Grenzfall: project_id ganz weggelassen -> Default 'shared' greift."""
    result = kms.knowledge_add(
        parent_path="/", title="t3", summary="s", source="test", neuer_ast=True,
    )
    assert "error" not in result
    conn = sqlite3.connect(str(temp_db))
    row = conn.execute("SELECT project_id FROM knowledge_nodes WHERE title='t3'").fetchone()
    conn.close()
    assert row[0] == "shared"
