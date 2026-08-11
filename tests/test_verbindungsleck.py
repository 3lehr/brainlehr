"""Eine geplatzte Werkzeugausfuehrung darf keine Schreibsperre hinterlassen.

ANLASS, gemessen am 2026-08-11: Ab 14:10 konnte keine Sitzung mehr in die
Wissensdatenbank schreiben. lesson_record, knowledge_add und freigabe_setzen
liefen alle in 'database is locked'. Der Halter war EIN Serverprozess mit einer
offenen Schreibtransaktion, untaetig seit Stunden (PID 25897, fremde Sitzung,
0,68 s Rechenzeit in 2:40 h Laufzeit). Nachgewiesen durch Ausschluss: den
eigenen Server beendet, die Sperre blieb.

Die vorhandene Dateisperre _write_lock() fing das nicht ab -- sie gibt im
finally die flock frei, nicht die SQLite-Verbindung. Zwei Sperren, nur eine
hatte ein finally.

Geprueft wird der Weg, auf dem es passiert ist: ein Werkzeug wirft mitten in
einer offenen Transaktion. Danach muss ein FREMDER Schreiber sofort drankommen.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))

import knowledge_mcp_server as kms  # noqa: E402


@pytest.fixture()
def db(tmp_path, monkeypatch):
    pfad = tmp_path / "probe.db"
    monkeypatch.setattr(kms, "DB_PATH", pfad)
    conn = kms.get_db()          # legt Schema an
    kms._offene_verbindungen_schliessen()
    del conn
    return pfad


def _fremder_schreiber_kommt_dran(pfad: Path, timeout_s: float = 2.0) -> bool:
    """Ein zweiter, unbeteiligter Schreiber -- genau die Rolle, die am
    2026-08-11 stundenlang nicht drankam."""
    fremd = sqlite3.connect(str(pfad), timeout=timeout_s)
    try:
        fremd.execute("BEGIN IMMEDIATE")
        fremd.rollback()
        return True
    except sqlite3.OperationalError:
        return False
    finally:
        fremd.close()


def test_werkzeug_das_platzt_hinterlaesst_keine_sperre(db, monkeypatch):
    """ROT vor dem Fix: die Verbindung des geplatzten Werkzeugs blieb mit
    offener Transaktion stehen, jeder weitere Schreiber lief in 'locked'."""
    def platzt(args):
        conn = kms.get_db()
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT INTO knowledge_nodes (id, path, title, summary, level, source, "
                      "norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
                      "VALUES (?,?,'t','s',0,'Test','keine_norm','test','Testfall')", ("x", "/x"))
        raise RuntimeError("Werkzeug geplatzt, mitten in der Transaktion")

    monkeypatch.setitem(kms.TOOLS, "_probe", {"description": "Probe", "inputSchema": {},
                                               "handler": platzt})
    antwort = kms.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                   "params": {"name": "_probe", "arguments": {}}})

    assert antwort["result"]["isError"] is True, "der Fehler muss gemeldet werden"
    assert _fremder_schreiber_kommt_dran(db), \
        "nach einem geplatzten Werkzeug haelt noch jemand die Schreibsperre"


def test_geplatzte_transaktion_wird_verworfen(db, monkeypatch):
    """Gegenprobe zur Aufraeumung: der halb geschriebene Satz darf NICHT in
    der Datenbank landen. Ein close() ohne rollback() waere die stille
    Variante, bei der er je nach Aufraeumreihenfolge doch drin steht."""
    def platzt(args):
        conn = kms.get_db()
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT INTO knowledge_nodes (id, path, title, summary, level, source, "
                      "norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
                      "VALUES (?,?,'t','s',0,'Test','keine_norm','test','Testfall')", ("geist", "/geist"))
        raise RuntimeError("geplatzt")

    monkeypatch.setitem(kms.TOOLS, "_probe", {"description": "Probe", "inputSchema": {},
                                               "handler": platzt})
    kms.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                        "params": {"name": "_probe", "arguments": {}}})

    pruef = sqlite3.connect(str(db))
    try:
        treffer = pruef.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE id='geist'").fetchone()[0]
    finally:
        pruef.close()
    assert treffer == 0, "die geplatzte Transaktion wurde nicht zurueckgerollt"


def test_erfolgreiches_werkzeug_bleibt_unberuehrt(db, monkeypatch):
    """Negativfall: die Aufraeumung darf einem SAUBEREN Lauf nichts wegnehmen.
    Ohne diesen Fall wuerde ein rollback() am falschen Ort jede Schreibung
    verwerfen und der erste Test bliebe trotzdem gruen."""
    def schreibt(args):
        conn = kms.get_db()
        conn.execute("INSERT INTO knowledge_nodes (id, path, title, summary, level, source, "
                      "norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
                      "VALUES (?,?,'t','s',0,'Test','keine_norm','test','Testfall')", ("bleibt", "/bleibt"))
        conn.commit()
        return {"ok": True}

    monkeypatch.setitem(kms.TOOLS, "_probe", {"description": "Probe", "inputSchema": {},
                                               "handler": schreibt})
    antwort = kms.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                   "params": {"name": "_probe", "arguments": {}}})

    assert "isError" not in antwort["result"], antwort
    pruef = sqlite3.connect(str(db))
    try:
        treffer = pruef.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE id='bleibt'").fetchone()[0]
    finally:
        pruef.close()
    assert treffer == 1, "ein sauber begangener Satz darf nicht mit aufgeraeumt werden"
    assert _fremder_schreiber_kommt_dran(db)


def test_mehrere_verbindungen_im_selben_aufruf(db, monkeypatch):
    """Der gemessene Fall hatte FUENF offene Verbindungen an einem Prozess --
    aufgeraeumt werden muessen alle, nicht die letzte."""
    def mehrfach(args):
        for _ in range(5):
            kms.get_db().execute("BEGIN IMMEDIATE")
        raise RuntimeError("geplatzt")

    monkeypatch.setitem(kms.TOOLS, "_probe", {"description": "Probe", "inputSchema": {},
                                               "handler": mehrfach})
    kms.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                        "params": {"name": "_probe", "arguments": {}}})

    assert kms._OFFENE_VERBINDUNGEN == [], "es blieb eine Verbindung offen"
    assert _fremder_schreiber_kommt_dran(db)
