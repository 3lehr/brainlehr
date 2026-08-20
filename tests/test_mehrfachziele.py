#!/usr/bin/env python3
"""Mehrfachziele im Pruefkorpus -- Betreiberfreigabe 2026-08-20 ("zu allen
drei ja!", Knoten 55ccd8c4).

WARUM: Der Korpus fuehrte je Frage GENAU EIN Ziel, waehrend mehrere
Eintraege dieselbe Frage sachlich beantworten koennen. Gemessen ueber alle
35 loesbaren Faelle (runs/mehrfachziele_2026-08-20.json): 7 von 20
Fehlgriffen haben ein legitimes Zweitziel, 13 nicht. Trefferquote danach
22 von 35 statt 15 von 35.

DER VORBEHALT WIRD MITGETRAGEN, nicht weggelassen: Die Beurteilung war
NICHT verblindet -- der Beurteilende sah je Fall das vorgesehene Ziel.
Genau die Schwaeche, die S4 an der ersten Handbeurteilung aufgedeckt hat.
Die Gegenprobe (13 von 20 ohne Zweitziel) spricht gegen ein zu
grosszuegiges Urteil, ersetzt aber keine Verblindung.

WAS HIER GEPRUEFT WIRD: nur die MECHANIK -- dass ein zweites Ziel zaehlt,
dass Altfaelle ohne zweites Ziel unveraendert funktionieren, und dass
nichts still durchrutscht. NICHT geprueft wird, ob die konkreten
Zweitziele richtig gewaehlt sind; das ist eine Beurteilung und steht in
der Messdatei.

ROT VOR GRUEN: Der erste Fall faellt gegen den Stand davor --
target_hit() prueft ausschliesslich c["target_id"].
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w), str(_w / "kern")]

import pytest  # noqa: E402

import messlauf_abrufguete as ml  # noqa: E402


def _n(pfad):
    return {"path": pfad, "title": "T", "summary": "S"}


def _l(kennung):
    return {"id": kennung, "description": "B", "prevention": "P"}


def test_zweitziel_zaehlt_als_treffer():
    fall = {"target_kind": "node", "target_id": "/a/eins",
            "target_ids_auch": ["/a/zwei"]}
    assert ml.target_hit(fall, [_n("/a/zwei")], []) is True


def test_erstziel_zaehlt_weiterhin():
    fall = {"target_kind": "node", "target_id": "/a/eins",
            "target_ids_auch": ["/a/zwei"]}
    assert ml.target_hit(fall, [_n("/a/eins")], []) is True


def test_ohne_zweitziel_unveraendert():
    """Die 28 Faelle ohne Zweitziel muessen sich exakt wie vorher verhalten --
    sonst waere aus der Erweiterung eine stille Aenderung des Massstabs
    geworden."""
    fall = {"target_kind": "node", "target_id": "/a/eins"}
    assert ml.target_hit(fall, [_n("/a/eins")], []) is True
    assert ml.target_hit(fall, [_n("/a/drei")], []) is False


def test_fremder_treffer_zaehlt_nicht():
    """NEGATIVFALL: Ein Eintrag, der WEDER Erst- NOCH Zweitziel ist, bleibt
    ein Fehlgriff. Ohne diese Zeile waere die Erweiterung eine Aufweichung."""
    fall = {"target_kind": "node", "target_id": "/a/eins",
            "target_ids_auch": ["/a/zwei"]}
    assert ml.target_hit(fall, [_n("/a/drei"), _n("/a/vier")], []) is False


def test_lehren_ebenso():
    fall = {"target_kind": "lesson", "target_id": "L-aaa111",
            "target_ids_auch": ["L-bbb222"]}
    assert ml.target_hit(fall, [], [_l("L-bbb222")]) is True
    assert ml.target_hit(fall, [], [_l("L-ccc333")]) is False


def test_zweitziel_darf_die_gattung_wechseln():
    """KORRIGIERT gegenueber dem ersten Entwurf dieses Tests, und die
    Messung hat den Ausschlag gegeben.

    Der Entwurf verlangte, ein Knotenfall duerfe nicht durch eine Lehre
    erfuellt werden -- "die Gattung bleibt Teil des Ziels". Die Messung vom
    2026-08-20 widerlegt das: DREI der sieben gefundenen Zweitziele
    wechseln die Gattung (L-298823 -> ein Knoten aus /plaene, L-476602 ->
    /arch/token-economy, L-b4b443 -> ein Knoten aus /methodik). Sachlich
    ist das richtig: Wer die Frage beantwortet bekommt, dem ist die Gattung
    des Eintrags gleichgueltig.

    Das ERSTziel behaelt seine Gattung -- target_kind steuert dort die
    Suchrichtung. Beim Zweitziel bindet sie nicht."""
    fall = {"target_kind": "lesson", "target_id": "L-aaa111",
            "target_ids_auch": ["/a/knoten-der-es-auch-beantwortet"]}
    assert ml.target_hit(fall, [_n("/a/knoten-der-es-auch-beantwortet")], []) is True


def test_korpus_traegt_die_gemessenen_zweitziele():
    """Die sieben Faelle aus runs/mehrfachziele_2026-08-20.json stehen im
    Korpus -- und NUR sie. Eine spaetere Erweiterung ohne Messung faellt
    hier auf."""
    faelle = ml.load_cases()
    mit = [c for c in faelle if c.get("target_ids_auch")]
    assert len(mit) == 7, [c["target_id"] for c in mit]
    for c in mit:
        assert isinstance(c["target_ids_auch"], list) and c["target_ids_auch"], c


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
