#!/usr/bin/env python3
"""Findet Swift-Ansichten und -Typen, die gebaut, aber von nirgends gerufen werden.

ANLASS, und er ist ein eigener Fehler: Am 2026-08-16 habe ich `DomaenenAnsicht`
gebaut, geprueft, committet und dem Betreiber gemeldet, der Bildschirm sei "jetzt
zu sehen". Er war es nicht -- die Ansicht wurde von KEINER Stelle aufgerufen.
Genau die Fehlerklasse "gebaut, laufend, wirkungslos", die dieses Haus an
anderen verfolgt, am eigenen Code.

WARUM ES DURCHRUTSCHTE: Es gab dafuer keine Stelle, an der es aufgefallen waere.
`hub/scripts/wiring_check.py` ist laut seinem eigenen Docstring Flutter/Dart-only
(dieselbe Falle wie in L-cd1ef0), `melder/ausloeserlos.py` prueft Python-Melder,
`hub/scripts/unverdrahtet.py` liefert fuer Swift nichts. Die Hausregel dazu
lautet: Wer eine Regel einzieht, fragt nicht "wo schreibe ich sie hin", sondern
"an welcher Stelle wuerde sie gebrochen, und was steht dort?" -- dort stand
nichts. Jetzt steht hier etwas.

WAS GEPRUEFT WIRD: Jeder in `app/Sources/` deklarierte Typ (struct/class/enum)
muss IRGENDWO ausser in seiner eigenen Deklarationszeile vorkommen -- in
derselben Datei oder in einer anderen.

Der erste Anlauf verlangte ein Vorkommen AUSSERHALB der eigenen Datei und
meldete daraufhin 31 Typen, fast alle private Hilfsansichten, die innerhalb
ihrer Datei voellig richtig benutzt werden. Ein Melder mit 31 Fehlalarmen wird
weggeklickt statt gelesen -- genau davor warnt der Absatz unten. Das Kriterium
ist deshalb enger: gemeldet wird nur, was NIRGENDS gebraucht wird.

WAS AUSDRUECKLICH NICHT GEPRUEFT WIRD, damit die Meldung nicht mehr behauptet
als sie zeigt:
  * Ob der Aufruf je AUSGEFUEHRT wird. Ein Zweig, den keine Bedingung erreicht,
    zaehlt hier als verdrahtet. Dagegen hilft nur ein Durchlauf.
  * Ob der Typ das Richtige tut.
  * Einstiegspunkte (@main) und Testtypen -- sie werden vom Rahmen gerufen,
    nicht vom Code, und waeren sonst Dauerfehlalarm.

ponytail: Textsuche statt Syntaxbaum. Ein Typ, der nur in einem Kommentar
erwaehnt wird, gilt faelschlich als verdrahtet -- das ist die bewusste Grenze.
Aufruesten auf SwiftSyntax, sobald der erste Fehlalarm dieser Art auftritt.

Aufruf:  python3 melder/unverdrahtet_swift.py [wurzel]
         python3 melder/unverdrahtet_swift.py --selbsttest
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DEKLARATION = re.compile(
    r"^\s*(?:public\s+|internal\s+|private\s+|fileprivate\s+|final\s+)*"
    r"(?:struct|class|enum|actor)\s+([A-Z][A-Za-z0-9_]*)",
    re.M,
)

# Vom Rahmen gerufen, nicht vom Code -- sonst Dauerfehlalarm.
AUSGENOMMEN = re.compile(r"Tests?$|^App$|Preview")


def _quelldateien(wurzel: Path) -> list[Path]:
    return [p for p in (wurzel / "app" / "Sources").rglob("*.swift") if ".build" not in p.parts]


def unverdrahtete(wurzel: Path) -> list[tuple[str, str]]:
    """[(Typname, Datei)] fuer Typen, die ausserhalb ihrer eigenen Datei
    nirgends vorkommen."""
    dateien = _quelldateien(wurzel)
    texte = {p: p.read_text(encoding="utf-8", errors="replace") for p in dateien}

    befunde = []
    for pfad, text in texte.items():
        if "@main" in text:
            continue
        for name in DEKLARATION.findall(text):
            if AUSGENOMMEN.search(name):
                continue
            # Vorkommen im GESAMTEN Quellbaum zaehlen. Eins ist die
            # Deklaration selbst; wer nur einmal vorkommt, wird nirgends
            # gebraucht -- auch nicht in seiner eigenen Datei.
            vorkommen = sum(t.count(name) for t in texte.values())
            if vorkommen <= 1:
                befunde.append((name, str(pfad.relative_to(wurzel))))
    return sorted(set(befunde))


def _selbsttest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        w = Path(d)
        quell = w / "app" / "Sources" / "X"
        quell.mkdir(parents=True)
        (quell / "Gerufen.swift").write_text("struct Gerufen { }\n", encoding="utf-8")
        # Rufer wird von Einstieg gebraucht, sonst waere er selbst verwaist
        # und der Negativfall unten koennte nie leer sein (erster Anlauf).
        (quell / "Rufer.swift").write_text("struct Rufer { let a = Gerufen() }\n", encoding="utf-8")
        (quell / "Einstieg.swift").write_text("@main struct Einstieg { let r = Rufer() }\n", encoding="utf-8")
        (quell / "Verwaist.swift").write_text("struct Verwaist { }\n", encoding="utf-8")

        namen = {n for n, _ in unverdrahtete(w)}
        assert "Verwaist" in namen, f"verwaister Typ nicht gefunden: {namen}"
        assert "Gerufen" not in namen, "gerufener Typ faelschlich gemeldet"
        # Negativfall: ohne verwaisten Typ darf NICHTS gemeldet werden -- ein
        # Melder, der immer anschlaegt, wird weggeklickt statt gelesen.
        (quell / "Verwaist.swift").unlink()
        assert unverdrahtete(w) == [], "Fehlalarm ohne verwaisten Typ"
    print("selbsttest: ok (3 Pruefungen)")


def main(argv: list[str]) -> int:
    if "--selbsttest" in argv:
        _selbsttest()
        return 0

    wurzel = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[1]
    befunde = unverdrahtete(wurzel)
    if not befunde:
        anzahl = len(_quelldateien(wurzel))
        print(f"Kein unverdrahteter Typ ({anzahl} Swift-Dateien geprueft).")
        return 0

    print(f"{len(befunde)} Typ(en) gebaut, aber von nirgends gerufen:")
    for name, datei in befunde:
        print(f"  {name}  ({datei})")
    print("\nEntweder verdrahten oder entfernen. Ein dritter Weg -- liegenlassen --")
    print("ist der, der die Fehlerklasse erzeugt hat.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
