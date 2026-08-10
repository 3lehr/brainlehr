"""Tests fuer kanten_aus_bedeutung.py -- Kanten aus vorhandenen Embeddings.

Rot-vor-Gruen: vor der Implementierung von kanten_aus_bedeutung.py schlagen
alle Tests hier beim Import fehl (ModuleNotFoundError), danach bestehen sie.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import kanten_aus_bedeutung as kab  # noqa: E402
from embeddings import cosine_similarity, pack_embedding  # noqa: E402


# ─── Hilfsfunktionen fuer die DB-gestuetzten Tests ──────────────────────────

@pytest.fixture()
def temp_db(tmp_path):
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    return db_path


def _insert_node(conn: sqlite3.Connection, path: str, title: str) -> str:
    """Minimaler, den schema.sql-Triggern genuegender Knoten (Testvorrichtung,
    keine echte Normfrage)."""
    node_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO knowledge_nodes
        (id, path, parent_path, project_id, title, summary, source, anlass,
         norm_entscheidung, norm_entschieden_von, norm_entschieden_am, norm_entschieden_grund,
         created_at, updated_at)
        VALUES (?, ?, NULL, 'shared', ?, ?, 'test', 'skript',
                'keine_norm', 'test', ?, 'Testvorrichtung, keine echte Norm-Pruefung',
                ?, ?)
        """,
        (node_id, path, title, f"Testknoten {title}", now, now, now),
    )
    return node_id


def _insert_embedding(conn: sqlite3.Connection, node_id: str, vector: list[float]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO knowledge_embeddings (kind, ref_id, project_id, model, dim, vector, updated_at)
        VALUES ('node', ?, 'shared', ?, ?, ?, ?)
        """,
        (node_id, kab.EMBED_MODEL, len(vector), pack_embedding(vector), now),
    )


def _knoten_mit_vektor(conn, path, title, vector):
    node_id = _insert_node(conn, path, title)
    _insert_embedding(conn, node_id, vector)
    return node_id


# ─── Negativfall: unaehnliche Knoten bekommen KEINE Kante ───────────────────

def test_unaehnliche_knoten_bekommen_keine_kante():
    paths = ["/a", "/b"]
    titles = ["A", "B"]
    # orthogonale Vektoren -> Kosinus-Aehnlichkeit exakt 0.0
    vektoren = [[1.0, 0.0], [0.0, 1.0]]
    kandidaten = kab.finde_kandidaten(paths, titles, vektoren, schwelle=0.5, k=5)
    assert kandidaten == []


# ─── Keine Selbstkante ───────────────────────────────────────────────────────

def test_keine_selbstkante():
    paths = ["/a", "/b", "/c"]
    titles = ["A", "B", "C"]
    # identische Vektoren -> Aehnlichkeit zu sich selbst waere 1.0, muss aber
    # nie als Kandidat auftauchen
    vektoren = [[1.0, 0.0]] * 3
    kandidaten = kab.finde_kandidaten(paths, titles, vektoren, schwelle=0.5, k=5)
    for kd in kandidaten:
        assert kd.a_path != kd.b_path


# ─── Grenzwert: Schwelle-1, Schwelle, Schwelle+1 (im Sinne einer minimalen
#     Verschiebung um die tatsaechlich gemessene Aehnlichkeit, nicht um "1") ──

def test_grenzwert_schwelle_minus_gleich_plus():
    vec_a = [1.0, 0.0]
    vec_b = [0.6, 0.8]  # feste Kosinus-Aehnlichkeit, unten exakt nachgemessen
    sim = cosine_similarity(vec_a, vec_b)

    paths = ["/a", "/b"]
    titles = ["A", "B"]
    vektoren = [vec_a, vec_b]

    # Schwelle == gemessene Aehnlichkeit: inklusiv, Kante entsteht (>=)
    an_schwelle = kab.finde_kandidaten(paths, titles, vektoren, schwelle=sim, k=5)
    assert len(an_schwelle) == 1

    # Schwelle knapp UEBER der gemessenen Aehnlichkeit: keine Kante mehr
    ueber_schwelle = kab.finde_kandidaten(paths, titles, vektoren, schwelle=sim + 0.0001, k=5)
    assert ueber_schwelle == []

    # Schwelle knapp UNTER der gemessenen Aehnlichkeit: weiterhin eine Kante
    unter_schwelle = kab.finde_kandidaten(paths, titles, vektoren, schwelle=sim - 0.0001, k=5)
    assert len(unter_schwelle) == 1


# ─── Obergrenze je Knoten (k naechste Nachbarn) ─────────────────────────────

def test_k_obergrenze_je_knoten():
    # Ein Zentralknoten "/z" ist fast identisch zu vier anderen Knoten
    # (alle deutlich ueber der Schwelle) -- mit k=2 duerfen aus SEINER
    # Nachbarschaft hoechstens 2 Kanten in seine Top-k-Liste einfliessen.
    paths = ["/z", "/n1", "/n2", "/n3", "/n4"]
    titles = paths[:]
    vektoren = [
        [1.0, 0.0],
        [0.999, 0.045],
        [0.998, 0.063],
        [0.997, 0.077],
        [0.996, 0.089],
    ]
    kandidaten = kab.finde_kandidaten(paths, titles, vektoren, schwelle=0.9, k=2)
    beteiligt_z = [kd for kd in kandidaten if kd.a_path == "/z" or kd.b_path == "/z"]
    assert len(beteiligt_z) <= 2, beteiligt_z


# ─── Keine Dublette bei einem einzelnen Lauf (ungerichtet dedupliziert) ─────

def test_keine_dublette_pro_lauf():
    paths = ["/a", "/b"]
    titles = ["A", "B"]
    vektoren = [[1.0, 0.0], [0.9, 0.436]]
    kandidaten = kab.finde_kandidaten(paths, titles, vektoren, schwelle=0.5, k=5)
    paare = {frozenset((kd.a_path, kd.b_path)) for kd in kandidaten}
    assert len(paare) == len(kandidaten)


# ─── Idempotenz: zweiter Lauf gegen dieselbe DB legt nichts Neues an ────────

def test_idempotenz_zweiter_lauf_erzeugt_nichts_neues(temp_db):
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    _knoten_mit_vektor(conn, "/a", "A", [1.0, 0.0])
    _knoten_mit_vektor(conn, "/b", "B", [0.9, 0.436])
    conn.commit()

    paths, titles, vektoren = kab.lade_knoten_vektoren(conn)
    kandidaten = kab.finde_kandidaten(paths, titles, vektoren, schwelle=0.5, k=5)
    assert len(kandidaten) == 1

    created1, skipped1 = kab.schreibe_kanten(conn, kandidaten)
    assert created1 == 1
    assert skipped1 == 0

    anzahl_nach_erstem_lauf = conn.execute(
        "SELECT COUNT(*) FROM knowledge_relations WHERE relation_type = ?", (kab.RELATION_TYPE,)
    ).fetchone()[0]
    assert anzahl_nach_erstem_lauf == 1

    # Zweiter, identischer Lauf
    created2, skipped2 = kab.schreibe_kanten(conn, kandidaten)
    assert created2 == 0
    assert skipped2 == 1

    anzahl_nach_zweitem_lauf = conn.execute(
        "SELECT COUNT(*) FROM knowledge_relations WHERE relation_type = ?", (kab.RELATION_TYPE,)
    ).fetchone()[0]
    assert anzahl_nach_zweitem_lauf == 1

    conn.close()


# ─── Bestehende Kanten anderer Herkunft werden nicht ueberschrieben ─────────

def test_bestehende_kante_anderer_herkunft_bleibt_unberuehrt(temp_db):
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    _knoten_mit_vektor(conn, "/a", "A", [1.0, 0.0])
    _knoten_mit_vektor(conn, "/b", "B", [0.9, 0.436])
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO knowledge_relations
        (id, source_path, target_path, relation_type, confidence, weight,
         evidence, source, creator, model, session, created_at, updated_at)
        VALUES (?, '/a', '/b', 'analogous_to', 0.9, 1.0, 'von Hand', 'betreiber',
                'betreiber', NULL, NULL, ?, ?)
        """,
        (str(uuid.uuid4()), now, now),
    )
    conn.commit()

    paths, titles, vektoren = kab.lade_knoten_vektoren(conn)
    kandidaten = kab.finde_kandidaten(paths, titles, vektoren, schwelle=0.5, k=5)
    created, skipped = kab.schreibe_kanten(conn, kandidaten)
    assert created == 1  # unsere eigene Kante (anderer relation_type) entsteht zusaetzlich

    rows = conn.execute(
        "SELECT relation_type FROM knowledge_relations WHERE source_path='/a' AND target_path='/b' ORDER BY relation_type"
    ).fetchall()
    relation_types = {r["relation_type"] for r in rows}
    assert relation_types == {"analogous_to", kab.RELATION_TYPE}

    conn.close()
