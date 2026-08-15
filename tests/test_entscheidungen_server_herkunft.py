"""Sicherheitsfund O2 (docs/SICHERHEITSFUNDE_2026-08-14.md): POST auf 8799
pruefte weder Herkunft noch Kennung -- 0 Treffer fuer ausweis|Authorization|
token. Eine beliebige Seite im Browser des Betreibers genuegte fuer einen
Schreibzugriff, ohne Rechnerzugang.

Rot-vor-gruen-Beleg VOR dieser Aenderung (git show HEAD -- Stand vor dem
Fix, ausserhalb dieser Datei nachvollzogen, da hier nur der reparierte Stand
lebt): POST ohne jeden Kopf an /api/abrufweg lieferte 200. Dieser Test prueft
den reparierten Stand -- Origin muss exakt zum eigenen Ursprung passen,
Fetch setzt ihn bei POST-Anfragen immer, auch gleichursprnglich, das macht
ihn zur Schranke ohne Aenderung an entscheidungen.html (tabu fuer diesen
Auftrag).

Getroffen wird der Endpunkt /api/abrufweg -- reine Lesefunktion (RO-Verbindung
zur echten brainlehr.db), kein Schreibzugriff im Test noetig."""
from __future__ import annotations

import http.client
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "berichte"))
sys.path.insert(0, str(REPO / "kern"))

import entscheidungen_server as es  # noqa: E402
import ausweis  # noqa: E402


@pytest.fixture(scope="module")
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), es.Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    yield srv
    srv.shutdown()


@pytest.fixture()
def berechtigter_kopf(tmp_path, monkeypatch):
    """Seit ADR-020 Schritt 1 (tests/test_entscheidungen_server_ausweis.py)
    verlangt jeder schreibende Pfad zusaetzlich zum Origin einen gueltigen
    Ausweis-Kopf. Diese Datei prueft weiterhin NUR die Origin-Schranke --
    darum hier ein minimaler, berechtigter Ausweis, der die Origin-Tests
    unveraendert isoliert haelt."""
    pfad = tmp_path / "ausweise.json"
    monkeypatch.setenv("BRAINLEHR_AUSWEISE", str(pfad))
    monkeypatch.delenv("BRAINLEHR_GEHEIMNIS", raising=False)
    return {"Authorization": f"Bearer {ausweis.anlegen('gruender', ['betreiber'], art='mensch', pfad=pfad)}"}


def _post(server, headers: dict, body: bytes = b'{"text": ""}') -> int:
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    hdr = {"Content-Type": "application/json", "Content-Length": str(len(body))}
    hdr.update(headers)
    conn.request("POST", "/api/abrufweg", body=body, headers=hdr)
    resp = conn.getresponse()
    resp.read()
    conn.close()
    return resp.status


def test_post_ohne_origin_wird_abgelehnt(server):
    assert _post(server, {}) == 403


def test_post_mit_fremdem_origin_wird_abgelehnt(server):
    assert _post(server, {"Origin": "http://boese.example"}) == 403


def test_post_mit_leerem_origin_wird_abgelehnt(server):
    assert _post(server, {"Origin": ""}) == 403


def test_post_mit_falschem_port_wird_abgelehnt(server):
    assert _post(server, {"Origin": f"http://127.0.0.1:{server.server_port + 1}"}) == 403


def test_post_mit_eigenem_origin_wird_angenommen(server, berechtigter_kopf):
    # Gegenprobe: der legitime Weg (eigene Oberflaeche, 127.0.0.1, PLUS seit
    # ADR-020 Schritt 1 ein gueltiger Ausweis) funktioniert unveraendert --
    # eine Sperre, die auch den Eigenbetrieb bricht, ist keine Loesung.
    headers = {"Origin": f"http://127.0.0.1:{server.server_port}"}
    headers.update(berechtigter_kopf)
    status = _post(server, headers)
    assert status == 200
