#!/usr/bin/env python3
"""Meldet, wenn gebaut wird, waehrend der Plan unveraendert bleibt.

AUFTRAG: Knoten 86151b42 (Rang 1), Betreiber woertlich: „sowas darf nicht
wieder passieren, eilmeldung an brainlehrchat, der soll das regeln!"

DER FALL, der ihn ausgeloest hat, gemessen am 2026-08-16 in buckeberg: Zwischen
15:05 und 18:05 traf der Betreiber sieben Entscheidungen. Alle wurden umgesetzt,
getestet und committet. KEINE stand im Plan -- grep ueber den Plantext ergab
null Vorkommen fuer alle sieben Stichworte. Zwei davon WIDERSPRACHEN dem, was
dort stand. Aufgefallen ist es nur, weil der Betreiber selbst fragte.

WARUM DIE BESTEHENDE REGEL NICHT GRIFF: „Plan vor Umsetzung" verlangt, den Plan
fortzuschreiben. Sie hat keinen Ausloeser. Waehrend gebaut wird, fuehlt sich
jeder Schritt vollstaendig an -- die Entscheidung steht in der
Commit-Nachricht, der Test ist gruen, das Ergebnis ist sichtbar. Der Plan ist
die einzige Stelle, deren Fehlen NICHTS kaputtmacht. Genau deshalb bleibt sie
liegen.

WAS GEZAEHLT WIRD, und warum nicht alles: Nur Commits mit dem Praefix `feat`.
Eine Fehlerbehebung, eine Messung, ein Werkzeuglauf aendert keine Entscheidung
und darf nicht melden -- wer auf blosse Commit-Anzahl prueft, baut einen
Waechter, der bei jeder Aufraeumarbeit anschlaegt und binnen einer Woche
weggeklickt wird. Das ist in diesem Verbund die haeufigste Todesart eines
Waechters.

WAS ER NICHT KANN, und das gehoert dazu: Er prueft, ob eine Plandatei BERUEHRT
wurde, nicht ob das Richtige darin steht. Ein Einzeiler im Plan macht ihn
still. Er verwandelt eine unsichtbare Unterlassung in eine sichtbare
Behauptung -- mehr nicht, aber auch nicht weniger. Dieselbe Grenze wie bei
melder/ablaufpflicht.py.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def _wurzel(vorgabe: str | None = None) -> Path:
    """Das zu pruefende Repo -- des AUFRUFERS, nicht das eigene (L-b8559a-Nachbar:
    dieselbe Falle hat ablaufpflicht.py am 2026-08-16 gestellt)."""
    if vorgabe:
        return Path(vorgabe).resolve()
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True, check=False)
    return Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() \
        else Path(__file__).resolve().parents[1]


_w = _wurzel()

# Ab wie vielen feat-Commits ohne Planberuehrung gemeldet wird. Der Auftrag
# schlaegt 3 vor und verlangt, die Zahl zu MESSEN. Gemessen am Ausloesefall
# (buckeberg, 2026-08-16, 15:05 bis 18:05): 11 feat-Commits, null
# Planberuehrungen -- die Schwelle 3 haette also mit deutlichem Abstand
# angeschlagen, und zwar bereits nach gut einer Stunde.
SCHWELLE = 3

# Was als Plan zaehlt: Plandokumente und ADRs. Beide tragen Entscheidungen;
# ein STAND.md tut es NICHT -- dort steht die Lage, nicht der Beschluss.
PLAN = re.compile(r"^docs/(PLAN_[\w.-]+\.md|adr/ADR-[\w.-]+\.md)$", re.I)

# Nur diese Commits tragen Entscheidungen. `fix`, `chore`, `docs`, `test`,
# `refactor` und `messen` aendern keine.
ENTSCHEIDUNG = re.compile(r"^feat[(:]", re.I)


def _lauf(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=_w, capture_output=True,
                          text=True, check=False).stdout


def _bereich_aufloesen(bereich: str) -> str:
    """`@{u}..HEAD` ohne Upstream ist die leere Menge, nicht 'alles sauber'.
    Dieselbe Korrektur wie in ablaufpflicht.py, aus demselben Befund."""
    if "@{u}" not in bereich:
        return bereich
    r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "@{u}"], cwd=_w,
                       capture_output=True, text=True, check=False)
    return bereich if r.returncode == 0 else "HEAD"


def erhebe(bereich: str = "@{u}..HEAD", seit: str | None = None,
           bis: str | None = None) -> dict:
    """Zaehlt Entscheidungs-Commits und Planberuehrungen im Bereich."""
    args = ["log", "--format=%H\t%s", "--name-only", _bereich_aufloesen(bereich)]
    if seit:
        args.append(f"--since={seit}")
    if bis:
        args.append(f"--until={bis}")
    roh = _lauf(*args)

    feats, plaene, betroffen = [], set(), []
    sha = betreff = None
    for zeile in roh.splitlines():
        if "\t" in zeile and len(zeile.split("\t", 1)[0]) == 40:
            sha, betreff = zeile.split("\t", 1)
            if ENTSCHEIDUNG.search(betreff):
                feats.append((sha, betreff))
            continue
        if zeile.strip() and PLAN.match(zeile.strip()):
            plaene.add(zeile.strip())
            betroffen.append(sha)
    return {"entscheidungen": feats, "planberuehrungen": sorted(plaene),
            "plan_commits": [s for s in betroffen if s]}


def befund(erhebung: dict) -> str | None:
    """Der Meldesatz, oder None wenn nichts zu melden ist."""
    n = len(erhebung["entscheidungen"])
    if n < SCHWELLE or erhebung["planberuehrungen"]:
        return None
    beispiele = "\n".join(f"    {s[:8]} {b[:64]}" for s, b in erhebung["entscheidungen"][:4])
    weitere = f"\n    … und {n - 4} weitere" if n > 4 else ""
    return (
        f"{n} Entscheidungs-Commits (feat), aber KEINE Plandatei berührt.\n"
        f"{beispiele}{weitere}\n\n"
        f"Welche Entscheidung der letzten Stunden steht nur in einer "
        f"Commit-Nachricht? Eine Commit-Nachricht ist ein Beleg für eine "
        f"Änderung, kein Ort für eine Entscheidung — sie wird nach Datei "
        f"gelesen, nicht nach Thema, und niemand sucht dort nach dem Warum.\n"
        f"Widerspricht die Entscheidung dem Plan, gehört die alte Stelle "
        f"BERICHTIGT, nicht nur ergänzt."
    )


def demo() -> None:
    """Netzloser Selbsttest: beide Richtungen und die Grenzwerte."""
    def e(feat_n, plaene):
        return {"entscheidungen": [(f"{i:040d}", f"feat(x): nr {i}") for i in range(feat_n)],
                "planberuehrungen": plaene, "plan_commits": []}

    assert ENTSCHEIDUNG.search("feat(kern): etwas")
    assert ENTSCHEIDUNG.search("feat: etwas")
    for still in ("fix(kern): etwas", "chore(karten): nachgezogen",
                  "docs(stand): Lage", "messen(x): Zahl", "refactor(y): Umbau"):
        assert not ENTSCHEIDUNG.search(still), still

    assert PLAN.match("docs/PLAN_TEILC_2026-08-16.md")
    assert PLAN.match("docs/adr/ADR-023-schalter.md")
    assert not PLAN.match("STAND.md"), "STAND traegt die Lage, nicht den Beschluss"
    assert not PLAN.match("docs/FORTSCHRITT_X.md")

    # Grenzwert an der Schwelle: 2 still, 3 meldet.
    assert befund(e(SCHWELLE - 1, [])) is None
    m = befund(e(SCHWELLE, []))
    assert m and "KEINE Plandatei" in m, m

    # Negativfall, die wichtigere Richtung: Plan BERUEHRT -> still, egal wie
    # viele feat-Commits. Ohne diese Zeile saehe ein Waechter, der immer
    # meldet, genauso gruen aus.
    assert befund(e(99, ["docs/PLAN_X.md"])) is None

    # Aufraeumarbeit allein meldet nie -- die haeufigste Todesart eines
    # Waechters ist, bei jeder Kleinigkeit anzuschlagen.
    assert befund(e(0, [])) is None
    print("demo: ok", file=sys.stderr)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("bereich", nargs="?", default="@{u}..HEAD")
    p.add_argument("--wurzel", default=None)
    p.add_argument("--seit", default=None, help="nur Commits ab diesem Zeitpunkt")
    p.add_argument("--bis", default=None)
    p.add_argument("--still", action="store_true")
    a = p.parse_args()
    global _w
    _w = _wurzel(a.wurzel)
    try:
        erhebung = erhebe(a.bereich, a.seit, a.bis)
    except Exception as ex:
        if not a.still:
            print(f"Planberührung nicht prüfbar ({ex}) — übersprungen.", file=sys.stderr)
        return 0
    satz = befund(erhebung)
    if not satz:
        if not a.still:
            n, p_ = len(erhebung["entscheidungen"]), len(erhebung["planberuehrungen"])
            print(f"In Ordnung: {n} Entscheidungs-Commits, {p_} Plandatei(en) berührt.")
        return 0
    if not a.still:
        print(satz, file=sys.stderr)
    return 1


if __name__ == "__main__":
    demo()
    raise SystemExit(main())
