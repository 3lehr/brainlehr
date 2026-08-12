"""Reine Zuordnungs-/Staerke-Logik fuer die Abrufweg-Ueberlagerung der
Punktwolke (Ansichten 0-2 in entscheidungen.html, Auftrag 2026-08-12 Teil A/B).

Gepruefte Funktionen: abrufwegPunktIndex, abrufwegPunkteZuordnen,
abrufwegStaerkeSkala, abrufwegStaerkeNormiert -- alle rein (kein DOM), extrahiert
aus der HTML-Datei und in echtem Node ausgefuehrt, wie tests/test_abrufweg_puls.py
es fuer den Puls tut.

Die FALLE, die hier gezielt geprueft wird (gemessen, Commit 0cd159e widerrufen):
Knoten stehen im Abrufweg unter ihrer DB-ID, die Punktwolke kennt sie aber nur
unter ihrem PFAD. Wer beide ueber `id` verbindet, findet fuer JEDEN Knoten
nichts -- das ist der Negativfall unten (test_knoten_ueber_id_verbunden_findet_nichts).
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
    start = text.index("// ---- Punktwolken-Zuordnung")
    ende = text.index("function zeichne(){")
    block = text[start:ende]
    assert "function abrufwegPunktIndex" in block
    assert "function abrufwegPunkteZuordnen" in block
    assert "function abrufwegStaerkeSkala" in block
    assert "function abrufwegStaerkeNormiert" in block
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


# ---- abrufwegPunktIndex / abrufwegPunkteZuordnen --------------------------

def test_knoten_wird_ueber_pfad_gefunden():
    js = """
    const pfadIndex = new Map([['/apps/a', 3]]);
    const lehreIndex = new Map();
    const idx = abrufwegPunktIndex({ art: 'knoten', id: 'db-id-abc', pfad: '/apps/a' }, pfadIndex, lehreIndex);
    console.log(JSON.stringify(idx));
    """
    assert _lauf(js) == 3


def test_lehre_wird_ueber_kennung_gefunden():
    js = """
    const pfadIndex = new Map();
    const lehreIndex = new Map([['L-aaa111', 7]]);
    const idx = abrufwegPunktIndex({ art: 'lehre', id: 'L-aaa111', pfad: null }, pfadIndex, lehreIndex);
    console.log(JSON.stringify(idx));
    """
    assert _lauf(js) == 7


def test_knoten_ueber_id_verbunden_findet_nichts():
    # Negativfall, der die eigentliche Falle nachstellt: die Punktwolke kennt
    # Knoten nur unter dem Pfad. Wer versehentlich e.id gegen den pfadIndex
    # matcht (oder der Pfad im Bestand fehlt), muss NULL zurueckbekommen --
    # kein falscher Treffer, kein stiller Erfolg.
    js = """
    const pfadIndex = new Map([['/apps/a', 3]]);
    const lehreIndex = new Map();
    const idx = abrufwegPunktIndex({ art: 'knoten', id: '/apps/a', pfad: 'nicht-im-bestand' }, pfadIndex, lehreIndex);
    console.log(JSON.stringify(idx));
    """
    assert _lauf(js) is None


def test_zuordnen_zaehlt_treffer_und_fehlschlaege_getrennt():
    js = """
    const pfadIndex = new Map([['/apps/a', 0], ['/apps/b', 1]]);
    const lehreIndex = new Map([['L-x', 2]]);
    const eintraege = [
      { art: 'knoten', id: 'db1', pfad: '/apps/a' },
      { art: 'knoten', id: 'db2', pfad: '/apps/toter-pfad' },
      { art: 'lehre', id: 'L-x', pfad: null },
      { art: 'lehre', id: 'L-fehlt', pfad: null },
    ];
    const out = abrufwegPunkteZuordnen(eintraege, pfadIndex, lehreIndex);
    console.log(JSON.stringify({
      gefunden: out.gefunden.map(g => g.index),
      nichtGefundenAnzahl: out.nichtGefunden.length,
    }));
    """
    out = _lauf(js)
    assert sorted(out["gefunden"]) == [0, 2]
    assert out["nichtGefundenAnzahl"] == 2


def test_leere_liste_liefert_alles_leer():
    js = "console.log(JSON.stringify(abrufwegPunkteZuordnen([], new Map(), new Map())))"
    out = _lauf(js)
    assert out == {"gefunden": [], "nichtGefunden": []}


# ---- abrufwegStaerkeSkala / abrufwegStaerkeNormiert ------------------------

def test_staerke_normiert_ueber_die_spanne():
    js = """
    const skala = abrufwegStaerkeSkala([0.65, 0.70, 0.80]);
    console.log(JSON.stringify({
      min: abrufwegStaerkeNormiert(0.65, skala),
      mitte: abrufwegStaerkeNormiert(0.70, skala),
      max: abrufwegStaerkeNormiert(0.80, skala),
    }));
    """
    out = _lauf(js)
    assert out["min"] == pytest.approx(0.0)
    assert out["mitte"] == pytest.approx(0.5 / 1.5)
    assert out["max"] == pytest.approx(1.0)


def test_staerke_skala_leere_liste_liefert_null():
    js = "console.log(JSON.stringify(abrufwegStaerkeSkala([])))"
    assert _lauf(js) is None


def test_staerke_normiert_ohne_skala_liefert_null():
    js = "console.log(JSON.stringify(abrufwegStaerkeNormiert(0.7, null)))"
    assert _lauf(js) is None


def test_staerke_normiert_fehlender_wert_liefert_null():
    js = """
    const skala = abrufwegStaerkeSkala([0.6, 0.8]);
    console.log(JSON.stringify(abrufwegStaerkeNormiert(undefined, skala)));
    """
    assert _lauf(js) is None


def test_staerke_normiert_grenzwert_alle_werte_gleich():
    # Ein einziger Kandidat (oder lauter gleiche Werte) -- keine Abstufung
    # darstellbar. Muss volle Deckkraft liefern, nicht durch 0 teilen.
    js = """
    const skala = abrufwegStaerkeSkala([0.71, 0.71, 0.71]);
    console.log(JSON.stringify(abrufwegStaerkeNormiert(0.71, skala)));
    """
    assert _lauf(js) == 1
