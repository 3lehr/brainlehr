"""Auftrag 2026-08-12: die Voreinstellung fuer ein unbeschriebenes
Rolle/Zweck-Paar soll Ablehnung sein statt Vollzugriff.

Vorher lieferte `_knowledge_read_projection` bei einer Rolle, die in
_KNOWLEDGE_READ_PROJEKTION nicht steht, `None` -- und das bedeutete an der
Aufrufstelle (knowledge_read) den VOLLEN Datensatz. Jede unbeschriebene Rolle
war frei, nicht gesperrt -- die Whitelist-Eigenschaft genau andersherum.

Dieser Test belegt zwei Dinge gleichzeitig, damit die Verschaerfung keine
Aussperrung wird:
  1. Eine erfundene, in KEINER Tabelle stehende Rolle bekommt NICHTS.
  2. Der Betreiber-Ausweis (Rolle 'betreiber', ebenfalls nicht in
     _KNOWLEDGE_READ_PROJEKTION) liest weiter vollstaendig -- er ist kein
     Dritter, dem gegenueber die Zweckprojektion gilt.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "kern")]

import ausweis  # noqa: E402
import knowledge_mcp_server as kms  # noqa: E402


@pytest.fixture()
def umgebung(tmp_path, monkeypatch):
    db = tmp_path / "synthetic.db"
    conn = sqlite3.connect(db)
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db)
    ausweise = tmp_path / "ausweise.json"
    monkeypatch.setenv(ausweis.ENV_AUSWEISDATEI, str(ausweise))
    monkeypatch.delenv(ausweis.ENV_GEHEIMNIS, raising=False)
    ausweis._pruefe.cache_clear()

    knoten = kms.knowledge_add(
        "/", "<KNOTEN>: Titel", "Kurzfassung fuer Zusammenfassung",
        content="<INTERNER_GRUND>", source="synthetische Testquelle",
        tags=["synthetisch"],
    )
    assert knoten["status"] == "created"

    gruender = ausweis.anlegen("gruender", ["betreiber"], art="mensch", pfad=ausweise)
    # 'leser' ist eine bekannte ROLLE (kern/ausweis.py: 'wissen:lesen') --
    # sie besteht also die vorgelagerte Rechtepruefung. Sie steht aber in
    # KEINER der beiden Zweckprojektions-Tabellen (weder
    # _KNOWLEDGE_READ_PROJEKTION noch _KNOWLEDGE_READ_VOLLZUGRIFF). Genau der
    # Fall aus den FAKTEN: eine beglaubigte, aber unbeschriebene Rolle.
    geheimnis_extern = ausweis.anlegen(
        "aussenstelle", ["leser"], pfad=ausweise, aussteller=gruender)

    return {
        "node_id": knoten["id"],
        "geheimnis_betreiber": gruender,
        "geheimnis_extern": geheimnis_extern,
        "monkeypatch": monkeypatch,
    }


def _lies_als(env, geheimnis_key: str, node_id: str) -> dict:
    env["monkeypatch"].setenv(ausweis.ENV_GEHEIMNIS, env[geheimnis_key])
    ausweis._pruefe.cache_clear()
    response = kms.handle_request({
        "jsonrpc": "2.0", "id": "dd", "method": "tools/call",
        "params": {"name": "knowledge_read", "arguments": {"node_id": node_id}},
    })
    return json.loads(response["result"]["content"][0]["text"])


def test_unbeschriebene_externe_rolle_bekommt_nichts(umgebung):
    antwort = _lies_als(umgebung, "geheimnis_extern", umgebung["node_id"])
    assert antwort == {"error": "zugriff verweigert"}
    assert "INTERNER_GRUND" not in json.dumps(antwort)
    assert antwort.get("content") is None
    assert antwort.get("title") is None


def test_betreiber_liest_trotz_fehlendem_tabelleneintrag_vollstaendig(umgebung):
    antwort = _lies_als(umgebung, "geheimnis_betreiber", umgebung["node_id"])
    assert antwort.get("content") == "<INTERNER_GRUND>"
    assert antwort.get("title") == "<KNOTEN>: Titel"
    assert "error" not in antwort
