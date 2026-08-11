"""Tests fuer auditanker.py (Auftrag 2026-08-06, Anschluss an test_auditkette.py).

Deckt zwei Ebenen: die reine Merkle-Baum-Mathematik (kein DB-Zugriff) und
den Bestandslauf gegen eine frische Temp-DB (echtes schema.sql, NIE gegen
die echte brainlehr.db).
"""
from __future__ import annotations

import hashlib
import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import auditanker as anchor  # type: ignore  # noqa: E402
import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


# ─── Merkle-Mathematik, ohne DB ─────────────────────────────────────────

def test_one_leaf_is_its_own_root():
    assert anchor.merkle_root(["a"]) == "a"


def test_two_leaves_matches_hand_computation():
    expected = hashlib.sha256("ab".encode()).hexdigest()
    assert anchor.merkle_root(["a", "b"]) == expected


def test_three_leaves_odd_rule_duplicates_last():
    p1 = hashlib.sha256("ab".encode()).hexdigest()
    p2 = hashlib.sha256("cc".encode()).hexdigest()
    expected = hashlib.sha256((p1 + p2).encode()).hexdigest()
    assert anchor.merkle_root(["a", "b", "c"]) == expected


def test_four_leaves_matches_hand_computation():
    """Explizit von Hand nachgerechnet -- nicht nur gegen die eigene
    Funktion gegengeprueft (Auftrag verlangt genau das)."""
    q1 = hashlib.sha256("ab".encode()).hexdigest()
    q2 = hashlib.sha256("cd".encode()).hexdigest()
    expected = hashlib.sha256((q1 + q2).encode()).hexdigest()
    assert anchor.merkle_root(["a", "b", "c", "d"]) == expected


def test_membership_proof_verifies_for_every_leaf_of_four():
    leaves = ["a", "b", "c", "d"]
    root = anchor.merkle_root(leaves)
    for i, leaf in enumerate(leaves):
        proof = anchor.merkle_proof(leaves, i)
        assert anchor.verify_proof(leaf, proof, root)


def test_tampered_leaf_with_old_proof_fails():
    leaves = ["a", "b", "c", "d"]
    root = anchor.merkle_root(leaves)
    proof0 = anchor.merkle_proof(leaves, 0)
    assert not anchor.verify_proof("manipuliert", proof0, root)


def test_proof_of_other_leaf_fails():
    leaves = ["a", "b", "c", "d"]
    root = anchor.merkle_root(leaves)
    proof1 = anchor.merkle_proof(leaves, 1)  # Nachweis fuer "b"
    assert not anchor.verify_proof(leaves[0], proof1, root)  # gegen "a" geprueft


def test_empty_leaves_raise_clean_error_not_crash():
    with pytest.raises(anchor.LeereStreckeError):
        anchor.merkle_root([])
    with pytest.raises(anchor.LeereStreckeError):
        anchor.merkle_proof([], 0)


# ─── Bestandslauf gegen Temp-DB ─────────────────────────────────────────

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


def _log3(n: int = 3) -> None:
    conn = kms.get_db()
    for i in range(n):
        kms.log_access(conn, f"/x/{i}", "read", query=f"q{i}")
    conn.close()


def test_wurzel_fuer_bereich_gegen_bestand(temp_db):
    _log3(4)
    info = anchor.wurzel_fuer_bereich(temp_db)
    assert info["n"] == 4
    assert info["von"] == 1
    assert info["bis"] == 4
    # Gegenprobe: unabhaengig ueber die rohen ketten_hash-Werte nachgerechnet.
    conn = sqlite3.connect(str(temp_db))
    leaves = [r[0] for r in conn.execute(
        "SELECT ketten_hash FROM access_log ORDER BY id"
    )]
    conn.close()
    assert info["root"] == anchor.merkle_root(leaves)


def test_legacy_rows_excluded_from_tree(temp_db):
    """Altzeilen ohne ketten_hash (ungedeckter Zeitraum) duerfen nicht in
    den Baum -- selbe Erwartung wie test_auditkette.py::
    test_legacy_rows_without_hash_are_not_a_break."""
    conn = sqlite3.connect(str(temp_db))
    for i in range(5):
        conn.execute(
            "INSERT INTO access_log (node_path, action, timestamp) VALUES (?, 'read', ?)",
            (f"/legacy/{i}", f"2020-01-0{i + 1}T00:00:00+01:00"),
        )
    conn.commit()
    conn.close()

    with pytest.raises(anchor.LeereStreckeError):
        anchor.wurzel_fuer_bereich(temp_db)

    _log3(2)
    info = anchor.wurzel_fuer_bereich(temp_db)
    assert info["n"] == 2


def test_pruefe_erkennt_manipulation_auf_kopie(temp_db, tmp_path):
    """Abnahme Punkt 3: Wurzel passt gegen den Bestand, dann bricht eine
    direkte SQL-Manipulation AUF EINER KOPIE die Uebereinstimmung -- die
    echte temp_db bleibt dabei unangetastet."""
    _log3(4)
    before = anchor.wurzel_fuer_bereich(temp_db)
    assert anchor.wurzel_fuer_bereich(temp_db)["root"] == before["root"]

    kopie = tmp_path / "kopie.db"
    kopie.write_bytes(temp_db.read_bytes())
    conn = sqlite3.connect(str(kopie))
    ids = [r[0] for r in conn.execute("SELECT id FROM access_log ORDER BY id")]
    conn.execute(
        "UPDATE access_log SET ketten_hash = 'deadbeef' || substr(ketten_hash, 9) WHERE id = ?",
        (ids[1],),
    )
    conn.commit()
    conn.close()

    after = anchor.wurzel_fuer_bereich(kopie, before["von"], before["bis"])
    assert after["root"] != before["root"]

    # Original unveraendert.
    original_still = anchor.wurzel_fuer_bereich(temp_db)
    assert original_still["root"] == before["root"]


def test_format_anchor_is_commit_message_shaped():
    info = {"root": "a" * 64, "von": 1, "bis": 4, "n": 4}
    text = anchor.format_anchor(info, "2026-08-06T12:00:00+01:00")
    assert "a" * 64 in text
    assert "1-4" in text
    assert "2026-08-06T12:00:00+01:00" in text
    assert "unsigniert" in text


def test_main_wurzel_and_pruefe_cli(temp_db, capsys):
    _log3(3)
    rc = anchor.main(["--db", str(temp_db), "wurzel"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Auditanker: Merkle-Wurzel" in out
    root = out.splitlines()[0].rsplit(" ", 1)[1]

    rc_ok = anchor.main(["--db", str(temp_db), "pruefe", root, "--von", "1", "--bis", "3"])
    assert rc_ok == 0
    assert "passt" in capsys.readouterr().out

    rc_bad = anchor.main(["--db", str(temp_db), "pruefe", "f" * 64, "--von", "1", "--bis", "3"])
    assert rc_bad == 1
    assert "PASST NICHT" in capsys.readouterr().out


def test_main_selftest_flag(capsys):
    rc = anchor.main(["--selftest"])
    assert rc == 0
    assert "bestanden" in capsys.readouterr().out


def test_main_empty_range_clean_message(temp_db, capsys):
    rc = anchor.main(["--db", str(temp_db), "wurzel"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "kein Anker moeglich" in out
