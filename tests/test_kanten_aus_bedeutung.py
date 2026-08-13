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


def _embedding_zeile(conn, node_id, project_id, vector, updated_at=None) -> None:
    """Fuegt eine ZUSAETZLICHE knowledge_embeddings-Zeile fuer einen
    bestehenden Knoten unter einer ANDEREN project_id ein -- bildet die
    liegengebliebene Zeile einer frueheren Projektzuordnung nach (Befund
    2026-08-13, Auftrag 83: 88 Knoten im echten Bestand mit genau diesem
    Muster)."""
    now = updated_at or datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO knowledge_embeddings (kind, ref_id, project_id, model, dim, vector, updated_at)
        VALUES ('node', ?, ?, ?, ?, ?, ?)
        """,
        (node_id, project_id, kab.EMBED_MODEL, len(vector), pack_embedding(vector), now),
    )


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


# ─── Dedup liegengebliebener project_id-Zeilen (Auftrag 83, 2026-08-13) ─────
# Befund am echten Bestand: 88 Knoten mit zwei knowledge_embeddings-Zeilen
# (verschiedene project_id, gleicher ref_id) -- Folge einer spaeteren
# Projekt-Neuzuordnung, bei der die alte Zeile nie geloescht wurde. Ohne
# Dedup liefert lade_knoten_vektoren denselben Knotenpfad zweimal, und
# finde_kandidaten faende ausschliesslich Selbstpaare mit Aehnlichkeit 1.0.

def test_grenzwert_eine_zeile_bleibt_unveraendert(temp_db):
    """Grenzwert 1 von 3: ein Knoten mit genau EINER Embedding-Zeile."""
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    _knoten_mit_vektor(conn, "/eine-zeile", "Eine Zeile", [1.0, 0.0])
    conn.commit()

    paths, titles, vektoren = kab.lade_knoten_vektoren(conn)
    assert paths == ["/eine-zeile"]
    conn.close()


def test_grenzwert_zwei_zeilen_werden_zu_einer(temp_db):
    """Grenzwert 2 von 3: zwei Zeilen (aktuelle project_id 'shared' + eine
    liegengebliebene 'fahrtenbuch') duerfen nur EINMAL erscheinen, und zwar
    mit dem Vektor der zur aktuellen knowledge_nodes.project_id passenden
    Zeile."""
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    node_id = _knoten_mit_vektor(conn, "/zwei-zeilen", "Zwei Zeilen", [1.0, 0.0])
    liegengeblieben = [0.0, 1.0]
    _embedding_zeile(conn, node_id, "fahrtenbuch", liegengeblieben, updated_at="2020-01-01T00:00:00+00:00")
    conn.commit()

    paths, titles, vektoren = kab.lade_knoten_vektoren(conn)
    assert paths == ["/zwei-zeilen"]
    # der Vektor der ZUR AKTUELLEN project_id ('shared', siehe _insert_node)
    # passenden Zeile wird geliefert, nicht der liegengebliebenen.
    assert vektoren[0] == [1.0, 0.0]
    conn.close()


def test_grenzwert_drei_zeilen_werden_zu_einer(temp_db):
    """Grenzwert 3 von 3: drei Zeilen -- eine aktuelle, zwei liegengebliebene."""
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    node_id = _knoten_mit_vektor(conn, "/drei-zeilen", "Drei Zeilen", [1.0, 0.0])
    _embedding_zeile(conn, node_id, "fahrtenbuch", [0.0, 1.0], updated_at="2020-01-01T00:00:00+00:00")
    _embedding_zeile(conn, node_id, "openlehr", [0.5, 0.5], updated_at="2021-01-01T00:00:00+00:00")
    conn.commit()

    paths, titles, vektoren = kab.lade_knoten_vektoren(conn)
    assert paths == ["/drei-zeilen"]
    assert vektoren[0] == [1.0, 0.0]
    conn.close()


def test_dublette_erzeugt_keine_selbstkante(temp_db):
    """Rot vor der Implementierung: ein Knoten mit zwei Embedding-Zeilen
    (gleicher Vektor, wie im echten Bestand bei 86 von 88 Faellen) lieferte
    VOR dem Dedup ein Selbstpaar mit Aehnlichkeit 1.0 -- derselbe Pfad auf
    beiden Seiten. finde_kandidaten schliesst i==j zwar aus, aber nur
    INNERHALB einer einzigen Liste; zwei Listeneintraege fuer denselben
    Knoten sind fuer finde_kandidaten zwei verschiedene Indizes und daher
    KEIN i==j."""
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    node_id = _knoten_mit_vektor(conn, "/dublette", "Dublette", [1.0, 0.0])
    _embedding_zeile(conn, node_id, "fahrtenbuch", [1.0, 0.0], updated_at="2020-01-01T00:00:00+00:00")
    conn.commit()

    paths, titles, vektoren = kab.lade_knoten_vektoren(conn)
    kandidaten = kab.finde_kandidaten(paths, titles, vektoren, schwelle=0.5, k=5)
    assert kandidaten == [], (
        "ein einzelner Knoten mit zwei liegengebliebenen Zeilen darf nach "
        "dem Dedup keine Kante (erst recht keine Selbstkante) erzeugen"
    )
    conn.close()


# ─── numpy-Weg vs. Python-Rueckfall: identisches Ergebnis (Auftrag 87) ──────
# Vor der Vektorisierung gab es nur den Python-Weg -- dieser Test kann also
# erst gruen sein, seit finde_kandidaten zwei Wege hat, die verglichen
# werden. Ohne die numpy-Implementierung schlaegt er fehl, weil kab._np
# dann bereits None ist und beide Aufrufe denselben (einzigen) Weg nehmen --
# das waere kein Beleg fuer Uebereinstimmung zweier unabhaengiger Wege.

def _zufallsvektoren(n: int, dim: int, seed: int) -> list[list[float]]:
    import random

    rng = random.Random(seed)
    return [[rng.uniform(-1.0, 1.0) for _ in range(dim)] for _ in range(n)]


def test_finde_kandidaten_numpy_und_python_liefern_gleiches_ergebnis():
    assert kab._np is not None, "numpy ist laut Auftrag 87 installiert -- Test setzt das voraus"

    paths = [f"/n{i}" for i in range(40)]
    titles = paths[:]
    vektoren = _zufallsvektoren(40, 16, seed=42)
    # ein paar Vektoren nahe beieinander erzwingen, damit ueberhaupt Kanten
    # ueber der Schwelle entstehen (rein zufaellige Vektoren streuen sonst
    # zu breit fuer schwelle=0.5)
    vektoren[3] = list(vektoren[1])
    vektoren[3][0] += 0.001
    vektoren[10] = [x * 0.999 for x in vektoren[7]]

    paare_numpy = kab._paare_numpy(vektoren, 0.5, 5)
    paare_python = kab._paare_python(vektoren, 0.5, 5)

    assert set(paare_numpy.keys()) == set(paare_python.keys())
    for key in paare_numpy:
        sim_np, i_np, j_np = paare_numpy[key]
        sim_py, i_py, j_py = paare_python[key]
        assert {i_np, j_np} == {i_py, j_py}
        assert sim_np == pytest.approx(sim_py, abs=1e-9)

    kandidaten_numpy = kab.finde_kandidaten(paths, titles, vektoren, schwelle=0.5, k=5)
    kab._np, gesicherter_np = None, kab._np
    try:
        kandidaten_python = kab.finde_kandidaten(paths, titles, vektoren, schwelle=0.5, k=5)
    finally:
        kab._np = gesicherter_np

    assert len(kandidaten_numpy) == len(kandidaten_python)
    for a, b in zip(kandidaten_numpy, kandidaten_python):
        assert a.a_path == b.a_path
        assert a.b_path == b.b_path
        assert a.similarity == pytest.approx(b.similarity, abs=1e-9)


# ─── Negativfall: numpy kuenstlich unauffindbar -- Rueckfall liefert dasselbe ─

def test_ohne_numpy_liefert_rueckfall_dasselbe_ergebnis(monkeypatch):
    paths = ["/a", "/b", "/c", "/d"]
    titles = paths[:]
    vektoren = [[1.0, 0.0], [0.99, 0.14107], [0.0, 1.0], [-1.0, 0.0]]

    mit_numpy = kab.finde_kandidaten(paths, titles, vektoren, schwelle=0.5, k=5)
    monkeypatch.setattr(kab, "_np", None)
    ohne_numpy = kab.finde_kandidaten(paths, titles, vektoren, schwelle=0.5, k=5)

    assert len(mit_numpy) == len(ohne_numpy) > 0
    for a, b in zip(mit_numpy, ohne_numpy):
        assert (a.a_path, a.b_path) == (b.a_path, b.b_path)
        assert a.similarity == pytest.approx(b.similarity, abs=1e-9)


# ─── Grenzwert: null, ein, zwei Knoten (Auftrag 87) ─────────────────────────

def test_grenzwert_null_ein_zwei_knoten():
    assert kab.finde_kandidaten([], [], [], schwelle=0.5, k=5) == []
    assert kab.finde_kandidaten(["/a"], ["A"], [[1.0, 0.0]], schwelle=0.5, k=5) == []

    zwei_paths, zwei_titles = ["/a", "/b"], ["A", "B"]
    zwei_vektoren = [[1.0, 0.0], [1.0, 0.0]]
    zwei = kab.finde_kandidaten(zwei_paths, zwei_titles, zwei_vektoren, schwelle=0.5, k=5)
    assert len(zwei) == 1
    assert zwei[0].similarity == pytest.approx(1.0)

    # dieselben Grenzwerte auch explizit ohne numpy
    import kanten_aus_bedeutung as kab_mod

    orig = kab_mod._np
    kab_mod._np = None
    try:
        assert kab.finde_kandidaten([], [], [], schwelle=0.5, k=5) == []
        assert kab.finde_kandidaten(["/a"], ["A"], [[1.0, 0.0]], schwelle=0.5, k=5) == []
        zwei_ohne_np = kab.finde_kandidaten(zwei_paths, zwei_titles, zwei_vektoren, schwelle=0.5, k=5)
        assert len(zwei_ohne_np) == 1
        assert zwei_ohne_np[0].similarity == pytest.approx(1.0)
    finally:
        kab_mod._np = orig


def test_negativfall_echte_verschiedene_knoten_mit_hoher_aehnlichkeit_bleiben_paar(temp_db):
    """Der wichtige Gegenfall (Abnahme 2): ZWEI ECHT VERSCHIEDENE Knoten mit
    sehr hoher Aehnlichkeit (0.995, deutlich > 0.99) muessen weiterhin als
    Kandidatenpaar erscheinen. Eine Loesung, die pauschal alles ueber einer
    Schwelle wegwirft, wuerde dieses Paar mit dem Dedup-Fix verwechseln --
    hier sind es zwei verschiedene ref_id/project_id-Kombinationen, kein
    liegengebliebenes Duplikat desselben Knotens."""
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    _knoten_mit_vektor(conn, "/aehnlich-a", "Aehnlich A", [1.0, 0.0])
    _knoten_mit_vektor(conn, "/aehnlich-b", "Aehnlich B", [0.995, 0.0998])  # cos ~= 0.995
    conn.commit()

    paths, titles, vektoren = kab.lade_knoten_vektoren(conn)
    assert len(paths) == 2
    kandidaten = kab.finde_kandidaten(paths, titles, vektoren, schwelle=0.99, k=5)
    assert len(kandidaten) == 1
    assert {kandidaten[0].a_path, kandidaten[0].b_path} == {"/aehnlich-a", "/aehnlich-b"}
    conn.close()
