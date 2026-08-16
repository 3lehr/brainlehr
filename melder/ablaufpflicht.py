#!/usr/bin/env python3
"""Die zwei unbelegten Schritte aus docs/ablauf.json bekommen einen
Mechanismus: `Plan` und `Rot vor Gruen`.

Beide standen bis zum 2026-08-16 als Absicht da -- gefordert von Hausregeln,
durchgesetzt von niemandem. Am 2026-08-12 wurde gemessen, was das heisst: ein
Agentenauftrag ueber drei Dateien ohne Plan lief durch beide vorhandenen
Waechter, beide exit 0.

WAS HIER GEPRUEFT WIRD, UND WAS AUSDRUECKLICH NICHT:

Die Rot-Probe selbst ist maschinell NICHT verifizierbar. Ob ein Test vor der
Aenderung fehlschlug, weiss nur, wer ihn damals laufen liess. Wer das
behauptet zu pruefen, baut einen Waechter, der Vertrauen vortaeuscht.

Geprueft wird deshalb die AUSSAGE: jeder Commit, der Produktivcode aendert,
sagt, wie er belegt ist -- oder sagt ehrlich, dass er es nicht ist. Die
Hausregel nennt drei zulaessige Formulierungen fuer den zweiten Fall
("geaendert, nicht verifiziert" / "Tests gruen, aber sie deckten den Fehler
nicht ab" / "im Kopflauf belegt, am Geraet nicht"). Diese Freiheit bleibt --
was verschwindet, ist das SCHWEIGEN. Ein Commit, der zur Belegfrage gar
nichts sagt, geht nicht mehr nach aussen.

Dasselbe fuer den Plan: geprueft wird nicht, ob der Plan gut ist, sondern ob
bei einer Aenderung ueber der Planschwelle ueberhaupt einer genannt wird.

DIE SCHWELLE ist die der Hausregel, nicht selbst erfunden: mehr als eine
Datei, echte Alternativen, oder Delegation. Maschinell greifbar ist davon die
erste -- hier ab DREI geaenderten Quelldateien, damit ein Zweizeiler an zwei
Stellen nicht schon einen Plan verlangt.

WAS DIESER WAECHTER NICHT KANN, und das gehoert dazu: Er prueft Commit-TEXTE.
Wer den Satz hinschreibt, ohne die Probe gefahren zu haben, kommt durch. Er
verwandelt eine unsichtbare Unterlassung in eine sichtbare Falschaussage --
mehr nicht, aber auch nicht weniger.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

def _wurzel(vorgabe: str | None = None) -> Path:
    """Das zu pruefende Repo -- des AUFRUFERS, nicht das eigene.

    Die erste Fassung nahm `Path(__file__).parents[1]`, also immer brainlehr.
    Gemeldet von der fahrtenbuch-Sitzung am 2026-08-16, die den Waechter
    ausrollen sollte: aus fahrtenbuch_nativ heraus aufgerufen meldete er
    brainlehrs Commits und keinen einzigen von dort. Ein Waechter, der das
    FALSCHE Repo prueft und dabei gruen meldet, ist schlimmer als keiner --
    er haette jedes fremde Repo freigesprochen.

    Reihenfolge: ausdrueckliche Angabe, sonst das Repo des aktuellen
    Verzeichnisses, sonst das eigene."""
    if vorgabe:
        return Path(vorgabe).resolve()
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True, check=False)
    if r.returncode == 0 and r.stdout.strip():
        return Path(r.stdout.strip())
    return Path(__file__).resolve().parents[1]


_w = _wurzel()

# Ab wie vielen geaenderten Quelldateien ein Plan genannt sein muss.
PLANSCHWELLE = 3

# Ab wann geprueft wird -- die VORGABE, je Repo per `--seit` zu uebersteuern.
# Gemeldet von der fahrtenbuch-Sitzung am 2026-08-16, nachdem die
# Wurzelkorrektur die Datei ueberhaupt erst fremdtauglich gemacht hatte: der
# Stichtag ist brainlehrs Einfuehrungstag und galt seither fuer jedes
# aufrufende Repo. Bei ihr war das nuetzlich (fing einen Altfall), in einem
# Repo mit vielen Commits von heute waere es sofort Dauerrot -- und Dauerrot
# heisst abgeschaltet.
#
# Ein Waechter, der beim ersten Lauf die eigene
# Vergangenheit blockiert, wird abgeschaltet -- und dann wirkt er nie.
# Deshalb ein Stichtag: sein eigener Einfuehrungstag. Die Altfaelle sind damit
# nicht vergessen, sondern ausgewiesen (--alle zeigt sie).
#
# Beim ersten Lauf traf die Regel DREI eigene Commits desselben
# Tages: 6e23d105, 89e96afc, 545e99b1 aenderten 3 bis 5 Quelldateien, ohne
# ihren Plan zu nennen -- obwohl es fuer alle drei einen gab. Das ist kein
# Argument gegen die Regel, sondern ihr erster Beleg.
# ACHTUNG, hier lag der erste Fehler: der Stichtag stand zunaechst auf 11:00,
# waehrend die Uhr 08:55 zeigte -- er lag in der ZUKUNFT, und damit prueft der
# Waechter NICHTS. Die Abnahme lief durch, der Push wurde nicht gestoppt, und
# das sah aus wie ein Freispruch. Ein Stichtag in der Zukunft ist ein
# abgeschalteter Waechter mit gutem Gewissen.
STICHTAG = "2026-08-16T08:55:00+02:00"

QUELLE = re.compile(r"\.(py|swift|js|dart|sh|sql)$")
NUR_ERZEUGT = re.compile(r"^(docs/karten/|docs/VERBUNDKARTE\.md|NODE_INDEX\.md|runs/)")

# Ein Plan ist genannt, wenn die Nachricht auf ein Plandokument oder eine ADR
# zeigt. Nicht geprueft wird, ob der Plan zur Aenderung PASST -- das kann kein
# Skript, und eine Scheinpruefung waere schlimmer als keine.
PLAN_GENANNT = re.compile(r"docs/PLAN_[\w.-]+|PLAN_[A-Z][\w-]*\.md|ADR-\d+", re.I)

# Die Belegfrage gilt als beantwortet, wenn der Text sagt WIE belegt wurde --
# oder ehrlich sagt, dass nicht belegt wurde. Beides zaehlt; nur Schweigen
# zaehlt nicht.
BELEG_GENANNT = re.compile(
    r"rot vor gr[uü]n|rot-probe|rot vor|war (vorher )?rot|vorher rot"
    r"|gegenprobe|abnahme|gemessen|belegt"
    r"|nicht verifiziert|nicht gepr[uü]ft|ungepr[uü]ft"
    r"|deckten den fehler nicht|am ger[aä]t nicht|handprobe",
    re.I)


def _lauf(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=_w, capture_output=True,
                          text=True, check=False).stdout


def commits(bereich: str, ab: str | None = STICHTAG) -> list[str]:
    args = ["rev-list", bereich] + ([f"--since={ab}"] if ab else [])
    return [z for z in _lauf(*args).splitlines() if z.strip()]


def pruefe_commit(sha: str) -> list[str]:
    """Befunde eines einzelnen Commits, leer heisst in Ordnung."""
    nachricht = _lauf("log", "-1", "--format=%B", sha)
    dateien = [z for z in _lauf("show", "--name-only", "--format=", sha).splitlines() if z.strip()]
    quellen = [d for d in dateien if QUELLE.search(d) and not NUR_ERZEUGT.match(d)]
    kurz = nachricht.strip().splitlines()[0][:60] if nachricht.strip() else sha[:8]
    befunde = []

    if len(quellen) >= PLANSCHWELLE and not PLAN_GENANNT.search(nachricht):
        befunde.append(
            f"{sha[:8]} „{kurz}\": {len(quellen)} Quelldateien geändert, aber kein Plan "
            f"und keine ADR genannt (Schwelle {PLANSCHWELLE}).")

    if quellen and not BELEG_GENANNT.search(nachricht):
        befunde.append(
            f"{sha[:8]} „{kurz}\": ändert Produktivcode, sagt aber nichts zur Belegfrage. "
            f"Entweder wie belegt wurde — oder ehrlich, dass nicht belegt ist "
            f"(„geändert, nicht verifiziert\").")
    return befunde


def pruefe(bereich: str, ab: str | None = STICHTAG) -> list[str]:
    befunde = []
    for sha in commits(bereich, ab):
        befunde += pruefe_commit(sha)
    return befunde


def demo() -> None:
    """Netzloser Selbsttest der beiden Regeln -- ohne git, mit den Texten
    direkt. Er prueft beide Richtungen: dass Fehlendes auffaellt UND dass
    ehrliche Selbstauskunft durchkommt."""
    assert PLAN_GENANNT.search("siehe docs/PLAN_DIAGRAMME_2026-08-16.md")
    assert PLAN_GENANNT.search("Umsetzung von ADR-014")
    assert not PLAN_GENANNT.search("kleine Korrektur am Regex")

    # Beleg genannt -- in allen zulaessigen Formen der Hausregel
    for satz in ("Beleg rot vor gruen: Test war vorher rot",
                 "Abnahme gefahren, Push wurde abgewiesen",
                 "gemessen ueber 117 Anfragen",
                 "geaendert, nicht verifiziert",
                 "Tests gruen, aber sie deckten den Fehler nicht ab",
                 "im Kopflauf belegt, am Geraet nicht"):
        assert BELEG_GENANNT.search(satz), satz
    # Schweigen zaehlt nicht
    assert not BELEG_GENANNT.search("Aufraeumen und Umbenennen von zwei Funktionen")

    assert QUELLE.search("kern/embeddings.py") and not QUELLE.search("docs/PLAN_X.md")
    # Die Wurzel muss aus dem AUFRUFER kommen, nicht aus dem Dateipfad.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        assert _wurzel(d) == Path(d).resolve(), "ausdrueckliche Angabe hat Vorrang"
    assert _wurzel() == Path(subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
        check=False).stdout.strip() or Path(__file__).resolve().parents[1]), (
        "ohne Angabe gilt das Repo des aktuellen Verzeichnisses -- sonst prueft "
        "der Waechter aus jedem fremden Repo heraus brainlehr und meldet gruen")

    assert NUR_ERZEUGT.match("docs/karten/verbund.md"), (
        "erzeugte Karten sind kein Produktivcode -- sonst verlangt der Waechter "
        "einen Beleg fuer eine Datei, die ein Skript geschrieben hat")
    print("demo: ok", file=sys.stderr)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("bereich", nargs="?", default="@{u}..HEAD",
                   help="git-Bereich, Vorgabe: alles Ungepushte")
    p.add_argument("--wurzel", default=None,
                   help="zu pruefendes Repo (Vorgabe: das des aktuellen Verzeichnisses)")
    p.add_argument("--still", action="store_true")
    p.add_argument("--alle", action="store_true",
                   help="auch Commits vor dem Stichtag (zeigt die Altfaelle)")
    p.add_argument("--seit", default=STICHTAG,
                   help=f"eigener Stichtag des Repos (Vorgabe: {STICHTAG}) -- "
                        f"jedes Repo hat seinen eigenen Einfuehrungstag")
    a = p.parse_args()
    global _w
    _w = _wurzel(a.wurzel)
    try:
        befunde = pruefe(a.bereich, None if a.alle else a.seit)
    except Exception as e:  # kein Upstream, frisches Repo -- kein Grund zu sperren
        if not a.still:
            print(f"Ablaufpflicht nicht prüfbar ({e}) — übersprungen.", file=sys.stderr)
        return 0
    if not befunde:
        if not a.still:
            print("Jeder Commit nennt Plan und Belegweg.")
        return 0
    if not a.still:
        print(f"{len(befunde)} Befund(e) zur Ablaufpflicht (docs/ablauf.json):", file=sys.stderr)
        for b in befunde:
            print(f"  {b}", file=sys.stderr)
        print("\nBeide Schritte stehen in docs/ablauf.json und hatten bis zum "
              "2026-08-16 keinen Mechanismus.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    demo()
    raise SystemExit(main())
