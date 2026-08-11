#!/usr/bin/env python3
"""Stop-Haken: den Auszug nachziehen, wenn der Bestand juenger ist.

`brainlehr.db` ist nicht versioniert (Dienst-Plan A1, L-84869f: git fuehrt
eine Binaerdatei nicht zusammen, es ueberschreibt sie). Versioniert wird der
zeilenweise Auszug unter `auszug/`. Damit ist die Sicherung genau so frisch
wie der letzte `brainlehr.py raus` -- und der lief bisher von Hand.

Das ist der gefaehrliche Zustand, nicht der offensichtliche: eine Sicherung,
die HINTERHERHINKT, sieht im Verzeichnis genauso aus wie eine aktuelle. Wer
sie braucht, merkt den Unterschied zum spaetestmoeglichen Zeitpunkt.

Was dieser Haken tut: den Auszug neu schreiben, wenn die Datenbank juenger
ist als er. Was er NICHT tut: committen. Ein Haken, der in die
Versionsverwaltung schreibt, tut das mitten in fremder Arbeit -- er wuerde
Zwischenstaende anderer Sitzungen mit festschreiben. Stattdessen meldet er,
dass etwas nachzuziehen ist; das Committen bleibt beim Arbeitsschritt, wo es
hingehoert.

Der Melder ist der Punkt: ohne die Zeile am Sitzungsende faellt ein
veralteter Auszug erst auf, wenn jemand ihn einliest.
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
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ort  # noqa: E402

AUSZUG_ORDNER = ort.WURZEL / "auszug"


def aktuellster_auszug() -> Path | None:
    dateien = sorted(AUSZUG_ORDNER.glob("bestand_*.jsonl"))
    return dateien[-1] if dateien else None


def ziel_fuer_heute(heute: str) -> Path:
    """Ein Auszug je Tag. Absichtlich nicht je Lauf: sonst waechst das
    Verzeichnis mit jeder Sitzung um acht Megabyte Text, der sich nur in
    Kleinigkeiten unterscheidet."""
    return AUSZUG_ORDNER / f"bestand_{heute}.jsonl"


def nachziehen_noetig(db: Path, auszug: Path | None) -> bool:
    if not db.exists():
        return False
    if auszug is None or not auszug.exists():
        return True
    return db.stat().st_mtime > auszug.stat().st_mtime


def main() -> None:
    try:
        db = Path(ort.DB)
        vorher = aktuellster_auszug()
        if not nachziehen_noetig(db, vorher):
            return

        # Datum aus der Datenbank-Zeit, nicht aus der Uhr: laeuft der Haken
        # kurz nach Mitternacht fuer eine Sitzung von gestern, gehoert der
        # Auszug zum Bestand, nicht zum Kalender.
        import datetime
        heute = datetime.datetime.fromtimestamp(db.stat().st_mtime).strftime("%Y-%m-%d")
        ziel = ziel_fuer_heute(heute)
        AUSZUG_ORDNER.mkdir(exist_ok=True)

        # Ueber das Kommando statt ueber den Import: brainlehr.py haelt die
        # Reihenfolge (Eltern vor Kindern) und den Kopf mit den Sollzahlen.
        # Ein zweiter Schreibweg hier waere die naechste Stelle, die
        # auseinanderlaeuft.
        r = subprocess.run(
            [sys.executable, str(ort.WURZEL / "brainlehr.py"), "raus", str(ziel), "--db", str(db)],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode != 0:
            print(f"Auszug konnte nicht nachgezogen werden: {r.stderr.strip()[:200]}")
            return

        zeilen = sum(1 for _ in ziel.open(encoding="utf-8"))
        neu = vorher is None or ziel != vorher
        wort = "angelegt" if neu else "nachgezogen"
        print(f"Auszug {wort}: {ziel.name} ({zeilen} Zeilen) — noch nicht committet. "
              f"`git add {ziel.relative_to(ort.WURZEL)} && git commit`, sonst hinkt die Sicherung.")
    except Exception:
        # Gleiches Muster wie die anderen Haken: eine Nebenpruefung darf das
        # Sitzungsende nie zum Scheitern bringen.
        pass


if __name__ == "__main__":
    main()
