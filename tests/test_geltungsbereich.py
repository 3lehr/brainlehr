"""Tests fuer geltungsbereich.py (N2c, docs/PLAN_NORMSCHICHT_2026-08-05.md).

Rot-vor-gruen: vor dieser Datei gab es geltungsbereich.py nicht -- jeder
Import schlug fehl (rot). Die fuenf Faelle unten sind die im Auftrag
genannten: einwertiger Knoten, mehrwertige Lehre, leeres projects (->
leere Menge = "ueberall"), kaputtes JSON in der L-9b3012b6-Form, und NULL.
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

import sqlite3
import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

from geltungsbereich import geltungsbereich, projekte_aus_project_id, projekte_aus_projects_json


def _row(**kwargs) -> sqlite3.Row:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cols = ", ".join(kwargs)
    placeholders = ", ".join("?" for _ in kwargs)
    conn.execute(f"CREATE TABLE t ({', '.join(c + ' TEXT' for c in kwargs)})")
    conn.execute(f"INSERT INTO t ({cols}) VALUES ({placeholders})", list(kwargs.values()))
    return conn.execute(f"SELECT {cols} FROM t").fetchone()


def test_einwertiger_knoten():
    row = _row(project_id="fahrtenbuch")
    assert geltungsbereich(row) == frozenset({"fahrtenbuch"})


def test_mehrwertige_lehre():
    row = _row(projects='["fahrtenbuch", "openlehr"]')
    assert geltungsbereich(row) == frozenset({"fahrtenbuch", "openlehr"})


def test_leeres_projects_heisst_ueberall():
    row = _row(projects="[]")
    assert geltungsbereich(row) == frozenset()


def test_kaputtes_json_l_9b3012b6_form():
    """Live-Befund: L-9b3012b6.projects == 'openlehr' (bare string, kein Array)."""
    row = _row(projects="openlehr")
    assert geltungsbereich(row) == frozenset({"openlehr"})


def test_null_projects_heisst_ueberall():
    row = _row(projects=None)
    assert geltungsbereich(row) == frozenset()


def test_null_project_id_heisst_ueberall():
    row = _row(project_id=None)
    assert projekte_aus_project_id(None) == frozenset()
    assert geltungsbereich(row) == frozenset()


def test_gegen_live_bestand_falls_vorhanden():
    """Gegenprobe direkt gegen die Live-DB, falls vorhanden -- L-9b3012b6
    muss auch dort als kaputtes JSON erkannt werden, nicht als Crash."""
    db_path = SHARED_KNOWLEDGE / "knowledge.db"
    if not db_path.exists():
        return
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT projects FROM lessons_learned WHERE id = 'L-9b3012b6'").fetchone()
    conn.close()
    if row is None:
        return
    assert geltungsbereich(row) == frozenset({"openlehr"})


def test_unmatched_json_type_is_defensive_everywhere():
    assert projekte_aus_projects_json("42") == frozenset()  # JSON-Zahl, kein Array/String
