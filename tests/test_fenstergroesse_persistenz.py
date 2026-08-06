"""Belegt den Fix vom 2026-08-07: fenstergroesse.py schrieb nichts weg, wenn
ein Ollama-Aufruf waehrend calibrate() scheiterte -- calibrate() rief
_call_ollama() direkt ohne try/except auf, jeder Netzfehler/Timeout riss den
kompletten Lauf ab, bevor auch nur eine Zeile persistiert war. Fund: der
Hintergrundlauf am 2026-08-07 hinterliess trotzdem eine vollstaendige
runs/fenstergroesse.json (Kipppunkt 8192) -- das urspruengliche 'Ergebnis:
NICHTS' bezog sich auf schreibpruefstand/runs/, in das fenstergroesse.py NIE
schreibt (OUT_PATH liegt in shared-knowledge/runs/). Die Haertung unten ist
trotzdem notwendig: ein spaeterer Kalibrierungsausfall wuerde ohne sie
weiterhin alles verlieren.

Ollama wird durchgehend gemockt (fg._call_ollama monkeypatch) -- kein echter
Netzaufruf, damit dieser Test den parallel laufenden wissensnutzen.py-Lauf
nicht stoert."""
from __future__ import annotations

import json
import sys
import urllib.error
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE / "schreibpruefstand"))
sys.path.insert(0, str(SHARED_KNOWLEDGE))
sys.path.insert(0, str(SHARED_KNOWLEDGE.parent / "scripts"))

import fenstergroesse as fg  # type: ignore  # noqa: E402


@pytest.fixture()
def jsonl_path(tmp_path, monkeypatch):
    path = tmp_path / "fenstergroesse.jsonl"
    monkeypatch.setattr(fg, "JSONL_PATH", path)
    return path


def test_append_jsonl_schreibt_sofort(jsonl_path):
    """Eine Zeile je Aufruf, sofort lesbar (kein Puffer bis Programmende)."""
    fg._append_jsonl({"phase": "test", "wert": 1})
    fg._append_jsonl({"phase": "test", "wert": 2})
    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["wert"] == 1
    assert json.loads(lines[1])["wert"] == 2


def test_calibrate_bricht_kontrolliert_ab_und_hinterlaesst_spur(jsonl_path, monkeypatch):
    """Kern des Fixes: ein Netzfehler beim ERSTEN Kalibrierungsaufruf
    (tool_tokens) darf calibrate() nicht mit einer rohen URLError sprengen,
    UND muss trotzdem eine JSONL-Zeile hinterlassen. Gegen den Stand VOR
    diesem Fix (calibrate() rief _call_ollama() direkt auf) waere dieser
    Test rot gewesen: die rohe urllib.error.URLError haette den Test-Aufruf
    verlassen (kein RuntimeError, keine Zeile in jsonl_path -- die Datei
    haette gar nicht existiert, weil _append_jsonl() in calibrate() vorher
    nie aufgerufen wurde)."""
    def immer_fehler(prompt, *, num_ctx, num_predict=None):
        raise urllib.error.URLError("Ollama nicht erreichbar (Testfehler)")

    monkeypatch.setattr(fg, "_call_ollama", immer_fehler)

    with pytest.raises(RuntimeError, match="tool_tokens"):
        fg.calibrate("werkzeuge", "wiedereinstieg", "aufgabe")

    assert jsonl_path.exists(), "kein Artefakt hinterlassen -- der urspruengliche Fehler"
    lines = [json.loads(l) for l in jsonl_path.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 1
    assert lines[0]["phase"] == "calibration"
    assert lines[0]["key"] == "tool_tokens"
    assert lines[0]["prompt_eval_count"] is None
    assert "Ollama nicht erreichbar" in lines[0]["error"]


def test_calibrate_persistiert_erfolgreiche_schritte_vor_dem_fehlschlag(jsonl_path, monkeypatch):
    """Halbe Kalibrierung: die ersten zwei Werte gelingen, der dritte
    (reference_full_tokens.ohne) schlaegt fehl -- die ersten zwei Zeilen
    muessen stehen bleiben, nicht nur die letzte."""
    calls = {"n": 0}

    def teils_fehler(prompt, *, num_ctx, num_predict=None):
        calls["n"] += 1
        if calls["n"] <= 2:
            return {"response": "", "prompt_eval_count": 100 * calls["n"]}
        raise TimeoutError("Zeitgrenze ueberschritten (Testfehler)")

    monkeypatch.setattr(fg, "_call_ollama", teils_fehler)

    with pytest.raises(RuntimeError):
        fg.calibrate("werkzeuge", "wiedereinstieg", "aufgabe")

    lines = [json.loads(l) for l in jsonl_path.read_text(encoding="utf-8").splitlines()]
    assert [l["key"] for l in lines] == ["tool_tokens", "wiedereinstieg_tokens", "reference_full_tokens.ohne"]
    assert lines[0]["prompt_eval_count"] == 100
    assert lines[1]["prompt_eval_count"] == 200
    assert lines[2]["prompt_eval_count"] is None
    assert "Zeitgrenze" in lines[2]["error"]


def test_call_with_retry_zeitueberschreitung_ist_messergebnis_kein_absturz():
    """Ein Aufruf, der die Zeitgrenze reisst, liefert (None, Fehlertext, ...)
    statt eine Exception weiterzureichen -- Voraussetzung dafuer, dass die
    Hauptschleife bei einem haengenden Fenster weiterlaeuft statt zu sterben."""
    def haengt(prompt, *, num_ctx, num_predict=None):
        raise TimeoutError("kein Zaehlwert nach TIMEOUT Sekunden")

    orig = fg._call_ollama
    fg._call_ollama = haengt
    try:
        raw, err, retries, peval = fg._call_with_retry("x", num_ctx=4096)
    finally:
        fg._call_ollama = orig

    assert raw is None
    assert peval is None
    assert "kein Zaehlwert" in err
    assert retries == 1  # beide Versuche (0,1) ausgeschoepft
