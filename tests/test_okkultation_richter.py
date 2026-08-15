"""Deckt messungen/okkultation_richter.py ab -- der Richter mit Soll-Antwort
(Betreiberidee 2026-08-15, s. Modulkopf dort). Kernpunkt: die Leckpruefung
MUSS ein absichtlich leckendes Kriterium erkennen (nicht nur behaupten, es
zu tun), und der Blindheitsnachweis MUSS zeigen, dass Labels das Urteil
nicht veraendern.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken", "messungen")]

import okkultation_richter as rk  # noqa: E402


KRITERIEN = [
    {"text": "nennt die Schwelle 0,65", "muster": ["0,65", "0.65"]},
    {"text": "nennt den Knoten /brainlehr/schwelle", "muster": ["/brainlehr/schwelle"]},
]


def test_kriterien_pruefen_voll_erfuellt():
    urteil = rk.kriterien_pruefen(
        KRITERIEN, "Die Schwelle liegt bei 0,65, siehe /brainlehr/schwelle.")
    assert urteil["erfuellt"] == 2 and urteil["anteil"] == 1.0


def test_kriterien_pruefen_nichts_erfuellt():
    urteil = rk.kriterien_pruefen(KRITERIEN, "Ich habe dazu keine Information.")
    assert urteil["erfuellt"] == 0


def test_kriterien_pruefen_teilweise():
    urteil = rk.kriterien_pruefen(KRITERIEN, "Ich vermute 0,65, mehr weiss ich nicht.")
    assert urteil["erfuellt"] == 1


def test_leck_pruefung_kriterien_erkennt_absichtliches_leck():
    """Rot-Probe: Ohne die Pruefung waere dieses Kriterium unbemerkt in den
    Richter gewandert und haette effektiv die Ziel-Kennung verraten."""
    leckendes_kriterium = [{"text": "nenne die Kennung /brainlehr/geheimziel",
                             "muster": ["/brainlehr/geheimziel"]}]
    ziele = [{"id": "/brainlehr/geheimziel"}]
    leckt, befunde = rk.leck_pruefung_kriterien(leckendes_kriterium, ziele)
    assert leckt is True
    assert len(befunde) == 1


def test_leck_pruefung_kriterien_sauberer_fall_leckt_nicht():
    sauberes_kriterium = [{"text": "nennt die Reihenfolge der Schritte",
                            "muster": ["zuerst", "danach"]}]
    ziele = [{"id": "/brainlehr/geheimziel"}]
    leckt, befunde = rk.leck_pruefung_kriterien(sauberes_kriterium, ziele)
    assert leckt is False
    assert befunde == []


def test_blindheitsnachweis_identische_quote_mit_vertauschten_labels():
    antworten = {
        "MIT": "Die Schwelle liegt bei 0,65, siehe /brainlehr/schwelle.",
        "OHNE": "Ich habe dazu keine Information.",
        "NEG": "Space Shuttle Program, Orbiter, Avionics.",
    }
    bn = rk.blindheitsnachweis(KRITERIEN, antworten)
    assert bn["stimmt_ueberein"] is True
    assert bn["abweichungen"] == []


def test_auswerten_richter_schliesst_werkzeugnutzung_aus():
    erg = rk.auswerten_richter(KRITERIEN, {
        "MIT": {"antwort": "Die Schwelle liegt bei 0,65, siehe /brainlehr/schwelle.",
                "werkzeuge_benutzt": False},
        "OHNE": {"antwort": "Ich habe dazu keine Information.", "werkzeuge_benutzt": False},
        "NEG": "nackter String ohne Feld",
    })
    assert erg["urteile"]["MIT"]["erfuellt"] == 2
    assert erg["urteile"]["OHNE"]["erfuellt"] == 0
    assert "NEG" in erg["werkzeug_ausgeschlossen"]
    assert "NEG" not in erg["urteile"]


def test_selftest_laeuft_durch():
    rk._selftest()
