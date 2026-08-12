"""Auftrag 38 (2026-08-13): Rolle 'leser' hat ein Leserecht (kern/ausweis.py
ROLLEN: 'wissen:lesen' ungebunden -- gleiche Weite wie 'fachkundig' und
'schreiber'), stand aber in KEINER der beiden Tabellen
_KNOWLEDGE_READ_VOLLZUGRIFF/_KNOWLEDGE_READ_PROJEKTION in
knowledge_mcp_server.py. Bei Default-Deny (Auftrag 2026-08-12, siehe
test_enigma_zweckprojektion_unbekannte_rolle_default_deny.py) bedeutet das
einen stillen Vollausfall: eine beglaubigte, leseberechtigte Rolle bekam
"zugriff verweigert" auf jeden Knoten.

BEFUND, ENTSCHIEDEN: 'leser' ist eine vergessene Eintragung, keine gewollte
Aussperrung. Belege:
  - kern/anmeldung.py ANGEBOTEN listet 'leser' ("nur lesen") als allgemeine
    interne Teilnehmerrolle neben 'fachkundig' und 'schreiber' -- nicht als
    Serving-Zugang wie 'raumplaner'/'gast'.
  - kern/ausweis.py ROLLEN traegt 'leser' mit denselben UNGEBUNDENEN Rechten
    (wissen:lesen, lehre:lesen, kante:lesen, annahme:lesen -- kein ':own',
    kein ':published') wie 'fachkundig'/'schreiber'. Genau das Kriterium, das
    der Kommentar an _KNOWLEDGE_READ_VOLLZUGRIFF fuer die drei dort schon
    stehenden Rollen nennt.
  - 'gast' und 'raumplaner' tragen dagegen ausdruecklich eingeschraenkte
    Rechte (':published') bzw. einen im Kommentar benannten Serving-Zweck --
    'leser' hat keine solche Markierung.

Rot vor gruen: vor der Eintragung lieferte knowledge_read fuer 'leser'
{"error": "zugriff verweigert"} -- siehe Bericht/Commit. Dieser Test haelt
den GRUEN-Zustand fest, mit Negativfall (eine Rolle ohne passenden Tag bleibt
bei nichts).
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
    geheimnis_leser = ausweis.anlegen(
        "vorleser", ["leser"], pfad=ausweise, aussteller=gruender)
    # Negativfall: 'gast' hat ein Leserecht, aber ':published' gebunden UND
    # keinen zum Knoten passenden zweck/feld-Tag -- muss bei nichts bleiben.
    geheimnis_gast = ausweis.anlegen(
        "kiosk", ["gast"], pfad=ausweise, aussteller=gruender)

    return {
        "node_id": knoten["id"],
        "geheimnis_betreiber": gruender,
        "geheimnis_leser": geheimnis_leser,
        "geheimnis_gast": geheimnis_gast,
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


def test_leser_liest_vollstaendig(umgebung):
    antwort = _lies_als(umgebung, "geheimnis_leser", umgebung["node_id"])
    assert antwort.get("content") == "<INTERNER_GRUND>", antwort
    assert antwort.get("title") == "<KNOTEN>: Titel", antwort
    assert "error" not in antwort


def test_negativfall_gast_ohne_passenden_tag_bekommt_nichts(umgebung):
    antwort = _lies_als(umgebung, "geheimnis_gast", umgebung["node_id"])
    assert antwort == {"error": "zugriff verweigert"}
    assert "INTERNER_GRUND" not in json.dumps(antwort)
