#!/usr/bin/env python3
"""gattung_filter.py -- Auftrag S1b (docs/PLAN_DESTILLE_2026-08-09.md).

Ein Werk (z.B. die NASA-LLIS-Sammlung, 1638 Knoten) ist ein Nachschlagewerk:
man schlaegt darin nach, es draengt sich nicht auf. knowledge_nodes.gattung
traegt das je Knoten (Vorgabe 'arbeitsbestand', s. schema.sql). Zwei Stellen
im Recall-Haken (haken/knowledge_recall_hook.py, Monolith-Bremse >2000
Zeilen) brauchen denselben Ausschluss -- darum eigenes kleines Modul statt
Duplikat.

SQL_ARBEITSBESTAND_NUR ist ein WHERE-Fragment (mit fuehrendem "AND"), das an
bestehende knowledge_nodes-Abfragen angehaengt wird -- kein neues Praedikat,
nur der Filter."""
from __future__ import annotations

SQL_ARBEITSBESTAND_NUR = "AND n.gattung != 'nachschlagewerk'"


def ist_arbeitsbestand(gattung: str | None) -> bool:
    """Fuer Python-seitige Nachpruefung (z.B. Tests), wo kein SQL laeuft.
    NULL/leer zaehlt als Arbeitsbestand -- Vorgabewert der Spalte."""
    return gattung != "nachschlagewerk"


def _selftest() -> int:
    assert ist_arbeitsbestand(None) is True
    assert ist_arbeitsbestand("arbeitsbestand") is True
    assert ist_arbeitsbestand("nachschlagewerk") is False
    assert SQL_ARBEITSBESTAND_NUR.startswith("AND ")
    print("SELFTEST OK: gattung_filter")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
