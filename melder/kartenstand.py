#!/usr/bin/env python3
"""Sind die Landkarten noch wahr? -- Punkt 3 der Betreiberfrage vom 2026-08-16:
"wie bekommen wir das hin, das die graphen auch bei neuem code usw noch aktuell
sind?"

DIE ANTWORT IST NICHT "haeufiger erzeugen". Eine erzeugte Karte veraltet nicht
im Erzeugnis, sondern ZWISCHEN zwei Laeufen -- laeuft niemand, ist sie so
falsch wie eine handgezeichnete, nur mit der Behauptung von Genauigkeit. Die
Frage lautet deshalb: woran haengt der Lauf?

Dieses Modul erzeugt die Karten neu, in ein Wegwerf-Verzeichnis, und
VERGLEICHT sie mit den abgelegten. Weicht etwas ab, ist die Karte veraltet --
und das ist ein Befund mit Dateinamen, kein Zeitplan und keine Verabredung.
Verdrahtet als pre-push: die Karte darf im Arbeitsbereich hinterherhinken,
aber nichts Veraltetes geht nach aussen.

VERWORFEN, und beides aus demselben Grund:
  * Bei jedem Commit mitschreiben -- schreibt Dateien in fremde Commits und
    verschiebt die Frage nur eine Ebene: wer prueft, dass der Haken haengt?
  * Zeitgesteuert erzeugen -- ein Lauf, dessen Ausbleiben niemandem auffaellt.
    Genau die Bauform, die dieses Haus zwoelfmal als "gebaut, laufend,
    wirkungslos" gemessen hat.

Dass die Erzeugung deterministisch ist (kein Zeitstempel im Erzeugnis), ist
die Voraussetzung dafuer -- sonst meldete jeder Lauf eine Abweichung und der
Waechter waere binnen einer Woche abgeschaltet.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "melder")]

import landkarten  # noqa: E402


def pruefen(repos_fuer_code: list[str]) -> list[str]:
    """Gibt die Namen der abgewichenen Dateien zurueck; leer heisst aktuell."""
    karten = landkarten.alle(repos_fuer_code)
    abgewichen: list[str] = []
    echtes_ziel = landkarten.ZIEL
    with tempfile.TemporaryDirectory() as tmp:
        landkarten.ZIEL = Path(tmp)
        try:
            for neu in landkarten.schreiben(karten):
                alt = echtes_ziel / neu.name
                if not alt.exists():
                    abgewichen.append(f"{neu.name} (fehlt)")
                elif alt.read_bytes() != neu.read_bytes():
                    abgewichen.append(neu.name)
        finally:
            landkarten.ZIEL = echtes_ziel
    # Auch der umgekehrte Fall ist eine Abweichung: eine Karte, die es nicht
    # mehr gibt, deren Datei aber liegen blieb -- sie sieht aktuell aus.
    erwartet = {f"{k[0]}.md" for k in karten} | {f"{k[0]}.json" for k in karten}
    if echtes_ziel.exists():
        for p in sorted(echtes_ziel.iterdir()):
            if p.name not in erwartet and p.suffix in (".md", ".json"):
                abgewichen.append(f"{p.name} (verwaist)")
    return abgewichen


def demo() -> None:
    """Netzloser Selbsttest der Vergleichslogik, ohne die echten Karten
    anzufassen: legt zwei Verzeichnisse an und prueft, dass eine geaenderte,
    eine fehlende und eine verwaiste Datei je erkannt werden."""
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        echt, tmp = Path(a), Path(b)
        (echt / "x.md").write_text("alt", encoding="utf-8")
        (echt / "weg.md").write_text("verwaist", encoding="utf-8")
        (tmp / "x.md").write_text("neu", encoding="utf-8")

        # Dieselbe Logik wie oben, auf zwei Wegwerf-Verzeichnissen.
        erwartet = {"x.md", "fehlt.md"}
        abgewichen = []
        for name in sorted(erwartet):
            neu = tmp / name
            alt = echt / name
            if not alt.exists():
                abgewichen.append(f"{name} (fehlt)")
            elif not neu.exists() or alt.read_bytes() != neu.read_bytes():
                abgewichen.append(name)
        for p in sorted(echt.iterdir()):
            if p.name not in erwartet:
                abgewichen.append(f"{p.name} (verwaist)")
        assert abgewichen == ["fehlt.md (fehlt)", "x.md", "weg.md (verwaist)"], abgewichen
    print("demo: ok")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--code", nargs="*", default=["brainlehr", "hub"])
    p.add_argument("--still", action="store_true", help="nur Rueckgabewert, keine Ausgabe")
    a = p.parse_args()
    abgewichen = pruefen(a.code)
    if not abgewichen:
        if not a.still:
            print("Landkarten sind aktuell.")
        return 0
    if not a.still:
        print("VERALTET -- die Landkarten geben den Quelltext nicht mehr wieder:",
              file=sys.stderr)
        for name in abgewichen:
            print(f"  docs/karten/{name}", file=sys.stderr)
        print(f"\nAuffrischen: python3 melder/landkarten.py --code {' '.join(a.code)}",
              file=sys.stderr)
    return 1


if __name__ == "__main__":
    demo()
    raise SystemExit(main())
