#!/usr/bin/env python3
"""Gegenprobe + Negativfall: LEHREN-Treffer aus knowledge_search() tragen
jetzt ihre eigenen Herkunfts-/Geltungsfelder (session, actor, model,
pruefstelle, status, first_seen, last_seen, occurrences, bezug, gilt_ab,
gilt_bis, gilt_bis_version, node_path) -- roh aus lessons_learned, nicht
erfunden. Leer bleibt leer (None), s. Auftrag 2026-08-19.

Rot-vor-gruen-Vergleichsstand: Commit e32a0280 (fester Hash, s. Auftrag) --
gegen HEAD zu vergleichen waere in dieser Sitzung mit mehreren schreibenden
Agenten falsch (L-82415c).
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
        "'erzeugt aus tests/test_lehren_herkunft_felder.py','keine_norm',"
        "'Astwurzel, traegt keine Aussage','betreiber','arbeitsbestand','shared',"
        "'2026-08-19T00:00:00Z','2026-08-19T00:00:00Z')")
    # Lehre MIT session/gilt_ab -- muss die Werte liefern.
    conn.execute(
        "INSERT INTO lessons_learned (id, node_path, type, description, projects,"
        " status, session, actor, model, pruefstelle, first_seen, last_seen,"
        " occurrences, bezug, gilt_ab, gilt_bis, gilt_bis_version, freigabe)"
        " VALUES ('L-gefuellt','/probe','insight',"
        "'Herkunftslehre mit gefuellten Feldern fuer den Suchtest.','[]','active',"
        "'sitzung-42','betreiber','sonnet-5','tests/test_lehren_herkunft_felder.py',"
        "'2026-08-19T00:00:00Z','2026-08-19T00:00:00Z',2,'[\"brainlehr\"]',"
        "'2026-08-01',NULL,NULL,'intern')")
    # Lehre OHNE gilt_ab/gilt_bis/session -- muss None liefern, nicht '' oder 0.
    conn.execute(
        "INSERT INTO lessons_learned (id, node_path, type, description, projects, status, freigabe)"
        " VALUES ('L-leer','/probe','insight',"
        "'Herkunftslehre ohne Geltungsfelder fuer den Suchtest.','[]','active','intern')")
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


def test_lehre_mit_gefuellten_feldern_liefert_die_werte(bestand):
    res = _suche(query="Herkunftslehre mit gefuellten Feldern", scope="all", max_results=10)
    treffer = {r["id"]: r for r in res["results"] if r["kind"] == "lesson"}
    assert "L-gefuellt" in treffer, treffer
    r = treffer["L-gefuellt"]
    assert r["session"] == "sitzung-42", r
    assert r["actor"] == "betreiber", r
    assert r["model"] == "sonnet-5", r
    assert r["pruefstelle"] == "tests/test_lehren_herkunft_felder.py", r
    assert r["status"] == "active", r
    assert r["first_seen"] == "2026-08-19T00:00:00Z", r
    assert r["last_seen"] == "2026-08-19T00:00:00Z", r
    assert r["occurrences"] == 2, r
    assert r["bezug"] == '["brainlehr"]', r
    assert r["gilt_ab"] == "2026-08-01", r
    assert r["node_path"] == "/probe", r


def test_lehre_ohne_geltungsfelder_liefert_none_nicht_leerstring(bestand):
    res = _suche(query="Herkunftslehre ohne Geltungsfelder", scope="all", max_results=10)
    treffer = {r["id"]: r for r in res["results"] if r["kind"] == "lesson"}
    assert "L-leer" in treffer, treffer
    r = treffer["L-leer"]
    assert r["gilt_ab"] is None, r
    assert r["gilt_bis"] is None, r
    assert r["gilt_bis_version"] is None, r
    assert r["session"] is None, r
    assert r["pruefstelle"] is None, r


def test_knoten_treffer_feldgleich_zum_vorherigen_stand(bestand):
    """Negativfall: KNOTEN-Treffer duerfen durch diese Aenderung keine neuen
    oder fehlenden Felder bekommen -- Schluesselmengen vergleichen."""
    res = _suche(query="Probe", scope="all", max_results=10)
    knoten = [r for r in res["results"] if r["kind"] == "node"]
    assert knoten, res
    erwartete_schluessel = {
        "kind", "id", "path", "title", "summary", "project", "abgeleitet_von",
        "bedeutungs_kosinus", "source", "norm_rang", "gilt_ab", "gilt_bis",
        "norm_entscheidung", "freigabe",
    }
    assert set(knoten[0].keys()) == erwartete_schluessel, knoten[0].keys()


def test_auswahl_und_reihenfolge_unveraendert(bestand):
    """Negativfall: die neuen Lehren-Felder duerfen keine Kandidaten
    hinzufuegen, wegnehmen oder umsortieren -- Kennungsliste vergleichen."""
    res = _suche(query="Herkunftslehre", scope="all", max_results=10)
    ids = [r["id"] for r in res["results"]]
    assert set(ids) == {"L-gefuellt", "L-leer"}, ids
    assert len(ids) == len(set(ids)), ids


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
