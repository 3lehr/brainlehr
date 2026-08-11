#!/usr/bin/env python3
"""Ausgangsmessung S12, zweiter Anlauf -- Schritt 2
(docs/PLAN_S12_ZWEITER_ANLAUF_2026-08-11.md).

ZWECK: nicht "wie gut ist der Abruf", sondern "sind behandelt/unbehandelt
(kern/teilung_s12.py) VOR jeder Neuformulierung gleich gut". Sind sie es
nicht, ist eine spaetere Differenz wertlos und die Teilung muss neu gezogen
werden, bevor irgendein Text entsteht.

ECHTER ABRUFWEG: ruft kern/abrufguete.py::abrufen() -- exakt
rh.keywords()+rh.query() mit MIT_PROMPT, also derselbe Weg wie der Betrieb,
inklusive der eingebauten Deckel MAX_NODES=10/MAX_LESSONS=7
(haken/knowledge_recall_hook.py). Keine Kandidatenliste vor dem Deckel (L-399b9a).

EINHEIT DER MESSUNG -- Abweichung vom Auftragstext, hier vermerkt: FAKTEN
nennt "je Fall ... ein Ziel", der reale Pruefkorpus (runs/echtkorpus_...json)
hat aber Faelle mit 1 bis 10 Zielen (messungen/echtkorpus.py: 'pfad'-Faelle
hoechstens 3, 'kennung'-Faelle unbegrenzt). Ein Fall kann Ziele in BEIDEN
Haelften haben -- eine einzelne Haelfte liesse sich einem solchen Fall nicht
zuordnen. Gezaehlt wird darum je ZIEL-INSTANZ (Fall, Ziel), nicht je Fall:
Der Abruf laeuft einmal pro Fall (ein Prompt, eine Retrieval-Antwort), aber
jedes Ziel darin traegt sein eigenes Treffer/Verfehlt und seine eigene
Haelfte. Bei Faellen mit genau einem Ziel faellt das mit "je Fall" zusammen.

Aufruf:
    python3 messungen/ausgangsmessung_s12.py --out runs/ausgangsmessung_s12_<datum>.json
    python3 messungen/ausgangsmessung_s12.py --demo
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import json
from datetime import datetime, timezone, timedelta

import teilung_s12
from abrufguete import abrufen  # kern/abrufguete.py -- echter Abrufweg

WURZEL = _w
KORPUS = WURZEL / "runs" / "echtkorpus_2026-08-11T2300.json"

HAELFTEN = (teilung_s12.BEHANDELT, teilung_s12.UNBEHANDELT)
SATZARTEN = ("frage", "auftrag")


def _leere_zelle() -> dict:
    return {"treffer": 0, "gesamt": 0}


def messe(faelle: list[dict]) -> dict:
    """Ein Abruf je Fall (Prompt), Zaehlung je (Haelfte, Satzart)-Zelle ueber
    alle Ziel-Instanzen des Falls. gefunden() prueft je Art getrennt --
    ein Knotenpfad zaehlt nie als Lehrentreffer und umgekehrt."""
    zellen: dict[str, dict[str, dict]] = {
        h: {s: _leere_zelle() for s in SATZARTEN} for h in HAELFTEN
    }
    einzel = []  # Nachvollziehbarkeit je Ziel-Instanz, kein Aggregat
    for fall in faelle:
        satzart = fall.get("satzart")
        if satzart not in SATZARTEN:
            continue  # Korpus derzeit nur frage/auftrag; neue Satzart waere ein Befund
        nodes, lessons = abrufen(fall["prompt"])
        gefundene_knoten = {n["path"] for n in nodes}
        gefundene_lehren = {l["id"] for l in lessons}
        for ziel in fall.get("ziele", []):
            art, id_ = ziel["art"], ziel["id"]
            if art == "knoten":
                treffer = id_ in gefundene_knoten
            elif art == "lehre":
                treffer = id_ in gefundene_lehren
            else:
                continue  # unbekannte Art -- kein Ziel, das dieser Abruf je liefern koennte
            halb = teilung_s12.haelfte(art, id_)
            zelle = zellen[halb][satzart]
            zelle["gesamt"] += 1
            if treffer:
                zelle["treffer"] += 1
            einzel.append({"art": art, "id": id_, "haelfte": halb,
                            "satzart": satzart, "treffer": treffer})
    return {"zellen": zellen, "einzel": einzel}


def _summe_je_haelfte(zellen: dict) -> dict:
    out = {}
    for h in HAELFTEN:
        treffer = sum(zellen[h][s]["treffer"] for s in SATZARTEN)
        gesamt = sum(zellen[h][s]["gesamt"] for s in SATZARTEN)
        out[h] = {"treffer": treffer, "gesamt": gesamt,
                   "quote": round(treffer / gesamt, 4) if gesamt else None}
    return out


def vergleichbar(zellen: dict, toleranz: float = 0.10) -> tuple[bool, str]:
    """Sind behandelt/unbehandelt VOR der Behandlung gleich gut? Masstab:
    Trefferquote je Haelfte (ueber beide Satzarten summiert, da 'frage' mit
    6 Faellen je Haelfte zu duenn fuer eine eigene Aussage ist) innerhalb
    +/-10 Prozentpunkte. Kein Signifikanztest -- bei ~35-40 Ziel-Instanzen
    je Haelfte waere ein p-Wert Show, keine Erkenntnis; die Toleranz ist
    eine bewusste, benannte Faustregel, keine Berechnung."""
    s = _summe_je_haelfte(zellen)
    qa, qb = s[teilung_s12.BEHANDELT]["quote"], s[teilung_s12.UNBEHANDELT]["quote"]
    if qa is None or qb is None:
        return False, "mindestens eine Haelfte hat 0 Ziel-Instanzen -- nicht beurteilbar"
    diff = abs(qa - qb)
    ok = diff <= toleranz
    text = (f"Quote {teilung_s12.BEHANDELT}={qa:.4f} vs {teilung_s12.UNBEHANDELT}={qb:.4f}, "
            f"Differenz={diff:.4f} (Toleranz {toleranz})")
    return ok, text


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--korpus", type=_Path, default=KORPUS)
    p.add_argument("--out", type=_Path, default=None)
    a = p.parse_args()

    faelle = json.loads(a.korpus.read_text(encoding="utf-8"))["faelle"]
    ergebnis = messe(faelle)
    zellen = ergebnis["zellen"]
    summe = _summe_je_haelfte(zellen)
    ok, begruendung = vergleichbar(zellen)

    print(f"Faelle im Korpus: {len(faelle)}  ({a.korpus.name})")
    print(f"{'Haelfte':14s}{'Satzart':10s}{'Treffer/Gesamt':>16s}")
    for h in HAELFTEN:
        for s in SATZARTEN:
            z = zellen[h][s]
            print(f"{h:14s}{s:10s}{z['treffer']:>10d}/{z['gesamt']:<5d}")
        print(f"{h:14s}{'GESAMT':10s}{summe[h]['treffer']:>10d}/{summe[h]['gesamt']:<5d}"
              f"  Quote={summe[h]['quote']}")
    print(f"\nVergleichbar (Faustregel +/-10 Punkte): {'JA' if ok else 'NEIN'} -- {begruendung}")

    tz = timezone(timedelta(hours=2))
    ausgabe = {
        "zweck": "Ausgangsmessung VOR jeder Neuformulierung -- prueft Vergleichbarkeit "
                 "der Haelften, nicht die Abrufguete selbst.",
        "verfahren": "echter Abrufweg (kern/abrufguete.py::abrufen() -> "
                     "knowledge_recall_hook.keywords()+query(), MIT_PROMPT=1, "
                     "Deckel MAX_NODES=10/MAX_LESSONS=7 eingebaut, kein Zwischenschritt "
                     "vor dem Deckel gemessen (L-399b9a).",
        "teilung": "kern/teilung_s12.py::haelfte(), festgeschrieben in "
                   "runs/teilung_s12_2026-08-11.json",
        "einheit": "Ziel-Instanz (Fall, Ziel) -- Begruendung im Modulkopf dieser Datei; "
                   "Abweichung vom Auftragstext 'je Fall ein Ziel', siehe Bericht.",
        "versuche": 1,
        "erzeugt_am": datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S%z"),
        "korpus": a.korpus.name,
        "faelle_im_korpus": len(faelle),
        "zellen": zellen,
        "summe_je_haelfte": summe,
        "vergleichbar": ok,
        "vergleichbar_begruendung": begruendung,
        "einzel": ergebnis["einzel"],
    }
    if a.out:
        a.out.write_text(json.dumps(ausgabe, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\ngeschrieben: {a.out}")


def demo() -> None:
    """Netzloser Selbsttest ohne DB-Zugriff: messe() mit einem gefaelschten
    abrufen(), das feste Treffer liefert -- belegt Zellenzuordnung je
    (Haelfte, Satzart) und die Mehrfach-Ziel-Behandlung eines Falls."""
    import teilung_s12 as t

    k1, k2 = "/demo/eins", "/demo/zwei"
    h1 = t.haelfte("knoten", k1)

    faelle = [
        {"prompt": "p1", "satzart": "auftrag",
         "ziele": [{"art": "knoten", "id": k1}]},
        {"prompt": "p2", "satzart": "frage",
         "ziele": [{"art": "knoten", "id": k2}, {"art": "lehre", "id": "L-demo"}]},
        {"prompt": "p3", "satzart": "sonstiges",  # muss ignoriert werden
         "ziele": [{"art": "knoten", "id": k1}]},
    ]

    global abrufen
    orig = abrufen

    def fake_abrufen(prompt):
        if prompt == "p1":
            return [{"path": k1}], []
        if prompt == "p2":
            return [{"path": k2}], []  # L-demo NICHT gefunden
        return [], []

    abrufen = fake_abrufen  # ersetzt den Modul-Namen, den messe() aufruft
    try:
        erg = messe(faelle)
    finally:
        abrufen = orig

    zellen = erg["zellen"]
    assert zellen[h1]["auftrag"] == {"treffer": 1, "gesamt": 1}, zellen[h1]["auftrag"]
    # p2 hat zwei Ziele mit je eigener Haelfte (Art wirkt auf haelfte(), siehe
    # kern/teilung_s12.py), darum ueber Summen pruefen statt ueber eine
    # Einzelzelle -- welche Haelfte k2/L-demo im Detail treffen ist fuer
    # diesen Test irrelevant, nur DASS beide gezaehlt werden:
    gesamt_frage = sum(zellen[h]["frage"]["gesamt"] for h in HAELFTEN)
    treffer_frage = sum(zellen[h]["frage"]["treffer"] for h in HAELFTEN)
    assert gesamt_frage == 2, gesamt_frage  # k2 + L-demo
    assert treffer_frage == 1, treffer_frage  # nur k2 gefunden, L-demo nicht
    # dritter Fall (satzart 'sonstiges') taucht in keiner Zelle auf:
    gesamt_ziele = sum(zellen[h][s]["gesamt"] for h in HAELFTEN for s in SATZARTEN)
    assert gesamt_ziele == 3, gesamt_ziele  # k1 + k2 + L-demo, NICHT der dritte Fall
    print("demo ok (3 Faelle synthetisch: Zellenzuordnung, Mehrfachziel, "
          "unbekannte Satzart uebersprungen)")


if __name__ == "__main__":
    if "--demo" in _sys.argv:
        demo()
    else:
        main()
