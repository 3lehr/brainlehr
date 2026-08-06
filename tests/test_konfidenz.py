"""Tests fuer konfidenz.py (ADR-026 Z3, letztes bauliches Stueck).

Rot-vor-gruen: vor dieser Datei gab es konfidenz.py nicht -- jeder Import
schlug fehl (rot), und die confidence-Spalte hatte seit Bestehen nie einen
Schreibpfad ausser dem Vorgabewert (grep ueber shared-knowledge/*.py,
2026-08-06: 0 Treffer ausser INSERT-Defaults). Deckt die Formel an den drei
geforderten Grenzwerten, die Norm-Gegenprobe, die Wissensart-Klassifikation
und den vollen bestaetigen()-Rundlauf (Ablehnungen, dry-run, Erfolgsfall,
find_confidence_decay())."""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

from normkraft import Ablehnung  # noqa: E402
from konfidenz import (  # noqa: E402
    CET,
    HALBWERTSZEIT_TAGE,
    WISSENSART_ARCHITEKTUR,
    WISSENSART_BETRIEB,
    WISSENSART_STANDARD,
    _init_temp_db,
    _insert_node,
    bestaetigen,
    find_confidence_decay,
    gerechnete_konfidenz,
    plan_bestaetigen,
    wissensart,
)

_NOW = datetime.fromisoformat("2026-04-11T00:00:00+01:00")


def _ts(tage_zurueck: float) -> str:
    return (_NOW - timedelta(days=tage_zurueck)).isoformat()


def test_null_alter_ergibt_vollen_ausgangswert():
    g = gerechnete_konfidenz(0.8, _ts(0), None, "/standard/x", None, _NOW)
    assert abs(g - 0.8) < 1e-9


def test_eine_halbwertszeit_ergibt_die_haelfte():
    hwz = HALBWERTSZEIT_TAGE[WISSENSART_STANDARD]
    g = gerechnete_konfidenz(0.8, _ts(hwz), None, "/standard/x", None, _NOW)
    assert abs(g - 0.4) < 1e-9  # von Hand: 0.8 * 0.5**1


def test_zwei_halbwertszeiten_ergibt_ein_viertel():
    hwz = HALBWERTSZEIT_TAGE[WISSENSART_STANDARD]
    g = gerechnete_konfidenz(0.8, _ts(2 * hwz), None, "/standard/x", None, _NOW)
    assert abs(g - 0.2) < 1e-9  # von Hand: 0.8 * 0.5**2


def test_norm_verfaellt_nie_gegenprobe():
    """Der Kern des Auftrags: norm_rang gesetzt -> Ausgangswert bleibt,
    egal wie alt (hier ~55 Jahre)."""
    jung = gerechnete_konfidenz(0.9, _ts(0), 1, "/adr/x", "ADR", _NOW)
    uralt = gerechnete_konfidenz(0.9, _ts(20000), 1, "/adr/x", "ADR", _NOW)
    assert jung == 0.9
    assert uralt == 0.9


def test_wissensart_klassifikation():
    assert wissensart("/arch/mcp", None) == WISSENSART_ARCHITEKTUR
    assert wissensart("/shared/irgendwas", "Konsil 2026-08-05") == WISSENSART_ARCHITEKTUR
    assert wissensart("/shared/irgendwas", "docs/adr/ADR-026.md") == WISSENSART_ARCHITEKTUR
    assert wissensart("/testing/pytest", None) == WISSENSART_BETRIEB
    assert wissensart("/ops/appstoreconnect", None) == WISSENSART_BETRIEB
    assert wissensart("/lessons", None) == WISSENSART_STANDARD


def _basis_db(tmp_path):
    db_path = tmp_path / "knowledge.db"
    _init_temp_db(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        _insert_node(conn, "n-alt", "/standard/alt", confidence=0.8,
                     updated_at=_ts(HALBWERTSZEIT_TAGE[WISSENSART_STANDARD]))
        _insert_node(conn, "n-norm", "/adr/x", confidence=0.9, norm_rang=1, source="ADR")
        conn.commit()
    finally:
        conn.close()
    return db_path


def test_ablehnung_pfad_fehlt(tmp_path):
    db_path = _basis_db(tmp_path)
    try:
        plan_bestaetigen(db_path, "/nirgends", "Grund")
        assert False
    except Ablehnung as e:
        assert "nicht gefunden" in str(e)


def test_ablehnung_norm_braucht_keine_bestaetigung(tmp_path):
    db_path = _basis_db(tmp_path)
    try:
        plan_bestaetigen(db_path, "/adr/x", "Grund")
        assert False
    except Ablehnung as e:
        assert "Normen verfallen nicht" in str(e)


def test_wegen_ist_pflicht(tmp_path):
    db_path = _basis_db(tmp_path)
    try:
        plan_bestaetigen(db_path, "/standard/alt", "")
        assert False
    except Ablehnung as e:
        assert "Pflicht" in str(e)


def test_dry_run_schreibt_nichts(tmp_path):
    db_path = _basis_db(tmp_path)
    result = bestaetigen(db_path, "/standard/alt", "Grund", apply=False, now=_NOW)
    assert result["backup"] is None
    conn = sqlite3.connect(str(db_path))
    val = conn.execute("SELECT updated_at FROM knowledge_nodes WHERE path='/standard/alt'").fetchone()[0]
    conn.close()
    assert val != result["nachher_updated_at"]


def test_erfolgsfall_setzt_updated_at_content_und_access_log_konfidenz_springt_zurueck(tmp_path):
    db_path = _basis_db(tmp_path)
    result = bestaetigen(db_path, "/standard/alt", "Testgrund fuer Bestaetigung", apply=True, now=_NOW)
    assert abs(result["vorher_gerechnet"] - 0.4) < 1e-6  # nach 1 Halbwertszeit verfallen
    assert result["nachher_gerechnet"] == 0.8  # sofort nach Reset wieder voll
    assert result["backup"] and Path(result["backup"]).exists()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT updated_at, content, confidence FROM knowledge_nodes WHERE path='/standard/alt'"
        ).fetchone()
        assert row["updated_at"] == result["nachher_updated_at"]
        assert row["confidence"] == 0.8, "confidence-Spalte bleibt Ausgangswert, wird nie ueberschrieben"
        assert "Testgrund fuer Bestaetigung" in row["content"]

        log_row = conn.execute(
            "SELECT action, query, node_path FROM access_log WHERE action='bestaetigt' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert log_row["action"] == "bestaetigt"
        assert log_row["query"] == "Testgrund fuer Bestaetigung"
        assert log_row["node_path"] == "/standard/alt"
    finally:
        conn.close()


def test_ablehnung_ohne_begruendung_schreibt_trotz_apply_nichts(tmp_path):
    db_path = _basis_db(tmp_path)
    try:
        bestaetigen(db_path, "/standard/alt", "   ", apply=True, now=_NOW)
        assert False
    except Ablehnung:
        pass


def test_find_confidence_decay_findet_verfallenes_nie_normen(tmp_path):
    db_path = _basis_db(tmp_path)
    conn = sqlite3.connect(str(db_path))
    _insert_node(conn, "n-verfallen", "/standard/verfallen", confidence=0.8,
                 updated_at=_ts(5 * HALBWERTSZEIT_TAGE[WISSENSART_STANDARD]))
    conn.commit()
    conn.row_factory = sqlite3.Row
    try:
        decay = find_confidence_decay(conn, now=_NOW)
    finally:
        conn.close()
    decay_paths = {d["path"] for d in decay}
    assert "/standard/verfallen" in decay_paths
    assert "/adr/x" not in decay_paths, "Norm darf nie im Konfidenzverfall auftauchen"
