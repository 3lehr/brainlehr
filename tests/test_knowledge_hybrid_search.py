"""Tests fuer die Hybrid-Suche (FTS5/LIKE + optionale lokale Embeddings) in
knowledge_mcp_server.py.

Befund, der diese Arbeit ausgeloest hat: reines FTS5-Stichwortmatching findet
"AfA"/"AVEUER" nicht bei einer Suche nach "Abschreibung" -- falsche Nadel,
kein Treffer, gelesen als "gibt es nicht". Diese Tests pruefen die fuenf
Abnahme-Kriterien aus dem Auftrag:
  1. Ohne Vektoren identisch zum bisherigen FTS5/LIKE-Verhalten.
  2. Modell nicht erreichbar -> trotzdem Stichworttreffer, kein Fehler.
  3. Mit Vektoren: Treffer ohne den Suchbegriff im Wortlaut.
  4. Fusion verliert keinen Stichworttreffer, der heute gefunden wuerde.
  5. DB ohne knowledge_embeddings-Tabelle oeffnet und liefert weiterhin.

Die echte Gegenprobe am Live-Bestand (rund 275 Lehren/145 Knoten, echtes
Ollama-Modell) läuft separat per `build_embeddings.py` + manuellem Aufruf,
nicht hier -- dieser Test nutzt synthetische Vektoren, damit er ohne
Netzwerk/Modell deterministisch bleibt.
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


# --- Fixtures ---------------------------------------------------------------

@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Frische Test-DB mit dem echten (additiven) Schema, DB_PATH umgebogen."""
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.executemany(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source) "
        "VALUES (?, ?, 'shared', ?, ?, NULL, 0, 'test')",
        [
            ("n1", "/steuer/aveuer-regel", "AVEUER Sonderabschreibung",
             "Regel zur Abschreibung von Anlagegütern im ersten Jahr"),
            ("n2", "/freizeit/katzen", "Katzen sind neugierig",
             "Ein Text ganz ohne Bezug zu Steuern oder Buchhaltung"),
            ("n3", "/steuer/afa-tabelle", "AfA-Tabelle Steuer",
             "Nutzungsdauer und Restwert fuer Wirtschaftsgueter, amtliche Tabelle"),
        ],
    )
    conn.executemany(
        "INSERT INTO lessons_learned (id, type, description, root_cause, prevention, projects) "
        "VALUES (?, 'insight', ?, ?, ?, '[]')",
        [
            ("L-aaa111", "Falscher Interpreter liess Tests dauerhaft als kaputt gelten",
             "System-python3 statt .venv/bin/python verwendet",
             "Immer den Projekt-Interpreter fuer Testlaeufe nutzen"),
            ("L-bbb222", "Katzenfutter-Lieferung war drei Tage verspaetet",
             "Lieferant hatte Lagerengpass", "Fruehzeitiger nachbestellen"),
        ],
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _fake_vec(*floats: float) -> bytes:
    return struct.pack(f"<{len(floats)}f", *floats)


def _insert_embedding(db_path: Path, kind: str, ref_id: str, vector: tuple[float, ...],
                       model: str | None = None):
    # model default = das aktuell konfigurierte Modell (kms.embeddings.DEFAULT_EMBED_MODEL),
    # NICHT ein fester String -- die Modell-Sperre (Auftrag 2026-08-07) liest nur Vektoren
    # mit passendem model, ein hartkodierter Fremdname wuerde jeden Test hier sonst
    # unbemerkt auf reines FTS5-Verhalten zurueckfallen lassen.
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT OR REPLACE INTO knowledge_embeddings (kind, ref_id, model, dim, vector, updated_at) "
        "VALUES (?, ?, ?, ?, ?, '2026-07-31T00:00:00+01:00')",
        (kind, ref_id, model or kms.embeddings.DEFAULT_EMBED_MODEL, len(vector), _fake_vec(*vector)),
    )
    conn.commit()
    conn.close()


# --- 1. Ohne Vektoren: identisch zum bisherigen FTS5-Verhalten --------------

def test_knowledge_search_without_vectors_matches_plain_fts_order(temp_db, monkeypatch):
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: None)

    hybrid = kms.knowledge_search("Abschreibung")

    # Referenz: die alte, reine FTS5-Abfrage (Wortlaut vor diesem Umbau).
    conn = kms.get_db()
    plain_rows = conn.execute(
        """SELECT n.id FROM knowledge_fts f JOIN knowledge_nodes n ON f.rowid = n.rowid
           WHERE knowledge_fts MATCH ? ORDER BY rank""",
        ("Abschreibung",),
    ).fetchall()
    conn.close()
    plain_ids = [r["id"] for r in plain_rows][:10]

    assert [r["id"] for r in hybrid["results"]] == plain_ids
    assert plain_ids == ["n1"]  # nur n1 enthaelt "Abschreibung" woertlich


# --- 2. Modell nicht erreichbar -> trotzdem Stichworttreffer, kein Fehler --

def test_knowledge_search_survives_unreachable_model(temp_db, monkeypatch):
    def boom(*a, **k):
        return None  # embed_text() ist per Vertrag best-effort, nie ein Raise

    monkeypatch.setattr(kms.embeddings, "embed_text", boom)
    result = kms.knowledge_search("Abschreibung")
    assert result["count"] == 1
    assert result["results"][0]["id"] == "n1"


def test_lesson_query_survives_unreachable_model(temp_db, monkeypatch):
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: None)
    result = kms.lesson_query(query="Interpreter")
    assert result["count"] == 1
    assert result["results"][0]["id"] == "L-aaa111"


# --- 3. Mit Vektoren: Treffer ohne den Suchbegriff im Wortlaut --------------

def test_knowledge_search_finds_node_via_meaning_not_wording(temp_db, monkeypatch):
    # n3 ("AfA-Tabelle") enthaelt "Abschreibung" nirgends woertlich -> FTS
    # findet es nicht. Vektor von n3 liegt trotzdem nah am Query-Vektor.
    _insert_embedding(temp_db, "node", "n1", (1.0, 0.0, 0.0))
    _insert_embedding(temp_db, "node", "n3", (0.95, 0.05, 0.0))   # semantisch nah
    _insert_embedding(temp_db, "node", "n2", (0.0, 1.0, 0.0))     # unbeteiligt, orthogonal

    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0, 0.0])

    plain_ids = {"n1"}  # reiner FTS5-Treffer fuer "Abschreibung"
    # max_results=2 knapp gehalten, damit der unbeteiligte, orthogonale
    # Knoten n2 (schwaechster Kandidat) sichtbar herausfaellt.
    result = kms.knowledge_search("Abschreibung", max_results=2)
    result_ids = [r["id"] for r in result["results"]]

    assert "n3" in result_ids, "semantisch verwandter Knoten ohne Wortlaut-Treffer wurde nicht gefunden"
    assert "n1" in result_ids  # der Stichworttreffer bleibt erhalten (siehe Test 4)
    assert "n2" not in result_ids, "unbeteiligter, orthogonaler Knoten wurde faelschlich promotet"
    assert plain_ids <= set(result_ids)


def test_embedding_with_foreign_model_is_never_used(temp_db, monkeypatch):
    # Auftrag 2026-08-07: Vektoren aus zwei Modellen liegen in verschiedenen
    # Raeumen -- ein Vektor mit fremdem Modellnamen darf nie in die
    # Kosinus-Rechnung einfliessen, auch wenn er (wie hier) exakt am
    # Query-Vektor liegt. n3 traegt absichtlich ein anderes Modell als das
    # aktuell konfigurierte -- ohne die Sperre waere es der Top-Treffer.
    _insert_embedding(temp_db, "node", "n1", (1.0, 0.0, 0.0))
    _insert_embedding(temp_db, "node", "n3", (1.0, 0.0, 0.0), model="alt-modell-vor-umstellung")

    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0, 0.0])
    result = kms.knowledge_search("Abschreibung", max_results=3)
    result_ids = [r["id"] for r in result["results"]]

    assert "n3" not in result_ids, "Vektor mit fremdem Modellnamen wurde trotz Sperre benutzt"
    assert "n1" in result_ids  # Stichworttreffer bleibt unberuehrt


def test_lesson_query_finds_lesson_via_meaning_not_wording(temp_db, monkeypatch):
    _insert_embedding(temp_db, "lesson", "L-aaa111", (1.0, 0.0))
    _insert_embedding(temp_db, "lesson", "L-bbb222", (0.0, 1.0))

    # Anfrage nutzt komplett andere Worte als die Lesson-Beschreibung, trifft
    # aber semantisch (via fest verdrahtetem Fake-Vektor) L-aaa111.
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0])
    # max_results=1 knapp gehalten, damit die unbeteiligte Lesson sichtbar herausfaellt.
    result = kms.lesson_query(query="virtuelle Umgebung fuer Testlaeufe verwenden", max_results=1)
    result_ids = [r["id"] for r in result["results"]]
    assert "L-aaa111" in result_ids
    assert "L-bbb222" not in result_ids


# --- 4. Fusion verliert keinen Stichworttreffer -----------------------------

def test_fusion_never_drops_a_keyword_hit(temp_db, monkeypatch):
    # n1 ist der einzige Stichworttreffer, bekommt aber einen Vektor, der
    # WEIT vom Query-Vektor entfernt liegt (waere also embedding-seitig ganz
    # unten) -- muss trotzdem im Ergebnis erscheinen.
    _insert_embedding(temp_db, "node", "n1", (-1.0, 0.0, 0.0))   # entgegengesetzt
    _insert_embedding(temp_db, "node", "n2", (1.0, 0.0, 0.0))    # embedding-seitig top
    _insert_embedding(temp_db, "node", "n3", (0.9, 0.1, 0.0))    # embedding-seitig top

    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0, 0.0])
    result = kms.knowledge_search("Abschreibung", max_results=2)
    result_ids = [r["id"] for r in result["results"]]
    assert "n1" in result_ids, "Stichworttreffer wurde von embedding-staerkeren Kandidaten verdraengt"


# --- 5. DB ohne knowledge_embeddings-Tabelle oeffnet und liefert weiterhin -

def test_knowledge_search_works_without_embeddings_table(temp_db, monkeypatch):
    conn = sqlite3.connect(str(temp_db))
    conn.execute("DROP TABLE knowledge_embeddings")
    conn.commit()
    conn.close()

    # embed_text liefert hier sogar einen echten Vektor zurueck -- der Punkt
    # ist, dass die fehlende Tabelle selbst (nicht das Modell) toleriert wird.
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0, 0.0])
    result = kms.knowledge_search("Abschreibung")
    assert result["count"] == 1
    assert result["results"][0]["id"] == "n1"

    lesson_result = kms.lesson_query(query="Interpreter")
    assert lesson_result["count"] == 1
    assert lesson_result["results"][0]["id"] == "L-aaa111"


# --- Rollback-Schalter -------------------------------------------------------

def test_hybrid_embedding_weight_zero_reproduces_pure_keyword_order(temp_db, monkeypatch):
    """embedding_weight=0 (KNOWLEDGE_HYBRID_EMBEDDING_WEIGHT=0) muss die reine
    Stichwort-Reihenfolge reproduzieren, selbst wenn Vektoren vorhanden sind."""
    _insert_embedding(temp_db, "node", "n3", (1.0, 0.0, 0.0))
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0, 0.0])
    monkeypatch.setattr(kms.embeddings, "hybrid_retrieval_weight", lambda: 0.0)

    result = kms.knowledge_search("Abschreibung")
    assert [r["id"] for r in result["results"]] == ["n1"]
