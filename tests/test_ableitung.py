"""Tests fuer abgeleitet_von (Auftrag 2026-08-06, ADR-027 Nachtrag 4, Lehre
L-adfb33). Gemessener Fehler: eine abgeleitete Aussage ("Abwesenheit: Fritz
Mueller (Reha)") schrieb den Namen woertlich in source, weil source Freitext
ist und Freitext nur nennen kann, indem er wiedergibt. Entwurfsvorgabe: dem
Schreiber die Feder nehmen -- ist abgeleitet_von gesetzt, erzeugt das System
den Herkunftstext selbst, aus der Art des Quellknotens (parent_path/
norm_rang/tags), nie aus dessen title/summary/content.
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


def _sql(temp_db, query, params=()):
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    row = conn.execute(query, params).fetchone()
    conn.close()
    return row


# ─── a) ROT VOR GRUEN: der echte Fall ───────────────────────────────────────

def test_a_vorher_source_traegt_den_namen(temp_db):
    """VORHER (ohne abgeleitet_von, wie im gemessenen Befund): der Schreiber
    formuliert source selbst, source traegt den Namen woertlich."""
    quelle = kms.knowledge_add(
        "/", "Abwesenheit: <Vorname Nachname> (Reha)", "Abwesend bis 2026-08-15",
        content="Reha-Aufenthalt, Rueckkehr voraussichtlich 2026-08-15",
        source="erzeugt aus Personalakte (Stand 2026-08-06T10:00:00+0200)",
    )
    assert quelle.get("status") == "created", quelle

    ableitung_vorher = kms.knowledge_add(
        "/", "Hausmeisterei-Hinweis (vorher)", "Abwesenheit <Vorname Nachname> (gueltig bis 2026-08-15)",
        source="Abwesenheit <Vorname Nachname> (gueltig bis 2026-08-15)",
    )
    assert ableitung_vorher.get("status") == "created", ableitung_vorher
    row = _sql(temp_db, "SELECT source FROM knowledge_nodes WHERE id = ?", (ableitung_vorher["id"],))
    # Der Testbestand traegt seit 2026-08-10 einen PLATZHALTER statt eines
    # Namens (dieselbe Regel wie in L-adfb33: ein Beleg braucht die FORM des
    # Datums, nicht seinen INHALT). Der Befund ist unveraendert -- die A-Seite
    # zeigt, WER abwesend ist; nur steht der Name nicht mehr im Repo.
    assert "<Vorname Nachname>" in row["source"], (
        f"Vorher-Fall soll den Namen woertlich zeigen, tut es nicht: {row['source']!r}"
    )


def test_a_nachher_erzeugter_source_enthaelt_weder_namen_noch_diagnose(temp_db):
    """NACHHER: dieselbe Ableitung ueber abgeleitet_von. Der erzeugte
    source-Text enthaelt weder 'Fritz' noch 'Mueller' noch 'Reha'."""
    quelle = kms.knowledge_add(
        "/", "Abwesenheit: <Vorname Nachname> (Reha)", "Abwesend bis 2026-08-15",
        content="Reha-Aufenthalt, Rueckkehr voraussichtlich 2026-08-15",
        source="erzeugt aus Personalakte (Stand 2026-08-06T10:00:00+0200)",
        tags=["personal", "abwesenheit"],
    )
    assert quelle.get("status") == "created", quelle

    ableitung = kms.knowledge_add(
        "/", "Hausmeisterei-Hinweis", "Ein Mitarbeiter ist bis 2026-08-15 abwesend",
        abgeleitet_von=quelle["id"],
    )
    assert ableitung.get("status") == "created", ableitung
    row = _sql(temp_db, "SELECT source, abgeleitet_von FROM knowledge_nodes WHERE id = ?", (ableitung["id"],))
    erzeugte_source = row["source"]
    print("VORHER (Freitext):", "Abwesenheit <Vorname Nachname> (gueltig bis 2026-08-15)")
    print("NACHHER (erzeugt): ", erzeugte_source)
    assert "Fritz" not in erzeugte_source, erzeugte_source
    assert "Mueller" not in erzeugte_source, erzeugte_source
    assert "Reha" not in erzeugte_source, erzeugte_source
    assert row["abgeleitet_von"] == quelle["id"]


# ─── b) Negativfall: abgeleitet_von + eigenes source -> Ablehnung ──────────

def test_b_abgeleitet_von_plus_eigenes_source_wird_abgelehnt(temp_db):
    quelle = kms.knowledge_add(
        "/", "Quellknoten", "Zusammenfassung",
        source="erzeugt aus Datei.md (Stand 2026-08-06T10:00:00+0200)",
    )
    assert quelle.get("status") == "created", quelle

    res = kms.knowledge_add(
        "/", "Ableitung mit eigenem source", "Zusammenfassung",
        source="das habe ich mir selbst ausgedacht",
        abgeleitet_von=quelle["id"],
    )
    assert "error" in res, f"abgeleitet_von + eigenes source haette abgelehnt werden muessen: {res}"

    row = _sql(temp_db, "SELECT COUNT(*) AS n FROM knowledge_nodes WHERE title = 'Ableitung mit eigenem source'")
    assert row["n"] == 0, "trotz Ablehnung wurde etwas geschrieben"


# ─── c) Kennung ins Leere -> Ablehnung mit sprechendem Text ────────────────

def test_c_abgeleitet_von_zeigt_ins_leere(temp_db):
    res = kms.knowledge_add(
        "/", "Ableitung ohne Quelle", "Zusammenfassung",
        abgeleitet_von="existiert-nicht-12345",
    )
    assert "error" in res, res
    assert "existiert-nicht-12345" in res["error"], res
    assert "keinen vorhandenen Knoten" in res["error"], res

    row = _sql(temp_db, "SELECT COUNT(*) AS n FROM knowledge_nodes WHERE title = 'Ableitung ohne Quelle'")
    assert row["n"] == 0


# ─── d) NICHTAENDERUNG: fuenf echte Bestandsknoten ─────────────────────────

def test_d_fuenf_echte_bestandsknoten_ohne_abgeleitet_von_unveraendert(temp_db):
    """Fuenf echte source-Werte aus der Produktions-DB (siehe
    test_knowledge_add_source.py::test_fuenf_echte_bestands_quellen_bleiben_
    erlaubt fuer die Herkunft der Zeilen). Ohne abgeleitet_von muss sich am
    Verhalten nichts aendern: source geht unveraendert durch, wird
    unveraendert gespeichert."""
    echte_quellen = [
        ("erzeugt aus buckeberg/auswertung/efbe-gruppe-recherche.md, dieses aus "
         "Handelsregister-Auskunft HRB 739928 und Impressen (Abruf 2026-08-06) "
         "sowie dem efbe-Vertragsentwurf in dokumente/Angebote Verwaltung 2027/ "
         "(Stand 2026-08-06T10:50:00+0200)"),
        ("Zweiter Rechercheweg (Gemini) 2026-08-06T12:40:00+0200, vom Betreiber "
         "eingebracht; Primaerquellen im Content genannt, Belegvorbehalt ebenda"),
        ("Recherche 2026-08-06T12:20:00+0200, 12 Web-Abrufe; Primaerquellen in "
         "Content genannt"),
        ("erzeugt aus Commit a5085064 im Repo /Volumes/daten/Begod2026/openlehr, "
         "Zweig merge/daten-features (Stand 2026-08-06T10:25:00+0200)"),
        ("erzeugt aus buckeberg/auswertung/heizung-bestand-und-historie.md, "
         "dieses wiederum aus dokumente/ (Wartungsvertraege, Protokolle 2016-"
         "2025, Rechnungen, Pruefberichte) (Stand 2026-08-06T10:20:00+0200)"),
    ]
    for i, quelle in enumerate(echte_quellen):
        res = kms.knowledge_add(
            "/", f"Bestandsknoten ohne Ableitung {i}", "Zusammenfassung ohne Bezug zur Quelle",
            content="Inhalt ist absichtlich themenfremd zur source.",
            source=quelle,
        )
        assert res.get("status") == "created", (i, quelle, res)
        row = _sql(temp_db, "SELECT source, abgeleitet_von FROM knowledge_nodes WHERE id = ?", (res["id"],))
        assert row["source"] == quelle, (i, "source wurde veraendert", row["source"])
        assert row["abgeleitet_von"] is None, (i, "abgeleitet_von haette NULL bleiben muessen")
