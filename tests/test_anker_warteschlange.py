"""Tests fuer die Anker-Warteschlange (Auftrag 2026-08-06, Anschluss an
ankerverfahren.py). Rot-vor-gruen-Beleg: ein Ankerversuch darf niemals eine
Ausnahme nach oben durchreichen -- kein Netz, Zeitueberschreitung,
Dienstablehnung, fehlender Schluessel. Kein Netzaufruf: urllib.request.urlopen
wird ueberall gezielt gepatcht, nie wirklich aufgerufen.
"""
from __future__ import annotations

import json
import sys
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import ankerverfahren as av  # type: ignore  # noqa: E402
import knowledge_lint as lint  # type: ignore  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from cryptography.hazmat.primitives.serialization import (  # noqa: E402
    Encoding,
    NoEncryption,
    PrivateFormat,
)

BEREICH = {"von": 1, "bis": 4, "n": 4}
ZEIT = "2026-08-06T00:00:00+02:00"


@pytest.fixture()
def queue_path(tmp_path) -> Path:
    return tmp_path / "anker_warteschlange.json"


def _raise(exc):
    def _urlopen(*a, **k):
        raise exc
    return _urlopen


# ─── Abnahme 1: scheitert, kommt trotzdem erfolgreich zurueck, je Fehlerart ─

def test_versuche_anker_kein_netz_blockiert_nicht(monkeypatch, queue_path):
    monkeypatch.setattr(
        av.urllib.request, "urlopen",
        _raise(urllib.error.URLError(OSError("no route to host"))),
    )
    ergebnis = av.versuche_anker("rfc3161", "aaaa", BEREICH, ZEIT, queue_path=queue_path, senden=True)
    assert ergebnis["modus"] == "aufgeschoben"
    assert ergebnis["fehlerart"] == "netz"
    entries = json.loads(queue_path.read_text(encoding="utf-8"))
    assert len(entries) == 1
    assert entries[0]["fehlerart"] == "netz"
    assert entries[0]["status"] == "offen"


def test_versuche_anker_zeitueberschreitung_blockiert_nicht(monkeypatch, queue_path):
    monkeypatch.setattr(av.urllib.request, "urlopen", _raise(TimeoutError("timed out")))
    ergebnis = av.versuche_anker("rfc3161", "aaaa", BEREICH, ZEIT, queue_path=queue_path, senden=True)
    assert ergebnis["modus"] == "aufgeschoben"
    assert ergebnis["fehlerart"] == "zeitueberschreitung"
    entries = json.loads(queue_path.read_text(encoding="utf-8"))
    assert entries[0]["fehlerart"] == "zeitueberschreitung"


# ─── Abnahme 4: drei Fehlerarten, unterscheidbar (dritte: Dienstablehnung) ──

def test_versuche_anker_dienstablehnung_unterscheidbar(monkeypatch, queue_path):
    http_error = urllib.error.HTTPError("https://tsa.example/tsr", 400, "Bad Request", {}, None)
    monkeypatch.setattr(av.urllib.request, "urlopen", _raise(http_error))
    ergebnis = av.versuche_anker("rfc3161", "aaaa", BEREICH, ZEIT, queue_path=queue_path, senden=True)
    assert ergebnis["fehlerart"] == "abgelehnt"


def test_versuche_anker_fehlender_schluessel_blockiert_nicht(queue_path):
    ergebnis = av.versuche_anker("gegenzeichnung", "cccc", BEREICH, ZEIT, queue_path=queue_path, signieren=True)
    assert ergebnis["modus"] == "aufgeschoben"
    assert ergebnis["fehlerart"] == "schluessel_fehlt"
    entries = json.loads(queue_path.read_text(encoding="utf-8"))
    # Geheimnis nie in der Datei -- es gab hier keins, aber kwargs_sicher
    # darf den Schluessel-Schluessel gar nicht erst kennen.
    assert "private_key_pem" not in entries[0]["kwargs_sicher"]


# ─── Abnahme 3: Gegenprobe -- erfolgreicher Versuch landet NICHT in der Queue

def test_versuche_anker_erfolg_landet_nicht_in_queue(queue_path):
    beleg = av.versuche_anker("rfc3161", "aaaa", BEREICH, ZEIT, queue_path=queue_path)
    assert beleg["modus"] == "trocken"  # trockener Erfolg (kein senden=True)
    assert not queue_path.exists()


# ─── Abnahme 2: Nachholen -- gelingt, wird erledigt markiert, Beleg daneben ──

def test_nachholen_erfolgreich_markiert_erledigt(monkeypatch, queue_path):
    monkeypatch.setattr(av.urllib.request, "urlopen", _raise(urllib.error.URLError(OSError("kein netz"))))
    av.versuche_anker("rfc3161", "aaaa", BEREICH, ZEIT, queue_path=queue_path, senden=True)
    vor = av.rueckstand(queue_path)
    assert vor["anzahl"] == 1

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"\x30\x03\x02\x01\x00"

    monkeypatch.setattr(av.urllib.request, "urlopen", lambda *a, **k: _Resp())
    ergebnis = av.nachholen(queue_path=queue_path, ausfuehren=True)
    assert ergebnis["erledigt"] == 1

    nach = av.rueckstand(queue_path)
    assert nach["anzahl"] == 0  # Rueckstand um eins kleiner

    entries = json.loads(queue_path.read_text(encoding="utf-8"))
    assert entries[0]["status"] == "erledigt"
    assert entries[0]["beleg"] is not None  # Beleg daneben
    assert entries[0]["beleg"]["modus"] == "gesendet"


# ─── Abnahme 7: Trockenlauf ist Vorgabe, auch beim Nachholen ────────────────

def test_nachholen_ohne_ausfuehren_ruehrt_nichts_an(monkeypatch, queue_path):
    monkeypatch.setattr(av.urllib.request, "urlopen", _raise(urllib.error.URLError(OSError("kein netz"))))
    av.versuche_anker("rfc3161", "aaaa", BEREICH, ZEIT, queue_path=queue_path, senden=True)
    inhalt_vorher = queue_path.read_text(encoding="utf-8")

    def _schlaegt_fehl_wenn_gerufen(*a, **k):
        raise AssertionError("urlopen haette im Trockenlauf NICHT gerufen werden duerfen")

    monkeypatch.setattr(av.urllib.request, "urlopen", _schlaegt_fehl_wenn_gerufen)
    ergebnis = av.nachholen(queue_path=queue_path)  # kein ausfuehren=True
    assert ergebnis["modus"] == "trocken"
    assert ergebnis["faellig"] == 1
    assert queue_path.read_text(encoding="utf-8") == inhalt_vorher  # unveraendert


# ─── Abnahme 5: Deckel -- nach MAX_VERSUCHE wird markiert, nicht weiter versucht

def test_nachholen_deckel_bei_max_versuche(monkeypatch, queue_path):
    monkeypatch.setattr(av.urllib.request, "urlopen", _raise(urllib.error.URLError(OSError("kein netz"))))
    av.versuche_anker("rfc3161", "aaaa", BEREICH, ZEIT, queue_path=queue_path, senden=True)

    entries = json.loads(queue_path.read_text(encoding="utf-8"))
    entries[0]["versuche"] = av.MAX_VERSUCHE - 1  # ein Fehlschlag vor der Schwelle
    queue_path.write_text(json.dumps(entries), encoding="utf-8")

    ergebnis = av.nachholen(queue_path=queue_path, ausfuehren=True)
    assert ergebnis["braucht_aufmerksamkeit"] == 1
    assert ergebnis["weiter_offen"] == 0

    entries = json.loads(queue_path.read_text(encoding="utf-8"))
    assert entries[0]["status"] == "braucht_aufmerksamkeit"
    assert entries[0]["versuche"] == av.MAX_VERSUCHE

    # Ein weiterer Nachhol-Lauf ruehrt den Eintrag nicht mehr an (Status != offen).
    ergebnis2 = av.nachholen(queue_path=queue_path, ausfuehren=True)
    assert ergebnis2["erledigt"] == 0
    assert ergebnis2["braucht_aufmerksamkeit"] == 0
    assert ergebnis2["weiter_offen"] == 0


# ─── Gegenzeichnung: Nachholen mit Schluessel, ohne Schluessel uebersprungen

def test_nachholen_gegenzeichnung_ohne_schluessel_uebersprungen(queue_path):
    av.versuche_anker("gegenzeichnung", "cccc", BEREICH, ZEIT, queue_path=queue_path, signieren=True)
    ergebnis = av.nachholen(queue_path=queue_path, ausfuehren=True)  # kein Schluessel mitgegeben
    assert ergebnis["uebersprungen"] == 1
    entries = json.loads(queue_path.read_text(encoding="utf-8"))
    assert entries[0]["status"] == "offen"
    assert entries[0]["versuche"] == 1  # kein Aufschlag, es wurde ja nicht versucht


def test_nachholen_gegenzeichnung_mit_schluessel_gelingt(queue_path):
    av.versuche_anker("gegenzeichnung", "cccc", BEREICH, ZEIT, queue_path=queue_path, signieren=True)
    schluessel = Ed25519PrivateKey.generate()
    pem = schluessel.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    ergebnis = av.nachholen(queue_path=queue_path, ausfuehren=True, private_key_pem=pem)
    assert ergebnis["erledigt"] == 1
    entries = json.loads(queue_path.read_text(encoding="utf-8"))
    assert entries[0]["beleg"]["modus"] == "signiert"


# ─── Lint-Kategorie 13: Rueckstand mit altem und frischem Eintrag ───────────

def test_lint_anker_queue_backlog_meldet_alter_des_aeltesten(queue_path):
    jetzt = datetime(2026, 8, 6, tzinfo=timezone.utc)
    alt = (jetzt - timedelta(days=90)).isoformat()
    frisch = (jetzt - timedelta(days=1)).isoformat()
    entries = [
        {"id": "a", "verfahren": "rfc3161", "wurzel": "x", "bereich": BEREICH, "zeitstempel": ZEIT,
         "kwargs_sicher": {}, "fehlerart": "netz", "fehler_text": "alt", "versuche": 1,
         "status": "offen", "erstellt_am": alt, "letzter_versuch_am": alt, "erledigt_am": None, "beleg": None},
        {"id": "b", "verfahren": "rfc3161", "wurzel": "y", "bereich": BEREICH, "zeitstempel": ZEIT,
         "kwargs_sicher": {}, "fehlerart": "netz", "fehler_text": "frisch", "versuche": 1,
         "status": "offen", "erstellt_am": frisch, "letzter_versuch_am": frisch, "erledigt_am": None, "beleg": None},
        {"id": "c", "verfahren": "rfc3161", "wurzel": "z", "bereich": BEREICH, "zeitstempel": ZEIT,
         "kwargs_sicher": {}, "fehlerart": None, "fehler_text": None, "versuche": 1,
         "status": "erledigt", "erstellt_am": alt, "letzter_versuch_am": alt, "erledigt_am": alt, "beleg": {}},
    ]
    queue_path.write_text(json.dumps(entries), encoding="utf-8")

    ergebnis = lint.find_anker_queue_backlog(queue_path, now=jetzt)

    assert ergebnis["anzahl"] == 2  # das erledigte zaehlt nicht mit
    assert ergebnis["aeltester_seit"] == alt
    assert ergebnis["alter_tage"] == 90
