#!/usr/bin/env python3
"""geltungsbereich.py -- N2 aus docs/PLAN_NORMSCHICHT_2026-08-05.md, Teil c.

Normalisierter Lese-Zugriff auf die Projektmenge eines Artefakts. Der
Speicher kennt zwei Formen fuer denselben Sachverhalt:
- knowledge_nodes.project_id  -- einwertig (TEXT, NOT NULL DEFAULT 'shared')
- lessons_learned.projects    -- mehrwertig (JSON-Array als TEXT, 191
                                  Eintraege mit >1 Projekt; einer kaputt,
                                  L-9b3012b6 traegt 'openlehr' statt
                                  '["openlehr"]')

Die Zuschnitt-Korrektur vom 2026-08-05T22:20 (Plan Kapitel 5, N2) baut das
Schema NICHT um -- project_id bleibt einwertig, projects bleibt sein
eigenes JSON-Array. N3/N4 brauchen nur die Menge zum Vergleichen, kein
gemeinsames Speicherformat. Eigene, kleine Datei statt Ergaenzung in
knowledge_mcp_server.py (1622 Zeilen, Monolith-Bremse aktiv).

WICHTIG: leere Menge heisst "gilt ueberall", nicht "gilt nirgends". Ein
Artefakt ohne Bereichseinschraenkung (NULL/leeres projects) gilt fuer jedes
Projekt -- N4 vergleicht zwei Normen sonst faelschlich als nicht
ueberlappend, obwohl die bereichslose Norm jede andere ueberlappt.
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

import json


def projekte_aus_project_id(project_id: str | None) -> frozenset[str]:
    """Knoten-Form: einwertig. Leer/NULL -> ueberall (siehe Moduldoc)."""
    return frozenset({project_id}) if project_id else frozenset()


def projekte_aus_projects_json(raw: str | None) -> frozenset[str]:
    """Lehren-Form: JSON-Array als Text. Deckt drei Sonderfaelle ab, die
    live im Bestand vorkommen (siehe Moduldoc): leer/NULL -> ueberall;
    kaputtes JSON wie bei L-9b3012b6 ('openlehr' statt '["openlehr"]') ->
    der Rohwert ist dann selbst schon der eine Projektname; ein JSON-Array
    -> seine nicht-leeren String-Eintraege."""
    if not raw or not raw.strip():
        return frozenset()
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        stripped = raw.strip()
        return frozenset({stripped}) if stripped else frozenset()
    if isinstance(parsed, str):
        return frozenset({parsed}) if parsed else frozenset()
    if isinstance(parsed, list):
        return frozenset(p for p in parsed if isinstance(p, str) and p)
    return frozenset()  # unerwarteter JSON-Typ -> defensiv "ueberall", kein Crash


def geltungsbereich(row) -> frozenset[str]:
    """Nimmt eine sqlite3.Row oder ein dict mit 'projects' (Lehre) oder
    'project_id' (Knoten) und liefert die normalisierte Projektmenge.
    'projects' hat Vorrang, falls beide Schluessel vorhanden sind (kommt in
    der Praxis nicht vor, beide Tabellen haben nur je eines der Felder)."""
    keys = row.keys()
    if "projects" in keys:
        return projekte_aus_projects_json(row["projects"])
    if "project_id" in keys:
        return projekte_aus_project_id(row["project_id"])
    raise ValueError("Datensatz hat weder 'project_id' noch 'projects'")


def sql_projects_exact(column: str = "projects") -> str:
    """SQL-Fragment: prueft EIN Platzhalter-'?' exakt gegen die JSON-Array-
    Elemente von <column> (json_each, SQLite-Bordmittel). Ersetzt die bisherige
    Filterform 'projects LIKE \'%"name"%\''.

    Die alte, quotierte LIKE-Form matcht ueberraschend oft trotzdem exakt (auf
    761 Lehren gemessen 2026-08-11: 0 Falschtreffer fuer wohlair/wohlairr,
    aka/aka2026, aka/aka-homepage, fahrtenbuch/fahrtenbuch_legacy,
    shared/shared-knowledge -- die Anfuehrungszeichen im Muster verhindern
    reine Praefix-Kollisionen). Ihre echte Luecke ist eine andere: LIKE
    behandelt '_' und '%' im SUCHBEGRIFF als Wildcards. 'fahrtenbuch_legacy'
    ist selbst ein Projektname mit '_' -- eine Suche danach matcht per LIKE
    auch 'fahrtenbuchXlegacy' (ein beliebiges Zeichen statt '_'), verifiziert
    per Test. json_each vergleicht das Element als Wert, nicht als Muster,
    und ist gegen beide Faelle blind.

    Jeder Aufruf braucht einen eigenen '?'-Parameter mit dem gesuchten
    Projektnamen; mehrere Aufrufe (z.B. 'shared' ODER 'systemweit' ODER
    <scope>) werden mit OR verknuepft."""
    return f"EXISTS (SELECT 1 FROM json_each({column}) AS je WHERE je.value = ?)"


if __name__ == "__main__":
    assert projekte_aus_project_id("fahrtenbuch") == frozenset({"fahrtenbuch"})
    assert projekte_aus_project_id(None) == frozenset()
    assert projekte_aus_projects_json('["a", "b"]') == frozenset({"a", "b"})
    assert projekte_aus_projects_json("[]") == frozenset()
    assert projekte_aus_projects_json(None) == frozenset()
    assert projekte_aus_projects_json("openlehr") == frozenset({"openlehr"})

    import sqlite3
    _c = sqlite3.connect(":memory:")
    _c.execute("CREATE TABLE t (projects TEXT)")
    _c.executemany("INSERT INTO t VALUES (?)", [('["wohlair"]',), ('["wohlairr"]',)])
    _sql = f"SELECT count(*) FROM t WHERE {sql_projects_exact()}"
    assert _c.execute(_sql, ("wohlair",)).fetchone()[0] == 1
    assert _c.execute(_sql, ("wohlairr",)).fetchone()[0] == 1

    # Der reale Fehlerfall alter LIKE-Filter: '_' im Suchbegriff ist fuer
    # LIKE ein Wildcard. 'fahrtenbuch_legacy' ist selbst ein Projektname.
    _c.execute("INSERT INTO t VALUES (?)", ('["fahrtenbuchXlegacy"]',))
    _c.execute("INSERT INTO t VALUES (?)", ('["fahrtenbuch_legacy"]',))
    assert _c.execute(_sql, ("fahrtenbuch_legacy",)).fetchone()[0] == 1  # nicht 2
    print("OK")
