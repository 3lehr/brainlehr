"""START.md und README.md duerfen nicht verrotten.

Eine Anleitung, die niemand prueft, ist nach drei Monaten eine Falle — sie
sieht aus wie Wissen und ist eine Behauptung. Genau die Fehlerklasse, gegen
die brainlehr selbst gebaut ist, nur in Markdown statt in der Datenbank.

Geprueft wird das Nachpruefbare, nicht der Stil:
* jeder genannte `brainlehr.py <verb>` existiert wirklich,
* jeder genannte Dateipfad existiert wirklich,
* jede genannte Fehlermeldung kommt so auch im Code vor.

ROT VOR GRUEN: `python3 brainlehr.py haken` in START.md gegen einen Stand
ohne dieses Verb schlaegt hier fehl — vor dem 2026-08-08 gab es es nicht.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import re
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))

import brainlehr  # type: ignore  # noqa: E402

DOKUMENTE = ("START.md", "README.md")


def _text(name: str) -> str:
    return (WURZEL / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name", DOKUMENTE)
def test_genannte_verben_gibt_es(name):
    verben = set(re.findall(r"brainlehr\.py\s+([a-z]+)", _text(name)))
    assert verben, f"{name} nennt keinen einzigen Befehl — dann stimmt der Test nicht"
    for v in verben:
        assert hasattr(brainlehr, v), f"{name} nennt 'brainlehr.py {v}', das Verb gibt es nicht"


@pytest.mark.parametrize("name", DOKUMENTE)
def test_genannte_dateien_gibt_es(name):
    text = _text(name)
    # Pfade in Backticks, die wie Dateien oder Ordner aussehen
    kandidaten = set(re.findall(r"`([a-z_]+(?:/[a-z_.]+)*\.(?:py|sql|md|jsonl))`", text))
    kandidaten |= set(re.findall(r"`(haken/|tests/|auszug/)`", text))
    fehlend = [k for k in kandidaten if not (WURZEL / k).exists()]
    assert not fehlend, f"{name} nennt, was es nicht gibt: {sorted(fehlend)}"


def test_genannte_fehlermeldungen_stehen_im_code():
    """Die Tabelle 'Wenn etwas nicht geht' ist nur brauchbar, solange die
    Meldungen wirklich so lauten. Sie stammen aus den Triggern und aus dem
    Server — beide aendern sich, die Tabelle nicht von selbst."""
    text = _text("START.md")
    quellen = "\n".join(
        (WURZEL / f).read_text(encoding="utf-8")
        for f in ("herkunft_unveraenderlich.sql", "schema.sql", "knowledge_mcp_server.py")
    )
    tabelle = text.split("## Wenn etwas nicht geht")[1]
    meldungen = re.findall(r"^\| `([^`]+)` \|", tabelle, re.M)
    assert len(meldungen) >= 3, "die Tabelle ist leer oder anders aufgebaut"
    fehlend = [m for m in meldungen if m not in quellen and m != "database is locked"]
    assert not fehlend, f"START.md nennt Meldungen, die es so nicht mehr gibt: {fehlend}"
