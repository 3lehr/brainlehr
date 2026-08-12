"""Eine Aufzeichnung, die eine Zahl festhaelt, muss aus dem Code herleitbar sein.

BEFUND 2026-08-12: runs/teilung_s12_2026-08-11.json hielt die Verteilung der
S12-Teilung fest (Knoten 1008 behandelt / 1115 unbehandelt). Der im SELBEN
Commit c69c7e4 festgeschriebene Code liefert 1070 / 1055. Der Bestand war
seither um zwei Knoten gewachsen -- das erklaert keine 62. Aufzeichnung und
Code widersprachen sich vom ersten Tag an, und niemand haette es bemerkt: die
Datei erklaert sich selbst als unveraenderlich, also liest man sie als Wahrheit.

Die Zuordnungsfunktion war in Ordnung (alte gegen neue Fassung ueber 2888
Eintraege: 0 Abweichungen). Falsch war nur die Zahl daneben -- und genau das
ist die gefaehrlichere Sorte Fehler, weil die Zahl das ist, was gelesen wird.

Dieser Test haelt die AUFGEZEICHNETE Verteilung gegen die GERECHNETE. Er
prueft nicht die Teilung, sondern die Ehrlichkeit ihrer Aufzeichnung.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))

AUFZEICHNUNG = WURZEL / "runs" / "teilung_s12_2026-08-11.json"


def _gerechnet() -> dict:
    from kern import speicher, teilung_s12 as t
    with speicher.lesen() as conn:
        k = Counter(t.haelfte("knoten", i) for i, in conn.execute(
            "select id from knowledge_nodes where zurueckgezogen=0"))
        l = Counter(t.haelfte("lehre", i) for i, in conn.execute(
            "select id from lessons_learned where status!='resolved'"))
    return {"knoten": {"gesamt": sum(k.values()), **dict(k)},
            "lehre": {"gesamt": sum(l.values()), **dict(l)}}


@pytest.mark.skipif(not AUFZEICHNUNG.exists(), reason="keine Aufzeichnung an diesem Ort")
def test_aufgezeichnete_verteilung_ist_aus_dem_code_herleitbar():
    """Der Korrekturblock muss zur Rechnung passen -- sonst ist er selbst falsch.

    Bewusst gegen den KORREKTURBLOCK geprueft, nicht gegen das urspruengliche
    Feld: der falsche Wert von damals bleibt absichtlich stehen, weil die Datei
    sich als unveraenderlich erklaert. Getestet wird die Berichtigung.
    """
    d = json.loads(AUFZEICHNUNG.read_text())
    korrektur = d.get("korrektur_2026-08-12")
    assert korrektur, "Korrekturblock fehlt -- die Aufzeichnung behauptet wieder ungeprueft"
    assert korrektur["verteilung_gerechnet"] == _gerechnet(), (
        "Korrigierte Aufzeichnung weicht von der Rechnung ab.\n"
        f"aufgezeichnet: {korrektur['verteilung_gerechnet']}\n"
        f"gerechnet:     {_gerechnet()}\n"
        "Der Bestand waechst -- wenn nur die Gesamtzahl steigt, ist die "
        "Aufzeichnung nachzuziehen. Verschieben sich die Haelften staerker als "
        "der Zuwachs, hat sich die Zuordnung geaendert, und DAS entwertet jede "
        "S12-Messung."
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
