"""Aufgabe 79, Schritt 2: normiere_modell()/normiere_akteur() (Schritt 1,
test_herkunft_schreibnormierung.py) sind reine Funktionen -- sie wirken erst,
wenn der SCHREIBPFAD sie aufruft. Einziger Choke Point fuer actor/model bei
knowledge_nodes/lessons_learned/access_log ist _identity() in
knowledge_mcp_server.py (knowledge_add, lesson_record, _ensure_ast_chain,
log_access rufen alle _identity() auf, siehe Modulkopf dort).

LUECKE, die dieser Test rot zeigt: ausweis.loese_auf() kennt den literalen
Text 'unbekannt' als Sentinel (protokollname-Sonderfall), aber NICHT dessen
Gross-/Kleinschreib- oder Leerzeichen-Varianten -- 'Unbekannt', '  unbekannt  '
etc. bleiben unveraendert stehen und tragen faelschlich das Praefix
'unbeglaubigt:'. speicher.normiere_akteur()/normiere_modell() faengt genau
das ab (Trim + Klein-Vergleich); sie muss VOR ausweis.loese_auf() bzw. vor
modell_normalisieren() auf den rohen Aufrufer-Wert angewendet werden.

Reiner Funktionstest gegen _identity() -- keine Datenbank noetig (_identity
schreibt nichts, siehe Aufruf in log_access/knowledge_add)."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


def test_grossschreibung_von_unbekannt_wird_wie_unbekannt_behandelt():
    """GRENZWERT: 'Unbekannt' (abweichende Gross-/Kleinschreibung) muss
    dasselbe Ergebnis liefern wie 'unbekannt' -- sonst zwei Schreibweisen
    fuer dieselbe Sache im Protokoll."""
    normal = kms._identity(actor="unbekannt", model=None, session="s")
    variante = kms._identity(actor="Unbekannt", model=None, session="s")
    assert normal[0] == variante[0], (normal, variante)
    assert not variante[0].startswith("unbeglaubigt:"), variante


def test_leerzeichen_um_unbekannt_wird_wie_unbekannt_behandelt():
    """GRENZWERT: Wert mit Leerzeichen am Rand."""
    variante = kms._identity(actor="  unbekannt  ", model=None, session="s")
    assert not variante[0].startswith("unbeglaubigt:"), variante


def test_leerer_actor_faellt_auf_die_bestehende_kette_zurueck():
    """GRENZWERT: leerer Wert -- muss identisches Ergebnis wie None liefern
    (beides 'kein Wert', vorher schon per Falsy-or abgefangen -- Gegenprobe,
    dass die Normierung das NICHT veraendert)."""
    leer = kms._identity(actor="", model=None, session="s")
    keiner = kms._identity(actor=None, model=None, session="s")
    assert leer[0] == keiner[0], (leer, keiner)


def test_echter_akteur_bleibt_unveraendert():
    """NEGATIVFALL: ein echter Akteursname darf NICHT normiert/veraendert
    werden -- nur 'unbekannt'/Leerwerte werden vereinheitlicht."""
    ergebnis = kms._identity(actor="claude-code/opus-5", model=None, session="s")
    # unbeglaubigt (kein Ausweis in der Testumgebung), aber der Name selbst
    # bleibt exakt erhalten -- kein Kollaps auf 'unbekannt'.
    assert ergebnis[0].endswith("claude-code/opus-5"), ergebnis


def test_modell_grossschreibung_von_unbekannt():
    """Dieselbe Regel gilt fuer model -- Grenzwert Gross-/Kleinschreibung."""
    ergebnis = kms._identity(actor=None, model="Unbekannt", session="s")
    assert ergebnis[1] == kms.UNBEKANNTER_SCHREIBER, ergebnis


def demo() -> None:
    test_grossschreibung_von_unbekannt_wird_wie_unbekannt_behandelt()
    test_leerzeichen_um_unbekannt_wird_wie_unbekannt_behandelt()
    test_leerer_actor_faellt_auf_die_bestehende_kette_zurueck()
    test_echter_akteur_bleibt_unveraendert()
    test_modell_grossschreibung_von_unbekannt()
    print("test_identity_normierung_79.demo ok")


if __name__ == "__main__":
    demo()
