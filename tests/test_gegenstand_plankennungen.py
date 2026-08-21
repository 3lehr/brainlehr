#!/usr/bin/env python3
"""P16: Die Gegenstands-Achse, angewandt auf die Plankennungen.

WARUM DIESE TESTS UND NICHT DER SELBSTTEST IN kern/gegenstand.py: Der dortige
Selbsttest belegt die BAUFORM aus ADR-028 (Namenskette, alter Name aufloesbar).
Er belegt NICHT die drei Faehigkeiten, die die Erstanwendung verlangt und die
am 2026-08-21 nachweislich fehlten:

  1. Aufloesung MIT ZEITPUNKT. `aufloesen()` kannte kein `ts`. Bei drei
     gleichnamigen Sprints ist "welcher S12 war 2026-08-09 gemeint" aber genau
     die Frage, wegen der das Register existiert.
  2. Ein Name allein ist kein Schluessel -- es braucht einen Weg, der bei
     Mehrdeutigkeit AUSDRUECKLICH scheitert statt still den ersten zu nehmen.
     Ein stiller Griff auf `[0]` ist die Fehlerklasse, gegen die ADR-028 steht.
  3. Die Bindung eines Wissensknotens an einen Gegenstand. `knowledge_relations`
     kann das NICHT: beide Fremdschluessel zeigen auf knowledge_nodes(path),
     ein Gegenstand ist kein Knoten (schema.sql:1073-1095, nachgesehen).

BEIDE AUSGANGSZUSTAENDE werden gefahren. Der gewachsene Bestand wird nicht aus
einer Namensliste nachgebaut, sondern INHALTSBESTIMMT: das Alt-Schema kommt per
`git show 2c37048f:kern/gegenstand.py` aus der Versionsverwaltung (L-e12296 --
eine Namensliste vergisst genau die Anweisung, die spaeter fehlt).
"""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "kern"))

import gegenstand  # noqa: E402

BEZUGSPUNKT = "2c37048f"


# ---------------------------------------------------------------- Vorrichtung

def _alt_schema() -> str:
    """Das Gegenstands-Schema, wie es am Bezugspunkt im Repo stand.

    Inhaltsbestimmt aus git, nicht aus einer Aufzaehlung von Tabellennamen:
    eine Liste haette am 2026-08-08 den Index vergessen und der Test waere
    gruen geblieben, obwohl der Nachzug ihn nie angelegt haette (L-e12296)."""
    quelle = subprocess.run(
        ["git", "-C", str(WURZEL), "show", f"{BEZUGSPUNKT}:kern/gegenstand.py"],
        capture_output=True, text=True, check=True).stdout
    m = re.search(r'TABLE_SQL = """(.*?)"""', quelle, re.DOTALL)
    assert m, "TABLE_SQL am Bezugspunkt nicht gefunden -- der Anker stimmt nicht"
    return m.group(1)


@pytest.fixture
def frisch(tmp_path) -> sqlite3.Connection:
    """Ausgangszustand 1: Datenbank aus schema.sql, nie gewachsen."""
    conn = sqlite3.connect(tmp_path / "frisch.db")
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    conn.execute("PRAGMA foreign_keys=ON")
    gegenstand.ensure_schema(conn)
    return conn


@pytest.fixture
def gewachsen(tmp_path) -> sqlite3.Connection:
    """Ausgangszustand 2: Datenbank, die das Alt-Schema samt Zeilen schon traegt.

    Genau die Lage der Produktivdatenbank am 2026-08-21 (2 Gegenstaende,
    7 Namen). Wer nur den frischen Fall faehrt, prueft die Haelfte und weiss
    nicht, welche."""
    conn = sqlite3.connect(tmp_path / "gewachsen.db")
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    conn.executescript(_alt_schema())
    conn.execute("INSERT INTO gegenstaende VALUES ('5e385722','anwendung','2026-08-01T00:00:00+0200')")
    conn.execute("INSERT INTO gegenstand_namen VALUES ('5e385722','Atelier','ruf',"
                 "'2026-08-14T00:00:00+0200','2026-08-18T22:00:00+0200','ADR-008')")
    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON")
    gegenstand.ensure_schema(conn)
    return conn


def _knoten(conn, kid: str, pfad: str, titel: str) -> None:
    """Ein Knoten, der die Schranken von schema.sql erfuellt.

    `norm_entscheidung` ist per Trigger Pflicht -- eine Testvorrichtung, die
    sie umgeht, wuerde einen Weg pruefen, den es im Betrieb nicht gibt."""
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, title, summary, level, norm_entscheidung,"
        " norm_entschieden_von, norm_entschieden_grund, source, anlass)"
        " VALUES (?,?,?,'Testknoten fuer die Gegenstandsbindung',2,'keine_norm','Test P16','Vorrichtung fuer die Gegenstandsbindung',"
        " 'tests/test_gegenstand_plankennungen.py', 'skript')",
        (kid, pfad, titel))


def _zwei_gleichnamige(conn) -> tuple[str, str]:
    """Zwei verschiedene Sachen, die beide 'S1' heissen -- der echte Fall.

    PLAN_DESTILLE_2026-08-09 vergibt S1 an 'Reifegrad messen',
    PLAN_ZWEITES_SIGNAL_2026-08-20 an 'Aufgriffsquote messen'. Zwei Gegenstaende,
    ein Rufname, verschiedene Zeitraeume."""
    a = gegenstand.anlegen(conn, "plankennung", "S1", beleg="docs/PLAN_DESTILLE_2026-08-09.md",
                           ts="2026-08-09T00:00:00+0200")
    gegenstand.umbenennen(conn, a, "S1-alt", beleg="abgeloest", ts="2026-08-20T00:00:00+0200")
    b = gegenstand.anlegen(conn, "plankennung", "S1", beleg="docs/PLAN_ZWEITES_SIGNAL_2026-08-20.md",
                           ts="2026-08-20T00:00:00+0200")
    return a, b


# ------------------------------------------------ 1. Aufloesung mit Zeitpunkt

@pytest.mark.parametrize("zustand", ["frisch", "gewachsen"])
def test_negativ_gleicher_rufname_verschiedene_zeit_bleibt_unterscheidbar(zustand, request):
    """Negativtest 1: derselbe Rufname zu verschiedenen Zeiten meint
    verschiedene Gegenstaende -- und die Auskunft muss sie trennen."""
    conn = request.getfixturevalue(zustand)
    a, b = _zwei_gleichnamige(conn)
    assert a != b, "zwei Anlaesse, ein Schluessel -- die ID ist nicht bedeutungslos genug"

    frueh = gegenstand.aufloesen(conn, "S1", ts="2026-08-10T00:00:00+0200")
    assert [t["id"] for t in frueh] == [a], frueh
    spaet = gegenstand.aufloesen(conn, "S1", ts="2026-08-21T00:00:00+0200")
    assert [t["id"] for t in spaet] == [b], spaet


@pytest.mark.parametrize("zustand", ["frisch", "gewachsen"])
def test_zeitpunkt_vor_jeder_geltung_liefert_nichts(zustand, request):
    """Grenzwert: vor gilt_ab gibt es den Namen nicht. Kein Ausweichen auf den
    naechstbesten Treffer."""
    conn = request.getfixturevalue(zustand)
    _zwei_gleichnamige(conn)
    assert gegenstand.aufloesen(conn, "S1", ts="2026-08-08T23:59:59+0200") == []


@pytest.mark.parametrize("zustand", ["frisch", "gewachsen"])
def test_grenzwert_gilt_ab_zaehlt_gilt_bis_nicht(zustand, request):
    """Schwelle-1 / Schwelle / Schwelle+1: gilt_ab ist eingeschlossen,
    gilt_bis ausgeschlossen -- sonst gehoert ein Name in zwei Zeitraeume."""
    conn = request.getfixturevalue(zustand)
    a, b = _zwei_gleichnamige(conn)
    wechsel = "2026-08-20T00:00:00+0200"
    assert [t["id"] for t in gegenstand.aufloesen(conn, "S1", ts=wechsel)] == [b], \
        "am Wechseltag muss der NEUE gelten, nicht beide"


# --------------------------------- 2. Ein Name allein ist kein Schluessel

@pytest.mark.parametrize("zustand", ["frisch", "gewachsen"])
def test_negativ_ohne_zeitpunkt_alle_kandidaten_nie_stille_auswahl(zustand, request):
    """Negativtest 2: ohne Zeitpunkt liefert die Aufloesung ALLE Kandidaten."""
    conn = request.getfixturevalue(zustand)
    a, b = _zwei_gleichnamige(conn)
    alle = gegenstand.aufloesen(conn, "S1")
    assert sorted(t["id"] for t in alle) == sorted([a, b]), alle


@pytest.mark.parametrize("zustand", ["frisch", "gewachsen"])
def test_negativ_eindeutige_aufloesung_scheitert_ausdruecklich(zustand, request):
    """Wer EINEN Gegenstand will, bekommt bei Mehrdeutigkeit einen Fehler --
    nicht den ersten. Der stille Griff auf [0] ist die Fehlerklasse aus
    ADR-028; ein Weg, der ausdruecklich scheitert, muss existieren."""
    conn = request.getfixturevalue(zustand)
    a, b = _zwei_gleichnamige(conn)
    with pytest.raises(gegenstand.MehrdeutigerName) as exc:
        gegenstand.aufloesen_eindeutig(conn, "S1")
    assert a in str(exc.value) and b in str(exc.value), \
        "der Fehler muss die Kandidaten NENNEN, sonst ist er keine Auskunft"
    # Mit Zeitpunkt ist er eindeutig und liefert.
    assert gegenstand.aufloesen_eindeutig(conn, "S1", ts="2026-08-10T00:00:00+0200")["id"] == a
    # Und ein nie vergebener Name erfindet nichts, sondern scheitert eigen.
    with pytest.raises(gegenstand.UnbekannterName):
        gegenstand.aufloesen_eindeutig(conn, "S99")


# ---------------------------------------- 3. Gegenprobe in beide Richtungen

@pytest.mark.parametrize("zustand", ["frisch", "gewachsen"])
def test_umbenennung_aendert_auffindbarkeit_ueber_alten_namen_nicht(zustand, request):
    """BDW-P16-AC1, beide Richtungen: der ALTE Name findet den Gegenstand
    weiterhin, der NEUE findet denselben."""
    conn = request.getfixturevalue(zustand)
    gid = gegenstand.anlegen(conn, "plankennung", "S12", beleg="PLAN_DESTILLE",
                             ts="2026-08-09T00:00:00+0200")
    vorher = gegenstand.aufloesen(conn, "S12")
    gegenstand.umbenennen(conn, gid, "S12-zweiter-Anlauf", beleg="PLAN_S12_ZWEITER_ANLAUF",
                          ts="2026-08-11T23:40:00+0200")

    alt = gegenstand.aufloesen(conn, "S12")
    assert [t["id"] for t in alt] == [t["id"] for t in vorher] == [gid], alt
    assert alt[0]["heisst_heute"] == "S12-zweiter-Anlauf"
    neu = gegenstand.aufloesen(conn, "S12-zweiter-Anlauf")
    assert [t["id"] for t in neu] == [gid], "der neue Name findet einen anderen Gegenstand"

    # Und vom Gegenstand zu allen seinen Namen -- die andere Richtung.
    assert [n["name"] for n in gegenstand.namen(conn, gid)] == ["S12", "S12-zweiter-Anlauf"]


# ------------------------------------------------- 4. Bindung an Eintraege

@pytest.mark.parametrize("zustand", ["frisch", "gewachsen"])
def test_bindung_knoten_an_gegenstand_beide_richtungen(zustand, request):
    """BDW-P16-AC1: ein Eintrag nennt seinen Gegenstand als KENNUNG.
    Und die Umbenennung des Gegenstands aendert daran nichts -- der Bezug
    haengt am Schluessel, nicht am Namen."""
    conn = request.getfixturevalue(zustand)
    _knoten(conn, "t1", "/test/s12", "Testknoten")
    gid = gegenstand.anlegen(conn, "plankennung", "S12", beleg="PLAN_DESTILLE",
                             ts="2026-08-09T00:00:00+0200")
    gegenstand.bezug_setzen(conn, "/test/s12", gid, beleg="Auftrag P16",
                            ts="2026-08-21T00:00:00+0200")

    assert [b["gegenstand_id"] for b in gegenstand.bezuege_des_knotens(conn, "/test/s12")] == [gid]
    assert [b["node_path"] for b in gegenstand.knoten_des_gegenstands(conn, gid)] == ["/test/s12"]

    gegenstand.umbenennen(conn, gid, "S12neu", beleg="x", ts="2026-08-22T00:00:00+0200")
    assert [b["node_path"] for b in gegenstand.knoten_des_gegenstands(conn, gid)] == ["/test/s12"], \
        "die Umbenennung hat die Bindung geloest -- dann haengt sie am Namen"


@pytest.mark.parametrize("zustand", ["frisch", "gewachsen"])
def test_bindung_negativ_unbekannter_gegenstand_wird_abgewiesen(zustand, request):
    """BDW-P16-AC2: ein Eintrag ohne gebundenen Gegenstand wird als solcher
    ausgewiesen statt geraten -- und ein erfundener Gegenstand nicht gebunden."""
    conn = request.getfixturevalue(zustand)
    _knoten(conn, "t2", "/test/ohne", "Ohne Gegenstand")
    assert gegenstand.bezuege_des_knotens(conn, "/test/ohne") == []
    with pytest.raises(ValueError):
        gegenstand.bezug_setzen(conn, "/test/ohne", "deadbeef", beleg="b",
                                ts="2026-08-21T00:00:00+0200")


# ------------------------------------------- 5. Die Erfassung der 57 Plaene

def test_erfassung_unterscheidet_vergabe_von_erwaehnung():
    """Der Unterschied, der schon einmal eine doppelt zu hohe Zahl erzeugt hat:
    eine Ueberschrift 'Warum F und G -- und nicht S1, S2, S3' VERGIBT nichts."""
    import gegenstand_plankennungen as gp
    text = (
        "# S12, zweiter Anlauf\n"
        "### Warum F und G — und nicht S1, S2, S3\n"
        "### S3 · Ein echter Abschnitt\n"
        "### S3 ist kein Forschungsschritt mehr\n"
        "Im Fliesstext steht S7 und wird nicht vergeben.\n"
        "| Kennung | Titel |\n| S4 | Eine Tabellenvergabe |\n"
        "| irgendwas | hier steht S8 im Text |\n"
    )
    assert sorted(f.kennung for f in gp.vergaben(text, "x.md")) == ["S12", "S3", "S4"]


def test_erfassung_gegen_die_echten_plandateien(tmp_path):
    """Ein gebautes Skript ist keine Messung. Dieser Test faehrt es gegen die
    echten Dateien und prueft die zwei Zahlen aus dem Auftrag nach."""
    import gegenstand_plankennungen as gp
    dateien = gp.plandateien(WURZEL)
    assert len(dateien) == 58, f"57 PLAN_*.md + SPRINTS.md erwartet, {len(dateien)} gefunden"

    conn = sqlite3.connect(tmp_path / "lauf.db")
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    gegenstand.ensure_schema(conn)
    bericht = gp.erfassen(conn, WURZEL)

    s12 = [k for k in bericht["kollisionen"] if k["kennung"] == "S12"]
    assert s12 and s12[0]["anzahl"] == 3, s12
    assert {Path(v["datei"]).name for v in s12[0]["vergaben"]} == {
        "PLAN_S12_ZWEITER_ANLAUF_2026-08-11.md", "PLAN_DESTILLE_2026-08-09.md", "SPRINTS.md"}

    # Jeder Gegenstand traegt Kennung, Datei, Datum und Projekt als NAMEN --
    # der Betreiber hat Datum und Projekt ausdruecklich verlangt, und ADR-028
    # verbietet sie im Schluessel.
    for g in bericht["gegenstaende"]:
        arten = {n["art_des_namens"] for n in g["namen"]}
        assert {"ruf", "pfad", "datum", "projekt"} <= arten, (g["id"], arten)
        assert not any(t in g["id"] for t in ("S1", "S12", "PLAN", "brainlehr")), \
            f"sprechender Schluessel {g['id']} -- das ist wieder ein Name"

    # Und die Kernauskunft: S12 aufgeloest liefert DREI Kandidaten, keinen.
    assert len(gegenstand.aufloesen(conn, "S12")) == 3
