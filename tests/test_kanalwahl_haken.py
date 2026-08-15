"""Regressionstest fuer Auftrag 89 (Kanalwahl an die Anfragelaenge binden)
am haken/-Retrieval-Pfad (haken/suchpfad_abruf.kandidaten, der Pfad, den
haken/knowledge_recall_hook.py bei _suchpfad_aktiv()==True -- der Vorgabe
seit 2026-08-09 -- tatsaechlich benutzt).

MESSBEFUND, nicht Vermutung (2026-08-15): dieser Pfad hatte den Fehler nie,
den knowledge_search() vor a31f6f7 hatte. Er ist reine RRF-Fusion ohne
Stichwort-Sockel (_fuse_with_keyword_floor wird hier NICHT verwendet, s.
Moduldoc); ein Stichwortkanal, der leer bleibt, traegt zu
embeddings.rrf_fuse() nachweislich nichts bei, der Bedeutungskanal
entscheidet dann allein -- gemessen an echten Bestandsdaten (2210 Knoten):
'KI' (2 Zeichen) und '知識' (2 Zeichen) je 0 FTS-Treffer, aber beide Ziel-
knoten ueber den Bedeutungskanal unter den ersten drei Kandidaten. Kein
Rot-vor-gruen-Fall herstellbar: nichts an DIESEM Pfad war je blind fuer
kurze/CJK-Anfragen.

Trotzdem ergaenzt: _stichwortkanal_blind() (import aus knowledge_mcp_server,
selbst Teil von Auftrag 89) spart am blinden Fall zwei SQL-Anfragen, deren
Ergebnis ohnehin leer ist -- Parity/Performance, kein Korrekturmechanismus.
Dieser Test haelt genau das fest: (a) die Einsparung wirkt, (b) sie darf NIE
den Bedeutungskanal mit abwuergen (das waere ein neuer, schwererer Fehler
als der, den sie vermeiden soll), (c) ein Wort ab drei Zeichen laesst den
Stichwortkanal unveraendert mitentscheiden (Gegenprobe: Mehrheit bleibt
unveraendert)."""
from __future__ import annotations

import sqlite3
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "kern"))
sys.path.insert(0, str(ROOT / "haken"))

import knowledge_mcp_server as kms  # noqa: E402
import haken.suchpfad_abruf as sa  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path):
    """Frische Test-DB mit dem echten Schema -- gleicher Aufbau wie
    tests/test_stichwortkanal_kurze_anfragen.py::temp_db, hier ohne
    kms.DB_PATH-Monkeypatch, weil kandidaten() die Verbindung als Parameter
    nimmt statt sie selbst zu oeffnen."""
    db_path = tmp_path / "knowledge_test.db"
    schema = (ROOT / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.executemany(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, "
        "norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
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


def _open(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


# --- (a) Einsparung wirkt: keine MATCH-Abfrage bei blinder Anfrage --------

def test_blinde_anfrage_stellt_keine_fts_anfrage(temp_db):
    conn = _open(temp_db)
    calls = {"match": 0}
    conn.set_trace_callback(
        lambda sql: calls.__setitem__("match", calls["match"] + 1) if "MATCH" in sql else None
    )
    sa.kandidaten(conn, "ab", None, 5)
    conn.close()
    assert calls["match"] == 0, "blinder Stichwortkanal hat trotzdem eine MATCH-Abfrage gestellt"


# --- (b) Einsparung wuergt den Bedeutungskanal NICHT ab --------------------

def test_blinde_anfrage_liefert_trotzdem_ueber_bedeutungskanal(temp_db):
    _insert_embedding(temp_db, "n2", (1.0, 0.0, 0.0))
    conn = _open(temp_db)
    nodes, _ = sa.kandidaten(conn, "ab", [1.0, 0.0, 0.0], 5)
    conn.close()
    assert [n["id"] for n in nodes] == ["n2"], (
        "Bedeutungskanal haette trotz blindem Stichwortkanal liefern muessen -- "
        "genau der Fehler, den die Parity-Ergaenzung NICHT einfuehren darf")


def test_japanischer_probefall_zwei_knoten(temp_db):
    """Gleicher Fall wie tests/test_stichwortkanal_kurze_anfragen.py, hier
    gegen den tatsaechlich live genutzten haken/-Pfad."""
    conn = _open(temp_db)
    fts_treffer = conn.execute(
        "SELECT n.id FROM knowledge_fts f JOIN knowledge_nodes n ON f.rowid = n.rowid "
        "WHERE knowledge_fts MATCH ?", ('"知識"',)
    ).fetchall()
    assert fts_treffer == [], "Trigramm-Tokenizer sollte bei 2 Zeichen strukturell 0 Treffer liefern"
    conn.close()

    _insert_embedding(temp_db, "n2", (1.0, 0.0, 0.0))
    _insert_embedding(temp_db, "n3", (0.0, 1.0, 0.0))
    conn = _open(temp_db)
    nodes, _ = sa.kandidaten(conn, "知識", [1.0, 0.0, 0.0], 5)
    conn.close()
    assert nodes and nodes[0]["id"] == "n2"


# --- (c) Gegenprobe: Wort ab drei Zeichen bleibt unveraendert -------------

def test_langes_wort_nutzt_weiterhin_stichwortkanal(temp_db):
    conn = _open(temp_db)
    nodes, _ = sa.kandidaten(conn, "Abschreibung", None, 5)
    conn.close()
    assert [n["id"] for n in nodes] == ["n1"]


def test_gemischt_ein_kurzes_ein_langes_wort_bleibt_aktiv(temp_db):
    """Abnahme Grenzwert 'gemischt': ein einzelnes langes Wort neben einem
    kurzen darf den Stichwortkanal NICHT stilllegen (anders als
    knowledge_search()'s All-oder-Nichts-Gate, das erst bei JEDEM Wort < 3
    Zeichen greift -- hier ist der Effekt derselbe, weil OR-Terme einzeln
    matchen, aber die Abnahme verlangt die Probe explizit)."""
    conn = _open(temp_db)
    calls = {"match": 0}
    conn.set_trace_callback(
        lambda sql: calls.__setitem__("match", calls["match"] + 1) if "MATCH" in sql else None
    )
    nodes, _ = sa.kandidaten(conn, "ab Abschreibung", None, 5)
    conn.close()
    assert calls["match"] > 0, "gemischte Anfrage haette den Stichwortkanal befragen muessen"
    assert [n["id"] for n in nodes] == ["n1"]


# --- Grenzwerte ------------------------------------------------------------

def test_leere_anfrage_liefert_leer(temp_db):
    conn = _open(temp_db)
    nodes, lessons = sa.kandidaten(conn, "", None, 5)
    conn.close()
    assert nodes == [] and lessons == []


def test_ein_zeichen_ist_blind(temp_db):
    conn = _open(temp_db)
    calls = {"match": 0}
    conn.set_trace_callback(
        lambda sql: calls.__setitem__("match", calls["match"] + 1) if "MATCH" in sql else None
    )
    sa.kandidaten(conn, "a", None, 5)
    conn.close()
    assert calls["match"] == 0


def test_sehr_lange_anfrage_bleibt_unveraendert(temp_db):
    conn = _open(temp_db)
    lange_anfrage = "Abschreibung " * 200
    nodes, _ = sa.kandidaten(conn, lange_anfrage, None, 5)
    conn.close()
    assert [n["id"] for n in nodes] == ["n1"]
