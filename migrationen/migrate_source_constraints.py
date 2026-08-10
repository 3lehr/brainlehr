#!/usr/bin/env python3
"""migrate_source_constraints.py -- Auftrag 2026-08-06 (Befund: ein roher
INSERT am knowledge_mcp_server.py-Werkzeug vorbei erzeugte 17 Knoten ohne
source, mit freiem parent_path und beliebigem anlass -- die Python-seitigen
Pruefungen (source-Leercheck in knowledge_add, _validate_anlass) schuetzen
nur den Weg ueber das Werkzeug, nicht die Datei selbst).

Zwei Schritte, beide idempotent:
1. Rueckfuellung: knowledge_nodes.source, das NULL oder nur Leerzeichen ist,
   bekommt SOURCE_BACKFILL_PLACEHOLDER. Testdaten, Umschreiben ist erlaubt
   (Betreiber-Direktive) -- deshalb Nachtrag statt "Regel gilt nur fuer
   Neues", das haette zwei Klassen von Zeilen dauerhaft nebeneinander
   stehen lassen.
2. Sechs BEFORE-Trigger (schema.sql-Vorbild, siehe NODE_CONSTRAINT_TRIGGERS_SQL
   dort und in knowledge_mcp_server.py -- identischer Text, gleiches Muster
   wie jede andere additive Migration hier): source nicht leer, parent_path
   zeigt auf einen vorhandenen Knoten oder ist '/', anlass aus der erlaubten
   Liste -- je INSERT und UPDATE.

Der laufende Server (knowledge_mcp_server.py::ensure_schema) zieht dasselbe
automatisch je Verbindung nach; dieses Skript ist der manuelle/CI-Weg und
der Ort, an dem die Abnahme (rot-vor-gruen, Zeilenzahlen, Backup) belegt
wird.

Usage:
    .venv/bin/python shared-knowledge/migrate_source_constraints.py [--apply]
    .venv/bin/python shared-knowledge/migrate_source_constraints.py --selftest
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
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
# BEGOD_KNOWLEDGE_DB ueberschreibt den Pfad -- gleiches Muster wie
# knowledge_mcp_server.py::DB_PATH, sonst laesst sich dieses Skript nie gegen
# eine Testkopie fahren, ohne die Produktiv-DB anzufassen.
DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (HERE / "knowledge.db"))
CET = timezone(timedelta(hours=1))

SOURCE_BACKFILL_PLACEHOLDER = "unbekannt (Altbestand vor Migration 2026-08-06, nachgetragen)"

NEEDED_TRIGGERS = (
    "knowledge_nodes_source_check_bi", "knowledge_nodes_source_check_bu",
    "knowledge_nodes_parent_check_bi", "knowledge_nodes_parent_check_bu",
    "knowledge_nodes_anlass_check_bi", "knowledge_nodes_anlass_check_bu",
)

TRIGGERS_SQL = """
CREATE TRIGGER IF NOT EXISTS knowledge_nodes_source_check_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.source IS NULL OR TRIM(NEW.source) = ''
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.source darf nicht leer sein: Herkunft angeben (Datei, Konsil oder Recherche, aus der dieser Knoten stammt)');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_source_check_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.source IS NULL OR TRIM(NEW.source) = ''
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.source darf nicht leer sein: Herkunft angeben (Datei, Konsil oder Recherche, aus der dieser Knoten stammt)');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_parent_check_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.parent_path IS NOT NULL AND NEW.parent_path <> '/'
    AND NOT EXISTS (SELECT 1 FROM knowledge_nodes WHERE path = NEW.parent_path)
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.parent_path zeigt auf keinen vorhandenen Knoten: zuerst den Elternknoten anlegen, dann parent_path erneut setzen');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_parent_check_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.parent_path IS NOT NULL AND NEW.parent_path <> '/'
    AND NOT EXISTS (SELECT 1 FROM knowledge_nodes WHERE path = NEW.parent_path)
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.parent_path zeigt auf keinen vorhandenen Knoten: zuerst den Elternknoten anlegen, dann parent_path erneut setzen');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_anlass_check_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.anlass NOT IN ('selbst','betreiber','hook','skript','unbekannt')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.anlass unzulaessig: erlaubt sind selbst, betreiber, hook, skript, unbekannt');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_anlass_check_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.anlass NOT IN ('selbst','betreiber','hook','skript','unbekannt')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.anlass unzulaessig: erlaubt sind selbst, betreiber, hook, skript, unbekannt');
END;
"""


def _backup(db_path: Path) -> Path:
    """Gleiches Muster wie migrate_anlass.py -- Checkpoint vor dem Kopieren,
    sonst fehlen committete, aber noch nicht zurueckgeschriebene
    WAL-Aenderungen in der Sicherung (Lehre L-218f1e)."""
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


def missing_triggers(conn: sqlite3.Connection) -> list[str]:
    existing = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    return [t for t in NEEDED_TRIGGERS if t not in existing]


def migrate(db_path: Path, apply: bool) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        before_nodes = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        before_lessons = conn.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
        empty_source_before = conn.execute(
            "SELECT COUNT(*) FROM knowledge_nodes WHERE source IS NULL OR TRIM(source) = ''"
        ).fetchone()[0]
        to_add = missing_triggers(conn)
    finally:
        conn.close()

    result = {
        "vorher_zeilen_nodes": before_nodes,
        "vorher_zeilen_lessons": before_lessons,
        "source_leer_vorher": empty_source_before,
        "geplant": to_add,
        "backup": None,
        "source_nachgetragen": None,
        "nachher_zeilen_nodes": before_nodes,
        "nachher_zeilen_lessons": before_lessons,
    }
    if not to_add or not apply:
        return result

    backup_path = _backup(db_path)
    result["backup"] = str(backup_path)

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute(
            "UPDATE knowledge_nodes SET source = ? WHERE source IS NULL OR TRIM(source) = ''",
            (SOURCE_BACKFILL_PLACEHOLDER,),
        )
        result["source_nachgetragen"] = cur.rowcount
        conn.executescript(TRIGGERS_SQL)
        conn.commit()
        result["nachher_zeilen_nodes"] = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        result["nachher_zeilen_lessons"] = conn.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
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
    print(f"=== migrate_source_constraints ({mode}) ===")
    print(f"vorher: {res['vorher_zeilen_nodes']} Knoten, {res['vorher_zeilen_lessons']} Lehren, "
          f"{res['source_leer_vorher']} Knoten mit leerer source")
    print(f"fehlende Trigger: {res['geplant'] or '(keine -- bereits migriert)'}")
    if res["backup"]:
        print(f"Sicherung: {res['backup']}")
    if res["source_nachgetragen"] is not None:
        print(f"source nachgetragen bei: {res['source_nachgetragen']} Knoten")
    print(f"nachher: {res['nachher_zeilen_nodes']} Knoten, {res['nachher_zeilen_lessons']} Lehren")
    return 0


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "knowledge.db"
        schema_sql = (HERE / "schema.sql").read_text(encoding="utf-8")

        conn = sqlite3.connect(str(db_path))
        conn.executescript(schema_sql)
        # Alte Bestandslage nachbauen: Trigger entfernen (schema.sql legt sie
        # schon an), leere source simulieren.
        for t in NEEDED_TRIGGERS:
            conn.execute(f"DROP TRIGGER IF EXISTS {t}")
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, "
            "norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
            "VALUES ('n1', '/x', 'shared', 'Titel', 'Summary', 'Inhalt', 0, '', "
            "'keine_norm', 'skript:test', 'Testvorrichtung')"
        )
        conn.commit()
        conn.close()

        conn = sqlite3.connect(str(db_path))
        before = missing_triggers(conn)
        conn.close()
        assert set(before) == set(NEEDED_TRIGGERS), before

        res1 = migrate(db_path, apply=True)
        assert res1["backup"] and Path(res1["backup"]).exists()
        assert res1["source_leer_vorher"] == 1
        assert res1["source_nachgetragen"] == 1
        assert res1["vorher_zeilen_nodes"] == res1["nachher_zeilen_nodes"] == 1

        conn = sqlite3.connect(str(db_path))
        row = conn.execute("SELECT source FROM knowledge_nodes WHERE id='n1'").fetchone()
        assert row == (SOURCE_BACKFILL_PLACEHOLDER,), row
        # Trigger jetzt aktiv: roher INSERT ohne source wird abgelehnt.
        try:
            conn.execute(
                "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source) "
                "VALUES ('n2', '/y', 'shared', 't', 's', 'c', 0, '')"
            )
            raised = False
        except sqlite3.IntegrityError:
            raised = True
        assert raised, "roher INSERT ohne source haette abgelehnt werden muessen"
        conn.close()

        # Zweiter Lauf: nichts zu tun, keine neue Sicherung.
        res2 = migrate(db_path, apply=True)
        assert res2["geplant"] == [], res2["geplant"]
        assert res2["backup"] is None

    print("SELFTEST OK: source nachgetragen, sechs Trigger aktiv, roher INSERT ohne source abgelehnt, idempotent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
