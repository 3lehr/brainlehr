#!/usr/bin/env python3
"""Jeder Melder, der laufen SOLL, haengt auch an einem Ereignis.

ANLASS, und er ist frisch: Am 2026-08-14 war die Verdrahtung von
`haken/worktree_identitaet.py` 36 Minuten nach dem Commit wieder aus
`~/.claude/settings.json` verschwunden (`L-083b95`). Der Commit belegte, dass
etwas getan wurde -- nicht, dass es noch gilt. Fuer Haken gibt es seither
`tests/test_haken_verdrahtung.py`; fuer MELDER gab es nichts.

DER UNTERSCHIED ZU DEN HAKEN, und deshalb eine eigene Datei: Ein Haken laesst
sich am Verhalten erkennen (er liest stdin). Ein Melder nicht -- er ist ein
gewoehnliches Skript. Es gibt also kein Merkmal im Code, aus dem sich ableiten
liesse, ob er verdrahtet gehoert. Diese Liste ist deshalb von HAND gepflegt,
und das ist die ehrliche Form: sie nennt genau die Melder, deren Verdrahtung
jemand ausdruecklich beschlossen hat.

WAS DIESE PROBE NICHT LEISTET: Sie prueft die EXISTENZ des Eintrags, nicht
seine Tauglichkeit -- dieselbe Grenze wie bei den Haken (`L-b3eb79`: gebaut,
verdrahtet und wirksam sind drei verschiedene Dinge). Ein Melder, der an einem
Ereignis haengt, das im Selbstlauf nie feuert, besteht diese Probe.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
WURZEL = _w

EINSTELLUNGEN = Path.home() / ".claude" / "settings.json"

# Melder, deren Verdrahtung beschlossen ist. Wer einen neuen baut und ihn
# NICHT hier eintraegt, hat entschieden, dass er nicht laufen soll -- diese
# Datei ist der Ort, an dem diese Entscheidung sichtbar wird.
SOLLEN_LAUFEN = [
    "melder/dienstwache.py",       # G2, seit 2026-08-14
    "melder/offene_arbeit.py",
    "melder/pruefer.py",
    "melder/rasterblick.py",
    "melder/sichtbarkeit.py",
    "melder/wissensverlauf.py",
]


def _alle_befehle() -> str:
    if not EINSTELLUNGEN.exists():
        return ""
    try:
        d = json.loads(EINSTELLUNGEN.read_text(encoding="utf-8"))
    except ValueError:
        return ""
    teile = []
    for eintraege in (d.get("hooks") or {}).values():
        for eintrag in eintraege:
            for haken in eintrag.get("hooks", []):
                teile.append(haken.get("command", ""))
    return "\n".join(teile)


@pytest.mark.skipif(not EINSTELLUNGEN.exists(),
                    reason="fremde Maschine ohne Klient-Einstellungen: kein Befund")
def test_jeder_beschlossene_melder_haengt_an_einem_ereignis():
    befehle = _alle_befehle()
    fehlend = [m for m in SOLLEN_LAUFEN if m.split("/")[-1] not in befehle]
    assert not fehlend, (
        f"{len(fehlend)} Melder sind gebaut und beschlossen, haengen aber an keinem "
        f"Ereignis: {', '.join(fehlend)} -- ein Melder, der nirgends haengt, zaehlt als "
        "keiner. Eintragen in ~/.claude/settings.json (SessionStart) oder aus "
        "SOLLEN_LAUFEN streichen, wenn er nicht laufen soll.")


def test_jeder_eingetragene_melder_existiert_auch():
    """Die Gegenrichtung: eine Liste, die auf nichts zeigt, ist schlimmer als keine."""
    fehlend = [m for m in SOLLEN_LAUFEN if not (WURZEL / m).exists()]
    assert not fehlend, f"in SOLLEN_LAUFEN, aber nicht im Verzeichnis: {', '.join(fehlend)}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
