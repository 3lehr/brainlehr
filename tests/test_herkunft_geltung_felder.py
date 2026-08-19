#!/usr/bin/env python3
"""Gegenprobe + Negativfall zum Auftrag "Herkunfts-/Geltungsfelder in
knowledge_search()": jede Trefferzeile traegt source/norm_rang/gilt_ab/
gilt_bis/norm_entscheidung/freigabe (Knoten) bzw. nur freigabe (Lehren,
weil lessons_learned die anderen fuenf Spalten nicht kennt, schema.sql).

Rot-vor-gruen-Vergleichsstand: Commit 633049ff26bac21438a6b034c5f2fe64d0738c4f
(fester Hash, s. Auftrag) -- gegen HEAD zu vergleichen waere in dieser
Sitzung mit mehreren schreibenden Agenten falsch (L-82415c).
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(WURZEL), str(WURZEL / "kern")]


@pytest.fixture
def bestand(tmp_path, monkeypatch):
    """Eigene Datenbank -- nie die produktive, siehe test_kern_modellneutral.py."""
    db = tmp_path / "pruefbestand.db"
    conn = sqlite3.connect(str(db))
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, title, summary, content,"
        " source, norm_entscheidung, norm_entschieden_grund, norm_entschieden_von,"
        " gattung, project_id, created_at, updated_at)"
        " VALUES ('t0','/probe',NULL,'Probe','Ast fuer Pruefknoten.','',"
        "'erzeugt aus tests/test_herkunft_geltung_felder.py','keine_norm',"
        "'Astwurzel, traegt keine Aussage','betreiber','arbeitsbestand','shared',"
        "'2026-08-19T00:00:00Z','2026-08-19T00:00:00Z')")
    # Knoten MIT norm_rang -- muss die Zahl liefern.
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, title, summary, content,"
        " source, norm_rang, gilt_ab, gilt_bis, norm_entscheidung, norm_entschieden_grund,"
        " norm_entschieden_von, gattung, project_id, created_at, updated_at)"
        " VALUES ('mitrang','/probe/mitrang','/probe','Herkunftsknoten mit Rang',"
        "'Traegt norm_rang und gilt_ab.','Volltext Herkunftsprobe mit Rang.',"
        "'Quellenangabe-Testwert',3,'2026-08-01',NULL,'norm_unbefristet',"
        "'Pruefknoten Gegenprobe MIT Rang','betreiber','arbeitsbestand','shared',"
        "'2026-08-19T00:00:00Z','2026-08-19T00:00:00Z')")
    # Knoten OHNE norm_rang (Fakt) -- muss None liefern, nicht 0/leer.
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, title, summary, content,"
        " source, norm_entscheidung, norm_entschieden_grund, norm_entschieden_von,"
        " gattung, project_id, created_at, updated_at)"
        " VALUES ('ohnerang','/probe/ohnerang','/probe','Herkunftsknoten ohne Rang',"
        "'Traegt keinen norm_rang.','Volltext Herkunftsprobe ohne Rang.',"
        "'Quellenangabe-Testwert','keine_norm','Pruefknoten Gegenprobe OHNE Rang',"
        "'betreiber','arbeitsbestand','shared','2026-08-19T00:00:00Z','2026-08-19T00:00:00Z')")
    conn.commit()
    conn.close()
    monkeypatch.setenv("BEGOD_KNOWLEDGE_DB", str(db))
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9")  # Bedeutungskanal tot, Stichwort genuegt
    for name in ("knowledge_mcp_server",):
        sys.modules.pop(name, None)
    return db


def _suche(**kwargs):
    import knowledge_mcp_server as srv
    return srv.knowledge_search(**kwargs)


def test_knoten_mit_norm_rang_liefert_die_zahl(bestand):
    res = _suche(query="Herkunftsknoten mit Rang", scope="all", max_results=10)
    treffer = {r["id"]: r for r in res["results"] if r["kind"] == "node"}
    assert "mitrang" in treffer, treffer
    r = treffer["mitrang"]
    assert r["norm_rang"] == 3, r
    assert r["gilt_ab"] == "2026-08-01", r
    assert r["source"] == "Quellenangabe-Testwert", r
    assert r["norm_entscheidung"] == "norm_unbefristet", r
    assert r["freigabe"] == "intern", r  # Vorgabewert, s. schema.sql


def test_knoten_ohne_norm_rang_liefert_none_nicht_0_oder_leer(bestand):
    res = _suche(query="Herkunftsknoten ohne Rang", scope="all", max_results=10)
    treffer = {r["id"]: r for r in res["results"] if r["kind"] == "node"}
    assert "ohnerang" in treffer, treffer
    r = treffer["ohnerang"]
    assert r["norm_rang"] is None, r
    assert r["gilt_ab"] is None, r
    assert r["gilt_bis"] is None, r
    assert r["source"] == "Quellenangabe-Testwert", r
    assert r["norm_entscheidung"] == "keine_norm", r


def test_auswahl_und_reihenfolge_unveraendert(bestand):
    """Negativfall: die neuen Felder duerfen keine Kandidaten hinzufuegen,
    wegnehmen oder umsortieren -- Kennungsliste vergleichen, nicht nur die
    Laenge."""
    res = _suche(query="Herkunftsknoten", scope="all", max_results=10)
    ids = [r["id"] for r in res["results"]]
    assert ids == ["mitrang", "ohnerang"] or ids == ["ohnerang", "mitrang"], ids
    assert len(ids) == len(set(ids)) == 2, ids


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
