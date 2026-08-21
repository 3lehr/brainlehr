#!/usr/bin/env python3
"""Meldet, wenn Code entsteht, ohne dass der Plan mitwaechst.

DER ANLASS ist ein Knoten mit Rang 1 vom 2026-08-16
(/methodik/direktiven/dringend-an-brainlehr): "Sieben Betreiberentscheidungen
wurden umgesetzt, committet und gebaut -- aber nie in den Plan geschrieben.
Gemessen: null Vorkommen im Plantext. Aufgefallen nur, weil der Betreiber
selbst fragte."

Der Knoten verlangt woertlich "einen Waechter, keinen Vorsatz". Gemessen am
2026-08-20, vier Tage spaeter: Es gab keinen. Die Forderung war eine Absicht
geblieben -- also genau das, wovor sie warnt.

WARUM MELDER UND NICHT WAECHTER, also Hinweis statt Veto: Nicht jeder Commit
gehoert in einen Plan. Ein Tippfehler, eine Umbenennung, ein Formatlauf --
wer die blockiert, wird umgangen, und dann wirkt gar nichts mehr. Dieser
Melder nennt das VERHAELTNIS und die Commits namentlich; entscheiden muss ein
Mensch.

DER NENNER IST DIE GEPRUEFTE MENGE, nicht die Befundliste (Norm 17b14a32).
Reine Dokumentationscommits zaehlen gar nicht mit -- sie setzen keine
Entscheidung um, und wer sie mitzaehlt, misst Fleiss statt Disziplin. Ohne
diese Trennung sinkt die Quote an jedem Schreibtag von selbst.

ZWEITE FRAGE (2026-08-21, gleicher Bau): Nennt eine Commit-Nachricht eine
Betreiberentscheidung, ohne dass docs/REQUIREMENTS_BRAINLEHR.md mitwaechst?
Anlass war Commit 6c464372 -- der Katalog hatte 71 Zeilen registriert, waehrend
fuenf Zeilen (BDW-P15 bis P19) ohne Eintrag in tests/test_requirements_
brainlehr.py entstanden waren. Auch hier gilt Norm 17b14a32: Nenner ist die
Menge der Commits mit Entscheidungswort, nicht alle Commits -- sonst sinkt die
Quote mit jedem Commit, der von etwas anderem handelt.

Aufruf:
    python3 melder/planmitschrieb.py            # letzte 20 Commits
    python3 melder/planmitschrieb.py --anzahl 50
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Was als "Code" gilt -- eine Aenderung hier setzt in der Regel eine
# Entscheidung um und gehoert in einen Plan.
CODE = (".py", ".sql", ".sh", ".swift", ".dart", ".ts", ".js", ".yml", ".yaml")
# Was als Plan gilt. Bewusst weit: auch eine ADR ist eine festgehaltene
# Entscheidung.
PLAN = ("docs/PLAN_", "docs/adr/", "docs/SPRINTS")


def _ist_code(p: str) -> bool:
    return p.endswith(CODE) and not p.startswith(("tests/",))


def _ist_plan(p: str) -> bool:
    return any(p.startswith(x) for x in PLAN)


FENSTER = 3   # Nachbarcommits, in denen ein Plan mitzaehlt -- ungemessen


def pruefe(commits: list, fenster: int = FENSTER) -> dict:
    """[{hash, dateien}] -> Lage. Nur Commits MIT Code kommen in den Nenner.

    DAS FENSTER IST DER KERN, und es ist der Fehler meines ersten Entwurfs:
    Der mass, ob Code und Plan im SELBEN Commit stehen -- und meldete daraufhin
    13 von 13, obwohl der Plan am selben Tag fuenfmal fortgeschrieben worden
    war, nur in eigenen Commits. Code und Plan getrennt zu committen ist
    SAUBERER (ein Sammelcommit laesst sich nicht einzeln zuruecknehmen), und
    der Melder haette genau die bestraft, die ordentlich trennen.

    Gefragt ist also nicht der Commit, sondern das Zeitfenster: Gab es RUND UM
    diesen Code eine Planaenderung?"""
    hat_plan = [any(_ist_plan(d) for d in (c.get("dateien") or [])) for c in commits]
    ohne, mit = [], []
    for i, c in enumerate(commits):
        dateien = c.get("dateien") or []
        if not any(_ist_code(d) for d in dateien):
            continue                      # kein Code -> gehoert nicht in den Nenner
        nahe = any(hat_plan[max(0, i - fenster):i + fenster + 1])
        (mit if nahe else ohne).append(c["hash"])
    return {"geprueft": len(ohne) + len(mit), "ohne_plan": len(ohne),
            "mit_plan": len(mit), "hashes": ohne}


def als_text(lage: dict) -> str:
    if not lage["ohne_plan"]:
        return ""
    q = lage["ohne_plan"] / max(lage["geprueft"], 1) * 100
    z = [f"⚠ {lage['ohne_plan']} von {lage['geprueft']} Code-Commits ohne "
         f"Planfortschreibung ({q:.0f} %):",
         "  " + " ".join(lage["hashes"][:12]),
         "  Nicht jeder Commit gehoert in einen Plan -- aber sieben "
         "Betreiberentscheidungen",
         "  sind schon einmal genau so verschwunden (Knoten "
         "/methodik/direktiven/dringend-an-brainlehr)."]
    return "\n".join(z)


def _letzte(anzahl: int) -> list:
    aus = subprocess.run(
        ["git", "log", f"-{anzahl}", "--format=%h", "--name-only"],
        cwd=REPO, capture_output=True, text=True).stdout
    commits, aktuell = [], None
    for zeile in aus.splitlines():
        if not zeile.strip():
            continue
        if aktuell is None or (len(zeile) <= 12 and " " not in zeile and "/" not in zeile):
            aktuell = {"hash": zeile.strip(), "dateien": []}
            commits.append(aktuell)
        else:
            aktuell["dateien"].append(zeile.strip())
    return commits


# --- Katalogmitschrieb: Betreiberentscheidung ohne Katalogzeile ------------

KATALOG = "docs/REQUIREMENTS_BRAINLEHR.md"
# Woertlich die vier Formen aus dem Auftrag. "Betreiberfreigabe" ist im
# Hausgebrauch belegt (git log, z.B. Commit 3ff9e98a), gehoert aber NICHT
# zum Auftrag und wird bewusst nicht stillschweigend ergaenzt, sondern hier
# nur vermerkt -- eine Freigabe ist keine neue Entscheidung, sondern die
# Bestaetigung einer vorgelegten.
ENTSCHEIDUNGSWORT = re.compile(
    r"betreiber(entscheidung|wort|weisung|direktive)", re.IGNORECASE)


def _ist_katalog(p: str) -> bool:
    return p == KATALOG


def pruefe_katalog(commits: list) -> dict:
    """[{hash, nachricht, dateien}] -> Lage. Nenner sind Commits, deren
    Nachricht ein Entscheidungswort traegt -- nicht alle Commits (17b14a32)."""
    geprueft, befunde = [], []
    for c in commits:
        if not ENTSCHEIDUNGSWORT.search(c.get("nachricht") or ""):
            continue
        geprueft.append(c["hash"])
        if not any(_ist_katalog(d) for d in (c.get("dateien") or [])):
            befunde.append(c["hash"])
    return {"geprueft": len(geprueft), "befunde": len(befunde), "hashes": befunde}


def als_text_katalog(lage: dict) -> str:
    if not lage["befunde"]:
        return ""
    q = lage["befunde"] / max(lage["geprueft"], 1) * 100
    return "\n".join([
        f"⚠ {lage['befunde']} von {lage['geprueft']} Commits mit "
        f"Entscheidungswort ohne Katalogzeile ({q:.0f} %):",
        "  " + " ".join(lage["hashes"][:12]),
        f"  Nennt die Nachricht eine Betreiberentscheidung, gehoert sie in "
        f"{KATALOG} -- Commit 6c464372 ist das Beispiel, an dem das fehlte.",
    ])


def _letzte_mit_nachricht(anzahl: int) -> list:
    trenner, ende = "\x1f", "\x1e"
    aus = subprocess.run(
        ["git", "log", f"-{anzahl}", f"--format=%h{trenner}%B{ende}"],
        cwd=REPO, capture_output=True, text=True).stdout
    nachrichten = {}
    for satz in aus.split(ende):
        satz = satz.strip("\n")
        if not satz.strip():
            continue
        h, _, msg = satz.partition(trenner)
        nachrichten[h.strip()] = msg
    commits = _letzte(anzahl)
    for c in commits:
        c["nachricht"] = nachrichten.get(c["hash"], "")
    return commits


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--anzahl", type=int, default=20)
    args = p.parse_args()
    commits = _letzte_mit_nachricht(args.anzahl)
    text = als_text(pruefe(commits))
    if text:
        print(text)
    katalog_text = als_text_katalog(pruefe_katalog(commits))
    if katalog_text:
        print(katalog_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
