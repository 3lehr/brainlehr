"""Eine Aufzeichnung, die eine Zahl festhaelt, muss aus dem Code herleitbar sein.

ENTSTEHUNG, und sie ist selbst die Lehre: Diese Datei wurde am 2026-08-12
angelegt, weil ein Befund behauptete, runs/teilung_s12_2026-08-11.json halte
eine Verteilung fest (1008 / 1115), die aus dem Code nicht herleitbar sei --
dieser liefere 1070 / 1055. Der Befund war FALSCH und ist widerrufen (Commit
0cd159e). Der Code lieferte 1009 / 1116; die Aufzeichnung stimmte bis auf den
Zuwachs von zwei Knoten.

Der Irrtum entstand in der Gegenrechnung: sie baute teilung_s12.bestand() nach
und nahm die id als Schluessel, waehrend der Code damals den path nahm. Ein
Test, der die Rechnung des Codes NACHBAUT statt sie aufzurufen, prueft seine
eigene Nachbildung -- und ist dann nicht bloss falsch, sondern ueberzeugend.

Die Datei bleibt trotzdem, weil die Pruefung selbst richtig ist: eine
Aufzeichnung, die eine aus Code ableitbare Zahl festhaelt, muss gegen den Code
gehalten werden. Nur eben durch AUFRUF, siehe _gerechnet() unten.

Dieser Test haelt die AUFGEZEICHNETE Verteilung gegen die GERECHNETE. Er
prueft nicht die Teilung, sondern die Ehrlichkeit ihrer Aufzeichnung.

NACHTRAG 2026-08-12 (Schluesselwechsel path->id, siehe kern/teilung_s12.py::
bestand()): Die Wachstumsschranke unten prueft, dass eine einmal vergebene
Haelfte sich nie aendert -- das gilt nur INNERHALB desselben Schluessels.
runs/teilung_s12_2026-08-11.json ist unter dem alten (Pfad-)Schluessel
eingefroren und bleibt WORTGLEICH stehen (Beleg fuer die Vergangenheit); die
Wachstumspruefung braucht aber eine Baseline unter dem AKTUELLEN (ID-)
Schluessel, sonst vergleicht sie zwei verschiedene Teilungen und jede
Umverteilung sieht wie eine Verschiebung aus, obwohl keine (im neuen
Schluessel) stattfand. Baseline dafuer ist die NEUE Aufzeichnung
runs/teilung_s12_2026-08-12_id.json, die den Wechsel dokumentiert. Der
zweite Test unten (`test_der_falsche_wert_von_damals_steht_noch_da`) prueft
weiterhin gegen die ALTE Datei -- er ist ein Audit ihrer historischen
Unversehrtheit, kein Test der aktuellen Teilung."""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))

AUFZEICHNUNG = WURZEL / "runs" / "teilung_s12_2026-08-11.json"
# Neue Aufzeichnung nach dem Schluesselwechsel path->id (2026-08-12) --
# Baseline fuer die Wachstumspruefung, siehe Nachtrag im Modul-Docstring.
AUFZEICHNUNG_ID = WURZEL / "runs" / "teilung_s12_2026-08-12_id.json"


def _gerechnet() -> dict:
    """Ruft das Werkzeug, statt seine Rechnung nachzubauen.

    BEFUND 2026-08-12: Die erste Fassung dieses Tests baute die Zaehlung nach
    -- mit `id` als Schluessel. teilung_s12.bestand() nimmt fuer Knoten aber
    den `path`. Ergebnis: 1070 statt 1009 behandelte Knoten, und daraus wurde
    ein Befund gegen eine Aufzeichnung gemacht, die richtig war. Ein Test, der
    die Rechnung des Codes NACHBAUT, prueft seine eigene Nachbildung.
    """
    from kern import speicher, teilung_s12 as t
    with speicher.lesen() as conn:
        return t.zaehlen(conn)


@pytest.mark.skipif(
    os.environ.get("BRAINLEHR_RUN_LIVE") != "1" or not AUFZEICHNUNG_ID.exists(),
    reason="requires the explicitly selected live corpus and recorded baseline",
)
def test_aufgezeichnete_verteilung_ist_aus_dem_code_herleitbar():
    """Die eingefrorene (ID-basierte) Verteilung muss zur Rechnung passen --
    sonst ist die Aufzeichnung selbst falsch.

    Baseline ist runs/teilung_s12_2026-08-12_id.json (Schluessel `id`), nicht
    mehr runs/teilung_s12_2026-08-11.json (Schluessel `path`, bleibt als
    historischer Beleg unveraendert stehen -- siehe Modul-Docstring).
    """
    d = json.loads(AUFZEICHNUNG_ID.read_text())
    war, ist = d["verteilung_beim_einfrieren"], _gerechnet()

    # Nicht auf Gleichheit pruefen. Am Speicher wird waehrend des Laufs aus
    # anderen Projekten geschrieben -- ein Test auf absolute Zahlen ist dann
    # nicht rot, weil etwas kaputt ist, sondern weil jemand gearbeitet hat.
    # (Genau daran ist die erste Fassung dieses Tests gescheitert, im vollen
    # Lauf am 2026-08-12: allein, gruen; in der Suite, rot.)
    #
    # Geprueft wird stattdessen die Eigenschaft, auf die es ankommt: eine
    # einmal vergebene Haelfte aendert sich nie. Daraus folgt zwingend, dass
    # jede Haelfte nur WACHSEN kann, und zwar hoechstens um den Zuwachs
    # insgesamt. Diese Schranke haelt bei jedem Bestand und faengt trotzdem
    # jede echte Umverteilung.
    for art in ("knoten", "lehre"):
        zuwachs = ist[art]["gesamt"] - war[art]["gesamt"]
        assert zuwachs >= 0, f"{art}: Bestand geschrumpft ({war[art]} -> {ist[art]})"
        for haelfte in ("behandelt", "unbehandelt"):
            delta = ist[art].get(haelfte, 0) - war[art].get(haelfte, 0)
            assert 0 <= delta <= zuwachs, (
                f"{art}/{haelfte}: Zuordnung hat sich verschoben.\n"
                f"aufgezeichnet: {war[art]}\ngerechnet:     {ist[art]}\n"
                f"Diese Haelfte aenderte sich um {delta}, der Gesamtzuwachs "
                f"betraegt aber nur {zuwachs}. Eine vergebene Haelfte darf sich "
                "nie aendern -- passiert es doch, ist jede S12-Messung wertlos, "
                "und niemand koennte sagen, ab wann."
            )


@pytest.mark.skipif(not AUFZEICHNUNG.exists(), reason="keine Aufzeichnung an diesem Ort")
def test_der_falsche_wert_von_damals_steht_noch_da():
    """Gegenprobe zur Bauart: eine als unveraenderlich erklaerte Aufzeichnung
    wird berichtigt, nicht ueberschrieben. Verschwindet der alte Wert, ist die
    Datei kein Beleg mehr, sondern eine Behauptung ueber die Gegenwart."""
    d = json.loads(AUFZEICHNUNG.read_text())
    alt = d["verteilung_beim_einfrieren"]["knoten"]
    assert alt["behandelt"] == 1008 and alt["unbehandelt"] == 1115, (
        "Der urspruengliche -- falsche -- Wert wurde entfernt. Er gehoert dort "
        "hin; die Berichtigung steht daneben, nicht an seiner Stelle."
    )
