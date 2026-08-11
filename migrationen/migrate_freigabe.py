#!/usr/bin/env python3
"""migrate_freigabe.py -- Planschritt S17.

Zieht die Live-DB auf schema.sql nach (Vorbild migrate_gattung.py --
additiv, ALTER TABLE + zwei BEFORE-Trigger, SQLite kennt kein nachtraeg-
liches CHECK, s. schema.sql-Kommentar):

1. Spalte knowledge_nodes.freigabe (NOT NULL DEFAULT 'intern', SQLite
   fuellt jede Bestandszeile automatisch beim ALTER TABLE -- ein Eintrag
   ohne eigene Entscheidung geht NIE als 'offen' hinaus).
2. Zwei Werte-Trigger (bi/bu): erlaubt sind offen, intern, gesperrt.

Ausdruecklich NICHT Teil dieser Migration: keine Massenzuweisung von
'offen' oder 'gesperrt' an vorhandene Knoten -- jeder Bestandsknoten
bleibt 'intern', bis jemand ihn einzeln entscheidet.

Usage:
    python3 migrate_freigabe.py [--apply]
    python3 migrate_freigabe.py --selftest
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
DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (HERE / "brainlehr.db"))
CET = timezone(timedelta(hours=1))

NEW_COLUMN_SQL = "freigabe TEXT NOT NULL DEFAULT 'intern'"
NEEDED_TRIGGERS = ("knowledge_nodes_freigabe_check_bi", "knowledge_nodes_freigabe_check_bu")

TRIGGERS_SQL = """
CREATE TRIGGER IF NOT EXISTS knowledge_nodes_freigabe_check_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.freigabe NOT IN ('offen','intern','gesperrt')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.freigabe unzulaessig: erlaubt sind offen, intern, gesperrt');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_freigabe_check_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.freigabe NOT IN ('offen','intern','gesperrt')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.freigabe unzulaessig: erlaubt sind offen, intern, gesperrt');
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
    stamp = datetime.now(CET).strftime("%Y%m%dT%H%M%S")
    dest = db_path.parent / f"{db_path.name}.bak-{stamp}"
    shutil.copy2(db_path, dest)
    return dest


def _has_column(conn: sqlite3.Connection) -> bool:
    return "freigabe" in {row[1] for row in conn.execute("PRAGMA table_info(knowledge_nodes)")}


def missing_triggers(conn: sqlite3.Connection) -> list[str]:
    existing = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    return [t for t in NEEDED_TRIGGERS if t not in existing]


def exportierbar(nodes: list[dict]) -> list[dict]:
    """Whitelist, nicht Ausschlussliste: nur Knoten mit freigabe='offen'
    kommen durch. Jede Ausschlussliste hat ein Loch -- bei einem
    Wissensspeicher ist dieses Loch personenbezogen (Auftrag S17). Leere
    Eingabe liefert leere Menge, kein Fehler."""
    return [n for n in nodes if n.get("freigabe") == "offen"]


def migrate(db_path: Path, apply: bool) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        before_nodes = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        column_missing = not _has_column(conn)
        triggers_missing = [] if column_missing else missing_triggers(conn)
    finally:
        conn.close()

    result = {
        "vorher_zeilen": before_nodes,
        "spalte_fehlt": column_missing,
        "trigger_fehlen": triggers_missing,
        "backup": None,
        "nachher_zeilen": before_nodes,
    }
    if not (column_missing or triggers_missing) or not apply:
        return result

    backup_path = _backup(db_path)
    result["backup"] = str(backup_path)

    conn = sqlite3.connect(str(db_path))
    try:
        if column_missing:
            conn.execute(f"ALTER TABLE knowledge_nodes ADD COLUMN {NEW_COLUMN_SQL}")
        conn.executescript(TRIGGERS_SQL)
        conn.commit()
        result["nachher_zeilen"] = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
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
    print(f"=== migrate_freigabe ({mode}) ===")
    print(f"vorher: {res['vorher_zeilen']} Knoten, Spalte fehlt: {res['spalte_fehlt']}, "
          f"fehlende Trigger: {res['trigger_fehlen'] or '(keine)'}")
    if res["backup"]:
        print(f"Sicherung: {res['backup']}")
    print(f"nachher: {res['nachher_zeilen']} Knoten")
    return 0


def _selftest() -> int:
    import re as _re
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "brainlehr.db"
        schema_sql = (HERE / "schema.sql").read_text(encoding="utf-8")

        # Freigabe-Block (Spalte + Kommentar) aus dem Schema herausschneiden,
        # damit der Selbsttest gegen den Vorher-Stand rot laufen kann.
        old_schema, n1 = _re.subn(
            r",\n    -- Freigabe \(Planschritt S17\).*?freigabe TEXT NOT NULL DEFAULT 'intern'\n\);",
            "\n);", schema_sql, count=1, flags=_re.DOTALL,
        )
        assert n1 == 1, "Freigabe-Block an knowledge_nodes nicht wie erwartet gefunden"
        old_schema, n2 = _re.subn(
            r"-- Freigabe \(Planschritt S17\): gleiche Bauform wie gattung oben, drei Werte\.\n"
            r"CREATE TRIGGER IF NOT EXISTS knowledge_nodes_freigabe_check_bi.*?END;\n\n"
            r"CREATE TRIGGER IF NOT EXISTS knowledge_nodes_freigabe_check_bu.*?END;\n\n",
            "", old_schema, count=1, flags=_re.DOTALL,
        )
        assert n2 == 1, "Freigabe-Trigger nicht wie erwartet gefunden"
        assert "freigabe" not in old_schema.split("CREATE VIRTUAL TABLE")[0]

        conn = sqlite3.connect(str(db_path))
        conn.executescript(old_schema)
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, "
            "norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
            "VALUES ('n1', '/a', 'shared', 't', 's', 'c', 0, 'selbst beobachtet', "
            "'keine_norm', 'skript:test', 'Testvorrichtung')"
        )
        conn.commit()
        conn.close()

        conn = sqlite3.connect(str(db_path))
        assert not _has_column(conn)
        conn.close()

        # (a) Knoten ohne Angabe bekommt 'intern'.
        res1 = migrate(db_path, apply=True)
        assert res1["backup"] and Path(res1["backup"]).exists()
        assert res1["vorher_zeilen"] == res1["nachher_zeilen"] == 1

        conn = sqlite3.connect(str(db_path))
        rows = dict(conn.execute("SELECT id, freigabe FROM knowledge_nodes").fetchall())
        assert rows == {"n1": "intern"}, rows

        # (b) unzulaessiger Wert wird abgewiesen.
        try:
            conn.execute("UPDATE knowledge_nodes SET freigabe = 'quatsch' WHERE id = 'n1'")
            raised = False
        except sqlite3.IntegrityError:
            raised = True
        assert raised, "unzulaessiger freigabe-Wert haette abgelehnt werden muessen"

        # gueltige Werte bleiben erlaubt, in beide Richtungen (keine
        # Rueckfall-Sperre wie bei norm_entscheidung).
        conn.execute("UPDATE knowledge_nodes SET freigabe = 'offen' WHERE id = 'n1'")
        conn.execute("UPDATE knowledge_nodes SET freigabe = 'gesperrt' WHERE id = 'n1'")
        conn.execute("UPDATE knowledge_nodes SET freigabe = 'intern' WHERE id = 'n1'")
        conn.commit()
        conn.close()

        # (e) zweiter Lauf: nichts zu tun, keine neue Sicherung -- idempotent.
        res2 = migrate(db_path, apply=True)
        assert res2["spalte_fehlt"] is False
        assert res2["trigger_fehlen"] == []
        assert res2["backup"] is None
        assert res2["vorher_zeilen"] == res2["nachher_zeilen"] == 1

    # (c) exportierbar() liefert bei gemischter Eingabe ausschliesslich die
    # offenen, (d) leere Eingabe liefert leere Menge ohne Fehler.
    gemischt = [
        {"id": "a", "freigabe": "offen"},
        {"id": "b", "freigabe": "intern"},
        {"id": "c", "freigabe": "gesperrt"},
        {"id": "d", "freigabe": "offen"},
    ]
    ergebnis = exportierbar(gemischt)
    assert [n["id"] for n in ergebnis] == ["a", "d"], ergebnis
    assert exportierbar([]) == []

    print("SELFTEST OK: freigabe additiv mit Vorgabe 'intern', Trigger aktiv, "
          "beide Richtungen erlaubt, idempotent, exportierbar() liefert nur 'offen'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
