"""Belegt (nicht behauptet), dass der Vorfuehrmodus in entscheidungen.html
ECHTE Abrufe absetzt -- denselben Weg wie eine Handeingabe derselben Anfrage.

Der Beleg ist Code-Identitaet statt einer zweiten Laufzeitmessung: Sowohl der
Formular-Submit (Handeingabe) als auch vorfuehrTick() (Simulator) rufen
ausschliesslich abrufwegLaden(text) auf, das intern GENAU EINEN
fetch('/api/abrufweg', ...) absetzt. Es gibt keine zweite Implementierung
des Abrufs im Vorfuehr-Block -- ein Duplikat waere die Stelle, an der sich
Simulator und Handeingabe auseinanderentwickeln koennten, ohne dass es
auffiele. Siehe docs/PLAN_SIMULATOR_2026-08-12.md, Alternative B.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATEI = REPO / "entscheidungen.html"


def _text() -> str:
    return DATEI.read_text(encoding="utf-8")


def _vorfuehr_block() -> str:
    text = _text()
    start = text.index("// ---- Simulator: Regler + Vorfuehrmodus")
    ende = text.index("// ---- Wissensraum-Zeichenflaeche")
    return text[start:ende]


def test_es_gibt_genau_eine_fetch_implementierung_fuer_api_abrufweg():
    # Handeingabe UND Simulator muessen durch denselben, einzigen Aufruf.
    treffer = re.findall(r"fetch\(\s*'/api/abrufweg'", _text())
    assert len(treffer) == 1, (
        f"erwartet genau einen fetch('/api/abrufweg', ...) -- gefunden {len(treffer)}. "
        "Ein zweiter waere eine zweite, potenziell abweichende Implementierung."
    )


def test_formular_submit_ruft_abrufwegladen_auf():
    text = _text()
    ziel = "abrufwegLaden(document.getElementById('abrufwegText').value);"
    start = text.index("document.getElementById('abrufwegLeiste').addEventListener")
    ende = text.index(ziel, start) + len(ziel)
    block = text[start:ende]
    assert "abrufwegLaden(document.getElementById('abrufwegText').value)" in block


def test_vorfuehrtick_ruft_denselben_abrufwegladen_auf_ohne_eigenen_fetch():
    block = _vorfuehr_block()
    assert "async function vorfuehrTick()" in block
    tick_start = block.index("async function vorfuehrTick()")
    tick_ende = block.index("function vorfuehrTimerNeuStarten")
    tick = block[tick_start:tick_ende]
    assert "await abrufwegLaden(text)" in tick, "Simulator muss denselben Weg wie die Handeingabe gehen"
    assert "fetch(" not in tick, "Simulator darf keine eigene fetch-Implementierung haben"


def test_vorfuehrmodus_verwendet_den_echtkorpus_nicht_erfundene_texte():
    block = _vorfuehr_block()
    assert "/api/echtkorpus" in block
    assert "Math.random" not in block  # keine erfundene/zufaellige Anfrage


def test_vorfuehrmodus_stoppt_bei_verdecktem_fenster():
    block = _vorfuehr_block()
    tick_start = block.index("async function vorfuehrTick()")
    tick = block[tick_start:tick_start + 300]
    assert "document.visibilityState !== 'visible'" in tick
