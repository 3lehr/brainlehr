#!/usr/bin/env python3
"""migrate_schreiber.py -- Auftrag 2026-08-06 (Mangel: access_log.actor nur
9%, .session nur 0,5% gefuellt, UND kein Feld fuer den Schreiber auf
knowledge_nodes/lessons_learned selbst). Rueckstand: die drei Spalten
actor/session/model fehlen in Bestands-DBs, die vor diesem Auftrag angelegt
wurden, auf BEIDEN Tabellen. Additiv und idempotent, gleiches Muster wie
migrate_zuruecknahme.py: WAL-Checkpoint + Sicherungskopie (Lehre L-218f1e) VOR
dem ALTER TABLE. NULL-faehig, kein Rueckfuell-Schritt (Altbestand hatte keinen
Schreiber erfasst -- 'unbekannt' waere hier eine erfundene Aussage, anders als
bei anlass, das von Anfang an einen Vorgabewert trug). Der laufende Server
zieht dieselben Spalten automatisch je Verbindung nach
(knowledge_mcp_server.py::_ensure_schreiber_columns), dieses Skript ist der
manuelle/CI-Weg und der Ort, an dem die Abnahme belegt wird.

NACHTRAG (Auftrag 2026-08-06, zweiter Teil): model kam dazu -- DIESE Migration
erweitert statt eine zweite angelegt, weil actor/session/model dieselbe
Machform, dieselben zwei Tabellen und denselben Nachzug-Mechanismus teilen;
zwei fast identische Skripte waeren reine Duplikation gewesen. Bereits
gelaufene Installationen (nur actor/session vorhanden) werden beim naechsten
Lauf automatisch um model ergaenzt -- missing_columns() prueft alle drei
unabhaengig je Tabelle.

Usage:
    .venv/bin/python shared-knowledge/migrate_schreiber.py [--apply]
    .venv/bin/python shared-knowledge/migrate_schreiber.py --selftest
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

TABLES = ("knowledge_nodes", "lessons_learned")
NEW_COLUMNS = ("actor", "session", "model")


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


def missing_columns(conn: sqlite3.Connection) -> dict[str, set[str]]:
    tables_present = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    out = {}
    for table in TABLES:
        if table not in tables_present:
            continue
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        missing = set(NEW_COLUMNS) - existing
        if missing:
            out[table] = missing
    return out


def migrate(db_path: Path, apply: bool) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        vorher_nodes = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        missing = missing_columns(conn)
    finally:
        conn.close()

    result = {"vorher_zeilen_nodes": vorher_nodes,
              "fehlende_spalten": {t: sorted(cols) for t, cols in missing.items()},
              "backup": None, "nachher_zeilen_nodes": vorher_nodes}
    if not missing or not apply:
        return result

    backup_path = _backup(db_path)
    result["backup"] = str(backup_path)

    conn = sqlite3.connect(str(db_path))
    try:
        for table, cols in missing.items():
            for name in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} TEXT")
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
    print(f"=== migrate_schreiber ({mode}) ===")
    print(f"vorher: {res['vorher_zeilen_nodes']} Knoten")
    print(f"fehlende Spalten: {res['fehlende_spalten']}")
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
        # Alte Bestandslage nachbauen: actor/session fehlen an beiden Tabellen
        # (schema.sql legt sie schon an) -- SQLite kennt kein DROP COLUMN vor
        # 3.35, Tabellen neu aufbauen ohne sie.
        conn.execute("ALTER TABLE knowledge_nodes RENAME TO knowledge_nodes_alt")
        conn.execute("""
            CREATE TABLE knowledge_nodes AS
            SELECT id, path, parent_path, project_id, title, summary, content, level,
                   tags, source, confidence, access_count, created_at, updated_at,
                   norm_rang, gilt_ab, gilt_bis, quell_hash, anlass, abgeleitet_von,
                   zurueckgezogen, zurueckgezogen_grund, zurueckgezogen_am, zurueckgezogen_von
            FROM knowledge_nodes_alt
        """)
        conn.execute("DROP TABLE knowledge_nodes_alt")
        conn.execute("ALTER TABLE lessons_learned RENAME TO lessons_learned_alt")
        conn.execute("""
            CREATE TABLE lessons_learned AS
            SELECT id, node_path, type, severity, description, root_cause, resolution,
                   prevention, occurrences, projects, status, first_seen, last_seen,
                   auto_rule_generated, anlass
            FROM lessons_learned_alt
        """)
        conn.execute("DROP TABLE lessons_learned_alt")
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, anlass) "
            "VALUES ('n1', '/x', 'shared', 'Titel', 'Summary', 'Inhalt', 0, 'quelle', 'unbekannt')"
        )
        conn.execute(
            "INSERT INTO lessons_learned (id, type, description) VALUES ('L-1', 'pattern', 'Testlesson')"
        )
        conn.commit()
        conn.close()

        conn = sqlite3.connect(str(db_path))
        missing = missing_columns(conn)
        assert missing == {"knowledge_nodes": {"actor", "session", "model"},
                            "lessons_learned": {"actor", "session", "model"}}, missing
        conn.close()

        res1 = migrate(db_path, apply=True)
        assert res1["fehlende_spalten"] == {"knowledge_nodes": ["actor", "model", "session"],
                                             "lessons_learned": ["actor", "model", "session"]}, res1
        assert res1["backup"] and Path(res1["backup"]).exists()
        assert res1["vorher_zeilen_nodes"] == res1["nachher_zeilen_nodes"] == 1, res1

        conn = sqlite3.connect(str(db_path))
        assert missing_columns(conn) == {}, "Spalten fehlen nach dem Lauf"
        row_n = conn.execute("SELECT actor, session, model FROM knowledge_nodes WHERE id='n1'").fetchone()
        assert row_n == (None, None, None), row_n  # Bestandszeile bleibt NULL, kein erfundener Rueckfuellwert
        row_l = conn.execute("SELECT actor, session, model FROM lessons_learned WHERE id='L-1'").fetchone()
        assert row_l == (None, None, None), row_l
        conn.close()

        # Zweiter Lauf: nichts zu tun, keine neue Sicherung.
        res2 = migrate(db_path, apply=True)
        assert res2["fehlende_spalten"] == {}
        assert res2["backup"] is None

    print("SELFTEST OK: actor/session/model auf knowledge_nodes UND lessons_learned nachgetragen, "
          "Bestandszeilen bleiben NULL, idempotent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
