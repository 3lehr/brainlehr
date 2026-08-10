"""Rot-vor-gruen: lesson_query()s eigener Stichwort-Suchpfad (Python-Substring
in description/root_cause/prevention) hatte dieselbe Faltungsluecke wie
knowledge_search() vor dem Fix -- nur nie behoben, weil er ueber einen
komplett anderen Code-Pfad laeuft (kein FTS5, direktes `k in text`).

Nachtrag zum urspruenglichen Auftrag (2026-08-01): 374 der 153+374 Eintraege
im Wissensspeicher sind Lehren, nicht Knoten -- der groessere Teil des
Bestands stand also weiter hinter derselben Wand.

Laeuft gegen eine Kopie der echten knowledge.db, wie test_knowledge_search_fold.py.
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
import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


@pytest.fixture()
def real_db_copy(tmp_path, monkeypatch):
    src = SHARED_KNOWLEDGE / "knowledge.db"
    dst = tmp_path / "knowledge_real_copy.db"
    shutil.copy2(src, dst)
    monkeypatch.setattr(kms, "DB_PATH", dst)
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: None)
    return dst


# L-021f62 enthaelt woertlich "Plausibilitäts" (ü) -- nirgends "Plausibilitaets"
# (ue-Schreibung). Isolierte Anfrage: EIN Wort, ausschliesslich ueber Faltung
# erreichbar, kein zufaelliger Zweittreffer ueber ein anderes Wort im Text
# moeglich (siehe Kopflauf: mit "guards"/"kalibriert" im Query waeren beide
# schon vorher literal getroffen worden -- das haette nichts bewiesen).

def test_umlaut_substitute_spelling_finds_lesson_by_meaning_word(real_db_copy):
    result = kms.lesson_query(query="Plausibilitaets", max_results=20)
    ids = {r["id"] for r in result["results"]}
    assert "L-021f62" in ids, "Faltung wirkt nicht im Lesson-Suchpfad"


def test_native_umlaut_and_substitute_spelling_agree(real_db_copy):
    via_ue = kms.lesson_query(query="Zaehlern", max_results=20)
    via_umlaut = kms.lesson_query(query="Zählern", max_results=20)
    ids_ue = {r["id"] for r in via_ue["results"]}
    ids_umlaut = {r["id"] for r in via_umlaut["results"]}
    assert "L-021f62" in ids_ue
    assert "L-021f62" in ids_umlaut


# --- Negativfall: Anfrage, die nichts treffen darf, trifft weiterhin nichts

def test_nonsense_query_finds_no_lesson(real_db_copy):
    result = kms.lesson_query(query="qxzvwkpfjhtklonpqrstuvw zzxxccvvbbnnmm", max_results=20)
    assert result["count"] == 0
