#!/usr/bin/env python3
"""Teilung des Bestands in behandelt/unbehandelt -- S12, zweiter Anlauf
(docs/PLAN_S12_ZWEITER_ANLAUF_2026-08-11.md, Schritt 1).

Bindend, bevor irgendein Text entsteht: eine Haelfte wird spaeter neu
formuliert, die andere nicht. Damit niemand die Trennung spaeter still
anders zieht, ist sie hier als REINE FUNKTION DER KENNUNG festgeschrieben --
kein Zufallsgenerator mit Startwert, den spaeter niemand kennt, und keine
gespeicherte Liste, die veralten oder verloren gehen kann. Wer dieselbe
(art, id) hineingibt, bekommt zu jedem Zeitpunkt dieselbe Haelfte heraus --
das IST die Festschreibung, nicht eine Datei unter runs/.

Getrennt je Art gezogen (Knoten fuer sich, Lehren fuer sich): sha256 ueber
"art:id" ist nicht dasselbe wie sha256 ueber "id" allein, darum faerbt eine
gemeinsame Ziehung nicht zufaellig alle Lehren in eine Haelfte -- geprueft
in demo().
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import hashlib
import sqlite3

WURZEL = _w

BEHANDELT = "behandelt"
UNBEHANDELT = "unbehandelt"


def haelfte(art: str, id_: str) -> str:
    """art in {'knoten', 'lehre'} (Schreibweise wie im Pruefkorpus,
    runs/echtkorpus_2026-08-11T2300.json). Deterministisch, ohne Seed:
    unteres Bit von sha256('art:id')."""
    digest = hashlib.sha256(f"{art}:{id_}".encode("utf-8")).hexdigest()
    return BEHANDELT if int(digest[:8], 16) % 2 == 0 else UNBEHANDELT


def bestand(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """Der volle Bestand (nicht der Auslieferungs-Deckel): alle Knoten ausser
    zurueckgezogenen, alle Lehren ausser aufgeloesten. Deckel (10/7) und
    Gattungsfilter greifen erst beim ABRUF, nicht bei der Teilung -- die
    Teilung betrifft den Bestand, aus dem geliefert werden koennte."""
    knoten = [r[0] for r in conn.execute(
        "SELECT path FROM knowledge_nodes WHERE zurueckgezogen = 0")]
    lehren = [r[0] for r in conn.execute(
        "SELECT id FROM lessons_learned WHERE status != 'resolved'")]
    return {"knoten": knoten, "lehre": lehren}


def zaehlen(conn: sqlite3.Connection) -> dict:
    b = bestand(conn)
    ergebnis = {}
    for art, ids in b.items():
        beh = sum(1 for i in ids if haelfte(art, i) == BEHANDELT)
        ergebnis[art] = {"gesamt": len(ids), BEHANDELT: beh,
                          UNBEHANDELT: len(ids) - beh}
    return ergebnis


def demo() -> None:
    """Netzloser Selbsttest, ersetzt tests/ (dort haelt gerade eine andere
    Sitzung einen neuen Test in Arbeit -- Datei tabu laut Auftrag)."""
    # 1) Reproduzierbar: zweimal ziehen, gleiches Ergebnis.
    assert haelfte("knoten", "/x/y") == haelfte("knoten", "/x/y")
    assert haelfte("lehre", "L-abc123") == haelfte("lehre", "L-abc123")

    # 2) Beide Haelften existieren ueberhaupt (kein Konstant-Bug).
    beispiele_knoten = [f"/x/{i}" for i in range(200)]
    werte = {haelfte("knoten", k) for k in beispiele_knoten}
    assert werte == {BEHANDELT, UNBEHANDELT}, werte

    # 3) Art wirkt: dieselbe Kennung als Knoten und als Lehre kann in
    #    verschiedene Haelften fallen (sonst faerbte die Art ihr Ergebnis
    #    nicht selbststaendig -- Praefix "art:" nimmt daran teil).
    unterschiedlich = any(
        haelfte("knoten", str(i)) != haelfte("lehre", str(i))
        for i in range(50)
    )
    assert unterschiedlich

    # 4) Reale DB, falls vorhanden: beide Haelften enthalten beide Arten.
    db = WURZEL / "brainlehr.db"
    if db.exists() and db.stat().st_size > 0:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        z = zaehlen(conn)
        conn.close()
        for art, z_art in z.items():
            assert z_art[BEHANDELT] > 0 and z_art[UNBEHANDELT] > 0, (art, z_art)
        print(f"demo ok (4 Faelle, reale DB: {z})")
    else:
        print("demo ok (4 Faelle, reale DB uebersprungen -- brainlehr.db leer/fehlt)")


if __name__ == "__main__":
    import argparse
    import json as _json

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zaehlen", action="store_true", help="Verteilung auf der realen DB ausgeben")
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()

    if a.demo:
        demo()
    elif a.zaehlen:
        conn = sqlite3.connect(f"file:{WURZEL / 'brainlehr.db'}?mode=ro", uri=True)
        print(_json.dumps(zaehlen(conn), ensure_ascii=False, indent=2))
        conn.close()
    else:
        demo()
