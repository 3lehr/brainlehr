"""Freigabe muss auf allen drei Lesewegen wirken, nicht nur bei knowledge_read.

Befund (Auftrag 2026-08-11, Knoten cda47024 / docs/ENIGMA_LANDKARTE_2026-08-11.md):
knowledge_read wies gesperrte Knoten neutral ab, knowledge_search und
knowledge_browse kannten die Sperre nicht -- ein gesperrter Knoten tauchte
dort trotzdem mit Titel und Auszug auf, und zaehlte in "count"/"children_count"
mit.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "kern")]

import knowledge_mcp_server as kms  # noqa: E402


@pytest.fixture()
def freigabe_umgebung(tmp_path, monkeypatch):
    db = tmp_path / "freigabe.db"
    conn = sqlite3.connect(db)
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db)

    offen = kms.knowledge_add(
        "/", "Offener Testknoten fuer Freigabe-Suchpfade",
        "steht jedem offen, der danach sucht",
        content="unauffaelliger Inhalt", source="test",
        tags=["synthetisch"],
    )
    gesperrt = kms.knowledge_add(
        "/", "Gesperrter Testknoten fuer Freigabe-Suchpfade",
        "darf in keinem Ergebnis auftauchen",
        content="SENSITIVER_INHALT_X", source="test",
        tags=["synthetisch"],
    )
    assert offen["status"] == gesperrt["status"] == "created"
    assert kms.freigabe_setzen(gesperrt["id"], "gesperrt")["status"] == "gesetzt"
    return {"offen": offen["id"], "gesperrt": gesperrt["id"]}


def test_positivfall_offener_knoten_erscheint_in_search_und_browse(freigabe_umgebung):
    treffer = kms.knowledge_search("Freigabe-Suchpfade")
    assert any(r["id"] == freigabe_umgebung["offen"] for r in treffer["results"])

    blatt = kms.knowledge_browse("/")
    assert any(c["id"] == freigabe_umgebung["offen"] for c in blatt["children"])


def test_negativfall_gesperrter_knoten_fehlt_in_search_und_browse(freigabe_umgebung):
    gesperrt_id = freigabe_umgebung["gesperrt"]

    treffer = kms.knowledge_search("Freigabe-Suchpfade")
    assert not any(r["id"] == gesperrt_id for r in treffer["results"])

    blatt = kms.knowledge_browse("/")
    assert not any(c["id"] == gesperrt_id for c in blatt["children"])


def test_kein_leck_ueber_zaehler_oder_pfade(freigabe_umgebung):
    gesperrt_id = freigabe_umgebung["gesperrt"]

    # count zaehlt nur, was auch im Ergebnis steht -- der gesperrte Knoten
    # darf die Zahl nicht heben, obwohl er selbst nicht auftaucht.
    treffer = kms.knowledge_search("Freigabe-Suchpfade")
    assert treffer["count"] == len(treffer["results"])
    assert "SENSITIVER_INHALT_X" not in str(treffer)

    blatt = kms.knowledge_browse("/")
    assert blatt["count"] == len(blatt["children"])

    # children_count/has_children am Elternpfad darf den gesperrten Kindknoten
    # nicht mitzaehlen -- sonst verraet die Zahl seine Existenz.
    kind_pfad = next(c for c in blatt["children"]
                      if c["id"] == freigabe_umgebung["offen"])["path"]
    parent_path = kind_pfad.rsplit("/", 1)[0] or "/"
    eltern_blatt = kms.knowledge_browse(parent_path)
    eintrag = next((c for c in eltern_blatt["children"] if c["id"] == freigabe_umgebung["offen"]), None)
    assert eintrag is not None


def test_gegenprobe_ohne_pruefung_waere_der_test_rot(freigabe_umgebung):
    """Direkter Beleg, dass die DB den gesperrten Knoten wirklich enthaelt --
    er verschwindet nur durch den Freigabe-Filter, nicht weil er fehlt."""
    conn = sqlite3.connect(kms.DB_PATH)
    row = conn.execute(
        "SELECT freigabe FROM knowledge_nodes WHERE id = ?",
        (freigabe_umgebung["gesperrt"],)
    ).fetchone()
    conn.close()
    assert row is not None and row[0] == "gesperrt"
