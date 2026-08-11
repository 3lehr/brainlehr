#!/usr/bin/env python3
"""Welche Lehre gehoert in den Codepfad, welche bleibt im Nachschlagewerk?

ANLASS (Recherche 2026-08-11, Pruefspruch #5, belegt): Die SEC hat zu Rule
15c3-5 ausdruecklich festgestellt, dass menschliche Ueberwachung in Echtzeit
NICHT genuegt -- die Pruefung muss automatisiert vor der Handlung laufen. Unter
Zeitdruck liest niemand nach. Wissen wirkt nur, wenn es VORHER in eine
ausfuehrbare Kontrolle uebersetzt wurde.

Daraus die Sortierregel, die hier bisher fehlte: eine Lehre mit hohem Schaden
gehoert nicht in den durchsuchbaren Speicher, sondern als Bedingung in den
Codepfad. Der Speicher behaelt den Rest -- Zusammenhang, Begruendung, Historie.
Bisher landete beides im selben Topf, und deshalb sah die Abruffrage aus wie
das ganze Problem.

DER MASSSTAB, und warum er nicht "Wichtigkeit" heisst:
  schaden       severity der Lehre (critical/high/medium/low)
  haeufigkeit   occurrences -- wie oft ist es wirklich passiert
  mechanisierbar laesst sich der Verstoss als BEDINGUNG schreiben, oder braucht
                er Urteilskraft? Erkannt an der Sprache der prevention: eine
                Anweisung mit pruefbarem Gegenstand ("nie X ohne Y", "immer
                mode=ro") gegen eine Haltung ("sorgfaeltiger pruefen").

Nur die Verbindung aus allen dreien entscheidet. Eine kritische Lehre, die sich
nicht mechanisieren laesst, wird KEIN Pruefstein -- daraus wuerde eine Attrappe,
die Sicherheit vortaeuscht. Das ist die haeufigste Art, eine solche Sortierung
falsch zu bauen, und der Grund fuer die dritte Spalte.

WAS DIESES WERKZEUG NICHT TUT: Es baut keinen Pruefstein und schreibt nichts in
die Datenbank. Es sortiert und schlaegt vor -- die Bedingung fuer 'automatisch'
ist die maschinelle Abnahme, und die fehlt (dieselbe Begruendung wie in
vorschlag.py, S18).

PREIS DER ERKENNUNG, benannt statt versteckt: 'mechanisierbar' wird an Woertern
erkannt, nicht am Sinn. Eine Lehre, die ihre pruefbare Bedingung in Prosa
versteckt, faellt durch; eine, die zufaellig ein Signalwort traegt, kommt
faelschlich durch. Darum ist die Ausgabe ein VORSCHLAG mit Fundstelle, kein
Urteil -- wer ihn liest, sieht die Lehre daneben.

Aufruf:
    python3 sortierregel.py --bericht
    python3 sortierregel.py --selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "haken"))

import speicher  # noqa: E402

# Schadensgewicht. Bewusst grob: eine feinere Skala taeuscht eine Genauigkeit
# vor, die das Feld severity nicht hat (vier Stufen, von Hand gesetzt).
SCHADEN = {"critical": 3, "high": 2, "medium": 1, "low": 0}

# Sprache einer pruefbaren Bedingung. Jedes Muster stammt aus einer Lehre, die
# tatsaechlich zu einem Pruefstein geworden ist oder haette werden koennen --
# nicht aus einer Liste, die jemand fuer plausibel hielt.
_MECHANISIERBAR = re.compile(
    r"\b(nie |niemals |immer |kein |keine |nur mit |nur wenn |muss |darf nicht |"
    r"vor jedem |vor jeder |bevor |mode=ro|--\w+|=\w+|\bexit\b|\bassert\b)", re.I)
# Sprache einer Haltung: kein Gegenstand, den eine Bedingung pruefen koennte.
_HALTUNG = re.compile(
    r"\b(sorgfaelt|aufmerksam|bewusst sein|im Blick behalten|beachten, dass|"
    r"daran denken|nicht vergessen|Verstaendnis|abwaegen|Fingerspitzengefuehl)", re.I)

SCHWELLE_CODE = 3   # ab hier: gehoert in den Codepfad


def bewerten(lehre: dict) -> dict:
    """Drei Groessen, eine Empfehlung. Die Rechnung steht in der Ausgabe, damit
    sie bestreitbar ist -- eine Zahl ohne ihre Herleitung ist ein Orakel."""
    schaden = SCHADEN.get((lehre.get("severity") or "").lower(), 0)
    haeufigkeit = min(int(lehre.get("occurrences") or 1), 3)
    text = " ".join(str(lehre.get(k) or "") for k in ("prevention", "resolution"))
    mechanisierbar = bool(_MECHANISIERBAR.search(text)) and not _HALTUNG.search(text)

    punkte = schaden + (haeufigkeit - 1)
    if not mechanisierbar:
        empfehlung = "nachschlagewerk"
        grund = ("nicht als Bedingung schreibbar -- ein Pruefstein daraus waere "
                 "eine Attrappe")
    elif punkte >= SCHWELLE_CODE:
        empfehlung = "codepfad"
        grund = f"Schaden {schaden} + Wiederholung {haeufigkeit - 1} = {punkte} >= {SCHWELLE_CODE}"
    else:
        empfehlung = "nachschlagewerk"
        grund = f"Schaden {schaden} + Wiederholung {haeufigkeit - 1} = {punkte} < {SCHWELLE_CODE}"

    return {"id": lehre.get("id"), "severity": lehre.get("severity"),
            "occurrences": lehre.get("occurrences"), "mechanisierbar": mechanisierbar,
            "punkte": punkte, "empfehlung": empfehlung, "grund": grund}


def sortieren(conn) -> dict:
    zeilen = conn.execute(
        "SELECT id, type, severity, occurrences, description, resolution, prevention "
        "FROM lessons_learned WHERE status IN ('active','escalated_to_rule')").fetchall()
    bewertet = [ {**bewerten(dict(z)), "description": (z["description"] or "")[:120]}
                 for z in zeilen ]
    code = [b for b in bewertet if b["empfehlung"] == "codepfad"]
    return {
        "lehren": len(bewertet),
        "codepfad": sorted(code, key=lambda b: -b["punkte"]),
        "nachschlagewerk": len(bewertet) - len(code),
        "nicht_mechanisierbar": sum(1 for b in bewertet if not b["mechanisierbar"]),
    }


def _selftest() -> None:
    # 1) Kritisch, wiederholt, als Bedingung schreibbar -> Codepfad.
    a = bewerten({"id": "L-a", "severity": "critical", "occurrences": 3,
                   "prevention": "Nie beantworten ohne mode=ro zu setzen."})
    assert a["empfehlung"] == "codepfad", a

    # 2) Gegenprobe zur Mechanisierbarkeit: derselbe Schaden, aber Haltung
    #    statt Bedingung -> NICHT Codepfad. Ohne diesen Fall waere die dritte
    #    Spalte wirkungslos und jede kritische Lehre wuerde zum Pruefstein.
    b = bewerten({"id": "L-b", "severity": "critical", "occurrences": 3,
                   "prevention": "Sorgfaeltiger pruefen und die Lage im Blick behalten."})
    assert b["empfehlung"] == "nachschlagewerk" and not b["mechanisierbar"], b

    # 3) Gegenprobe zum Schaden: schreibbar, aber einmalig und gering.
    c = bewerten({"id": "L-c", "severity": "low", "occurrences": 1,
                   "prevention": "Immer die Datei vorher lesen."})
    assert c["empfehlung"] == "nachschlagewerk", c

    # 4) Grenzwert in beide Richtungen: genau auf der Schwelle zaehlt.
    d = bewerten({"id": "L-d", "severity": "high", "occurrences": 2,
                   "prevention": "Nie ohne --dry-run starten."})
    assert d["punkte"] == SCHWELLE_CODE and d["empfehlung"] == "codepfad", d
    e = bewerten({"id": "L-e", "severity": "high", "occurrences": 1,
                   "prevention": "Nie ohne --dry-run starten."})
    assert e["punkte"] == SCHWELLE_CODE - 1 and e["empfehlung"] == "nachschlagewerk", e

    # 5) Die Rechnung steht in der Ausgabe und ist nachvollziehbar.
    assert str(d["punkte"]) in d["grund"] and "Schaden" in d["grund"]

    print("selftest ok (5 Faelle, Gegenprobe in beide Richtungen)", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bericht", action="store_true")
    p.add_argument("--out", type=Path)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    with speicher.lesen() as conn:
        e = sortieren(conn)

    print(f"{e['lehren']} Lehren sortiert")
    print(f"  in den CODEPFAD:      {len(e['codepfad'])}")
    print(f"  ins Nachschlagewerk:  {e['nachschlagewerk']} "
          f"(davon {e['nicht_mechanisierbar']} nicht als Bedingung schreibbar)")
    print("\nDie faelligsten -- Schaden zuerst:")
    for b in e["codepfad"][:12]:
        print(f"  {b['id']} [{b['severity']}, {b['occurrences']}x, {b['punkte']} Punkte] "
              f"{b['description'][:88]}")
    if a.out:
        a.out.write_text(json.dumps(e, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nGeschrieben: {a.out}")


if __name__ == "__main__":
    main()
