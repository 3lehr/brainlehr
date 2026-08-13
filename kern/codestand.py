#!/usr/bin/env python3
"""Ermittelt den Codestand (Commit, Zweig, schmutzig) zur LAUFZEIT fuer
Messergebnisse unter runs/ (AUFGABE 70).

Grund: mindestens ein Skript unter messungen/ trug den Codestand fest
verdrahtet als Zeichenkette im Quelltext -- ab dem naechsten Commit falsch,
und trotzdem geglaubt. Eine Zahl, die gegen einen schmutzigen Arbeitsbaum
gemessen wurde, ist zudem nicht reproduzierbar; das gehoert ins Ergebnis
statt verloren zu gehen.

Verwendung in einem Messskript (WURZEL wie ueblich per schema.sql-Suche):
    import codestand
    ausgabe = {..., "codestand": codestand.ermitteln(WURZEL), ...}
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path


def ermitteln(wurzel: Path) -> dict:
    """Commit (kurz), Zweig und ob der Arbeitsbaum beim Messzeitpunkt
    schmutzig war (uncommittete Aenderungen, `git status --porcelain`)."""
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=wurzel,
        capture_output=True, text=True, check=True).stdout.strip()
    zweig = subprocess.run(
        ["git", "branch", "--show-current"], cwd=wurzel,
        capture_output=True, text=True, check=True).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=wurzel,
        capture_output=True, text=True, check=True).stdout
    return {
        "commit": commit,
        "zweig": zweig,
        "schmutzig": bool(status.strip()),
        "ermittelt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def demo() -> None:
    """ponytail-Selbstcheck: commit-Feld gegen den echten HEAD dieses
    Repos, Form der uebrigen Felder."""
    hier = Path(__file__).resolve().parent.parent
    ergebnis = ermitteln(hier)
    echter_head = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=hier,
        capture_output=True, text=True, check=True).stdout.strip()
    assert ergebnis["commit"] == echter_head, ergebnis
    assert isinstance(ergebnis["schmutzig"], bool), ergebnis
    assert ergebnis["zweig"], ergebnis
    print("codestand.ermitteln() ok:", ergebnis)


if __name__ == "__main__":
    demo()
