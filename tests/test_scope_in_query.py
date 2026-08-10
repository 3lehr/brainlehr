"""Abnahme fuer AP "Bereich in der Abfrage, nicht als Sieb dahinter" —
knowledge_search() und lesson_query() in knowledge_mcp_server.py.

Kernpruefung: ein sehr gut passendes Fremd-Dokument aus einem anderen Bereich
darf weder Rangfolge noch Trefferzahl in eigenen Bereich veraendern. Bei einem
nachgelagerten Filter waeren sie es. Gemessen per A/B: Anfrage einmal mit,
einmal ohne Fremd-Dokument, Reihenfolge+Zahl muessen identisch sein.
"""
from __future__ import annotations

import sqlite3
import struct
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
    conn.executemany(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, norm_entscheidung, "
        "norm_entschieden_von, norm_entschieden_grund) "
        "VALUES (?, ?, ?, ?, ?, NULL, 0, 'test', 'keine_norm', 'skript:test', 'Testvorrichtung')",
        [
            ("n-own", "/projA/regel", "projA", "Abschreibungsregel projA",
             "Regel zur Abschreibung von Anlageguetern im ersten Jahr"),
            ("n-foreign", "/projB/regel", "projB", "Abschreibungsregel projB",
             "Regel zur Abschreibung von Anlageguetern, ebenfalls projB"),
            ("n-shared", "/shared/regel", "shared", "Abschreibung geteilt",
             "Geteilter Knoten, in jedem Bereich sichtbar"),
        ],
    )
    conn.executemany(
        "INSERT INTO lessons_learned (id, type, description, root_cause, prevention, projects) "
        "VALUES (?, 'insight', ?, ?, ?, ?)",
        [
            ("L-own", "Abschreibung falsch verbucht in projA",
             "Ursache projA", "Vermeidung projA", '["projA"]'),
            ("L-foreign", "Abschreibung falsch verbucht in projB",
             "Ursache projB", "Vermeidung projB", '["projB"]'),
            ("L-multi", "Abschreibung mehrwertige Lehre in beiden Bereichen",
             "Ursache multi", "Vermeidung multi", '["projA", "projB"]'),
        ],
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _vec(*floats: float) -> bytes:
    return struct.pack(f"<{len(floats)}f", *floats)


def _insert_embedding(db_path: Path, kind: str, ref_id: str, vector: tuple[float, ...],
                       project_id: str = "shared"):
    # model = das aktuell konfigurierte Modell, nicht ein fester String -- die
    # Modell-Sperre (Auftrag 2026-08-07, knowledge_mcp_server._embedding_ranking)
    # ignoriert sonst jede hier eingefuegte Zeile.
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT OR REPLACE INTO knowledge_embeddings (kind, ref_id, project_id, model, dim, vector, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, '2026-08-05T00:00:00+01:00')",
        (kind, ref_id, project_id, kms.embeddings.DEFAULT_EMBED_MODEL, len(vector), _vec(*vector)),
    )
    conn.commit()
    conn.close()


# --- Knotensuche: FTS-Ebene --------------------------------------------------

def test_node_search_scoped_returns_only_own_project(temp_db, monkeypatch):
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: None)
    result = kms.knowledge_search("Abschreibung", scope="projA")
    ids = [r["id"] for r in result["results"]]
    assert "n-own" in ids
    assert "n-foreign" not in ids
    assert "n-shared" in ids  # shared bleibt in jedem Bereich sichtbar


def test_knowledge_search_scoped_returns_only_own_project_lessons(temp_db, monkeypatch):
    """Auftrag 2026-08-07: dieselbe Bereichsfilterung gilt jetzt auch fuer
    die in knowledge_search() mitgelieferten Lehren (allowed_lesson_ids)."""
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: None)
    result = kms.knowledge_search("Abschreibung", scope="projA")
    lesson_ids = [r["id"] for r in result["results"] if r["kind"] == "lesson"]
    assert "L-own" in lesson_ids
    assert "L-foreign" not in lesson_ids
    assert "L-multi" in lesson_ids  # mehrwertig, projA gehoert dazu


def test_node_search_scoped_rank_and_count_unaffected_by_foreign_doc(temp_db, monkeypatch):
    """Kein Sieb: Fremd-Dokument entfernen darf Reihenfolge/Zahl im eigenen
    Bereich nicht aendern, sonst haette es vorher mitgezaehlt."""
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: None)
    with_foreign = kms.knowledge_search("Abschreibung", scope="projA")

    conn = sqlite3.connect(str(temp_db))
    conn.execute("DELETE FROM knowledge_nodes WHERE id = 'n-foreign'")
    conn.commit()
    conn.close()

    without_foreign = kms.knowledge_search("Abschreibung", scope="projA")
    assert [r["id"] for r in with_foreign["results"]] == [r["id"] for r in without_foreign["results"]]
    assert with_foreign["count"] == without_foreign["count"]


# --- Knotensuche: Vektor-Ebene ----------------------------------------------

def test_node_search_scoped_excludes_foreign_project_from_vector_candidates(temp_db, monkeypatch):
    """Ein sehr aehnliches Fremd-Dokument darf gar nicht erst in die
    Kandidatenmenge der Aehnlichkeitsrechnung geraten."""
    _insert_embedding(temp_db, "node", "n-own", (1.0, 0.0), project_id="projA")
    _insert_embedding(temp_db, "node", "n-foreign", (1.0, 0.0), project_id="projB")  # identisch aehnlich
    _insert_embedding(temp_db, "node", "n-shared", (0.0, 1.0), project_id="shared")  # orthogonal, unbeteiligt

    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0])
    result = kms.knowledge_search("Abschreibung", scope="projA", max_results=5)
    ids = [r["id"] for r in result["results"]]
    assert "n-foreign" not in ids


# --- Lehrensuche: Stichwort-Ebene --------------------------------------------

def test_lesson_query_scoped_returns_only_own_project(temp_db, monkeypatch):
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: None)
    result = kms.lesson_query(project="projA", query="Abschreibung", status=None)
    ids = [r["id"] for r in result["results"]]
    assert "L-own" in ids
    assert "L-foreign" not in ids


def test_lesson_query_scoped_rank_and_count_unaffected_by_foreign_lesson(temp_db, monkeypatch):
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: None)
    with_foreign = kms.lesson_query(project="projA", query="Abschreibung", status=None)

    conn = sqlite3.connect(str(temp_db))
    conn.execute("DELETE FROM lessons_learned WHERE id = 'L-foreign'")
    conn.commit()
    conn.close()

    without_foreign = kms.lesson_query(project="projA", query="Abschreibung", status=None)
    assert [r["id"] for r in with_foreign["results"]] == [r["id"] for r in without_foreign["results"]]
    assert with_foreign["count"] == without_foreign["count"]


# --- Lehrensuche: Vektor-Ebene -----------------------------------------------

def test_lesson_query_scoped_excludes_foreign_project_from_vector_candidates(temp_db, monkeypatch):
    _insert_embedding(temp_db, "lesson", "L-own", (1.0, 0.0), project_id="projA")
    _insert_embedding(temp_db, "lesson", "L-foreign", (1.0, 0.0), project_id="projB")
    _insert_embedding(temp_db, "lesson", "L-multi", (0.0, 1.0), project_id="projA")
    _insert_embedding(temp_db, "lesson", "L-multi", (0.0, 1.0), project_id="projB")

    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0])
    result = kms.lesson_query(project="projA", query="Abschreibung", status=None, max_results=5)
    ids = [r["id"] for r in result["results"]]
    assert "L-foreign" not in ids


# --- Mehrwertige Lehre: je einmal, nicht doppelt -----------------------------

def test_multivalued_lesson_visible_once_in_each_of_its_scopes(temp_db, monkeypatch):
    _insert_embedding(temp_db, "lesson", "L-multi", (1.0, 0.0), project_id="projA")
    _insert_embedding(temp_db, "lesson", "L-multi", (1.0, 0.0), project_id="projB")

    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0])

    for scope in ("projA", "projB"):
        result = kms.lesson_query(project=scope, query="Abschreibung", status=None, max_results=10)
        ids = [r["id"] for r in result["results"]]
        assert ids.count("L-multi") == 1, f"L-multi mehrfach im Ergebnis fuer scope={scope}: {ids}"


def test_multivalued_lesson_score_not_inflated_by_row_count(temp_db, monkeypatch):
    """Root-cause-Probe fuer den Fix in _embedding_ranking: eine ECHT
    aehnlichere einwertige Lehre (L-own, cos=0.95) muss vor einer weniger
    aehnlichen mehrwertigen Lehre (L-multi, cos=0.90, aber zwei Bereichs-
    Zeilen mit gleichem Vektor) liegen. Vor dem Fix zaehlt jede zusaetzliche
    Zeile erneut in die RRF-Fusion ein (zwei Rang-Positionen statt einer) und
    haengt L-multi allein durch Zeilenzahl vor die eigentlich relevantere
    Lehre -- ohne dass ein Stichwort- oder Bedeutungsunterschied das
    rechtfertigt."""
    _insert_embedding(temp_db, "lesson", "L-own", (0.95, 0.31225), project_id="projA")  # cos ~0.95
    _insert_embedding(temp_db, "lesson", "L-multi", (0.9, 0.43589), project_id="projA")  # cos ~0.90
    _insert_embedding(temp_db, "lesson", "L-multi", (0.9, 0.43589), project_id="projB")  # zweite Zeile, gleicher Vektor

    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0])
    # Anfragewort, das in keiner Lehre woertlich vorkommt -> reiner Embedding-Pfad.
    result = kms.lesson_query(project="projA", query="qqqqqq zzzzzz", status=None)
    ids = [r["id"] for r in result["results"]]
    assert ids.index("L-own") < ids.index("L-multi"), (
        f"L-own ist echt aehnlicher (cos 0.95 > 0.90), darf trotzdem nicht "
        f"hinter L-multi liegen, nur weil L-multi zwei Bereichs-Zeilen hat: {ids}"
    )


def test_multivalued_lesson_visible_once_without_scope_too(temp_db, monkeypatch):
    """Regressionsschutz fuer den Bug, den die Vektortabelle mit ihrer
    Je-Bereich-eine-Zeile-Struktur nahelegt: auch ohne scope duerfen die
    beiden Zeilen (gleicher Vektor, verschiedene project_id) die Lehre nicht
    doppelt in die Kandidatenliste einspeisen."""
    _insert_embedding(temp_db, "lesson", "L-multi", (1.0, 0.0), project_id="projA")
    _insert_embedding(temp_db, "lesson", "L-multi", (1.0, 0.0), project_id="projB")

    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0])
    result = kms.lesson_query(query="Abschreibung", status=None, max_results=10)
    ids = [r["id"] for r in result["results"]]
    assert ids.count("L-multi") == 1


# --- Gegenprobe: ohne Bereichsangabe unveraendert ----------------------------

def test_knowledge_search_without_scope_unchanged(temp_db, monkeypatch):
    """Auftrag 2026-08-07: knowledge_search() liefert seither Knoten UND
    Lehren gemischt (Feld "kind") -- vorher nur Knoten. Ohne scope (= "all")
    bleiben beide Sorten ungefiltert, die Knotenmenge selbst ist unveraendert
    (siehe test_node_search_scoped_returns_only_own_project fuer die
    Bereichsfilterung)."""
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: None)
    result = kms.knowledge_search("Abschreibung")
    node_ids = {r["id"] for r in result["results"] if r["kind"] == "node"}
    lesson_ids = {r["id"] for r in result["results"] if r["kind"] == "lesson"}
    assert node_ids == {"n-own", "n-foreign", "n-shared"}
    assert lesson_ids == {"L-own", "L-foreign", "L-multi"}


def test_lesson_query_without_scope_unchanged(temp_db, monkeypatch):
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: None)
    result = kms.lesson_query(query="Abschreibung", status=None)
    ids = {r["id"] for r in result["results"]}
    assert ids == {"L-own", "L-foreign", "L-multi"}
