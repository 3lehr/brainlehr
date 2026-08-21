"""Tests fuer forderung_zustaendig ueber die Gegenstands-Achse (Strang B4,
Auftrag 2026-08-21).

BEFUND VOR DIESEM AUFTRAG: knowledge_nodes.forderung_zustaendig war freier,
ueber speicher.normiere_akteur() normierter Text -- ein NAME als Schluessel,
die Bauform, gegen die ADR-028 (kern/gegenstand.py) geschrieben wurde. Eine
Umbenennung der zustaendigen Person aendert daran nichts: der alte Name
bleibt in der Spalte stehen, und es gab ueberhaupt keinen Weg, "welche
Vorgaenge haengen an dieser Person" zu beantworten (keine Ruecklaufabfrage
existierte). ROT hier heisst: melder.forderung_vorgang kennt
zustaendiger_von()/vorgaenge_des_zustaendigen()/terminieren(...,
zustaendig_gegenstand=...) VOR diesem Auftrag nicht -- test_rot_* belegt das
gegen den echten Stand an 668b64c0 (kein Nachbau von Hand).

Beide Ausgangszustaende: `frisch` baut die DB direkt aus schema.sql auf,
`gewachsen` simuliert eine Datenbank, in der weder die gegenstand_bezug- noch
die gegenstaende-Tabelle je angelegt wurden (der Normalfall fuer jede
bestehende brainlehr-Instanz vor diesem Auftrag, da kern/gegenstand.py seine
Tabellen nur lazy ueber ensure_schema() anlegt)."""
from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "kern"))
sys.path.insert(0, str(WURZEL / "melder"))

import gegenstand  # noqa: E402
import speicher  # noqa: E402
import forderung_vorgang as fv  # noqa: E402

BEZUG = "668b64c0"
TS = "2026-08-21T12:00:00+0200"


def _insert(conn: sqlite3.Connection, node_id: str, path: str,
           erstellt: str = "2026-08-21T09:00:00Z") -> None:
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, "
        "level, source, created_at, norm_entscheidung, norm_entschieden_von, "
        "norm_entschieden_grund) VALUES (?,?,?,?,?,?,0,?,?,'keine_norm','test',"
        "'Testvorrichtung, keine echte Norm-Pruefung')",
        (node_id, path, "shared", "Vorgang", "x", "x", "test", erstellt))


@pytest.fixture()
def frisch(tmp_path) -> Path:
    """Ausgangszustand 1 von 2: frisch aus schema.sql angelegt."""
    db = tmp_path / "frisch.db"
    conn = sqlite3.connect(str(db))
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    _insert(conn, "v1", "/brainlehr/vorgang-eins")
    conn.execute("UPDATE knowledge_nodes SET forderung_stand='offen' WHERE path=?",
                ("/brainlehr/vorgang-eins",))
    conn.commit()
    conn.close()
    return db


@pytest.fixture()
def gewachsen(tmp_path) -> Path:
    """Ausgangszustand 2 von 2: schema.sql wie bei `frisch`, aber OHNE dass
    gegenstand.ensure_schema() je gelaufen ist -- gegenstaende/gegenstand_namen/
    gegenstand_bezug existieren nicht. Genau dieser Zustand ist heute (Stand
    668b64c0) der Normalfall fuer jede bestehende brainlehr-Instanz."""
    db = tmp_path / "gewachsen.db"
    conn = sqlite3.connect(str(db))
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    tabellen = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "gegenstaende" not in tabellen, "gegenstand.ensure_schema() lief schon vor dem Test"
    _insert(conn, "v2", "/brainlehr/vorgang-zwei")
    conn.execute("UPDATE knowledge_nodes SET forderung_stand='offen' WHERE path=?",
                ("/brainlehr/vorgang-zwei",))
    conn.commit()
    conn.close()
    return db


# --- ROT an 668b64c0 --------------------------------------------------------

def test_rot_an_668b64c0_terminieren_kennt_zustaendig_gegenstand_nicht():
    quelle = subprocess.run(["git", "show", f"{BEZUG}:melder/forderung_vorgang.py"],
                            cwd=WURZEL, capture_output=True, text=True, check=True).stdout
    assert "zustaendig_gegenstand" not in quelle
    assert "zustaendiger_von" not in quelle
    assert "vorgaenge_des_zustaendigen" not in quelle


# --- Haupttest: Umbenennung aendert die Auffindbarkeit NICHT ----------------

@pytest.mark.parametrize("db_fixture", ["frisch", "gewachsen"])
def test_haupttest_umbenennung_aendert_auffindbarkeit_nicht(db_fixture, request):
    db = request.getfixturevalue(db_fixture)
    path = "/brainlehr/vorgang-eins" if db_fixture == "frisch" else "/brainlehr/vorgang-zwei"

    with speicher.schreiben(db) as con:
        gegenstand.ensure_schema(con)
        gid = gegenstand.anlegen(con, "person", "Mira", beleg="Testanlage", ts=TS)

    fv.terminieren(path, zustaendig_gegenstand=gid, beleg="Testbindung", ts=TS, db=db)

    vor = fv.zustaendiger_von(path, db=db)
    assert vor == {"gegenstand_id": gid, "name": "Mira", "quelle": "gegenstand"}

    with speicher.schreiben(db) as con:
        gegenstand.umbenennen(con, gid, "Mira Musterfrau", beleg="Heirat", ts="2026-08-21T13:00:00+0200")

    nach = fv.zustaendiger_von(path, db=db)
    assert nach == {"gegenstand_id": gid, "name": "Mira Musterfrau", "quelle": "gegenstand"}, (
        "die Umbenennung der zustaendigen Person hat die Auffindbarkeit des Vorgangs veraendert")


# --- Negativtest: zwei Personen desselben Namens bleiben unterscheidbar ----

def test_negativtest_gleichnamige_personen_bleiben_unterscheidbar(frisch):
    db = frisch
    with speicher.schreiben(db) as con:
        gegenstand.ensure_schema(con)
        g1 = gegenstand.anlegen(con, "person", "Mira", beleg="Anlage 1", ts=TS)
        g2 = gegenstand.anlegen(con, "person", "Mira", beleg="Anlage 2", ts="2026-08-21T12:05:00+0200")
    assert g1 != g2

    with pytest.raises(gegenstand.MehrdeutigerName):
        fv.terminieren("/brainlehr/vorgang-eins", zustaendig="Mira",
                       beleg="Testbindung", ts="2026-08-21T14:00:00+0200", db=db)

    # kein Rueckfall: eine mehrdeutige Namensaufloesung darf auch NICHT still
    # als Freitext landen -- sonst waere die Auffindbarkeit wieder geraten.
    assert fv.zustaendiger_von("/brainlehr/vorgang-eins", db=db) is None

    # Ueber die explizite ID gelingt es, und die beiden bleiben unterschieden.
    fv.terminieren("/brainlehr/vorgang-eins", zustaendig_gegenstand=g2,
                   beleg="Testbindung", ts="2026-08-21T14:00:00+0200", db=db)
    treffer = fv.zustaendiger_von("/brainlehr/vorgang-eins", db=db)
    assert treffer["gegenstand_id"] == g2 and treffer["gegenstand_id"] != g1


# --- Gegenprobe in BEIDE Richtungen -----------------------------------------

@pytest.mark.parametrize("db_fixture", ["frisch", "gewachsen"])
def test_gegenprobe_beide_richtungen(db_fixture, request):
    db = request.getfixturevalue(db_fixture)
    path = "/brainlehr/vorgang-eins" if db_fixture == "frisch" else "/brainlehr/vorgang-zwei"

    with speicher.schreiben(db) as con:
        gegenstand.ensure_schema(con)
        gid = gegenstand.anlegen(con, "person", "Boris", beleg="Testanlage", ts=TS)
    fv.terminieren(path, zustaendig_gegenstand=gid, beleg="Testbindung", ts=TS, db=db)

    # Vorgang -> Zustaendiger.
    assert fv.zustaendiger_von(path, db=db)["gegenstand_id"] == gid

    # Zustaendiger -> Vorgaenge.
    vorgaenge = fv.vorgaenge_des_zustaendigen(gid, db=db)
    assert [v["path"] for v in vorgaenge] == [path]
    assert vorgaenge[0]["forderung_stand"] == "offen"

    # Ein fremder Gegenstand findet nichts -- keine Bergung auf Verdacht.
    with speicher.schreiben(db) as con:
        fremd = gegenstand.anlegen(con, "person", "Niemand", beleg="Testanlage", ts=TS)
    assert fv.vorgaenge_des_zustaendigen(fremd, db=db) == []


# --- Rueckweg: ein Zustaendiger ohne Gegenstand bleibt eintragbar -----------

def test_rueckweg_freitext_ohne_gegenstand_bleibt_moeglich(frisch):
    db = frisch
    # Ohne beleg/ts: reiner Freitext wie im Altverhalten, unveraendert.
    fv.terminieren("/brainlehr/vorgang-eins", zustaendig="Praktikant Nr. 3", db=db)
    assert fv.zustaendiger_von("/brainlehr/vorgang-eins", db=db) == {
        "gegenstand_id": None, "name": "Praktikant Nr. 3", "quelle": "freitext"}

    # Mit beleg/ts, aber ohne dass der Name je einen Gegenstand bekommen hat:
    # derselbe Rueckweg, kein erzwungenes Anlegen.
    fv.terminieren("/brainlehr/vorgang-eins", zustaendig="Ganz Unbekannt",
                  beleg="Testbindung", ts=TS, db=db)
    with speicher.lesen(db) as con:
        namen_vorher = con.execute("SELECT count(*) FROM gegenstaende").fetchone()
    assert namen_vorher[0] == 0, "ein unbekannter Name hat einen Gegenstand erfunden"
    assert fv.zustaendiger_von("/brainlehr/vorgang-eins", db=db) == {
        "gegenstand_id": None, "name": "Ganz Unbekannt", "quelle": "freitext"}


def test_gegenstand_und_gegenstand_gleichzeitig_ist_ein_fehler(frisch):
    with pytest.raises(ValueError):
        fv.terminieren("/brainlehr/vorgang-eins", zustaendig="X", zustaendig_gegenstand="irgendeine",
                      beleg="b", ts=TS, db=frisch)


def test_zustaendiger_ohne_gegenstand_liest_leer_auf_gewachsener_db(gewachsen):
    """Kein Bezug, kein Freitext, keine gegenstand-Tabellen ueberhaupt --
    zustaendiger_von() und vorgaenge_des_zustaendigen() duerfen daran nicht
    scheitern (OperationalError), sondern melden schlicht 'nichts da'."""
    assert fv.zustaendiger_von("/brainlehr/vorgang-zwei", db=gewachsen) is None
    assert fv.vorgaenge_des_zustaendigen("irgendeine-id", db=gewachsen) == []
