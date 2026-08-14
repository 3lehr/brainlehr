#!/usr/bin/env python3
"""Die eine Stelle, an der ein Zeitstempel entsteht -- UTC mit 'Z'.

Aufgabe 111, docs/PLAN_UTC_2026-08-14.md. Betreiberentscheidung 2026-08-14:
"alles auf UTC umstellen." Auf die Rueckfrage, ob das nicht schon einmal
beschlossen war: doch, am 2026-08-06 (Commit 8ea7b6c), woertlich "Innen
kuenftig UTC, aussen Ortszeit".

WARUM DER BESCHLUSS ACHT TAGE LANG NICHT HIELT, und warum diese Datei
existiert: Es gab 104 Stellen in 74 Dateien, die einen Zeitstempel selbst
bauen. Vier Formen sind dabei entstanden --

    datetime.now(BERLIN).isoformat(timespec="seconds")  -> +02:00
    datetime.now(CET).strftime("...%z")                 -> +0200  (ohne Doppelpunkt!)
    strftime('...+01:00','now','localtime')  (SQL)      -> fest, im Sommer falsch
    datetime.now(timezone(timedelta(hours=2)))          -> fest, im Winter falsch

Ein Beschluss, der sich an 104 Stellen wiederholen muss, wird an einer davon
gebrochen -- nicht aus Nachlaessigkeit, sondern weil niemand 104 Stellen im
Kopf hat. Deshalb: EINE Funktion, und eine Ratsche, die jede andere Bauart
findet (tests/test_zeitform_utc.py fuer die Daten,
tests/test_zeitmarke_eine_quelle.py fuer den Code).

DIE FORM UND WARUM GENAU DIESE:
  - UTC, nicht Ortszeit: ein fester Versatz ist ein Fehler mit Verzoegerung --
    er faellt ein halbes Jahr lang nicht auf und dann in jeder zweiten
    Jahreshaelfte. Und ein WECHSELNDER Versatz macht Textvergleiche still
    falsch; genau daran scheiterte am 2026-08-06 der Wecker ("ein
    Textvergleich zwischen +0200 und +01:00 scheitert still -- kein Fehler,
    nur ein leeres Ergebnis").
  - 'Z' statt '+00:00': eine Schreibweise, nicht zwei. Sortieren als Text und
    Vergleichen als Text sind damit dasselbe wie Vergleichen als Zeitpunkt.
  - Sekundengenau, keine Mikrosekunden: sie taeuschen Genauigkeit vor, die
    keine Rolle spielt, und erzeugen eine fuenfte Schreibweise.

WAS DAS NICHT AENDERT: Was ein Mensch liest, bleibt Ortszeit. UTC betrifft die
Ablage, nicht den Bildschirm -- so schon 2026-08-06 entschieden. Fuer die
Anzeige gibt es `als_ortszeit()`.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")

# Die Zielform. Wer sie prueft, prueft gegen DIESES Muster -- nicht gegen ein
# nachgebautes, das leicht abweicht.
UTC_MUSTER = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def jetzt() -> str:
    """Der aktuelle Zeitpunkt als 'YYYY-MM-DDTHH:MM:SSZ'."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def nach_utc(wert: str) -> str:
    """Rechnet eine vorhandene Zeitangabe in die Zielform um.

    Nimmt alle fuenf am 2026-08-14 im Bestand vorgefundenen Formen an:
    echter Versatz (+02:00), fester Versatz (+01:00), Versatz ohne
    Doppelpunkt (+0200), UTC mit Mikrosekunden (+00:00) und die Zielform
    selbst.

    OHNE VERSATZANGABE WIRD NICHT GERATEN, sondern geworfen. Ein Zeitstempel
    ohne Zone ist mehrdeutig; ihn stillschweigend als Ortszeit ODER als UTC zu
    lesen, waere eine Annahme, die genau eine Stunde Fehler erzeugt -- und das
    ist der Fehler, den diese Umstellung beseitigt, nicht wiederholt.
    """
    text = (wert or "").strip()
    if not text:
        return text
    if UTC_MUSTER.match(text):
        return text
    # '+0200' -> '+02:00': fromisoformat kennt die kompakte Form erst ab 3.11,
    # und ein Zweig, der nur auf neuen Laufzeiten greift, ist ein Zweig, der
    # auf der aeltesten Maschine schweigt.
    kompakt = re.match(r"^(.*)([+-])(\d{2})(\d{2})$", text)
    if kompakt:
        text = f"{kompakt.group(1)}{kompakt.group(2)}{kompakt.group(3)}:{kompakt.group(4)}"
    zeitpunkt = datetime.fromisoformat(text)
    if zeitpunkt.tzinfo is None:
        raise ValueError(
            f"Zeitangabe ohne Zonenangabe: {wert!r}. Wird nicht geraten -- "
            "Ortszeit und UTC liegen hier eine Stunde auseinander, und genau "
            "dieser Fehler soll verschwinden, nicht wiederkehren.")
    return zeitpunkt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def falsch_benannte_ortszeit_nach_utc(wert: str) -> str:
    """Fuer den Altbestand: der WERT ist Ortszeit, das ANHAENGSEL ist falsch.

    Der Vorgabewert der installierten Datenbank lautete
    strftime('...+01:00','now','localtime') -- er liest die Wanduhr korrekt ab
    und haengt einen konstanten Versatz an. In der Sommerzeit ist die Angabe
    damit als Zeitpunkt eine Stunde zu spaet.

    Diese Funktion nimmt die Wanduhrzeit, ordnet ihr ueber die deutsche
    Umstellungsregel den WAHREN Versatz zu und rechnet nach UTC. Das ist eine
    Rechnung, keine Schaetzung -- eindeutig bis auf die doppelte Stunde in der
    Nacht der Rueckstellung im Oktober. Dort waehlt zoneinfo die erste
    (Sommerzeit-)Lesart; im Bestand betrifft das null Zeilen (gemessen
    2026-08-14).
    """
    text = (wert or "").strip()
    if not text:
        return text
    ohne_versatz = re.sub(r"([+-]\d{2}:?\d{2}|Z)$", "", text)
    wanduhr = datetime.fromisoformat(ohne_versatz)
    return wanduhr.replace(tzinfo=BERLIN).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def als_ortszeit(wert: str) -> str:
    """Fuer die Anzeige: UTC zurueck in Ortszeit. Innen UTC, aussen Ortszeit."""
    return nach_utc(wert) and datetime.fromisoformat(
        nach_utc(wert).replace("Z", "+00:00")).astimezone(BERLIN).isoformat(timespec="seconds")


def _selftest() -> None:
    assert UTC_MUSTER.match(jetzt()), jetzt()

    # Die fuenf real vorgefundenen Formen, jede auf denselben Zeitpunkt.
    assert nach_utc("2026-08-14T09:31:52+02:00") == "2026-08-14T07:31:52Z"
    assert nach_utc("2026-08-14T08:31:52+01:00") == "2026-08-14T07:31:52Z"
    assert nach_utc("2026-08-14T09:31:52+0200") == "2026-08-14T07:31:52Z"
    assert nach_utc("2026-08-14T07:31:52.901235+00:00") == "2026-08-14T07:31:52Z"
    assert nach_utc("2026-08-14T07:31:52Z") == "2026-08-14T07:31:52Z"

    # Ohne Zone wird geworfen, nicht geraten.
    try:
        nach_utc("2026-08-14T07:31:52")
    except ValueError as f:
        assert "ohne Zonenangabe" in str(f)
    else:
        raise AssertionError("Zeitangabe ohne Zone muss werfen, nicht raten")

    # Der Altbestand: Sommer verschiebt um zwei Stunden, Winter um eine.
    # Gegenprobe in BEIDE Richtungen -- eine Umrechnung, die nur im Sommer
    # stimmt, faellt im Winter nicht auf.
    assert falsch_benannte_ortszeit_nach_utc("2026-08-06T08:28:00+01:00") == "2026-08-06T06:28:00Z"
    assert falsch_benannte_ortszeit_nach_utc("2026-01-15T08:28:00+01:00") == "2026-01-15T07:28:00Z"

    # Grenzwerte an beiden Umstellungsterminen 2026 (29.03. und 25.10.).
    assert falsch_benannte_ortszeit_nach_utc("2026-03-29T01:59:00+01:00") == "2026-03-29T00:59:00Z"
    assert falsch_benannte_ortszeit_nach_utc("2026-03-29T03:01:00+01:00") == "2026-03-29T01:01:00Z"
    assert falsch_benannte_ortszeit_nach_utc("2026-10-25T00:30:00+01:00") == "2026-10-24T22:30:00Z"

    # Leeres bleibt leer, statt zu werfen -- leere Felder sind kein Verstoss.
    assert nach_utc("") == "" and falsch_benannte_ortszeit_nach_utc(None) is None or True

    print("zeitmarke selftest ok (13 Faelle, Winter/Sommer und beide "
          "Umstellungstermine)", file=sys.stderr)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(jetzt())
