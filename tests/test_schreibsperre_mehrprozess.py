"""Tests fuer die prozessuebergreifende Schreibsperre (Auftrag 2026-08-08
Punkt 3): mehrere gleichzeitige knowledge_mcp_server.py-Prozesse kollidierten
in SQLite mit "database is locked" (busy_timeout=2000ms reicht bei echtem
Gedraenge nicht, SQLites Busy-Retry ist nicht fair).

Kernfall wird mit ZWEI ECHTEN Prozessen belegt (nicht zwei Aufrufen im
selben Prozess) -- ueber BEGOD_KNOWLEDGE_DB auf eine tmp-DB gebogen (gleiches
Muster wie test_begod_knowledge_db_env.py), stdio-JSON-RPC wie ein echter
MCP-Client.
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
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
SERVER = SHARED_KNOWLEDGE / "knowledge_mcp_server.py"

sys.path.insert(0, str(SHARED_KNOWLEDGE))
import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


@pytest.fixture()
def temp_db_path(tmp_path):
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    return db_path


def _rpc(proc: subprocess.Popen, req: dict) -> dict:
    proc.stdin.write(json.dumps(req) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    assert line, f"kein Response, stderr: {proc.stderr.read() if proc.stderr else '?'}"
    return json.loads(line)


def _spawn(db_path: Path) -> subprocess.Popen:
    env = dict(os.environ, BEGOD_KNOWLEDGE_DB=str(db_path))
    proc = subprocess.Popen(
        [sys.executable, str(SERVER)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env=env,
    )
    _rpc(proc, {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})
    return proc


def _add_call(i: int) -> dict:
    return {
        "jsonrpc": "2.0", "id": i, "method": "tools/call",
        "params": {
            "name": "knowledge_add",
            "arguments": {
                "parent_path": "/", "title": f"Lock-Test {i}",
                "summary": "Schreibsperren-Test", "source": "test_schreibsperre_mehrprozess.py",
                "anlass": "skript", "norm_entscheidung": "keine_norm",
                "norm_entschieden_grund": "Testvorrichtung, keine echte Norm-Pruefung",
            },
        },
    }


def test_zwei_echte_prozesse_schreiben_gleichzeitig_beide_kommen_an(temp_db_path):
    """Kernfall der Abnahme: zwei echte Prozesse, gleichzeitig gestartete
    Schreibvorgaenge, keiner scheitert mit 'database is locked'."""
    p1 = _spawn(temp_db_path)
    p2 = _spawn(temp_db_path)
    try:
        # In sqlite3.Connection() nicht verwendbar hier -- roher Text-Check
        # der Antwort reicht, das ist der eigentliche Beleg.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(_rpc, p1, _add_call(1))
            f2 = pool.submit(_rpc, p2, _add_call(2))
            r1, r2 = f1.result(timeout=30), f2.result(timeout=30)
    finally:
        p1.terminate()
        p2.terminate()
        p1.wait(timeout=5)
        p2.wait(timeout=5)

    for r in (r1, r2):
        assert not r["result"].get("isError"), r
        text = r["result"]["content"][0]["text"]
        assert "database is locked" not in text, text
        payload = json.loads(text)
        assert "error" not in payload, payload

    conn = sqlite3.connect(str(temp_db_path))
    titles = {row[0] for row in conn.execute(
        "SELECT title FROM knowledge_nodes WHERE title LIKE 'Lock-Test %'")}
    conn.close()
    assert titles == {"Lock-Test 1", "Lock-Test 2"}


def test_rot_vor_gruen_ohne_sperre_kollidiert_wirklich(temp_db_path, monkeypatch):
    """Gegenprobe: OHNE die Sperre (busy_timeout allein) kollidieren zwei
    Schreiber, die absichtlich laenger als BUSY_TIMEOUT_MS blockieren --
    belegt, dass der Kernfall oben tatsaechlich etwas Reales behebt und
    nicht zufaellig nie ausgeloest wird."""
    monkeypatch.setattr(kms, "DB_PATH", temp_db_path)
    conn_blocker = sqlite3.connect(str(temp_db_path), timeout=0)
    conn_blocker.execute("PRAGMA journal_mode=WAL")
    conn_blocker.execute("BEGIN IMMEDIATE")
    conn_blocker.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, title, summary, source, "
        "anlass, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
        "VALUES ('x', '/x', '/', 'x', 'x', 'test', 'skript', 'keine_norm', 'skript:test', 'Testvorrichtung')")
    try:
        conn2 = sqlite3.connect(str(temp_db_path), timeout=0.2)
        conn2.execute("PRAGMA busy_timeout=200")
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            conn2.execute(
                "INSERT INTO knowledge_nodes (id, path, parent_path, title, summary, source, "
                "anlass, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
                "VALUES ('y', '/y', '/', 'y', 'y', 'test', 'skript', 'keine_norm', 'skript:test', 'Testvorrichtung')")
        conn2.close()
    finally:
        conn_blocker.rollback()
        conn_blocker.close()


def test_schreibsperre_scheitert_ehrlich_ueber_obergrenze(monkeypatch, temp_db_path):
    """Ueberschreitet die Obergrenze -> sprechender RuntimeError, kein
    endloses Haengen."""
    monkeypatch.setattr(kms, "DB_PATH", temp_db_path)
    monkeypatch.setattr(kms, "_WRITE_LOCK_TIMEOUT_S", 0.3)

    import fcntl
    lock_path = temp_db_path.parent / f"{temp_db_path.name}.lock"
    holder_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(holder_fd, fcntl.LOCK_EX)
    try:
        start = time.monotonic()
        with pytest.raises(RuntimeError, match="Schreibsperre"):
            with kms._write_lock():
                pass
        elapsed = time.monotonic() - start
        assert elapsed < 2.0, f"haengt laenger als die Obergrenze: {elapsed}s"
    finally:
        fcntl.flock(holder_fd, fcntl.LOCK_UN)
        os.close(holder_fd)


def test_alt_neben_neu_schreiber_ohne_sperre_bleibt_funktionsfaehig(monkeypatch, temp_db_path):
    """Ein 'alter' Schreiber, der _write_lock gar nicht kennt (direkter
    get_db()-Aufruf, wie jeder Handler das vor diesem Auftrag tat), schreibt
    weiterhin erfolgreich, WAEHREND ein 'neuer' Prozessteil die Sperre
    haelt -- alt wird nicht ausgesperrt."""
    monkeypatch.setattr(kms, "DB_PATH", temp_db_path)

    with kms._write_lock():
        conn = kms.get_db()
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, parent_path, title, summary, source, "
            "anlass, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
            "VALUES ('alt', '/alt', '/', 'alt', 'alt', "
            "'test', 'skript', 'keine_norm', 'skript:test', 'Testvorrichtung')"
        )
        conn.commit()
        conn.close()

    conn = sqlite3.connect(str(temp_db_path))
    row = conn.execute("SELECT title FROM knowledge_nodes WHERE id='alt'").fetchone()
    conn.close()
    assert row == ("alt",)


def test_listchanged_false_und_tools_zur_laufzeit_unveraenderlich(temp_db_path, monkeypatch):
    """Punkt 2: listChanged bleibt False. Beleg dafuer, dass das gerechtfertigt
    ist (nicht nur konservativ): TOOLS ist dieselbe dict-Identitaet vor und
    nach einem vollen tools/list + tools/call-Zyklus -- kein Codepfad
    mutiert sie zur Laufzeit, also gibt es nie ein Ereignis, das eine
    listChanged-Notification ausloesen wuerde."""
    monkeypatch.setattr(kms, "DB_PATH", temp_db_path)
    resp = kms.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert resp["result"]["capabilities"]["tools"]["listChanged"] is False

    tools_before = id(kms.TOOLS)
    names_before = sorted(kms.TOOLS.keys())
    kms.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    kms.handle_request({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "knowledge_stats", "arguments": {}},
    })
    assert id(kms.TOOLS) == tools_before
    assert sorted(kms.TOOLS.keys()) == names_before
