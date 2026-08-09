"""Tests fuer P4->ADR-032 (Vektor-Frische) und P5 (Wikilink-Kanten).

P4 (Plan 2026-08-05, abgeloest durch ADR-032): ein veralteter Vektor ist
schlechter als gar keiner -- die Hybridsuche gewichtet ihn gutgläubig mit
(siehe test_knowledge_hybrid_search.py), waehrend sie einen fehlenden sauber
verkraftet. Urspruenglich loeschte knowledge_update()/lesson_update() die
zugehoerige knowledge_embeddings-Zeile bei Textaenderung und liess die Luecke
bis zum naechsten build_embeddings.py-Lauf offen. ADR-032 (Ausfuehrungsschulden
an die Schreibzeit): updated_at/last_seen bumpen bei JEDEM Update, auch einem
reinen tags/resolution-Wechsel -- ein reines Loeschen haette JEDE Aenderung zu
einem vector_gaps-Fund gemacht. Beide Schreibpfade bauen den Vektor deshalb
jetzt unconditional sofort neu (embed_text() gemockt in diesen Tests).

P5: [[wikilink]]-Verweise im content werden beim Schreiben zu echten
knowledge_relations-Kanten aufgeloest. Ein unaufgeloester Verweis ist kein
Fehler (Hinweis auf einen noch zu schreibenden Knoten), wird aber im
Rueckgabewert gemeldet statt verschluckt.
"""
from __future__ import annotations

import itertools
import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


@pytest.fixture(autouse=True)
def _mock_embed(monkeypatch):
    """Kein echtes Ollama in diesem Testlauf noetig -- _rebuild_node_embedding/
    _rebuild_lesson_embedding rufen embeddings.embed_text() bei jedem
    knowledge_add/knowledge_update/lesson_record/lesson_update auf. Jeder
    Aufruf liefert einen ANDEREN Vektor (Zaehler), damit ein Test per
    Bytevergleich unterscheiden kann "neu gebaut" von "liegen gelassen" --
    now_iso() ist nur sekundengenau, ein Zeitstempelvergleich innerhalb
    desselben Tests waere sonst blind."""
    counter = itertools.count()
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda text, **kw: [float(next(counter)), 0.0, 0.0])


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    # /shared muss als echter Knoten existieren, sonst lehnt knowledge_add()
    # seit P1 den Elternpfad ab (unbekannter parent_path).
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, level, updated_at, source, norm_entscheidung, "
        "norm_entschieden_von, norm_entschieden_grund) "
        "VALUES ('root', '/shared', NULL, 'shared', 'Shared', 'Wurzel', 0, ?, 'test', 'keine_norm', 'skript:test', 'Testvorrichtung')",
        (kms.now_iso(),),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _insert_node(db_path, node_id, path, title, content="", parent_path="/shared"):
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, content, level, updated_at, source, norm_entscheidung, "
        "norm_entschieden_von, norm_entschieden_grund) "
        "VALUES (?, ?, ?, 'shared', ?, 'Zusammenfassung', ?, 1, ?, 'test', 'keine_norm', 'skript:test', 'Testvorrichtung')",
        (node_id, path, parent_path, title, content, kms.now_iso()),
    )
    conn.commit()
    conn.close()


def _insert_vector(db_path, kind, ref_id):
    # model = das aktuell konfigurierte Modell (nicht ein fester Fantasiename):
    # dieser Test prueft NUR, ob ein VORHANDENER Vektor beim naechsten Update
    # neu gebaut wird -- welches Modell die Altzeile traegt, ist irrelevant
    # fuer diese Frage, muss aber seit der Modell-Sperre (Auftrag 2026-08-07,
    # knowledge_embeddings_model_check_bi) mit knowledge_config uebereinstimmen,
    # sonst lehnt schon dieser Setup-INSERT ab.
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO knowledge_embeddings (kind, ref_id, model, vector, updated_at) VALUES (?,?,?,?,?)",
        (kind, ref_id, kms.embeddings.DEFAULT_EMBED_MODEL, b"\x00\x00\x80?" * 4, kms.now_iso()),
    )
    conn.commit()
    conn.close()


def _vector_exists(db_path, kind, ref_id) -> bool:
    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT 1 FROM knowledge_embeddings WHERE kind = ? AND ref_id = ?", (kind, ref_id)
    ).fetchone()
    conn.close()
    return row is not None


def _vector_bytes(db_path, kind, ref_id) -> bytes | None:
    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT vector FROM knowledge_embeddings WHERE kind = ? AND ref_id = ?", (kind, ref_id)
    ).fetchone()
    conn.close()
    return row[0] if row else None


def _insert_relation(db_path, source_path, target_path, relation_type):
    """Legt eine Kante direkt per SQL an, wie sie ein Aehnlichkeits-Lauf oder
    eine von Hand gesetzte Belegkante hinterlaesst -- nicht ueber
    knowledge_relation_add(), das nur die knowledge_relation_add()-eigene
    RELATION_TYPES-Menge zulaesst und 'aehnlich_bedeutung' (vom
    Aehnlichkeits-Rechenlauf) gar nicht kennt."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO knowledge_relations "
        "(id, source_path, target_path, relation_type, confidence, weight, "
        "evidence, source, creator, model, session, created_at, updated_at) "
        "VALUES (?,?,?,?,0.5,1.0,'test','test','test',NULL,NULL,?,?)",
        (f"R-{source_path}-{target_path}-{relation_type}", source_path, target_path,
         relation_type, kms.now_iso(), kms.now_iso()),
    )
    conn.commit()
    conn.close()


def _relations_from(db_path, source_path) -> list[sqlite3.Row]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM knowledge_relations WHERE source_path = ?", (source_path,)
    ).fetchall()
    conn.close()
    return rows


# --- ADR-032: jede Aenderung baut den Vektor neu statt ihn nur zu loeschen --

def test_content_change_rebuilds_node_vector(temp_db):
    _insert_node(temp_db, "n1", "/shared/knoten", "Knoten")
    _insert_vector(temp_db, "node", "n1")
    stale = _vector_bytes(temp_db, "node", "n1")
    kms.knowledge_update("n1", content="Neuer Text")
    assert _vector_exists(temp_db, "node", "n1"), "Vektor haette neu gebaut, nicht nur geloescht werden sollen"
    assert _vector_bytes(temp_db, "node", "n1") != stale


def test_summary_change_rebuilds_node_vector(temp_db):
    _insert_node(temp_db, "n1", "/shared/knoten", "Knoten")
    _insert_vector(temp_db, "node", "n1")
    stale = _vector_bytes(temp_db, "node", "n1")
    kms.knowledge_update("n1", summary="Neue Zusammenfassung")
    assert _vector_exists(temp_db, "node", "n1")
    assert _vector_bytes(temp_db, "node", "n1") != stale


def test_tags_only_change_rebuilds_node_vector(temp_db):
    """ADR-032: updated_at bumpt bei JEDEM Update, auch reinem Tags-Wechsel --
    ein liegen gelassener alter Vektor waere sofort wieder ein vector_gaps-
    Fund (Vektor aelter als updated_at). Deshalb auch hier neu gebaut."""
    _insert_node(temp_db, "n1", "/shared/knoten", "Knoten")
    _insert_vector(temp_db, "node", "n1")
    stale = _vector_bytes(temp_db, "node", "n1")
    result = kms.knowledge_update("n1", tags=["a", "b"])
    assert result["status"] == "updated"
    assert _vector_exists(temp_db, "node", "n1")
    assert _vector_bytes(temp_db, "node", "n1") != stale


def test_lesson_text_change_rebuilds_lesson_vector(temp_db):
    rec = kms.lesson_record("error", "Urspruengliche Beschreibung.")
    lesson_id = rec["id"]
    first = _vector_bytes(temp_db, "lesson", lesson_id)
    assert first is not None, "lesson_record haette den Vektor schon bauen sollen (ADR-032)"
    kms.lesson_update(lesson_id, description="Korrigierte Beschreibung.")
    assert _vector_exists(temp_db, "lesson", lesson_id)
    assert _vector_bytes(temp_db, "lesson", lesson_id) != first


def test_lesson_resolution_only_change_rebuilds_vector(temp_db):
    """ADR-032: last_seen bumpt bei JEDEM lesson_update, auch reinem
    resolution-Wechsel (resolution fliesst laut build_embeddings.py selbst
    NICHT in den Embedding-Text ein) -- ohne Neubau waere das sofort wieder
    ein vector_gaps-Fund."""
    rec = kms.lesson_record("error", "Beschreibung bleibt gleich.")
    lesson_id = rec["id"]
    assert _vector_exists(temp_db, "lesson", lesson_id)
    result = kms.lesson_update(lesson_id, resolution="So wurde es geloest.")
    assert result["status"] == "updated"
    assert _vector_exists(temp_db, "lesson", lesson_id)


# --- P5: Wikilinks -> Kanten -------------------------------------------------

def test_known_wikilink_creates_one_relation(temp_db):
    _insert_node(temp_db, "target", "/shared/ziel", "Zielknoten")
    result = kms.knowledge_add("/shared", "Quellknoten", "Zsf",
                               content="siehe [[Zielknoten]]", source="test")
    assert result["relations_created"] == ["/shared/ziel"]
    rows = _relations_from(temp_db, result["path"])
    assert len(rows) == 1
    assert rows[0]["target_path"] == "/shared/ziel"


def test_unknown_wikilink_creates_no_relation_but_is_reported(temp_db):
    result = kms.knowledge_add("/shared", "Quellknoten", "Zsf",
                               content="siehe [[gibt-es-nicht]]", source="test")
    assert result["relations_created"] == []
    assert "gibt-es-nicht" in result["unresolved_links"]
    assert _relations_from(temp_db, result["path"]) == []


def test_update_removing_link_drops_old_edge(temp_db):
    _insert_node(temp_db, "target", "/shared/ziel", "Zielknoten")
    add_result = kms.knowledge_add("/shared", "Quellknoten", "Zsf",
                                   content="siehe [[Zielknoten]]", source="test")
    assert len(_relations_from(temp_db, add_result["path"])) == 1

    kms.knowledge_update(add_result["id"], content="kein Verweis mehr")
    assert _relations_from(temp_db, add_result["path"]) == []


def test_duplicate_wikilink_creates_only_one_relation(temp_db):
    _insert_node(temp_db, "target", "/shared/ziel", "Zielknoten")
    result = kms.knowledge_add("/shared", "Quellknoten", "Zsf",
                               content="[[Zielknoten]] und nochmal [[Zielknoten]]", source="test")
    assert result["relations_created"] == ["/shared/ziel"]
    assert len(_relations_from(temp_db, result["path"])) == 1


def test_self_link_creates_no_relation(temp_db):
    _insert_node(temp_db, "self", "/shared/selbstbezug", "Selbstbezug")
    result = kms.knowledge_update("self", content="siehe [[Selbstbezug]]")
    assert result["relations_created"] == []
    assert _relations_from(temp_db, "/shared/selbstbezug") == []


# --- Auftrag 2026-08-09: DELETE vor _sync_wikilinks darf nur 'references' --
# treffen, sonst reisst jedes knowledge_update() gerechnete Aehnlichkeits-
# kanten und von Hand gesetzte Belegkanten mit, die _sync_wikilinks gar nicht
# neu anlegen kann (die stammen nicht aus [[Wiki-Links]] im content).

def test_update_keeps_analogous_to_edge(temp_db):
    _insert_node(temp_db, "quelle", "/shared/quelle", "Quelle", content="ohne links")
    _insert_node(temp_db, "ziel", "/shared/ziel", "Ziel")
    _insert_relation(temp_db, "/shared/quelle", "/shared/ziel", "analogous_to")

    kms.knowledge_update("quelle", content="immer noch ohne links")

    types = {r["relation_type"] for r in _relations_from(temp_db, "/shared/quelle")}
    assert "analogous_to" in types, "von Hand gesetzte Belegkante darf ein knowledge_update nicht ueberleben"


def test_update_keeps_aehnlich_bedeutung_edge(temp_db):
    _insert_node(temp_db, "quelle", "/shared/quelle", "Quelle", content="ohne links")
    _insert_node(temp_db, "ziel", "/shared/ziel", "Ziel")
    _insert_relation(temp_db, "/shared/quelle", "/shared/ziel", "aehnlich_bedeutung")

    kms.knowledge_update("quelle", content="immer noch ohne links")

    types = {r["relation_type"] for r in _relations_from(temp_db, "/shared/quelle")}
    assert "aehnlich_bedeutung" in types, "gerechnete Aehnlichkeitskante darf ein knowledge_update nicht ueberleben"


def test_update_still_drops_removed_wikilink_reference_edge(temp_db):
    """Gegenrichtung: die Einschraenkung darf das Loeschen nicht abschalten,
    nur auf 'references' begrenzen -- ein aus dem content entfernter
    [[Wiki-Link]] muss weiterhin verschwinden."""
    _insert_node(temp_db, "ziel", "/shared/ziel", "Zielknoten")
    add_result = kms.knowledge_add("/shared", "Quellknoten", "Zsf",
                                   content="siehe [[Zielknoten]]", source="test")
    assert len(_relations_from(temp_db, add_result["path"])) == 1

    kms.knowledge_update(add_result["id"], content="kein Verweis mehr")

    rows = _relations_from(temp_db, add_result["path"])
    assert not any(r["relation_type"] == "references" for r in rows)


def test_update_without_content_leaves_relations_untouched(temp_db):
    """Negativfall: ein Update ohne content-Aenderung ruft _sync_wikilinks
    (und damit das DELETE davor) gar nicht auf -- Kanten jeder Art bleiben
    unangetastet."""
    _insert_node(temp_db, "quelle", "/shared/quelle", "Quelle", content="siehe [[Ziel]]")
    _insert_node(temp_db, "ziel", "/shared/ziel", "Ziel")
    _insert_relation(temp_db, "/shared/quelle", "/shared/ziel", "analogous_to")
    _insert_relation(temp_db, "/shared/quelle", "/shared/ziel", "aehnlich_bedeutung")
    _insert_relation(temp_db, "/shared/quelle", "/shared/ziel", "references")

    before = {r["relation_type"] for r in _relations_from(temp_db, "/shared/quelle")}
    result = kms.knowledge_update("quelle", tags=["a"])
    assert result["status"] == "updated"
    after = {r["relation_type"] for r in _relations_from(temp_db, "/shared/quelle")}

    assert before == after == {"analogous_to", "aehnlich_bedeutung", "references"}
