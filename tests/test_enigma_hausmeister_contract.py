"""Enigma Phase 2: synthetic housekeeper acceptance contract.

This is deliberately a strict xfail: the current public MCP read path has no
purpose projection.  It records the boundary that must turn green before an
Enigma confidentiality claim is made; it does not add a proxy or policy engine.
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

    sensitive = kms.knowledge_add(
        "/", "<PERSON_A>: Abwesenheit", "nicht verfuegbar",
        content="<SENSITIVER_GRUND>", source="synthetische Testquelle",
    )
    assert sensitive["status"] == "created"
    secret = ausweis.anlegen("hausmeister", ["leser"], pfad=ausweise)
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, secret)
    ausweis._pruefe.cache_clear()
    return sensitive["id"]


def _public_read(node_id: str) -> dict:
    response = kms.handle_request({
        "jsonrpc": "2.0", "id": "Z0-Z8", "method": "tools/call",
        "params": {"name": "knowledge_read", "arguments": {"node_id": node_id}},
    })
    return json.loads(response["result"]["content"][0]["text"])


@pytest.mark.xfail(strict=True, reason="Enigma Zweckprojektion existiert noch nicht")
def test_z0_bis_z8_hausmeister_erhaelt_nur_nutzinformation(hausmeister_umgebung):
    """Z0 Identitaet; Z1 Befugnis; Z2 Zweck; Z3 Zustaendigkeit;
    Z4 Nutzinformation; Z5 kein Grund; Z6 keine Metadaten; Z7 leere
    Ablehnung; Z8 keine Rekonstruktion durch Wiederholung."""
    actor, _, _ = kms._identity(actor="behauptet-andere-identitaet")
    assert actor == "hausmeister"  # Z0: credential wins over request data.

    # The desired public answer is intentionally tiny.  Current MCP exposes
    # the complete stored node: Z1--Z8 therefore fail at the first read.
    answer = _public_read(hausmeister_umgebung)
    assert answer == {"nutzinformation": "Bereich verfuegbar"}
