"""Verdrahtungstest fuer haken/existenzpruefung.py.

LUECKE (Auftrag 2026-08-13): tests/test_existenzpruefung.py hat neun
Testfaelle -- alle pruefen Modullogik und main() direkt. Keiner prueft, ob
der Haken ueberhaupt am Stop-Haltepunkt der projekteigenen
.claude/settings.json haengt. Loescht jemand den Eintrag, bleiben alle neun
gruen -- der Haken lief nur nie. Genau das war heute an ui_guard.py und
push_guard.py gemessen worden (docs/PLAN_VERDRAHTUNG_2026-08-13.md).

GEPRUEFT wird der EINTRAG (steht er da, zeigt er auf eine existierende
Datei) -- nicht das Verhalten des Hooks selbst, das ist Sache der neun
anderen Testfaelle.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
SETTINGS = WURZEL / ".claude" / "settings.json"


def test_existenzpruefung_ist_als_stop_hook_eingetragen_und_zeigt_auf_vorhandene_datei():
    daten = json.loads(SETTINGS.read_text(encoding="utf-8"))
    stop_hooks = daten.get("hooks", {}).get("Stop", [])
    kommandos = [
        h.get("command", "")
        for eintrag in stop_hooks
        for h in eintrag.get("hooks", [])
    ]

    treffer = [k for k in kommandos if "existenzpruefung.py" in k]
    assert treffer, (
        f"Kein Stop-Hook in {SETTINGS} verweist auf existenzpruefung.py -- "
        "der Haken haengt nirgends."
    )

    fund = re.search(r"(\S+existenzpruefung\.py)", treffer[0])
    assert fund, f"Kein Dateipfad im Kommando erkennbar: {treffer[0]!r}"

    ziel = Path(fund.group(1))
    if not ziel.is_absolute():
        ziel = WURZEL / ziel
    assert ziel.exists(), f"Eingetragene Datei existiert nicht: {ziel}"
