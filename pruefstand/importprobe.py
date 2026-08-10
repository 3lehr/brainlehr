#!/usr/bin/env python3
"""Laedt JEDE .py des Repos in einem eigenen Prozess und wertet den Exit-Code aus.

Grund fuer die Datei: ein Massenumzug von 19 Dateien wurde einmal als
erfolgreich gemeldet, obwohl 7 davon mit Traceback abstuerzten -- die
Pruefschleife sammelte Ausgabe und sah nie auf den Rueckgabewert (L-733583).
Eine Pruefung, die nicht rot werden kann, belegt nichts.

Rot heisst hier: mindestens eine Datei laesst sich nicht laden. Der Vergleich
gegen eine vor dem Umbau erhobene Basislinie zeigt, was der Umbau kaputt
gemacht hat -- ohne sie ist ein Fehlschlag nicht von einem Altbestand zu
unterscheiden.

    python3 pruefstand/importprobe.py --basislinie basis.json   # vorher
    python3 pruefstand/importprobe.py --gegen basis.json        # nachher
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder")]

import argparse
import json
import subprocess
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
# Wandert der Ordner mit, bleibt der Ausschluss richtig -- Namen, keine Pfade.
AUS = {".git", ".venv", "node_modules", "__pycache__", "auszug-offen"}


def _ladbar(datei: Path) -> tuple[bool, str]:
    """Laedt die Datei als Modul in einem eigenen Prozess.

    Eigener Prozess, weil ein Importfehler in diesem hier alles Weitere
    verfaelschen wuerde -- und weil nur so ein Exit-Code entsteht, den man
    nicht uebersehen kann.
    """
    p = subprocess.run(
        [sys.executable, "-c",
         # Das Modul MUSS vor exec_module in sys.modules stehen: dataclasses
         # und typing schlagen Typangaben ueber sys.modules[__name__] nach.
         # Ohne diese Zeile meldet die Probe fuer voellig gesunde Dateien
         # "AttributeError: 'NoneType' object has no attribute '__dict__'" --
         # ein Befund ueber das Pruefwerkzeug, nicht ueber den Code.
         "import importlib.util,sys;"
         "n='probe_'+sys.argv[1].replace('/','_').removesuffix('.py');"
         "s=importlib.util.spec_from_file_location(n,sys.argv[1]);"
         "m=importlib.util.module_from_spec(s);sys.modules[n]=m;"
         "s.loader.exec_module(m)",
         str(datei)],
        cwd=WURZEL, capture_output=True, text=True, timeout=60,
    )
    if p.returncode == 0:
        return True, ""
    zeilen = [z for z in p.stderr.strip().splitlines() if z.strip()]
    return False, zeilen[-1] if zeilen else f"Exit {p.returncode} ohne Meldung"


def erheben() -> dict[str, str]:
    """Gibt {relativer Pfad: Fehlerzeile} -- leerer Wert heisst ladbar."""
    ergebnis: dict[str, str] = {}
    dateien = sorted(d for d in WURZEL.rglob("*.py")
                     if not (AUS & set(d.relative_to(WURZEL).parts)))
    for d in dateien:
        ok, meldung = _ladbar(d)
        ergebnis[str(d.relative_to(WURZEL))] = "" if ok else meldung
    return ergebnis


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--basislinie", type=Path, help="Stand hierhin schreiben")
    p.add_argument("--gegen", type=Path, help="gegen diesen Stand vergleichen")
    a = p.parse_args()

    jetzt = erheben()
    kaputt = {d: m for d, m in jetzt.items() if m}
    print(f"{len(jetzt)} Dateien geladen, {len(kaputt)} davon nicht ladbar")

    if a.basislinie:
        a.basislinie.write_text(json.dumps(jetzt, indent=1, ensure_ascii=False))
        print(f"Basislinie geschrieben: {a.basislinie}")
        for d, m in sorted(kaputt.items()):
            print(f"  vorbestehend kaputt  {d}\n      {m}")
        return 0

    if a.gegen:
        # Auf DATEINAMEN vergleichen, nicht auf Pfade: der haeufigste Anlass
        # fuer diese Probe ist ein Umzug, und der aendert jeden Pfad. Ein
        # Pfadvergleich meldete dann jede Datei als "weg" und jede als "neu
        # kaputt" -- viel Text, kein Befund.
        roh = json.loads(a.gegen.read_text())
        vorher = {Path(d).name: m for d, m in roh.items()}
        jetzt_n = {Path(d).name: m for d, m in jetzt.items()}
        kaputt_n = {Path(d).name: m for d, m in kaputt.items()}
        neu = {d: m for d, m in kaputt_n.items() if not vorher.get(d)}
        geheilt = [d for d, m in vorher.items() if m and not jetzt_n.get(d, "x")]
        verschwunden = [d for d in vorher if d not in jetzt_n]
        for d in sorted(verschwunden):
            print(f"  WEG      {d}  (umbenannt, verschoben oder geloescht)")
        for d in sorted(geheilt):
            print(f"  geheilt  {d}")
        for d, m in sorted(neu.items()):
            print(f"  NEU KAPUTT  {d}\n      {m}")
        if neu:
            print(f"\nROT: {len(neu)} Datei(en) waren vorher ladbar und sind es "
                  f"jetzt nicht mehr.")
            return 1
        print("\nGRUEN: keine Datei ist durch die Aenderung unladbar geworden.")
        return 0

    for d, m in sorted(kaputt.items()):
        print(f"  {d}\n      {m}")
    return 1 if kaputt else 0


if __name__ == "__main__":
    raise SystemExit(main())
