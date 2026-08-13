"""Tests fuer Auftrag 89: Kanalwahl an die Anfragelaenge binden.

Befund, der den Auftrag ausgeloest hat (2026-08-13, eigene Trigramm-Probe):
knowledge_fts/lessons_fts nutzen tokenize='trigram' (schema.sql) -- ein
Trigramm braucht mindestens drei Zeichen. Woerter unter drei Zeichen
erzeugen keins und koennen darum NIE ueber den Stichwortkanal treffen
('ベース' 3 Zeichen -> 2 Treffer, '知識'/'検索'/'日本' je 2 Zeichen -> 0). Im
Japanischen/Chinesischen ist die zweistellige Verbindung die HAEUFIGSTE Form
eines Substantivs -- der Kanal ist dort blind fuer den Normalfall.

Zwei getrennte Befunde, zwei getrennte Belege:
  A) _QUERY_WORD_RE (Wortauszug fuer die FTS-Anfrage) erkannte japanische/
     chinesische Zeichen VORHER GAR NICHT als Wort -- eine reine CJK-Anfrage
     ergab dadurch fts_query == "" und knowledge_search() brach VOR jedem
     Kanal (auch dem Bedeutungskanal) mit count=0 ab. Schwerer als im
     Auftrag beschrieben ("verwaessert trotzdem"): es lieferte ueberhaupt
     nichts, auch keine Verwaesserung. Siehe test_cjk_wort_wird_erkannt.
  B) Auch mit erkanntem Wort war der Stichwortkanal fuer eine Anfrage aus
     lauter Woertern unter drei Zeichen weiterhin per Konstruktion blind --
     jetzt wird die FTS-Abfrage fuer diesen Fall gar nicht mehr gestellt und
     beansprucht dadurch nachweislich kein Ranggewicht in der RRF-Fusion.
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
import struct
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Frische Test-DB mit dem echten Schema, DB_PATH umgebogen -- gleicher
    Aufbau wie tests/test_knowledge_hybrid_search.py::temp_db."""
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.executemany(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, norm_entscheidung, "
        "norm_entschieden_von, norm_entschieden_grund) "
        "VALUES (?, ?, 'shared', ?, ?, NULL, 0, 'test', 'keine_norm', 'skript:test', 'Testvorrichtung')",
        [
            ("n1", "/steuer/aveuer-regel", "AVEUER Sonderabschreibung",
             "Regel zur Abschreibung von Anlagegütern im ersten Jahr"),
            ("n2", "/sprache/jp-wissen", "知識 und 検索 in Japan",
             "Ein Knoten ueber 知識 (Wissen) und 検索 (Suche) in 日本"),
            ("n3", "/sprache/jp-datenbank", "Japanische Datenbank-Notiz",
             "Noch ein Knoten mit 知識 als Thema, andere Formulierung"),
        ],
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _fake_vec(*floats: float) -> bytes:
    return struct.pack(f"<{len(floats)}f", *floats)


def _insert_embedding(db_path: Path, ref_id: str, vector: tuple[float, ...]):
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT OR REPLACE INTO knowledge_embeddings (kind, ref_id, model, dim, vector, updated_at) "
        "VALUES ('node', ?, ?, ?, ?, '2026-08-13T00:00:00+02:00')",
        (ref_id, kms.embeddings.DEFAULT_EMBED_MODEL, len(vector), _fake_vec(*vector)),
    )
    conn.commit()
    conn.close()


# --- Grenzwert: 2/3 Zeichen, gemischt --------------------------------------

def test_zwei_zeichen_ist_blind():
    assert kms._stichwortkanal_blind("ab") is True


def test_drei_zeichen_ist_nicht_blind():
    assert kms._stichwortkanal_blind("abc") is False


def test_alle_woerter_unter_drei_zeichen_ist_blind():
    assert kms._stichwortkanal_blind("ab cd") is True


def test_gemischt_ein_kurzes_ein_langes_wort_ist_nicht_blind():
    # Negativfall aus dem Auftrag: MINDESTENS EIN Begriff ab drei Zeichen
    # genuegt, um den Kanal nicht als blind zu behandeln.
    assert kms._stichwortkanal_blind("ab database") is False


def test_leere_anfrage_ist_nicht_blind():
    # Kein Wort ueberhaupt -> _or_query() faengt das schon vorher ab
    # (fts_query == "", frueher Return); _stichwortkanal_blind soll hier
    # nicht faelschlich True liefern (bool(words) guard).
    assert kms._stichwortkanal_blind("   ") is False


# --- Befund A: CJK-Wort wurde vorher gar nicht als Wort erkannt -----------

def test_cjk_wort_wird_erkannt():
    """VOR diesem Auftrag: _QUERY_WORD_RE = [A-Za-zÄÖÜäöüß0-9]+ matcht keine
    japanischen/chinesischen Zeichen -- findall("知識") == []. Damit wurde
    _or_query("知識") zu "", und knowledge_search() gab schon an der
    fts_query-Leerpruefung {"results": [], "count": 0} zurueck, OHNE je den
    Bedeutungskanal zu befragen. Das ist die vom Auftrag verlangte
    Vor-Zustands-Zahl in schaerferer Form: nicht 'verwaessert', sondern
    strukturell 0 in jedem Fall, auch mit passendem Vektor."""
    woerter = kms._QUERY_WORD_RE.findall("知識")
    assert woerter == ["知識"], "CJK-Zeichen muessen als Wort erkannt werden"
    assert kms._or_query("知識") != ""


def test_stichwortkanal_blind_erkennt_cjk_kurzwort():
    assert kms._stichwortkanal_blind("知識") is True
    assert kms._stichwortkanal_blind("ベース") is False  # 3 Zeichen, siehe Docstring


# --- Befund B: blinder Kanal beansprucht kein Ranggewicht mehr -------------

def test_rein_kurze_anfrage_stellt_keine_fts_anfrage(temp_db, monkeypatch):
    """Direkter Beleg, eine Zahl: fuer eine Anfrage aus lauter Woertern unter
    drei Zeichen wird conn.execute() mit 'MATCH' ueberhaupt nicht mehr
    aufgerufen -- vorher lief die FTS-Abfrage immer (und lieferte, weil der
    Trigramm-Tokenizer bei <3 Zeichen strukturell nichts findet, ohnehin 0
    Zeilen zurueck, aber eben nach einer echten Abfrage, nicht durch eine
    Weiche davor)."""
    calls = {"match": 0}
    orig_get_db = kms.get_db

    def traced_get_db(*a, **k):
        conn = orig_get_db(*a, **k)
        conn.set_trace_callback(
            lambda sql: calls.__setitem__("match", calls["match"] + 1) if "MATCH" in sql else None
        )
        return conn

    monkeypatch.setattr(kms, "get_db", traced_get_db)
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: None)

    result = kms.knowledge_search("ab")
    assert calls["match"] == 0, "blinder Stichwortkanal hat trotzdem eine MATCH-Abfrage gestellt"
    assert result["count"] == 0  # kein Vektor in diesem Lauf -> auch der Bedeutungskanal liefert nichts


def test_kurze_anfrage_liefert_nur_ueber_bedeutungskanal(temp_db, monkeypatch):
    """n2 traegt keinen woertlichen Treffer fuer die Anfrage 'ab' (Trigramm
    kann 2 Zeichen strukturell nicht matchen), bekommt aber einen zum
    Query-Vektor identischen Vektor -- muss trotzdem gefunden werden, weil
    ausschliesslich der Bedeutungskanal entscheidet."""
    _insert_embedding(temp_db, "n2", (1.0, 0.0, 0.0))
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0, 0.0])

    result = kms.knowledge_search("ab")
    result_ids = [r["id"] for r in result["results"]]
    assert result_ids == ["n2"]


def test_negativfall_anfrage_mit_langem_wort_unveraendert(temp_db, monkeypatch):
    """Negativfall aus der Abnahme: eine Anfrage mit mindestens einem Begriff
    ab drei Zeichen verhaelt sich unveraendert -- gemessen, nicht angenommen:
    dieselbe Trefferliste in derselben Reihenfolge wie eine reine
    Stichwortsuche ohne Vektoren (identisches Muster wie
    tests/test_knowledge_hybrid_search.py::test_knowledge_search_without_vectors_matches_plain_fts_order)."""
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: None)

    hybrid = kms.knowledge_search("Abschreibung")

    conn = kms.get_db()
    plain_rows = conn.execute(
        """SELECT n.id FROM knowledge_fts f JOIN knowledge_nodes n ON f.rowid = n.rowid
           WHERE knowledge_fts MATCH ? ORDER BY rank""",
        ("Abschreibung",),
    ).fetchall()
    conn.close()
    plain_ids = [r["id"] for r in plain_rows][:10]

    assert [r["id"] for r in hybrid["results"]] == plain_ids
    assert plain_ids == ["n1"]


# --- Japanischer Probefall (Abnahme Punkt 4) --------------------------------

def test_japanischer_probefall_zwei_knoten(temp_db, monkeypatch):
    """Zwei Knoten mit japanischem Text (n2, n3), zweistellige Anfrage '知識'.
    Vorher (Befund A): fts_query=="" -> sofortiger Abbruch, count=0, auch mit
    Vektor. Jetzt: der Stichwortkanal wird gar nicht befragt (Befund B,
    belegt per direkter MATCH-Pruefung unten), der Bedeutungskanal liefert
    den semantisch naeheren Knoten."""
    conn = sqlite3.connect(str(temp_db))
    fts_treffer = conn.execute(
        "SELECT n.id FROM knowledge_fts f JOIN knowledge_nodes n ON f.rowid = n.rowid "
        "WHERE knowledge_fts MATCH ?", ('"知識"',)
    ).fetchall()
    conn.close()
    assert fts_treffer == [], "Trigramm-Tokenizer sollte bei 2 Zeichen strukturell 0 Treffer liefern"

    _insert_embedding(temp_db, "n2", (1.0, 0.0, 0.0))
    _insert_embedding(temp_db, "n3", (0.0, 1.0, 0.0))
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0, 0.0])

    result = kms.knowledge_search("知識")
    assert result["count"] > 0, "Bedeutungskanal haette trotz blindem Stichwortkanal liefern muessen"
    result_ids = [r["id"] for r in result["results"]]
    assert result_ids[0] == "n2"  # naeher am Query-Vektor
