#!/usr/bin/env python3
"""Wieviel Kontext ist zuviel? Trefferquote und Liefermenge ueber eine Deckelreihe.

ANLASS, und er kommt von aussen: Der Deep-Research-Bericht vom 2026-08-09
nennt zwei Befunde, die unsere 7/35 anders erklaeren als "die Suche ist zu
schwach".

  - "Metadata Tax": Werden je Abruf saemtliche Herkunfts-, Geltungs- und
    Belegfelder mitgeliefert, waechst der Kontext, und die Genauigkeit faellt
    durch Lost-in-the-Middle. Das ist eine Erklaerung, die NICHT am
    Suchverfahren haengt.
  - Governed Memory (arXiv:2603.17787) misst Saettigung der Ausgabequalitaet
    bei etwa SIEBEN Eintraegen je Entitaet. Unsere Deckel stehen bei 3+2=5.

Beide Zahlen sind FREMDBERICHT auf fremdem Aufbau. Genau deshalb werden sie
hier nicht uebernommen, sondern nachgemessen -- eine Fremdzahl, die zur
eigenen Vorgabe erhoben wird, ist geraten mit Fussnote.

Dazu passt ein eigener Befund von heute (S12): ein GROESSERER Kandidatenpool
senkte die Trefferzahl (7/35 -> 6/35). Ich habe das als Sortierfehler gelesen
und den Sortierschluessel testweise entfernt -- ohne Wirkung. Bleibt die
zweite Erklaerung: nicht die Auswahl war schuld, sondern die Menge.

WAS GEMESSEN WIRD: fuer jedes Deckelpaar (MAX_NODES, MAX_LESSONS) die
Zieltrefferquote (abrufguete) und die ausgelieferte Zeichenmenge
(liefermenge), am selben Korpus, im selben Prozess.

WAS NICHT GEMESSEN WIRD, und das ist die ehrliche Grenze: ob ein Modell mit
mehr Kontext SCHLECHTER ANTWORTET. Lost-in-the-Middle ist eine Aussage ueber
die Antwort, nicht ueber den Abruf. Diese Reihe kann nur zeigen, ob mehr
Deckel mehr Zieltreffer bringt und was er kostet. Faende sich Saettigung --
Treffer steigen nicht mehr, Zeichen schon --, waere jeder weitere Deckel
reiner Preis. Das ist die Frage, die hier beantwortbar ist.

Die Deckel sind Modulkonstanten, keine Umgebungsvariablen. Sie werden hier
zur Laufzeit gesetzt und danach zurueckgestellt; die Produktionsdatei bleibt
unangetastet.

Aufruf:
    python3 deckelreihe.py
    python3 deckelreihe.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER / "haken"))
sys.path.insert(0, str(HIER / "kern"))

import abrufguete  # noqa: E402
import knowledge_recall_hook as rh  # noqa: E402
import liefermenge  # noqa: E402
import ort
import speicher  # noqa: E402

# Die Reihe. 3/2 ist der Ist-Stand, 7/5 liegt bei der Fremdzahl (12 gesamt
# waere deren "sieben je Entitaet" nicht vergleichbar -- unser Deckel gilt je
# ABRUF, nicht je Entitaet; darum wird die Reihe breit gefahren statt auf
# einen fremden Punkt gezielt).
REIHE = [(3, 2), (5, 3), (7, 5), (10, 7), (15, 10)]


def _mit_deckel(nodes: int, lessons: int, faelle: list, conn: sqlite3.Connection) -> dict:
    """Setzt die Deckel, misst, stellt zurueck. Rueckgabe ist eine Zeile."""
    alt_n, alt_l = rh.MAX_NODES, rh.MAX_LESSONS
    try:
        rh.MAX_NODES, rh.MAX_LESSONS = nodes, lessons
        guete = abrufguete.messe(faelle, conn)
        menge = liefermenge.messe_liefermenge(faelle)
    finally:
        rh.MAX_NODES, rh.MAX_LESSONS = alt_n, alt_l
    return {"max_nodes": nodes, "max_lessons": lessons, "guete": guete, "menge": menge}


def _zahl(d: dict, *pfad, vorgabe=None):
    """Greift verschachtelt zu, ohne bei fehlendem Schluessel zu sterben --
    die Rueckgabeformen von abrufguete/liefermenge sind hier NICHT
    festgeschrieben, damit diese Datei nicht bricht, wenn dort ein Feld
    umbenannt wird. Fehlt ein Wert, steht das in der Ausgabe."""
    for p in pfad:
        if not isinstance(d, dict) or p not in d:
            return vorgabe
        d = d[p]
    return d


def lauf() -> list[dict]:
    faelle = abrufguete.lade_korpus()
    # Ueber die Naht (speicher.py) statt eigener Verbindung -- dasselbe
    # mode=ro wie vorher, aber das Schliessen haengt nicht mehr an dieser Datei.
    with speicher.lesen() as conn:
        return [_mit_deckel(n, l, faelle, conn) for n, l in REIHE]


def _selftest() -> None:
    # Der eine Fall, der wirklich schiefgehen kann: die Deckel bleiben
    # verstellt. Dann misst jeder spaetere Lauf im selben Prozess falsch,
    # ohne dass irgendwo ein Fehler auftaucht -- dieselbe Signatur wie eine
    # Markierungsdatei, die den zweiten Lauf entwertet (L-871c8a).
    vorher = (rh.MAX_NODES, rh.MAX_LESSONS)

    class Krach(Exception):
        pass

    def platzt(*a, **k):
        raise Krach

    alt = abrufguete.messe
    try:
        abrufguete.messe = platzt
        try:
            _mit_deckel(9, 9, [], None)
        except Krach:
            pass
    finally:
        abrufguete.messe = alt
    assert (rh.MAX_NODES, rh.MAX_LESSONS) == vorher, \
        f"Deckel nach Ausnahme nicht zurueckgestellt: {(rh.MAX_NODES, rh.MAX_LESSONS)} statt {vorher}"

    # Negativfall: _zahl darf bei fehlendem Pfad nicht werfen.
    assert _zahl({"a": {"b": 1}}, "a", "b") == 1
    assert _zahl({"a": {}}, "a", "b", vorgabe="fehlt") == "fehlt"
    assert _zahl({}, "x", vorgabe=None) is None

    # Die Reihe muss aufsteigend sein, sonst ist "Saettigung" nicht ablesbar.
    assert REIHE == sorted(REIHE), "die Reihe muss aufsteigend sein"
    assert REIHE[0] == (rh.MAX_NODES, rh.MAX_LESSONS), \
        "der erste Punkt der Reihe muss der Ist-Stand sein, sonst fehlt die Nulllinie"

    print("selftest ok (6 Faelle)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--json", type=Path, default=None, help="Ergebnis zusaetzlich als JSON ablegen")
    a = p.parse_args()
    if a.selftest:
        _selftest()
        return

    zeilen = lauf()
    # abrufguete.messe() liefert je Art ein Paar [treffer, gesamt]; die
    # Gesamtquote ist deren Summe, NICHT ein eigenes Feld. Beim ersten Lauf
    # habe ich hier "treffer"/"gesamt" geraten und fuenf Zeilen "?/?"
    # gedruckt -- die Zahlen lagen die ganze Zeit im JSON.
    print(f"{'Deckel':>7} {'LESSON':>8} {'NODE':>8} {'gesamt':>9} {'Zeichen':>9} {'max':>8}")
    for z in zeilen:
        g, m = z["guete"], z["menge"]
        L, N = g["LESSON"], g["NODE"]
        deckel = f"{z['max_nodes']}/{z['max_lessons']}"
        print(f"{deckel:>7} {f'{L[0]}/{L[1]}':>8} {f'{N[0]}/{N[1]}':>8} "
              f"{f'{L[0] + N[0]}/{L[1] + N[1]}':>9} "
              f"{m['avg_zeichen']:>9.0f} {m['max_zeichen']:>8.0f}")

    if a.json:
        a.json.write_text(json.dumps(zeilen, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\ngeschrieben: {a.json}")
    print("\nGrenze dieser Messung: sie zeigt Abruf, nicht Antwortqualitaet. "
          "Steigen die Zeichen und die Treffer nicht mehr, ist der Rest Preis.")


if __name__ == "__main__":
    main()
