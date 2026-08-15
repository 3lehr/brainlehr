"""Auftrag 2026-08-15: /api/domaene-import schrieb nichts (rief
domaene.pruefe() statt domaene.speichere()) und meldete der App trotzdem
"gilt jetzt" -- eine FALSCHE ERFOLGSMELDUNG (Befund vom selben Tag, siehe
berichte/entscheidungen_server.py::_domaene_import). Seit dieser Aenderung
ruft der Endpunkt domaene.speichere() -- das schreibt tatsaechlich, darum
gehoert er nicht mehr in _OHNE_KOPFPRUEFUNG (dieselbe Regel wie fuer jeden
anderen schreibenden Pfad, siehe test_entscheidungen_server_ausweis.py).

ROT VOR GRUEN, woertlich: vor diesem Auftrag stand "/api/fundstelle",
"/api/domaene-import" in _OHNE_KOPFPRUEFUNG (git show HEAD~N -- Commit vor
diesem). test_ohne_ausweis_wird_abgewiesen zeigt denselben Aufruf, der
frueher mit 200 durchging, liefert jetzt 403 ohne Ausweis-Kopf.

Absichtlich WIRD HIER NICHT in den echten Bestand geschrieben (die
Datenbank dieses Repos zaehlt gerade ein anderer Agent fuer eine
Guetemessung, siehe Auftrag): jedes Paket in diesem Modul ist so gebaut,
dass domaene.pruefe() es ABLEHNT (unbelegte Fundstelle) -- speichere()
schreibt bei Ablehnung nachweislich nichts (tests/test_domaene.py::
test_abgelehntes_paket_schreibt_nichts). Die Schreibung selbst (Wirkung
Null, Idempotenz, norm_rang) ist bereits in tests/test_domaene.py belegt;
hier wird nur geprueft, DASS der HTTP-Weg sie erreicht und DASS er den
Ausweis verlangt, bevor er es tut."""
from __future__ import annotations

import http.client
import json
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

# Wird von pruefe_regeln() sicher abgelehnt (Fundstelle passt zu keiner
# Quelle) -- kein Schreibvorgang moeglich, ganz gleich ob der Ausweis stimmt.
_ABGELEHNTES_PAKET = {
    "domaene": "testdomaene-abgelehnt",
    "bezeichnung": "Testpaket",
    "herkunft": "test",
    "stand": "2026-08-15T00:00:00+0200",
    "quellen": {"z1": {"bezeichnung": "Betriebsausgaben (netto)"}},
    "regeln": [{"id": "r1", "ziel_id": "z1", "fundstelle": "passt zu nichts hier"}],
}


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
    pfad = tmp_path / "ausweise.json"
    monkeypatch.setenv("BRAINLEHR_AUSWEISE", str(pfad))
    monkeypatch.delenv("BRAINLEHR_GEHEIMNIS", raising=False)
    gruender = ausweis.anlegen("gruender", ["betreiber"], art="mensch", pfad=pfad)
    return pfad, gruender


def _post(server, headers: dict, paket: dict) -> tuple[int, dict]:
    body = json.dumps(paket).encode("utf-8")
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    hdr = {"Content-Type": "application/json", "Content-Length": str(len(body)),
           "Origin": f"http://127.0.0.1:{server.server_port}"}
    hdr.update(headers)
    conn.request("POST", "/api/domaene-import", body=body, headers=hdr)
    resp = conn.getresponse()
    roh = json.loads(resp.read())
    conn.close()
    return resp.status, roh


# --- Rot vor gruen -------------------------------------------------------

def test_ohne_ausweis_wird_abgewiesen(server, bestand):
    status, roh = _post(server, {}, _ABGELEHNTES_PAKET)
    assert status == 403
    assert "error" in roh


# --- Gegenprobe in beide Richtungen ---------------------------------------

def test_mit_gueltigem_ausweis_kommt_die_domaenenpruefung_durch(server, bestand):
    """Der Ausweis oeffnet die Tuer, ersetzt aber nicht den Belegvertrag:
    ein unbelegtes Paket wird weiterhin sichtbar abgelehnt (Negativfall aus
    der Abnahme), nicht stillschweigend uebernommen."""
    pfad, gruender = bestand
    status, roh = _post(server, {"Authorization": f"Bearer {gruender}"}, _ABGELEHNTES_PAKET)
    assert status == 200
    assert roh["angenommen"] is False
    assert "r1" in roh["grund"]


# --- Grenzwerte ------------------------------------------------------------

def test_leerer_kopf_wird_abgewiesen(server, bestand):
    assert _post(server, {"Authorization": ""}, _ABGELEHNTES_PAKET)[0] == 403


def test_ausweis_ohne_schreibrecht_wird_abgewiesen(server, bestand):
    pfad, gruender = bestand
    g = ausweis.anlegen("leser", ["leser"], aussteller=gruender, pfad=pfad)
    assert _post(server, {"Authorization": f"Bearer {g}"}, _ABGELEHNTES_PAKET)[0] == 403


def test_herkunftspruefung_bleibt_zusaetzlich_bestehen(server, bestand):
    """Zwei Schranken: ein gueltiger Ausweis ohne passenden Origin wird
    weiterhin abgewiesen -- _herkunft_ok() laeuft VOR der Ausweispruefung."""
    pfad, gruender = bestand
    body = json.dumps(_ABGELEHNTES_PAKET).encode("utf-8")
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    hdr = {"Content-Type": "application/json", "Content-Length": str(len(body)),
           "Authorization": f"Bearer {gruender}", "Origin": "http://boese.example"}
    conn.request("POST", "/api/domaene-import", body=body, headers=hdr)
    resp = conn.getresponse()
    resp.read()
    conn.close()
    assert resp.status == 403
