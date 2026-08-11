"""Tests fuer normrang.py (N3, docs/PLAN_NORMSCHICHT_2026-08-05.md).

Rot-vor-gruen: vor dieser Datei gab es normrang.py nicht -- jeder Import
schlug fehl (rot). Deckt: die drei Ableitungsmuster einzeln, der Fakt-Fall
(kein Rang), und dass ein zweiter Lauf nichts mehr aendert.
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

from normrang import (
    GLOBAL_CLAUDE_MD,
    HUB_CLAUDE_MD,
    _insert_node,
    _init_temp_db,
    anwenden,
    quelle_aus_source,
    rang_fuer_source,
)


def test_quelle_aus_source_erkennt_muster():
    src = f"erzeugt aus {GLOBAL_CLAUDE_MD} (Stand 2026-08-05T00:00:00+02:00)"
    assert quelle_aus_source(src) == str(GLOBAL_CLAUDE_MD)


def test_quelle_aus_source_ohne_muster_ist_none():
    assert quelle_aus_source("normbestand.py::ensure_category") is None
    assert quelle_aus_source(None) is None
    assert quelle_aus_source("") is None


def test_rang_1_globale_claude_md():
    src = f"erzeugt aus {GLOBAL_CLAUDE_MD} (Stand X)"
    assert rang_fuer_source(src) == 1


def test_rang_2_hub_claude_md():
    src = f"erzeugt aus {HUB_CLAUDE_MD} (Stand X)"
    assert rang_fuer_source(src) == 2


def test_rang_3_adr():
    assert rang_fuer_source("erzeugt aus docs/adr/001-use-drift-database.md (Stand X)") == 3


def test_fakt_bleibt_ohne_rang():
    """Sammelknoten und beliebige andere Quellen sind keine Norm."""
    assert rang_fuer_source("normbestand.py::ensure_category") is None
    assert rang_fuer_source("erzeugt aus scripts/methodik_export.py (Stand X)") is None
    assert rang_fuer_source(None) is None


def test_apply_setzt_rang_und_gilt_ab_faktbleibt_null(tmp_path):
    db_path = tmp_path / "brainlehr.db"
    _init_temp_db(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        _insert_node(conn, "n-global", "/x/g", f"erzeugt aus {GLOBAL_CLAUDE_MD} (Stand X)", "2026-08-01T00:00:00+01:00")
        _insert_node(conn, "n-fakt", "/x/f", "irgendein Fund", "2026-08-01T00:00:00+01:00")
        conn.commit()
    finally:
        conn.close()

    res = anwenden(db_path, apply=True)
    assert res["je_rang"][1] == 1
    assert res["ohne_rang"] == 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        g = conn.execute("SELECT norm_rang, gilt_ab, gilt_bis FROM knowledge_nodes WHERE id='n-global'").fetchone()
        assert (g["norm_rang"], g["gilt_ab"], g["gilt_bis"]) == (1, "2026-08-01T00:00:00+01:00", None)
        f = conn.execute("SELECT norm_rang FROM knowledge_nodes WHERE id='n-fakt'").fetchone()
        assert f["norm_rang"] is None
    finally:
        conn.close()


def test_zweiter_lauf_aendert_nichts(tmp_path):
    db_path = tmp_path / "brainlehr.db"
    _init_temp_db(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        _insert_node(conn, "n-adr", "/x/a", "erzeugt aus docs/adr/001-x.md (Stand X)", "2026-08-01T00:00:00+01:00")
        conn.commit()
    finally:
        conn.close()

    res1 = anwenden(db_path, apply=True)
    assert len(res1["aenderungen"]) == 1
    assert res1["backup"] is not None

    res2 = anwenden(db_path, apply=True)
    assert res2["aenderungen"] == []
    assert res2["backup"] is None


def test_reproduzierbarkeit_gleiche_db_gleiche_raenge(tmp_path):
    """Abnahme Punkt 5: --apply auf einer Kopie liefert dieselben Raenge."""
    db_path = tmp_path / "brainlehr.db"
    _init_temp_db(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        _insert_node(conn, "n1", "/x/1", f"erzeugt aus {GLOBAL_CLAUDE_MD} (Stand X)", "2026-08-01T00:00:00+01:00")
        _insert_node(conn, "n2", "/x/2", f"erzeugt aus {HUB_CLAUDE_MD} (Stand X)", "2026-08-01T00:00:00+01:00")
        _insert_node(conn, "n3", "/x/3", "erzeugt aus docs/adr/002-x.md (Stand X)", "2026-08-01T00:00:00+01:00")
        _insert_node(conn, "n4", "/x/4", "sonstwas", "2026-08-01T00:00:00+01:00")
        conn.commit()
    finally:
        conn.close()

    copy_path = tmp_path / "kopie.db"
    shutil.copy2(db_path, copy_path)

    anwenden(db_path, apply=True)
    anwenden(copy_path, apply=True)

    def _raenge(p):
        conn = sqlite3.connect(str(p))
        rows = conn.execute("SELECT id, norm_rang FROM knowledge_nodes ORDER BY id").fetchall()
        conn.close()
        return rows

    assert _raenge(db_path) == _raenge(copy_path)
