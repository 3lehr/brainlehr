"""Die Umrechnung des Bestands -- geprueft, bevor sie gefahren wird.

Aufgabe 111 Schritt 3, migrationen/lauf_utc_bestand_2026-08-14.py.

DER LAUF IST VORBEREITET UND BEWUSST NICHT GEFAHREN. Zwei Gruende, beide
gemessen am 2026-08-14, keiner davon Vorsicht:

1. Die laufenden MCP-Serverprozesse tragen den alten Code im Speicher (Start
   21:44, die Umstellung kam um 08:20). Ihr now_iso() liefert weiter
   Ortszeit. Nachgesehen: der juengste Knoten traegt '+02:00', waehrend
   access_log -- dessen Spalten-Vorgabewert in der Datenbank sitzt und nicht
   im Prozess -- bereits 'Z' bekommt. Wer den Bestand jetzt umrechnet, hat
   ihn beim naechsten Schreibvorgang wieder gemischt.
2. Die Datenbank war beim Versuch von einer parallelen Sitzung belegt
   ('database table is locked', fuenf Versuche). 38000 Werte umzuschreiben,
   waehrend jemand anders schreibt, ist kein Umbau, sondern ein Rennen.

Das ist dieselbe bindende Reihenfolge, die schon im Plan steht -- erst die
Erzeuger, dann der Bestand -- nur weitergedacht: EIN LAUFENDER PROZESS IST EIN
ERZEUGER. Ein Neustart der Sitzungen ist damit keine Aufraeumarbeit, sondern
die Vorbedingung.

Diese Datei belegt, dass die Umrechnung stimmt, wenn sie laeuft. Sie prueft
die reine Funktion, nicht den Bestand -- letzteres tut
tests/test_zeitform_utc.py, und das bleibt bis dahin rot.
"""
from __future__ import annotations

import importlib.util
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
WURZEL = _w
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken", "melder")]

import pytest  # noqa: E402


def _modul():
    spec = importlib.util.spec_from_file_location(
        "utc_bestand", WURZEL / "migrationen" / "lauf_utc_bestand_2026-08-14.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


M = _modul()


@pytest.mark.parametrize("vorher,nachher,was", [
    ("2026-08-14T09:31:52+02:00", "2026-08-14T07:31:52Z", "echter Versatz, Sommer"),
    ("2026-01-15T09:31:52+01:00", "2026-01-15T08:31:52Z", "echter Versatz, Winter"),
    ("2026-08-11T17:37:16+0200", "2026-08-11T15:37:16Z", "ohne Doppelpunkt"),
    ("2026-08-07T18:29:03.901235+00:00", "2026-08-07T18:29:03Z", "UTC mit Mikrosekunden"),
    ("2026-08-13T07:31:06Z", "2026-08-13T07:31:06Z", "Zielform bleibt"),
])
def test_alle_fuenf_formen(vorher, nachher, was):
    assert M.umrechnen(vorher) == nachher, was


def test_der_sonderfall_ist_der_ganze_grund():
    """'+01:00' im SOMMER ist ein gelogenes Anhaengsel: der Wert ist die
    abgelesene Wanduhr (CEST), das Label sagt CET. Wer stur nach dem Label
    rechnet, schreibt den Fehler fest, statt ihn zu beheben -- die Zeile waere
    danach immer noch eine Stunde daneben, nur in UTC."""
    assert M.umrechnen("2026-08-06T08:28:00+01:00") == "2026-08-06T06:28:00Z"
    # Stur nach Label waere 07:28 -- genau der Fehler, der verschwinden soll.
    assert M.umrechnen("2026-08-06T08:28:00+01:00") != "2026-08-06T07:28:00Z"


def test_im_winter_stimmt_dasselbe_label_und_wird_nicht_verbogen():
    """Gegenprobe, ohne die der Test darueber auch bei einer Umrechnung
    bestuende, die JEDES '+01:00' um zwei Stunden schiebt -- dann waere der
    ganze Winterbestand kaputt."""
    assert M.umrechnen("2026-01-15T08:28:00+01:00") == "2026-01-15T07:28:00Z"


@pytest.mark.parametrize("wert,sommer", [
    ("2026-03-29T01:59:00+01:00", False),   # eine Minute vor der Umstellung
    ("2026-03-29T03:01:00+01:00", True),    # eine Minute danach
    ("2026-10-25T01:59:00+01:00", True),    # vor der Rueckstellung
    ("2026-10-25T03:01:00+01:00", False),   # danach
])
def test_grenzwerte_an_beiden_umstellungsterminen(wert, sommer):
    """Schwelle minus, Schwelle, Schwelle plus -- an BEIDEN Terminen. Eine
    Umrechnung, die nur den Maerz kennt, faellt im Oktober nicht auf."""
    assert M._sommerzeit(wert) is sommer


def test_umstellungsregel_kommt_aus_zoneinfo_nicht_aus_handarbeit():
    """Die Regel hat sich in der Vergangenheit geaendert und kann es wieder.
    Eine nachgebaute Datumsrechnung ist ab diesem Tag falsch, und niemand
    merkt es -- deshalb zoneinfo. Belegt an einem Jahr mit anderen Terminen."""
    assert M._sommerzeit("2024-03-31T03:01:00+01:00") is True
    assert M._sommerzeit("2024-03-31T01:59:00+01:00") is False


def test_leeres_bleibt_leer():
    assert M.umrechnen("") == ""
    assert M.umrechnen(None) is None
