#!/usr/bin/env python3
"""fix_namensraum_knoten.py — legt fehlende Namensraum-Knoten in
knowledge_nodes an (Vorbereitung fuer P1: parent_path-Validierung in
knowledge_mcp_server.py).

Ermittelt selbst, welche parent_path-Werte in knowledge_nodes referenziert
werden, aber selbst keinen Knoten haben (Baum hat Loecher), und legt sie
rekursiv an -- fehlt /shared/arch, muss auch /shared zuerst existieren.
"/" ist die Wurzel und bekommt keinen Knoten.

Nur INSERT der fehlenden Namensraum-Knoten. Keine bestehende Zeile wird
angefasst.

Usage:
    .venv/bin/python shared-knowledge/fix_namensraum_knoten.py            # dry-run (Vorgabe)
    .venv/bin/python shared-knowledge/fix_namensraum_knoten.py --apply    # schreibt
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

import shutil
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DB_PATH = _w / "knowledge.db"
BERLIN = ZoneInfo("Europe/Berlin")
SOURCE = "fix_namensraum_knoten.py 2026-08-05"


def now_iso() -> str:
    return datetime.now(BERLIN).isoformat(timespec="seconds")


def _backup() -> Path:
    """Checkpoint vor dem Kopieren, Befund 2026-08-05: die Live-DB laeuft im
    WAL-Modus, ein reiner shutil.copy2 der Hauptdatei laesst committete, aber
    noch nicht zurueckgeschriebene Aenderungen im WAL-Journal zurueck --
    beobachtet an drei .bak-Dateien vom selben Tag, in denen die neu
    angelegte Spalte norm_rang fehlte, obwohl die Live-DB sie laengst hatte
    (eine davon entstand sogar NACH der Migration). TRUNCATE checkpointed
    und leert die WAL-Datei; ist ein anderer Prozess busy und der Checkpoint
    bleibt unvollstaendig, wird abgebrochen statt eine unvollstaendige Kopie
    anzulegen (siehe RuntimeError unten)."""
    conn = sqlite3.connect(str(DB_PATH))
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
    stamp = datetime.now(BERLIN).strftime("%Y%m%dT%H%M%S")
    dest = DB_PATH.parent / f"knowledge.db.bak-{stamp}"
    shutil.copy2(DB_PATH, dest)
    return dest


def humanize(segment: str) -> str:
    """Letztes Pfadsegment lesbar machen: 'model-cascade' -> 'Model Cascade'."""
    return " ".join(w.capitalize() for w in segment.replace("-", " ").replace("_", " ").split())


def missing_parent_paths(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        """
        select distinct n.parent_path from knowledge_nodes n
        where n.parent_path is not null and n.parent_path != ''
          and not exists (select 1 from knowledge_nodes p where p.path = n.parent_path)
        """
    ).fetchall()
    return {r[0] for r in rows}


def ancestors(path: str) -> list[str]:
    """Alle Elternpfade von path bis zur Wurzel, root zuerst. '/' wird ausgelassen."""
    parts = [p for p in path.split("/") if p]
    result = []
    for i in range(1, len(parts) + 1):
        result.append("/" + "/".join(parts[:i]))
    return result


def main() -> int:
    apply = "--apply" in sys.argv

    if not DB_PATH.exists():
        print(f"FEHLER: {DB_PATH} nicht gefunden.")
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    count_before = conn.execute("select count(*) from knowledge_nodes").fetchone()[0]
    holes_before = len(missing_parent_paths(conn))

    # rekursiver Abschluss: fuer jeden fehlenden Elternpfad auch dessen Vorfahren sammeln
    referenced_parents = missing_parent_paths(conn)
    existing_paths = {r[0] for r in conn.execute("select path from knowledge_nodes")}

    to_create: dict[str, dict] = {}  # path -> node dict, insert-order = Tiefe aufsteigend
    frontier = set(referenced_parents)
    all_needed: set[str] = set()
    while frontier:
        next_frontier = set()
        for path in frontier:
            if path == "/" or path in existing_paths or path in all_needed:
                continue
            all_needed.add(path)
            for anc in ancestors(path)[:-1]:  # alle Vorfahren ausser path selbst
                if anc not in existing_paths and anc not in all_needed:
                    next_frontier.add(anc)
        frontier = next_frontier - all_needed

    # Kinderzahl je fehlendem Namensraum-Knoten (nur direkte Kinder in
    # knowledge_nodes, egal ob deren parent selbst fehlt oder existiert)
    child_counts: dict[str, int] = {}
    for row in conn.execute("select parent_path, count(*) c from knowledge_nodes group by parent_path"):
        if row["parent_path"]:
            child_counts[row["parent_path"]] = row["c"]

    # sortiert nach Tiefe aufsteigend, damit Eltern vor Kindern angelegt werden
    ordered = sorted(all_needed, key=lambda p: p.count("/"))

    for path in ordered:
        parts = [p for p in path.split("/") if p]
        parent = "/" + "/".join(parts[:-1]) if len(parts) > 1 else "/"
        if parent == "/":
            parent_path = None  # Wurzel hat keinen eigenen Knoten -> top-level Namensraum
        else:
            parent_path = parent
        level = path.count("/") - 1 if path != "/" else 0
        title = humanize(parts[-1])
        n_children = child_counts.get(path, 0)
        summary = f"Namensraum-Knoten fuer {path} — traegt {n_children} direkte Kind-Knoten in knowledge_nodes."
        to_create[path] = {
            "id": str(uuid.uuid4())[:8],
            "path": path,
            "parent_path": parent_path,
            "title": title,
            "summary": summary,
            "level": level,
            "project_id": "shared",
            "source": SOURCE,
        }

    print(f"Bestand vorher: {count_before} Knoten, {holes_before} Loecher (parent_path ohne Knoten).")
    print(f"Direkt fehlende Elternpfade: {len(referenced_parents)}. Rekursiv (inkl. Vorfahren) anzulegen: {len(to_create)}.")
    for path in ordered:
        n = to_create[path]
        print(f"  {'[NEU]' if apply else '[DRY]'} {path}  parent={n['parent_path']}  level={n['level']}  title={n['title']!r}  children={n['summary'].split('—')[1].strip()}")

    if not apply:
        print("\n--dry-run (Vorgabe). Zum Schreiben: --apply")
        return 0

    if not to_create:
        print("\nNichts anzulegen.")
        return 0

    backup_path = _backup()
    print(f"\nSicherung: {backup_path}")

    ts = now_iso()
    for path in ordered:
        n = to_create[path]
        conn.execute(
            """
            insert into knowledge_nodes
                (id, path, parent_path, project_id, title, summary, content, level, tags, source, confidence, created_at, updated_at)
            values (?, ?, ?, ?, ?, ?, NULL, ?, '[]', ?, 0.8, ?, ?)
            """,
            (n["id"], n["path"], n["parent_path"], n["project_id"], n["title"], n["summary"], n["level"], n["source"], ts, ts),
        )
    conn.commit()

    count_after = conn.execute("select count(*) from knowledge_nodes").fetchone()[0]
    holes_after = len(missing_parent_paths(conn))
    print(f"Angelegt: {len(to_create)}. Bestand nachher: {count_after} Knoten, {holes_after} Loecher.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
