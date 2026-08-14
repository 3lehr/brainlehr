#!/usr/bin/env python3
"""Zieht knowledge_widerruf_archiv auf den Schluessel nach, der in schema.sql
steht -- Surrogatschluessel statt (node_id, zurueckgezogen_am).

WARUM ES DIESE DATEI ueberhaupt braucht, und das ist die eigentliche Lehre:
Die Tabelle entstand am 2026-08-14 zuerst mit dem zusammengesetzten
Schluessel. Wenige Minuten spaeter fing ein Grenzwerttest den Fehler --
now_iso() hat Sekundengranularitaet, zwei Widerrufe in derselben Sekunde
teilen den Schluessel, INSERT OR REPLACE loescht die erste Fassung. In
schema.sql liess sich das korrigieren; die BEREITS ANGELEGTE Tabelle im
gewachsenen Bestand erreicht `CREATE TABLE IF NOT EXISTS` aber nicht mehr
(L-55075a, L-96db3e: eine Erstanlage sieht immer die neue Fassung, ein
gewachsener Bestand nie).

Der Melder melder/schemastand.py hat genau das binnen Minuten gemeldet --
'knowledge_widerruf_archiv: beidseitig vorhanden, ABWEICHENDES SQL'. Ohne ihn
waeren die beiden Fassungen auseinandergelaufen, und der Unterschied waere
erst bei zwei Widerrufen in derselben Sekunde aufgefallen, also womoeglich
nie.

Verlustfrei: die Tabelle traegt beim Lauf 0 Zeilen (nichts wurde seit ihrer
Anlage zurueckgezogen). Vorhandene Zeilen werden trotzdem uebernommen, statt
sich auf die Null zu verlassen -- ein Skript, das nur bei leerer Tabelle
richtig ist, ist beim zweiten Einsatz falsch.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken", "melder")]

import speicher  # noqa: E402

NEU = """
CREATE TABLE knowledge_widerruf_archiv_neu (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id            TEXT NOT NULL,
    path               TEXT NOT NULL,
    title              TEXT NOT NULL,
    summary            TEXT,
    content            TEXT,
    grund              TEXT NOT NULL,
    zurueckgezogen_am  TEXT NOT NULL,
    zurueckgezogen_von TEXT
);
"""


def main() -> int:
    with speicher.schreiben() as conn:
        vorhanden = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'knowledge_widerruf_archiv'"
        ).fetchone()
        if not vorhanden:
            print("knowledge_widerruf_archiv fehlt -- schema.sql legt sie an, nichts zu tun.")
            return 0
        if "AUTOINCREMENT" in vorhanden[0]:
            print("knowledge_widerruf_archiv traegt bereits den Surrogatschluessel, nichts zu tun.")
            return 0

        vorher = conn.execute("SELECT COUNT(*) FROM knowledge_widerruf_archiv").fetchone()[0]
        conn.executescript(NEU)
        conn.execute(
            """INSERT INTO knowledge_widerruf_archiv_neu
               (node_id, path, title, summary, content, grund, zurueckgezogen_am, zurueckgezogen_von)
               SELECT node_id, path, title, summary, content, grund, zurueckgezogen_am, zurueckgezogen_von
               FROM knowledge_widerruf_archiv ORDER BY zurueckgezogen_am"""
        )
        nachher = conn.execute("SELECT COUNT(*) FROM knowledge_widerruf_archiv_neu").fetchone()[0]
        # Zahl VOR dem Wegwerfen der Quelle pruefen -- danach ist die
        # Gegenprobe nicht mehr moeglich.
        assert nachher == vorher, f"uebernommen {nachher}, erwartet {vorher} -- nichts geloescht"
        conn.execute("DROP TABLE knowledge_widerruf_archiv")
        conn.execute("ALTER TABLE knowledge_widerruf_archiv_neu RENAME TO knowledge_widerruf_archiv")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_widerruf_archiv_node "
            "ON knowledge_widerruf_archiv(node_id, id)"
        )
        print(f"knowledge_widerruf_archiv umgestellt, {nachher} Zeile(n) uebernommen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
