#!/usr/bin/env python3
"""build_embeddings.py — expliziter Lauf, der Vektoren fuer den Wissensbestand
erzeugt (knowledge_nodes + lessons_learned) und additiv in
knowledge_embeddings ablegt.

Kein Nebeneffekt von knowledge_add/lesson_record -- nur dieser Aufruf
schreibt Vektoren. Ohne Aufruf bleibt die Suche beim heutigen reinen
FTS5/LIKE-Zustand (siehe embeddings.hybrid_retrieval_weight()-Rollback und
knowledge_mcp_server.py's Fallback bei fehlender Tabelle/Ollama).

Ablauf: Sicherung der DB (gleiche Benennung wie bestehende .bak-Dateien) ->
Pruefsumme der Bestandsdaten -> Tabelle anlegen (additiv, IF NOT EXISTS) ->
je Node/Lesson einbetten -> Pruefsumme erneut, muss identisch sein (keine
Bestandsdaten angefasst).

Usage: .venv/bin/python shared-knowledge/build_embeddings.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import embeddings

DB_PATH = Path(__file__).parent / "knowledge.db"
CET = timezone(timedelta(hours=1))

# project_id additiv (siehe schema.sql-Kommentar bei knowledge_embeddings):
# PRIMARY KEY jetzt (kind, ref_id, project_id), damit eine Suche die
# Kandidatenmenge VOR der Aehnlichkeitsrechnung nach Bereich einschraenken
# kann, statt hinterher zu filtern.
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_embeddings (
    kind TEXT NOT NULL,
    ref_id TEXT NOT NULL,
    project_id TEXT NOT NULL DEFAULT 'shared',
    model TEXT NOT NULL,
    vector BLOB NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (kind, ref_id, project_id)
);
"""


def resolve_lesson_projects(raw: str | None) -> list[str]:
    """lessons_learned.projects (JSON-Array, mehrwertig) -> Liste der Bereiche,
    unter denen die Lehre embedding-seitig auffindbar sein soll (eine
    Embedding-Zeile pro Bereich, gleicher Vektor -- siehe schema.sql).

    Regulaerfall: gueltiges, nicht-leeres JSON-Array wie '["begod","aka"]' ->
    genau diese Bereiche.

    Leeres Array '[]' (2 Faelle im Bestand: L-4ab9b0, L-2f67b2): keine
    Bereichsangabe vorhanden. Bucket 'shared' -- derselbe Vorgabewert wie
    knowledge_nodes.project_id DEFAULT 'shared' -- statt die Lehre embedding-
    seitig unauffindbar zu machen.

    Kaputtes JSON (L-9b3012b6: Rohwert literal 'openlehr', ohne Klammern/
    Anfuehrungszeichen -- wird bewusst NICHT repariert, Pruefall fuer
    Fehlertoleranz laut Auftrag): der Rohstring benennt den Bereich trotzdem
    -- als einzelner Bereich uebernommen, statt die Lehre zu verlieren.

    Alles andere (leer/None/nicht parsbar zu einem brauchbaren String) ->
    Bucket 'shared'."""
    if not raw or not raw.strip():
        return ["shared"]
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list) and parsed:
            return [str(p) for p in parsed]
        return ["shared"]
    except (json.JSONDecodeError, TypeError):
        candidate = raw.strip()
        return [candidate] if candidate else ["shared"]


def now_iso() -> str:
    return datetime.now(CET).strftime("%Y-%m-%dT%H:%M:%S+01:00")


def _checksum(conn: sqlite3.Connection) -> str:
    """Pruefsumme ueber alle Bestandsdaten in knowledge_nodes + lessons_learned
    (Reihenfolge-unabhaengig durch sortierte id). Aendert sich NICHT durch das
    Anlegen/Fuellen von knowledge_embeddings, da dieses Skript beide Tabellen
    nur liest."""
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


def _backup() -> Path:
    stamp = datetime.now(CET).strftime("%Y%m%dT%H%M%S")
    dest = DB_PATH.parent / f"knowledge.db.bak-{stamp}"
    shutil.copy2(DB_PATH, dest)
    return dest


def main() -> int:
    if not DB_PATH.exists():
        print(f"FEHLER: {DB_PATH} nicht gefunden.")
        return 1

    backup_path = _backup()
    print(f"Sicherung: {backup_path}")

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    checksum_before = _checksum(conn)
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()

    # Cold-Start des lokalen Modells kann > 5s dauern (gemessen: ~8s) -- fuer
    # den expliziten Batch-Lauf grosszuegigerer Timeout als embeddings.py's
    # interaktiver Default (5s).
    BATCH_TIMEOUT = 30.0

    # Ollama-Erreichbarkeit einmal vorab pruefen (best-effort, kein Abbruch bei Fehler --
    # embed_text() degradiert je Item selbst).
    probe = embeddings.embed_text("Erreichbarkeitstest", timeout=BATCH_TIMEOUT)
    if probe is None:
        print("WARNUNG: Lokales Embedding-Modell nicht erreichbar "
              f"({embeddings.DEFAULT_OLLAMA_URL}, Modell {embeddings.DEFAULT_EMBED_MODEL}). "
              "Kein Vektor wird geschrieben, Suche bleibt beim reinen FTS5/LIKE-Zustand.")
        conn.close()
        return 1

    model = embeddings.DEFAULT_EMBED_MODEL
    t0 = time.monotonic()
    embedded, skipped = 0, 0

    rows_written = 0

    nodes = conn.execute("SELECT id, path, project_id, title, summary, content FROM knowledge_nodes").fetchall()
    for n in nodes:
        text = f"{n['path']}\n{n['title']}\n{n['summary']}\n{n['content'] or ''}"
        vec = embeddings.embed_text(text, timeout=BATCH_TIMEOUT)
        if vec is None:
            skipped += 1
            continue
        conn.execute(
            "INSERT OR REPLACE INTO knowledge_embeddings (kind, ref_id, project_id, model, vector, updated_at) "
            "VALUES ('node', ?, ?, ?, ?, ?)",
            (n["id"], n["project_id"], model, embeddings.pack_embedding(vec), now_iso())
        )
        embedded += 1
        rows_written += 1

    lessons = conn.execute(
        "SELECT id, node_path, projects, description, root_cause, prevention FROM lessons_learned"
    ).fetchall()
    for l in lessons:
        zuordnung = l["node_path"] or l["projects"] or ""
        text = f"{zuordnung}\n{l['description']}\n{l['root_cause'] or ''}\n{l['prevention'] or ''}"
        vec = embeddings.embed_text(text, timeout=BATCH_TIMEOUT)
        if vec is None:
            skipped += 1
            continue
        packed = embeddings.pack_embedding(vec)
        ts = now_iso()
        for proj in resolve_lesson_projects(l["projects"]):
            conn.execute(
                "INSERT OR REPLACE INTO knowledge_embeddings (kind, ref_id, project_id, model, vector, updated_at) "
                "VALUES ('lesson', ?, ?, ?, ?, ?)",
                (l["id"], proj, model, packed, ts)
            )
            rows_written += 1
        embedded += 1

    conn.commit()
    elapsed = time.monotonic() - t0

    checksum_after = _checksum(conn)
    conn.close()

    print(f"Nodes: {len(nodes)}, Lessons: {len(lessons)}")
    print(f"Eingebettet (Vektoren berechnet): {embedded}, uebersprungen (Embedding-Fehler): {skipped}")
    print(f"Embedding-Zeilen geschrieben (mit Bereichs-Fanout bei Lessons): {rows_written}")
    print(f"Laufzeit: {elapsed:.1f}s")

    if checksum_before != checksum_after:
        print("FEHLER: Pruefsumme der Bestandsdaten hat sich geaendert! "
              f"Sicherung liegt unter {backup_path}.")
        return 1
    print("Pruefsumme unveraendert -- Bestandsdaten unangetastet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
