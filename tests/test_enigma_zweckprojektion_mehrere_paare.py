"""Enigma-Punkt 2 (docs/ENIGMA_LANDKARTE_2026-08-11.md): die Zweckprojektion
kannte bisher nur EIN Rolle/Zweck-Paar (raumplaner/raumplanung). Dieser Test
belegt, dass die Tabelle _KNOWLEDGE_READ_PROJEKTION mehr als ein Paar traegt
-- und zwar so, dass ein neues Paar eine Datenzeile ist, keine Funktionsaenderung.

Whitelist-Eigenschaft im Mittelpunkt: ein unbekanntes Rolle/Zweck-Paar liefert
NICHTS, nicht den vollen Datensatz -- sonst waere die Projektion im Zweifel
eine Blacklist mit einem Loch.
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
def zwei_paare_umgebung(tmp_path, monkeypatch):
    db = tmp_path / "synthetic.db"
    conn = sqlite3.connect(db)
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db)
    ausweise = tmp_path / "ausweise.json"
    monkeypatch.setenv(ausweis.ENV_AUSWEISDATEI, str(ausweise))
    monkeypatch.delenv(ausweis.ENV_GEHEIMNIS, raising=False)
    ausweis._pruefe.cache_clear()

    # Ein Knoten, an dem BEIDE Paare taggen -- die einzige Art, "gleicher
    # Knoten, verschiedene Zwecke" ohne zwei Knoten zu zeigen.
    doppelt_getaggt = kms.knowledge_add(
        "/", "<RAUM>: Zustand", "Raum belegt bis 17 Uhr",
        content="<INTERNER_GRUND>", source="synthetische Testquelle",
        tags=["synthetisch", "zweck:raumplanung", "feld:nutzinformation",
              "zweck:wartung", "feld:wartungshinweis"],
    )
    # Nur mit dem ERSTEN Paar getaggt -- fuer den Negativfall: die zweite
    # Rolle (gast/wartung) hat hier kein passendes Tag.
    nur_raumplanung = kms.knowledge_add(
        "/", "<RAUM_2>: Zustand", "Raum frei",
        content="<INTERNER_GRUND_2>", source="synthetische Testquelle",
        tags=["synthetisch", "zweck:raumplanung", "feld:nutzinformation"],
    )
    assert doppelt_getaggt["status"] == "created"
    assert nur_raumplanung["status"] == "created"

    gruender = ausweis.anlegen("gruender", ["betreiber"], art="mensch", pfad=ausweise)
    geheimnis_raumplaner = ausweis.anlegen(
        "raumdienst", ["raumplaner"], pfad=ausweise, aussteller=gruender)
    geheimnis_gast = ausweis.anlegen(
        "wartungsdienst", ["gast"], pfad=ausweise, aussteller=gruender)
    return {
        "doppelt": doppelt_getaggt["id"],
        "nur_raumplanung": nur_raumplanung["id"],
        "geheimnis_raumplaner": geheimnis_raumplaner,
        "geheimnis_gast": geheimnis_gast,
        "monkeypatch": monkeypatch,
        "ausweise": ausweise,
    }


def _lies_als(env, geheimnis_key: str, node_id: str) -> dict:
    env["monkeypatch"].setenv(ausweis.ENV_GEHEIMNIS, env[geheimnis_key])
    ausweis._pruefe.cache_clear()
    response = kms.handle_request({
        "jsonrpc": "2.0", "id": "zp", "method": "tools/call",
        "params": {"name": "knowledge_read", "arguments": {"node_id": node_id}},
    })
    return json.loads(response["result"]["content"][0]["text"])


def test_zwei_zwecke_liefern_fuer_denselben_knoten_verschiedene_felder(zwei_paare_umgebung):
    node_id = zwei_paare_umgebung["doppelt"]

    als_raumplaner = _lies_als(zwei_paare_umgebung, "geheimnis_raumplaner", node_id)
    als_gast = _lies_als(zwei_paare_umgebung, "geheimnis_gast", node_id)

    assert als_raumplaner == {"nutzinformation": "Raum belegt bis 17 Uhr"}
    assert als_gast == {"wartungshinweis": "Raum belegt bis 17 Uhr"}
    assert als_raumplaner != als_gast


def test_unbekanntes_paar_liefert_nichts_kein_leck(zwei_paare_umgebung):
    """gast/wartung ist ein bekanntes Paar in der Tabelle -- aber dieser
    Knoten traegt kein zweck:wartung-Tag. Das Paar ist fuer DIESEN Knoten
    unbekannt/unpassend und muss NICHTS liefern, nicht den vollen Datensatz."""
    node_id = zwei_paare_umgebung["nur_raumplanung"]

    conn = sqlite3.connect(kms.DB_PATH)
    vorher = conn.execute(
        "SELECT access_count FROM knowledge_nodes WHERE id = ?", (node_id,)
    ).fetchone()[0]
    conn.close()

    antwort = _lies_als(zwei_paare_umgebung, "geheimnis_gast", node_id)

    assert antwort == {"error": "zugriff verweigert"}
    assert antwort.get("content") is None
    assert antwort.get("wartungshinweis") is None
    assert antwort.get("nutzinformation") is None
    assert "INTERNER_GRUND_2" not in json.dumps(antwort)

    conn = sqlite3.connect(kms.DB_PATH)
    nachher = conn.execute(
        "SELECT access_count FROM knowledge_nodes WHERE id = ?", (node_id,)
    ).fetchone()[0]
    conn.close()
    assert vorher == nachher == 0  # kein Zaehler-Leck ueber den abgewiesenen Teil


def test_projektionstabelle_traegt_mehr_als_ein_paar():
    """Kriterium des Auftrags: ein neues Paar ist eine Datenzeile, keine
    Funktionsaenderung. Belegt hier direkt an der Tabelle, unabhaengig vom
    MCP-Pfad."""
    anzahl_paare = sum(len(paare) for paare in kms._KNOWLEDGE_READ_PROJEKTION.values())
    assert anzahl_paare >= 2, (
        "Tabelle traegt nur ein Rolle/Zweck-Paar -- Auftrag verlangt mehr")
