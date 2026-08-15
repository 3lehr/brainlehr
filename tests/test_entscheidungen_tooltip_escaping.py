"""Sicherheitsfund O1 (docs/SICHERHEITSFUNDE_2026-08-14.md): die Punktwolken-
Tooltips in entscheidungen.html schrieben p.a/p.p/p.d/p.t sowie die
Abrufweg-Felder ee.titel/ee.pfad/best.zusatz roh per innerHTML in die Seite.
Die Werte stammen aus kern/raum_daten.py (Pfad/Titel/Datum von Knoten und
Lehren) -- eingeschleustes Markup dort liefe im Kontext des Betrachters.

Kein DOM noetig: beide Tooltip-Bloecke werden als reine Stringbildung aus der
HTML-Datei extrahiert und in echtem Node ausgefuehrt (wie
tests/test_abrufweg_punktwolke.py es fuer die Zuordnungslogik tut). Geprueft
wird nur die resultierende Zeichenkette, nie ihre Auswertung als Markup.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DATEI = REPO / "entscheidungen.html"


def _node_verfuegbar() -> bool:
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True, timeout=10)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


pytestmark = pytest.mark.skipif(not _node_verfuegbar(), reason="node nicht installiert")


def _quelltext() -> str:
    return DATEI.read_text(encoding="utf-8")


def _escHtml_quelltext() -> str:
    text = _quelltext()
    start = text.index("function escHtml(s) {")
    ende = text.index("\n}\n", start) + len("\n}")
    block = text[start:ende]
    assert "function escHtml" in block
    return block


def _punktwolke_block() -> str:
    """Der Tooltip-Aufbau fuer P[best] (p.a/p.t/p.p/p.d), Ansichten 0-2."""
    text = _quelltext()
    start = text.index("const p=P[best];")
    ende = text.index("abrufwegPunktZusatztext(best);", start) + len(
        "abrufwegPunktZusatztext(best);"
    )
    block = text[start:ende]
    assert "p.a" in block and "p.t" in block and "p.p" in block and "p.d" in block
    return block


def _abrufweg_block() -> str:
    """Der Tooltip-Aufbau fuer ee/best.zusatz, Ansicht 4."""
    text = _quelltext()
    start = text.index("const ee=best.e;")
    marker = "(ee.pfad ? '<span class=\"weg\">'+escHtml(ee.pfad)+'</span>' : '');"
    ende = text.index(marker, start) + len(marker)
    block = text[start:ende]
    assert "ee.titel" in block and "ee.pfad" in block and "best.zusatz" in block
    return block


def _lauf(skript: str):
    r = subprocess.run(["node", "-e", skript], capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        raise AssertionError(f"node-Lauf fehlgeschlagen:\n{r.stderr}")
    return json.loads(r.stdout)


NUTZLAST = '<img src=x onerror=alert(1)>"\'&'
NUTZLAST_ESCAPED_FRAGMENTE = ("&lt;img", "&quot;", "&#39;", "&amp;")


def _p_tooltip(p: dict, escHtml_verfuegbar: bool = True) -> str:
    fahne = {"innerHTML": None}
    stub_fahne = "const fahne = {};"
    zuordnung_stub = "function abrufwegPunktZusatztext(i){ return ''; }"
    esc_quelle = _escHtml_quelltext() if escHtml_verfuegbar else (
        # roher Vorzustand: keine Maskierung, wie vor dem Fix
        "function escHtml(s){ return s; }"
    )
    skript = f"""
{esc_quelle}
{zuordnung_stub}
{stub_fahne}
const P = [{json.dumps(p)}];
const best = 0;
{_punktwolke_block()}
console.log(JSON.stringify(fahne.innerHTML));
"""
    return _lauf(skript)


def _ee_tooltip(ee: dict, zusatz: str, escHtml_verfuegbar: bool = True) -> str:
    stub_fahne = "const fahne = {};"
    esc_quelle = _escHtml_quelltext() if escHtml_verfuegbar else (
        "function escHtml(s){ return s; }"
    )
    skript = f"""
{esc_quelle}
const ABRUFWEG_GRUND_TEXT = {{}};
{stub_fahne}
const best = {{ e: {json.dumps(ee)}, zusatz: {json.dumps(zusatz)} }};
{_abrufweg_block()}
console.log(JSON.stringify(fahne.innerHTML));
"""
    return _lauf(skript)


# ---- escHtml selbst ---------------------------------------------------------

def test_eschtml_maskiert_alle_fuenf_sonderzeichen():
    ergebnis = _lauf(_escHtml_quelltext() + "\nconsole.log(JSON.stringify(escHtml(" + json.dumps(NUTZLAST) + ")));")
    assert "<" not in ergebnis
    assert ergebnis == "&lt;img src=x onerror=alert(1)&gt;&quot;&#39;&amp;"


def test_eschtml_leerer_wert():
    ergebnis = _lauf(_escHtml_quelltext() + "\nconsole.log(JSON.stringify(escHtml('')));")
    assert ergebnis == ""


def test_eschtml_sehr_langer_wert_bleibt_vollstaendig_maskiert():
    lang = "<script>" * 2000
    ergebnis = _lauf(_escHtml_quelltext() + "\nconsole.log(JSON.stringify(escHtml(" + json.dumps(lang) + ")));")
    assert "<script>" not in ergebnis
    assert ergebnis.count("&lt;script&gt;") == 2000


# ---- Gegenprobe: harmloser Text bleibt lesbar --------------------------------

def test_p_tooltip_harmloser_text_unveraendert_lesbar():
    p = {"k": "n", "a": "Ast/Pfad", "t": "Ganz normaler Titel", "p": "/pfad/knoten", "d": "2026-08-14", "h": 3}
    ergebnis = _p_tooltip(p)
    assert "Ast/Pfad" in ergebnis
    assert "Ganz normaler Titel" in ergebnis
    assert "/pfad/knoten" in ergebnis
    assert "2026-08-14" in ergebnis


# ---- Rot-vor-gruen: der alte (rohe) Zustand liefert ausfuehrbares Markup ----

def test_p_tooltip_ohne_maskierung_waere_die_nutzlast_roh_enthalten():
    """Belegt, dass der Test die Schwachstelle wirklich trifft: mit einer
    escHtml-Attrappe, die nichts maskiert (= Stand vor dem Fix), erscheint
    das eingeschleuste Markup unveraendert im String."""
    p = {"k": "n", "a": NUTZLAST, "t": "t", "p": "p", "d": "d", "h": 0}
    ergebnis = _p_tooltip(p, escHtml_verfuegbar=False)
    assert "<img src=x onerror=alert(1)>" in ergebnis


# ---- Gegenprobe: eingeschleustes Markup bleibt Text (P-Tooltip, alle Felder) -

@pytest.mark.parametrize("feld", ["a", "t", "p", "d"])
def test_p_tooltip_maskiert_eingeschleustes_markup_je_feld(feld):
    p = {"k": "n", "a": "a", "t": "t", "p": "p", "d": "d", "h": 0}
    p[feld] = NUTZLAST
    ergebnis = _p_tooltip(p)
    assert "<img" not in ergebnis
    for fragment in NUTZLAST_ESCAPED_FRAGMENTE:
        assert fragment in ergebnis, f"Feld {feld}: {fragment!r} fehlt in {ergebnis!r}"


def test_p_tooltip_grenzwert_leeres_feld_und_fehlendes_feld():
    p = {"k": "n", "a": "", "t": "", "p": "", "d": None, "h": 0}
    ergebnis = _p_tooltip(p)
    assert "<" not in ergebnis.replace("<br>", "").replace('<span class="weg">', "").replace("</span>", "")


def test_p_tooltip_sehr_langer_wert():
    p = {"k": "n", "a": "x" * 5000, "t": NUTZLAST * 100, "p": "p", "d": "d", "h": 0}
    ergebnis = _p_tooltip(p)
    assert "<img" not in ergebnis
    assert "&lt;img" in ergebnis


# ---- Gegenprobe: Abrufweg-Tooltip (ee.titel/ee.pfad/best.zusatz) -----------

def test_ee_tooltip_harmloser_text_unveraendert_lesbar():
    ee = {"art": "knoten", "titel": "Normaler Titel", "id": "x", "pfad": "/a/b", "ausgeschieden": None}
    ergebnis = _ee_tooltip(ee, "Rang 1")
    assert "Normaler Titel" in ergebnis
    assert "/a/b" in ergebnis
    assert "Rang 1" in ergebnis


@pytest.mark.parametrize("feld", ["titel", "pfad"])
def test_ee_tooltip_maskiert_eingeschleustes_markup(feld):
    ee = {"art": "knoten", "titel": "t", "id": "x", "pfad": "p", "ausgeschieden": None}
    ee[feld] = NUTZLAST
    ergebnis = _ee_tooltip(ee, "Rang 1")
    assert "<img" not in ergebnis
    assert "&lt;img" in ergebnis


def test_ee_tooltip_maskiert_zusatz():
    ee = {"art": "knoten", "titel": "t", "id": "x", "pfad": "p", "ausgeschieden": None}
    ergebnis = _ee_tooltip(ee, NUTZLAST)
    assert "<img" not in ergebnis
    assert "&lt;img" in ergebnis


def test_ee_tooltip_grenzwert_fehlendes_feld():
    ee = {"art": "anfrage", "titel": None, "id": "K-1", "pfad": None, "ausgeschieden": None}
    ergebnis = _ee_tooltip(ee, "")
    assert "K-1" in ergebnis
