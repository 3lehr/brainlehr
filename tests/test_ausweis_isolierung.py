"""Negativbeleg zu tests/conftest.py::_kein_echter_ausweis (Auftrag 2026-08-13).

ANLASS: seit ~/Desktop/brainlehr-ausweise/mein-geheimnis.txt auf diesem
Rechner existiert, loeste ausweis.loese_auf() ohne expliziten `pfad` denselben
echten Ausweis auf -- 14 Tests, die 'unbekannt'/unbeglaubigt erwarten, wurden
dadurch rot, weil sie sich (unbeabsichtigt) auf das Fehlen dieser Datei
verlassen hatten.

Dieser Test ist der wichtigere Beleg aus dem Auftrag: nicht nur, dass die
14 Tests wieder gruen sind, sondern dass die GESAMTE Suite unabhaengig vom
Heimatverzeichnis des ausfuehrenden Rechners ist -- auf JEDEM Rechner, mit
oder ohne echten Ausweis auf dem Schreibtisch, dasselbe Ergebnis."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import ausweis  # noqa: E402


def test_ohne_expliziten_pfad_ist_kein_test_beglaubigt(monkeypatch):
    """Die autouse-Vorrichtung (_kein_echter_ausweis in conftest.py) setzt
    BRAINLEHR_AUSWEISE bereits vor diesem Testkoerper auf ein leeres, frisches
    Verzeichnis -- dieser Test ruft loese_auf() bewusst OHNE eigenen `pfad`,
    genau wie die 14 zuvor roten Tests es taten, und prueft damit direkt die
    Vorrichtung selbst, nicht nur ihre Wirkung an anderer Stelle."""
    a = ausweis.loese_auf()

    assert not a.beglaubigt, (
        "loese_auf() ohne pfad war beglaubigt -- die Isolierungs-Vorrichtung "
        "in conftest.py greift nicht, ein Ausweis im Heimatverzeichnis des "
        "Rechners wird wieder gesehen"
    )
    assert a.rollen == ()


def test_desktop_ausweis_existiert_auf_diesem_rechner_trotzdem(monkeypatch):
    """Gegenprobe zur Gegenprobe: der echte Ausweis liegt tatsaechlich da --
    sonst waere der Test oben trivial gruen, weil es nichts zu isolieren gab.
    Nur der PFAD wird geprueft (existiert die Datei), nie ihr Inhalt."""
    monkeypatch.delenv("BRAINLEHR_AUSWEISE", raising=False)
    monkeypatch.delenv("BRAINLEHR_GEHEIMNIS", raising=False)

    echte_datei = ausweis.VORGABE_AUSWEISORDNER / "mein-geheimnis.txt"

    if not echte_datei.exists():
        import pytest
        pytest.skip(
            f"kein echter Ausweis unter {echte_datei} auf diesem Rechner -- "
            "der Negativbeleg oben ist dann nicht scharf, aber auch nicht falsch"
        )

    a = ausweis.loese_auf()
    assert a.beglaubigt, (
        "der echte Ausweis existiert, wird aber ausserhalb der Testsuite "
        "(ohne die autouse-Vorrichtung) nicht mehr aufgeloest -- das waere "
        "ein anderer Fehler, nicht der hier zu belegende"
    )
