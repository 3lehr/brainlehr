"""Der Melder, der eine ZAHL aus Annahme/Modellwissen ohne Quelle erkennt.

Dritter Melder der Familie (normbezug.py, existenzpruefung.py), Auftrag
2026-08-12: Anlass war eine modellierte statt gemessene Temperaturkurve, im
Text selbst als Annahme gekennzeichnet.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import zahlenbezug as zb  # noqa: E402


def test_positivkontrolle_anlassfall():
    """Der echte Satz aus dem Vorfall, woertlich (ABNAHME-Vorgabe)."""
    text = ("Ich habe die Temperaturkurve modelliert, nicht gemessen. "
            "Jahresmittel und Amplitude stammen aus meinem Modellwissen, "
            "gekennzeichnet als Annahme.")
    treffer = zb.treffer(text)
    assert treffer, "Anlassfall schlaegt nicht an"
    meldung = zb.melde(treffer)
    assert "ZAHL AUS ANNAHME/MODELLWISSEN" in meldung
    assert "DWD" in meldung  # naechste Handlung: freie amtliche Quelle


def test_negativfall_zahl_aus_quelle_loest_nichts_aus():
    """Zahlen, die aus einer Quelle stammen (Testlauf, amtliche Angabe),
    duerfen NICHT anschlagen -- ohne diesen Test waere ein Melder gruen, der
    immer meldet, und der wird nach drei Tagen uebersehen."""
    testlauf = ("Ausgangslage 2026-08-12T12:00, selbst gemessen: 863 passed, "
                "1 skipped, 7 xfailed, 0 failed.")
    assert zb.treffer(testlauf) == []

    amtlich = "Laut DWD lag das Jahresmittel 2025 bei 10,3 Grad."
    assert zb.treffer(amtlich) == []


def test_nur_signal_oder_nur_quant_loest_nichts_aus():
    """Beide Bedingungen sind noetig -- eine Annahme ohne Groessenbezug ist
    keine Zahlenannahme, eine Zahl ohne Annahmesignal ist keine unbelegte."""
    nur_signal = "Das ist eine ungeprueft Annahme, aber es geht um nichts Zaehlbares."
    assert zb.treffer(nur_signal) == []

    nur_quant = "Der Mittelwert liegt laut Messreihe bei 4,2."
    assert zb.treffer(nur_quant) == []


def test_gewoehnlicher_text_bleibt_still():
    assert zb.treffer("Der Test ist gruen. Die Funktion tut, was sie soll.") == []


def test_meldung_schweigt_bei_ordnung():
    assert zb.melde([]) == ""


def test_dublettenfrei():
    text = ("Der Wert stammt aus meinem Modellwissen, ungepruefte Annahme. "
            "Der Wert stammt aus meinem Modellwissen, ungepruefte Annahme.")
    treffer = zb.treffer(text)
    assert len(treffer) == len(set(treffer))
