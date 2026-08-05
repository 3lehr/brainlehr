"""Tests fuer die Herkunftspflicht von knowledge_add() (Auftrag 2026-08-05).

225 Knoten mit norm_rang IS NULL (Fakten), davon 38 ganz ohne Herkunft --
man weiss nicht einmal, wo man nachsehen muesste. source ist die Herkunft
des DATENSATZES (aus welcher Datei/welchem Lauf er stammt), kein Belegfeld
fuer die Aussage selbst.

Nur knowledge_add betroffen. knowledge_update aendert einen bestehenden
Knoten, dessen Herkunft schon feststeht -- bewusst nicht angefasst.
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


def test_fehlende_source_legt_keinen_knoten_an(temp_db):
    res = kms.knowledge_add("/", "Ohne Herkunft", "Zusammenfassung")
    assert "error" in res, f"Knoten ohne source wurde angelegt: {res}"
    conn = sqlite3.connect(str(temp_db))
    assert conn.execute(
        "SELECT COUNT(*) FROM knowledge_nodes WHERE title = 'Ohne Herkunft'"
    ).fetchone()[0] == 0, "Knoten wurde trotz Fehler geschrieben"
    conn.close()


def test_nur_leerzeichen_als_source_zaehlt_als_fehlend(temp_db):
    res = kms.knowledge_add("/", "Nur Leerzeichen", "Zusammenfassung", source="   ")
    assert "error" in res, res


def test_fehlertext_nennt_beispiel_im_hier_ueblichen_format(temp_db):
    res = kms.knowledge_add("/", "Ohne Herkunft", "Zusammenfassung")
    assert "erzeugt aus" in res["error"], res
    assert "(Stand" in res["error"], res


def test_mit_source_geht_unveraendert_durch(temp_db):
    """Gegenprobe: die Pflicht darf das normale Schreiben nicht treffen."""
    res = kms.knowledge_add("/", "Mit Herkunft", "Zusammenfassung",
                            source="erzeugt aus /pfad/datei.md (Stand 2026-08-05T23:40:00+02:00)")
    assert res.get("status") == "created", res
