#!/usr/bin/env python3
"""Agenten-Auswertung — welcher Agent laeuft, welcher liegt brach.

    python3 aufsaetze/agenten.py [--tage N] [--register PFAD] [--definitionen PFAD ...]

DIES IST EIN AUFSATZ, KEIN KERN. Die Trennlinie (Dienst-Plan Abschnitt 8):
*Darf es ausfallen, ohne dass eine Aussage ihre Herkunft verliert?* Ja — also
Aufsatz. Er zeigt, er bindet nichts. Entsprechend bringt er sein eigenes
Schema nicht in knowledge_nodes unter, sondern rechnet aus vorhandenen
Stroemen, und er faellt aus, ohne etwas mitzureissen.

Die Frage des Betreibers war: welche Agenten sind wirklich hilfreich, und
welche rufen wir zu selten automatisch auf. Die zweite Haelfte ist die
interessante, und sie braucht einen NENNER — nicht "wie oft lief einer",
sondern "wie viele der definierten liefen ueberhaupt nie".

Quellen, beide mit ihren Grenzen benannt:
  hub/laufzeit/agent-register.jsonl   Start/Stop/Datei je Subagent
  .claude/agents/*.md                 was ueberhaupt definiert ist
"""
from __future__ import annotations

import argparse
import collections
import json
import time
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
VORGABE_REGISTER = WURZEL.parent / "hub" / "laufzeit" / "agent-register.jsonl"
VORGABE_DEFINITIONEN = (
    WURZEL.parent / "hub" / ".claude" / "agents",
    Path.home() / ".claude" / "agents",
)


def lies_register(pfad: Path) -> list[dict]:
    if not pfad.exists():
        return []
    zeilen = []
    for zeile in pfad.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            zeilen.append(json.loads(zeile))
        except json.JSONDecodeError:
            continue
    return zeilen


def definierte(orte) -> dict[str, Path]:
    gefunden: dict[str, Path] = {}
    for ort in orte:
        ort = Path(ort)
        if ort.is_dir():
            for d in sorted(ort.glob("*.md")):
                gefunden.setdefault(d.stem, d)
    return gefunden


def auswerten(zeilen: list[dict], tage: int | None) -> dict:
    grenze = time.time() - tage * 86400 if tage else None
    laeufe = collections.Counter()
    modelle: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    letzter: dict[str, float] = {}
    dateien = collections.Counter()
    ohne_zeit = 0
    starts = stops = 0

    for e in zeilen:
        ts = e.get("ts")
        if ts in (None, 0):
            ohne_zeit += 1
        if grenze and (not ts or ts < grenze):
            continue
        art = e.get("ev")
        typ = e.get("agent_type")
        if art == "start":
            starts += 1
            if typ:
                laeufe[typ] += 1
                if e.get("model"):
                    modelle[typ][e["model"]] += 1
                if ts:
                    letzter[typ] = max(letzter.get(typ, 0), ts)
        elif art == "stop":
            stops += 1
        elif art == "file" and typ:
            dateien[typ] += 1

    return {"laeufe": laeufe, "modelle": modelle, "letzter": letzter,
            "dateien": dateien, "ohne_zeit": ohne_zeit,
            "starts": starts, "stops": stops}


def bericht(erg: dict, def_agenten: dict[str, Path], tage: int | None) -> int:
    zeitraum = f"letzte {tage} Tage" if tage else "gesamter Bestand"
    print(f"Agenten — {zeitraum}\n")

    laeufe = erg["laeufe"]
    if not laeufe:
        print("Keine Laeufe im Register. Entweder laeuft der Register-Haken nicht,")
        print("oder es gab wirklich keine — das ist ohne den Haken nicht zu trennen.")
        return 1

    breite = max(len(t) for t in set(laeufe) | set(def_agenten))
    print(f"{'Agent':{breite}}  Laeufe  Dateien  zuletzt      Modell")
    for typ, n in laeufe.most_common():
        wann = erg["letzter"].get(typ)
        wann_s = time.strftime("%Y-%m-%d", time.localtime(wann)) if wann else "unbekannt"
        modell = erg["modelle"][typ].most_common(1)
        print(f"{typ:{breite}}  {n:6d}  {erg['dateien'][typ]:7d}  {wann_s}   "
              f"{modell[0][0] if modell else '—'}")

    nie = sorted(set(def_agenten) - set(laeufe))
    print(f"\nDefiniert: {len(def_agenten)} · gelaufen: {len(laeufe)} · "
          f"nie ausgeloest: {len(nie)}")
    if nie:
        print("Nie ausgeloest — entweder zu selten gerufen oder ueberfluessig:")
        for t in nie:
            print(f"  {t:{breite}}  {def_agenten[t].parent.name}/{def_agenten[t].name}")

    # Vorbehalte gehoeren in den Bericht, nicht in eine Fussnote: eine Zahl
    # ohne Nenner ist das, wogegen dieses Haus gebaut ist.
    print("\nVorbehalte:")
    print(f"  {erg['starts']} Starts gegen {erg['stops']} Stopps — "
          + ("ungleich, also enthaelt das Register Stopps ohne zugehoerigen Start "
             "(aeltere Rotation oder Ereignisse fremder Herkunft). Die Laufzahlen "
             "zaehlen NUR Starts." if erg["starts"] != erg["stops"] else "stimmig."))
    if erg["ohne_zeit"]:
        print(f"  {erg['ohne_zeit']} Eintrag/Eintraege ohne brauchbaren Zeitstempel — "
              f"bei Zeitraumfiltern nicht enthalten.")
    print("  'Laeufe' misst Aufrufe, nicht Nutzen. Wer daraus 'hilfreich' liest, "
          "verwechselt Haeufigkeit mit Wirkung.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tage", type=int, default=None)
    p.add_argument("--register", type=Path, default=VORGABE_REGISTER)
    p.add_argument("--definitionen", type=Path, nargs="*", default=list(VORGABE_DEFINITIONEN))
    a = p.parse_args(argv)

    zeilen = lies_register(a.register)
    if not zeilen:
        print(f"Kein Register unter {a.register}.")
        print("Der Aufsatz faellt damit aus — und nichts anderes faellt mit. "
              "Das ist die Zusicherung, die ihn zum Aufsatz macht.")
        return 1
    return bericht(auswerten(zeilen, a.tage), definierte(a.definitionen), a.tage)


if __name__ == "__main__":
    raise SystemExit(main())
