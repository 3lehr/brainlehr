"""Auftrag 2026-08-12: die Zweckprojektion (bisher nur knowledge_read) soll
auch bei knowledge_search und knowledge_browse greifen.

Entscheidung (siehe Docstring an _zweckprojektion_sichtbar in
knowledge_mcp_server.py): eine Trefferliste zeigt schon in Titel+Summary die
minimale Darstellung -- ein weiteres Kuerzen wie bei knowledge_read (Zeile ->
ein Feld) gibt es nicht. Ein Treffer ohne passendes Rolle/Zweck-Tag
VERSCHWINDET darum ganz, statt gekuerzt zu erscheinen (ein gekuerzter Titel
wuerde Existenz+Thema trotzdem verraten). Gleiche Kroete wie bei
FREIGABE_GESPERRT: der Aufrufer erfaehrt nicht, DASS es den Knoten gibt.

Rot vor dem Fix: gegen den Stand vor diesem Auftrag tauchte ein Knoten ohne
passendes Tag in Suche/Blaettern trotzdem mit Titel+Summary auf, und
count/children_count/has_children zaehlten ihn mit.
"""
from __future__ import annotations

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

    # Fuer raumplaner/raumplanung sichtbar (Tag passt).
    sichtbar = kms.knowledge_add(
        "/", "Zweckprojektion-Suchtest: Raum belegt",
        "Raum belegt bis 17 Uhr Zweckprojektion-Suchtest",
        content="INTERNER_GRUND_SICHTBAR", source="test",
        tags=["synthetisch", "zweck:raumplanung", "feld:nutzinformation"],
    )
    # Fuer raumplaner NICHT sichtbar (kein passendes Tag) -- muss ganz
    # verschwinden, auch aus den Zaehlern.
    unsichtbar = kms.knowledge_add(
        "/", "Zweckprojektion-Suchtest: interner Grund",
        "darf raumplaner nicht erreichen Zweckprojektion-Suchtest",
        content="INTERNER_GRUND_UNSICHTBAR", source="test",
        tags=["synthetisch"],
    )
    assert sichtbar["status"] == unsichtbar["status"] == "created"

    gruender = ausweis.anlegen("gruender", ["betreiber"], art="mensch", pfad=ausweise)
    geheimnis_raumplaner = ausweis.anlegen(
        "raumdienst", ["raumplaner"], pfad=ausweise, aussteller=gruender)

    return {
        "sichtbar": sichtbar["id"],
        "unsichtbar": unsichtbar["id"],
        "geheimnis_raumplaner": geheimnis_raumplaner,
        "geheimnis_betreiber": gruender,
        "monkeypatch": monkeypatch,
    }


def _als(env, geheimnis_key: str):
    env["monkeypatch"].setenv(ausweis.ENV_GEHEIMNIS, env[geheimnis_key])
    ausweis._pruefe.cache_clear()


def test_negativfall_treffer_ohne_passendes_tag_fehlt_in_search_und_browse(umgebung):
    _als(umgebung, "geheimnis_raumplaner")

    treffer = kms.knowledge_search("Zweckprojektion-Suchtest")
    assert not any(r.get("id") == umgebung["unsichtbar"] for r in treffer["results"])

    blatt = kms.knowledge_browse("/")
    assert not any(c["id"] == umgebung["unsichtbar"] for c in blatt["children"])


def test_positivfall_betreiber_sieht_in_search_und_browse_unveraendert_alles(umgebung):
    _als(umgebung, "geheimnis_betreiber")

    treffer = kms.knowledge_search("Zweckprojektion-Suchtest")
    gefundene_ids = {r.get("id") for r in treffer["results"]}
    assert umgebung["sichtbar"] in gefundene_ids
    assert umgebung["unsichtbar"] in gefundene_ids

    blatt = kms.knowledge_browse("/")
    kinder_ids = {c["id"] for c in blatt["children"]}
    assert umgebung["sichtbar"] in kinder_ids
    assert umgebung["unsichtbar"] in kinder_ids


def test_kein_leck_ueber_zaehler(umgebung):
    _als(umgebung, "geheimnis_raumplaner")

    treffer = kms.knowledge_search("Zweckprojektion-Suchtest")
    assert treffer["count"] == len(treffer["results"])
    assert "INTERNER_GRUND_UNSICHTBAR" not in str(treffer)

    blatt = kms.knowledge_browse("/")
    assert blatt["count"] == len(blatt["children"])
    # children_count/has_children am Wurzelverzeichnis selbst: siehe eigener
    # Test test_children_count_unter_root_zaehlt_unsichtbaren_kindknoten_nicht
    # fuer den Beleg an einem echten Elternpfad unterhalb der Wurzel.


def test_children_count_unter_root_zaehlt_unsichtbaren_kindknoten_nicht(umgebung):
    """Eigener Astknoten mit genau einem sichtbaren und einem unsichtbaren
    Kind -- direkter Beleg fuer children_count/has_children am Elternpfad,
    nicht nur am Wurzelverzeichnis."""
    # Der Astknoten selbst braucht das passende Tag, sonst ist schon ER fuer
    # raumplaner unsichtbar (gleiche Regel wie fuer jeden anderen Knoten) --
    # der Test soll children_count pruefen, nicht nochmal die Astsichtbarkeit.
    ast = kms.knowledge_add(
        "/", "Zweckprojektion-Suchtest: Ast", "Astknoten", source="test",
        tags=["synthetisch", "zweck:raumplanung", "feld:nutzinformation"],
    )
    assert ast["status"] == "created"
    ast_pfad = ast["path"]

    kind_sichtbar = kms.knowledge_add(
        ast_pfad, "Zweckprojektion-Suchtest: Astkind Alpha", "sichtbares Astkind",
        source="test", tags=["synthetisch", "zweck:raumplanung", "feld:nutzinformation"],
    )
    kind_unsichtbar = kms.knowledge_add(
        ast_pfad, "Zweckprojektion-Suchtest: Astkind Beta", "unsichtbares Astkind",
        source="test", tags=["synthetisch"],
    )
    assert kind_sichtbar["status"] == kind_unsichtbar["status"] == "created"

    _als(umgebung, "geheimnis_raumplaner")
    blatt = kms.knowledge_browse("/")
    ast_eintrag = next(c for c in blatt["children"] if c["path"] == ast_pfad)
    assert ast_eintrag["children_count"] == 1
    assert ast_eintrag["has_children"] is True

    kinder_blatt = kms.knowledge_browse(ast_pfad)
    kinder_ids = {c["id"] for c in kinder_blatt["children"]}
    assert kind_sichtbar["id"] in kinder_ids
    assert kind_unsichtbar["id"] not in kinder_ids


def test_gegenprobe_ohne_pruefung_waere_der_test_rot(umgebung):
    """Direkter Beleg, dass die DB den unsichtbaren Knoten wirklich enthaelt
    -- er verschwindet nur durch die Zweckprojektion, nicht weil er fehlt."""
    conn = sqlite3.connect(kms.DB_PATH)
    row = conn.execute(
        "SELECT tags FROM knowledge_nodes WHERE id = ?", (umgebung["unsichtbar"],)
    ).fetchone()
    conn.close()
    assert row is not None
    assert "zweck:raumplanung" not in row[0]
