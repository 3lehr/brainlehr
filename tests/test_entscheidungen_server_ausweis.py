"""ADR-020 (docs/adr/ADR-020-mcp-server-klient-des-dienstes.md), Abschnitt 5,
Schritt 1: die Origin-Pruefung auf den schreibenden Endpunkten von
berichte/entscheidungen_server.py wird durch eine echte Ausweispruefung
(kern/ausweis.py) ERGAENZT -- nicht ersetzt, siehe Begruendung im Code
(_SCHREIBRECHT-Block dort).

ROT VOR GRUEN, woertlich gezeigt: der Stand vor dieser Aenderung (git show
HEAD -- der Commit, der vor diesem liegt) traegt in _herkunft_ok()s
Docstring selbst den Befund "0 Treffer fuer ausweis|Authorization|token" --
also GAB es dort keinen Ausweis-Kopf, den irgendein Aufruf haette
mitschicken muessen. test_post_mit_nur_origin_ging_vorher_durch_jetzt_nicht
zeigt das nicht nur behauptet, sondern gemessen: derselbe Aufruf, der frueher
(siehe tests/test_entscheidungen_server_herkunft.py,
test_post_mit_eigenem_origin_wird_angenommen) mit 200 durchging, liefert
jetzt 403, wenn kein Ausweis-Kopf dabei ist.

Getroffener Endpunkt: /api/abrufweg -- reine Lesefunktion (RO-Verbindung),
kein Seiteneffekt im Test noetig, dieselbe Wahl wie in der Herkunfts-Datei.
"""
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
def bestand(tmp_path, monkeypatch):
    """Eigene Ausweisdatei je Test -- ueber BRAINLEHR_AUSWEISE, denselben Weg,
    den kern/ausweis.py::ausweisdatei() selbst vorsieht. Der Dienst liest sie
    bei jedem Aufruf frisch (loese_auf() ohne festen pfad -> ausweisdatei())."""
    pfad = tmp_path / "ausweise.json"
    monkeypatch.setenv("BRAINLEHR_AUSWEISE", str(pfad))
    monkeypatch.delenv("BRAINLEHR_GEHEIMNIS", raising=False)
    gruender = ausweis.anlegen("gruender", ["betreiber"], art="mensch", pfad=pfad)
    return pfad, gruender


def _post(server, headers: dict, body: bytes = b'{"text": ""}') -> int:
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    hdr = {"Content-Type": "application/json", "Content-Length": str(len(body)),
           "Origin": f"http://127.0.0.1:{server.server_port}"}
    hdr.update(headers)
    conn.request("POST", "/api/abrufweg", body=body, headers=hdr)
    resp = conn.getresponse()
    resp.read()
    conn.close()
    return resp.status


# --- Rot vor gruen -----------------------------------------------------------

def test_post_mit_nur_origin_ging_vorher_durch_jetzt_nicht(server, bestand):
    # Kein Authorization-Kopf, nur der (gueltige) Origin -- genau das, was
    # ein beliebiges Programm heute frei setzen kann. Vor diesem Auftrag: 200.
    assert _post(server, {}) == 403


# --- Gegenprobe in beide Richtungen ------------------------------------------

def test_gueltiger_ausweis_geht_durch(server, bestand):
    pfad, gruender = bestand
    assert _post(server, {"Authorization": f"Bearer {gruender}"}) == 200


def test_widerrufener_ausweis_wird_abgewiesen(server, bestand):
    pfad, gruender = bestand
    g = ausweis.anlegen("hausmeister", ["betreiber"], aussteller=gruender, pfad=pfad)
    assert _post(server, {"Authorization": f"Bearer {g}"}) == 200  # vor dem Widerruf: gueltig
    ausweis.widerrufen("hausmeister", aussteller=gruender, pfad=pfad)
    assert _post(server, {"Authorization": f"Bearer {g}"}) == 403


def test_abgelaufener_ausweis_wird_abgewiesen(server, bestand):
    pfad, gruender = bestand
    vergangen = "2020-01-01T00:00:00+00:00"
    g = ausweis.anlegen("kurzgast", ["betreiber"], aussteller=gruender,
                        gilt_bis=vergangen, pfad=pfad)
    assert _post(server, {"Authorization": f"Bearer {g}"}) == 403


# --- Grenzwerte ---------------------------------------------------------------

def test_kein_kopf_wird_abgewiesen(server, bestand):
    assert _post(server, {}) == 403


def test_leerer_kopf_wird_abgewiesen(server, bestand):
    assert _post(server, {"Authorization": ""}) == 403


def test_kopf_ohne_bearer_praefix_wird_abgewiesen(server, bestand):
    pfad, gruender = bestand
    assert _post(server, {"Authorization": gruender}) == 403


def test_unbekannter_name_wird_abgewiesen(server, bestand):
    assert _post(server, {"Authorization": "Bearer irgendein-geratenes-geheimnis"}) == 403


def test_gueltiger_name_mit_falschem_geheimnis_wird_abgewiesen(server, bestand):
    pfad, gruender = bestand
    ausweis.anlegen("leser1", ["leser"], geheimnis="korrektes-geheimnis-xyz",
                    aussteller=gruender, pfad=pfad)
    assert _post(server, {"Authorization": "Bearer falsches-geheimnis-xyz"}) == 403


def test_ausweis_ohne_noetige_rolle_wird_abgewiesen(server, bestand):
    """'leser' traegt nur wissen:lesen/lehre:lesen/... -- nicht
    verwaltung:schreiben. Beglaubigt, aber ohne das verlangte Recht."""
    pfad, gruender = bestand
    g = ausweis.anlegen("leser2", ["leser"], aussteller=gruender, pfad=pfad)
    assert _post(server, {"Authorization": f"Bearer {g}"}) == 403


# --- Ausweis-Bruecke bleibt beim Origin-Weg (Zwischenstand, siehe Code) -----

def test_ausweisliste_get_bleibt_ungeprueft(server):
    """GET war nie betroffen -- nur POST bekommt die neue Pruefung."""
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    conn.request("GET", "/api/ausweisliste")
    resp = conn.getresponse()
    resp.read()
    conn.close()
    assert resp.status == 200


def test_herkunftspruefung_bleibt_zusaetzlich_bestehen(server, bestand):
    """Zwei Schranken, nicht eine getauschte: ein gueltiger Ausweis OHNE
    passenden Origin wird weiterhin abgewiesen -- _herkunft_ok() laeuft nach
    wie vor VOR der Ausweispruefung."""
    pfad, gruender = bestand
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    body = b'{"text": ""}'
    hdr = {"Content-Type": "application/json", "Content-Length": str(len(body)),
           "Authorization": f"Bearer {gruender}", "Origin": "http://boese.example"}
    conn.request("POST", "/api/abrufweg", body=body, headers=hdr)
    resp = conn.getresponse()
    resp.read()
    conn.close()
    assert resp.status == 403
