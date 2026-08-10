"""neuer_ast=True legte bisher nur das Kind an, nie den Astknoten selbst.
Befund 2026-08-06: /brainlehr hatte zwei Kinder, aber path='/brainlehr'
existierte in knowledge_nodes nicht -- eine Waise, genau die Klasse, gegen
die die Elternpfad-Pruefung (test_knowledge_add_pfad.py) gebaut wurde.
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


def test_neuer_ast_legt_astknoten_selbst_an(temp_db):
    res = kms.knowledge_add("/brainlehr", "Erster Fund", "Zusammenfassung",
                            neuer_ast=True, source="test")
    assert res.get("status") == "created", res
    conn = sqlite3.connect(str(temp_db))
    count = conn.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE path = '/brainlehr'").fetchone()[0]
    conn.close()
    assert count == 1, f"Astknoten /brainlehr wurde nicht angelegt (Waise), count={count}"


def test_neuer_ast_zweiter_aufruf_erzeugt_keinen_zweiten_ast(temp_db):
    kms.knowledge_add("/brainlehr", "Erster Fund", "Zusammenfassung", neuer_ast=True, source="test")
    res2 = kms.knowledge_add("/brainlehr", "Zweiter Fund", "Zusammenfassung", neuer_ast=True, source="test")
    assert res2.get("status") == "created", res2
    conn = sqlite3.connect(str(temp_db))
    count = conn.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE path = '/brainlehr'").fetchone()[0]
    conn.close()
    assert count == 1, f"zweiter Ast angelegt oder Fehler, count={count}"


def test_neuer_ast_mehrstufig_legt_alle_zwischenstufen_an(temp_db):
    res = kms.knowledge_add("/a/b/c", "Tiefer Fund", "Zusammenfassung", neuer_ast=True, source="test")
    assert res.get("status") == "created", res
    conn = sqlite3.connect(str(temp_db))
    paths = {r[0] for r in conn.execute("SELECT path FROM knowledge_nodes")}
    conn.close()
    assert {"/a", "/a/b", "/a/b/c"} <= paths, paths
