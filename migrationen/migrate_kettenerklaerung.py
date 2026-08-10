#!/usr/bin/env python3
"""migrate_kettenerklaerung.py -- Auftrag 2026-08-06 (erklaerte Kettenbrueche).

Zieht die Live-DB auf schema.sql nach: eine neue Tabelle chain_explanations
(siehe deren Spaltenkommentar in schema.sql und kettenerklaerung.py fuer das
Verfahren). CREATE TABLE IF NOT EXISTS in schema.sql wirkt nur auf eine neu
erstellte Datei -- ohne diesen Lauf bliebe die Live-DB ohne die Tabelle,
gleiche Luecke wie migrate_auditkette.py fuer access_log.zeilen_hash/
ketten_hash beschreibt (Lehre L-636a44).

Weg: CREATE TABLE IF NOT EXISTS direkt (keine ALTER-Spalte an einer
bestehenden Tabelle) -- idempotent, kein Datenverlust moeglich, weil nichts
Bestehendes angefasst wird.

Usage:
    .venv/bin/python shared-knowledge/migrate_kettenerklaerung.py [--apply]
    .venv/bin/python shared-knowledge/migrate_kettenerklaerung.py --selftest
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

import hashlib
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (HERE / "knowledge.db"))
CET = timezone(timedelta(hours=1))

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS chain_explanations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    access_log_id INTEGER NOT NULL,
    grund TEXT NOT NULL,
    commit_hash TEXT,
    vorher_hash TEXT NOT NULL,
    nachher_hash TEXT NOT NULL,
    erstellt_am TEXT NOT NULL,
    erstellt_von TEXT,
    anker_beleg TEXT
)
"""


def _backup(db_path: Path) -> Path:
    """Identisches Muster wie migrate_auditkette.py::_backup()."""
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


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table_exists(conn: sqlite3.Connection) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='chain_explanations'"
    ).fetchone() is not None


def migrate(db_path: Path, apply: bool) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        vorher = table_exists(conn)
    finally:
        conn.close()

    result = {"vorher_vorhanden": vorher, "backup": None, "nachher_vorhanden": vorher}
    if vorher or not apply:
        return result

    backup_path = _backup(db_path)
    result["backup"] = str(backup_path)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(TABLE_SQL)
        conn.commit()
        result["nachher_vorhanden"] = table_exists(conn)
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

    sha_before = _file_sha256(DB_PATH)
    res = migrate(DB_PATH, apply=apply)
    mode = "APPLY" if apply else "DRY-RUN (kein --apply)"
    print(f"=== migrate_kettenerklaerung ({mode}) ===")
    print(f"chain_explanations vorher vorhanden: {res['vorher_vorhanden']}")
    if res["backup"]:
        print(f"Sicherung: {res['backup']}")
    print(f"chain_explanations nachher vorhanden: {res['nachher_vorhanden']}")
    if apply:
        sha_after = _file_sha256(DB_PATH)
        print(f"sha256 Datei vorher={sha_before[:16]} nachher={sha_after[:16]}")
    return 0


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "knowledge.db"
        schema_sql = (HERE / "schema.sql").read_text(encoding="utf-8")
        import re as _re
        # Alte Form simulieren: schema.sql OHNE den chain_explanations-Block,
        # wie eine echte Alt-DB vor dieser Migration.
        old_schema, n = _re.subn(
            r"-- Erklaerte Kettenbrueche.*?CREATE TABLE IF NOT EXISTS chain_explanations \(.*?\);\n\n",
            "", schema_sql, flags=_re.DOTALL,
        )
        assert n == 1, "chain_explanations-Block im schema.sql nicht wie erwartet gefunden"
        assert "chain_explanations" not in old_schema

        conn = sqlite3.connect(str(db_path))
        conn.executescript(old_schema)
        conn.commit()
        conn.close()

        conn = sqlite3.connect(str(db_path))
        vorher = table_exists(conn)
        conn.close()
        assert vorher is False

        res1 = migrate(db_path, apply=True)
        assert res1["vorher_vorhanden"] is False
        assert res1["backup"] and Path(res1["backup"]).exists()
        assert res1["nachher_vorhanden"] is True

        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO chain_explanations (access_log_id, grund, vorher_hash, nachher_hash, erstellt_am) "
            "VALUES (1, 'Test', 'a', 'b', '2026-08-06T00:00:00+02:00')"
        )
        conn.commit()
        conn.close()

        # Zweiter Lauf: nichts zu tun, keine neue Sicherung, Daten bleiben.
        res2 = migrate(db_path, apply=True)
        assert res2["vorher_vorhanden"] is True
        assert res2["backup"] is None

        conn = sqlite3.connect(str(db_path))
        n_rows = conn.execute("SELECT COUNT(*) FROM chain_explanations").fetchone()[0]
        conn.close()
        assert n_rows == 1

    print("migrate_kettenerklaerung --selftest: alle Faelle bestanden")
    return 0


if __name__ == "__main__":
    sys.exit(main())
