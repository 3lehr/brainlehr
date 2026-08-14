#!/usr/bin/env python3
"""migrate_zuruecknahme.py -- Auftrag 2026-08-06 (Luecke "kein Loeschweg fuer
die KI"). Rueckstand: knowledge_nodes.zurueckgezogen/zurueckgezogen_grund/
zurueckgezogen_am/zurueckgezogen_von fehlen in Bestands-DBs, die vor diesem
Auftrag angelegt wurden. Additiv und idempotent, gleiches Muster wie
migrate_ableitung.py: WAL-Checkpoint + Sicherungskopie (Lehre L-218f1e) VOR
dem ALTER TABLE. zurueckgezogen bekommt NOT NULL DEFAULT 0 -- SQLite befuellt
Bestandszeilen beim ALTER selbst (unveraendert sichtbar, korrekt fuer
Altbestand). Der laufende Server zieht dasselbe automatisch je Verbindung nach
(knowledge_mcp_server.py::_ensure_zuruecknahme_columns), dieses Skript ist der
manuelle/CI-Weg und der Ort, an dem die Abnahme belegt wird.

Usage:
    .venv/bin/python shared-knowledge/migrate_zuruecknahme.py [--apply]
    .venv/bin/python shared-knowledge/migrate_zuruecknahme.py --selftest
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

import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import zeitmarke

HERE = Path(__file__).parent
DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (HERE / "brainlehr.db"))

NEW_COLUMNS = {
    "zurueckgezogen": "INTEGER NOT NULL DEFAULT 0",
    "zurueckgezogen_grund": "TEXT",
    "zurueckgezogen_am": "TEXT",
    "zurueckgezogen_von": "TEXT",
}


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
    stamp = datetime.now(zeitmarke.BERLIN).strftime("%Y%m%dT%H%M%S")
    dest = db_path.parent / f"{db_path.name}.bak-{stamp}"
    shutil.copy2(db_path, dest)
    return dest


def missing_columns(conn: sqlite3.Connection) -> set[str]:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(knowledge_nodes)")}
    return set(NEW_COLUMNS) - existing


def migrate(db_path: Path, apply: bool) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        before_nodes = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        missing = missing_columns(conn)
    finally:
        conn.close()

    result = {"vorher_zeilen_nodes": before_nodes, "fehlende_spalten": sorted(missing),
              "backup": None, "nachher_zeilen_nodes": before_nodes}
    if not missing or not apply:
        return result

    backup_path = _backup(db_path)
    result["backup"] = str(backup_path)

    conn = sqlite3.connect(str(db_path))
    try:
        for name in missing:
            conn.execute(f"ALTER TABLE knowledge_nodes ADD COLUMN {name} {NEW_COLUMNS[name]}")
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
    print(f"=== migrate_zuruecknahme ({mode}) ===")
    print(f"vorher: {res['vorher_zeilen_nodes']} Knoten")
    print(f"fehlende Spalten: {res['fehlende_spalten']}")
    if res["backup"]:
        print(f"Sicherung: {res['backup']}")
    print(f"nachher: {res['nachher_zeilen_nodes']} Knoten")
    return 0


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "brainlehr.db"
        schema_sql = (HERE / "schema.sql").read_text(encoding="utf-8")

        conn = sqlite3.connect(str(db_path))
        conn.executescript(schema_sql)
        # Alte Bestandslage nachbauen: die vier Spalten fehlen (schema.sql legt
        # sie schon an) -- SQLite kennt kein DROP COLUMN vor 3.35, Tabelle neu
        # aufbauen ohne sie.
        conn.execute("ALTER TABLE knowledge_nodes RENAME TO knowledge_nodes_alt")
        conn.execute("""
            CREATE TABLE knowledge_nodes AS
            SELECT id, path, parent_path, project_id, title, summary, content, level,
                   tags, source, confidence, access_count, created_at, updated_at,
                   norm_rang, gilt_ab, gilt_bis, quell_hash, anlass, abgeleitet_von
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
        assert missing_columns(conn) == set(NEW_COLUMNS), missing_columns(conn)
        conn.close()

        res1 = migrate(db_path, apply=True)
        assert res1["fehlende_spalten"] == sorted(NEW_COLUMNS), res1
        assert res1["backup"] and Path(res1["backup"]).exists()
        assert res1["vorher_zeilen_nodes"] == res1["nachher_zeilen_nodes"] == 1, res1

        conn = sqlite3.connect(str(db_path))
        assert missing_columns(conn) == set(), "Spalten fehlen nach dem Lauf"
        row = conn.execute(
            "SELECT zurueckgezogen, zurueckgezogen_grund FROM knowledge_nodes WHERE id='n1'"
        ).fetchone()
        assert row == (0, None), row  # Bestandszeile: nicht zurueckgezogen, kein Grund
        conn.close()

        # Zweiter Lauf: nichts zu tun, keine neue Sicherung.
        res2 = migrate(db_path, apply=True)
        assert res2["fehlende_spalten"] == []
        assert res2["backup"] is None

    print("SELFTEST OK: Spalten zurueckgezogen* nachgetragen, Bestandszeilen unveraendert, idempotent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
