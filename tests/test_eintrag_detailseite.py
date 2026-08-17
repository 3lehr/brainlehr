from __future__ import annotations

import http.client
import sqlite3
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "berichte"))
sys.path.insert(0, str(REPO / "kern"))

import entscheidungen_server as es  # noqa: E402


@pytest.fixture()
def server(tmp_path, monkeypatch):
    db = tmp_path / "brainlehr.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE knowledge_nodes (
            id TEXT PRIMARY KEY, path TEXT, title TEXT, summary TEXT,
            content TEXT, source TEXT, freigabe TEXT, zurueckgezogen INTEGER
        );
        CREATE TABLE lessons_learned (
            id TEXT PRIMARY KEY, type TEXT, severity TEXT, description TEXT,
            root_cause TEXT, resolution TEXT, prevention TEXT, status TEXT,
            freigabe TEXT
        );
        INSERT INTO knowledge_nodes VALUES
            ('1234abcd', '/test', 'Testknoten', 'Kurzfassung',
             'Volltext', 'Testquelle', 'intern', 0);
        INSERT INTO lessons_learned VALUES
            ('L-186d02', 'insight', 'high', '<script>Lehre</script>',
             'Ursache', 'Loesung', 'Vorbeugung', 'active', 'intern');
        """
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(es, "DB_PATH", db)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), es.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()


def _get(server, path: str, host: str | None = None):
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    conn.putrequest("GET", path, skip_host=host is not None)
    if host is not None:
        conn.putheader("Host", host)
    conn.endheaders()
    response = conn.getresponse()
    body = response.read().decode("utf-8")
    headers = dict(response.getheaders())
    conn.close()
    return response.status, headers, body


def test_lesson_und_knoten_werden_lokal_als_sichere_html_seite_angezeigt(server):
    status, headers, body = _get(server, "/eintrag/L-186d02")
    assert status == 200
    assert "L-186d02" in body and "Vorbeugung" in body
    assert "<script>" not in body and "&lt;script&gt;" in body
    assert headers["Cache-Control"] == "no-store"
    assert headers["X-Frame-Options"] == "DENY"

    status, _, body = _get(server, "/eintrag/1234abcd")
    assert status == 200
    assert "Testknoten" in body and "Volltext" in body


def test_detailseite_lehnt_fremden_host_und_unbekannte_kennung_ab(server):
    assert _get(server, "/eintrag/L-186d02", "boese.example")[0] == 403
    assert _get(server, "/eintrag/nicht-gueltig")[0] == 404
