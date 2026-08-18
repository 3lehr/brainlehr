"""Tests fuer den Gattung-Filter in knowledge_search() (Auftrag S1b).

ANLASS, gemessen 2026-08-18: 4354 von 5115 Knoten tragen
gattung='nachschlagewerk' (germanquad, nasa-llis) -- Material, das nie Ziel
einer Frage ist, sondern nur nachgeschlagen wird. knowledge_search kannte
gattung bislang gar nicht (SELECT ohne diese Spalte) -- der eine Weg, ueber
den Claude/Codex selbst suchen (Werkzeug knowledge_search), lieferte
Nachschlagewerk-Treffer ungefiltert mit. Fuenf Stichproben-Suchen gegen den
echten Bestand zeigten 5 Nachschlagewerk-Treffer unter 28 Knotentreffern
(Belege in der Auftragsantwort, nicht hier -- dieser Test arbeitet auf einer
kleinen tmp-DB, damit er nicht vom Bestandsinhalt abhaengt).

Filter: kern/gattung_filter.SQL_ARBEITSBESTAND_NUR, dieselbe Logik wie in
haken/suchpfad_abruf.py, haken/knowledge_recall_hook.py usw. -- keine zweite
Filterimplementierung.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
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
    conn.executemany(
        """INSERT INTO knowledge_nodes
           (id, path, project_id, title, summary, content, level, source,
            norm_entscheidung, norm_entschieden_von, norm_entschieden_grund, gattung)
           VALUES (?, ?, 'shared', ?, ?, NULL, 0, 'test', 'keine_norm', 'skript:test', 'Testvorrichtung', ?)""",
        [
            # Arbeitsbestand -- MUSS immer gefunden werden (Positivkontrolle).
            ("k-arbeit", "/test/arbeitsbestand-knoten", "Ausweiswesen Rollen",
             "Ausweiswesen Rollen Arbeitsbestand", "arbeitsbestand"),
            # Nachschlagewerk -- soll per Vorgabe NICHT auftauchen.
            ("k-nachschlag", "/test/nachschlagewerk-knoten", "Ausweiswesen Rollen Lexikon",
             "Ausweiswesen Rollen Nachschlagewerk", "nachschlagewerk"),
        ],
    )
    # Grenzfall: gattung NICHT in der Spaltenliste -- die Spaltenvorgabe in
    # schema.sql ('arbeitsbestand') muss greifen, ein Knoten ohne explizit
    # gesetzte Gattung darf nicht stillschweigend verschwinden.
    conn.execute(
        """INSERT INTO knowledge_nodes
           (id, path, project_id, title, summary, content, level, source,
            norm_entscheidung, norm_entschieden_von, norm_entschieden_grund)
           VALUES ('k-unset', '/test/unset-gattung-knoten', 'shared', 'Ausweiswesen Rollen Ungesetzt',
                   'Ausweiswesen Rollen ohne gesetzte Gattung', NULL, 0, 'test', 'keine_norm', 'skript:test', 'Testvorrichtung')"""
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _node_ids(result):
    return [r["id"] for r in result["results"] if r["kind"] == "node"]


def test_vorgabe_blendet_nachschlagewerk_aus(temp_db):
    ergebnis = kms.knowledge_search("Ausweiswesen Rollen")
    ids = _node_ids(ergebnis)
    assert "k-nachschlag" not in ids


def test_positivkontrolle_arbeitsbestand_bleibt_auffindbar(temp_db):
    ergebnis = kms.knowledge_search("Ausweiswesen Rollen")
    ids = _node_ids(ergebnis)
    assert "k-arbeit" in ids


def test_grenzfall_ungesetzte_gattung_zaehlt_als_arbeitsbestand(temp_db):
    ergebnis = kms.knowledge_search("Ausweiswesen Rollen")
    ids = _node_ids(ergebnis)
    assert "k-unset" in ids


def test_ausdrueckliche_anforderung_liefert_nachschlagewerk(temp_db):
    ergebnis = kms.knowledge_search("Ausweiswesen Rollen", nachschlagewerk=True)
    ids = _node_ids(ergebnis)
    assert "k-nachschlag" in ids
    # Und weiterhin auch der Arbeitsbestand -- die Anforderung erweitert,
    # sie ersetzt nicht.
    assert "k-arbeit" in ids
    assert "k-unset" in ids
