"""Tests fuer knowledge_add/knowledge_update/knowledge_read -- Normschicht-
Felder (norm_rang/gilt_ab/gilt_bis) und Kindknoten bei read.

Zwei Befunde aus echter Nutzung (roh, L-baaa61 / L-4eb2bc):

Befund 1 -- Normschicht unerreichbar. schema.sql traegt norm_rang/gilt_ab/
gilt_bis seit N2, aber knowledge_add/knowledge_update kannten nur
parent_path/title/summary/content/tags/project_id/source -- eine Sitzung
konnte Rang und Gueltigkeit nicht setzen, der Aufruf gelang trotzdem
stillschweigend ohne sie.

Befund 2 -- Astknoten liefert keine Kinder. knowledge_read auf einen Knoten
MIT Kindern gab weder deren Titel noch Summary zurueck -- Zweck und Regeln
stehen in den Kindknoten, "lies /brainlehr" las eine leere Seite.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Frische Test-DB mit dem echten Schema, DB_PATH umgebogen."""
    import sqlite3
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


# --- Befund 1: knowledge_add setzt norm_rang/gilt_ab/gilt_bis ---------------

def test_add_writes_norm_felder(temp_db):
    """ROT VOR GRUEN: vor der Aenderung kannte knowledge_add() kein
    norm_rang/gilt_ab/gilt_bis-Keyword -- der Aufruf haette mit
    TypeError: knowledge_add() got an unexpected keyword argument 'norm_rang'
    abgebrochen."""
    result = kms.knowledge_add(
        "/", "WEG-Beschluss", "Testnorm", source="test",
        norm_rang=3, gilt_ab="2026-08-01", gilt_bis="2026-12-31",
    )
    assert "error" not in result
    read = kms.knowledge_read(result["id"])
    assert read["norm_rang"] == 3
    assert read["gilt_ab"] == "2026-08-01"
    assert read["gilt_bis"] == "2026-12-31"


def test_add_ohne_normangaben_bleibt_null(temp_db):
    """Negativfall: Knoten ohne Normangaben -- norm_rang bleibt NULL, kein
    Fehler, Verhalten unveraendert gegenueber vor dieser Aenderung."""
    result = kms.knowledge_add("/", "Reiner Fakt", "Zusammenfassung", source="test")
    assert "error" not in result
    read = kms.knowledge_read(result["id"])
    assert read["norm_rang"] is None
    assert read["gilt_ab"] is None
    assert read["gilt_bis"] is None


@pytest.mark.parametrize("gilt_ab,gilt_bis,soll_ok", [
    ("2026-08-01", "2026-08-01", True),   # Grenzwert: gleicher Tag erlaubt
    ("2026-08-01", "2026-07-31", False),  # Grenzwert: einen Tag davor abgelehnt
])
def test_add_grenzwerte_gilt_bis_vs_gilt_ab(temp_db, gilt_ab, gilt_bis, soll_ok):
    result = kms.knowledge_add(
        "/", f"Grenzfall {gilt_bis}", "Test", source="test",
        norm_rang=3, gilt_ab=gilt_ab, gilt_bis=gilt_bis,
    )
    if soll_ok:
        assert "error" not in result
    else:
        assert "error" in result
        assert "gilt_bis" in result["error"]


def test_add_gilt_ab_unsinn_wird_abgelehnt(temp_db):
    """Grenzwert: kein ISO-8601 -> sprechender Fehler, kein 500/stiller Erfolg."""
    result = kms.knowledge_add(
        "/", "Unsinnsdatum", "Test", source="test", norm_rang=3, gilt_ab="morgen",
    )
    assert "error" in result
    assert "gilt_ab" in result["error"]


# --- Befund 1b: knowledge_update aendert dieselben Felder --------------------

def test_update_setzt_gilt_bis(temp_db):
    """ROT VOR GRUEN: vor der Aenderung kannte knowledge_update() kein
    gilt_bis-Keyword -- eine Norm war nach dem Anlegen eingefroren."""
    node = kms.knowledge_add("/", "Norm ohne Ende", "Test", source="test",
                              norm_rang=2, gilt_ab="2026-01-01")
    result = kms.knowledge_update(node["id"], gilt_bis="2026-12-31")
    assert "error" not in result
    read = kms.knowledge_read(node["id"])
    assert read["gilt_bis"] == "2026-12-31"


def test_update_lehnt_gilt_bis_vor_bestehendem_gilt_ab_ab(temp_db):
    """Grenzwertpruefung greift auch, wenn nur gilt_bis geaendert wird und
    gilt_ab aus dem Bestand kommt."""
    node = kms.knowledge_add("/", "Norm mit Start", "Test", source="test",
                              norm_rang=2, gilt_ab="2026-08-01")
    result = kms.knowledge_update(node["id"], gilt_bis="2026-01-01")
    assert "error" in result
    read = kms.knowledge_read(node["id"])
    assert read["gilt_bis"] is None  # unveraendert, kein stiller Teilerfolg


# --- Befund 2: knowledge_read liefert Kinder --------------------------------

def test_read_liefert_kinder_mit_titel(temp_db):
    """ROT VOR GRUEN: vor der Aenderung fehlte der "children"-Key komplett --
    ein Astknoten wie /brainlehr lieferte content == "(kein Volltext)" und
    keinen Hinweis auf seine Kinder."""
    ast = kms.knowledge_add("/", "Brainlehr", "Astknoten", source="test")
    kms.knowledge_add(ast["path"], "Regel A", "Erste Regel", source="test")
    kms.knowledge_add(ast["path"], "Regel B", "Zweite Regel", source="test")

    read = kms.knowledge_read(ast["id"])
    titles = {c["title"] for c in read["children"]}
    assert titles == {"Regel A", "Regel B"}
    assert all("summary" in c for c in read["children"])


def test_read_kinderlos_liefert_leere_liste(temp_db):
    node = kms.knowledge_add("/", "Blatt ohne Kinder", "Test", source="test")
    read = kms.knowledge_read(node["id"])
    assert read["children"] == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
