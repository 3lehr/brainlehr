"""Tests fuer den rohen Kosinus-Wert je Trefferzeile in knowledge_search()
(Feld "bedeutungs_kosinus", Auftrag 2026-08-19).

Vorher gab knowledge_search nur die Position nach RRF-Fusion zurueck
(embeddings.rrf_fuse addiert 1/(k+Rang), der Rohwert des Bedeutungskanals
ging dabei verloren) -- ein Aufrufer konnte einen starken von einem
schwachen Treffer nicht unterscheiden. _embedding_ranking() konnte den
Kosinus schon vorher liefern (Parameter "werte"), er wurde in
knowledge_search() nur nicht bis in die Ergebniszeile durchgereicht.

Rot-vor-gruen-Beleg (Abnahme 1): test_rot_vor_dem_fix laedt den
Dateistand vor der Aenderung (fixer Commit _VORHER_COMMIT = 4c88915b~1,
git show -- nicht HEAD, das mit jedem weiteren Commit auf dem Zweig
wandert), zu dem "bedeutungs_kosinus" in keiner Trefferzeile vorkam,
und zeigt den KeyError. Derselbe Test bestaetigt danach den GRUENEN
Stand am Arbeitsverzeichnis.

Fixtures/Helfer (temp_db, _insert_embedding) aus test_knowledge_hybrid_search.py
wiederverwendet statt verdoppelt -- gleiche DB-Bauform, gleiches Muster.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402

from test_knowledge_hybrid_search import temp_db, _insert_embedding  # noqa: E402,F401


# --- 2. Gegenprobe in beide Richtungen: MIT Vektor eine Zahl, OHNE Vektor None -

def test_treffer_mit_vektor_traegt_kosinuszahl(temp_db, monkeypatch):
    _insert_embedding(temp_db, "node", "n1", (1.0, 0.0, 0.0))
    _insert_embedding(temp_db, "node", "n3", (0.95, 0.05, 0.0))
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0, 0.0])

    result = kms.knowledge_search("Abschreibung", max_results=2)
    by_id = {r["id"]: r for r in result["results"]}

    assert "n1" in by_id and "n3" in by_id
    for rid in ("n1", "n3"):
        wert = by_id[rid]["bedeutungs_kosinus"]
        assert wert is not None
        assert isinstance(wert, float)
        assert -1.0 <= wert <= 1.0
    # n1 ist exakt der Query-Vektor -> Kosinus 1.0; n3 ist nah, aber nicht exakt.
    assert by_id["n1"]["bedeutungs_kosinus"] == pytest.approx(1.0, abs=1e-6)
    assert by_id["n3"]["bedeutungs_kosinus"] < by_id["n1"]["bedeutungs_kosinus"]


def test_treffer_ohne_vektor_traegt_none_nicht_null(temp_db, monkeypatch):
    # Keine Embeddings eingefuegt -- n1 kommt nur ueber den Stichwortkanal.
    # 0.0 waere eine (falsche) Aussage ueber Aehnlichkeit; None sagt "kein Vektor da".
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0, 0.0])
    result = kms.knowledge_search("Abschreibung")
    assert result["count"] == 1
    assert result["results"][0]["id"] == "n1"
    assert result["results"][0]["bedeutungs_kosinus"] is None


def test_lesson_treffer_traegt_ebenfalls_das_feld(temp_db, monkeypatch):
    _insert_embedding(temp_db, "lesson", "L-aaa111", (1.0, 0.0))
    _insert_embedding(temp_db, "lesson", "L-bbb222", (0.0, 1.0))
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0])

    result = kms.lesson_query(query="virtuelle Umgebung fuer Testlaeufe verwenden", max_results=1)
    # lesson_query() ist eine andere Funktion als knowledge_search() -- hier nur
    # zur Kontrolle, dass sie unberuehrt bleibt (kein bedeutungs_kosinus-Feld
    # verlangt, Auftrag betrifft ausdruecklich nur knowledge_search).
    assert "L-aaa111" in [r["id"] for r in result["results"]]

    result2 = kms.knowledge_search("Testlaeufe virtuelle Umgebung", max_results=5)
    lesson_hits = {r["id"]: r for r in result2["results"] if r["kind"] == "lesson"}
    assert "L-aaa111" in lesson_hits
    assert lesson_hits["L-aaa111"]["bedeutungs_kosinus"] is not None
    assert isinstance(lesson_hits["L-aaa111"]["bedeutungs_kosinus"], float)


# --- 3. Negativfall: Reihenfolge vor/nach der Aenderung identisch -----------

# Fixer Commit statt HEAD: HEAD wandert mit jedem weiteren Commit auf diesem
# Zweig (z.B. der Leer-Commit in der Abnahme) und traegt danach die Aenderung,
# die belegt werden soll, bereits selbst -- der Vergleichsstand ist deshalb
# der Elter von 4c88915b (dem Commit, der "bedeutungs_kosinus" einfuehrte).
_VORHER_COMMIT = "4c88915b~1"


def _lade_head_fassung():
    """Laedt knowledge_mcp_server.py-Stand VOR der Kosinus-Aenderung (fixer
    Commit _VORHER_COMMIT, nicht HEAD) als eigenstaendiges Modul, damit
    derselbe Testlauf beide Fassungen gegen dieselbe temp_db ausfuehren kann
    -- ohne git checkout/stash (tabu laut Auftrag) am Arbeitsverzeichnis."""
    quelltext = subprocess.run(
        ["git", "show", f"{_VORHER_COMMIT}:knowledge_mcp_server.py"],
        cwd=str(SHARED_KNOWLEDGE), capture_output=True, text=True, check=True,
    ).stdout
    # Neben knowledge_mcp_server.py selbst ablegen (nicht in tests/): das Modul
    # sucht schema.sql relativ zu seinem eigenen __file__-Verzeichnis.
    tmp_datei = SHARED_KNOWLEDGE / "_kms_head_snapshot_tmp.py"
    tmp_datei.write_text(quelltext, encoding="utf-8")
    try:
        spec = importlib.util.spec_from_file_location("kms_head_snapshot", tmp_datei)
        modul = importlib.util.module_from_spec(spec)
        sys.modules["kms_head_snapshot"] = modul
        spec.loader.exec_module(modul)
    finally:
        tmp_datei.unlink()
    return modul


def test_reihenfolge_identisch_zu_head_ohne_das_feld(temp_db, monkeypatch):
    _insert_embedding(temp_db, "node", "n1", (-1.0, 0.0, 0.0))
    _insert_embedding(temp_db, "node", "n2", (1.0, 0.0, 0.0))
    _insert_embedding(temp_db, "node", "n3", (0.9, 0.1, 0.0))
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0, 0.0])

    aktuell = kms.knowledge_search("Abschreibung", max_results=2)
    aktuelle_ids = [r["id"] for r in aktuell["results"]]

    kms_head = _lade_head_fassung()
    monkeypatch.setattr(kms_head, "DB_PATH", kms.DB_PATH)
    monkeypatch.setattr(kms_head.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0, 0.0])
    vorher = kms_head.knowledge_search("Abschreibung", max_results=2)
    vorherige_ids = [r["id"] for r in vorher["results"]]

    assert aktuelle_ids == vorherige_ids, "die Reihenfolge der Treffer hat sich durch das neue Feld veraendert"
    assert "bedeutungs_kosinus" not in vorher["results"][0], "Vorher-Fassung sollte das Feld noch nicht kennen"
    assert "bedeutungs_kosinus" in aktuell["results"][0]


def test_rot_vor_dem_fix(temp_db, monkeypatch):
    """Belegt Abnahmepunkt 1: gegen den fixen Vorher-Stand (_VORHER_COMMIT,
    vor diesem Auftrag) schlaegt genau diese Zusicherung fehl -- das Feld
    fehlte dort."""
    _insert_embedding(temp_db, "node", "n1", (1.0, 0.0, 0.0))
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0, 0.0])

    kms_head = _lade_head_fassung()
    monkeypatch.setattr(kms_head, "DB_PATH", kms.DB_PATH)
    monkeypatch.setattr(kms_head.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0, 0.0])
    vorher = kms_head.knowledge_search("Abschreibung")
    with pytest.raises(KeyError):
        _ = vorher["results"][0]["bedeutungs_kosinus"]  # rot: Feld existierte im Vorher-Stand nicht

    jetzt = kms.knowledge_search("Abschreibung")
    assert jetzt["results"][0]["bedeutungs_kosinus"] == pytest.approx(1.0, abs=1e-6)  # gruen: jetzt vorhanden


# --- 4. Grenzwert: max_results=1 und eine Anfrage ohne Treffer werfen nicht -

def test_max_results_eins_wirft_nicht(temp_db, monkeypatch):
    _insert_embedding(temp_db, "node", "n1", (1.0, 0.0, 0.0))
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0, 0.0])
    result = kms.knowledge_search("Abschreibung", max_results=1)
    assert result["count"] == 1
    assert result["results"][0]["bedeutungs_kosinus"] is not None


def test_anfrage_ohne_treffer_wirft_nicht(temp_db, monkeypatch):
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda *a, **k: [1.0, 0.0, 0.0])
    result = kms.knowledge_search("voellig-unbekannter-begriff-xyzzy")
    assert result["count"] == 0
    assert result["results"] == []
