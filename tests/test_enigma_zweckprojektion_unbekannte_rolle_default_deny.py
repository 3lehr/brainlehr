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

Nachtrag Auftrag 38 (2026-08-13): urspruenglich stand hier die echte Rolle
'leser' als Beispiel einer "unbeschriebenen Rolle". Das war der Befund, nicht
der Sollzustand -- 'leser' ist seither in _KNOWLEDGE_READ_VOLLZUGRIFF
eingetragen (siehe tests/test_leser_rolle_vollzugriff.py) und darum kein
Beispiel fuer den Default-Deny-Fall mehr. Ersetzt durch eine per Monkeypatch
erfundene Rolle, damit dieser Test unabhaengig von kuenftigen Eintragungen in
den beiden Tabellen bleibt.
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
    # Erfundene ROLLE per Monkeypatch (monkeypatch.setitem entfernt den
    # Schluessel beim Teardown wieder, da er vorher nicht existierte): traegt
    # ein Leserecht, besteht also die vorgelagerte Rechtepruefung, steht aber
    # bewusst in KEINER der beiden Zweckprojektions-Tabellen. Frueher stand
    # hier die echte Rolle 'leser' -- die ist seit Auftrag 38 in
    # _KNOWLEDGE_READ_VOLLZUGRIFF eingetragen und darum kein Beispiel fuer
    # eine unbeschriebene Rolle mehr (siehe Moduldocstring).
    monkeypatch.setitem(ausweis.ROLLEN, "unbeschriebene_testrolle", ("wissen:lesen",))
    geheimnis_extern = ausweis.anlegen(
        "aussenstelle", ["unbeschriebene_testrolle"], pfad=ausweise, aussteller=gruender)

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
