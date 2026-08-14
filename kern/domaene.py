"""Domaenenpaket-Importer (PLAN_OPENLEHR_2026-08-14.md H8a).

Ein Paket ist eine JSON-Datei mit Regeln und ihren Quellen -- das Format ist
kern/belegvertrag.pruefe_regeln in Dateiform (siehe H8-Abschnitt des Plans):
{"domaene", "bezeichnung", "herkunft", "stand", "quellen", "regeln"}.

Ein Paket ist reine Daten. Es wird nie ausgefuehrt, nie als Code geladen --
importiere() liest JSON und prueft, sonst nichts.

Eine Regel ohne belegte Fundstelle wird abgewiesen, nicht stillschweigend
uebernommen (ADR-007). Der Grund ist ein Satz fuer den Menschen, der das
Paket ausgewaehlt hat -- keine Ausnahme, kein Dateiname, keine Zeilennummer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kern.belegvertrag import pruefe_regeln

_PFLICHTSCHLUESSEL = ("domaene", "quellen", "regeln")


def importiere(pfad: str | Path) -> dict[str, Any]:
    """Liest und prueft ein Domaenenpaket. Liefert immer ein Ergebnis, wirft
    nie: {"angenommen": bool, "anzahl_regeln": int | None, "grund": str | None}."""
    try:
        rohtext = Path(pfad).read_text(encoding="utf-8")
    except OSError:
        return _abgelehnt("Die Paketdatei laesst sich nicht oeffnen.")

    try:
        paket = json.loads(rohtext)
    except json.JSONDecodeError:
        return _abgelehnt("Die Paketdatei ist beschaedigt und laesst sich nicht lesen.")

    if not isinstance(paket, dict):
        return _abgelehnt("Die Paketdatei enthaelt kein gueltiges Paket.")

    fehlend = [schluessel for schluessel in _PFLICHTSCHLUESSEL if schluessel not in paket]
    if fehlend:
        return _abgelehnt(f"Der Paketdatei fehlen Angaben: {', '.join(fehlend)}.")

    regeln = paket["regeln"]
    quellen = paket["quellen"]
    if not isinstance(regeln, list) or not isinstance(quellen, dict):
        return _abgelehnt("Die Paketdatei ist falsch aufgebaut.")

    try:
        pruefe_regeln(regeln, quellen)
    except (ValueError, KeyError, TypeError):
        return _abgelehnt(_grund_fuer_ablehnung(regeln, quellen))

    return {"angenommen": True, "anzahl_regeln": len(regeln), "grund": None}


def _grund_fuer_ablehnung(regeln: list[dict[str, Any]], quellen: dict[str, Any]) -> str:
    """Findet die erste Regel, die alleine gegen den Vertrag scheitert, und
    benennt sie -- statt die Ausnahme von pruefe_regeln() weiterzureichen."""
    for regel in regeln:
        if not isinstance(regel, dict):
            return "Eine Regel im Paket ist falsch aufgebaut."
        try:
            pruefe_regeln([regel], quellen)
        except (ValueError, KeyError, TypeError):
            name = regel.get("id", "?")
            return f"Die Regel '{name}' nennt keine Quelle, die zu ihrer Fundstelle passt."
    return "Eine Regel im Paket nennt keine passende Quelle."


def _abgelehnt(grund: str) -> dict[str, Any]:
    return {"angenommen": False, "anzahl_regeln": None, "grund": grund}


__all__ = ["importiere"]
