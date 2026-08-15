"""Tests fuer kern/herkunft_belegung.py -- die Belegungstabelle fuer Aufgabe
J4 (docs/PLAN_GESAMT_2026-08-13.md, Linie J).

ANLASS: J4 verlangt eine Belegungstabelle mit Nenner je Feld, gegen den
ECHTEN Bestand -- diese Datei misst das wiederholbar statt es einmalig per
Handmessung zu behaupten. Grenzwerte: leeres Feld, Feld nur Leerzeichen,
Feld mit dem Text 'unbekannt', NULL. Alle vier zaehlen als 'leer' -- dieselbe
Regel wie speicher.normiere_akteur() sie fuer die Normierung (Aufgabe 79)
schon durchsetzt; hier wiederverwendet statt zweiter Definition.

Rot-vor-Gruen: vor der Implementierung schlaegt der Import fehl
(ModuleNotFoundError), danach bestehen die Tests. Vorrichtung ist eine
tmp_path-Datenbank (nie die echte, sonst schlaegt test_naht_ratsche.py an)."""
from __future__ import annotations

import sys as _sys
from datetime import datetime, timezone
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import sqlite3

import pytest

import herkunft_belegung as hb  # noqa: E402


@pytest.fixture()
def db(tmp_path):
    pfad = tmp_path / "herkunft_belegung_test.db"
    schema = (_w / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(pfad))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    return pfad


def _knoten(conn, id_, path, *, actor=None, session=None, model=None, client=None,
            abgeleitet_von=None, bedient_von=None):
    jetzt = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO knowledge_nodes
           (id, path, parent_path, project_id, title, summary, content, source,
            anlass, norm_entscheidung, norm_entschieden_von, norm_entschieden_am,
            norm_entschieden_grund, created_at, updated_at,
            actor, session, model, client, abgeleitet_von, bedient_von)
           VALUES (?, ?, NULL, 'shared', ?, '', NULL, 'test', 'skript',
                   'keine_norm', 'test', ?, 'Testvorrichtung, keine echte Norm-Pruefung',
                   ?, ?, ?, ?, ?, ?, ?, ?)""",
        (id_, path, path, jetzt, jetzt, jetzt, actor, session, model, client,
         abgeleitet_von, bedient_von))


def test_leer_und_leerzeichen_und_unbekannt_zaehlen_gleich(db):
    """GRENZWERT: NULL, '', '   ' und 'unbekannt' sind alle vier 'kein
    Wissen' -- eine Zaehlung darf sie nicht in vier Kategorien aufteilen."""
    conn = sqlite3.connect(str(db))
    _knoten(conn, "a1", "/t/eins", actor=None)
    _knoten(conn, "a2", "/t/zwei", actor="")
    _knoten(conn, "a3", "/t/drei", actor="   ")
    _knoten(conn, "a4", "/t/vier", actor="unbekannt")
    conn.commit()
    conn.close()

    ergebnis = hb.belegung(db)
    leer, gesamt = ergebnis["knowledge_nodes"]["actor"]
    assert gesamt == 4
    assert leer == 4, "NULL/Leerstring/Leerzeichen/'unbekannt' muessen alle als leer zaehlen"


def test_echter_wert_zaehlt_nicht_als_leer(db):
    """NEGATIVFALL: ein gefuelltes Feld darf nicht als leer gezaehlt werden."""
    conn = sqlite3.connect(str(db))
    _knoten(conn, "b1", "/t/fuenf", actor="claude-code")
    conn.commit()
    conn.close()

    ergebnis = hb.belegung(db)
    leer, gesamt = ergebnis["knowledge_nodes"]["actor"]
    assert (leer, gesamt) == (0, 1)


def test_bedient_von_und_abgeleitet_von_getrennt_gezaehlt(db):
    """Zwei Felder mit demselben leeren Bestand duerfen sich nicht
    gegenseitig verdecken -- jedes Feld hat seinen eigenen Nenner."""
    conn = sqlite3.connect(str(db))
    _knoten(conn, "c1", "/t/sechs", bedient_von="markus")
    _knoten(conn, "c2", "/t/sieben")
    conn.commit()
    conn.close()

    ergebnis = hb.belegung(db)
    assert ergebnis["knowledge_nodes"]["bedient_von"] == (1, 2)
    assert ergebnis["knowledge_nodes"]["abgeleitet_von"] == (2, 2)


def test_leere_tabelle_liefert_nenner_null_statt_fehler(db):
    """GRENZWERT: eine Tabelle ohne Zeilen (z.B. lessons_learned frisch
    angelegt) darf keine Division durch 0 ausloesen und keinen Fehler
    werfen -- Nenner 0 ist ein gueltiges, meldbares Ergebnis."""
    ergebnis = hb.belegung(db)
    assert ergebnis["lessons_learned"]["bedient_von"] == (0, 0)


def test_bericht_ist_lesbarer_text(db):
    conn = sqlite3.connect(str(db))
    _knoten(conn, "d1", "/t/acht", actor="claude-code")
    conn.commit()
    conn.close()

    text = hb.bericht(hb.belegung(db))
    assert "knowledge_nodes" in text
    assert "actor" in text
