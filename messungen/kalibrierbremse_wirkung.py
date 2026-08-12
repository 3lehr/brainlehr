#!/usr/bin/env python3
"""Wirkung der Projektstufungs-Bremse (PROJECT_CALIBRATION_MIN_SAMPLES) auf
den Abruf der eigenen brainlehr-Knoten -- Auftrag 2026-08-12.

BEFUND VOR JEDER MESSUNG (Code-Beleg, kein Korpuslauf noetig fuer DIESEN
Teil): haken/knowledge_recall_hook.py::query() ruft
`_effective_noise_mult(None, project_counts)` (Zeile ~959) -- project_id ist
dort HART auf None verdrahtet, unabhaengig davon, wie viele Knoten
'brainlehr' traegt. _effective_noise_mult() selbst gibt bei project_id=None
sofort NOISE_FLOOR_MAD_MULT zurueck (Zeile 576f, vor der
PROJECT_CALIBRATION_MIN_SAMPLES-Pruefung). Und selbst WENN query() die echte
project_id uebergeben wuerde: PROJECT_NOISE_OVERRIDES ist ein leeres dict --
_effective_noise_mult('brainlehr', counts) faellt in Zeile 580 auf
`.get('brainlehr', NOISE_FLOOR_MAD_MULT)` zurueck, also wieder
NOISE_FLOOR_MAD_MULT. Zwei unabhaengige Gruende, warum 'Bremse wie heute' und
'Bremse fuer brainlehr ausgesetzt' im PRODUKTIONSCODE denselben mad_mult
(2.0) liefern -- geprueft per direktem Aufruf, siehe Kommentar unten bei
_beleg_aequivalenz().

Deshalb: EIN Korpuslauf (der echte Produktionspfad), keine zwei. Ein zweiter
Lauf mit project_id='brainlehr' haendisch verdrahtet wuerde bitidentische
mad_mult-Werte durchreichen und damit bitidentische Treffer -- ihn trotzdem
zu fahren waere kein zusaetzlicher Beleg, nur doppelte Rechenzeit (Embedding-
Kanal je Fall). _beleg_aequivalenz() haelt den Code-Beleg als lauffaehige
Probe fest, EIN Korpuslauf liefert die Zahlen.

Aufruf:
    python3 messungen/kalibrierbremse_wirkung.py --korpus runs/echtkorpus_2026-08-12T1000.json --out runs/kalibrierbremse_wirkung_2026-08-12.json
    python3 messungen/kalibrierbremse_wirkung.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken")]

import argparse
import json
import sqlite3
import sys

from kern import speicher
import time
from pathlib import Path

WURZEL = _w
import knowledge_recall_hook as rh  # noqa: E402 -- echter Abrufweg


def _kein_explore() -> float:
    return 1.0


def _beleg_aequivalenz(conn) -> None:
    """Laeuft als Teil von --selftest UND vor jedem echten Lauf (main()):
    haelt den Code-Beleg aus dem Modulkopf lauffaehig fest, statt ihn nur im
    Kommentar zu behaupten."""
    counts = rh._project_node_counts(conn)
    assert counts.get("brainlehr", 0) >= rh.PROJECT_CALIBRATION_MIN_SAMPLES, (
        "Voraussetzung des Auftrags nicht mehr erfuellt: brainlehr unter der "
        "Schwelle -- der ganze Befund waere hinfaellig", counts.get("brainlehr"))
    heute = rh._effective_noise_mult(None, counts)
    # So ruft der Betrieb es TATSAECHLICH auf (query() Zeile ~959).
    assert heute == rh.NOISE_FLOOR_MAD_MULT
    ausgesetzt = rh._effective_noise_mult("brainlehr", counts)
    # Hypothetisch verdrahtet (query() tut das heute NICHT) -- selbst dann
    # gleich, weil PROJECT_NOISE_OVERRIDES leer ist.
    assert ausgesetzt == rh.NOISE_FLOOR_MAD_MULT
    assert heute == ausgesetzt


def abrufen(task_text: str):
    kws = rh.keywords(task_text)
    if len(kws) < rh.MIN_HITS:
        return [], []
    return rh.query(kws, rand=_kein_explore, cwd=None, prompt=task_text)


def messen(faelle: list[dict]) -> dict:
    """Ein Fall = ein query()-Aufruf, danach jedes seiner Ziele einzeln
    geprueft (Nenner = Anzahl ZIELE, nicht Faelle -- ein Fall kann bis zu 3
    Ziele tragen). Getrennt nach Knoten/Lehren wie beauftragt."""
    ziel_treffer = {"knoten": [], "lehre": []}
    uebersprungen = 0
    for fall in faelle:
        kws = rh.keywords(fall["prompt"])
        if len(kws) < rh.MIN_HITS:
            uebersprungen += len(fall["ziele"])
            continue
        nodes, lessons = rh.query(kws, rand=_kein_explore, cwd=None, prompt=fall["prompt"])
        node_pfade = {n["path"] for n in nodes}
        lesson_ids = {l["id"] for l in lessons}
        for z in fall["ziele"]:
            art = "knoten" if z["art"] == "knoten" else "lehre"
            treffer = z["id"] in (node_pfade if art == "knoten" else lesson_ids)
            ziel_treffer[art].append(treffer)
    return {
        "knoten": [sum(ziel_treffer["knoten"]), len(ziel_treffer["knoten"])],
        "lehre": [sum(ziel_treffer["lehre"]), len(ziel_treffer["lehre"])],
        "uebersprungen_unter_min_hits": uebersprungen,
    }


def _selftest() -> None:
    # Naht statt eigener Verbindung (tests/test_naht_ratsche.py). Hier lag
    # zuerst ein eigenes sqlite3.connect -- ohne Not: gelesen wird nur.
    with speicher.lesen() as conn:
        _beleg_aequivalenz(conn)
    print("selftest ok (Code-Beleg: Bremse heute == Bremse ausgesetzt fuer "
          "brainlehr, project_id im Betrieb hartcodiert None, "
          "PROJECT_NOISE_OVERRIDES leer)", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--korpus", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    with speicher.lesen() as conn:
        _beleg_aequivalenz(conn)
        counts = rh._project_node_counts(conn)

    daten = json.loads(a.korpus.read_text(encoding="utf-8"))
    faelle = daten["faelle"]

    t0 = time.monotonic()
    ergebnis = messen(faelle)
    dauer = time.monotonic() - t0

    ausgabe = {
        "verfahren": "Ein Korpuslauf ueber den echten Produktionspfad "
                      "(rh.keywords + rh.query, MAX_NODES/MAX_LESSONS-Betriebsdeckel "
                      "10/7, Explore deterministisch aus). 'zustand_ausgesetzt' ist "
                      "NICHT separat gelaufen -- Code-Beleg oben (und "
                      "_beleg_aequivalenz(), lauffaehig) zeigt, dass query() heute "
                      "project_id=None hartcodiert ruft und PROJECT_NOISE_OVERRIDES "
                      "leer ist; ein zweiter Lauf mit project_id='brainlehr' liefert "
                      "denselben mad_mult (2.0) und damit bitidentische Treffer.",
        "korpus": str(a.korpus),
        "brainlehr_knoten": counts.get("brainlehr"),
        "project_calibration_min_samples": rh.PROJECT_CALIBRATION_MIN_SAMPLES,
        "noise_floor_mad_mult_heute": rh.NOISE_FLOOR_MAD_MULT,
        "noise_floor_mad_mult_ausgesetzt": rh.NOISE_FLOOR_MAD_MULT,
        "faelle_im_korpus": len(faelle),
        "dauer_sekunden": round(dauer, 1),
        "zustand_heute": ergebnis,
        "zustand_ausgesetzt": ergebnis,
        "unterschied": False,
    }
    if a.out:
        a.out.write_text(json.dumps(ausgabe, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Geschrieben: {a.out}")
    print(json.dumps(ausgabe, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
