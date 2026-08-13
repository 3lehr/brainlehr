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
import json
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import embeddings
from haken.ort import DB as DB_PATH  # noqa: E402
BERLIN = ZoneInfo("Europe/Berlin")

# --force (Auftrag 2026-08-07, Modellwechsel-Fall): rechnet ALLES neu, auch
# wenn Pruefsumme+Modell passen. Noetig, wenn embed_text() selbst anders
# rechnet (neue Modellversion unter gleichem Tag) -- die Pruefsumme sieht das
# nicht, weil sich der eingebettete TEXT dabei nicht aendert.
FORCE = "--force" in sys.argv[1:]

# Stapelgroesse fuer /api/embed (Ergaenzung 2026-08-07, gemessen waehrend des
# Vollaufs): Ollama nimmt bei `input` eine Liste entgegen -- 1 Text/Aufruf
# maass 132-205ms/Text (HTTP-Overhead dominiert, nicht Rechenzeit), 32
# Texte/Aufruf 17,7-18,6ms/Text (Faktor ~7-11, zwei unabhaengige Messungen).
# Eigene Messreihe (1/8/16/32/64/128/256, waehrend ein Parallellauf denselben
# Ollama-Prozess mit Einzelanfragen belegte): Gewinn flacht zwischen 16 und
# 32 ab, danach unter Nebenlast SCHLECHTER (64 45,7ms/Text, 256 88,7ms/Text)
# -- ein grosser Stapel haelt Ollama laenger blockiert und verliert unter
# echter Nebenlast (z.B. knowledge_recall_hook waehrenddessen) mehr, als er
# gewinnt. 32 ist der belegte Sweet Spot, nicht geraten.
BATCH_SIZE = 32

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
    dim INTEGER,
    vector BLOB NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (kind, ref_id, project_id)
);
"""

# dim (Auftrag 2026-08-07, Modellwechsel bge-m3): additive Nachfuehrung fuer
# eine bereits bestehende Tabelle, die vor der Spalte angelegt wurde -- die
# CREATE TABLE IF NOT EXISTS oben legt sie nur bei einer ganz neuen Tabelle an.
ENSURE_DIM_COLUMN_SQL = "ALTER TABLE knowledge_embeddings ADD COLUMN dim INTEGER"

# text_checksum (Auftrag 2026-08-07, Ueberspringen unveraenderter Eintraege):
# sha256 ueber genau den Text, der eingebettet wurde -- gleiches additive
# Nachfuehrungs-Idiom wie dim oben. Warum Pruefsumme statt updated_at-
# Zeitstempel: updated_at wird an anderer Stelle (knowledge_update() u.ae.)
# auch OHNE Textaenderung neu gesetzt (siehe test_updated_at_nebenwirkungen.py)
# -- ein Zeitstempelvergleich haette in genau diesem Fall unveraenderten Text
# faelschlich neu gerechnet, ist also kein verlaesslicher Indikator fuer
# "Text hat sich geaendert". Die Pruefsumme schuetzt NICHT davor, dass sich
# embeddings.embed_text() selbst aendert (Ollama-Modell-Update unter gleichem
# Tag, andere Praeprozessierung) oder dass jemand den vector-Blob manuell
# verfaelscht, ohne Text/Modell anzufassen -- fuer den ersten Fall existiert
# der FORCE-Schalter unten, der zweite Fall ist ausserhalb des Auftrags.
ENSURE_CHECKSUM_COLUMN_SQL = "ALTER TABLE knowledge_embeddings ADD COLUMN text_checksum TEXT"

# Config-Tabelle fuer die Modellsperre (Auftrag 2026-08-07, siehe schema.sql-
# Kommentar bei knowledge_embeddings_model_check_bi/_bu). Dieses Skript
# verbindet sich direkt (nicht ueber knowledge_mcp_server.get_db/ensure_schema)
# -- ohne dieses CREATE TABLE waere die Tabelle auf einer DB fehlend, deren
# Server noch nicht neu gestartet wurde, und der UPSERT unten schluege fehl.
CREATE_CONFIG_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
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
    return datetime.now(BERLIN).isoformat(timespec="seconds")


def _text_checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# Textzusammensetzung EINMAL hier, nicht an jeder Stelle neu abgeschrieben --
# vektorstand.py (Melder fuer veraltete/fehlende Vektoren) importiert genau
# diese zwei Funktionen, statt den Text ein zweites Mal zu erfinden. Nur so
# gibt es eine Wahrheit darueber, was eingebettet wurde.
def node_text(row) -> str:
    return f"{row['path']}\n{row['title']}\n{row['summary']}\n{row['content'] or ''}"


def lesson_text(row) -> str:
    zuordnung = row["node_path"] or row["projects"] or ""
    return f"{zuordnung}\n{row['description']}\n{row['root_cause'] or ''}\n{row['prevention'] or ''}"


def _needs_recompute(
    conn: sqlite3.Connection, kind: str, ref_id: str, project_ids: list[str],
    model: str, checksum: str, force: bool,
) -> bool:
    """True, wenn mindestens einer der Ziel-Bereiche neu gerechnet werden muss
    (fehlende Zeile, anderes Modell, oder Pruefsumme weicht ab -- Text hat
    sich seither geaendert oder die Zeile stammt von vor diesem Auftrag und
    traegt noch keine Pruefsumme)."""
    if force:
        return True
    for pid in project_ids:
        row = conn.execute(
            "SELECT model, text_checksum FROM knowledge_embeddings "
            "WHERE kind = ? AND ref_id = ? AND project_id = ?",
            (kind, ref_id, pid),
        ).fetchone()
        if row is None or row[0] != model or row[1] != checksum:
            return True
    return False


def _embed_batch(texts: list[str], *, timeout: float) -> list[list[float] | None]:
    """Ein HTTP-Aufruf gegen Ollamas /api/embed fuer bis zu BATCH_SIZE Texte
    (Grenze aus dem Auftrag: embeddings.py bleibt unangetastet, deshalb hier
    dieselbe Anfrage-/Sicherheitslogik wie embeddings.embed_text() dupliziert
    -- nur fuer `input` als Liste statt einzelnem String).

    Rueckgabe: gleich lange Liste wie texts, je Eintrag Vektor oder None.
    Scheitert der GANZE Stapel (Netzwerk/Timeout/Ollama liefert eine andere
    Anzahl Vektoren als gesendet), werden die Texte NICHT still verworfen --
    Fallback ist der bestehende Einzelpfad embeddings.embed_text() je Text
    (dieselbe Fehlerbehandlung wie vor diesem Umbau, nur langsamer). Damit
    verliert ein kaputter Stapel bestenfalls Zeit, nie Vektoren."""
    cleaned = [(t or "").strip() for t in texts]
    non_empty = [i for i, t in enumerate(cleaned) if t]
    result: list[list[float] | None] = [None] * len(texts)
    if not non_empty:
        return result

    url = embeddings.DEFAULT_OLLAMA_URL.rstrip("/")
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Ollama-Embeddings duerfen nur Loopback-URLs nutzen")
    # DEFAULT_EMBED_MODEL traegt die volle Identitaet ('bge-m3@ctx2048');
    # Ollama kennt dieses Tag nicht -- in Rohname + num_ctx zerlegen (Auftrag 80).
    raw_model, ctx = embeddings.parse_model_identity(embeddings.DEFAULT_EMBED_MODEL)
    payload = {"model": raw_model, "input": [cleaned[i] for i in non_empty],
               "options": {"num_ctx": ctx}}
    req = urllib.request.Request(
        f"{url}/api/embed",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw_body = json.loads(response.read().decode("utf-8"))
        vectors = raw_body.get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(non_empty):
            raise ValueError(f"Stapel-Antwort: {len(vectors) if isinstance(vectors, list) else 'keine Liste'} "
                              f"Vektoren fuer {len(non_empty)} gesendete Texte")
        for pos, idx in enumerate(non_empty):
            vec = vectors[pos]
            result[idx] = [float(x) for x in vec] if isinstance(vec, list) else None
        return result
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError, TypeError) as exc:
        print(f"WARNUNG: Stapel-Einbettung fehlgeschlagen ({len(non_empty)} Texte, {exc}) "
              "-- fahre einzeln nach, kein stiller Vektorverlust.")
        for idx in non_empty:
            result[idx] = embeddings.embed_text(cleaned[idx], timeout=timeout)
        return result


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
    dest = DB_PATH.parent / f"brainlehr.db.bak-{stamp}"
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
    emb_columns = {row[1] for row in conn.execute("PRAGMA table_info(knowledge_embeddings)")}
    if "dim" not in emb_columns:
        conn.execute(ENSURE_DIM_COLUMN_SQL)
    if "text_checksum" not in emb_columns:
        conn.execute(ENSURE_CHECKSUM_COLUMN_SQL)
    conn.execute(CREATE_CONFIG_TABLE_SQL)
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
    # Modellsperre (schema.sql, knowledge_embeddings_model_check_bi/_bu) VOR
    # der Schreibschleife freischalten -- sonst weist der eigene Trigger die
    # erste Zeile mit dem neuen Modell ab, weil knowledge_config noch das
    # alte traegt.
    conn.execute(
        "INSERT INTO knowledge_config (key, value, updated_at) VALUES ('embed_model', ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (model, now_iso()),
    )
    conn.commit()
    t0 = time.monotonic()
    embedded, skipped_error, skipped_unchanged = 0, 0, 0

    rows_written = 0

    # Erst sammeln, wer ueberhaupt neu gerechnet werden muss (kein Ollama-
    # Aufruf fuer unveraenderte Eintraege), dann in BATCH_SIZE-Haeppchen ueber
    # /api/embed einbetten -- ein HTTP-Request statt einem je Text.
    nodes = conn.execute("SELECT id, path, project_id, title, summary, content FROM knowledge_nodes").fetchall()
    node_pending = []
    for n in nodes:
        text = node_text(n)
        text_checksum = _text_checksum(text)
        if _needs_recompute(conn, "node", n["id"], [n["project_id"]], model, text_checksum, FORCE):
            node_pending.append((n, text, text_checksum))
        else:
            skipped_unchanged += 1

    for i in range(0, len(node_pending), BATCH_SIZE):
        chunk = node_pending[i:i + BATCH_SIZE]
        vecs = _embed_batch([c[1] for c in chunk], timeout=BATCH_TIMEOUT)
        for (n, text, text_checksum), vec in zip(chunk, vecs):
            if vec is None:
                skipped_error += 1
                continue
            conn.execute(
                "INSERT OR REPLACE INTO knowledge_embeddings "
                "(kind, ref_id, project_id, model, dim, vector, updated_at, text_checksum) "
                "VALUES ('node', ?, ?, ?, ?, ?, ?, ?)",
                (n["id"], n["project_id"], model, len(vec), embeddings.pack_embedding(vec), now_iso(), text_checksum)
            )
            embedded += 1
            rows_written += 1

    lessons = conn.execute(
        "SELECT id, node_path, projects, description, root_cause, prevention FROM lessons_learned"
    ).fetchall()
    lesson_pending = []
    for l in lessons:
        text = lesson_text(l)
        text_checksum = _text_checksum(text)
        target_projects = resolve_lesson_projects(l["projects"])
        if _needs_recompute(conn, "lesson", l["id"], target_projects, model, text_checksum, FORCE):
            lesson_pending.append((l, text, text_checksum, target_projects))
        else:
            skipped_unchanged += 1

    for i in range(0, len(lesson_pending), BATCH_SIZE):
        chunk = lesson_pending[i:i + BATCH_SIZE]
        vecs = _embed_batch([c[1] for c in chunk], timeout=BATCH_TIMEOUT)
        for (l, text, text_checksum, target_projects), vec in zip(chunk, vecs):
            if vec is None:
                skipped_error += 1
                continue
            packed = embeddings.pack_embedding(vec)
            ts = now_iso()
            for proj in target_projects:
                conn.execute(
                    "INSERT OR REPLACE INTO knowledge_embeddings "
                    "(kind, ref_id, project_id, model, dim, vector, updated_at, text_checksum) "
                    "VALUES ('lesson', ?, ?, ?, ?, ?, ?, ?)",
                    (l["id"], proj, model, len(vec), packed, ts, text_checksum)
                )
                rows_written += 1
            embedded += 1

    conn.commit()
    elapsed = time.monotonic() - t0

    checksum_after = _checksum(conn)
    conn.close()

    # Aufgabe 69: Wer laenger ist als die Zeichengrenze, verliert seinen
    # hinteren Teil VOR dem Rechnen -- und zwar still. Genau daran kann eine
    # Abrufzahl scheitern, ohne dass jemand die Ursache sieht. Deshalb hier
    # gezaehlt und mit Pfad genannt, nicht nur summiert: eine blosse Zahl
    # sagt nicht, WORAUS sie besteht.
    gekappt = [(n["path"], len(node_text(n))) for n in nodes
               if embeddings.wird_gekappt(node_text(n))]
    gekappt += [(f"Lehre {l['id']}", len(lesson_text(l))) for l in lessons
                if embeddings.wird_gekappt(lesson_text(l))]

    print(f"Nodes: {len(nodes)}, Lessons: {len(lessons)}")
    if gekappt:
        grenze = embeddings.zeichengrenze()
        print(f"GEKAPPT beim Einbetten: {len(gekappt)} von {len(nodes) + len(lessons)} "
              f"Eintraegen ueberschreiten {grenze} Zeichen (num_ctx={embeddings.EMBED_NUM_CTX}) "
              "-- ihr hinterer Teil ist im Bedeutungskanal unauffindbar:")
        for pfad, laenge in sorted(gekappt, key=lambda x: -x[1]):
            print(f"  {laenge:6} Zeichen  {pfad}")
    print(f"Neu gerechnet: {embedded}, uebersprungen (unveraendert): {skipped_unchanged}, "
          f"uebersprungen (Embedding-Fehler): {skipped_error}")
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
