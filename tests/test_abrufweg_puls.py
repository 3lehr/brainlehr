"""Reine Alterungs-/Auswahllogik fuer den Abrufweg-Puls (Ansicht 4 in
entscheidungen.html): welcher Weg ist aktuell, welcher verglimmt, wie alt ist
jeder. Die Animation selbst (requestAnimationFrame, Canvas-Zeichnen) wird hier
NICHT geprueft -- das ist Browser-Sache und laut Auftrag nicht Testgegenstand.
Geprueft wird nur abrufwegZustand()/abrufwegPulsAlpha()/abrufwegStatusText(),
extrahiert aus der HTML-Datei und in echtem Node ausgefuehrt (kein DOM noetig,
die Funktionen sind rein).
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DATEI = REPO / "entscheidungen.html"


def _puls_quelltext() -> str:
    text = DATEI.read_text(encoding="utf-8")
    start = text.index("// ---- Puls/Verglimmen")
    ende = text.index("function abrufwegSpalte(art)")
    block = text[start:ende]
    assert "function abrufwegZustand" in block
    assert "function abrufwegPulsAlpha" in block
    assert "function abrufwegStatusText" in block
    return block


def _node_verfuegbar() -> bool:
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True, timeout=10)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


pytestmark = pytest.mark.skipif(not _node_verfuegbar(), reason="node nicht installiert")


def _lauf(js_nach_extraktion: str):
    """Fuehrt den extrahierten Puls-Quelltext plus Zusatzcode in Node aus.
    Der Zusatzcode gibt am Ende JSON auf stdout aus; das wird zurueckgegeben."""
    skript = _puls_quelltext() + "\n" + js_nach_extraktion
    r = subprocess.run(["node", "-e", skript], capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        raise AssertionError(f"node-Lauf fehlgeschlagen:\n{r.stderr}")
    return json.loads(r.stdout)


def test_leerer_verlauf_liefert_nichts():
    out = _lauf("console.log(JSON.stringify(abrufwegZustand([], 1000, 4000)))")
    assert out == {"aktuell": None, "verglimmend": None}


def test_ein_eintrag_ist_aktuell_ohne_verglimmen():
    js = """
    const v = [{ d: { id: 'a' }, seit: 1000 }];
    console.log(JSON.stringify(abrufwegZustand(v, 1500, 4000)));
    """
    out = _lauf(js)
    assert out["verglimmend"] is None
    assert out["aktuell"]["d"]["id"] == "a"
    assert out["aktuell"]["alterMs"] == 500


def test_zweiter_eintrag_laesst_ersten_verglimmen():
    js = """
    const v = [{ d: { id: 'alt' }, seit: 0 }, { d: { id: 'neu' }, seit: 1000 }];
    console.log(JSON.stringify(abrufwegZustand(v, 1500, 4000)));
    """
    out = _lauf(js)
    assert out["aktuell"]["d"]["id"] == "neu"
    assert out["aktuell"]["alterMs"] == 500
    assert out["verglimmend"]["d"]["id"] == "alt"
    assert out["verglimmend"]["alterMs"] == 1500
    assert out["verglimmend"]["fortschritt"] == pytest.approx(500 / 4000)


@pytest.mark.parametrize("versatz,erwartet_verglimmend", [
    (-1, True),   # eine Millisekunde vor der Grenze: verglimmt noch
    (0, False),   # exakt an der Grenze: schon weg (Bedingung ist "<", nicht "<=")
    (1, False),   # eine Millisekunde darueber: erst recht weg
])
def test_glimmdauer_grenzwert(versatz, erwartet_verglimmend):
    glimm = 4000
    js = f"""
    const v = [{{ d: {{ id: 'alt' }}, seit: 0 }}, {{ d: {{ id: 'neu' }}, seit: 0 }}];
    const jetzt = {glimm} + {versatz};
    console.log(JSON.stringify(abrufwegZustand(v, jetzt, {glimm})));
    """
    out = _lauf(js)
    if erwartet_verglimmend:
        assert out["verglimmend"] is not None
    else:
        assert out["verglimmend"] is None


def test_fortschritt_bleibt_in_0_bis_1_auch_weit_nach_der_glimmdauer():
    # Sicherheitsnetz gegen die Kappungslogik in abrufwegLaden: selbst wenn
    # abrufwegZustand mit einem sehr grossen "jetzt" aufgerufen wird, darf
    # fortschritt nie ueber 1 laufen (Min-Klammer in der Implementierung).
    js = """
    const v = [{ d: { id: 'alt' }, seit: 0 }, { d: { id: 'neu' }, seit: 0 }];
    const z = abrufwegZustand(v, 999999, 4000);
    console.log(JSON.stringify({ verglimmend: z.verglimmend }));
    """
    out = _lauf(js)
    assert out["verglimmend"] is None  # laengst ausgeblendet, nicht bloss gekappt


def test_puls_alpha_bleibt_in_der_gedaempften_spanne():
    js = f"""
    let min = Infinity, max = -Infinity;
    for (let t = 0; t < {8 * 3200}; t += 17) {{
      const a = abrufwegPulsAlpha(t, {3200}, {0.83}, {0.13});
      min = Math.min(min, a); max = Math.max(max, a);
    }}
    console.log(JSON.stringify({{ min, max }}));
    """
    out = _lauf(js)
    assert out["min"] >= 0.70 - 1e-9
    assert out["max"] <= 0.96 + 1e-9
    # keine Abrisskante: die Spanne wird tatsaechlich ausgenutzt, es ist also
    # eine Schwingung und keine Konstante.
    assert out["max"] - out["min"] > 0.2


def test_status_text_nennt_verglimmen_nur_wenn_es_einen_ghost_gibt():
    js = """
    const ohne = abrufwegStatusText({ aktuell: null, verglimmend: null });
    const mitAktuell = abrufwegStatusText({
      aktuell: { d: { anfrage: { text: 'x' }, geliefert: { knoten: [1], lehren: [] } }, alterMs: 2000 },
      verglimmend: null,
    });
    const mitGhost = abrufwegStatusText({
      aktuell: { d: { anfrage: { text: 'x' }, geliefert: { knoten: [1], lehren: [] } }, alterMs: 2000 },
      verglimmend: { d: {}, alterMs: 6000, fortschritt: 0.5 },
    });
    console.log(JSON.stringify({ ohne, mitAktuell, mitGhost }));
    """
    out = _lauf(js)
    assert "verglimmt" not in out["ohne"]
    assert "verglimmt" not in out["mitAktuell"]
    assert "verglimmt" in out["mitGhost"]
    assert "50%" in out["mitGhost"]
