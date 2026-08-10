"""Rot-vor-gruen-Test fuer den gemessenen Suchausfall in knowledge_search():

  1. Mehrere Woerter liefen als implizites UND in FTS5 MATCH -- ein einziges
     Wort, das nirgends vorkommt, killte die ganze Anfrage.
  2. Keine deutsche Umlaut-Faltung: "Existenzgruender" (ue-Schreibung) fand
     "Existenzgründer" (ü) nicht, weil FTS5s remove_diacritics nur ü->u macht,
     nicht ue->u.

Laeuft gegen eine Kopie der ECHTEN knowledge.db (derselbe Bestand, den auch
die Agenten im Betrieb sehen) -- nicht gegen synthetische Fixtures, weil der
Fehler an genau diesem Bestand gemessen wurde (siehe Auftrag: Tabelle mit
sechs Anfragen, vier davon 0 Treffer trotz vorhandenem Knoten).
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

import shutil
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


@pytest.fixture()
def real_db_copy(tmp_path, monkeypatch):
    """Kopie der echten DB -- Schreibzugriffe der Tests treffen nie das Original."""
    src = SHARED_KNOWLEDGE / "knowledge.db"
    dst = tmp_path / "knowledge_real_copy.db"
    shutil.copy2(src, dst)
    monkeypatch.setattr(kms, "DB_PATH", dst)
    # Embeddings ausser Betrieb setzen -- dieser Test prueft reines Stichwort-
    # matching (FTS5/Faltung), nicht die Bedeutungssuche.
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: None)
    return dst


# --- Die sechs gemessenen Anfragen aus dem Auftrag -------------------------
# (erwartet: mind. 1 Treffer je Anfrage; vor dem Fix waren vier davon 0.)

_EXPECT_NONZERO = [
    "Spotlight",
    "Sparsebundle Spotlight verschluesselt",
    "Existenzgründer",
    "Existenzgruender",
    "amtliche Beschreibungen Ablauf Luecken",
    "Landesbroschuere Steuertipps Existenzgruender Bayern Hessen Sachsen",
]


@pytest.mark.parametrize("query", _EXPECT_NONZERO)
def test_measured_queries_find_at_least_one_hit(real_db_copy, query):
    result = kms.knowledge_search(query)
    assert result["count"] >= 1, f"Anfrage {query!r} fand nichts (Auftrags-Messung)"


def test_umlaut_query_and_native_spelling_find_the_same_node(real_db_copy):
    """'Existenzgruender' (ue) und 'Existenzgründer' (ü) muessen denselben
    Knoten finden -- Faltung ist beidseitig, nicht nur eine Richtung."""
    via_ue = kms.knowledge_search("Existenzgruender")
    via_ue_umlaut = kms.knowledge_search("Existenzgründer")
    ids_ue = {r["id"] for r in via_ue["results"]}
    ids_umlaut = {r["id"] for r in via_ue_umlaut["results"]}
    assert ids_ue & ids_umlaut, "beide Schreibweisen sollten denselben Knoten treffen"


# --- Negativfall: Woerter, die nirgends vorkommen, treffen weiterhin nichts

def test_nonsense_query_still_finds_nothing(real_db_copy):
    result = kms.knowledge_search("qxzvwkpfjhtklonpqrstuvw zzxxccvvbbnnmm")
    assert result["count"] == 0


# --- ODER-Rangfolge: mehr uebereinstimmende Woerter stehen oben ------------

def test_more_matching_words_rank_higher(real_db_copy):
    """Synthetische Zusatzknoten, damit die Rangfolge kontrolliert pruefbar
    ist: n_alle enthaelt alle drei Suchworte, n_eins nur eines."""
    conn = kms.get_db()
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
        "VALUES ('rank_all', '/test/rank-all', 'shared', "
        "'Kraftfahrzeugsteuer Erstattung Widerspruch', "
        "'Kraftfahrzeugsteuer Erstattung Widerspruch komplett', NULL, 0, 'test', 'keine_norm', 'skript:test', 'Testvorrichtung')"
    )
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
        "VALUES ('rank_one', '/test/rank-one', 'shared', "
        "'Nur Widerspruch', 'Nur das Wort Widerspruch alleine', NULL, 0, 'test', 'keine_norm', 'skript:test', 'Testvorrichtung')"
    )
    conn.commit()
    conn.close()

    result = kms.knowledge_search("Kraftfahrzeugsteuer Erstattung Widerspruch")
    ids = [r["id"] for r in result["results"]]
    assert "rank_all" in ids and "rank_one" in ids
    assert ids.index("rank_all") < ids.index("rank_one"), (
        "Knoten mit mehr uebereinstimmenden Woertern sollte weiter oben stehen"
    )


# --- Fehler nicht verschluckt: leerer Query bleibt ein sauberes 0-Treffer --

def test_empty_query_returns_zero_not_error(real_db_copy):
    result = kms.knowledge_search("   ")
    assert result["count"] == 0
    assert result["results"] == []


# --- Gleichheit Python fold_de() <-> SQL-Faltung in schema.sql -------------
# Zwei Implementierungen (SQL-Trigger koennen keine Python-Funktion aufrufen,
# ohne sie auf jeder schreibenden Verbindung zu registrieren -- siehe
# Kommentar an fold_de()). Diese Gleichheit ist die Klammer, die beide
# zusammenhaelt: Index (SQL) und Anfrage (Python) muessen denselben Text
# erzeugen, sonst verfehlen sich beide Seiten wieder.

_SQL_FOLD_EXPR = (
    "LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(?,"
    "'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss'))"
)

_FOLD_SAMPLES = [
    "Gründer", "Gruender", "GRÜNDER", "Straße", "Strasse", "STRASSE",
    "Größe", "Groesse", "für", "fuer", "Existenzgründer-Broschüren",
    "", "ohne Umlaute", "ÄÖÜäöüß", "Bayern Hessen Sachsen",
]


@pytest.mark.parametrize("text", _FOLD_SAMPLES)
def test_fold_de_matches_sql_fold(text):
    conn = __import__("sqlite3").connect(":memory:")
    sql_result = conn.execute(f"SELECT {_SQL_FOLD_EXPR}", (text,)).fetchone()[0]
    conn.close()
    assert kms.fold_de(text) == sql_result
