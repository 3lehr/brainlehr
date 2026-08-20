"""Aussetzer-Sicherung fuer kern/embeddings.py (Auftrag A3,
docs/PLAN_BETRIEBSPROFILE_2026-08-20.md).

ANLASS, gemessen: der Einbettungsdienst war am 2026-08-20 zweimal weg, jeder
Aufruf lief still in den Timeout, 13 Eintraege entstanden ohne Vektor, ohne
dass irgendwo ein Fehler erschien. Vorbild mem0: nach 5 Fehlern in Folge fuer
120s pausieren -- aber der Kern ist das MERKEN, nicht das Pausieren: der
Uebergang in die Pause muss nach ort.AUSSETZER_LOG geschrieben werden, sonst
ist der stille Ausfall nur billiger geworden.

ROT VOR GRUEN: gegen den Stand vor diesem Auftrag (kein Aussetzer-Zaehler,
kein AUSSETZER_LOG) faellt jeder Fall hier -- entweder weil embed_text() bei
jedem der 6 Versuche erneut den Netzwerkaufruf macht (kein Kurzschluss), oder
weil embeddings.ort.AUSSETZER_LOG als Attribut fehlt.
"""
from __future__ import annotations

import json
import sys
import urllib.error
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path.insert(0, str(_w / "kern"))
sys.path.insert(0, str(_w / "haken"))

import embeddings  # noqa: E402


def _kaputt_zaehlend(calls):
    def _f(*_a, **_k):
        calls["n"] += 1
        raise urllib.error.URLError("Verbindung abgelehnt")
    return _f


class _GesundeAntwort:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return json.dumps({"embeddings": [[0.1, 0.2, 0.3]]}).encode("utf-8")


def test_schwelle_pause_und_protokoll(monkeypatch, tmp_path):
    embeddings._aussetzer_zuruecksetzen()
    log = tmp_path / "einbettungsausfaelle.jsonl"
    monkeypatch.setattr(embeddings.ort, "AUSSETZER_LOG", log)

    calls = {"n": 0}
    monkeypatch.setattr(embeddings.urllib.request, "urlopen", _kaputt_zaehlend(calls))
    uhr = {"t": 0.0}
    monkeypatch.setattr(embeddings.time, "monotonic", lambda: uhr["t"])

    # SCHWELLE-1 (4 Fehler in Folge): kein Aussetzer, jeder Versuch geht raus.
    for _ in range(embeddings.AUSSETZER_SCHWELLE - 1):
        assert embeddings.embed_text("hallo", base_url="http://127.0.0.1:1") is None
    assert calls["n"] == embeddings.AUSSETZER_SCHWELLE - 1
    assert not log.exists(), "vor der Schwelle darf noch nichts protokolliert sein"
    assert not embeddings._aussetzer_aktiv()

    # SCHWELLE (der 5. Fehler): loest die Pause aus UND wird protokolliert --
    # das ist die Haelfte des Auftrags, die sonst stumm bliebe.
    assert embeddings.embed_text("hallo", base_url="http://127.0.0.1:1") is None
    assert calls["n"] == embeddings.AUSSETZER_SCHWELLE
    assert embeddings._aussetzer_aktiv()
    assert log.exists(), "der Uebergang in die Pause muss festgehalten werden"
    zeilen = log.read_text(encoding="utf-8").splitlines()
    assert len(zeilen) == 1
    eintrag = json.loads(zeilen[0])
    assert eintrag["fehler_in_folge"] == embeddings.AUSSETZER_SCHWELLE
    assert eintrag["pause_sekunden"] == embeddings.AUSSETZER_PAUSE_SEKUNDEN
    assert eintrag["url"] == "http://127.0.0.1:1"
    assert eintrag["ts"]

    # SCHWELLE+1: waehrend der Pause wird gar nicht erst versucht -- der
    # Netzwerk-Aufruf-Zaehler bleibt stehen (das ist der eingesparte Aufruf).
    assert embeddings.embed_text("hallo", base_url="http://127.0.0.1:1") is None
    assert calls["n"] == embeddings.AUSSETZER_SCHWELLE, "waehrend der Pause darf nicht versucht werden"
    # ... und es wird nicht bei jedem uebersprungenen Versuch erneut protokolliert.
    assert len(log.read_text(encoding="utf-8").splitlines()) == 1

    # NEGATIVFALL: nach Ablauf der Pause wird wieder versucht -- die
    # Sicherung darf nicht dauerhaft zumachen.
    uhr["t"] += embeddings.AUSSETZER_PAUSE_SEKUNDEN + 1
    assert embeddings.embed_text("hallo", base_url="http://127.0.0.1:1") is None
    assert calls["n"] == embeddings.AUSSETZER_SCHWELLE + 1, "nach der Pause muss wieder versucht werden"

    embeddings._aussetzer_zuruecksetzen()


def test_positivkontrolle_erreichbarer_dienst_pausiert_nicht(monkeypatch, tmp_path):
    embeddings._aussetzer_zuruecksetzen()
    log = tmp_path / "einbettungsausfaelle.jsonl"
    monkeypatch.setattr(embeddings.ort, "AUSSETZER_LOG", log)
    monkeypatch.setattr(embeddings.urllib.request, "urlopen", lambda *a, **k: _GesundeAntwort())

    for _ in range(10):
        assert embeddings.embed_text("hallo") == [0.1, 0.2, 0.3]
    assert not embeddings._aussetzer_aktiv()
    assert not log.exists()
    embeddings._aussetzer_zuruecksetzen()


def test_einzelner_fehler_loest_noch_keinen_aussetzer_aus(monkeypatch, tmp_path):
    embeddings._aussetzer_zuruecksetzen()
    log = tmp_path / "einbettungsausfaelle.jsonl"
    monkeypatch.setattr(embeddings.ort, "AUSSETZER_LOG", log)
    monkeypatch.setattr(embeddings.urllib.request, "urlopen", _kaputt_zaehlend({"n": 0}))

    assert embeddings.embed_text("hallo", base_url="http://127.0.0.1:1") is None
    assert not embeddings._aussetzer_aktiv()
    assert not log.exists()
    embeddings._aussetzer_zuruecksetzen()
