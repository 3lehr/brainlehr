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

import codestand
import teilung_s12
import zeitmarke
from abrufguete import abrufen  # kern/abrufguete.py -- echter Abrufweg

WURZEL = _w
KORPUS = WURZEL / "runs" / "echtkorpus_2026-08-11T2300.json"

HAELFTEN = (teilung_s12.BEHANDELT, teilung_s12.UNBEHANDELT)
SATZARTEN = ("frage", "auftrag")


def _leere_zelle() -> dict:
    return {"treffer": 0, "gesamt": 0}


def messe(faelle: list[dict], conn) -> dict:
    """Ein Abruf je Fall (Prompt), Zaehlung je (Haelfte, Satzart)-Zelle ueber
    alle Ziel-Instanzen des Falls. gefunden() prueft je Art getrennt --
    ein Knotenpfad zaehlt nie als Lehrentreffer und umgekehrt.

    Der Korpus traegt fuer Knotenziele einen PFAD als 'id' (siehe
    messungen/echtkorpus.py), teilung_s12.haelfte() teilt aber ueber die
    knowledge_nodes.id (unveraenderlich, seit 655baf1 -- der Pfad ist es
    nicht). Ohne Aufloesung wuerde hier eine andere, instabile Teilung
    gemessen als die, nach der spaeter behandelt wird -- dieselbe
    Fehlerklasse wie in echtkorpus.s12_bericht(), darum dieselbe Aufloesung
    (teilung_s12.id_je_pfad), nicht eine zweite."""
    zellen: dict[str, dict[str, dict]] = {
        h: {s: _leere_zelle() for s in SATZARTEN} for h in HAELFTEN
    }
    knoten_pfade = {z["id"] for f in faelle for z in f.get("ziele", []) if z["art"] == "knoten"}
    id_je_pfad = teilung_s12.id_je_pfad(conn, knoten_pfade)
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
                schluessel = id_je_pfad.get(id_)
                if schluessel is None:
                    continue  # Pfad ohne (mehr) passenden Knoten -- keine Haelfte zuweisbar
            elif art == "lehre":
                treffer = id_ in gefundene_lehren
                schluessel = id_
            else:
                continue  # unbekannte Art -- kein Ziel, das dieser Abruf je liefern koennte
            halb = teilung_s12.haelfte(art, schluessel)
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
    import speicher
    with speicher.lesen() as conn:
        ergebnis = messe(faelle, conn)
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
        "erzeugt_am": zeitmarke.jetzt(),
        "code_stand": codestand.ermitteln(WURZEL),
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
    """Netzloser Selbsttest (in-memory sqlite statt echter DB): messe() mit
    einem gefaelschten abrufen(), das feste Treffer liefert -- belegt
    Zellenzuordnung je (Haelfte, Satzart), Mehrfach-Ziel-Behandlung eines
    Falls, UND dass der Korpus-Pfad ueber knowledge_nodes.id aufgeloest wird,
    genau wie in messungen/echtkorpus.py::s12_bericht -- sonst misst diese
    Datei eine andere Teilung als kern/teilung_s12.py::haelfte() selbst
    tatsaechlich zieht (Auftrag A, 2026-08-12)."""
    import sqlite3 as _sqlite3
    import teilung_s12 as t

    k1, k2, k_verwaist = "/demo/eins", "/demo/zwei", "/demo/kein-knoten-mehr"
    id1, id2 = "nodeid-eins", "nodeid-zwei"

    conn = _sqlite3.connect(":memory:")
    conn.row_factory = _sqlite3.Row
    conn.execute("CREATE TABLE knowledge_nodes (path TEXT, id TEXT)")
    conn.execute("INSERT INTO knowledge_nodes VALUES (?, ?)", (k1, id1))
    conn.execute("INSERT INTO knowledge_nodes VALUES (?, ?)", (k2, id2))
    conn.commit()  # k_verwaist bewusst NICHT eingetragen -- Pfad ohne Knoten mehr

    # id != Pfad als sha256-Eingabe gewaehlt (nicht nur zufaellig verschieden):
    # sonst koennte ein Test, der zufaellig dieselbe Haelfte trifft, die
    # Pfad->id-Aufloesung vortaeuschen, ohne sie zu pruefen.
    h1 = t.haelfte("knoten", id1)
    assert h1 != t.haelfte("knoten", k1), (
        "Testaufbau untauglich: id und Pfad ziehen zufaellig dieselbe Haelfte -- "
        "eine falsche Aufloesung (Pfad statt id) waere hier nicht sichtbar")

    faelle = [
        {"prompt": "p1", "satzart": "auftrag",
         "ziele": [{"art": "knoten", "id": k1}]},
        {"prompt": "p2", "satzart": "frage",
         "ziele": [{"art": "knoten", "id": k2}, {"art": "lehre", "id": "L-demo"}]},
        {"prompt": "p3", "satzart": "sonstiges",  # muss ignoriert werden
         "ziele": [{"art": "knoten", "id": k1}]},
        {"prompt": "p4", "satzart": "frage",  # Pfad ohne passenden Knoten
         "ziele": [{"art": "knoten", "id": k_verwaist}]},
    ]

    global abrufen
    orig = abrufen

    def fake_abrufen(prompt):
        if prompt == "p1":
            return [{"path": k1}], []
        if prompt == "p2":
            return [{"path": k2}], []  # L-demo NICHT gefunden
        if prompt == "p4":
            return [{"path": k_verwaist}], []
        return [], []

    abrufen = fake_abrufen  # ersetzt den Modul-Namen, den messe() aufruft
    try:
        erg = messe(faelle, conn)
    finally:
        abrufen = orig
        conn.close()

    zellen = erg["zellen"]
    # h1 ist ueber die ID gezogen -- faellt der Eintrag in die andere Zelle
    # (Pfad statt id als Schluessel), schlaegt genau diese Zeile rot an.
    assert zellen[h1]["auftrag"] == {"treffer": 1, "gesamt": 1}, zellen[h1]["auftrag"]
    # p2 hat zwei Ziele mit je eigener Haelfte (Art wirkt auf haelfte(), siehe
    # kern/teilung_s12.py), darum ueber Summen pruefen statt ueber eine
    # Einzelzelle -- welche Haelfte k2/L-demo im Detail treffen ist fuer
    # diesen Test irrelevant, nur DASS beide gezaehlt werden:
    gesamt_frage = sum(zellen[h]["frage"]["gesamt"] for h in HAELFTEN)
    treffer_frage = sum(zellen[h]["frage"]["treffer"] for h in HAELFTEN)
    assert gesamt_frage == 2, gesamt_frage  # k2 + L-demo, NICHT k_verwaist
    assert treffer_frage == 1, treffer_frage  # nur k2 gefunden, L-demo nicht
    # dritter Fall (satzart 'sonstiges') taucht in keiner Zelle auf, vierter
    # (Pfad ohne Knoten) ebenfalls nicht -- keine Haelfte zuweisbar:
    gesamt_ziele = sum(zellen[h][s]["gesamt"] for h in HAELFTEN for s in SATZARTEN)
    assert gesamt_ziele == 3, gesamt_ziele  # k1 + k2 + L-demo, NICHT p3/p4
    print("demo ok (4 Faelle synthetisch: Zellenzuordnung, Mehrfachziel, "
          "unbekannte Satzart uebersprungen, Pfad->id-Aufloesung wie in "
          "echtkorpus.s12_bericht, unaufloesbarer Pfad ohne Haelfte)")


if __name__ == "__main__":
    if "--demo" in _sys.argv:
        demo()
    else:
        main()
