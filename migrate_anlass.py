#!/usr/bin/env python3
"""migrate_anlass.py -- Auftrag 2026-08-06 (Frage: entsteht Wissen von allein
oder nur auf Anordnung?). Zieht die Live-DB auf schema.sql nach: Spalte
anlass additiv an knowledge_nodes UND lessons_learned (schema.sql wirkt nur
auf eine neu erstellte Datei, siehe migrate_normfelder.py-Vorbild).

NOT NULL DEFAULT 'unbekannt' -- SQLite fuellt bei ALTER TABLE ADD COLUMN mit
einem konstanten DEFAULT automatisch jede Bestandszeile, kein separater
Rueckfuell-Schritt noetig (anders als migrate_quellhash.py, dessen Spalte
nullbar ist und wert-abhaengig rueckgefuellt wird).

Usage:
    .venv/bin/python shared-knowledge/migrate_anlass.py [--apply]
    .venv/bin/python shared-knowledge/migrate_anlass.py --selftest
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
# BEGOD_KNOWLEDGE_DB ueberschreibt den Pfad -- gleiches Muster wie
# knowledge_mcp_server.py::DB_PATH, sonst laesst sich dieses Skript nie gegen
# eine Testkopie fahren, ohne die Produktiv-DB anzufassen.
DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (HERE / "knowledge.db"))
CET = timezone(timedelta(hours=1))

NEW_COLUMN_SQL = "anlass TEXT NOT NULL DEFAULT 'unbekannt'"
TABLES = ("knowledge_nodes", "lessons_learned")


def _backup(db_path: Path) -> Path:
    """Identisches Muster wie migrate_normfelder.py/migrate_quellhash.py --
    Checkpoint vor dem Kopieren, sonst fehlen committete, aber noch nicht
    zurueckgeschriebene WAL-Aenderungen in der Sicherung (Befund 2026-08-05,
    Lehre L-218f1e)."""
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


def _row_checksum(conn: sqlite3.Connection) -> str:
    """Gleiche Methode wie migrate_normfelder.py -- deckt bewusst nur
    Inhaltsfelder ab, nicht die neue Spalte."""
    h = hashlib.sha256()
    for row in conn.execute(
        "SELECT id, title, summary, coalesce(content,'') FROM knowledge_nodes ORDER BY id"
    ):
        h.update("|".join(row).encode("utf-8"))
    for row in conn.execute(
        "SELECT id, description, coalesce(root_cause,''), coalesce(resolution,''), "
        "coalesce(prevention,'') FROM lessons_learned ORDER BY id"
    ):
        h.update("|".join(row).encode("utf-8"))
    return h.hexdigest()


def missing_tables(conn: sqlite3.Connection) -> list[str]:
    missing = []
    for table in TABLES:
        cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if "anlass" not in cols:
            missing.append(table)
    return missing


def migrate(db_path: Path, apply: bool) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        before_nodes = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        before_lessons = conn.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
        to_add = missing_tables(conn)
        checksum_before = _row_checksum(conn)
    finally:
        conn.close()

    result = {
        "vorher_zeilen_nodes": before_nodes,
        "vorher_zeilen_lessons": before_lessons,
        "geplant": to_add,
        "backup": None,
        "checksum_vorher": checksum_before,
        "checksum_nachher": checksum_before,
        "unbekannt_nodes": None,
        "unbekannt_lessons": None,
    }
    if not to_add or not apply:
        return result

    backup_path = _backup(db_path)
    result["backup"] = str(backup_path)

    conn = sqlite3.connect(str(db_path))
    try:
        for table in to_add:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {NEW_COLUMN_SQL}")
        conn.commit()
        result["unbekannt_nodes"] = conn.execute(
            "SELECT COUNT(*) FROM knowledge_nodes WHERE anlass = 'unbekannt'"
        ).fetchone()[0]
        result["unbekannt_lessons"] = conn.execute(
            "SELECT COUNT(*) FROM lessons_learned WHERE anlass = 'unbekannt'"
        ).fetchone()[0]
        result["checksum_nachher"] = _row_checksum(conn)
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
    print(f"=== migrate_anlass ({mode}) ===")
    print(f"vorher: {res['vorher_zeilen_nodes']} Knoten, {res['vorher_zeilen_lessons']} Lehren")
    print(f"fehlende Spalte anlass in: {res['geplant'] or '(keine -- bereits migriert)'}")
    if res["backup"]:
        print(f"Sicherung: {res['backup']}")
    if res["unbekannt_nodes"] is not None:
        print(f"anlass='unbekannt' gesetzt: {res['unbekannt_nodes']} Knoten, {res['unbekannt_lessons']} Lehren")
    print(f"Pruefsumme Bestandsdaten vorher={res['checksum_vorher'][:16]} "
          f"nachher={res['checksum_nachher'][:16]} "
          f"({'gleich' if res['checksum_vorher'] == res['checksum_nachher'] else 'GEAENDERT -- FEHLER'})")
    return 0


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "knowledge.db"
        schema_sql = (HERE / "schema.sql").read_text(encoding="utf-8")

        # Alte Form simulieren: beide Tabellen OHNE anlass, wie eine echte
        # Alt-DB vor diesem Auftrag.
        import re as _re
        old_schema, n1 = _re.subn(
            r",\n    -- Anlass \(Auftrag 2026-08-06\).*?anlass TEXT NOT NULL DEFAULT 'unbekannt'\n\);",
            "\n);", schema_sql, count=1, flags=_re.DOTALL,
        )
        assert n1 == 1, "Anlass-Block an knowledge_nodes nicht wie erwartet gefunden"
        old_schema, n2 = _re.subn(
            r",(\s*-- 1 wenn bereits Regel generiert\n)"
            r"    anlass TEXT NOT NULL DEFAULT 'unbekannt'  -- siehe Kommentar an knowledge_nodes\.anlass\n\);",
            r"\1);", old_schema, count=1,
        )
        assert n2 == 1, "Anlass-Spalte an lessons_learned nicht wie erwartet gefunden"
        assert "anlass" not in old_schema.split("CREATE VIRTUAL TABLE")[0]

        conn = sqlite3.connect(str(db_path))
        conn.executescript(old_schema)
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level) "
            "VALUES ('n1', '/x', 'shared', 'Titel', 'Summary', 'Inhalt', 0)"
        )
        conn.execute(
            "INSERT INTO lessons_learned (id, type, description) VALUES ('L-1', 'insight', 'Text')"
        )
        conn.commit()
        conn.close()

        conn = sqlite3.connect(str(db_path))
        before = missing_tables(conn)
        conn.close()
        assert set(before) == set(TABLES), before

        res1 = migrate(db_path, apply=True)
        assert res1["backup"] and Path(res1["backup"]).exists()
        assert res1["vorher_zeilen_nodes"] == 1 and res1["vorher_zeilen_lessons"] == 1
        assert res1["checksum_vorher"] == res1["checksum_nachher"]
        assert res1["unbekannt_nodes"] == 1
        assert res1["unbekannt_lessons"] == 1

        conn = sqlite3.connect(str(db_path))
        row_n = conn.execute("SELECT anlass FROM knowledge_nodes WHERE id='n1'").fetchone()
        row_l = conn.execute("SELECT anlass FROM lessons_learned WHERE id='L-1'").fetchone()
        conn.close()
        assert row_n == ("unbekannt",), row_n
        assert row_l == ("unbekannt",), row_l

        # Zweiter Lauf: nichts zu tun, keine neue Sicherung.
        res2 = migrate(db_path, apply=True)
        assert res2["geplant"] == [], res2["geplant"]
        assert res2["backup"] is None

    print("SELFTEST OK: anlass additiv an beiden Tabellen, Altbestand automatisch 'unbekannt', idempotent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
