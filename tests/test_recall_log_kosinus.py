#!/usr/bin/env python3
"""Die Luecke, die S2 blockiert: recall_log.jsonl fuehrt keinen Kosinuswert.

BEFUND aus S1 (runs/aufgriffsquote_2026-08-20.json, Abschnitt
aufschluesselung_nach_staerke_des_treffers): Die Aufgriffsquote laesst sich
NICHT nach Trefferstaerke aufschluesseln. `bedeutungs_kosinus` existiert zur
Rechenzeit an jedem Treffer -- gemessen am 2026-08-20 -- wird aber nie
persistiert. Das Protokoll kennt nur, WAS eingespielt wurde, nicht WIE STARK.

DIE FOLGE, und sie ist der Grund fuer diesen Test: Wird die abgestufte
Ausgabe scharf geschaltet, bevor der Wert im Protokoll steht, ist danach
nicht mehr messbar, ob die Stufung richtig lag. Die Nulllinie von heute
(19,4 % Aufgriff, 30,5 % bei Lehren gegen 8,2 % bei Knoten) waere dann eine
Zahl ohne Vergleichbarkeit -- man wuesste, dass sich etwas geaendert hat, und
nie, ob zum Besseren.

Die Reihenfolge ist damit bindend: erst diese Spalte, dann der Schalter.

ROT VOR GRUEN: Gegen den Stand vor dieser Aenderung faellt der erste Fall --
das Protokoll schreibt den Schluessel nicht.
"""
from __future__ import annotations

import json
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken")]

import pytest  # noqa: E402

import knowledge_recall_hook as hook  # noqa: E402


def _zeile_schreiben(tmp_path, nodes, lessons):
    ziel = tmp_path / "recall_log.jsonl"
    hook.log_recall(nodes, lessons, log_path=str(ziel), cwd=str(tmp_path),
                    session_id="testtest", prompt=None)
    return json.loads(ziel.read_text().strip().splitlines()[-1])


def test_protokoll_fuehrt_den_kosinuswert_je_kennung(tmp_path):
    """Der Wert steht je KENNUNG, nicht als Liste -- eine Liste ohne
    Zuordnung ist genau das, was der Abrufweg schon einmal weggeworfen hat
    (L-497059) und was S1 dann nicht auswerten konnte."""
    zeile = _zeile_schreiben(
        tmp_path,
        nodes=[{"id": "abc12345", "path": "/a/eins", "title": "T", "summary": "S",
                "bedeutungs_kosinus": 0.6123}],
        lessons=[{"id": "L-abc123", "description": "B", "prevention": "P",
                  "bedeutungs_kosinus": 0.4711}],
    )
    werte = zeile.get("bedeutungs_kosinus")
    assert werte is not None, ("recall_log fuehrt keinen Kosinuswert -- die "
                              "Stufung ist danach nicht mehr nachpruefbar", sorted(zeile))
    assert werte.get("abc12345") == 0.6123, werte
    assert werte.get("L-abc123") == 0.4711, werte


def test_ohne_wert_kein_platzhalter(tmp_path):
    """NEGATIVFALL: Ein Treffer aus dem Stichwortkanal hat keinen Kosinuswert.
    Er bekommt KEINEN erfundenen -- eine 0.0 waere eine Aussage, die niemand
    gemessen hat, und sie wuerde spaeter als 'sehr schwach' gelesen."""
    zeile = _zeile_schreiben(
        tmp_path,
        nodes=[{"id": "ohnewert", "path": "/a/zwei", "title": "T", "summary": "S"}],
        lessons=[],
    )
    werte = zeile.get("bedeutungs_kosinus") or {}
    assert "ohnewert" not in werte, ("Platzhalter statt Auslassung", werte)


def test_alte_zeilen_bleiben_lesbar(tmp_path):
    """Der Schluessel wird NUR bei Werten gesetzt -- wie 'prompt' und
    'erstverwendung_vorschlag'. Bestandszeilen ohne ihn bleiben ueber .get()
    unveraendert lesbar, und S1 kann alt und neu im selben Lauf auswerten."""
    zeile = _zeile_schreiben(
        tmp_path,
        nodes=[{"id": "ohnewert", "path": "/a/zwei", "title": "T", "summary": "S"}],
        lessons=[],
    )
    assert "bedeutungs_kosinus" not in zeile, zeile
    # Und die Zeile ist trotzdem vollstaendig -- der Umbau nimmt nichts weg.
    for pflicht in ("nodes", "node_ids", "lessons", "cwd", "session"):
        assert pflicht in zeile, (pflicht, sorted(zeile))


def test_protokollieren_wirft_nie(tmp_path):
    """Die wichtigste Zusicherung dieser Datei, unveraendert aus dem
    bestehenden Vertrag: Das Protokoll ist Beiwerk und darf den Abruf NIE
    scheitern lassen. Ein kaputter Treffer bricht den Lauf nicht."""
    hook.log_recall([{"kaputt": True}], [], log_path=str(tmp_path / "r.jsonl"),
                    cwd=str(tmp_path), session_id="x", prompt=None)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
