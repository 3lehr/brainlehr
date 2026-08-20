"""Tests fuer kern/betriebsprofil.py -- BDW-P09-AC2.

Wechsel und Rueckweg je einmal gefahren, mit Bestandszaehlung davor und
danach -- auf einem FRISCHEN (leeren) und einem GEWACHSENEN (mit Zeilen)
Bestand, denn BDW-P09-AC1 verlangt genau diese Unterscheidung.

Rot vor f64e7a12: kern/betriebsprofil.py existiert dort nicht, dieser Import
scheitert mit ModuleNotFoundError -- gemessen, nicht behauptet.
"""
from __future__ import annotations

import sqlite3

import pytest

from kern import betriebsprofil as bp
from kern import speicher


def _leere_db(tmp_path):
    db = tmp_path / "leer.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        "CREATE TABLE knowledge_nodes (id TEXT PRIMARY KEY, mandant TEXT NOT NULL DEFAULT 'lokal');"
        "CREATE TABLE lessons_learned (id TEXT PRIMARY KEY, mandant TEXT NOT NULL DEFAULT 'lokal');"
        "CREATE TABLE knowledge_config (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL);"
    )
    conn.commit()
    conn.close()
    return db


def _gewachsene_db(tmp_path):
    db = tmp_path / "gewachsen.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        "CREATE TABLE knowledge_nodes (id TEXT PRIMARY KEY, mandant TEXT NOT NULL DEFAULT 'lokal');"
        "CREATE TABLE lessons_learned (id TEXT PRIMARY KEY, mandant TEXT NOT NULL DEFAULT 'lokal');"
        "CREATE TABLE knowledge_config (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL);"
        "INSERT INTO knowledge_nodes (id) VALUES ('n1'), ('n2'), ('n3');"
        "INSERT INTO lessons_learned (id) VALUES ('l1'), ('l2');"
    )
    conn.commit()
    conn.close()
    return db


def test_vorgabe_ohne_zeile_ist_einzelplatz(tmp_path):
    db = _leere_db(tmp_path)
    assert bp.profil(db) == bp.EINZELPLATZ


@pytest.mark.parametrize("aufbau", [_leere_db, _gewachsene_db])
def test_wechsel_und_rueckweg_bestandszaehlung_gleich(tmp_path, aufbau):
    db = aufbau(tmp_path)
    vorher = bp.zaehlung(db)

    hin = bp.wechsel(bp.UNTERNEHMEN, mandant="kunde-x", db=db)
    zwischenstand = bp.zaehlung(db)
    assert zwischenstand == vorher, "Wechsel darf keine Zeile verlieren oder gewinnen"
    assert bp.profil(db) == bp.UNTERNEHMEN
    assert hin["mandant"] == "kunde-x"

    with speicher.lesen(db) as conn:
        werte = {r["mandant"] for r in conn.execute("SELECT mandant FROM knowledge_nodes")}
        werte |= {r["mandant"] for r in conn.execute("SELECT mandant FROM lessons_learned")}
    if vorher["knowledge_nodes"] or vorher["lessons_learned"]:
        assert werte == {"kunde-x"}, werte

    zurueck = bp.wechsel(bp.EINZELPLATZ, db=db)
    nachher = bp.zaehlung(db)
    assert nachher == vorher, "Rueckweg darf keine Zeile verlieren oder gewinnen"
    assert bp.profil(db) == bp.EINZELPLATZ
    assert zurueck["mandant"] == bp.MANDANT_LOKAL

    with speicher.lesen(db) as conn:
        werte = {r["mandant"] for r in conn.execute("SELECT mandant FROM knowledge_nodes")}
        werte |= {r["mandant"] for r in conn.execute("SELECT mandant FROM lessons_learned")}
    if vorher["knowledge_nodes"] or vorher["lessons_learned"]:
        assert werte == {bp.MANDANT_LOKAL}, werte


def test_unbekanntes_profil_wird_abgelehnt(tmp_path):
    db = _leere_db(tmp_path)
    with pytest.raises(ValueError):
        bp.wechsel("weltraum", db=db)
    assert not list(tmp_path.glob("*.bak-*")), "abgelehnter Wechsel hat trotzdem gesichert"
    assert bp.profil(db) == bp.EINZELPLATZ, "abgelehnter Wechsel darf das Profil nicht aendern"


def test_leerer_mandantenname_scheitert(tmp_path):
    db = _gewachsene_db(tmp_path)
    with pytest.raises(ValueError):
        bp.wechsel(bp.UNTERNEHMEN, mandant="", db=db)
    with pytest.raises(ValueError):
        bp.wechsel(bp.UNTERNEHMEN, mandant="   ", db=db)
    assert bp.profil(db) == bp.EINZELPLATZ


def test_sicherung_liegt_vor_dem_wechsel(tmp_path):
    db = _gewachsene_db(tmp_path)
    bp.wechsel(bp.UNTERNEHMEN, mandant="kunde-y", db=db)
    sicherungen = list(tmp_path.glob(f"{db.name}.bak-*"))
    assert len(sicherungen) == 1, "genau eine Sicherung vor dem Wechsel"
