"""Test fuer melder/eilmeldung_etikett.py -- Wache gegen den Fall vom
2026-08-12/13: ein Titel behauptet Dringlichkeit ('EILMELDUNG:', 'DRINGEND'),
das Zustell-Etikett (Tag 'dringend') fehlt, der Knoten wird nie zugestellt.

Rot-vor-gruen und Negativfall stehen bereits im Modul-eigenen --selftest
(eilmeldung_etikett._selftest, laeuft ueber test_alle_selftests.py als
Teil der vollen Suite). Diese Datei ergaenzt den Blick auf den ECHTEN
Bestand -- die Pruefung soll gemaess Auftrag darueber laufen und drei
Zahlen liefern, ohne die Betriebsdatenbank zu veraendern."""
from __future__ import annotations

import eilmeldung_etikett


def test_drei_zahlen_ueber_echten_bestand():
    ergebnis = eilmeldung_etikett.pruefe()
    for schluessel in ("vorhanden", "geprueft", "beanstandet", "befunde"):
        assert schluessel in ergebnis
    assert ergebnis["vorhanden"] == ergebnis["geprueft"], (
        "jeder vorhandene Dringlichkeits-Titel wird geprueft, keine Stichprobe")
    assert ergebnis["beanstandet"] <= ergebnis["vorhanden"]
    assert ergebnis["beanstandet"] == len(ergebnis["befunde"])
    # Faktenlage 2026-08-13: der einzige bekannte Fall (a146403a) wurde
    # bereits behoben -- 0 von 7 Knoten mit EILMELDUNG/DRINGEND im Titel
    # tragen kein 'dringend' mehr. Kein harter Gleichheits-Assert auf 0,
    # weil der Bestand zwischen Sitzungen waechst -- nur die Invariante,
    # dass die Pruefung selbst konsistent bleibt.


def test_negativfall_wort_im_satz_wird_nicht_beanstandet():
    """Gegenprobe direkt auf der Zaehlfunktion: ein Titel, der das Wort nur
    ENTHAELT statt damit zu BEGINNEN, ist keine Behauptung."""
    assert not eilmeldung_etikett._behauptet_dringlichkeit(
        "Die Eilmeldung von gestern im Rueckblick")
    assert not eilmeldung_etikett._behauptet_dringlichkeit(
        "Ist das wirklich dringend genug fuer heute?")


def test_praefix_wird_erkannt():
    assert eilmeldung_etikett._behauptet_dringlichkeit("EILMELDUNG: Belegpflicht")
    assert eilmeldung_etikett._behauptet_dringlichkeit("DRINGEND Serverausfall")
    assert eilmeldung_etikett._behauptet_dringlichkeit("eilmeldung klein geschrieben")
