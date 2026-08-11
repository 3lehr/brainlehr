"""Deckt die drei Filter/Merkmale aus messungen/echtkorpus.py ab, die die
Positivkontrolle vom 2026-08-11 verlangt hat: Fertigkeits-Vorspann raus,
Uebergabe-Prompts als eigene Satzart ('auftrag') statt stillschweigend
geloescht, ein echter Betreiber-Fall bleibt erhalten (Negativfall -- sonst
ist ein Filter, der alles wirft, gruen).

Rot-Probe (siehe Auftrag): mit VORSPANN durch ein Muster ersetzt, das nie
matcht, wird test_vorspann_wird_verworfen rot -- siehe Sitzungsbericht.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "messungen", "melder")]

import echtkorpus as ek  # noqa: E402


# Wortlaut wie ihn eine geladene Skill tatsaechlich voranstellt (siehe
# ek.VORSPANN) -- kein erfundenes Beispiel.
VORSPANN_FALL = ("Base directory for this skill: /Users/x/.claude/skills/foo\n\n"
                  "Lies zuerst STAND.md, dann arbeite den Plan ab.")

# Ein echter Betreiber-Fall: Bitte-Formulierung, kein Vorspann-Anfang, lang
# genug -- muss durch _ist_echte_frage UND als 'frage' oder 'auftrag'
# einsortiert werden, aber NIE verworfen.
ECHTER_FALL = "Sieh dir bitte kern/speicher.py an, das Zeitfeld sieht falsch aus."

# Uebergabe-Prompt: referiert den Stand, stellt keine Frage, ist aber eine
# echte, von einem Menschen abgeschickte Nachricht -- keine Systemmeldung,
# kein Vorspann. Muss unter Satzart 'auftrag' landen, nicht verworfen werden.
UEBERGABE_FALL = (
    "brainlehr, Fortsetzung. Lies zuerst STAND.md, dann arbeite.\n\n"
    "FAKTEN (gemessen 2026-08-09):\n"
    "  Der Knoten /agents/mcp-tools traegt den Befund.\n"
    "  Weitere Zeile Kontext, damit der Text lang genug ist fuer die Pruefung.\n")


def test_vorspann_wird_verworfen():
    assert not ek._ist_echte_frage(VORSPANN_FALL), \
        "Fertigkeits-Vorspann wurde nicht als solcher erkannt"


def test_echter_betreiber_fall_bleibt():
    # Negativfall zur vorigen Pruefung: ein Filter, der VORSPANN_FALL wirft,
    # aber auch alles andere wirft, waere gruen ohne etwas zu pruefen.
    assert ek._ist_echte_frage(ECHTER_FALL), \
        "ein echter Betreiber-Fall wurde faelschlich verworfen"


def test_uebergabe_prompt_eigene_satzart_kein_muell_keine_frage():
    assert ek._ist_echte_frage(UEBERGABE_FALL), \
        "Uebergabe-Prompt wurde verworfen statt als eigene Satzart gefuehrt"
    assert ek.satzart(UEBERGABE_FALL) == "auftrag", \
        "Uebergabe-Prompt landete nicht bei 'auftrag' (der eigenen Satzart)"


def test_selftest_des_moduls_besteht():
    ek._selftest()
