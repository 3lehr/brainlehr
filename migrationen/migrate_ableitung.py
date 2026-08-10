#!/usr/bin/env python3
"""migrate_ableitung.py -- Auftrag 2026-08-06 (ADR-027 Nachtrag 4, Lehre
L-adfb33). Rueckstand: knowledge_nodes.abgeleitet_von fehlt in Bestands-DBs,
die vor diesem Auftrag angelegt wurden. Additiv und idempotent, gleiches
Muster wie migrate_source_constraints.py: WAL-Checkpoint + Sicherungskopie
(Lehre L-218f1e) VOR dem ALTER TABLE. Kein Rueckfuell-Schritt noetig -- die
Spalte ist NULL-faehig, NULL ist der unveraenderte Normalfall (der laufende
Server zieht dasselbe automatisch je Verbindung nach ueber
knowledge_mcp_server.py::_ensure_abgeleitet_von_column, dieses Skript ist der
manuelle/CI-Weg und der Ort, an dem die Abnahme belegt wird).

Usage:
    .venv/bin/python shared-knowledge/migrate_ableitung.py [--apply]
    .venv/bin/python shared-knowledge/migrate_ableitung.py --selftest
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (HERE / "knowledge.db"))
CET = timezone(timedelta(hours=1))


def _backup(db_path: Path) -> Path:
    conn = sqlite3.connect(str(db_path))
    try:
        busy, log_frames, checkpointed = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if busy:
            raise RuntimeError(
                f"WAL-Checkpoint blockiert (busy={busy}, log={log_frames} Frames, "
                f"{checkpointed} checkpointed) -- ein anderer Prozess schreibt gerade. "
                "Sicherung abgebrochen statt unvollstaendig angelegt."
            )
    finally:
        conn.close()
    stamp = datetime.now(CET).strftime("%Y%m%dT%H%M%S")
    dest = db_path.parent / f"{db_path.name}.bak-{stamp}"
    shutil.copy2(db_path, dest)
    return dest


def has_column(conn: sqlite3.Connection) -> bool:
    return "abgeleitet_von" in {row[1] for row in conn.execute("PRAGMA table_info(knowledge_nodes)")}


def migrate(db_path: Path, apply: bool) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        before_nodes = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        schon_da = has_column(conn)
    finally:
        conn.close()

    result = {"vorher_zeilen_nodes": before_nodes, "geplant": not schon_da,
              "backup": None, "nachher_zeilen_nodes": before_nodes}
    if schon_da or not apply:
        return result

    backup_path = _backup(db_path)
    result["backup"] = str(backup_path)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("ALTER TABLE knowledge_nodes ADD COLUMN abgeleitet_von TEXT")
        conn.commit()
        result["nachher_zeilen_nodes"] = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    finally:
        conn.close()
    return result


def main() -> int:
    apply = "--apply" in sys.argv
    if "--selftest" in sys.argv:
        return _selftest()

    print(f"Datenbank: {DB_PATH}")
    if not DB_PATH.exists():
        print(f"FEHLER: {DB_PATH} nicht gefunden.")
        return 1

    res = migrate(DB_PATH, apply=apply)
    mode = "APPLY" if apply else "DRY-RUN (kein --apply)"
    print(f"=== migrate_ableitung ({mode}) ===")
    print(f"vorher: {res['vorher_zeilen_nodes']} Knoten")
    print(f"Spalte abgeleitet_von fehlt: {res['geplant']}")
    if res["backup"]:
        print(f"Sicherung: {res['backup']}")
    print(f"nachher: {res['nachher_zeilen_nodes']} Knoten")
    return 0


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "knowledge.db"
        schema_sql = (HERE / "schema.sql").read_text(encoding="utf-8")

        conn = sqlite3.connect(str(db_path))
        conn.executescript(schema_sql)
        # Alte Bestandslage nachbauen: Spalte entfernen (schema.sql legt sie
        # schon an) -- SQLite kennt kein DROP COLUMN vor 3.35, Tabelle neu
        # aufbauen ohne die Spalte.
        conn.execute("ALTER TABLE knowledge_nodes RENAME TO knowledge_nodes_alt")
        conn.execute("""
            CREATE TABLE knowledge_nodes AS
            SELECT id, path, parent_path, project_id, title, summary, content, level,
                   tags, source, confidence, access_count, created_at, updated_at,
                   norm_rang, gilt_ab, gilt_bis, quell_hash, anlass
            FROM knowledge_nodes_alt
        """)
        conn.execute("DROP TABLE knowledge_nodes_alt")
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, anlass) "
            "VALUES ('n1', '/x', 'shared', 'Titel', 'Summary', 'Inhalt', 0, 'quelle', 'unbekannt')"
        )
        conn.commit()
        conn.close()

        conn = sqlite3.connect(str(db_path))
        assert not has_column(conn), "Spalte haette in der Nachbau-Fixture fehlen muessen"
        conn.close()

        res1 = migrate(db_path, apply=True)
        assert res1["geplant"] is True, res1
        assert res1["backup"] and Path(res1["backup"]).exists()
        assert res1["vorher_zeilen_nodes"] == res1["nachher_zeilen_nodes"] == 1, res1

        conn = sqlite3.connect(str(db_path))
        assert has_column(conn), "Spalte fehlt nach dem Lauf"
        row = conn.execute("SELECT abgeleitet_von FROM knowledge_nodes WHERE id='n1'").fetchone()
        assert row == (None,), row  # Bestandszeile bleibt NULL, kein Rueckfuellwert
        conn.close()

        # Zweiter Lauf: nichts zu tun, keine neue Sicherung.
        res2 = migrate(db_path, apply=True)
        assert res2["geplant"] is False, res2
        assert res2["backup"] is None

    print("SELFTEST OK: Spalte abgeleitet_von nachgetragen, Bestandszeilen bleiben NULL, idempotent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
