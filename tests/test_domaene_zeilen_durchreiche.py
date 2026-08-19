"""Die Zeilen einer Domaene ueber den Wissensraum holen -- fuer Klienten, die
den Fachdienst nicht selbst erreichen koennen.

ANLASS (Betreiberfrage 2026-08-19): „fuer die webui braeuchten wir die zwei
wege dann garnicht?" Gemessen an diesem Tag: Doch -- und der zweite wird sogar
schwerer. `/api/domaene-dienst` gibt dem Klienten eine PORTNUMMER und erwartet,
dass er sich selbst verbindet. Eine native Anwendung kann das. Eine Seite im
Browser nicht: der Fachdienst sendet keine CORS-Koepfe, ein Abruf von einer
Seite auf Port 8799 nach 8812 waere fremder Herkunft und wird abgewiesen.

DIE GEWAEHLTE ANTWORT ist die Durchreiche, nicht CORS am Fachdienst. CORS
oeffnete ihn fuer JEDE lokale Seite; die Durchreiche laesst ihn geschlossen und
gibt dem Browser genau eine Herkunft.
"""
from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]
if str(WURZEL) not in sys.path:
    sys.path.insert(0, str(WURZEL))

from berichte import entscheidungen_server as server  # noqa: E402


@pytest.fixture()
def fachdienst():
    """Ein Fachdienst, wie ihn eine Domaene mitbringt -- klein, aber echt:
    er antwortet ueber HTTP, damit die Durchreiche wirklich etwas durchreicht
    und nicht eine Attrappe im selben Prozess."""
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            rumpf = json.dumps({"zeilen": [{"quelle": "estg", "faellig": "ja"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(rumpf)))
            self.end_headers()
            self.wfile.write(rumpf)

        def log_message(self, *_):
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield httpd.server_port
    httpd.shutdown()


def test_durchreiche_gibt_es():
    assert hasattr(server, "_domaene_zeilen")


def test_zeilen_kommen_durch(fachdienst, monkeypatch):
    monkeypatch.setattr(server, "_domaene_dienst", lambda _d: {
        "importiert": True,
        "dienst": {"horcht_auf": fachdienst, "lebenszeichen": "/gesundheit", "zeilen": "/zeilen"},
    })
    ergebnis = server._domaene_zeilen("einzelunternehmer")
    assert ergebnis["zeilen"] == [{"quelle": "estg", "faellig": "ja"}]


def test_nicht_importierte_domaene_liefert_keine_erfundenen_zeilen(monkeypatch):
    monkeypatch.setattr(server, "_domaene_dienst", lambda _d: {"importiert": False})
    ergebnis = server._domaene_zeilen("gibtsnicht")
    assert ergebnis.get("zeilen") == []
    assert ergebnis.get("meldung"), "kein Satz fuer den Menschen"


def test_dienst_antwortet_nicht_wird_benannt_statt_als_leer_ausgegeben(monkeypatch):
    """Der Unterschied, an dem heute schon dreimal etwas haengen blieb: 'nichts
    da' und 'nicht erreichbar' sehen auf dem Bildschirm gleich aus."""
    monkeypatch.setattr(server, "_domaene_dienst", lambda _d: {
        "importiert": True,
        "dienst": {"horcht_auf": 1, "lebenszeichen": "/gesundheit", "zeilen": "/zeilen"},
    })
    ergebnis = server._domaene_zeilen("einzelunternehmer")
    assert ergebnis.get("zeilen") == []
    assert ergebnis.get("erreichbar") is False
    assert ergebnis.get("meldung")
