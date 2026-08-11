"""Enigma Phase 2: synthetic housekeeper acceptance contract.

The public MCP read path must project a credential-bound serving role before
returning protected content. This remains a synthetic P1 contract, not a
production-security or anonymity claim.
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
def hausmeister_umgebung(tmp_path, monkeypatch):
    db = tmp_path / "synthetic.db"
    conn = sqlite3.connect(db)
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db)
    ausweise = tmp_path / "ausweise.json"
    monkeypatch.setenv(ausweis.ENV_AUSWEISDATEI, str(ausweise))
    monkeypatch.delenv(ausweis.ENV_GEHEIMNIS, raising=False)
    ausweis._pruefe.cache_clear()

    # A: broad Stufe-0 release must never add a role, purpose, or recipient.
    person_a = kms.knowledge_add(
        "/", "<PERSON_A>: Abwesenheit", "nicht verfuegbar",
        content="<SENSITIVER_GRUND_A>", source="synthetische Testquelle",
        tags=["synthetisch", "stufe-0:breit"],
    )
    # B: field/purpose release is an intersection, never a blanket read.
    person_b = kms.knowledge_add(
        "/", "<PERSON_B>: Abwesenheit", "Bereich verfuegbar",
        content="<SENSITIVER_GRUND_B>", source="synthetische Testquelle",
        tags=["synthetisch", "feld:nutzinformation", "zweck:raumplanung"],
    )
    # Trade secrets have an independent provider/purpose gate, even without PII.
    geheimnis = kms.knowledge_add(
        "/", "<BETRIEBSFRAGMENT>", "synthetisch klassifiziert",
        content="<GESCHAEFTSGEHEIMNIS>", source="synthetische Testquelle",
        tags=["synthetisch", "geschaeftsgeheimnis", "anbieter:lokal", "zweck:betrieb"],
    )
    assert all(node["status"] == "created" for node in (person_a, person_b, geheimnis))
    secret = ausweis.anlegen("hausmeister", ["raumplaner"], pfad=ausweise)
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, secret)
    ausweis._pruefe.cache_clear()
    return {"person_a": person_a["id"], "person_b": person_b["id"], "geheimnis": geheimnis["id"]}


def _public_read(node_id: str) -> dict:
    response = kms.handle_request({
        "jsonrpc": "2.0", "id": "Z0-Z8", "method": "tools/call",
        "params": {"name": "knowledge_read", "arguments": {"node_id": node_id}},
    })
    return json.loads(response["result"]["content"][0]["text"])


def test_z0_bis_z8_hausmeister_erhaelt_nur_nutzinformation(hausmeister_umgebung):
    """Z0 Identitaet; Z1 Befugnis; Z2 Zweck; Z3 Zustaendigkeit;
    Z4 Nutzinformation; Z5 kein Grund; Z6 keine Metadaten; Z7 leere
    Ablehnung; Z8 keine Rekonstruktion durch Wiederholung."""
    actor, _, _ = kms._identity(actor="behauptet-andere-identitaet")
    assert actor == "hausmeister"  # Z0: credential wins over request data.

    # A's broad release does not add role, purpose, or recipient. B's narrow
    # release therefore yields only the allowed intersection. The secret has
    # its independent provider/purpose gate. Current raw MCP exposes all three.
    answers = {name: _public_read(node_id) for name, node_id in hausmeister_umgebung.items()}
    assert answers == {
        "person_a": {"error": "zugriff verweigert"},
        "person_b": {"nutzinformation": "Bereich verfuegbar"},
        "geheimnis": {"error": "zugriff verweigert"},
    }
    assert {name: _public_read(node_id)
            for name, node_id in hausmeister_umgebung.items()} == answers
