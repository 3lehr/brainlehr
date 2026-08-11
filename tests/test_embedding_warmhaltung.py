"""Der zweite Suchkanal darf nicht am Modell-Kaltstart verhungern.

BEFUND, gemessen 2026-08-11T12:08:00+0200:

    Kaltstart bge-m3 ueber Ollama   11,5 s
    Timeout in kern/embeddings.py    5,0 s
    warmer Aufruf                    0,12 s

Jeder Einbettungsversuch lief damit in den Timeout und gab still None zurueck.
embed_text ist ausdruecklich "best effort" und faellt lautlos auf Stichwort-
Suche zurueck -- deshalb fiel es niemandem auf. Folge im Bestand: 3323 Vektoren,
juengster vom 2026-08-10T12:26. Alles seither Angelegte hat keinen Vektor und
ist nur ueber den Trigramm-Index auffindbar.

DER TEUFELSKREIS, der es dauerhaft machte: Ollama entlaedt das Modell nach
Leerlauf. Der naechste Aufruf muss es laden, braucht dafuer laenger als der
Timeout erlaubt, bricht ab -- und weil er abbricht, wird das Modell nie warm.
Ein hoeherer Timeout allein wuerde jeden ersten Aufruf teuer machen; keep_alive
allein hilft nicht, wenn schon der erste Versuch in den Timeout laeuft. Beides
zusammen loest es.

FORMAT VON keep_alive: mit Einheit. L-ce7310 haelt fest, dass Ollama den Wert
"-1" mit HTTP 400 ablehnt ("time: missing unit in duration") -- eine Zahl ohne
Einheit ist kein gueltiger Wert.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path.insert(0, str(_w / "kern"))

import embeddings  # noqa: E402


def test_timeout_deckt_den_kaltstart(monkeypatch):
    """ROT VOR GRUEN: 5,0 s lagen unter der gemessenen Ladezeit von 11,5 s."""
    gesehen = {}

    def falscher_urlopen(req, timeout=None):
        gesehen["timeout"] = timeout
        raise TimeoutError("Probe")

    monkeypatch.setattr(embeddings.urllib.request, "urlopen", falscher_urlopen)
    embeddings.embed_text("Probe")
    assert gesehen["timeout"] >= 15, \
        (f"Vorgabe-Timeout {gesehen['timeout']} s deckt den gemessenen "
         f"Kaltstart von 11,5 s nicht")


def test_keep_alive_wird_mitgeschickt(monkeypatch):
    """Ohne Warmhaltung faellt das Modell zurueck in den Kaltstart, und der
    naechste Schreibvorgang zahlt ihn erneut."""
    gesehen = {}

    def falscher_urlopen(req, timeout=None):
        gesehen["payload"] = json.loads(req.data.decode("utf-8"))
        raise TimeoutError("Probe")

    monkeypatch.setattr(embeddings.urllib.request, "urlopen", falscher_urlopen)
    embeddings.embed_text("Probe")
    assert "keep_alive" in gesehen["payload"], "keine Warmhaltung angefordert"


def test_keep_alive_traegt_eine_einheit(monkeypatch):
    """NEGATIVFALL aus L-ce7310: Ollama lehnt einen Wert ohne Zeiteinheit mit
    HTTP 400 ab. Eine blosse Zahl -- auch '-1' -- ist unzulaessig."""
    gesehen = {}

    def falscher_urlopen(req, timeout=None):
        gesehen["payload"] = json.loads(req.data.decode("utf-8"))
        raise TimeoutError("Probe")

    monkeypatch.setattr(embeddings.urllib.request, "urlopen", falscher_urlopen)
    embeddings.embed_text("Probe")
    wert = str(gesehen["payload"]["keep_alive"])
    assert wert[-1].isalpha(), f"keep_alive {wert!r} hat keine Zeiteinheit"


def test_stiller_rueckfall_bleibt(monkeypatch):
    """GEGENPROBE: Die Aenderung darf das Verhalten bei echtem Ausfall nicht
    verschieben -- ein nicht erreichbarer Dienst gibt weiterhin None zurueck
    und wirft nicht. Sonst braeche jeder Schreibvorgang ohne Ollama ab."""
    def falscher_urlopen(req, timeout=None):
        raise OSError("kein Dienst")

    monkeypatch.setattr(embeddings.urllib.request, "urlopen", falscher_urlopen)
    assert embeddings.embed_text("Probe") is None
