#!/usr/bin/env python3
"""migrate_gedaechtnisart.py -- Aufgabe 104
(docs/PLAN_GEDAECHTNISARTEN_2026-08-19.md), BDW-F01/F02.

Zieht die Live-DB auf schema.sql nach (Vorbild migrate_gattung.py/
migrate_freigabe.py -- additiv, ALTER TABLE je Tabelle + zwei BEFORE-
Trigger je Tabelle, SQLite kennt kein nachtraegliches CHECK):

1. Spalte knowledge_nodes.gedaechtnisart (NOT NULL DEFAULT 'semantisch').
2. Spalte lessons_learned.gedaechtnisart (NOT NULL DEFAULT 'episodisch').
   ZWEI VERSCHIEDENE Vorgabewerte, weil die Tabellen unterschiedlich
   vorsortiert sind (104.1.2 der Planung): Stichprobe n=32 aus
   knowledge_nodes WHERE gattung='arbeitsbestand' ergab 53% semantisch,
   n=30 aus lessons_learned ergab 70% episodisch. SQLite fuellt jede
   Bestandszeile automatisch mit dem Vorgabewert beim ALTER TABLE -- das
   IST der Zuordnungsweg fuer bestehende Zeilen, keine zusaetzliche
   UPDATE-Kampagne noetig oder gebaut.
3. Je zwei Werte-Trigger (bi/bu) je Tabelle: erlaubt sind episodisch,
   semantisch, prozedural.

AUSDRUECKLICH NICHT TEIL DIESER MIGRATION (F03, docs/PLAN_GEDAECHTNISARTEN_
2026-08-19.md §104.2/104.3): keine eigene Tabelle/kein eigener Lebenszyklus
fuer Prozeduren, kein Freigabe-/Widerruftest, der von Fakten getrennt ist.
'prozedural' ist als Wert zulaessig und wird von keiner Zeile automatisch
vergeben -- ohne einen solchen zweiten Mechanismus fehlt BDW-F03-AC1 weiterhin
vollstaendig.

Usage:
    python3 migrationen/migrate_gedaechtnisart.py [--apply]
    python3 migrationen/migrate_gedaechtnisart.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

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
# Repo-Wurzel wie oben ermittelt (an schema.sql erkannt) -- migrate_gattung.py
# geht hier faelschlich von HERE aus, was bricht, seit die Migrationsskripte
# unter migrationen/ statt im Repo-Root liegen (schema.sql/brainlehr.db
# liegen weiterhin im Root). Fuer diese neue Datei richtig verdrahtet: _w
# wurde oben beim sys.path-Aufbau bereits an schema.sql verankert.
WURZEL = _w
DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (WURZEL / "brainlehr.db"))

WERTE = ("episodisch", "semantisch", "prozedural")

# (Tabelle, Vorgabewert, Trigger-Namen).
TABELLEN = (
    ("knowledge_nodes", "semantisch",
     ("knowledge_nodes_gedaechtnisart_check_bi", "knowledge_nodes_gedaechtnisart_check_bu")),
    ("lessons_learned", "episodisch",
     ("lessons_learned_gedaechtnisart_check_bi", "lessons_learned_gedaechtnisart_check_bu")),
)


def _has_column(conn: sqlite3.Connection, table: str) -> bool:
    return "gedaechtnisart" in {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def missing_triggers(conn: sqlite3.Connection, trigger_names: tuple[str, ...]) -> list[str]:
    existing = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    return [t for t in trigger_names if t not in existing]


def _trigger_sql(table: str, bi_name: str, bu_name: str) -> str:
    werte_liste = ",".join(f"'{w}'" for w in WERTE)
    fehlermeldung = f"{table}.gedaechtnisart unzulaessig: erlaubt sind episodisch, semantisch, prozedural"
    return f"""
CREATE TRIGGER IF NOT EXISTS {bi_name}
BEFORE INSERT ON {table}
FOR EACH ROW WHEN NEW.gedaechtnisart NOT IN ({werte_liste})
BEGIN
    SELECT RAISE(ABORT, '{fehlermeldung}');
END;

CREATE TRIGGER IF NOT EXISTS {bu_name}
BEFORE UPDATE ON {table}
FOR EACH ROW WHEN NEW.gedaechtnisart NOT IN ({werte_liste})
BEGIN
    SELECT RAISE(ABORT, '{fehlermeldung}');
END;
"""


def _backup(db_path: Path) -> Path:
    """Gleiches Muster wie migrate_gattung.py -- Checkpoint vor dem Kopieren,
    sonst fehlen committete, aber noch nicht zurueckgeschriebene WAL-
    Aenderungen in der Sicherung (Lehre L-218f1e)."""
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


def migrate(db_path: Path, apply: bool) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        je_tabelle = {}
        etwas_fehlt = False
        for table, default, (bi_name, bu_name) in TABELLEN:
            spalte_fehlt = not _has_column(conn, table)
            trigger_fehlen = [] if spalte_fehlt else missing_triggers(conn, (bi_name, bu_name))
            je_tabelle[table] = {
                "vorher_zeilen": conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0],
                "spalte_fehlt": spalte_fehlt,
                "trigger_fehlen": trigger_fehlen,
                "vorgabewert": default,
            }
            if spalte_fehlt or trigger_fehlen:
                etwas_fehlt = True
    finally:
        conn.close()

    result = {"je_tabelle": je_tabelle, "backup": None, "etwas_fehlt": etwas_fehlt}
    if not etwas_fehlt or not apply:
        return result

    backup_path = _backup(db_path)
    result["backup"] = str(backup_path)

    conn = sqlite3.connect(str(db_path))
    try:
        for table, default, (bi_name, bu_name) in TABELLEN:
            info = je_tabelle[table]
            if info["spalte_fehlt"]:
                conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN "
                    f"gedaechtnisart TEXT NOT NULL DEFAULT '{default}'"
                )
            conn.executescript(_trigger_sql(table, bi_name, bu_name))
        conn.commit()
        for table, _default, _names in TABELLEN:
            je_tabelle[table]["nachher_zeilen"] = conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
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
    print(f"=== migrate_gedaechtnisart ({mode}) ===")
    for table, info in res["je_tabelle"].items():
        print(f"{table}: vorher {info['vorher_zeilen']} Zeilen, Spalte fehlt: "
              f"{info['spalte_fehlt']}, fehlende Trigger: {info['trigger_fehlen'] or '(keine)'}, "
              f"Vorgabewert: {info['vorgabewert']}")
    if res["backup"]:
        print(f"Sicherung: {res['backup']}")
    return 0


def _selftest() -> int:
    import re as _re
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "brainlehr.db"
        schema_sql = (WURZEL / "schema.sql").read_text(encoding="utf-8")

        # gedaechtnisart-Bloecke (Spalten + Trigger) aus dem Schema
        # herausschneiden, damit der Selbsttest gegen den Vorher-Stand rot
        # laufen kann (gleiche Technik wie migrate_gattung.py::_selftest).
        old_schema, n1 = _re.subn(
            r",\n    -- Gedaechtnisart \(Aufgabe 104.*?gedaechtnisart TEXT NOT NULL DEFAULT 'semantisch'\n\);",
            "\n);", schema_sql, count=1, flags=_re.DOTALL,
        )
        assert n1 == 1, "gedaechtnisart-Block an knowledge_nodes nicht wie erwartet gefunden"
        old_schema, n2 = _re.subn(
            r",\n    -- Gedaechtnisart, s\. Kommentar.*?gedaechtnisart TEXT NOT NULL DEFAULT 'episodisch'\n\);",
            "\n);", old_schema, count=1, flags=_re.DOTALL,
        )
        assert n2 == 1, "gedaechtnisart-Block an lessons_learned nicht wie erwartet gefunden"
        old_schema, n3 = _re.subn(
            r"-- Gedaechtnisart \(Aufgabe 104\): gleiche Bauform.*?"
            r"CREATE TRIGGER IF NOT EXISTS knowledge_nodes_gedaechtnisart_check_bi.*?END;\n\n"
            r"CREATE TRIGGER IF NOT EXISTS knowledge_nodes_gedaechtnisart_check_bu.*?END;\n\n",
            "", old_schema, count=1, flags=_re.DOTALL,
        )
        assert n3 == 1, "gedaechtnisart-Trigger an knowledge_nodes nicht wie erwartet gefunden"
        old_schema, n4 = _re.subn(
            r"-- Gedaechtnisart \(Aufgabe 104\), s\. Kommentar.*?"
            r"CREATE TRIGGER IF NOT EXISTS lessons_learned_gedaechtnisart_check_bi.*?END;\n\n"
            r"CREATE TRIGGER IF NOT EXISTS lessons_learned_gedaechtnisart_check_bu.*?END;\n\n",
            "", old_schema, count=1, flags=_re.DOTALL,
        )
        assert n4 == 1, "gedaechtnisart-Trigger an lessons_learned nicht wie erwartet gefunden"
        assert "gedaechtnisart" not in old_schema

        conn = sqlite3.connect(str(db_path))
        conn.executescript(old_schema)
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, "
            "norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
            "VALUES ('n1', '/a', 'shared', 't', 's', 'c', 0, 'selbst beobachtet', "
            "'keine_norm', 'skript:test', 'Testvorrichtung')"
        )
        conn.execute(
            "INSERT INTO lessons_learned (id, type, description, anlass) "
            "VALUES ('L-x', 'insight', 'Testlehre', 'skript')"
        )
        conn.commit()
        conn.close()

        conn = sqlite3.connect(str(db_path))
        assert not _has_column(conn, "knowledge_nodes")
        assert not _has_column(conn, "lessons_learned")
        conn.close()

        # (a) erster Lauf: Spalte + Trigger je Tabelle, Vorgabewerte
        # unterscheiden sich zwischen den Tabellen.
        res1 = migrate(db_path, apply=True)
        assert res1["backup"] and Path(res1["backup"]).exists()
        assert res1["je_tabelle"]["knowledge_nodes"]["vorher_zeilen"] == 1
        assert res1["je_tabelle"]["lessons_learned"]["vorher_zeilen"] == 1

        conn = sqlite3.connect(str(db_path))
        rows_n = dict(conn.execute("SELECT id, gedaechtnisart FROM knowledge_nodes").fetchall())
        rows_l = dict(conn.execute("SELECT id, gedaechtnisart FROM lessons_learned").fetchall())
        assert rows_n == {"n1": "semantisch"}, rows_n
        assert rows_l == {"L-x": "episodisch"}, rows_l

        # (b) Gegenprobe abweisend: unzulaessiger Wert wird abgelehnt, auf
        # BEIDEN Tabellen.
        for table, id_col, id_val in (("knowledge_nodes", "id", "n1"), ("lessons_learned", "id", "L-x")):
            try:
                conn.execute(f"UPDATE {table} SET gedaechtnisart = 'quatsch' WHERE {id_col} = ?", (id_val,))
                raised = False
            except sqlite3.IntegrityError:
                raised = True
            assert raised, f"unzulaessiger gedaechtnisart-Wert an {table} haette abgelehnt werden muessen"

        # (c) Gegenprobe annehmend: 'prozedural' -- heute leer, aber
        # zulaessig -- wird angenommen, auf BEIDEN Tabellen.
        conn.execute("UPDATE knowledge_nodes SET gedaechtnisart = 'prozedural' WHERE id = 'n1'")
        conn.execute("UPDATE lessons_learned SET gedaechtnisart = 'prozedural' WHERE id = 'L-x'")
        conn.execute("UPDATE knowledge_nodes SET gedaechtnisart = 'episodisch' WHERE id = 'n1'")
        conn.commit()
        conn.close()

        # (d) zweiter Lauf: nichts zu tun, keine neue Sicherung, keine
        # Verdopplung -- idempotent.
        res2 = migrate(db_path, apply=True)
        assert res2["backup"] is None
        assert res2["etwas_fehlt"] is False
        for table, _default, _names in TABELLEN:
            assert res2["je_tabelle"][table]["spalte_fehlt"] is False
            assert res2["je_tabelle"][table]["trigger_fehlen"] == []

    print("SELFTEST OK: gedaechtnisart additiv auf beiden Tabellen, je eigener "
          "Vorgabewert (knowledge_nodes=semantisch, lessons_learned=episodisch), "
          "Trigger auf beiden Tabellen aktiv, prozedural zulaessig, idempotent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
