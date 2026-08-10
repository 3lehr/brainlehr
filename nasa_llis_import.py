#!/usr/bin/env python3
"""nasa_llis_import.py -- Auftrag 2026-08-07: NASA LLIS (llis.csv, MIT-lizenziert
NASADatanauts/llis_topicModel) als eigener Ast in knowledge_nodes einlesen.

Restlos entfernbar: project_id='nasa-llis' + Tag 'nasa-llis-import' an jedem
Eintrag, siehe --delete. Idempotent: id = 'nasa-llis-<LessonId>' (Primary Key),
INSERT OR IGNORE. Kein Eintrag in lessons_learned -- das sind fremde Lehren,
keine eigenen.

Trockenlauf ist Voreinstellung. Embeddings NICHT hier -- eigener Schritt
(build_embeddings.py), vom Hauptfaden angestossen.

Nutzung:
  python3 nasa_llis_import.py --csv /tmp/llis_probe.csv --db knowledge.db          # Trockenlauf
  python3 nasa_llis_import.py --csv /tmp/llis_probe.csv --db knowledge.db --write  # echter Import
  python3 nasa_llis_import.py --db knowledge.db --delete                          # restlos entfernen
  python3 nasa_llis_import.py --selftest
"""
import argparse
import csv
import json
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ID = "nasa-llis"
TAG_IMPORT = "nasa-llis-import"
PARENT_PATH = "/nasa-llis"
CET = timezone(timedelta(hours=1))
SUMMARY_MAXLEN = 500


def now_iso():
    return datetime.now(CET).strftime("%Y-%m-%dT%H:%M:%S+01:00")


def parse_date(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None  # unparsebar -> Rohwert landet stattdessen im content (siehe row_to_node)


def row_to_node(row, ts):
    lesson_id = row["LessonId"].strip()
    title = (row.get("Title") or "").strip() or f"NASA LLIS {lesson_id}"
    abstract = (row.get("Abstract") or "").strip()
    lesson = (row.get("Lesson") or "").strip()
    org = (row.get("Organization") or "").strip()
    url = (row.get("url") or "").strip()
    date_raw = (row.get("LessonDate") or "").strip()
    date_iso = parse_date(date_raw)

    summary = abstract if len(abstract) <= SUMMARY_MAXLEN else abstract[:SUMMARY_MAXLEN].rstrip() + " [...]"
    if not summary:
        summary = title

    content_parts = [f"Datum: {date_iso or date_raw or 'unbekannt'}"]
    if org:
        content_parts.append(f"Organisation: {org}")
    content_parts.append(f"Abstract (Volltext):\n{abstract}")
    content_parts.append(f"Lesson:\n{lesson}")
    content = "\n\n".join(content_parts)

    tags = [t.strip() for t in (row.get("Categories") or "").split(",") if t.strip()]
    tags += [TAG_IMPORT, f"lessonid:{lesson_id}"]
    if org:
        tags.append(f"org:{org}")

    source = f"{url} (NASA LLIS LessonId {lesson_id})" if url else f"NASA LLIS LessonId {lesson_id}"

    return (
        f"nasa-llis-{lesson_id}",           # id (Primary Key -> idempotent)
        f"{PARENT_PATH}/{lesson_id}",        # path (UNIQUE)
        PARENT_PATH,                         # parent_path
        PROJECT_ID,                          # project_id
        title,
        summary,
        content,
        1,                                   # level
        json.dumps(tags, ensure_ascii=False),
        source,
        0.6,                                 # confidence: fremde Sekundaerquelle, keine eigene Verifikation
        ts,
        ts,
        "skript",                            # anlass (CHECK: selbst|betreiber|hook|skript|unbekannt)
        "nasa_llis_import.py",               # actor
    )


INSERT_SQL = """
INSERT OR IGNORE INTO knowledge_nodes
    (id, path, parent_path, project_id, title, summary, content, level, tags,
     source, confidence, created_at, updated_at, anlass, actor,
     norm_entscheidung, norm_entschieden_von, norm_entschieden_grund)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'keine_norm','skript:nasa_llis_import.py',
        'importierte Fremdlehre (NASA LLIS) ist kein Normtext')
"""


def read_rows(csv_path):
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        yield from csv.DictReader(f)


PARENT_NODE = (
    "nasa-llis-root", PARENT_PATH, None, PROJECT_ID,
    "NASA Lessons Learned Information System (Import)",
    "Wurzelknoten fuer importierte NASA-LLIS-Eintraege (llis.csv, NASADatanauts/llis_topicModel, MIT).",
    None, 0, json.dumps([TAG_IMPORT], ensure_ascii=False),
    "https://github.com/NASADatanauts/llis_topicModel data/llis.csv",
    0.6, None, None, "skript", "nasa_llis_import.py",
)


def ensure_parent(conn, ts):
    node = list(PARENT_NODE)
    node[11] = ts
    node[12] = ts
    conn.execute(INSERT_SQL, node)


def run_import(db_path, csv_path, write):
    ts = now_iso()
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    if write:
        ensure_parent(conn, ts)
    before = conn.execute(
        "SELECT COUNT(*) FROM knowledge_nodes WHERE project_id!=?", (PROJECT_ID,)
    ).fetchone()[0]

    inserted = 0
    skipped_dup = 0
    skipped_bad = 0
    for row in read_rows(csv_path):
        if not (row.get("LessonId") or "").strip():
            skipped_bad += 1
            continue
        node = row_to_node(row, ts)
        if write:
            cur = conn.execute(INSERT_SQL, node)
            if cur.rowcount:
                inserted += 1
            else:
                skipped_dup += 1
        else:
            exists = conn.execute(
                "SELECT 1 FROM knowledge_nodes WHERE id=?", (node[0],)
            ).fetchone()
            if exists:
                skipped_dup += 1
            else:
                inserted += 1

    if write:
        conn.commit()
    after = conn.execute(
        "SELECT COUNT(*) FROM knowledge_nodes WHERE project_id!=?", (PROJECT_ID,)
    ).fetchone()[0]
    total_import = conn.execute(
        "SELECT COUNT(*) FROM knowledge_nodes WHERE project_id=?", (PROJECT_ID,)
    ).fetchone()[0]
    conn.close()

    mode = "SCHREIB-LAUF" if write else "TROCKENLAUF"
    print(f"{mode}: {inserted} angelegt/anlegbar, {skipped_dup} uebersprungen (schon vorhanden), "
          f"{skipped_bad} uebersprungen (LessonId fehlt)")
    print(f"Fremdbestand (project_id != '{PROJECT_ID}') vorher: {before}, nachher: {after} "
          f"({'unveraendert' if before == after else 'GEAENDERT -- FEHLER'})")
    print(f"nasa-llis-Knoten gesamt in DB: {total_import}")
    return inserted, skipped_dup, skipped_bad, before, after


def run_delete(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    before_import = conn.execute(
        "SELECT COUNT(*) FROM knowledge_nodes WHERE project_id=?", (PROJECT_ID,)
    ).fetchone()[0]
    before_total = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.execute("DELETE FROM knowledge_nodes WHERE project_id=?", (PROJECT_ID,))
    conn.commit()
    after_total = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()
    print(f"GELOESCHT: {before_import} nasa-llis-Knoten. Bestand gesamt vorher: {before_total}, "
          f"nachher: {after_total}")
    return before_import, before_total, after_total


def selftest():
    import tempfile, os, shutil

    schema_src = Path(__file__).parent / "schema.sql"
    tmpdir = tempfile.mkdtemp()
    db = Path(tmpdir) / "t.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(schema_src.read_text())
    conn.close()

    csv_content = (
        "LessonId,Submitter1,Title,Abstract,Lesson,Organization,LessonDate,"
        "MissionDirectorate,SafetyIssue,Categories,DocNum,Topic,Category,url\n"
        '1,A,"Titel 1","Abstract eins","Lesson eins",KSC,6/6/14,,TRUE,'
        '"Energy, Facilities",1,1,Energy,https://example.org/1\n'
        '2,B,"Titel 2","Abstract zwei","Lesson zwei",JSC,,,FALSE,,2,2,NA,\n'
    )
    csv_path = Path(tmpdir) / "t.csv"
    csv_path.write_text(csv_content, encoding="utf-8")

    # anderer Bestand bleibt unangetastet
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, source, "
        "norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
        "VALUES ('x1','/shared/x1','shared','X','x','selftest','keine_norm','skript:test','Testvorrichtung')"
    )
    conn.commit()
    conn.close()

    ins, dup, bad, before, after = run_import(db, csv_path, write=True)
    assert ins == 2 and dup == 0 and bad == 0, (ins, dup, bad)
    assert before == 1 and after == 1, (before, after)

    ins2, dup2, bad2, before2, after2 = run_import(db, csv_path, write=True)
    assert ins2 == 0 and dup2 == 2, (ins2, dup2)

    conn = sqlite3.connect(str(db))
    row = conn.execute(
        "SELECT title, summary, content, tags, source FROM knowledge_nodes WHERE id='nasa-llis-1'"
    ).fetchone()
    conn.close()
    assert row[0] == "Titel 1"
    assert "Abstract eins" in row[1]
    assert "Abstract eins" in row[2] and "Lesson eins" in row[2]
    assert "nasa-llis-import" in row[3]
    assert "example.org/1" in row[4]

    before_imp, before_tot, after_tot = run_delete(db)
    assert before_imp == 3 and after_tot == before_tot - 3, (before_imp, before_tot, after_tot)  # +1 Wurzelknoten

    conn = sqlite3.connect(str(db))
    remaining = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    assert remaining == 1
    conn.close()

    shutil.rmtree(tmpdir)
    print("SELFTEST OK: Import, Idempotenz, Feldzuordnung, Loeschung, Fremdbestand unangetastet.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="/tmp/llis_probe.csv")
    ap.add_argument("--db", default=str(Path(__file__).parent.parent / "knowledge.db"))
    ap.add_argument("--write", action="store_true", help="echt schreiben (sonst Trockenlauf)")
    ap.add_argument("--delete", action="store_true", help="alle nasa-llis-Knoten restlos entfernen")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return
    if args.delete:
        run_delete(args.db)
        return
    run_import(args.db, args.csv, args.write)


if __name__ == "__main__":
    sys.exit(main())
