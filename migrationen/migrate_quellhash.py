#!/usr/bin/env python3
"""migrate_quellhash.py -- Auftrag 2026-08-06 (Betreiber-Idee "Selbstentwertung
statt Beleg", docs/PLAN_NORMSCHICHT_2026-08-05.md als Vorlaeufer-Kontext).

Zwei Schritte, beide idempotent:
1. Spalte quell_hash TEXT additiv an knowledge_nodes (schema.sql wirkt nur
   auf eine neu erstellte Datei, siehe migrate_normfelder.py-Vorbild).
2. Rueckfuellung: fuer die 87 Knoten mit source = "erzeugt aus <Datei>
   (Stand <ISO>)" wird quell_hash NUR gesetzt, wenn die Quelldatei seither
   NICHT veraendert wurde (mtime <= Stand) -- sonst bliebe er NULL und der
   Knoten erschiene als "Quelle geaendert", obwohl wir den heutigen (schon
   veraenderten) Abschnittsinhalt eingetragen haetten. Das wuerde den Befund
   verdecken, den die Messung gerade erst freigelegt hat (14 von 87 mit
   geaenderter Quelle, alle aus derselben CLAUDE.md-Bearbeitung).

mtime ist hier NUR der Ausloeser fuer die einmalige Ruecksicht in die
Vergangenheit -- die laufende Pruefung (knowledge_lint.py Kategorie 11)
vergleicht ausschliesslich Hashes, nie mtime (siehe Auftrag: "Der
Dateizeitstempel taugt als Ausloeser, nicht als Urteil").

Usage:
    .venv/bin/python shared-knowledge/migrate_quellhash.py [--apply]
    .venv/bin/python shared-knowledge/migrate_quellhash.py --selftest
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
sys.path.insert(0, str(HERE))
import normbestand  # noqa: E402  (parse_source, abschnitt_hash, current_section_body)

# BEGOD_KNOWLEDGE_DB ueberschreibt den Pfad -- gleiches Muster wie
# knowledge_mcp_server.py::DB_PATH, sonst laesst sich dieses Skript nie gegen
# eine Testkopie fahren, ohne die Produktiv-DB anzufassen.
DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (HERE / "knowledge.db"))
CET = timezone(timedelta(hours=1))

NEW_COLUMNS = {"quell_hash": "TEXT"}


def _backup(db_path: Path) -> Path:
    """Identisches Muster wie migrate_normfelder.py::_backup() /
    build_embeddings.py::_backup() -- Checkpoint vor dem Kopieren, sonst
    fehlen committete, aber noch nicht zurueckgeschriebene WAL-Aenderungen
    in der Sicherung (Befund 2026-08-05)."""
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
    Inhaltsfelder ab, nicht die neue (bzw. hier: die betroffene) Spalte."""
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


def missing_columns(conn: sqlite3.Connection) -> list[str]:
    have = {row[1] for row in conn.execute("PRAGMA table_info(knowledge_nodes)")}
    return [c for c in NEW_COLUMNS if c not in have]


def add_columns(db_path: Path, apply: bool) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        before_cols = [r[1] for r in conn.execute("PRAGMA table_info(knowledge_nodes)")]
        to_add = missing_columns(conn)
    finally:
        conn.close()
    result = {"vorher_spalten": before_cols, "geplant": to_add, "nachher_spalten": before_cols}
    if not to_add or not apply:
        return result
    conn = sqlite3.connect(str(db_path))
    try:
        for col in to_add:
            conn.execute(f"ALTER TABLE knowledge_nodes ADD COLUMN {col} {NEW_COLUMNS[col]}")
        conn.commit()
        result["nachher_spalten"] = [r[1] for r in conn.execute("PRAGMA table_info(knowledge_nodes)")]
    finally:
        conn.close()
    return result


def _file_unchanged_since(path: Path, stand: str) -> bool | None:
    """True: Datei seither unveraendert (mtime <= Stand). False: veraendert.
    None: Datei fehlt oder Stand nicht parsbar -- beides KEIN 'unveraendert'."""
    if not path.exists():
        return None
    try:
        stand_dt = datetime.fromisoformat(stand.strip())
    except ValueError:
        return None
    mtime_dt = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    if stand_dt.tzinfo is None:
        stand_dt = stand_dt.replace(tzinfo=timezone.utc)
    return mtime_dt <= stand_dt


def backfill(db_path: Path, apply: bool) -> dict:
    """Setzt quell_hash nur fuer Knoten, deren Quelldatei seit dem im
    source-Feld vermerkten Stand nachweislich unveraendert ist. Nutzt
    normbestand.py::parse_source/current_section_body/abschnitt_hash --
    dasselbe Verfahren wie knowledge_lint.py Kategorie 11, keine zweite
    Fassung."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, path, title, source FROM knowledge_nodes "
            "WHERE source IS NOT NULL AND quell_hash IS NULL"
        ).fetchall()
    finally:
        conn.close()

    gesetzt: list[str] = []
    quelle_geaendert: list[str] = []  # Datei seither veraendert -> bleibt NULL
    kein_verweis: list[str] = []      # source passt nicht auf das Muster
    ohne_abschnitt: list[str] = []    # Datei unveraendert, Abschnitt aber nicht (mehr) gefunden
    updates: list[tuple[str, str]] = []

    for r in rows:
        ref = normbestand.parse_source(r["source"])
        if ref is None:
            kein_verweis.append(r["path"])
            continue
        path, stand = ref
        unchanged = _file_unchanged_since(path, stand)
        if not unchanged:  # False oder None (fehlend/unparsbar) -> nicht rueckfuellen
            quelle_geaendert.append(r["path"])
            continue
        body = normbestand.current_section_body(path, r["title"])
        if body is None:
            ohne_abschnitt.append(r["path"])
            continue
        h = normbestand.abschnitt_hash(body)
        updates.append((h, r["id"]))
        gesetzt.append(r["path"])

    if apply and updates:
        conn = sqlite3.connect(str(db_path))
        try:
            conn.executemany("UPDATE knowledge_nodes SET quell_hash = ? WHERE id = ?", updates)
            conn.commit()
        finally:
            conn.close()

    return {
        "kandidaten": len(rows),
        "gesetzt": gesetzt,
        "quelle_geaendert": quelle_geaendert,
        "kein_verweis": kein_verweis,
        "ohne_abschnitt": ohne_abschnitt,
    }


def migrate(db_path: Path, apply: bool) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        before_count = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        checksum_before = _row_checksum(conn)
    finally:
        conn.close()

    cols = add_columns(db_path, apply=False)
    result = {
        "vorher_spalten": cols["vorher_spalten"],
        "vorher_zeilen": before_count,
        "geplant_spalten": cols["geplant"],
        "backup": None,
        "nachher_spalten": cols["vorher_spalten"],
        "nachher_zeilen": before_count,
        "checksum_vorher": checksum_before,
        "checksum_nachher": checksum_before,
        "backfill": None,
    }
    if not apply:
        return result

    need_backup = bool(cols["geplant"])
    if need_backup:
        result["backup"] = str(_backup(db_path))
        add_columns(db_path, apply=True)

    result["backfill"] = backfill(db_path, apply=True)

    conn = sqlite3.connect(str(db_path))
    try:
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

    res = migrate(DB_PATH, apply=apply)
    mode = "APPLY" if apply else "DRY-RUN (kein --apply)"
    print(f"=== migrate_quellhash ({mode}) ===")
    print(f"vorher: {len(res['vorher_spalten'])} Spalten, {res['vorher_zeilen']} Zeilen")
    print(f"fehlende Spalten: {res['geplant_spalten'] or '(keine -- bereits migriert)'}")
    if res["backup"]:
        print(f"Sicherung: {res['backup']}")
    print(f"nachher: {len(res['nachher_spalten'])} Spalten, {res['nachher_zeilen']} Zeilen")
    print(f"Pruefsumme Bestandsdaten vorher={res['checksum_vorher'][:16]} "
          f"nachher={res['checksum_nachher'][:16]} "
          f"({'gleich' if res['checksum_vorher'] == res['checksum_nachher'] else 'GEAENDERT -- FEHLER'})")
    if res["backfill"] is not None:
        bf = res["backfill"]
        print(f"Rueckfuellung: {len(bf['gesetzt'])} gesetzt, "
              f"{len(bf['quelle_geaendert'])} Quelle seither geaendert (bleibt NULL), "
              f"{len(bf['ohne_abschnitt'])} Abschnitt nicht gefunden (bleibt NULL), "
              f"{len(bf['kein_verweis'])} ohne Dateibezug (bleibt NULL)")
    return 0


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "knowledge.db"
        schema_sql = (HERE / "schema.sql").read_text(encoding="utf-8")

        # Alte Form simulieren: Tabelle OHNE quell_hash, wie eine echte
        # Alt-DB vor diesem Auftrag.
        import re as _re
        old_schema, n = _re.subn(
            r",(\s*-- NULL = unbefristet in Kraft\n)    -- Quellhash \(Auftrag.*?nur Abwesenheit einer Aussage\.\n    quell_hash TEXT\n\);",
            r"\1);", schema_sql, flags=_re.DOTALL,
        )
        assert n == 1, "Quellhash-Block im schema.sql nicht wie erwartet gefunden"
        assert "quell_hash" not in old_schema.split("CREATE VIRTUAL TABLE")[0]

        conn = sqlite3.connect(str(db_path))
        conn.executescript(old_schema)
        conn.commit()
        conn.close()

        quelle_datei = tmp_path / "quelle.md"
        stand_alt = "2026-08-01T10:00:00+02:00"
        quelle_datei.write_text(
            "# Datei\n\n## Abschnitt A\n\nText A, unveraendert.\n\n"
            "## Abschnitt B\n\nText B, wird gleich geaendert.\n",
            encoding="utf-8",
        )
        # mtime der Datei auf VOR den Stand setzen -> gilt als unveraendert.
        import os
        alt_ts = datetime.fromisoformat(stand_alt).timestamp() - 3600
        os.utime(quelle_datei, (alt_ts, alt_ts))

        now = "2026-08-05T10:00:00+02:00"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """INSERT INTO knowledge_nodes
               (id, path, parent_path, project_id, title, summary, content, level, tags, source, created_at, updated_at)
               VALUES ('n_a', '/methodik/direktiven/abschnitt-a', '/methodik/direktiven', 'shared',
                       'Abschnitt A', 'x', 'x', 3, '[]', ?, ?, ?)""",
            (f"erzeugt aus {quelle_datei} (Stand {stand_alt})", now, now),
        )
        conn.execute(
            """INSERT INTO knowledge_nodes
               (id, path, parent_path, project_id, title, summary, content, level, tags, source, created_at, updated_at)
               VALUES ('n_b', '/methodik/direktiven/abschnitt-b', '/methodik/direktiven', 'shared',
                       'Abschnitt B', 'x', 'x', 3, '[]', ?, ?, ?)""",
            (f"erzeugt aus {quelle_datei} (Stand {stand_alt})", now, now),
        )
        # Knoten ohne Dateibezug -- Gegenprobe, darf nie in einer Liste
        # auftauchen ausser 'kein_verweis'.
        conn.execute(
            """INSERT INTO knowledge_nodes
               (id, path, parent_path, project_id, title, summary, content, level, tags, source, created_at, updated_at)
               VALUES ('n_c', '/methodik/sonst', '/methodik', 'shared', 'Sonst', 'x', 'x', 2, '[]',
                       'Konsil 2026-08-05', ?, ?)""",
            (now, now),
        )
        conn.commit()
        conn.close()

        # 1. Spalten fehlen vorher.
        conn = sqlite3.connect(str(db_path))
        before = missing_columns(conn)
        conn.close()
        assert set(before) == set(NEW_COLUMNS), before

        res1 = migrate(db_path, apply=True)
        assert res1["backup"] and Path(res1["backup"]).exists()
        assert set(NEW_COLUMNS) <= set(res1["nachher_spalten"])
        assert res1["vorher_zeilen"] == res1["nachher_zeilen"] == 3
        assert res1["checksum_vorher"] == res1["checksum_nachher"]

        # 2. Rueckfuellung: beide Datei-Knoten unveraendert -> Hash gesetzt,
        # weil die Datei zum Stand-Zeitpunkt so aussah. Sonst-Knoten bleibt
        # aussen vor (kein_verweis).
        bf1 = res1["backfill"]
        assert set(bf1["gesetzt"]) == {"/methodik/direktiven/abschnitt-a", "/methodik/direktiven/abschnitt-b"}, bf1
        assert bf1["kein_verweis"] == ["/methodik/sonst"], bf1
        assert bf1["quelle_geaendert"] == [] and bf1["ohne_abschnitt"] == []

        conn = sqlite3.connect(str(db_path))
        row_a = conn.execute("SELECT quell_hash FROM knowledge_nodes WHERE id='n_a'").fetchone()
        row_c = conn.execute("SELECT quell_hash FROM knowledge_nodes WHERE id='n_c'").fetchone()
        conn.close()
        assert row_a[0] is not None
        assert row_c[0] is None  # kein Dateibezug -> nie gesetzt

        # 3. Zweiter Lauf: Spalte existiert schon -> keine neue Sicherung,
        # kein Kandidat mehr uebrig (quell_hash schon gesetzt bzw. NULL ohne
        # Dateibezug -> WHERE quell_hash IS NULL traf n_c erneut, aber ohne
        # Dateibezug bleibt es dabei -- kein neuer Zustand, kein Fehler).
        res2 = migrate(db_path, apply=True)
        assert res2["backup"] is None, res2["backup"]
        assert res2["backfill"]["gesetzt"] == [], res2["backfill"]

        # 4. Jetzt die Datei WIRKLICH aendern (Abschnitt B) und mtime nach
        # dem Stand setzen -- ein DRITTER Knoten mit gleichem Muster, aber
        # noch ohne Hash, muss NICHT rueckgefuellt werden (das ist die
        # Falle aus dem Auftrag: sonst wuerde der heutige, schon veraenderte
        # Inhalt faelschlich als "damals gueltig" eingetragen).
        quelle_datei.write_text(
            "# Datei\n\n## Abschnitt A\n\nText A, unveraendert.\n\n"
            "## Abschnitt B\n\nText B, WURDE GEAENDERT.\n",
            encoding="utf-8",
        )
        neu_ts = datetime.fromisoformat(stand_alt).timestamp() + 3600
        os.utime(quelle_datei, (neu_ts, neu_ts))
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """INSERT INTO knowledge_nodes
               (id, path, parent_path, project_id, title, summary, content, level, tags, source, created_at, updated_at)
               VALUES ('n_d', '/methodik/direktiven/abschnitt-b-2', '/methodik/direktiven', 'shared',
                       'Abschnitt B', 'x', 'x', 3, '[]', ?, ?, ?)""",
            (f"erzeugt aus {quelle_datei} (Stand {stand_alt})", now, now),
        )
        conn.commit()
        conn.close()

        res3 = migrate(db_path, apply=True)
        assert res3["backfill"]["quelle_geaendert"] == ["/methodik/direktiven/abschnitt-b-2"], res3["backfill"]
        assert res3["backfill"]["gesetzt"] == [], res3["backfill"]

        conn = sqlite3.connect(str(db_path))
        row_d = conn.execute("SELECT quell_hash FROM knowledge_nodes WHERE id='n_d'").fetchone()
        conn.close()
        assert row_d[0] is None, "Quelle seither geaendert -- darf NICHT rueckgefuellt werden"

    print("SELFTEST OK: Spalte additiv, Rueckfuellung nur bei nachweislich unveraenderter Quelle, idempotent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
