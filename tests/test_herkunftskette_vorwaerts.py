"""Aufgabe 73 Schritt 2 (docs/PLAN_HERKUNFTSKETTE_2026-08-13.md) -- vorwaerts
beim Schreiben. Schritt 1 (kern/kanten_herkunft_rueckwirkend.py, Commit
462f527b) hat den Bestand rueckwirkend auf Kanten umgestellt: Entscheidung B
des Plans ist Kantentyp 'abgeleitet_von' in knowledge_relations statt der
Spalte gleichen Namens, weil ein Knoten oft mehrere Vorgaenger hat.

Der VORHER-Zustand (gemessen): knowledge_add(abgeleitet_von=...) (ADR-027
Nachtrag 4, 2026-08-06) schreibt die Kennung nur in die Spalte
knowledge_nodes.abgeleitet_von -- es entsteht dabei KEINE Kante in
knowledge_relations. Genau die Luecke schliesst Schritt 2: derselbe Aufruf
legt jetzt zusaetzlich eine Kante vom neuen Knoten zum genannten Quellknoten
an.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _relations(temp_db, source_path):
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT source_path, target_path, relation_type, confidence FROM knowledge_relations "
        "WHERE source_path = ? AND relation_type = 'abgeleitet_von'",
        (source_path,),
    ).fetchall()
    conn.close()
    return rows


def test_abgeleitet_von_erzeugt_kante_zum_quellknoten(temp_db):
    quelle = kms.knowledge_add(
        "/", "Quellknoten", "Zusammenfassung",
        source="erzeugt aus Datei.md (Stand 2026-08-13T10:00:00+0200)",
    )
    assert quelle.get("status") == "created", quelle

    ableitung = kms.knowledge_add(
        "/", "Abgeleiteter Knoten", "Zusammenfassung",
        abgeleitet_von=quelle["id"],
    )
    assert ableitung.get("status") == "created", ableitung

    kanten = _relations(temp_db, ableitung["path"])
    assert len(kanten) == 1, kanten
    assert kanten[0]["target_path"] == quelle["path"], kanten[0]


def test_zweiter_vorgaenger_bleibt_moeglich_mehrere_kanten_je_knoten(temp_db):
    # Grenzwert/Beleg fuer Entscheidung B: EIN Knoten kann mehrere
    # abgeleitet_von-Kanten tragen (aus mehreren Ableitungsaufrufen), waehrend
    # die Spalte nur EINEN Vorgaenger halten koennte.
    quelle_a = kms.knowledge_add("/", "Quelle A", "Zusammenfassung A", source="a.md")
    quelle_b = kms.knowledge_add("/", "Quelle B", "Zusammenfassung B", source="b.md")
    ableitung = kms.knowledge_add("/", "Ableitung X", "Zusammenfassung X",
                                  abgeleitet_von=quelle_a["id"])
    assert ableitung.get("status") == "created", ableitung
    # Zweite Kante manuell nachtragen wie ein zweiter Ableitungslauf es taete
    # (knowledge_relation_add ist der dafuer vorgesehene, allgemeine Weg --
    # abgeleitet_von auf knowledge_add bleibt bewusst eine einzelne Kennung
    # je Aufruf, siehe Docstring dort).
    res = kms.knowledge_relation_add(ableitung["path"], quelle_b["path"], "supports")
    assert res.get("id"), res
    kanten = _relations(temp_db, ableitung["path"])
    assert len(kanten) == 1  # nur die 'abgeleitet_von'-Kante zaehlt hier
    assert kanten[0]["target_path"] == quelle_a["path"]


def test_ohne_abgeleitet_von_entsteht_keine_kante(temp_db):
    # Negativfall: der ganz normale Schreibweg (kein abgeleitet_von) darf
    # keine 'abgeleitet_von'-Kante erzeugen -- ein Verfahren, das ueberall
    # etwas findet, findet nichts (Plan-Abnahme, Schritt 1 wortgleich).
    res = kms.knowledge_add("/", "Eigenstaendiger Knoten", "Zusammenfassung",
                            source="c.md")
    assert res.get("status") == "created", res
    kanten = _relations(temp_db, res["path"])
    assert kanten == []


def test_doppelter_aufruf_gegen_gleiche_quelle_erzeugt_keine_doppelkante(temp_db):
    # UNIQUE(source_path, target_path, relation_type) + INSERT OR IGNORE:
    # ein zweiter Schreibversuch mit derselben Kennung darf keine zweite
    # Kante anlegen. node_path ist aber pro knowledge_add-Aufruf eindeutig
    # (Pfad-Kollision wird sonst als 'existiert bereits' abgelehnt) -- der
    # Grenzfall hier ist deshalb: zwei VERSCHIEDENE neue Knoten leiten aus
    # DERSELBEN Quelle ab, beide bekommen ihre eigene Kante (kein Verlust
    # durch das IGNORE).
    quelle = kms.knowledge_add("/", "Mehrfachquelle", "Zusammenfassung", source="d.md")
    a = kms.knowledge_add("/", "Ableitung Eins", "Zusammenfassung", abgeleitet_von=quelle["id"])
    b = kms.knowledge_add("/", "Ableitung Zwei", "Zusammenfassung", abgeleitet_von=quelle["id"])
    assert _relations(temp_db, a["path"])[0]["target_path"] == quelle["path"]
    assert _relations(temp_db, b["path"])[0]["target_path"] == quelle["path"]
