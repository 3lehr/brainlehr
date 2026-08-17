import sqlite3

import session_checkpoint


def test_checkpoint_is_append_only_and_latest_is_deterministic():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(open("schema.sql", encoding="utf-8").read())
    first = session_checkpoint.save(conn, session="s", summary="one")
    second = session_checkpoint.save(conn, session="s", summary="two")
    assert (first["sequence"], second["sequence"]) == (1, 2)
    assert session_checkpoint.latest(conn, "s")["id"] == second["id"]


def test_checkpoint_rejects_empty_summary():
    conn = sqlite3.connect(":memory:")
    conn.executescript(open("schema.sql", encoding="utf-8").read())
    try:
        session_checkpoint.save(conn, session="s", summary=" ")
    except ValueError:
        pass
    else:
        raise AssertionError("empty summary accepted")
