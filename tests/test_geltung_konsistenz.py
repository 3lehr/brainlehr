"""Kreuzprobe: normkraft.py::in_kraft und knowledge_mcp_server.py::_geltung_status
muessen an denselben Grenzwerten dasselbe sagen -- beide werten dieselbe Spalte
gilt_bis aus, fuer denselben Bestand.

Rot-vor-gruen (2026-08-06): vor diesem Auftrag pruefte in_kraft `gilt_bis >
stichtag` (exklusiv), _geltung_status `stichtag <= gilt_bis` (inklusiv). Am
Stichtag == gilt_bis sagten sie Verschiedenes -- siehe Auftragsantwort fuer den
roten Lauf. Entscheidung: gilt_bis ist inklusiv (letzter Geltungstag), beide
Seiten sind seither auf diese Regel gebracht. Dieser Test haelt die Klammer,
nicht die jeweilige Implementierung -- er bleibt rot, wenn eine Seite kuenftig
wieder abweicht.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

from normkraft import _init_temp_db, _insert_node, in_kraft  # noqa: E402
import knowledge_mcp_server as kms  # type: ignore  # noqa: E402

GILT_AB = "2026-01-01T00:00:00+01:00"
GILT_BIS = "2026-12-31T23:59:59+01:00"


def _db(tmp_path):
    db_path = tmp_path / "knowledge.db"
    _init_temp_db(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        _insert_node(conn, "n-x", "/adr/x", norm_rang=3, gilt_ab=GILT_AB, gilt_bis=GILT_BIS)
        conn.commit()
    finally:
        conn.close()
    return db_path


def _beide_sagen_in_kraft(db_path, row, stichtag) -> tuple[bool, bool]:
    a = "/adr/x" in {r["path"] for r in in_kraft(db_path, stichtag)}
    b = kms._geltung_status(row["norm_rang"], row["gilt_ab"], row["gilt_bis"], stichtag) == "in_kraft"
    return a, b


def test_beide_wege_einig_an_allen_vier_grenzwerten(tmp_path):
    db_path = _db(tmp_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT norm_rang, gilt_ab, gilt_bis FROM knowledge_nodes WHERE path='/adr/x'").fetchone()
    conn.close()

    faelle = {
        "gilt_ab - 1s": ("2025-12-31T23:59:59+01:00", False),
        "gilt_ab": (GILT_AB, True),
        "gilt_bis": (GILT_BIS, True),
        "gilt_bis + 1s": ("2027-01-01T00:00:00+01:00", False),
    }
    for name, (stichtag, erwartet_in_kraft) in faelle.items():
        a, b = _beide_sagen_in_kraft(db_path, row, stichtag)
        assert a == b == erwartet_in_kraft, (
            f"{name} (stichtag={stichtag}): in_kraft()={a}, _geltung_status()={b}, erwartet={erwartet_in_kraft}"
        )
