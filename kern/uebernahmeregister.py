#!/usr/bin/env python3
"""Uebernahmeregister -- was aus einem Bestand geerbt wurde, gilt als ungeprueft.

ANLASS: Rang-1-Weisung `73f8a1c0` (Betreiber, 2026-08-16), woertlich: „wir
sollten legacy auch als nicht getestet makieren festlegen, nicht das wir alte
fehler uebernehmen!" Jede Regel, Schwelle, Formel oder Verhaltensweise, die aus
einem Bestandsrepo in einen Neubau wandert, traegt `status: unbelegt`. Sie wird
`belegt`, sobald im Neubau ein eigener Test existiert, der gegen eine BEWUSST
FALSCHE Fassung rot war.

WARUM UEBERHAUPT EIN MECHANISMUS. Nach einem Schnitt mit Historie liegt der
geerbte Code physisch da -- mit `git log`, mit gruenen Tests, mit allem, was
Vertrauen erzeugt. Genau das ist die Falle: 4 575 gruene Tests belegen, dass
der Code tut, was jemand aufgeschrieben hat, nicht dass es richtig ist. Das
Register ist dann das einzige, was Blaupause von Werkbank trennt, und eine
Selbstverpflichtung faellt beim ersten Zeitdruck.

WARUM HIER UND NICHT IM DOMAENEN-REPO (ADR-014): Ins Tragende gehoert, was
alle gemeinsam haben ODER was keiner ueber sich selbst entscheiden darf. Ob die
geerbten Regeln einer Domaene als belegt gelten, faellt unter das Zweite -- eine
Domaene, die sich ihr eigenes Zeugnis ausstellt, ist keine Schranke. Der
MECHANISMUS liegt deshalb hier, die MARKIERUNGEN liegen im Domaenen-Repo und
reisen mit ihm (ADR-012: das Wissenspaket reist frei, das Werkzeug wird
installiert).

DREI ENTSCHEIDUNGEN, jede mit einer schlechteren Alternative:

1. KEIN VORGABEWERT. Naheliegend waere `status` mit Vorgabe `unbelegt` -- das
   waere bequem und wuerde die Frage nie stellen. Ein fehlendes Feld ist
   deshalb eine ABLEHNUNG. Wer eine Regel uebernimmt, sagt beide Male
   ausdruecklich, woher sie kommt und was sie wert ist.

2. `belegt` VERLANGT ZWEI ANGABEN, nicht eine: den Test UND die Rot-Probe. Ein
   Test allein belegt nichts -- er kann von Anfang an gruen gewesen sein, und
   genau das ist der haeufigste Fall (`L-473ba2`: 386 jsdom- und ueber 300
   pytest-Tests standen gruen neben einem Rechnungschreiben, das im Feld tot
   war). Die Rot-Probe ist der Teil, der Wirksamkeit zeigt.

3. WIDERSPRUCH WIRD GEMELDET, NICHT AUFGELOEST. Ein Vektor mit `unbelegt` und
   einem vollstaendigen Beleg koennte zweierlei heissen -- vergessen
   umzustellen, oder Beleg erfunden. Diese Datei waehlt keine der beiden
   Lesarten aus, sie sagt es. Dieselbe Haltung wie bei `kern/fundstelle.py`,
   wo `belegt`, `markierbar` und `mehrdeutig` drei getrennte Aussagen sind.

WAS HIER BEWUSST NICHT DRIN IST: kein Urteil darueber, OB ein Test gut ist --
das kann kein Skript. Geprueft wird, dass die Behauptung ihre Belege mitfuehrt,
nicht dass sie stimmt.

Aufruf:  python3 kern/uebernahmeregister.py <verzeichnis>
         python3 kern/uebernahmeregister.py <verzeichnis> --zaehle
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

HERKUENFTE = ("legacy", "neu")
ZUSTAENDE = ("unbelegt", "belegt")
BELEGFELDER = ("test", "rotprobe")


def pruefe(vektor: Any) -> str | None:
    """Gibt den Grund der Ablehnung zurueck -- oder None, wenn der Vektor
    traegt. Der Grund nennt immer das FELD, an dem es haengt, damit ein Mensch
    nicht suchen muss."""
    if not isinstance(vektor, dict):
        return "Der Vektor ist kein Datensatz."

    for feld, erlaubt in (("herkunft", HERKUENFTE), ("status", ZUSTAENDE)):
        if feld not in vektor:
            return (
                f"Pflichtfeld '{feld}' fehlt -- es gibt keinen Vorgabewert. "
                f"Erlaubt: {', '.join(erlaubt)}."
            )
        if vektor[feld] not in erlaubt:
            return f"Feld '{feld}' traegt einen unbekannten Wert. Erlaubt: {', '.join(erlaubt)}."

    beleg = vektor.get("beleg")

    if vektor["status"] == "belegt":
        if not isinstance(beleg, dict) or not beleg:
            return (
                "Status 'belegt' ohne Beleg. Erwartet wird ein Beleg mit "
                f"{' und '.join(BELEGFELDER)} -- der Test allein genuegt nicht, "
                "er koennte von Anfang an gruen gewesen sein."
            )
        for feld in BELEGFELDER:
            if not beleg.get(feld):
                return f"Der Beleg nennt kein '{feld}'. Beide Angaben sind noetig."
    elif beleg:
        return (
            "Status 'unbelegt', aber ein Beleg ist angegeben. Entweder wurde das "
            "Umstellen vergessen, oder der Beleg gehoert nicht hierher -- beides "
            "gehoert entschieden, nicht geraten."
        )
    return None


def pruefe_verzeichnis(pfad: str | Path) -> list[str]:
    """Alle *.json unter `pfad`. Ein beschaedigter Vektor ist ein BEFUND, kein
    Absturz -- sonst haelt eine kaputte Datei den ganzen Lauf an und die
    uebrigen werden nie geprueft."""
    befunde = []
    for datei in sorted(Path(pfad).glob("*.json")):
        try:
            vektor = json.loads(datei.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as fehler:
            befunde.append(f"{datei.name}: laesst sich nicht lesen ({fehler.__class__.__name__}).")
            continue
        grund = pruefe(vektor)
        if grund:
            befunde.append(f"{datei.name}: {grund}")
    return befunde


def zaehle(pfad: str | Path) -> dict[str, int]:
    """Die Zahl, die nach STAND.md gehoert.

    NUR GEPRUEFTE VEKTOREN zaehlen als `belegt` oder `unbelegt`; beanstandete
    kommen in einen eigenen Topf. Der erste Anlauf zaehlte die BEHAUPTUNG --
    ein Vektor mit `status: belegt` und fehlendem Beleg erschien als belegt,
    und genau das faellt an der Ausgabe auf, nicht am Rueckgabewert: STAND.md
    haette „1 belegt" gemeldet fuer etwas, das die Pruefung ablehnt. Eine Zahl,
    die die Schuld kleiner macht, ist schlimmer als keine -- der ganze
    Mechanismus existiert gegen diese Richtung."""
    zahlen = dict.fromkeys(("gesamt", *ZUSTAENDE, *HERKUENFTE, "beanstandet"), 0)
    for datei in sorted(Path(pfad).glob("*.json")):
        try:
            vektor = json.loads(datei.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            zahlen["beanstandet"] += 1
            continue
        zahlen["gesamt"] += 1
        if pruefe(vektor):
            zahlen["beanstandet"] += 1
            continue
        for feld in ("status", "herkunft"):
            zahlen[vektor[feld]] += 1
    return zahlen


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("verzeichnis", help="Ordner mit den Vektor-Dateien (*.json)")
    p.add_argument("--zaehle", action="store_true", help="nur die Zahlen, kein Urteil")
    a = p.parse_args(argv)

    if a.zaehle:
        zahlen = zaehle(a.verzeichnis)
        satz = (
            f"{zahlen['gesamt']} Uebernahme(n): {zahlen['unbelegt']} unbelegt, "
            f"{zahlen['belegt']} belegt ({zahlen['legacy']} aus dem Bestand, "
            f"{zahlen['neu']} neu)."
        )
        if zahlen["beanstandet"]:
            satz += f" {zahlen['beanstandet']} beanstandet, in keiner der beiden Zahlen enthalten."
        print(satz)
        return 0

    befunde = pruefe_verzeichnis(a.verzeichnis)
    if not befunde:
        zahlen = zaehle(a.verzeichnis)
        print(f"{zahlen['gesamt']} Uebernahme(n) in Ordnung, davon {zahlen['unbelegt']} unbelegt.")
        return 0

    print(f"{len(befunde)} Befund(e) im Uebernahmeregister ({a.verzeichnis}):")
    for b in befunde:
        print(f"  {b}")
    print("\nGrundlage: Rang-1-Weisung 73f8a1c0 -- Geerbtes gilt als ungeprueft.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
