"""Tests fuer normkraft.py (letztes Glied, docs/PLAN_NORMSCHICHT_2026-08-05.md).

Rot-vor-gruen: vor dieser Datei gab es normkraft.py nicht -- jeder Import
schlug fehl (rot), und gilt_bis konnte von keiner Stelle im Bestand gesetzt
werden (grep ueber shared-knowledge/*.py, 2026-08-06: 0 Treffer). Deckt die
vier geforderten Ablehnungsfaelle einzeln, den Pflichtgrund, dry-run,
Idempotenz und die in_kraft-Gegenprobe vor/nach dem Stichtag.
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

from normkraft import (
    Ablehnung,
    _init_temp_db,
    _insert_node,
    ausser_kraft,
    in_kraft,
    plan_ausser_kraft,
)


def _basis_db(tmp_path):
    db_path = tmp_path / "knowledge.db"
    _init_temp_db(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        _insert_node(conn, "n-adr", "/adr/x", norm_rang=3, gilt_ab="2026-01-01T00:00:00+01:00")
        _insert_node(conn, "n-adr2", "/adr/y", norm_rang=3, gilt_ab="2026-01-01T00:00:00+01:00")
        _insert_node(conn, "n-fakt", "/fakt/x", norm_rang=None, gilt_ab=None)
        conn.commit()
    finally:
        conn.close()
    return db_path


def test_gilt_bis_war_vorher_von_nichts_setzbar_rot_fall(tmp_path):
    """Rot-Beleg: eine frische DB traegt gilt_bis nur als NULL -- kein
    Schreibpfad ausser diesem Skript existiert dafuer."""
    db_path = _basis_db(tmp_path)
    conn = sqlite3.connect(str(db_path))
    val = conn.execute("SELECT gilt_bis FROM knowledge_nodes WHERE path='/adr/x'").fetchone()[0]
    conn.close()
    assert val is None


def test_ablehnung_pfad_fehlt(tmp_path):
    db_path = _basis_db(tmp_path)
    try:
        plan_ausser_kraft(db_path, "/nirgends", "2026-03-01T00:00:00+01:00", "Grund", None)
        assert False
    except Ablehnung as e:
        assert "nicht gefunden" in str(e)


def test_ablehnung_kein_norm_traeger(tmp_path):
    db_path = _basis_db(tmp_path)
    try:
        plan_ausser_kraft(db_path, "/fakt/x", "2026-03-01T00:00:00+01:00", "Grund", None)
        assert False
    except Ablehnung as e:
        assert "keine Norm" in str(e)


def test_ablehnung_ab_vor_gilt_ab(tmp_path):
    db_path = _basis_db(tmp_path)
    try:
        plan_ausser_kraft(db_path, "/adr/x", "2025-01-01T00:00:00+01:00", "Grund", None)
        assert False
    except Ablehnung as e:
        assert "vor gilt_ab" in str(e)


def test_ablehnung_bereits_ausser_kraft(tmp_path):
    db_path = _basis_db(tmp_path)
    ausser_kraft(db_path, "/adr/x", "2026-03-01T00:00:00+01:00", "Erstgrund", None, apply=True)
    try:
        plan_ausser_kraft(db_path, "/adr/x", "2026-04-01T00:00:00+01:00", "Zweitgrund", None)
        assert False
    except Ablehnung as e:
        assert "bereits ausser Kraft" in str(e) and "2026-03-01" in str(e)


def test_wegen_ist_pflicht(tmp_path):
    db_path = _basis_db(tmp_path)
    try:
        plan_ausser_kraft(db_path, "/adr/x", "2026-03-01T00:00:00+01:00", "", None)
        assert False
    except Ablehnung as e:
        assert "Pflicht" in str(e)


def test_abgeloest_durch_muss_norm_sein(tmp_path):
    db_path = _basis_db(tmp_path)
    try:
        plan_ausser_kraft(db_path, "/adr/x", "2026-03-01T00:00:00+01:00", "Grund", "/fakt/x")
        assert False
    except Ablehnung as e:
        assert "kein gueltiger Vorgang" in str(e)


def test_dry_run_schreibt_nichts(tmp_path):
    db_path = _basis_db(tmp_path)
    result = ausser_kraft(db_path, "/adr/x", "2026-03-01T00:00:00+01:00", "Grund", None, apply=False)
    assert result["backup"] is None
    conn = sqlite3.connect(str(db_path))
    val = conn.execute("SELECT gilt_bis FROM knowledge_nodes WHERE path='/adr/x'").fetchone()[0]
    conn.close()
    assert val is None


def test_erfolgsfall_setzt_gilt_bis_content_und_access_log(tmp_path):
    db_path = _basis_db(tmp_path)
    result = ausser_kraft(db_path, "/adr/x", "2026-03-01T00:00:00+01:00", "Testgrund", "/adr/y", apply=True)
    assert result["backup"] and Path(result["backup"]).exists()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT gilt_bis, content FROM knowledge_nodes WHERE path='/adr/x'").fetchone()
        assert row["gilt_bis"] == "2026-03-01T00:00:00+01:00"
        assert "Testgrund" in row["content"]
        assert "/adr/y" in row["content"]

        log_row = conn.execute(
            "SELECT action, query, node_path FROM access_log WHERE action='ausser_kraft' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert log_row["action"] == "ausser_kraft"
        assert log_row["query"] == "Testgrund"
        assert log_row["node_path"] == "/adr/x"
    finally:
        conn.close()


def test_idempotenz_zweiter_lauf_lehnt_ab_und_aendert_nichts(tmp_path):
    db_path = _basis_db(tmp_path)
    ausser_kraft(db_path, "/adr/x", "2026-03-01T00:00:00+01:00", "Erstgrund", None, apply=True)
    try:
        ausser_kraft(db_path, "/adr/x", "2026-04-01T00:00:00+01:00", "Nochmal", None, apply=True)
        assert False
    except Ablehnung:
        pass
    conn = sqlite3.connect(str(db_path))
    val = conn.execute("SELECT gilt_bis FROM knowledge_nodes WHERE path='/adr/x'").fetchone()[0]
    conn.close()
    assert val == "2026-03-01T00:00:00+01:00"


def test_in_kraft_gegenprobe_vor_und_nach_stichtag(tmp_path):
    db_path = _basis_db(tmp_path)
    ausser_kraft(db_path, "/adr/x", "2026-03-01T00:00:00+01:00", "Grund", None, apply=True)

    vor = {r["path"] for r in in_kraft(db_path, "2026-02-01T00:00:00+01:00")}
    assert "/adr/x" in vor
    assert "/adr/y" in vor
    assert "/fakt/x" not in vor

    nach = {r["path"] for r in in_kraft(db_path, "2026-04-01T00:00:00+01:00")}
    assert "/adr/x" not in nach
    assert "/adr/y" in nach
    assert "/fakt/x" not in nach
