"""Tests fuer erklaerte Kettenbrueche (Auftrag 2026-08-06, Anschluss an
tests/test_auditkette.py). Rot-vor-gruen-Beleg fuer knowledge_lint.py::
find_broken_chain() mit kettenerklaerung.py -- eine Umschreibung wird
simuliert, vorher zeigt der Lint einen unerklaerten Bruch, nachher denselben
Bruch als erklaert. NIE gegen die echte brainlehr.db -- immer frische
Temp-DB aus schema.sql.
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
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402
import knowledge_lint as lint  # type: ignore  # noqa: E402
import kettenerklaerung as ke  # type: ignore  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _lint(db_path: Path) -> dict:
    conn = lint.get_ro_conn(db_path)
    try:
        return lint.find_broken_chain(conn)
    finally:
        conn.close()


def _log3(n: int = 3) -> None:
    conn = kms.get_db()
    for i in range(n):
        kms.log_access(conn, f"/x/{i}", "read", query=f"q{i}")
    conn.close()


def test_rewrite_then_explanation_flips_unexplained_to_explained(temp_db):
    """Rot-vor-gruen: eine befugte Umschreibung (Feld geaendert, ketten_hash
    absichtlich NICHT nachgerechnet -- so verhaelt sich eine Migration, die
    den Bruch stehen laesst statt ihn zu verstecken) macht die Kette zuerst
    unerklaert kaputt. Danach create_explanation() -- derselbe Bruch gilt als
    erklaert, die Pruefung stoppt nicht mehr dort."""
    _log3(3)
    ids = [r[0] for r in sqlite3.connect(str(temp_db)).execute(
        "SELECT id FROM access_log ORDER BY id")]
    umgeschrieben_id = ids[0]

    conn = sqlite3.connect(str(temp_db))
    conn.execute("UPDATE access_log SET query = 'umgeschrieben' WHERE id = ?", (umgeschrieben_id,))
    conn.commit()
    conn.close()

    # VORHER: unerklaerter Bruch, Pruefung stoppt dort.
    vorher = _lint(temp_db)
    assert vorher["heil"] is False
    assert vorher["erster_bruch"]["id"] == umgeschrieben_id
    assert vorher["erklaerte_brueche"] == []

    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    ke.create_explanation(
        conn, umgeschrieben_id, "Zeitzonen-Rueckrechnung, Testfall",
        commit_hash="deadbeef",
    )
    conn.close()

    # NACHHER: derselbe Bruch ist jetzt erklaert, Pruefung laeuft ueber ihn
    # hinweg und bis zum Ende (3 Zeilen).
    nachher = _lint(temp_db)
    assert nachher["heil"] is True
    assert nachher["erster_bruch"] is None
    assert nachher["geprueft_zeilen"] == 3
    assert len(nachher["erklaerte_brueche"]) == 1
    assert nachher["erklaerte_brueche"][0]["id"] == umgeschrieben_id
    assert nachher["erklaerte_brueche"][0]["grund"] == "Zeitzonen-Rueckrechnung, Testfall"


def test_break_without_explanation_stays_unexplained(temp_db):
    """Negativfall Teil 1: ein Bruch ohne jede Erklaerungszeile bleibt
    unerklaert und wird wie vorher gemeldet -- keine stille Kulanz."""
    _log3(2)
    ids = [r[0] for r in sqlite3.connect(str(temp_db)).execute(
        "SELECT id FROM access_log ORDER BY id")]
    conn = sqlite3.connect(str(temp_db))
    conn.execute("UPDATE access_log SET query = 'ohne erklaerung' WHERE id = ?", (ids[0],))
    conn.commit()
    conn.close()

    result = _lint(temp_db)
    assert result["heil"] is False
    assert result["erster_bruch"]["id"] == ids[0]
    assert result["erklaerte_brueche"] == []


def test_explanation_with_wrong_vorher_hash_is_not_accepted(temp_db):
    """Negativfall Teil 2: eine Erklaerungszeile, deren vorher_hash NICHT
    zum tatsaechlichen gespeicherten Zustand passt, deckt den Bruch nicht --
    weder bei der Anlage noch beim Lint."""
    _log3(2)
    ids = [r[0] for r in sqlite3.connect(str(temp_db)).execute(
        "SELECT id FROM access_log ORDER BY id")]
    bruch_id = ids[0]

    conn = sqlite3.connect(str(temp_db))
    conn.execute("UPDATE access_log SET query = 'manipuliert' WHERE id = ?", (bruch_id,))
    conn.commit()
    conn.close()

    # Anlage mit erfundenem vorher_hash direkt per SQL (am kettenerklaerung.py-
    # Weg vorbei, der den echten Zustand erzwingt) -- simuliert eine
    # nachtraeglich verfaelschte Erklaerung.
    conn = sqlite3.connect(str(temp_db))
    conn.execute(
        "INSERT INTO chain_explanations "
        "(access_log_id, grund, vorher_hash, nachher_hash, erstellt_am) "
        "VALUES (?, 'vorgetaeuscht', ?, ?, '2026-08-06T00:00:00+02:00')",
        (bruch_id, "0" * 64, "1" * 64),
    )
    conn.commit()
    conn.close()

    result = _lint(temp_db)
    assert result["heil"] is False
    assert result["erster_bruch"]["id"] == bruch_id
    assert result["erklaerte_brueche"] == []

    # Und: create_explanation() selbst wuerde denselben erfundenen
    # vorher_hash nie erzeugen -- sie liest ihn aus dem tatsaechlichen
    # Zustand, kein Aufrufer kann ihn vorgeben.
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    echte = ke.create_explanation(conn, bruch_id, "echte Erklaerung")
    conn.close()
    assert echte["vorher_hash"] != "0" * 64

    result2 = _lint(temp_db)
    assert result2["heil"] is True
    assert len(result2["erklaerte_brueche"]) == 1


def test_two_writers_record_one_matching_explanation(temp_db):
    _log3(1)
    bruch_id = sqlite3.connect(str(temp_db)).execute("SELECT id FROM access_log").fetchone()[0]
    conn = sqlite3.connect(str(temp_db))
    conn.execute("UPDATE access_log SET query = 'concurrent rewrite' WHERE id = ?", (bruch_id,))
    conn.commit(); conn.close()
    barrier = threading.Barrier(2)

    def writer():
        local = sqlite3.connect(str(temp_db), timeout=2)
        local.row_factory = sqlite3.Row
        try:
            barrier.wait()
            return ke.create_explanation(local, bruch_id, "same proven rewrite", commit_hash="deadbeef")
        finally:
            local.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: writer(), range(2)))
    assert sorted(r["status"] for r in results) == ["already_recorded", "recorded"]
    count = sqlite3.connect(str(temp_db)).execute(
        "SELECT COUNT(*) FROM chain_explanations WHERE access_log_id = ?", (bruch_id,)
    ).fetchone()[0]
    assert count == 1


def test_explanation_skips_uncovered_legacy_rows_like_chain_lint(temp_db):
    """The single-row writer must use the same predecessor as the full lint.

    Otherwise an explanation after an unhashed legacy interval is stored with
    a different expected hash and never covers the lint's reported break.
    """
    _log3(3)
    ids = [r[0] for r in sqlite3.connect(str(temp_db)).execute(
        "SELECT id FROM access_log ORDER BY id")]
    conn = sqlite3.connect(str(temp_db))
    conn.execute("UPDATE access_log SET ketten_hash = NULL WHERE id = ?", (ids[1],))
    conn.execute("UPDATE access_log SET query = 'rewritten after legacy gap' WHERE id = ?", (ids[2],))
    conn.commit(); conn.close()

    conn = sqlite3.connect(str(temp_db)); conn.row_factory = sqlite3.Row
    result = ke.create_explanation(conn, ids[2], "proven rewrite after uncovered gap")
    conn.close()

    assert result["status"] == "recorded"
    lint_result = _lint(temp_db)
    assert lint_result["heil"] is True
    assert [item["id"] for item in lint_result["erklaerte_brueche"]] == [ids[2]]
