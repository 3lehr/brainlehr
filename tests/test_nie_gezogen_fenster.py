"""Tests fuer knowledge_lint.py::find_never_pulled() -- Fenster-Splittung
(Auftrag 2026-08-06, Lehre L-73da37).

Vorher meldete die Kategorie "nie gezogen" jeden Knoten/jede Lesson, der
nicht in recall_log.jsonl auftaucht -- ohne zu pruefen, ob er ueberhaupt
JUNG GENUG ist, um darin haben auftauchen zu koennen. recall_log.jsonl
reicht nur wenige Tage zurueck; ein Knoten, der aelter ist als der
Fensterbeginn, konnte darin nie erscheinen -- das ist keine Aussage ueber
den Knoten, sondern ueber das Protokoll. Diese Tests belegen die Trennung:
"im Fenster nie gezogen" (echter Befund) vs. "aelter als das Protokoll"
(keine Aussage moeglich).

NIE gegen die echte knowledge.db -- immer frische Temp-DB aus schema.sql.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_lint as lint  # type: ignore  # noqa: E402

FMT = "%Y-%m-%dT%H:%M:%S+00:00"


@pytest.fixture()
def temp_db(tmp_path):
    """Frische DB aus dem echten Schema, drei Knoten mit kontrolliertem
    created_at (kein Trigger-Aerger noetig -- source ist ueberall gesetzt)."""
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=2)
    src = "Testvorrichtung test_nie_gezogen_fenster.py (kein echter Fund)"
    conn.executemany(
        "INSERT INTO knowledge_nodes "
        "(id, path, parent_path, project_id, title, summary, level, source, created_at, updated_at, norm_entscheidung, "
        " norm_entschieden_von, norm_entschieden_grund) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,'skript:test','Testvorrichtung')",
        [
            ("n_pulled", "/x/pulled", None, "shared", "Gezogen", "s", 0, src,
             window_start.strftime(FMT), now.strftime(FMT), "keine_norm"),
            ("n_on_boundary", "/x/on-boundary", None, "shared", "Auf Fensterbeginn", "s", 0, src,
             window_start.strftime(FMT), now.strftime(FMT), "keine_norm"),
            ("n_before_boundary", "/x/before-boundary", None, "shared", "Vor Fensterbeginn", "s", 0, src,
             (window_start - timedelta(seconds=1)).strftime(FMT), now.strftime(FMT), "keine_norm"),
            ("n_after_boundary", "/x/after-boundary", None, "shared", "Nach Fensterbeginn", "s", 0, src,
             (window_start + timedelta(seconds=1)).strftime(FMT), now.strftime(FMT), "keine_norm"),
        ],
    )
    conn.executemany(
        "INSERT INTO lessons_learned (id, type, description, status, first_seen, last_seen) VALUES (?,?,?,?,?,?)",
        [
            ("L_before_boundary", "insight", "Lesson aelter als das Protokoll.", "active",
             (window_start - timedelta(seconds=1)).strftime(FMT), now.strftime(FMT)),
            ("L_after_boundary", "insight", "Lesson im Fenster, nie gezogen.", "active",
             (window_start + timedelta(seconds=1)).strftime(FMT), now.strftime(FMT)),
        ],
    )
    conn.commit()
    conn.close()
    return db_path, window_start, now


def _log(tmp_path: Path, window_start: datetime, window_end: datetime, pulled_node: str | None = None) -> Path:
    log_path = tmp_path / "recall_log.jsonl"
    lines = [json.dumps({"ts": window_start.strftime(FMT), "nodes": [pulled_node] if pulled_node else [], "lessons": []})]
    lines.append(json.dumps({"ts": window_end.strftime(FMT), "nodes": [], "lessons": []}))
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return log_path


def _lint(db_path: Path, log_path: Path) -> dict:
    conn = lint.get_ro_conn(db_path)
    try:
        return lint.find_never_pulled(conn, log_path)
    finally:
        conn.close()


def test_window_reported_in_result(temp_db, tmp_path):
    db_path, window_start, now = temp_db
    log_path = _log(tmp_path, window_start, now, pulled_node="/x/pulled")
    result = _lint(db_path, log_path)
    assert result["window_start"] == window_start.strftime(FMT)
    assert result["window_end"] == now.strftime(FMT)


def test_pulled_node_never_appears_in_either_list(temp_db, tmp_path):
    db_path, window_start, now = temp_db
    log_path = _log(tmp_path, window_start, now, pulled_node="/x/pulled")
    result = _lint(db_path, log_path)
    assert "/x/pulled" not in result["nodes"]
    assert "/x/pulled" not in result["nodes_aelter_als_fenster"]


def test_boundary_exact_counts_as_in_window(temp_db, tmp_path):
    """Grenzwert: Entstehung GENAU auf dem Fensterbeginn zaehlt als im Fenster."""
    db_path, window_start, now = temp_db
    log_path = _log(tmp_path, window_start, now, pulled_node="/x/pulled")
    result = _lint(db_path, log_path)
    assert "/x/on-boundary" in result["nodes"]
    assert "/x/on-boundary" not in result["nodes_aelter_als_fenster"]


def test_boundary_one_second_before_is_no_assertion(temp_db, tmp_path):
    """Grenzwert: eine Sekunde vor dem Fensterbeginn -- keine Aussage moeglich,
    kein echter Befund."""
    db_path, window_start, now = temp_db
    log_path = _log(tmp_path, window_start, now, pulled_node="/x/pulled")
    result = _lint(db_path, log_path)
    assert "/x/before-boundary" not in result["nodes"]
    assert "/x/before-boundary" in result["nodes_aelter_als_fenster"]


def test_boundary_one_second_after_is_in_window(temp_db, tmp_path):
    """Grenzwert: eine Sekunde nach dem Fensterbeginn -- im Fenster."""
    db_path, window_start, now = temp_db
    log_path = _log(tmp_path, window_start, now, pulled_node="/x/pulled")
    result = _lint(db_path, log_path)
    assert "/x/after-boundary" in result["nodes"]
    assert "/x/after-boundary" not in result["nodes_aelter_als_fenster"]


def test_lessons_get_the_same_split(temp_db, tmp_path):
    """Dieselbe Trennung gilt fuer Lessons (first_seen statt created_at)."""
    db_path, window_start, now = temp_db
    log_path = _log(tmp_path, window_start, now, pulled_node="/x/pulled")
    result = _lint(db_path, log_path)
    assert "L_before_boundary" not in result["lessons"]
    assert "L_before_boundary" in result["lessons_aelter_als_fenster"]
    assert "L_after_boundary" in result["lessons"]
    assert "L_after_boundary" not in result["lessons_aelter_als_fenster"]


def test_rot_vor_gruen_old_behaviour_would_have_flagged_it(temp_db, tmp_path):
    """Rot-vor-gruen: der ungesplittete Treffer (das Verhalten VOR dieser
    Aenderung -- einfache Mengendifferenz ohne Fensterpruefung) haette
    /x/before-boundary als Befund gemeldet. Der neue Code haelt ihn aus dem
    echten Befund heraus. Beide Zustaende werden hier tatsaechlich
    nachgerechnet, nicht nur behauptet."""
    db_path, window_start, now = temp_db
    log_path = _log(tmp_path, window_start, now, pulled_node="/x/pulled")

    conn = sqlite3.connect(str(db_path))
    all_paths = {r[0] for r in conn.execute("SELECT path FROM knowledge_nodes")}
    conn.close()
    node_hits, _ = lint._recall_hits(log_path)
    altes_verhalten = all_paths - node_hits
    assert "/x/before-boundary" in altes_verhalten, "Vorbedingung: waere frueher ein Treffer gewesen"

    result = _lint(db_path, log_path)
    assert "/x/before-boundary" not in result["nodes"], "neues Verhalten haelt es aus dem echten Befund heraus"


def test_empty_log_no_crash_and_no_false_all_never_pulled(temp_db, tmp_path):
    """Leeres Protokoll: keine Division durch null, keine Falschmeldung
    'alles nie gezogen' -- ohne Fenster faellt alles in die getrennte Liste."""
    db_path, _, _ = temp_db
    empty_log = tmp_path / "empty.jsonl"
    empty_log.write_text("", encoding="utf-8")
    result = _lint(db_path, empty_log)
    assert result["window_start"] is None
    assert result["window_end"] is None
    assert result["nodes"] == []
    assert result["lessons"] == []
    assert len(result["nodes_aelter_als_fenster"]) == 4
    assert len(result["lessons_aelter_als_fenster"]) == 2


def test_missing_log_file_same_as_empty(temp_db, tmp_path):
    db_path, _, _ = temp_db
    result = _lint(db_path, tmp_path / "nicht-vorhanden.jsonl")
    assert result["window_start"] is None
    assert result["nodes"] == []


def test_access_count_and_access_log_do_not_influence_the_result(temp_db, tmp_path):
    """Dokumentierte Entscheidung (Kommentar an find_never_pulled/Kategorie 3
    in knowledge_lint.py): access_count und access_log fliessen bewusst NICHT
    ein. Belegt hier: ein Knoten mit hohem access_count und einer
    access_log-Zeile bleibt trotzdem im echten Befund, wenn recall_log.jsonl
    ihn nicht kennt -- sonst wuerde ein reiner Anlage-/Lesevorgang ausserhalb
    des Recall-Pfads einen echten Nie-gezogen-Fund verschlucken."""
    db_path, window_start, now = temp_db
    conn = sqlite3.connect(str(db_path))
    conn.execute("UPDATE knowledge_nodes SET access_count = 99 WHERE id = 'n_after_boundary'")
    conn.execute(
        "INSERT INTO access_log (node_path, action, timestamp) VALUES ('/x/after-boundary', 'add', ?)",
        (now.strftime(FMT),),
    )
    conn.commit()
    conn.close()

    log_path = _log(tmp_path, window_start, now, pulled_node="/x/pulled")
    result = _lint(db_path, log_path)
    assert "/x/after-boundary" in result["nodes"], \
        "access_count/access_log duerfen den recall_log-basierten Befund nicht veraendern"
