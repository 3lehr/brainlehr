#!/usr/bin/env python3
"""migrate_normfelder.py -- N2 aus docs/PLAN_NORMSCHICHT_2026-08-05.md.

Zieht die Live-DB auf schema.sql nach: drei nullbare Spalten an
knowledge_nodes (norm_rang, gilt_ab, gilt_bis). schema.sql selbst wirkt nur
auf eine neu erstellte Datei (CREATE TABLE IF NOT EXISTS greift bei
vorhandener Tabelle nicht, siehe Lehre L-636a44) -- ohne diesen Lauf bliebe
die Live-DB auf der alten Form, unbemerkt, bis der naechste Schreibzugriff
gegen die fehlende Spalte liefe.

Weg: ALTER TABLE ... ADD COLUMN, kein Neuaufbau. Fuer eine nullbare Spalte
ohne Default-Ausdruck ist das in SQLite ein reiner Metadaten-Schreibvorgang
(keine Tabellenkopie, keine Sperre ueber die volle Zeilenzahl) -- ein
Neuaufbau (CREATE TABLE neu + INSERT INTO ... SELECT + Umbenennen) waere
hier nur zusaetzliches Risiko fuer Trigger/Indizes ohne Gegenwert, da wir
weder eine Spalte umbenennen noch NOT NULL/CHECK nachtragen.

Setzt KEINEN Rang und KEINE Gueltigkeit -- alle drei Felder bleiben nach
diesem Lauf ausnahmslos NULL. Rang vergeben ist N3.

Usage:
    .venv/bin/python shared-knowledge/migrate_normfelder.py [--apply]
    .venv/bin/python shared-knowledge/migrate_normfelder.py --selftest
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
from datetime import datetime
from pathlib import Path

import zeitmarke

HERE = _w
# BEGOD_KNOWLEDGE_DB ueberschreibt den Pfad -- gleiches Muster wie
# knowledge_mcp_server.py::DB_PATH, sonst laesst sich dieses Skript nie gegen
# eine Testkopie fahren, ohne die Produktiv-DB anzufassen.
DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (HERE / "brainlehr.db"))

NEW_COLUMNS = {
    "norm_rang": "INTEGER",
    "gilt_ab": "TEXT",
    "gilt_bis": "TEXT",
}


def _backup(db_path: Path) -> Path:
    """Gleiches Namensschema wie build_embeddings.py::_backup() -- ein
    Blick ins Verzeichnis findet beide Sorten Sicherung gleich wieder.

    Checkpoint vor dem Kopieren, Befund 2026-08-05: die Live-DB laeuft im
    WAL-Modus, ein reiner shutil.copy2 der Hauptdatei laesst committete, aber
    noch nicht zurueckgeschriebene Aenderungen im WAL-Journal zurueck --
    beobachtet an drei .bak-Dateien vom selben Tag, in denen die neu
    angelegte Spalte norm_rang fehlte, obwohl die Live-DB sie laengst hatte
    (eine davon entstand sogar NACH der Migration). TRUNCATE checkpointed
    und leert die WAL-Datei; ist ein anderer Prozess busy und der Checkpoint
    bleibt unvollstaendig, wird abgebrochen statt eine unvollstaendige Kopie
    anzulegen (siehe RuntimeError unten)."""
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


def _row_checksum(conn: sqlite3.Connection) -> str:
    """Pruefsumme ueber den fachlichen Inhalt (nicht die neuen, ohnehin
    leeren Normfelder) -- muss vor/nach der Migration identisch sein.
    Gleiche Methode wie build_embeddings.py::_checksum()."""
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


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def missing_columns(conn: sqlite3.Connection) -> list[str]:
    have = {row[1] for row in conn.execute("PRAGMA table_info(knowledge_nodes)")}
    return [c for c in NEW_COLUMNS if c not in have]


def migrate(db_path: Path, apply: bool) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        before_cols = [r[1] for r in conn.execute("PRAGMA table_info(knowledge_nodes)")]
        before_count = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        to_add = missing_columns(conn)
        checksum_before = _row_checksum(conn)
    finally:
        conn.close()

    result = {
        "vorher_spalten": before_cols,
        "vorher_zeilen": before_count,
        "geplant": to_add,
        "backup": None,
        "nachher_spalten": before_cols,
        "nachher_zeilen": before_count,
        "checksum_vorher": checksum_before,
        "checksum_nachher": checksum_before,
    }
    if not to_add or not apply:
        return result

    backup_path = _backup(db_path)
    result["backup"] = str(backup_path)

    conn = sqlite3.connect(str(db_path))
    try:
        for col in to_add:
            conn.execute(f"ALTER TABLE knowledge_nodes ADD COLUMN {col} {NEW_COLUMNS[col]}")
        conn.commit()
        result["nachher_spalten"] = [r[1] for r in conn.execute("PRAGMA table_info(knowledge_nodes)")]
        result["nachher_zeilen"] = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
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

    sha_before = _file_sha256(DB_PATH)
    res = migrate(DB_PATH, apply=apply)
    mode = "APPLY" if apply else "DRY-RUN (kein --apply)"
    print(f"=== migrate_normfelder ({mode}) ===")
    print(f"vorher: {len(res['vorher_spalten'])} Spalten, {res['vorher_zeilen']} Zeilen")
    print(f"fehlende Normspalten: {res['geplant'] or '(keine -- bereits migriert)'}")
    if res["backup"]:
        print(f"Sicherung: {res['backup']}")
    print(f"nachher: {len(res['nachher_spalten'])} Spalten, {res['nachher_zeilen']} Zeilen")
    print(f"Pruefsumme Bestandsdaten vorher={res['checksum_vorher'][:16]} "
          f"nachher={res['checksum_nachher'][:16]} "
          f"({'gleich' if res['checksum_vorher'] == res['checksum_nachher'] else 'GEAENDERT -- FEHLER'})")
    if apply:
        sha_after = _file_sha256(DB_PATH)
        print(f"sha256 Datei vorher={sha_before[:16]} nachher={sha_after[:16]} "
              f"(Aenderung durch neue Spalten in der Dateistruktur erwartet, "
              f"die Pruefsumme oben belegt den fachlichen Inhalt)")
    return 0


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "brainlehr.db"
        schema_sql = (HERE / "schema.sql").read_text(encoding="utf-8")
        # Alte Form simulieren: Tabelle OHNE die drei neuen Spalten anlegen,
        # wie es eine echte Alt-DB vor N2 waere -- der Normschicht-Block
        # (Kommentar + norm_rang/gilt_ab/gilt_bis) wird herausgeschnitten,
        # das letzte verbleibende Feld verliert sein Komma vorm Tabellenschluss.
        import re as _re
        old_schema, n = _re.subn(
            r",\n    -- Normschicht \(N2.*?-- NULL = unbefristet in Kraft\n\);",
            "\n);", schema_sql, flags=_re.DOTALL,
        )
        assert n == 1, "Normschicht-Block im schema.sql nicht wie erwartet gefunden"
        for col in NEW_COLUMNS:
            assert col not in old_schema.split("CREATE VIRTUAL TABLE")[0], f"{col} noch in simuliertem Alt-Schema"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(old_schema)
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level) "
            "VALUES ('n1', '/x', 'shared', 'Titel', 'Summary', 'Inhalt', 0)"
        )
        conn.commit()
        conn.close()

        # Vorher: Spalten fehlen.
        conn = sqlite3.connect(str(db_path))
        before = missing_columns(conn)
        conn.close()
        assert set(before) == set(NEW_COLUMNS), before

        res1 = migrate(db_path, apply=True)
        assert res1["backup"] and Path(res1["backup"]).exists()
        assert set(NEW_COLUMNS) <= set(res1["nachher_spalten"])
        assert res1["vorher_zeilen"] == res1["nachher_zeilen"] == 1
        assert res1["checksum_vorher"] == res1["checksum_nachher"]

        conn = sqlite3.connect(str(db_path))
        row = conn.execute("SELECT norm_rang, gilt_ab, gilt_bis FROM knowledge_nodes WHERE id='n1'").fetchone()
        conn.close()
        assert row == (None, None, None), row

        # Zweiter Lauf: nichts zu tun, keine neue Sicherung.
        res2 = migrate(db_path, apply=True)
        assert res2["geplant"] == [], res2["geplant"]
        assert res2["backup"] is None

    print("SELFTEST OK: ALTER TABLE additiv, idempotent, Bestandsdaten unveraendert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
