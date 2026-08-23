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
