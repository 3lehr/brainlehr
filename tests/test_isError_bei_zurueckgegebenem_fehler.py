"""Wiederholungssperre fuer den Fund vom 2026-08-08 (Commit 3c535e2 auf
claude/hallo-3b3c8d, seither durch eine Umsortierung verloren gegangen und am
2026-08-13 erneut gemessen).

Wirft ein Handler eine Ausnahme, setzt handle_request() isError=True. Gibt er
{"error": ...} ZURUECK statt zu werfen, landete das bis zum heutigen Fix im
Erfolgspfad -- ohne isError. Ein fremder Klient sieht eine Abweisung dann als
Erfolg.

ROT VOR GRUEN: vor dem Fix lieferte Fall 1 isError=None statt True.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "kern")]

import ausweis  # noqa: E402
import knowledge_mcp_server as kms  # noqa: E402


def _bestand(tmp_path, monkeypatch):
    db = tmp_path / "k.db"
    conn = sqlite3.connect(str(db))
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db)
    monkeypatch.setenv(ausweis.ENV_AUSWEISDATEI, str(tmp_path / "a.json"))
    monkeypatch.delenv(ausweis.ENV_GEHEIMNIS, raising=False)
    monkeypatch.delenv("BRAINLEHR_DURCHSETZUNG", raising=False)
    ausweis._pruefe.cache_clear()
    return db


def _call(name: str, args: dict) -> dict:
    return kms.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": args},
    })["result"]


def test_zurueckgegebener_fehler_setzt_isError(tmp_path, monkeypatch):
    """Fall 1 (Abnahme): knowledge_add gibt bei fehlender Herkunft
    {"error": "source fehlt: ..."} ZURUECK (kein raise) -- gemessen an
    knowledge_add() Zeile ~2914. Vorher: isError=None. Nachher: isError=True."""
    _bestand(tmp_path, monkeypatch)

    res = _call("knowledge_add", {
        "parent_path": "/", "title": "ohne Herkunft", "summary": "s",
        "neuer_ast": True,
        "norm_entscheidung": "keine_norm", "norm_entschieden_grund": "Test",
        # source bewusst weggelassen -> {"error": "source fehlt..."} als RETURN
    })

    daten = json.loads(res["content"][0]["text"])
    assert "error" in daten, f"Testannahme falsch, kein Fehler zurueckgegeben: {daten}"
    assert res.get("isError") is True, (
        f"zurueckgegebener Fehler wurde nicht als isError markiert: {res}")


def test_erfolgreicher_aufruf_setzt_isError_nicht(tmp_path, monkeypatch):
    """Negativfall: ein erfolgreicher Aufruf traegt kein isError."""
    _bestand(tmp_path, monkeypatch)

    res = _call("knowledge_add", {
        "parent_path": "/", "title": "mit Herkunft", "summary": "s",
        "source": "test_isError", "neuer_ast": True,
        "norm_entscheidung": "keine_norm", "norm_entschieden_grund": "Test",
    })

    daten = json.loads(res["content"][0]["text"])
    assert "error" not in daten, f"unerwarteter Fehler: {daten}"
    assert "isError" not in res, f"Erfolg faelschlich als isError markiert: {res}"


def test_geworfener_fehler_bleibt_unveraendert_markiert(tmp_path, monkeypatch):
    """Grenzwert: ein geworfener Fehler (unbekanntes Werkzeug) war schon vor
    dem Fix korrekt isError=True markiert und darf es nicht doppelt oder
    anders werden."""
    _bestand(tmp_path, monkeypatch)

    res = _call("kein_werkzeug_mit_diesem_namen", {})

    assert res.get("isError") is True
    daten = json.loads(res["content"][0]["text"])
    assert "error" in daten
