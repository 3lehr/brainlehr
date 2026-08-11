#!/usr/bin/env python3
"""migrate_gattung.py -- Auftrag S1b (docs/PLAN_DESTILLE_2026-08-09.md).

Zieht die Live-DB auf schema.sql nach (Vorbild migrate_anlass.py/
migrate_source_constraints.py, additive ALTER TABLE + BEFORE-Trigger --
SQLite kennt kein nachtraegliches CHECK, s. schema.sql-Kommentar):

1. Spalte knowledge_nodes.gattung (NOT NULL DEFAULT 'arbeitsbestand', SQLite
   fuellt jede Bestandszeile automatisch beim ALTER TABLE).
2. Zwei Werte-Trigger (bi/bu), gleiche Bauform wie anlass.
3. Einordnung der NASA-LLIS-Sammlung als 'nachschlagewerk'.

ERKENNUNGSREGEL, und warum: (source LIKE '%nen.nasa.gov%' OR source LIKE
'%llis.csv%') UND anlass='skript' -- source traegt das Merkmal, an dem sich
das WERK selbst zeigt (Herkunfts-URL/Dateiname des Datensatzes), nicht der
Ort, an den es einsortiert wurde. Ein Pfadpraefix ('/nasa-llis%') waere
zerbrechlicher: er bricht, sobald jemand die Knoten verschiebt oder umbenennt,
waehrend source unveraenderlich ist (schema.sql, Auditkette).

source ALLEIN reicht nicht: erster Lauf traf 1639 statt der gemessenen 1638
-- der Ausreisser (Knoten 096669de, '/brainlehr/fremder-pruefkorpus-
gefunden-1637-nasa', anlass='betreiber') ist eine EIGENE Notiz UEBER den
Fund der NASA-Sammlung, deren source-Feld die llis.csv nur ERWAEHNT, ohne
dass ihr Inhalt daraus stammt -- kein Nachschlagewerk, sondern Arbeitsbestand
mit einem Zitat darin. anlass='skript' UNTERSCHEIDET genau das: es markiert,
dass der INHALT automatisiert aus dem Datensatz erzeugt wurde (nasa_llis_
import.py), nicht dass jemand ihn erwaehnt. Umgekehrt waere anlass='skript'
allein zu grob: 1640 Zeilen tragen ihn, zwei davon sind fachfremde
Stadtwerke-Testdaten (Knoten d4dc4599, 4c8edf7f) -- kein Nachschlagewerk, nur
ein anderer automatischer Ursprung. Erst UND beider Merkmale trifft genau
die 1638 gemessenen NASA-Datensatz-Knoten, 0 Differenz in beide Richtungen.

Usage:
    .venv/bin/python shared-knowledge/migrate_gattung.py [--apply]
    .venv/bin/python shared-knowledge/migrate_gattung.py --selftest
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (HERE / "brainlehr.db"))
CET = timezone(timedelta(hours=1))

NEW_COLUMN_SQL = "gattung TEXT NOT NULL DEFAULT 'arbeitsbestand'"
NEEDED_TRIGGERS = ("knowledge_nodes_gattung_check_bi", "knowledge_nodes_gattung_check_bu")

TRIGGERS_SQL = """
CREATE TRIGGER IF NOT EXISTS knowledge_nodes_gattung_check_bi
BEFORE INSERT ON knowledge_nodes
FOR EACH ROW WHEN NEW.gattung NOT IN ('arbeitsbestand','nachschlagewerk')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.gattung unzulaessig: erlaubt sind arbeitsbestand, nachschlagewerk');
END;

CREATE TRIGGER IF NOT EXISTS knowledge_nodes_gattung_check_bu
BEFORE UPDATE ON knowledge_nodes
FOR EACH ROW WHEN NEW.gattung NOT IN ('arbeitsbestand','nachschlagewerk')
BEGIN
    SELECT RAISE(ABORT, 'knowledge_nodes.gattung unzulaessig: erlaubt sind arbeitsbestand, nachschlagewerk');
END;
"""

# Erkennungsregel fuer die NASA-LLIS-Sammlung, s. Moduldoc oben.
NACHSCHLAGEWERK_WHERE = "(source LIKE '%nen.nasa.gov%' OR source LIKE '%llis.csv%') AND anlass = 'skript'"


def _backup(db_path: Path) -> Path:
    """Gleiches Muster wie migrate_anlass.py -- Checkpoint vor dem Kopieren,
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
    return "gattung" in {row[1] for row in conn.execute("PRAGMA table_info(knowledge_nodes)")}


def missing_triggers(conn: sqlite3.Connection) -> list[str]:
    existing = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    return [t for t in NEEDED_TRIGGERS if t not in existing]


def migrate(db_path: Path, apply: bool) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        before_nodes = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        column_missing = not _has_column(conn)
        triggers_missing = [] if column_missing else missing_triggers(conn)
        kandidaten_vorher = conn.execute(
            f"SELECT COUNT(*) FROM knowledge_nodes WHERE {NACHSCHLAGEWERK_WHERE}"
        ).fetchone()[0]
    finally:
        conn.close()

    result = {
        "vorher_zeilen": before_nodes,
        "spalte_fehlt": column_missing,
        "trigger_fehlen": triggers_missing,
        "kandidaten": kandidaten_vorher,
        "backup": None,
        "als_nachschlagewerk_markiert": None,
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
        cur = conn.execute(
            f"UPDATE knowledge_nodes SET gattung = 'nachschlagewerk' "
            f"WHERE {NACHSCHLAGEWERK_WHERE} AND gattung != 'nachschlagewerk'"
        )
        result["als_nachschlagewerk_markiert"] = cur.rowcount
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
    print(f"=== migrate_gattung ({mode}) ===")
    print(f"vorher: {res['vorher_zeilen']} Knoten, Spalte fehlt: {res['spalte_fehlt']}, "
          f"fehlende Trigger: {res['trigger_fehlen'] or '(keine)'}")
    print(f"Kandidaten (Erkennungsregel trifft): {res['kandidaten']}")
    if res["backup"]:
        print(f"Sicherung: {res['backup']}")
    if res["als_nachschlagewerk_markiert"] is not None:
        print(f"gattung='nachschlagewerk' gesetzt bei: {res['als_nachschlagewerk_markiert']} Knoten")
    print(f"nachher: {res['nachher_zeilen']} Knoten")
    return 0


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "brainlehr.db"
        schema_sql = (HERE / "schema.sql").read_text(encoding="utf-8")

        import re as _re
        old_schema, n1 = _re.subn(
            r",\n    -- Gattung \(Auftrag S1b.*?gattung TEXT NOT NULL DEFAULT 'arbeitsbestand'\n\);",
            "\n);", schema_sql, count=1, flags=_re.DOTALL,
        )
        assert n1 == 1, "Gattung-Block an knowledge_nodes nicht wie erwartet gefunden"
        old_schema = old_schema.replace(
            "-- Gattung (Auftrag S1b): gleiche Bauform wie anlass oben, zwei Werte.\n", ""
        )
        old_schema, n2 = _re.subn(
            r"CREATE TRIGGER IF NOT EXISTS knowledge_nodes_gattung_check_bi.*?END;\n\n"
            r"CREATE TRIGGER IF NOT EXISTS knowledge_nodes_gattung_check_bu.*?END;\n\n",
            "", old_schema, count=1, flags=_re.DOTALL,
        )
        assert n2 == 1, "Gattung-Trigger nicht wie erwartet gefunden"
        assert "gattung" not in old_schema.split("CREATE VIRTUAL TABLE")[0]

        conn = sqlite3.connect(str(db_path))
        conn.executescript(old_schema)
        # n1: echter NASA-Datensatz-Knoten (anlass='skript') -> nachschlagewerk.
        # n2: normaler eigener Knoten -> arbeitsbestand.
        # n3: EIGENE Notiz, die llis.csv nur ERWAEHNT (anlass='betreiber') --
        #     der Ausreisser aus dem ersten echten Lauf (1639 statt 1638,
        #     Knoten 096669de), muss arbeitsbestand BLEIBEN.
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, "
            "anlass, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
            "VALUES ('n1', '/nasa-llis/x', 'shared', 't', 's', 'c', 0, "
            "'https://nen.nasa.gov/web/11/viewall/-/viewall/1 (NASA LLIS LessonId 1)', "
            "'skript', 'keine_norm', 'skript:test', 'Testvorrichtung')"
        )
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, "
            "norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
            "VALUES ('n2', '/eigenes', 'shared', 't', 's', 'c', 0, 'selbst beobachtet', "
            "'keine_norm', 'skript:test', 'Testvorrichtung')"
        )
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, "
            "anlass, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
            "VALUES ('n3', '/brainlehr/fund-notiz', 'shared', 't', 's', 'c', 0, "
            "'Fund: liegt als data/llis.csv im Repo NASADatanauts/llis_topicModel', "
            "'betreiber', 'keine_norm', 'betreiber', 'Testvorrichtung')"
        )
        conn.commit()
        conn.close()

        conn = sqlite3.connect(str(db_path))
        assert not _has_column(conn)
        conn.close()

        res1 = migrate(db_path, apply=True)
        assert res1["backup"] and Path(res1["backup"]).exists()
        assert res1["vorher_zeilen"] == res1["nachher_zeilen"] == 3
        assert res1["kandidaten"] == 1
        assert res1["als_nachschlagewerk_markiert"] == 1

        conn = sqlite3.connect(str(db_path))
        rows = dict(conn.execute("SELECT id, gattung FROM knowledge_nodes").fetchall())
        assert rows == {"n1": "nachschlagewerk", "n2": "arbeitsbestand", "n3": "arbeitsbestand"}, rows
        # Trigger aktiv: unzulaessiger Wert wird abgelehnt.
        try:
            conn.execute("UPDATE knowledge_nodes SET gattung = 'quatsch' WHERE id = 'n2'")
            raised = False
        except sqlite3.IntegrityError:
            raised = True
        assert raised, "unzulaessiger gattung-Wert haette abgelehnt werden muessen"
        conn.close()

        # Zweiter Lauf: nichts zu tun, keine neue Sicherung.
        res2 = migrate(db_path, apply=True)
        assert res2["spalte_fehlt"] is False
        assert res2["trigger_fehlen"] == []
        assert res2["backup"] is None

    print("SELFTEST OK: gattung additiv, NASA-Kandidat korrekt erkannt, "
          "normaler Knoten unberuehrt, Trigger aktiv, idempotent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
