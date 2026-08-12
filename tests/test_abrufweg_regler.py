"""Reine Klemmfunktion fuer die fuenf Simulator-Regler (Ansicht 4 in
entscheidungen.html): abrufwegReglerKlemmen(wert, min, max). Die Pulsdauer-
Untergrenze 1000 ms ist eine WCAG-2.3.1-Grenze (max. 3 Blitze/s), kein
Vorschlag -- darum hier mit Grenzwerten an beiden Anschlaegen und einem
Negativfall geprueft. Extrahiert aus der HTML-Datei, in echtem Node
ausgefuehrt, wie tests/test_abrufweg_puls.py es fuer die Nachbarfunktionen
schon tut.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DATEI = REPO / "entscheidungen.html"


def _quelltext() -> str:
    text = DATEI.read_text(encoding="utf-8")
    start = text.index("// ---- Puls/Verglimmen")
    ende = text.index("function abrufwegSpalte(art)")
    block = text[start:ende]
    assert "function abrufwegReglerKlemmen" in block
    return block


def _node_verfuegbar() -> bool:
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True, timeout=10)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


pytestmark = pytest.mark.skipif(not _node_verfuegbar(), reason="node nicht installiert")


def _lauf(js_nach_extraktion: str):
    skript = _quelltext() + "\n" + js_nach_extraktion
    r = subprocess.run(["node", "-e", skript], capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        raise AssertionError(f"node-Lauf fehlgeschlagen:\n{r.stderr}")
    return json.loads(r.stdout)


@pytest.mark.parametrize("wert,erwartet", [
    (999, 1000),   # eine Millisekunde unter der Grenze: wird angehoben -- die Rot-Probe
    (1000, 1000),  # genau an der Grenze: unveraendert
    (1001, 1001),  # eine Millisekunde darueber: unveraendert
])
def test_pulsdauer_untergrenze_1000ms_ist_ein_anschlag(wert, erwartet):
    out = _lauf(f"console.log(JSON.stringify(abrufwegReglerKlemmen({wert}, 1000, 6000)))")
    assert out == erwartet


@pytest.mark.parametrize("wert,erwartet", [
    (5999, 5999),
    (6000, 6000),
    (6001, 6000),
])
def test_pulsdauer_obergrenze_6000ms(wert, erwartet):
    out = _lauf(f"console.log(JSON.stringify(abrufwegReglerKlemmen({wert}, 1000, 6000)))")
    assert out == erwartet


def test_negativfall_weit_ausserhalb_wird_trotzdem_geklemmt():
    # Ein eingebettetes Fenster (Mac-App) koennte einen Wert ausserhalb des
    # Schieberreglers hereinreichen (kein natives min/max-Attribut greift
    # dort zwingend) -- die Funktion muss auch -5000 oder 999999 abfangen.
    out = _lauf("console.log(JSON.stringify([abrufwegReglerKlemmen(-5000,1000,6000), abrufwegReglerKlemmen(999999,1000,6000)]))")
    assert out == [1000, 6000]


@pytest.mark.parametrize("wert,min_,max_,erwartet", [
    (0.39, 0.4, 1.0, 0.4),   # Helligkeit, Untergrenze
    (1.01, 0.4, 1.0, 1.0),   # Helligkeit, Obergrenze
    (-0.01, 0, 0.35, 0),     # Pulsstaerke, Untergrenze
    (0.36, 0, 0.35, 0.35),   # Pulsstaerke, Obergrenze
    (999, 1000, 15000, 1000),    # Nachleuchten, Untergrenze
    (15001, 1000, 15000, 15000), # Nachleuchten, Obergrenze
    (7, 8, 60, 8),           # Taktung, Untergrenze
    (61, 8, 60, 60),         # Taktung, Obergrenze
])
def test_alle_fuenf_regler_teilen_dieselbe_klemmung(wert, min_, max_, erwartet):
    out = _lauf(f"console.log(JSON.stringify(abrufwegReglerKlemmen({wert}, {min_}, {max_})))")
    assert out == erwartet
