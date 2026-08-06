#!/usr/bin/env python3
"""
Knowledge MCP Server — Shared Knowledge Database Access for AI Agents.

Erstellt: 2026-03-25T16:30:00+01:00
Transport: stdio (JSON-RPC 2.0)
DB: SQLite + FTS5 Baumstruktur

Tools:
  - knowledge_browse(path)        → Kinder-Knoten (nur Titel+Summary)
  - knowledge_read(node_id)       → Volltext eines Knotens
  - knowledge_search(query, scope)→ Hybrid-Suche (FTS5 + optional lokale Embeddings, RRF-fusioniert), gibt Summaries zurück
  - knowledge_add(parent_path, title, summary, content, project_id, tags)
  - knowledge_update(node_id, summary, content)
  - knowledge_relation_add|list|update|remove(...) → explizite belegte Kanten
  - lesson_record(type, description, root_cause, resolution, prevention, severity, projects, same_as)
  - lesson_update(lesson_id, description, root_cause, resolution, prevention, severity, projects, status, delete)
  - lesson_query(type, project, status)
  - knowledge_stats()             → Übersichts-Statistiken
"""

import difflib
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
import embeddings  # lokale Embeddings + RRF-Fusion, siehe embeddings.py

# BEGOD_KNOWLEDGE_DB ueberschreibt den Pfad (gleiche Bauform wie die drei
# BEGOD_KNOWLEDGE_*-Vars in _identity()). Ohne sie: heutiges Verhalten
# unveraendert. Grund: ein fest an __file__ gebundener DB-Pfad verhindert
# jeden Betrieb ausserhalb dieses Verzeichnisses (Fremdclient-Test, spaeter
# Portabilitaet ausserhalb Begod2026) und laesst sich nicht gegen eine
# Testkopie fahren, ohne die echte DB anzufassen.
DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (Path(__file__).parent / "knowledge.db"))
BERLIN = ZoneInfo("Europe/Berlin")
# Mehrere MCP-Prozesse/Sitzungen schreiben gleichzeitig auf dieselbe WAL-DB.
# WAL erlaubt genau einen Schreiber; ohne busy_timeout wirft ein zweiter
# gleichzeitiger Schreibversuch sofort SQLITE_BUSY statt kurz zu warten.
# 2000ms = derselbe Wert, mit dem knowledge_recall_hook.py seine RO-Verbindung
# oeffnet (dort als timeout=2.0) -- lang genug fuer einen normalen Schreibvorgang
# eines anderen Prozesses, kurz genug, dass ein Hook nicht spuerbar haengt.
BUSY_TIMEOUT_MS = 2000
RELATION_TYPES = {
    "references", "supersedes", "interprets", "implements", "contradicts",
    "supports", "derived_from", "cites", "evaluates_with", "constrains",
    "produces", "requires", "replaces_component", "analogous_to", "feeds_into",
}
EVENT_STATUSES = {"started", "completed", "failed"}
# Anlass (Auftrag 2026-08-06): was hat den Eintrag ausgeloest. 'selbst' und
# 'betreiber' sind SELBSTBERICHTET vom aufrufenden Modell -- nur so gut wie
# der Schreiber, die DB kann sie nicht nachpruefen. 'hook' und 'skript' sind
# dagegen objektiv, weil der Aufrufweg sie kennt (siehe knowledge_capture_hook.py:
# der Stop-Hook ruft lesson_record/knowledge_add NICHT selbst auf, er zwingt nur
# das Modell via decision:block zum /learn-Skill, das dann wie jeder normale
# Aufruf tool-seitig entscheidet -- 'hook' ist deshalb auch dort nur so
# verlässlich wie der Skill-Prompt, der es setzt, kein von aussen erzwungener
# Wert). 'unbekannt' ist Vorgabe und deckt den gesamten Altbestand vor diesem
# Feld ab. Wer die Verteilung auswertet (knowledge_stats), darf die vier
# Werte nicht gleich behandeln.
ALLOWED_ANLASS = {"selbst", "betreiber", "hook", "skript", "unbekannt"}
# Rueckfuellwert fuer Bestandszeilen ohne source (Auftrag 2026-08-06, siehe
# _ensure_node_constraint_triggers/migrate_source_constraints.py). Testdaten,
# Umschreiben erlaubt -- deshalb Nachtrag statt "Regel gilt nur fuer Neues".
SOURCE_BACKFILL_PLACEHOLDER = "unbekannt (Altbestand vor Migration 2026-08-06, nachgetragen)"
# Sechs Trigger, die die drei DB-Zusicherungen an knowledge_nodes tragen
# (source nicht leer, parent_path zeigt auf vorhandenen Knoten oder '/',
# anlass aus ALLOWED_ANLASS) -- identischer Text wie in schema.sql, dort
# fuer frisch angelegte Dateien, hier als Nachzug fuer Bestands-DBs. Zwei
# Kopien statt gemeinsamer Quelle, gleiches Muster wie jede andere additive
# Migration in diesem Server (z.B. _ensure_anlass_columns neben dem
# anlass-Block in schema.sql).
NODE_CONSTRAINT_TRIGGERS_SQL = """
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
# Auditkette ueber access_log (Auftrag 2026-08-06). Gleiche Laenge/Form wie
# ein SHA-256-Hexdigest, damit ein Genesis-Wert nicht wie ein "kaputter"
# Hash aussieht. Fachtrennung zu fahrtenbuch_legacy/.../hash_chain.dart::
# genesisHash bewusst: eigener Store, eigene Konstante.
GENESIS_KETTEN_HASH = "0" * 64


def now_iso() -> str:
    # echter Versatz statt fest "+01:00" -- isoformat() liefert bereits
    # Doppelpunkt-Form ("+02:00"), DST-Wechsel automatisch via zoneinfo.
    return datetime.now(BERLIN).isoformat(timespec="seconds")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    return conn


def _ensure_anlass_columns(conn: sqlite3.Connection) -> None:
    """Nachzug fuer Bestands-DBs ohne die Spalte anlass (Auftrag 2026-08-06,
    Befund: schreibpruefstand.db hatte schema.sql, aber keinen Migrationslauf
    -- knowledge_add/lesson_record brachen mit rohem sqlite3.OperationalError
    '<table> has no column named anlass' ab). PRAGMA table_info ist reine
    Metadaten-Abfrage (kein Tabellen-Scan), kostet also im Normalfall (Spalte
    vorhanden) nur Mikrosekunden pro Verbindung -- gemessen in
    tests/test_anlass_schema_backfill.py. Tabellen, die es (noch) gar nicht
    gibt (z.B. eine minimale Legacy-Testfixture ohne lessons_learned), werden
    uebersprungen statt einen ALTER-Fehlschlag zu produzieren.

    Entscheidung automatisch statt nur melden: gleiches Muster wie der
    bestehende access_log-Nachzug direkt darunter in dieser Funktion, additiv
    (ALTER TABLE ADD COLUMN, NOT NULL DEFAULT 'unbekannt' -- SQLite befuellt
    Bestandszeilen beim ALTER selbst, kein separater Ruckfuell-Schritt, siehe
    migrate_anlass.py). Anders als der access_log-Nachzug (der ohne Sicherung
    auf frueher schon additiv gewachsenen Spalten laeuft) wird hier vorher
    ein WAL-Checkpoint plus Dateisicherung erzwungen (Lehre L-218f1e: ein
    reiner shutil.copy2 im WAL-Betrieb kann committete, aber noch nicht
    zurueckgeschriebene Zeilen verlieren). Schlaegt der Checkpoint fehl (ein
    anderer Prozess schreibt gerade), wird NICHT stumm weiter-ALTERt --
    sprechender Fehler statt der rohen sqlite3-Ausnahme, mit dem Hinweis auf
    den manuellen Nachzug via migrate_anlass.py --apply."""
    existing_tables = {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    missing = {
        table for table in ("knowledge_nodes", "lessons_learned")
        if table in existing_tables
        and "anlass" not in {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    }
    if not missing:
        return

    busy, log_frames, checkpointed = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    if busy:
        raise RuntimeError(
            f"Spalte 'anlass' fehlt in {sorted(missing)}, aber die Sicherung vor dem "
            f"automatischen Nachzug ist blockiert (WAL-Checkpoint busy={busy}, "
            f"{log_frames} Frames, {checkpointed} checkpointed) -- vermutlich schreibt "
            "gerade ein anderer Prozess auf dieselbe Datenbank. Nachzug abgebrochen, "
            "nichts geaendert. Von Hand nachholen: "
            "'.venv/bin/python shared-knowledge/migrate_anlass.py --apply'."
        )
    if DB_PATH.exists():
        stamp = datetime.now(BERLIN).strftime("%Y%m%dT%H%M%S")
        backup_path = DB_PATH.parent / f"{DB_PATH.name}.bak-{stamp}"
        shutil.copy2(DB_PATH, backup_path)

    for table in missing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN anlass TEXT NOT NULL DEFAULT 'unbekannt'")


def _ensure_node_constraint_triggers(conn: sqlite3.Connection) -> None:
    """Nachzug fuer Bestands-DBs ohne die sechs Zusicherungs-Trigger an
    knowledge_nodes (Auftrag 2026-08-06). Gleiches Muster wie
    _ensure_anlass_columns direkt darueber: WAL-Checkpoint + Sicherungskopie
    VOR jeder Aenderung (Lehre L-218f1e), Abbruch mit sprechendem Fehler
    statt stillem Weiterlaufen wenn der Checkpoint blockiert ist. Anders als
    dort aendert dieser Nachzug zusaetzlich Daten (Rueckfuellung leerer
    source-Werte auf SOURCE_BACKFILL_PLACEHOLDER) -- Testdaten, Umschreiben
    erlaubt (Betreiber-Direktive), deshalb Nachtrag statt Bestandszeilen
    dauerhaft von der Regel auszunehmen. Backfill laeuft VOR der
    Trigger-Erzeugung, sonst wuerde z.B. das access_count-Increment in
    knowledge_read jede betroffene Bestandszeile sperren, bis jemand ihren
    source-Wert von Hand nachtraegt."""
    existing_triggers = {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
    }
    needed = {
        "knowledge_nodes_source_check_bi", "knowledge_nodes_source_check_bu",
        "knowledge_nodes_parent_check_bi", "knowledge_nodes_parent_check_bu",
        "knowledge_nodes_anlass_check_bi", "knowledge_nodes_anlass_check_bu",
    }
    if needed <= existing_triggers:
        return
    if "knowledge_nodes" not in {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }:
        return  # minimale Testfixture ohne die Tabelle -- nichts zu sichern
    node_columns = {row[1] for row in conn.execute("PRAGMA table_info(knowledge_nodes)")}
    if not {"source", "parent_path", "anlass"} <= node_columns:
        return  # minimale Legacy-Testfixture ohne diese Spalten (z.B.
        # migrate_relations.py-Selbsttest) -- die Trigger brauchen alle drei,
        # eine echte Bestands-DB hat source/parent_path seit jeher und
        # anlass spaetestens nach _ensure_anlass_columns() oben

    busy, log_frames, checkpointed = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    if busy:
        raise RuntimeError(
            f"Zusicherungs-Trigger an knowledge_nodes fehlen, aber die Sicherung vor dem "
            f"automatischen Nachzug ist blockiert (WAL-Checkpoint busy={busy}, "
            f"{log_frames} Frames, {checkpointed} checkpointed) -- vermutlich schreibt "
            "gerade ein anderer Prozess auf dieselbe Datenbank. Nachzug abgebrochen, "
            "nichts geaendert. Von Hand nachholen: "
            "'.venv/bin/python shared-knowledge/migrate_source_constraints.py --apply'."
        )
    if DB_PATH.exists():
        stamp = datetime.now(BERLIN).strftime("%Y%m%dT%H%M%S")
        backup_path = DB_PATH.parent / f"{DB_PATH.name}.bak-{stamp}"
        shutil.copy2(DB_PATH, backup_path)

    conn.execute(
        "UPDATE knowledge_nodes SET source = ? WHERE source IS NULL OR TRIM(source) = ''",
        (SOURCE_BACKFILL_PLACEHOLDER,),
    )
    conn.executescript(NODE_CONSTRAINT_TRIGGERS_SQL)


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Idempotent additive migration for old knowledge.db copies."""
    _ensure_anlass_columns(conn)
    _ensure_node_constraint_triggers(conn)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(access_log)")}
    for name, declaration in {
        "actor": "TEXT", "model": "TEXT", "session": "TEXT",
        "status": "TEXT DEFAULT 'completed'",
        "zeilen_hash": "TEXT", "ketten_hash": "TEXT",
    }.items():
        if name not in columns:
            conn.execute(f"ALTER TABLE access_log ADD COLUMN {name} {declaration}")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS knowledge_relations (
            id TEXT PRIMARY KEY,
            source_path TEXT NOT NULL,
            target_path TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0.8 CHECK(confidence BETWEEN 0.0 AND 1.0),
            weight REAL NOT NULL DEFAULT 1.0 CHECK(weight >= 0.0),
            evidence TEXT,
            source TEXT,
            creator TEXT,
            model TEXT,
            session TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(source_path, target_path, relation_type),
            FOREIGN KEY(source_path) REFERENCES knowledge_nodes(path) ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY(target_path) REFERENCES knowledge_nodes(path) ON UPDATE CASCADE ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_relations_source ON knowledge_relations(source_path);
        CREATE INDEX IF NOT EXISTS idx_relations_target ON knowledge_relations(target_path);
        CREATE INDEX IF NOT EXISTS idx_relations_type ON knowledge_relations(relation_type);
    """)
    conn.commit()


def _identity(actor: str | None = None, model: str | None = None,
              session: str | None = None) -> tuple[str | None, str | None, str | None]:
    return (
        actor or os.environ.get("BEGOD_KNOWLEDGE_ACTOR"),
        model or os.environ.get("BEGOD_KNOWLEDGE_MODEL"),
        session or os.environ.get("BEGOD_KNOWLEDGE_SESSION"),
    )


def compute_zeilen_hash(affected_row: dict | None) -> str | None:
    """SHA-256 ueber den von einer Aktion betroffenen Datensatz NACH der
    Aenderung. None (-> NULL in access_log.zeilen_hash) bei reinen
    Lesezugriffen und bei Loeschungen -- beides ein gueltiger Zustand,
    siehe Spaltenkommentar an access_log in schema.sql."""
    if affected_row is None:
        return None
    payload = json.dumps(affected_row, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_ketten_hash(prev_ketten_hash: str | None, *, node_path: str | None,
                        action: str, query: str | None, project_id: str | None,
                        actor: str | None, model: str | None, session: str | None,
                        status: str, timestamp: str, zeilen_hash: str | None) -> str:
    """Ein Schritt der Auditkette ueber access_log (Auftrag 2026-08-06).
    Feldreihenfolge ist Teil des Vertrags -- siehe Spaltenkommentar an
    access_log.ketten_hash in schema.sql; eine Aenderung hier bricht jede
    bereits geschriebene Kette rueckwirkend. KEINE Verschluesselung, keine
    Signatur: weist eine nachtraegliche Aenderung nach, verhindert sie
    nicht -- wer Schreibrechte auf die DB-Datei hat, kann die Kette neu
    rechnen (bekannte Grenze, siehe Auftrag)."""
    prev = prev_ketten_hash or GENESIS_KETTEN_HASH
    fields = (prev, node_path, action, query, project_id, actor, model,
              session, status, timestamp, zeilen_hash)
    payload = "|".join("" if f is None else str(f) for f in fields)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def log_access(conn: sqlite3.Connection, node_path: str | None, action: str,
               query: str | None = None, project_id: str | None = None,
               actor: str | None = None, model: str | None = None,
               session: str | None = None, status: str = "completed",
               affected_row: dict | None = None) -> int:
    if status not in EVENT_STATUSES:
        raise ValueError(f"Invalid event status: {status}")
    actor, model, session = _identity(actor, model, session)
    timestamp = now_iso()
    zeilen_hash = compute_zeilen_hash(affected_row)
    # Letzten ketten_hash auf DERSELBEN Verbindung lesen -- sieht auch die
    # noch nicht committete Datenaenderung dieser Transaktion (relevant,
    # weil dieser INSERT+commit gemeinsam mit dem vorangegangenen
    # Schreibzugriff (z.B. knowledge_nodes) die Transaktionsgrenze bildet,
    # siehe Aufrufer in knowledge_add/knowledge_update/etc.). Zeilen ohne
    # ketten_hash (Altbestand vor der Migration) zaehlen als Kettenanfang.
    prev_row = conn.execute(
        "SELECT ketten_hash FROM access_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    prev_ketten_hash = prev_row[0] if prev_row else None
    ketten_hash = compute_ketten_hash(
        prev_ketten_hash, node_path=node_path, action=action, query=query,
        project_id=project_id, actor=actor, model=model, session=session,
        status=status, timestamp=timestamp, zeilen_hash=zeilen_hash,
    )
    cursor = conn.execute(
        """INSERT INTO access_log
           (node_path, action, query, project_id, actor, model, session, status, timestamp,
            zeilen_hash, ketten_hash)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (node_path, action, query, project_id, actor, model, session, status, timestamp,
         zeilen_hash, ketten_hash)
    )
    conn.commit()
    return int(cursor.lastrowid)


# ─── MCP Tool Implementations ────────────────────────────────────────────

def knowledge_browse(path: str = "/", project_filter: str | None = None, *,
                     actor: str | None = None, model: str | None = None,
                     session: str | None = None) -> dict:
    """Browse children of a knowledge tree node. Returns titles and summaries only (token-efficient)."""
    conn = get_db()
    log_access(conn, path, "browse", project_id=project_filter,
               actor=actor, model=model, session=session, status="started")

    if path == "/":
        query = "SELECT id, path, title, summary, project_id, level, access_count FROM knowledge_nodes WHERE level = 0 ORDER BY path"
        params: tuple = ()
    else:
        normalized = path.rstrip("/")
        query = "SELECT id, path, title, summary, project_id, level, access_count FROM knowledge_nodes WHERE parent_path = ? ORDER BY path"
        params = (normalized,)

    if project_filter:
        query = query.replace("ORDER BY", f"AND project_id IN ('shared', ?) ORDER BY")
        params = (*params, project_filter)

    rows = conn.execute(query, params).fetchall()
    children_count_q = "SELECT COUNT(*) FROM knowledge_nodes WHERE parent_path = ?"

    results = []
    for r in rows:
        child_count = conn.execute(children_count_q, (r["path"],)).fetchone()[0]
        results.append({
            "id": r["id"],
            "path": r["path"],
            "title": r["title"],
            "summary": r["summary"],
            "project": r["project_id"],
            "has_children": child_count > 0,
            "children_count": child_count
        })

    log_access(conn, path, "browse", project_id=project_filter,
               actor=actor, model=model, session=session)
    conn.close()
    return {"path": path, "children": results, "count": len(results)}


def knowledge_read(node_id: str, *, actor: str | None = None,
                   model: str | None = None, session: str | None = None) -> dict:
    """Read full content of a knowledge node. Use browse first to find the right node."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM knowledge_nodes WHERE id = ? OR path = ?",
        (node_id, node_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"error": f"Node not found: {node_id}"}

    log_access(conn, row["path"], "read", project_id=row["project_id"],
               actor=actor, model=model, session=session, status="started")
    conn.execute("UPDATE knowledge_nodes SET access_count = access_count + 1 WHERE id = ?", (row["id"],))
    log_access(conn, row["path"], "read", project_id=row["project_id"],
               actor=actor, model=model, session=session)
    conn.commit()

    # Befund 2026-08-06: ein Astknoten ("Automatisch erzeugter Astknoten",
    # kein content) liefert ohne diesen Zusatz eine leere Seite -- Zweck und
    # Regeln stehen in den Kindknoten. Nur eine Ebene, nicht rekursiv (siehe
    # knowledge_browse fuer den vollen Baum).
    children = conn.execute(
        "SELECT title, summary FROM knowledge_nodes WHERE parent_path = ? ORDER BY path",
        (row["path"],)
    ).fetchall()

    result = {
        "id": row["id"],
        "path": row["path"],
        "title": row["title"],
        "summary": row["summary"],
        "content": row["content"] or "(kein Volltext)",
        "project": row["project_id"],
        "tags": json.loads(row["tags"]) if row["tags"] else [],
        "source": row["source"],
        "confidence": row["confidence"],
        "norm_rang": row["norm_rang"],
        "gilt_ab": row["gilt_ab"],
        "gilt_bis": row["gilt_bis"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "children": [{"title": c["title"], "summary": c["summary"]} for c in children],
    }
    conn.close()
    return result


def _embedding_ranking(conn: sqlite3.Connection, kind: str, query_vec: list[float],
                        allowed_ids: set | None) -> list[str]:
    """Cosine-Ranking ueber die additive knowledge_embeddings-Tabelle. Fehlt die
    Tabelle (aeltere DB-Kopie ohne AP "Wissenssuche nach Bedeutung"), liefert
    leere Liste statt zu werfen -- Aufrufer faellt dann automatisch auf reines
    FTS5/LIKE-Matching zurueck."""
    try:
        rows = conn.execute(
            "SELECT ref_id, vector FROM knowledge_embeddings WHERE kind = ?", (kind,)
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    scored = []
    seen_ref_ids = set()  # mehrwertige Lehren: je Bereich eine Zeile, gleicher Vektor --
    # ohne Dedup zaehlt dieselbe Aehnlichkeit mehrfach in die RRF-Fusion und
    # haengt eine mehrwertige Lehre allein wegen ihrer Zeilenzahl vor eine
    # gleich relevante einwertige (siehe test_scope_in_query.py).
    for r in rows:
        if allowed_ids is not None and r["ref_id"] not in allowed_ids:
            continue
        if r["ref_id"] in seen_ref_ids:
            continue
        seen_ref_ids.add(r["ref_id"])
        vec = embeddings.unpack_embedding(r["vector"])
        scored.append((embeddings.cosine_similarity(query_vec, vec), r["ref_id"]))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [ref_id for _, ref_id in scored]


def _fuse_with_keyword_floor(keyword_ordered_ids: list, embedding_ordered_ids: list,
                              max_results: int) -> list:
    """RRF-Fusion, aber mit garantiertem Stichwort-Sockel: jede der Top-
    max_results Stichworttreffer-IDs bleibt im Ergebnis, egal wie das
    Embedding-Ranking ausfaellt (Abnahme-Kriterium "kein Stichworttreffer geht
    verloren"). Ohne Embedding-Treffer (leere Liste, z.B. Ollama nicht
    erreichbar oder Tabelle fehlt) reproduziert das exakt die bisherige
    Stichwort-Reihenfolge, da dict.fromkeys() den Sockel unveraendert vorn
    haelt und `fused` in diesem Fall ohnehin identisch mit
    keyword_ordered_ids ist."""
    weight = embeddings.hybrid_retrieval_weight()
    fused = embeddings.rrf_fuse(keyword_ordered_ids, embedding_ordered_ids, embedding_weight=weight)
    floor = keyword_ordered_ids[:max_results]
    return list(dict.fromkeys(floor + fused))[:max(max_results, len(floor))]


# Deutsche Umlaut-Faltung: ae/oe/ue/ss-Schreibung UND ä/ö/ü/ß treffen sich.
# Dieselbe Abbildung wie der SQL-Ausdruck in schema.sql (Trigger
# knowledge_ai/ad/au) -- SQLite-Trigger koennen keine Python-Funktion
# aufrufen, ohne sie auf jeder schreibenden Verbindung zu registrieren
# (migrate_knowledge.py/build_embeddings.py/_add_phase2_nodes.py oeffnen die
# DB roh, ohne durch dieses Modul zu gehen), darum zwei Implementierungen.
# Gleichheit ist von
# tests/test_knowledge_hybrid_search.py::test_fold_de_matches_sql_fold belegt.
_FOLD_TABLE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def fold_de(text: str) -> str:
    """'Gründer' und 'Gruender' werden beide zu 'gruender'."""
    return text.lower().translate(_FOLD_TABLE)


_QUERY_WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüß0-9]+")


def _fts_phrase(word: str) -> str:
    """Ein Wort als FTS5-Phrase quoten (Anfuehrungszeichen verdoppelt escaped) --
    verhindert, dass ein Wort wie 'NOT' oder ein Bindestrich als FTS5-Operator
    statt als Suchtext interpretiert wird."""
    return '"' + word.replace('"', '""') + '"'


def _or_query(query: str) -> str:
    """Baut aus einer Anfrage eine FTS5-ODER-Verknuepfung ueber die einzelnen,
    gefalteten Woerter. Vorher lief MATCH mit mehreren Woertern als implizites
    UND -- ein einziges Wort, das nirgends vorkommt, killte die ganze Anfrage
    (gemessen: 4 von 6 Anfragen 0 Treffer trotz vorhandenem Knoten). Bei OR
    sortiert bm25/rank Dokumente mit mehr uebereinstimmenden Woertern weiter
    oben ein -- kein zusaetzliches Ranking noetig."""
    words = [fold_de(w) for w in _QUERY_WORD_RE.findall(query)]
    return " OR ".join(_fts_phrase(w) for w in words if w)


ZERO_HIT_LOG = Path(__file__).parent / "zero_hit_log.jsonl"
ZERO_HIT_LOG_MAX_BYTES = 200_000  # klein halten, gleiche Kappung wie recall_log.jsonl


def _log_zero_hit(query: str) -> None:
    """Haelt fest, welche Suchanfragen nichts fanden: Zeitpunkt, Anfragetext,
    Trefferzahl (=0) -- mehr nicht. Grundlage fuer eine spaetere, an echten
    Ausfaellen gemessene Entscheidung ueber Synonyme, statt das zu vermuten.
    Nie ein Grund, die Suche scheitern zu lassen -- Fehler werden verschluckt,
    wie beim analogen Recall-Log (knowledge_recall_hook.py::log_recall)."""
    try:
        entry = json.dumps({"ts": now_iso(), "query": query, "hits": 0}, ensure_ascii=False)
        if ZERO_HIT_LOG.exists() and ZERO_HIT_LOG.stat().st_size > ZERO_HIT_LOG_MAX_BYTES:
            lines = ZERO_HIT_LOG.read_text(encoding="utf-8").splitlines(keepends=True)
            ZERO_HIT_LOG.write_text("".join(lines[len(lines) // 2:]), encoding="utf-8")
        with ZERO_HIT_LOG.open("a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:
        pass


def _geltung_status(norm_rang, gilt_ab: str | None, gilt_bis: str | None, stichtag: str) -> str | None:
    """Geltung einer Norm zum Stichtag, nach dem Vorbild von normkraft.py::in_kraft
    (gilt_ab <= stichtag AND (gilt_bis IS NULL OR ...)) -- reiner ISO-Stringvergleich,
    keine datetime-Parsung, wie dort. Kanonische Bedeutung von gilt_bis
    (inklusiv, letzter Geltungstag) ist dort an EINER Stelle festgehalten,
    nicht hier wiederholt: normkraft.py::in_kraft.
    norm_rang IS NULL (Fakt) oder gilt_ab nicht gesetzt (Norm ohne Geltungsangabe)
    -> None, unveraendert wie vor diesem Auftrag."""
    if norm_rang is None or gilt_ab is None:
        return None
    if stichtag < gilt_ab:
        return "noch_nicht_in_kraft"
    if gilt_bis is not None and stichtag > gilt_bis:
        return "abgelaufen"
    return "in_kraft"


def knowledge_search(query: str, scope: str = "all", max_results: int = 10, *,
                     stichtag: str | None = None, nur_geltende: bool = False,
                     actor: str | None = None, model: str | None = None,
                     session: str | None = None) -> dict:
    """Hybrid-Suche ueber Wissensknoten: FTS5-Stichwortmatching (Woerter ODER-
    verknuepft, deutsch gefaltet) plus optionale Bedeutungs-Suche ueber lokale
    Embeddings (RRF-fusioniert). Ohne Vektoren (Tabelle fehlt oder leer) oder
    ohne erreichbares Ollama identisch zum reinen FTS5-Verhalten. Returns
    summaries (not full content) for token efficiency.

    Normen (norm_rang gesetzt) mit gilt_ab/gilt_bis werden gegen `stichtag`
    (ISO, Vorgabe: jetzt) geprueft: abgelaufene oder noch nicht in Kraft
    getretene rutschen ans Ende (nachrangig, nicht verborgen) und tragen
    "geltung"/"gilt_ab"/"gilt_bis" im Ergebnis. Mit nur_geltende=True werden
    sie ganz ausgeblendet. Fakten (norm_rang IS NULL) sind davon unberuehrt."""
    stichtag = stichtag or now_iso()
    conn = get_db()
    log_access(conn, None, "search", query=query, project_id=scope,
               actor=actor, model=model, session=session, status="started")
    fts_query = _or_query(query)
    if not fts_query:
        log_access(conn, None, "search", query=query, project_id=scope,
                   actor=actor, model=model, session=session)
        conn.close()
        return {"query": query, "scope": scope, "results": [], "count": 0}

    if scope == "all":
        fts_rows = conn.execute(
            """SELECT n.id, n.path, n.title, n.summary, n.project_id, n.norm_rang, n.gilt_ab, n.gilt_bis
               FROM knowledge_fts f
               JOIN knowledge_nodes n ON f.rowid = n.rowid
               WHERE knowledge_fts MATCH ?
               ORDER BY rank""",
            (fts_query,)
        ).fetchall()
        allowed_ids = None
    else:
        fts_rows = conn.execute(
            """SELECT n.id, n.path, n.title, n.summary, n.project_id, n.norm_rang, n.gilt_ab, n.gilt_bis
               FROM knowledge_fts f
               JOIN knowledge_nodes n ON f.rowid = n.rowid
               WHERE knowledge_fts MATCH ? AND n.project_id IN ('shared', ?)
               ORDER BY rank""",
            (fts_query, scope)
        ).fetchall()
        allowed_ids = {r["id"] for r in conn.execute(
            "SELECT id FROM knowledge_nodes WHERE project_id IN ('shared', ?)", (scope,)
        )}

    by_id = {r["id"]: r for r in fts_rows}
    fts_ordered_ids = [r["id"] for r in fts_rows]

    query_vec = embeddings.embed_text(query)
    embedding_ordered_ids = (
        _embedding_ranking(conn, "node", query_vec, allowed_ids) if query_vec else []
    )
    final_ids = _fuse_with_keyword_floor(fts_ordered_ids, embedding_ordered_ids, max_results)

    missing = [i for i in final_ids if i not in by_id]
    if missing:
        placeholders = ",".join("?" for _ in missing)
        for r in conn.execute(
            f"SELECT id, path, title, summary, project_id, norm_rang, gilt_ab, gilt_bis FROM knowledge_nodes WHERE id IN ({placeholders})",
            missing
        ):
            by_id[r["id"]] = r

    vorrang, nachrangig = [], []
    for i in final_ids:
        if i not in by_id:
            continue
        row = by_id[i]
        entry = {"id": row["id"], "path": row["path"], "title": row["title"],
                  "summary": row["summary"], "project": row["project_id"]}
        geltung = _geltung_status(row["norm_rang"], row["gilt_ab"], row["gilt_bis"], stichtag)
        if geltung in ("abgelaufen", "noch_nicht_in_kraft"):
            if nur_geltende:
                continue
            entry["geltung"] = geltung
            entry["gilt_ab"] = row["gilt_ab"]
            entry["gilt_bis"] = row["gilt_bis"]
            nachrangig.append(entry)
        else:
            vorrang.append(entry)
    results = vorrang + nachrangig
    if not results:
        _log_zero_hit(query)
    log_access(conn, results[0]["path"] if results else None, "search", query=query,
               project_id=scope, actor=actor, model=model, session=session)
    conn.close()
    return {"query": query, "scope": scope, "results": results, "count": len(results)}


SLUG_MAX_LEN = 40
_SLUG_CHAR_RE = re.compile(r"[^a-z0-9]+")


def _slugify(title: str) -> str:
    """Faltet deutsche Umlaute (fold_de), zerlegt uebrige Akzentzeichen
    (z.B. 'café' -> 'cafe') per NFKD-Normalisierung, ersetzt alles ausser
    [a-z0-9] durch '-', zieht Mehrfach-Trennstriche zusammen und kuerzt an
    der Wortgrenze statt hart bei SLUG_MAX_LEN mitten im Wort (Live-Befund:
    '...einstellungseb'). Nur ein einzelnes Wort, das schon laenger als
    SLUG_MAX_LEN ist, wird hart geschnitten -- sonst bliebe nichts uebrig."""
    decomposed = unicodedata.normalize("NFKD", fold_de(title))
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    raw = _SLUG_CHAR_RE.sub("-", without_accents).strip("-")
    raw = re.sub(r"-+", "-", raw)
    if len(raw) <= SLUG_MAX_LEN:
        return raw
    words = raw.split("-")
    if len(words[0]) >= SLUG_MAX_LEN:
        return words[0][:SLUG_MAX_LEN]
    out = words[0]
    for w in words[1:]:
        if len(out) + 1 + len(w) > SLUG_MAX_LEN:
            break
        out += "-" + w
    return out


# ─── P5: [[wikilink]] -> knowledge_relations ────────────────────────────────
# Billigster Anfang fuer das Karpathy-LLM-Wiki-Muster (eine Quelle beruehrt
# beim Einpflegen 10-15 Seiten statt eine einzelne anzulegen): die
# [[wikilink]]-Schreibweise aus den Memory-Dateien wird beim Schreiben zu
# echten Kanten aufgeloest, keine Aehnlichkeit wird erraten.
_WIKILINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")


def _extract_wikilinks(content: str) -> list[str]:
    """Deduplizierte, getrimmte Linkziele in Ursprungsreihenfolge."""
    targets = (m.strip() for m in _WIKILINK_RE.findall(content or ""))
    return list(dict.fromkeys(t for t in targets if t))


def _resolve_wikilink(conn: sqlite3.Connection, target: str) -> sqlite3.Row | None:
    """ziel darf Pfad oder Titel sein (Titel case-insensitiv)."""
    return conn.execute(
        "SELECT id, path, title FROM knowledge_nodes WHERE path = ? OR LOWER(title) = LOWER(?)",
        (target, target),
    ).fetchone()


def _sync_wikilinks(conn: sqlite3.Connection, source_path: str, content: str, *,
                    actor: str | None = None, model: str | None = None,
                    session: str | None = None) -> dict:
    """Legt fuer jedes aufloesbare [[ziel]] im content eine knowledge_relations-
    Zeile an. Unaufgeloeste Verweise werden NICHT geschrieben, sondern als
    Hinweis zurueckgegeben (ein Verweis ins Leere zeigt auf einen noch zu
    schreibenden Knoten, ist kein Fehler). Ein Selbstverweis erzeugt keine
    Kante -- deckt sich mit knowledge_relation_add(), das Selbstkanten
    ablehnt. Der Aufrufer ist verantwortlich, vorher bestehende Kanten dieses
    Knotens zu loeschen, falls es ein Update ist (siehe knowledge_update)."""
    creator, model, session = _identity(actor, model, session)
    relations_created: list[str] = []
    unresolved_links: list[str] = []
    seen_targets: set[str] = set()
    for target in _extract_wikilinks(content):
        row = _resolve_wikilink(conn, target)
        if not row:
            unresolved_links.append(target)
            continue
        if row["path"] == source_path or row["path"] in seen_targets:
            continue
        seen_targets.add(row["path"])
        timestamp = now_iso()
        conn.execute(
            """INSERT INTO knowledge_relations
               (id, source_path, target_path, relation_type, confidence, weight,
                evidence, source, creator, model, session, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (f"R-{uuid.uuid4().hex[:8]}", source_path, row["path"], "references",
             0.8, 1.0, f"[[{target}]] im content", "wikilink",
             creator, model, session, timestamp, timestamp),
        )
        relations_created.append(row["path"])
    return {"relations_created": relations_created, "unresolved_links": unresolved_links}


def _ensure_ast_chain(conn, missing_path: str, triggering_child_path: str,
                      project_id: str) -> None:
    """Legt jede fehlende Zwischenstufe von der Wurzel bis missing_path an
    (wie mkdir -p). Idempotent: vorhandene Stufen bleiben unangetastet.
    Titel = Pfadsegment, source kennzeichnet die automatische Herkunft samt
    dem Kind, das die Anlage ausgeloest hat."""
    current = ""
    for seg in [p for p in missing_path.split("/") if p]:
        current = f"{current}/{seg}"
        if conn.execute("SELECT 1 FROM knowledge_nodes WHERE path = ?", (current,)).fetchone():
            continue
        parent = current.rsplit("/", 1)[0] or "/"
        created_at = now_iso()
        conn.execute(
            """INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, content, level, tags, source, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4())[:8], current, parent, project_id, seg,
             f"Automatisch erzeugter Astknoten fuer {seg}", "",
             current.count("/") - 1, json.dumps([]),
             f"neuer_ast=True, automatisch erzeugt durch {triggering_child_path}",
             created_at, created_at),
        )


def _validate_geltung(norm_rang: int | None, gilt_ab: str | None, gilt_bis: str | None) -> str | None:
    """Prueft die drei Normschicht-Felder (schema.sql, N2/N3). Alle drei
    bleiben optional -- der Normalfall ist ein Fakt ohne Normangaben, NULL
    in norm_rang heisst weiterhin "kein Norm, sondern Fakt" (Plan §2).
    Nur bei gesetztem gilt_ab/gilt_bis wird ueberhaupt geparst, sonst No-op.
    Gibt eine sprechende Fehlermeldung zurueck oder None (gueltig)."""
    for name, value in (("gilt_ab", gilt_ab), ("gilt_bis", gilt_bis)):
        if value is None:
            continue
        try:
            datetime.fromisoformat(value)
        except ValueError:
            return f"{name} ist kein gueltiges ISO-8601-Datum/Zeitstempel: {value!r}"
    if gilt_ab is not None and gilt_bis is not None and gilt_bis < gilt_ab:
        return f"gilt_bis ({gilt_bis!r}) liegt vor gilt_ab ({gilt_ab!r})."
    return None


def _validate_anlass(anlass: str) -> str | None:
    """Sprechende Ablehnung statt stillem Erfolg oder 500 bei unbekanntem
    anlass (Auftrag 2026-08-06). Gibt eine Fehlermeldung mit der erlaubten
    Liste zurueck, oder None wenn gueltig."""
    if anlass not in ALLOWED_ANLASS:
        return (f"anlass unbekannt: {anlass!r}. Erlaubt: {sorted(ALLOWED_ANLASS)}.")
    return None


# \w{3,}: kurze Fuellwoerter (der/die/aus/of/and/...) sind in praktisch jeder
# Sprache 1-2 Zeichen lang, darum als Rauschgrenze fuer den Wortlauf-
# Vergleich geeignet, ohne eine Sprache konkret zu benennen.
_QUELLTOKEN_RE = re.compile(r"\w{3,}", re.UNICODE)
_MIN_ZITAT_LAUF = 6  # so viele Woerter am Stueck woertlich = Zitat, kein Zufall
# Ein Pfad/eine URL/ein Hash/ein Datum ist eine ueberpruefbare Fundstelle,
# unabhaengig davon, wie sie sprachlich eingeleitet wird -- rein an der
# ZEICHENFORM erkannt (Schraegstrich, Dateiendung, URL-Schema, Hex-Lauf,
# ISO-Datum), nicht am umgebenden Wortlaut.
_FUNDSTELLE_RE = re.compile(
    r"https?://\S+|[^\s]+/[^\s]+|\.[A-Za-z0-9]{2,4}\b|\b[0-9a-fA-F]{7,40}\b|"
    r"\b\d{4}-\d{2}-\d{2}\b"
)


def _inhaltstokens(*teile: str) -> list:
    return [t.lower() for t in _QUELLTOKEN_RE.findall(" ".join(t or "" for t in teile))]


def _laengster_gemeinsamer_lauf(a: list, b: list) -> int:
    return difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(
        0, len(a), 0, len(b)
    ).size


def _validate_source_provenance(source: str, title: str, summary: str, content: str) -> str | None:
    """Lehnt eine Herkunft ab, die im Kern nur den Knoten selbst zitiert
    (Lehre L-7aad34, Auftrag 2026-08-06, Befund 1 -- Tautologie: source
    'erzeugt aus Rohmaterial ... "Man hoert, dass die Sperrandrohung ..."'
    wiederholte woertlich genau den Inhalt, den sie belegen sollte).

    STRUKTURELL statt Wortliste (sprachunabhaengig, siehe Modul-Docstring von
    einschleusung.py fuer dieselbe Abwaegung an anderer Stelle): geprueft wird
    NICHT irgendein Bedeutungs-Ueberlappung (die schlaegt staendig zu Unrecht
    an -- ein Dateipfad wie 'buckeberg/.../2026-08-05-endrunde-abgleich.md'
    teilt zwangslaeufig Themenwoerter mit dem Titel, das ist erwuenscht, kein
    Zitieren-sich-selbst), sondern ein LAUF von mindestens sechs
    aufeinanderfolgenden Woertern, die woertlich sowohl in source als auch in
    Titel/Zusammenfassung/Inhalt DESSELBEN Knotens vorkommen. Reiner
    Zeichenfolgen-Abgleich (difflib, laengster gemeinsamer Block), kein
    Woerterbuch -- schlaegt in jeder Sprache/Schrift gleich an.

    ZWEITE BEDINGUNG, das eigentliche Herzstueck gegen Falschalarme (Auftrag
    Punkt 3, Falschalarm teurer als Durchlass): ein langer Wortlauf allein
    genuegt NICHT. Erst wenn source zusaetzlich KEINE ueberpruefbare
    Fundstelle traegt (kein Pfad, keine URL, kein Hash, kein Datum -- an der
    Zeichenform erkannt, s. _FUNDSTELLE_RE), gilt der Lauf als Beleg, dass
    source nichts ausserhalb des Knotens nennt. Ein Dateipfad, der zufaellig
    Themenwoerter mit dem Titel teilt, hat trotzdem eine Fundstelle und geht
    frei durch -- gemessen an den 290 Bestandsknoten der Produktions-DB, vor
    dieser zweiten Bedingung waren es 22 Falschalarme allein durch geteilte
    Pfad-/Dateinamen-Woerter.

    Bewusst NICHT erfasst: eine knappe, aber nicht-zitierende Angabe wie
    'Geruecht aus der Kantine' (kein langer woertlicher Lauf mit dem Inhalt,
    also greift die erste Bedingung nie) -- ob eine solche Kurzform generell
    genug Substanz hat, ist ohne Sprachverstaendnis nicht zuverlaessig zu
    entscheiden und bleibt bewusst durch, statt hart abgelehnt zu werden."""
    quelle = _inhaltstokens(source)
    if len(quelle) < _MIN_ZITAT_LAUF:
        return None  # zu kurz fuer einen verlaesslichen Zitat-Befund
    beleg = _inhaltstokens(title, summary, content)
    lauf = _laengster_gemeinsamer_lauf(quelle, beleg)
    if lauf < _MIN_ZITAT_LAUF:
        return None
    if _FUNDSTELLE_RE.search(source):
        return None  # traegt eine ueberpruefbare Fundstelle -- kein Verdacht
    return (
        f"source wirkt selbstbezueglich: {lauf} Woerter am Stueck stehen "
        "woertlich sowohl in source als auch im eigenen Titel/Zusammenfassung/"
        "Inhalt dieses Knotens, ohne dass source einen Pfad, eine URL, einen "
        "Hash oder ein Datum nennt. Herkunft ausserhalb des Knotens benennen "
        "(Datei, Person, Ort, URL, Sitzungsprotokoll), nicht den Inhalt "
        "zurueckspiegeln."
    )


def knowledge_add(parent_path: str, title: str, summary: str,
                  content: str = "", project_id: str = "shared",
                  tags: list | None = None, source: str = "", *,
                  neuer_ast: bool = False,
                  norm_rang: int | None = None, gilt_ab: str | None = None,
                  gilt_bis: str | None = None, anlass: str = "unbekannt",
                  actor: str | None = None, model: str | None = None,
                  session: str | None = None) -> dict:
    """Add a new knowledge node to the tree. Rejects an unknown parent_path
    unless neuer_ast=True (see U1 im Plan 2026-08-05, P1: erfundene Aeste
    streuten Wissen an Stellen, die nie wieder abgerufen wurden).

    anlass: was hat den Eintrag ausgeloest -- siehe ALLOWED_ANLASS oben.
    'selbst'/'betreiber' sind selbstberichtet vom Aufrufer, nicht geprueft;
    'hook'/'skript' objektiv, weil der Aufrufweg sie kennt. Unbekannter Wert
    wird abgelehnt (sprechender Fehler, kein stiller Erfolg)."""
    anlass_fehler = _validate_anlass(anlass)
    if anlass_fehler:
        return {"error": anlass_fehler}

    fixed = unmangle_knowledge_fields({
        "title": title, "summary": summary, "content": content, "tags": tags, "source": source,
    })
    title, summary = fixed["title"], fixed["summary"]
    content, tags, source = fixed["content"], fixed["tags"], fixed["source"]

    if not source.strip():
        return {
            "error": "source fehlt: Herkunft des Knotens angeben (aus welcher Datei/welchem Lauf er stammt). "
                     "Beispiel: 'erzeugt aus /pfad/zur/datei.md (Stand 2026-08-05T23:40:00+02:00)'.",
        }

    provenienz_fehler = _validate_source_provenance(source, title, summary, content)
    if provenienz_fehler:
        return {"error": provenienz_fehler}

    geltung_fehler = _validate_geltung(norm_rang, gilt_ab, gilt_bis)
    if geltung_fehler:
        return {"error": geltung_fehler}

    conn = get_db()
    parent_path = parent_path.rstrip("/") or "/"

    # Derive path from parent + slugified title
    slug = _slugify(title)
    node_path = f"{parent_path}/{slug}" if parent_path != "/" else f"/{slug}"

    if parent_path != "/":
        parent_row = conn.execute(
            "SELECT 1 FROM knowledge_nodes WHERE path = ?", (parent_path,)
        ).fetchone()
        if not parent_row:
            if not neuer_ast:
                all_paths = [r[0] for r in conn.execute("SELECT path FROM knowledge_nodes")]
                conn.close()
                return {
                    "error": f"Elternpfad existiert nicht: {parent_path}. "
                             f"Mit neuer_ast=True bewusst einen neuen Ast anlegen.",
                    "vorhandene_pfade": difflib.get_close_matches(parent_path, all_paths, n=5),
                }
            # neuer_ast=True: fehlende Zwischenstufen mit anlegen (mkdir -p),
            # statt eine Waise zu hinterlassen -- genau die Klasse, gegen die
            # die Elternpfad-Pruefung oben gebaut wurde.
            _ensure_ast_chain(conn, parent_path, node_path, project_id)

    # Check for duplicates
    existing = conn.execute("SELECT id FROM knowledge_nodes WHERE path = ?", (node_path,)).fetchone()
    if existing:
        conn.close()
        return {"error": f"Node already exists at path: {node_path}", "existing_id": existing["id"]}

    # Calculate level
    level = node_path.count("/") - 1

    node_id = str(uuid.uuid4())[:8]
    log_access(conn, node_path, "add", project_id=project_id,
               actor=actor, model=model, session=session, status="started")
    created_at = now_iso()
    conn.execute(
        """INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, content, level, tags, source, created_at, updated_at, norm_rang, gilt_ab, gilt_bis, anlass)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (node_id, node_path, parent_path, project_id, title, summary, content,
         level, json.dumps(tags or []), source, created_at, created_at,
         norm_rang, gilt_ab, gilt_bis, anlass)
    )
    log_access(conn, node_path, "add", project_id=project_id,
               actor=actor, model=model, session=session,
               affected_row={
                   "id": node_id, "path": node_path, "parent_path": parent_path,
                   "project_id": project_id, "title": title, "summary": summary,
                   "content": content, "level": level, "tags": tags or [],
                   "source": source, "created_at": created_at, "updated_at": created_at,
                   "norm_rang": norm_rang, "gilt_ab": gilt_ab, "gilt_bis": gilt_bis,
                   "anlass": anlass,
               })
    wikilinks = _sync_wikilinks(conn, node_path, content, actor=actor, model=model, session=session)
    conn.commit()
    conn.close()
    return {"id": node_id, "path": node_path, "status": "created", **wikilinks}


def knowledge_update(node_id: str, summary: str | None = None,
                     content: str | None = None, tags: list | None = None, *,
                     norm_rang: int | None = None, gilt_ab: str | None = None,
                     gilt_bis: str | None = None,
                     actor: str | None = None, model: str | None = None,
                     session: str | None = None) -> dict:
    """Update an existing knowledge node. Like summary/content/tags, only
    given norm_rang/gilt_ab/gilt_bis fields are changed -- a node stays frozen
    at "no Normschicht values" until one is explicitly passed."""
    conn = get_db()
    row = conn.execute("SELECT * FROM knowledge_nodes WHERE id = ? OR path = ?", (node_id, node_id)).fetchone()
    if not row:
        conn.close()
        return {"error": f"Node not found: {node_id}"}

    # Grenzwertpruefung braucht beide Werte im Kontext: wer nur gilt_bis
    # aendert, wird trotzdem gegen das vorhandene gilt_ab geprueft (und
    # umgekehrt) -- sonst liesse sich die Reihenfolge durch zwei getrennte
    # Aufrufe umgehen.
    effektiv_gilt_ab = gilt_ab if gilt_ab is not None else row["gilt_ab"]
    effektiv_gilt_bis = gilt_bis if gilt_bis is not None else row["gilt_bis"]
    geltung_fehler = _validate_geltung(norm_rang, effektiv_gilt_ab, effektiv_gilt_bis)
    if geltung_fehler:
        conn.close()
        return {"error": geltung_fehler}

    # Derselbe Aufrufer-Fehler wie bei knowledge_add moeglich (Parametergrenze
    # verrutscht ins Textfeld) -- nur uebergebene Felder unmangeln.
    given = {k: v for k, v in {"summary": summary, "content": content, "tags": tags}.items()
             if v is not None}
    if given:
        fixed = unmangle_knowledge_fields(given)
        summary = fixed.get("summary", summary)
        content = fixed.get("content", content)
        tags = fixed.get("tags", tags)

    updates = []
    params = []
    if summary is not None:
        updates.append("summary = ?")
        params.append(summary)
    if content is not None:
        updates.append("content = ?")
        params.append(content)
    if tags is not None:
        updates.append("tags = ?")
        params.append(json.dumps(tags))
    if norm_rang is not None:
        updates.append("norm_rang = ?")
        params.append(norm_rang)
    if gilt_ab is not None:
        updates.append("gilt_ab = ?")
        params.append(gilt_ab)
    if gilt_bis is not None:
        updates.append("gilt_bis = ?")
        params.append(gilt_bis)

    updates.append("updated_at = ?")
    params.append(now_iso())
    params.append(row["id"])
    # Lost-Update-Schutz: die WHERE-Klausel bindet an den beim SELECT oben
    # gelesenen updated_at. Hat zwischenzeitlich ein anderer Schreiber
    # denselben Knoten geaendert, trifft das UPDATE null Zeilen -- das ist
    # das Signal, nicht ein Fehler der SQL selbst.
    # ponytail: now_iso() ist sekundengenau -- zwei Schreiber in derselben
    # Sekunde kollidieren zufaellig auf denselben Wert und der Schutz greift
    # dann nicht. Aufwertung braeuchte eine Versions-Spalte, das ist eine
    # Schema-Aenderung und ausserhalb dieses Auftrags.
    expected_updated_at = row["updated_at"]
    params.append(expected_updated_at)

    log_access(conn, row["path"], "update", project_id=row["project_id"],
               actor=actor, model=model, session=session, status="started")
    cursor = conn.execute(
        f"UPDATE knowledge_nodes SET {', '.join(updates)} WHERE id = ? AND updated_at = ?",
        params,
    )
    if cursor.rowcount == 0:
        conn.rollback()
        current = conn.execute("SELECT * FROM knowledge_nodes WHERE id = ?", (row["id"],)).fetchone()
        log_access(conn, row["path"], "update", project_id=row["project_id"],
                   actor=actor, model=model, session=session, status="failed")
        conn.close()
        return {
            "error": "Conflict: node was modified by another writer since it was read",
            "id": row["id"],
            "expected_updated_at": expected_updated_at,
            "current": dict(current) if current else None,
        }

    # P4: ein veralteter Vektor ist schlechter als gar keiner -- die
    # Hybridsuche gewichtet ihn gutgläubig mit, waehrend sie einen fehlenden
    # sauber verkraftet (test_knowledge_hybrid_search.py). Nur bei
    # Textaenderung loeschen; ein reiner tags-Wechsel laesst ihn stehen.
    if summary is not None or content is not None:
        conn.execute("DELETE FROM knowledge_embeddings WHERE kind = 'node' AND ref_id = ?", (row["id"],))

    wikilinks = {"relations_created": [], "unresolved_links": []}
    if content is not None:
        # P5: Kanten dieses Knotens komplett neu ziehen, sonst ueberlebt ein
        # aus dem content entfernter Verweis als Karteileiche.
        conn.execute("DELETE FROM knowledge_relations WHERE source_path = ?", (row["path"],))
        wikilinks = _sync_wikilinks(conn, row["path"], content, actor=actor, model=model, session=session)

    updated_row = conn.execute("SELECT * FROM knowledge_nodes WHERE id = ?", (row["id"],)).fetchone()
    log_access(conn, row["path"], "update", project_id=row["project_id"],
               actor=actor, model=model, session=session,
               affected_row=dict(updated_row) if updated_row else None)
    conn.commit()
    conn.close()
    return {"id": row["id"], "status": "updated", **wikilinks}


def _relation_node(conn: sqlite3.Connection, value: str,
                   scope: str | None = None) -> sqlite3.Row:
    row = conn.execute(
        "SELECT id,path,project_id,title FROM knowledge_nodes WHERE id=? OR path=?",
        (value, value),
    ).fetchone()
    if not row:
        raise ValueError(f"Knowledge node not found: {value}")
    if scope and scope != "all" and row["project_id"] not in ("shared", scope):
        raise ValueError(f"Node {value} is outside scope shared|{scope}")
    return row


def _relation_values(relation_type: str, confidence: float, weight: float) -> None:
    if relation_type not in RELATION_TYPES:
        raise ValueError(f"Invalid relation type: {relation_type}")
    if not 0.0 <= float(confidence) <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    if float(weight) < 0.0:
        raise ValueError("weight must be >= 0")


def knowledge_relation_add(source_node: str, target_node: str, relation_type: str,
                           confidence: float = 0.8, weight: float = 1.0,
                           evidence: str = "", source: str = "",
                           scope: str = "all", creator: str | None = None,
                           model: str | None = None, session: str | None = None) -> dict:
    """Create one explicit evidenced edge; never infers similarity."""
    _relation_values(relation_type, confidence, weight)
    conn = get_db()
    source_row = _relation_node(conn, source_node, scope)
    target_row = _relation_node(conn, target_node, scope)
    if source_row["path"] == target_row["path"]:
        conn.close()
        raise ValueError("Self-relations are not allowed")
    creator, model, session = _identity(creator, model, session)
    relation_id = f"R-{uuid.uuid4().hex[:8]}"
    timestamp = now_iso()
    log_access(conn, source_row["path"], "relation_add", query=relation_id,
               project_id=source_row["project_id"], actor=creator, model=model,
               session=session, status="started")
    try:
        conn.execute(
            """INSERT INTO knowledge_relations
               (id,source_path,target_path,relation_type,confidence,weight,evidence,source,
                creator,model,session,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (relation_id, source_row["path"], target_row["path"], relation_type,
             float(confidence), float(weight), evidence, source, creator, model, session,
             timestamp, timestamp),
        )
    except sqlite3.IntegrityError as error:
        log_access(conn, source_row["path"], "relation_add", query=relation_id,
                   project_id=source_row["project_id"], actor=creator, model=model,
                   session=session, status="failed")
        conn.close()
        raise ValueError("Relation already exists or violates the knowledge contract") from error
    log_access(conn, source_row["path"], "relation_add", query=relation_id,
               project_id=source_row["project_id"], actor=creator, model=model, session=session,
               affected_row={
                   "id": relation_id, "source_path": source_row["path"],
                   "target_path": target_row["path"], "relation_type": relation_type,
                   "confidence": float(confidence), "weight": float(weight),
                   "evidence": evidence, "source": source, "creator": creator,
                   "model": model, "session": session,
                   "created_at": timestamp, "updated_at": timestamp,
               })
    conn.close()
    return {"id": relation_id, "status": "created", "source_path": source_row["path"],
            "target_path": target_row["path"], "relation_type": relation_type}


def knowledge_relation_list(node: str | None = None,
                            relation_type: str | None = None,
                            scope: str = "all", *, actor: str | None = None,
                            model: str | None = None, session: str | None = None) -> dict:
    """List explicit relations, optionally incident to one node."""
    if relation_type and relation_type not in RELATION_TYPES:
        raise ValueError(f"Invalid relation type: {relation_type}")
    conn = get_db()
    clauses, params = [], []
    node_row = _relation_node(conn, node, scope) if node else None
    if node_row:
        clauses.append("(r.source_path=? OR r.target_path=?)")
        params.extend([node_row["path"], node_row["path"]])
    if relation_type:
        clauses.append("r.relation_type=?")
        params.append(relation_type)
    if scope != "all":
        clauses.append("s.project_id IN ('shared',?) AND t.project_id IN ('shared',?)")
        params.extend([scope, scope])
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    log_access(conn, node_row["path"] if node_row else None, "relation_list",
               project_id=scope, actor=actor, model=model, session=session, status="started")
    rows = conn.execute(
        """SELECT r.*,s.title AS source_title,t.title AS target_title
           FROM knowledge_relations r
           JOIN knowledge_nodes s ON s.path=r.source_path
           JOIN knowledge_nodes t ON t.path=r.target_path""" + where + " ORDER BY r.updated_at DESC",
        params,
    ).fetchall()
    log_access(conn, node_row["path"] if node_row else None, "relation_list",
               project_id=scope, actor=actor, model=model, session=session)
    conn.close()
    return {"relations": [dict(row) for row in rows], "count": len(rows)}


def knowledge_relation_update(relation_id: str, relation_type: str | None = None,
                              confidence: float | None = None, weight: float | None = None,
                              evidence: str | None = None, source: str | None = None,
                              creator: str | None = None, model: str | None = None,
                              session: str | None = None) -> dict:
    conn = get_db()
    row = conn.execute("SELECT * FROM knowledge_relations WHERE id=?", (relation_id,)).fetchone()
    if not row:
        conn.close()
        return {"error": f"Relation not found: {relation_id}"}
    next_type = relation_type or row["relation_type"]
    next_confidence = row["confidence"] if confidence is None else confidence
    next_weight = row["weight"] if weight is None else weight
    _relation_values(next_type, next_confidence, next_weight)
    creator, model, session = _identity(creator, model, session)
    values = {
        "relation_type": next_type, "confidence": float(next_confidence),
        "weight": float(next_weight), "evidence": row["evidence"] if evidence is None else evidence,
        "source": row["source"] if source is None else source,
        "creator": creator or row["creator"], "model": model or row["model"],
        "session": session or row["session"], "updated_at": now_iso(),
    }
    log_access(conn, row["source_path"], "relation_update", query=relation_id,
               actor=creator, model=model, session=session, status="started")
    try:
        conn.execute(
            """UPDATE knowledge_relations SET relation_type=:relation_type,
               confidence=:confidence,weight=:weight,evidence=:evidence,source=:source,
               creator=:creator,model=:model,session=:session,updated_at=:updated_at
               WHERE id=:id""",
            values | {"id": relation_id},
        )
    except sqlite3.IntegrityError as error:
        log_access(conn, row["source_path"], "relation_update", query=relation_id,
                   actor=creator, model=model, session=session, status="failed")
        conn.close()
        raise ValueError("Updated relation would violate the knowledge contract") from error
    log_access(conn, row["source_path"], "relation_update", query=relation_id,
               actor=creator, model=model, session=session,
               affected_row=values | {"id": relation_id, "source_path": row["source_path"],
                                       "target_path": row["target_path"]})
    conn.close()
    return {"id": relation_id, "status": "updated"}


def knowledge_relation_remove(relation_id: str, *, actor: str | None = None,
                              model: str | None = None, session: str | None = None) -> dict:
    conn = get_db()
    row = conn.execute("SELECT * FROM knowledge_relations WHERE id=?", (relation_id,)).fetchone()
    if not row:
        conn.close()
        return {"error": f"Relation not found: {relation_id}"}
    log_access(conn, row["source_path"], "relation_remove", query=relation_id,
               actor=actor, model=model, session=session, status="started")
    conn.execute("DELETE FROM knowledge_relations WHERE id=?", (relation_id,))
    log_access(conn, row["source_path"], "relation_remove", query=relation_id,
               actor=actor, model=model, session=session)
    conn.close()
    return {"id": relation_id, "status": "removed"}


def _build_field_tag_re(fields: tuple) -> re.Pattern:
    """Baut die Feldgrenzen-Regex fuer eine gegebene Feldnamen-Menge.

    Zwei Tag-Stile kommen in der Wildnis vor: plain `<root_cause>...</root_cause>`
    und der antml-Tool-Call-Stil `<parameter name="root_cause">...</parameter>`
    (Schliesser dort ist generisch `</parameter>`, traegt keinen Feldnamen).
    Gemeinsame Engine fuer lesson_record UND knowledge_add -- beide leiden am
    selben Aufrufer-Fehler (Parametergrenze rutscht in den vorherigen Textwert),
    nur mit unterschiedlichen Feldnamen.
    """
    alt = "|".join(fields)
    return re.compile(
        r'<parameter\s+name="(?P<pname>' + alt + r')"\s*>'
        r"|</parameter>"
        r"|<(?P<oname>" + alt + r")>"
        r"|</(?P<cname>" + alt + r")>"
    )


LESSON_TEXT_FIELDS = ("description", "root_cause", "resolution", "prevention",
                      "severity", "projects", "node_path", "type")
_FIELD_TAG = _build_field_tag_re(LESSON_TEXT_FIELDS)

KNOWLEDGE_TEXT_FIELDS = ("content", "tags", "source", "summary", "title")
_KNOWLEDGE_FIELD_TAG = _build_field_tag_re(KNOWLEDGE_TEXT_FIELDS)

# "parameter" bewusst NICHT hier: ein `<parameter name="root_cause">` kann auch
# ein Zitat im Fliesstext sein (z.B. eine Lesson, die diesen Bug beschreibt).
# Echte, an einer Feldgrenze stehende parameter-Tags werden bereits von
# _split_tagged konsumiert und tauchen danach gar nicht mehr auf; ein
# uebrigbleibender parameter-Tag ist also so gut wie sicher ein Zitat und
# muss stehen bleiben. invoke/function_calls/antml:* sind dagegen reines
# Aufruf-Rauschen, das nie sinnvoll zitiert wird.
_CALL_NOISE = re.compile(r"</?(invoke|function_calls|antml:\w+)[^>]*>")


def _is_boundary_tag(value: str, m: re.Match) -> bool:
    """Nur Tags an einer echten Feldgrenze zaehlen, nicht als Zitat im Fliesstext.

    Eine echte verrutschte Feldgrenze steht immer isoliert: der Aufrufer
    schliesst einen Parameter und oeffnet sofort den naechsten, nie mitten in
    einem Satz. Ein oeffnender Tag zaehlt daher nur, wenn direkt davor (nur
    Leerraum dazwischen) Zeilenanfang/Stringanfang ODER das Ende eines anderen
    Tags (`>`) steht; ein schliessender Tag nur, wenn direkt danach
    Zeilenende/Stringende ODER der Anfang eines anderen Tags (`<`) folgt. Das
    deckt sowohl "jeder Tag auf eigener Zeile" als auch "Tags ohne Trenner
    aneinandergereiht" ab, verwirft aber einen Tag, der als Beispiel mitten in
    einem Satz zitiert wird (z.B. eine Lesson, die den Bug selbst beschreibt)
    — dort steht vor UND nach dem Tag echter Satztext auf derselben Zeile.
    """
    is_open = m.group("pname") is not None or m.group("oname") is not None
    if is_open:
        j = m.start()
        while j > 0 and value[j - 1] in " \t":
            j -= 1
        return j == 0 or value[j - 1] in "\n>"
    j = m.end()
    while j < len(value) and value[j] in " \t":
        j += 1
    return j == len(value) or value[j] in "\n<"


def _split_tagged(value: str, field_tag_re: re.Pattern = _FIELD_TAG) -> dict:
    """Zerlegt einen Wert an echten Feld-Tag-Grenzen (siehe _is_boundary_tag).

    Kein Zeichen NUTZTEXT geht verloren: jeder Textanteil, der keiner erkannten
    Feldgrenze zugeordnet werden kann (z.B. weil das Zielfeld gerade `current`
    None ist — etwa bei einem verwaisten schliessenden Tag), landet unter
    "_head" statt verworfen zu werden. Einzige Ausnahme: ein Anteil, der
    zwischen zwei Tags liegt UND nur aus Leerraum besteht, ist der
    Formatierungs-Zwischenraum der Tags selbst (kein Inhalt) und wird nicht
    extra angehaengt — sonst haeuften sich bei mehreren aufeinanderfolgenden
    Tags leere Zeilen im Ursprungsfeld an.

    field_tag_re: welche Feldnamen als Grenze zaehlen -- default die Lesson-
    Felder (_FIELD_TAG), knowledge_add nutzt _KNOWLEDGE_FIELD_TAG (siehe
    unmangle_knowledge_fields).
    """
    matches = [m for m in field_tag_re.finditer(value) if _is_boundary_tag(value, m)]
    out: dict[str, str] = {}
    current: str | None = None
    pos = 0
    head_parts: list[str] = []
    for m in matches:
        segment = value[pos:m.start()]
        if current is None:
            if segment.strip():
                head_parts.append(segment)
        else:
            out[current] = out.get(current, "") + segment
        pname, oname, cname = m.group("pname"), m.group("oname"), m.group("cname")
        is_open = pname is not None or oname is not None
        name = pname or oname or cname  # cname/name may be None for bare </parameter>
        current = name if is_open else None
        pos = m.end()
    tail = value[pos:]
    if current is None:
        if tail.strip():
            head_parts.append(tail)
    else:
        out[current] = out.get(current, "") + tail
    out["_head"] = "".join(head_parts)
    return out


def unmangle_lesson_fields(fields: dict) -> dict:
    """Repariert verrutschte Parametergrenzen in Lesson-Aufrufen.

    Schreibt ein Aufrufer einen langen mehrzeiligen Wert, rutscht die Grenze zum
    naechsten Parameter gelegentlich ins Textfeld — dann steht z.B. der komplette
    `root_cause` als `<root_cause>…</root_cause>` im `description`-Wert. 21 der
    218 Lessons waren so verstuemmelt, ausgerechnet die laengsten. Hier werden die
    Tags erkannt und die Anteile auf die richtigen Spalten verteilt; nur leere
    Zielfelder werden befuellt, ein echter Wert gewinnt immer. Kein Zeichen geht
    verloren: Text, dessen Zielfeld schon belegt ist oder der sich keinem Feld
    zuordnen laesst, bleibt im Ursprungsfeld erhalten statt geloescht zu werden.
    """
    out = dict(fields)
    for name in LESSON_TEXT_FIELDS:
        val = out.get(name)
        if not isinstance(val, str) or not _FIELD_TAG.search(val):
            continue
        parts = _split_tagged(val)
        head = parts.pop("_head", "")
        if not parts:
            # Kein anderes Feld zu befuellen -- entweder gar keine echte
            # Feldgrenze (dann ist head == val, No-op) oder eine selbstbezuegliche
            # Grenze wie eine verwaiste </description> ohne Gegenstueck (dann hat
            # head die Tag-Zeichen schon abgezogen, siehe efa1f597/1a714374).
            # Beide Faelle: head zurueckschreiben statt still zu ueberspringen.
            out[name] = head
            continue
        leftover = []
        for key, text in parts.items():
            stripped = text.strip()
            if not stripped:
                continue
            current_val = str(out.get(key) or "").strip()
            # severity traegt immer den Schema-Default "medium", auch wenn nie explizit
            # gesetzt — von einem echten Wert nicht unterscheidbar. Ein aus dem Tag
            # extrahierter gueltiger Enum-Wert gewinnt deshalb hier gegen den Default.
            beats_default = (key == "severity" and current_val == "medium"
                             and stripped in ("critical", "high", "medium", "low"))
            if key != name and (not current_val or beats_default):
                out[key] = stripped if key == "severity" else text
            else:
                leftover.append(text)
        out[name] = head + ("\n" + "\n".join(leftover) if leftover else "")
    for name in LESSON_TEXT_FIELDS:
        if isinstance(out.get(name), str):
            out[name] = _CALL_NOISE.sub("", out[name]).strip()
    if isinstance(out.get("projects"), str):
        try:
            out["projects"] = json.loads(out["projects"])
        except (ValueError, TypeError):
            out["projects"] = [p.strip(' "\'') for p in out["projects"].strip('[]').split(",") if p.strip(' "\'')]
    return out


def unmangle_knowledge_fields(fields: dict) -> dict:
    """Repariert verrutschte Parametergrenzen in knowledge_add/knowledge_update-
    Aufrufen -- derselbe Aufrufer-Fehler wie bei unmangle_lesson_fields, nur mit
    Knowledge-Feldnamen: der komplette content/tags/source landet dann als
    `<content>...</content>` etc. im summary-Wert (gemessen an efa1f597,
    7781dea1, 2a6098d1, c60b1b46, 3a978881, 5d899304). Nur leere Zielfelder
    werden befuellt, ein echter Wert gewinnt immer; kein Zeichen geht verloren.
    """
    out = dict(fields)
    for name in KNOWLEDGE_TEXT_FIELDS:
        val = out.get(name)
        if not isinstance(val, str) or not _KNOWLEDGE_FIELD_TAG.search(val):
            continue
        parts = _split_tagged(val, _KNOWLEDGE_FIELD_TAG)
        head = parts.pop("_head", "")
        if not parts:
            # Kein anderes Feld zu befuellen -- entweder gar keine echte
            # Feldgrenze (dann ist head == val, No-op) oder eine selbstbezuegliche
            # Grenze wie eine verwaiste </summary>/</content> ohne Gegenstueck
            # (dann hat head die Tag-Zeichen schon abgezogen, siehe 1a714374/
            # 6e22536d/698fc6b9/cbb40e73). Beide Faelle: head zurueckschreiben
            # statt still zu ueberspringen.
            out[name] = head
            continue
        leftover = []
        for key, text in parts.items():
            stripped = text.strip()
            if not stripped:
                continue
            current_val = out.get(key)
            has_value = bool(current_val) if isinstance(current_val, list) else bool(str(current_val or "").strip())
            if key != name and not has_value:
                out[key] = stripped if key == "tags" else text
            else:
                leftover.append(text)
        out[name] = head + ("\n" + "\n".join(leftover) if leftover else "")
    for name in KNOWLEDGE_TEXT_FIELDS:
        if isinstance(out.get(name), str):
            out[name] = _CALL_NOISE.sub("", out[name]).strip()
    if isinstance(out.get("tags"), str):
        try:
            out["tags"] = json.loads(out["tags"])
        except (ValueError, TypeError):
            out["tags"] = [p.strip(' "\'') for p in out["tags"].strip("[]").split(",") if p.strip(' "\'')]
    return out


MAX_REPEAT_PARAGRAPHS = 5
_REPEAT_MARKER_RE = re.compile(r"\n\n--- Wiederholung ([0-9T:+\-]+) ---\n")


def _append_repetition(base_description: str, new_text: str, when: str,
                       cap: int = MAX_REPEAT_PARAGRAPHS) -> str:
    """Haengt einen datierten Wiederholungs-Absatz an eine bestehende Beschreibung an.

    Gedeckelt auf die `cap` juengsten Wiederholungen — sonst waechst ein Eintrag
    unbegrenzt und wird unlesbar. Der urspruengliche Beschreibungstext (vor der
    ersten Wiederholung) bleibt immer erhalten, nur ueberzaehlige Wiederholungen
    fallen von vorne heraus.
    """
    parts = _REPEAT_MARKER_RE.split(base_description)
    head = parts[0]
    reps = list(zip(parts[1::2], parts[2::2]))
    reps.append((when, new_text.strip()))
    reps = reps[-cap:]
    out = head
    for date, text in reps:
        out += f"\n\n--- Wiederholung {date} ---\n{text}"
    return out


_STOPWORDS_DE = {
    "der", "die", "das", "und", "oder", "ein", "eine", "einer", "eines", "einem",
    "einen", "ist", "sind", "war", "waren", "im", "in", "am", "an", "auf", "zu",
    "von", "mit", "fuer", "für", "den", "dem", "des", "als", "auch", "nicht",
    "sich", "es", "bei", "aus", "wurde", "wurden", "werden", "sein", "seine",
    "seiner", "seinem", "je", "jede", "jeder", "jedes", "noch", "nur", "schon",
    "dann", "aber", "wenn", "hat", "hatte", "haben", "kann", "koennen", "können",
    "muss", "muessen", "müssen", "wird", "wo", "was", "wie", "so", "um", "ueber",
    "über", "nach", "vor", "durch",
}
_WORD_RE = re.compile(r"[a-zA-ZäöüÄÖÜß]+")
SIMILARITY_THRESHOLD = 0.18  # kalibriert gegen den Bestand, siehe PLAN/Bericht


def _tokenize(text: str) -> set:
    return {w for w in (m.lower() for m in _WORD_RE.findall(text))
            if w not in _STOPWORDS_DE and len(w) > 2}


def _find_similar_lesson(conn: sqlite3.Connection, type_: str, description: str,
                         threshold: float = SIMILARITY_THRESHOLD) -> dict | None:
    """Wortmengen-Jaccard-Vergleich gegen aktive Lessons desselben Typs.

    Reiner Hinweis fuer die Antwort, kein automatisches Verschmelzen (siehe
    lesson_record Docstring: zwei Lessons faelschlich zusammenzuziehen ist
    teurer als eine Dublette).
    """
    needle = _tokenize(description)
    if not needle:
        return None
    best = None
    for row in conn.execute(
        "SELECT id, occurrences, description FROM lessons_learned WHERE type = ? AND status = 'active'",
        (type_,)
    ):
        hay = _tokenize(row["description"])
        if not hay:
            continue
        score = len(needle & hay) / len(needle | hay)
        if score >= threshold and (best is None or score > best["score"]):
            best = {
                "id": row["id"],
                "occurrences": row["occurrences"],
                "score": round(score, 2),
                "description_first_line": row["description"].splitlines()[0][:200],
            }
    return best


def _bump_lesson(conn: sqlite3.Connection, lesson_id: str, node_path: str,
                 log_query: str, new_description: str | None = None) -> dict:
    """Erhoeht occurrences einer bestehenden Lesson um eins, eskaliert ab 3.

    Gemeinsamer Pfad fuer den exakten Dublettentreffer und den expliziten
    same_as-Bezug — nur die Frage, ob dabei auch die description ersetzt wird
    (Wiederholungs-Anhang), unterscheidet die beiden Aufrufer.
    """
    row = conn.execute("SELECT occurrences FROM lessons_learned WHERE id = ?", (lesson_id,)).fetchone()
    new_count = row["occurrences"] + 1
    if new_description is not None:
        conn.execute(
            "UPDATE lessons_learned SET occurrences = ?, description = ?, last_seen = ? WHERE id = ?",
            (new_count, new_description, now_iso(), lesson_id)
        )
    else:
        conn.execute(
            "UPDATE lessons_learned SET occurrences = ?, last_seen = ? WHERE id = ?",
            (new_count, now_iso(), lesson_id)
        )
    updated_row = conn.execute("SELECT * FROM lessons_learned WHERE id = ?", (lesson_id,)).fetchone()
    log_access(conn, node_path or None, "lesson", query=log_query,
               affected_row=dict(updated_row) if updated_row else None)
    conn.commit()

    escalated = new_count >= 3
    if escalated:
        conn.execute(
            "UPDATE lessons_learned SET status = 'escalated_to_rule' WHERE id = ?",
            (lesson_id,)
        )
        conn.commit()

    return {
        "id": lesson_id,
        "status": "incremented",
        "occurrences": new_count,
        "escalated": escalated,
        "message": f"Lesson seen {new_count}x. {'ESCALATED: Should become a rule in .instructions.md!' if escalated else ''}"
    }


def lesson_record(type_: str, description: str, root_cause: str = "",
                  resolution: str = "", prevention: str = "",
                  severity: str = "medium", projects: list | None = None,
                  node_path: str = "", same_as: str = "",
                  anlass: str = "unbekannt") -> dict:
    """Record a lesson learned.

    same_as gesetzt: erhoeht occurrences der referenzierten Lesson, haengt
    diese Beschreibung als datierten Wiederholungs-Absatz an (gedeckelt),
    legt KEINEN neuen Eintrag an. Zeigt same_as ins Leere: Fehler, kein
    stiller Fallback.

    same_as leer: bisheriges Verhalten (exakte Dublette gleichen Typs +
    gleicher Beschreibung erhoeht occurrences; sonst neuer Eintrag). Bei
    neuem Eintrag zusaetzlich ein Aehnlichkeits-Hinweis in der Antwort
    (similar_lesson_hint), falls eine inhaltlich nahe aktive Lesson
    gleichen Typs existiert — ohne automatisches Verschmelzen.

    Ab 3 Vorkommen (same_as-Pfad wie bisheriger Exact-Match-Pfad) wird die
    Lesson auf status='escalated_to_rule' gesetzt.

    anlass: was hat den Eintrag ausgeloest -- siehe ALLOWED_ANLASS oben.
    'selbst'/'betreiber' sind selbstberichtet vom Aufrufer, nicht geprueft;
    'hook'/'skript' objektiv, weil der Aufrufweg sie kennt. Unbekannter Wert
    wird abgelehnt (sprechender Fehler, kein stiller Erfolg). Gilt nur fuer
    einen NEUEN Eintrag -- ein Bump (Dublette/same_as) laesst den anlass der
    bestehenden Zeile unveraendert.
    """
    anlass_fehler = _validate_anlass(anlass)
    if anlass_fehler:
        return {"status": "rejected", "error": anlass_fehler}

    fixed = unmangle_lesson_fields({
        "type": type_, "description": description, "root_cause": root_cause,
        "resolution": resolution, "prevention": prevention, "severity": severity,
        "projects": projects, "node_path": node_path,
    })
    type_, description = fixed["type"], fixed["description"]
    root_cause, resolution = fixed["root_cause"], fixed["resolution"]
    prevention, severity = fixed["prevention"], fixed["severity"] or "medium"
    projects, node_path = fixed["projects"], fixed["node_path"]

    if not description.strip():
        return {"status": "rejected",
                "error": "description ist leer — Lesson nicht gespeichert."}

    conn = get_db()

    if same_as:
        target = conn.execute(
            "SELECT id, occurrences, description FROM lessons_learned WHERE id = ?",
            (same_as,)
        ).fetchone()
        if not target:
            conn.close()
            return {"status": "rejected",
                    "error": f"same_as verweist auf keine bestehende Lesson: {same_as}"}
        merged_description = _append_repetition(target["description"], description, now_iso())
        result = _bump_lesson(conn, target["id"], node_path, description,
                              new_description=merged_description)
        conn.close()
        return result

    # Check for exact-duplicate existing lesson (same type + same description)
    existing = conn.execute(
        "SELECT id, occurrences FROM lessons_learned WHERE type = ? AND description = ? AND status = 'active'",
        (type_, description)
    ).fetchone()

    if existing:
        result = _bump_lesson(conn, existing["id"], node_path, description)
        conn.close()
        return result

    similar = _find_similar_lesson(conn, type_, description)

    lesson_id = f"L-{str(uuid.uuid4())[:6]}"
    seen_at = now_iso()
    conn.execute(
        """INSERT INTO lessons_learned (id, node_path, type, severity, description, root_cause, resolution, prevention, occurrences, projects, first_seen, last_seen, anlass)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)""",
        (lesson_id, node_path or None, type_, severity, description, root_cause,
         resolution, prevention, json.dumps(projects or []), seen_at, seen_at, anlass)
    )
    log_access(conn, node_path or None, "lesson", query=description,
               affected_row={
                   "id": lesson_id, "node_path": node_path or None, "type": type_,
                   "severity": severity, "description": description,
                   "root_cause": root_cause, "resolution": resolution,
                   "prevention": prevention, "occurrences": 1,
                   "projects": projects or [], "first_seen": seen_at, "last_seen": seen_at,
                   "anlass": anlass,
               })
    conn.commit()
    conn.close()
    result = {"id": lesson_id, "status": "recorded", "occurrences": 1}
    if similar:
        result["similar_lesson_hint"] = similar
    return result


def lesson_update(lesson_id: str, description: str | None = None,
                  root_cause: str | None = None, resolution: str | None = None,
                  prevention: str | None = None, severity: str | None = None,
                  projects: list | None = None, status: str | None = None,
                  delete: bool = False) -> dict:
    """Correct or delete a recorded lesson. Only fields given are changed; the rest is left untouched."""
    conn = get_db()
    row = conn.execute("SELECT id FROM lessons_learned WHERE id = ?", (lesson_id,)).fetchone()
    if not row:
        conn.close()
        return {"error": f"Lesson not found: {lesson_id}"}

    if delete:
        conn.execute("DELETE FROM lessons_learned WHERE id = ?", (lesson_id,))
        log_access(conn, None, "lesson_delete", query=lesson_id)
        conn.commit()
        conn.close()
        return {"id": lesson_id, "status": "deleted"}

    raw = {
        "description": description, "root_cause": root_cause, "resolution": resolution,
        "prevention": prevention, "severity": severity, "projects": projects,
    }
    # Nur uebergebene Felder unmangeln/schreiben — derselbe Aufrufer-Fehler wie bei
    # lesson_record (Parametergrenze verrutscht ins Textfeld) kann hier genauso passieren.
    given = {k: v for k, v in raw.items() if v is not None}
    if given:
        fixed = unmangle_lesson_fields(given)
        given.update(fixed)

    updates = []
    params = []
    for col in ("description", "root_cause", "resolution", "prevention", "severity"):
        if col in given:
            updates.append(f"{col} = ?")
            params.append(given[col])
    if "projects" in given:
        updates.append("projects = ?")
        params.append(json.dumps(given["projects"] or []))
    if status is not None:
        updates.append("status = ?")
        params.append(status)

    if not updates:
        conn.close()
        return {"id": lesson_id, "status": "unchanged", "message": "Keine Felder uebergeben."}

    updates.append("last_seen = ?")
    params.append(now_iso())
    params.append(lesson_id)

    conn.execute(f"UPDATE lessons_learned SET {', '.join(updates)} WHERE id = ?", params)

    # P4: der Embedding-Text einer Lesson ist description+root_cause+prevention
    # (siehe build_embeddings.py) -- resolution/severity/projects/status
    # fliessen nicht ein und loesen deshalb keine Loeschung aus.
    if {"description", "root_cause", "prevention"} & given.keys():
        conn.execute("DELETE FROM knowledge_embeddings WHERE kind = 'lesson' AND ref_id = ?", (lesson_id,))

    updated_row = conn.execute("SELECT * FROM lessons_learned WHERE id = ?", (lesson_id,)).fetchone()
    log_access(conn, None, "lesson_update", query=lesson_id,
               affected_row=dict(updated_row) if updated_row else None)
    conn.commit()
    conn.close()
    return {"id": lesson_id, "status": "updated"}


def lesson_query(type_: str | None = None, project: str | None = None,
                 status: str = "active", max_results: int = 10,
                 query: str | None = None) -> dict:
    """Query lessons learned by type, project, or status. Optional `query`:
    Bedeutungs-/Stichwortsuche in description/root_cause/prevention (LIKE als
    Stichwort-Basis + optionale Embedding-Fusion, RRF wie knowledge_search).
    Ohne `query` unveraendertes Altverhalten (reine Filter, sortiert nach
    occurrences/last_seen)."""
    conn = get_db()
    conditions = []
    params = []

    if type_:
        conditions.append("type = ?")
        params.append(type_)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if project:
        conditions.append("projects LIKE ?")
        params.append(f'%"{project}"%')

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    if not query:
        rows = conn.execute(
            f"SELECT * FROM lessons_learned {where} ORDER BY occurrences DESC, last_seen DESC LIMIT ?",
            (*params, max_results)
        ).fetchall()
        results = [dict(r) for r in rows]
        conn.close()
        return {"results": results, "count": len(results)}

    all_rows = conn.execute(f"SELECT * FROM lessons_learned {where}", tuple(params)).fetchall()
    by_id = {r["id"]: r for r in all_rows}
    # Mindestlaenge 4 + Stopwortfilter wie knowledge_recall_hook.py's STOP-Liste
    # (hier dupliziert, nicht importiert -- der Hook selbst bleibt unangetastet,
    # siehe Auftrag). Ohne Filter matchen 3-Buchstaben-Fuellwoerter ("die",
    # "und", "ist") als Substring in fast jedem Lesson-Text und ertraenken das
    # eigentliche Signal.
    _stop = {
        "und", "oder", "der", "die", "das", "den", "dem", "ein", "eine", "einen", "einem",
        "ist", "sind", "war", "wird", "werden", "kann", "soll", "muss", "für", "mit", "von",
        "auf", "aus", "bei", "zum", "zur", "des", "als", "auch", "nicht", "noch", "wie", "was",
        "wenn", "dann", "aber", "nur", "mir", "mich", "dir", "dich", "ich", "wir", "ihr", "sie",
        "sich", "durch", "the", "and", "for", "that", "this", "with", "from", "have", "has",
        "was", "are", "you", "can", "should", "must", "not", "how", "what", "when", "then",
    }
    _stop = {fold_de(w) for w in _stop}  # "für" -> auch "fuer" filtern, sonst leckt es durch
    # fold_de() statt .lower(): "Existenzgruender" (ue-Schreibung) muss dieselbe
    # Lesson finden wie "Existenzgründer" (ü) -- gleiche Luecke wie vorher bei
    # knowledge_search(), hier nur unbehoben, weil ein eigener Python-Substring-
    # Pfad statt FTS5 (siehe Auftrag: 374 Lehren standen weiter hinter der Wand).
    keywords = [w for w in re.findall(r"[A-Za-zÄÖÜäöüß0-9]{4,}", fold_de(query)) if w not in _stop]

    def kw_hits(row: sqlite3.Row) -> int:
        text = fold_de(f"{row['description']} {row['root_cause']} {row['prevention']}")
        return sum(1 for k in keywords if k in text)

    keyword_ordered_ids = sorted((i for i in by_id if kw_hits(by_id[i]) > 0),
                                  key=lambda i: kw_hits(by_id[i]), reverse=True)

    query_vec = embeddings.embed_text(query)
    embedding_ordered_ids = (
        _embedding_ranking(conn, "lesson", query_vec, set(by_id.keys())) if query_vec else []
    )
    final_ids = _fuse_with_keyword_floor(keyword_ordered_ids, embedding_ordered_ids, max_results)

    results = [dict(by_id[i]) for i in final_ids if i in by_id]
    conn.close()
    return {"results": results, "count": len(results)}


def knowledge_stats() -> dict:
    """Overview statistics of the knowledge database."""
    conn = get_db()
    total_nodes = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    by_project = dict(conn.execute(
        "SELECT project_id, COUNT(*) FROM knowledge_nodes GROUP BY project_id"
    ).fetchall())
    by_level = dict(conn.execute(
        "SELECT level, COUNT(*) FROM knowledge_nodes GROUP BY level"
    ).fetchall())
    total_lessons = conn.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
    active_lessons = conn.execute("SELECT COUNT(*) FROM lessons_learned WHERE status = 'active'").fetchone()[0]
    escalated = conn.execute("SELECT COUNT(*) FROM lessons_learned WHERE status = 'escalated_to_rule'").fetchone()[0]
    recent_access = conn.execute(
        "SELECT action, COUNT(*) as cnt FROM access_log GROUP BY action"
    ).fetchall()
    # Anlass-Verteilung (Auftrag 2026-08-06) -- ganzer Zweck des Feldes.
    # selbst/betreiber selbstberichtet, hook/skript objektiv, siehe
    # ALLOWED_ANLASS. Getrennt fuer Knoten und Lehren, nicht zusammengefasst.
    nodes_by_anlass = dict(conn.execute(
        "SELECT anlass, COUNT(*) FROM knowledge_nodes GROUP BY anlass"
    ).fetchall())
    lessons_by_anlass = dict(conn.execute(
        "SELECT anlass, COUNT(*) FROM lessons_learned GROUP BY anlass"
    ).fetchall())
    conn.close()

    return {
        "nodes_total": total_nodes,
        "nodes_by_project": by_project,
        "nodes_by_level": by_level,
        "nodes_by_anlass": nodes_by_anlass,
        "lessons_total": total_lessons,
        "lessons_active": active_lessons,
        "lessons_escalated": escalated,
        "lessons_by_anlass": lessons_by_anlass,
        "access_patterns": dict(recent_access),
        "db_path": str(DB_PATH),
        "timestamp": now_iso()
    }


# ─── MCP Server Protocol (stdio JSON-RPC 2.0) ───────────────────────────

def _identity_args(args: dict) -> dict:
    return {key: args.get(key) for key in ("actor", "model", "session")}


IDENTITY_PROPERTIES = {
    "actor": {"type": "string", "description": "Calling agent identity; else BEGOD_KNOWLEDGE_ACTOR or unknown"},
    "model": {"type": "string", "description": "Calling model; else BEGOD_KNOWLEDGE_MODEL or unknown"},
    "session": {"type": "string", "description": "Stable session ID; else BEGOD_KNOWLEDGE_SESSION or unknown"},
}

TOOLS = {
    "knowledge_browse": {
        "description": "Browse children of a knowledge tree node. Returns titles+summaries only (token-efficient). Use '/' for root.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Tree path to browse, e.g. '/' or '/shared/arch'", "default": "/"},
                "project_filter": {"type": "string", "description": "Filter by project: shared|begod|aka|bebetter"},
                **IDENTITY_PROPERTIES,
            }
        },
        "handler": lambda args: knowledge_browse(args.get("path", "/"), args.get("project_filter"), **_identity_args(args))
    },
    "knowledge_read": {
        "description": "Read full content of a knowledge node (by ID or path), plus title+summary of its direct children (one level, not recursive) -- a branch node's own content is usually empty, the substance lives in its children. Use browse/search first to find the right node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "Node ID or full path"},
                **IDENTITY_PROPERTIES,
            },
            "required": ["node_id"]
        },
        "handler": lambda args: knowledge_read(args["node_id"], **_identity_args(args))
    },
    "knowledge_search": {
        "description": "Full-text search across knowledge. Returns summaries (not full content) for token efficiency.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (FTS5 syntax supported: AND, OR, NOT, phrases). Hybrid: fuses keyword matches with local-embedding meaning search when vectors exist."},
                "scope": {"type": "string", "description": "Scope: 'all' or project name", "default": "all"},
                "max_results": {"type": "integer", "description": "Max results (default 10)", "default": 10},
                "stichtag": {"type": "string", "description": "ISO-8601 date/timestamp to check norm validity (gilt_ab/gilt_bis) against; default now. Expired or not-yet-effective norms rank last and are marked, never hidden (unless nur_geltende=True). Facts (norm_rang unset) are unaffected."},
                "nur_geltende": {"type": "boolean", "description": "Drop expired/not-yet-effective norms instead of ranking them last. Default False.", "default": False},
                **IDENTITY_PROPERTIES,
            },
            "required": ["query"]
        },
        "handler": lambda args: knowledge_search(args["query"], args.get("scope", "all"), args.get("max_results", 10), stichtag=args.get("stichtag"), nur_geltende=args.get("nur_geltende", False), **_identity_args(args))
    },
    "knowledge_add": {
        "description": "Add a new knowledge node to the tree. Specify parent_path to place it in the hierarchy. "
                        "parent_path must already exist (or be '/'); an unknown parent_path is rejected with "
                        "suggested nearby paths unless neuer_ast=True explicitly opens a new branch. "
                        "source is required and rejected if empty -- e.g. \"erzeugt aus /pfad/datei.md (Stand 2026-08-05T23:40:00+02:00)\". "
                        "norm_rang/gilt_ab/gilt_bis are all optional and only for norms (directives/ADRs/escalated "
                        "lessons); a plain fact leaves them unset (norm_rang stays NULL). gilt_ab/gilt_bis must be "
                        "ISO-8601 date or timestamp; gilt_bis before gilt_ab is rejected. "
                        "anlass records what triggered this entry: 'selbst' (you wrote it unprompted) or "
                        "'betreiber' (an explicit human instruction, e.g. \"merk dir das\") are SELF-REPORTED -- "
                        "only as reliable as the caller. 'hook' (the enforcing Stop-hook made you call this) and "
                        "'skript' (batch/migration/harvest run, no conversation) are objective in principle, but "
                        "note the Stop-hook itself never calls this tool -- it only forces you to run /learn, "
                        "which then calls this normally, so 'hook' is still self-reported by that skill, not "
                        "verified by the server. Default 'unbekannt' if omitted. An unknown value is rejected "
                        "with the allowed list, nothing is written.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "parent_path": {"type": "string", "description": "Parent node path, e.g. '/shared/arch' -- must exist"},
                "title": {"type": "string"},
                "summary": {"type": "string", "description": "1-2 sentences summary (token-efficient)"},
                "content": {"type": "string", "description": "Full content (loaded only on read)"},
                "project_id": {"type": "string", "description": "shared|begod|aka|bebetter", "default": "shared"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "source": {"type": "string", "description": "Required, non-empty. Origin: file path, konsil ID, or research ID. Example: 'erzeugt aus /pfad/datei.md (Stand 2026-08-05T23:40:00+02:00)'"},
                "neuer_ast": {"type": "boolean", "description": "Explicitly allow creating a new top-level branch when parent_path doesn't exist yet", "default": False},
                "norm_rang": {"type": "integer", "description": "Optional: rank of a norm (1=global directive, 2=hub directive, 3=ADR). Omit for plain facts."},
                "gilt_ab": {"type": "string", "description": "Optional: ISO-8601 date/timestamp the norm takes effect"},
                "gilt_bis": {"type": "string", "description": "Optional: ISO-8601 date/timestamp the norm expires; omit for indefinite. Must not be before gilt_ab."},
                "anlass": {"type": "string", "enum": sorted(ALLOWED_ANLASS), "default": "unbekannt",
                           "description": "What triggered this entry -- selbst/betreiber self-reported, hook/skript objective in principle (see tool description). Default 'unbekannt'."},
                **IDENTITY_PROPERTIES,
            },
            "required": ["parent_path", "title", "summary"]
        },
        "handler": lambda args: knowledge_add(
            args["parent_path"], args["title"], args["summary"],
            args.get("content", ""), args.get("project_id", "shared"),
            args.get("tags"), args.get("source", ""), neuer_ast=args.get("neuer_ast", False),
            norm_rang=args.get("norm_rang"), gilt_ab=args.get("gilt_ab"), gilt_bis=args.get("gilt_bis"),
            anlass=args.get("anlass", "unbekannt"),
            **_identity_args(args)
        )
    },
    "knowledge_update": {
        "description": "Update an existing knowledge node (summary, content, tags, and/or the Normschicht fields "
                        "norm_rang/gilt_ab/gilt_bis -- see knowledge_add for their meaning). Only given fields change.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "Node ID or path"},
                "summary": {"type": "string"},
                "content": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "norm_rang": {"type": "integer", "description": "Optional: set/change the norm rank"},
                "gilt_ab": {"type": "string", "description": "Optional: ISO-8601 date/timestamp"},
                "gilt_bis": {"type": "string", "description": "Optional: ISO-8601 date/timestamp; must not be before gilt_ab (existing or given)"},
                **IDENTITY_PROPERTIES,
            },
            "required": ["node_id"]
        },
        "handler": lambda args: knowledge_update(
            args["node_id"], args.get("summary"), args.get("content"), args.get("tags"),
            norm_rang=args.get("norm_rang"), gilt_ab=args.get("gilt_ab"), gilt_bis=args.get("gilt_bis"),
            **_identity_args(args)
        )
    },
    "knowledge_relation_add": {
        "description": "Create one explicit evidenced knowledge edge between existing node IDs/paths. Never infers links from tags or text; validates endpoints, scope, type, confidence, and duplicate edges.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_node": {"type": "string", "description": "Existing source node ID or path"},
                "target_node": {"type": "string", "description": "Existing target node ID or path"},
                "relation_type": {"type": "string", "enum": sorted(RELATION_TYPES)},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.8},
                "weight": {"type": "number", "minimum": 0, "default": 1.0},
                "evidence": {"type": "string", "description": "Why this edge is true; cite the decision/source"},
                "source": {"type": "string", "description": "Source artifact path/ID"},
                "scope": {"type": "string", "description": "all or project; scoped calls permit shared + project", "default": "all"},
                **IDENTITY_PROPERTIES,
            },
            "required": ["source_node", "target_node", "relation_type", "evidence"]
        },
        "handler": lambda args: knowledge_relation_add(
            args["source_node"], args["target_node"], args["relation_type"],
            args.get("confidence", 0.8), args.get("weight", 1.0), args.get("evidence", ""),
            args.get("source", ""), args.get("scope", "all"),
            args.get("actor"), args.get("model"), args.get("session")
        )
    },
    "knowledge_relation_list": {
        "description": "List only explicit knowledge edges, optionally incident to one node and filtered by relation type/scope. This is the canonical link-read path.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Optional existing node ID or path"},
                "relation_type": {"type": "string", "enum": sorted(RELATION_TYPES)},
                "scope": {"type": "string", "default": "all"},
                **IDENTITY_PROPERTIES,
            }
        },
        "handler": lambda args: knowledge_relation_list(
            args.get("node"), args.get("relation_type"), args.get("scope", "all"), **_identity_args(args)
        )
    },
    "knowledge_relation_update": {
        "description": "Update evidence/provenance/weight/type of one explicit edge by relation ID; endpoints stay stable.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "relation_id": {"type": "string"},
                "relation_type": {"type": "string", "enum": sorted(RELATION_TYPES)},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "weight": {"type": "number", "minimum": 0},
                "evidence": {"type": "string"},
                "source": {"type": "string"},
                **IDENTITY_PROPERTIES,
            },
            "required": ["relation_id"]
        },
        "handler": lambda args: knowledge_relation_update(
            args["relation_id"], args.get("relation_type"), args.get("confidence"),
            args.get("weight"), args.get("evidence"), args.get("source"),
            args.get("actor"), args.get("model"), args.get("session")
        )
    },
    "knowledge_relation_remove": {
        "description": "Remove exactly one explicit edge by relation ID. Nodes are never deleted.",
        "inputSchema": {
            "type": "object",
            "properties": {"relation_id": {"type": "string"}, **IDENTITY_PROPERTIES},
            "required": ["relation_id"]
        },
        "handler": lambda args: knowledge_relation_remove(args["relation_id"], **_identity_args(args))
    },
    "lesson_record": {
        "description": (
            "Record a lesson learned. Pass same_as=<lesson id> when this is a repeat of an "
            "already-recorded lesson: increments that lesson's occurrences, appends this "
            "description to it as a dated, capped repetition note, and creates no new row "
            "(unknown same_as id is an error, never a silent new entry). Escalates to rule "
            "at 3+ occurrences. Without same_as: increments occurrences only on an exact "
            "duplicate (same type + byte-identical description); otherwise creates a new "
            "lesson and, if an active lesson of the same type looks similar, returns it as "
            "similar_lesson_hint (a hint only — never auto-merged; re-record with same_as to merge). "
            "anlass records what triggered this entry: 'selbst' (you wrote it unprompted) or "
            "'betreiber' (an explicit human instruction, e.g. \"merk dir das\") are SELF-REPORTED -- "
            "only as reliable as the caller. 'hook' and 'skript' are objective in principle, but "
            "note the enforcing Stop-hook never calls this tool itself -- it only forces you to run "
            "/learn, which then calls this normally, so 'hook' is still self-reported by that skill, "
            "not verified by the server. Default 'unbekannt' if omitted; an unknown value is rejected "
            "with the allowed list, nothing is written (applies even on a duplicate/same_as bump, where "
            "the existing row's anlass is left untouched anyway)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["error", "insight", "pattern", "antipattern"]},
                "description": {"type": "string"},
                "root_cause": {"type": "string"},
                "resolution": {"type": "string"},
                "prevention": {"type": "string"},
                "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"], "default": "medium"},
                "projects": {"type": "array", "items": {"type": "string"}, "description": "Affected projects"},
                "node_path": {"type": "string", "description": "Related knowledge node path"},
                "same_as": {"type": "string", "description": "ID of an existing lesson this is a repeat of, e.g. 'L-6e48a9'"},
                "anlass": {"type": "string", "enum": sorted(ALLOWED_ANLASS), "default": "unbekannt",
                           "description": "What triggered this entry -- selbst/betreiber self-reported, hook/skript objective in principle (see tool description). Default 'unbekannt'."}
            },
            "required": ["type", "description"]
        },
        "handler": lambda args: lesson_record(
            args["type"], args["description"], args.get("root_cause", ""),
            args.get("resolution", ""), args.get("prevention", ""),
            args.get("severity", "medium"), args.get("projects"), args.get("node_path", ""),
            args.get("same_as", ""), args.get("anlass", "unbekannt")
        )
    },
    "lesson_update": {
        "description": "Correct or delete a recorded lesson. Only given fields are changed; unmangles field-tag corruption in the same way lesson_record does. Use delete:true to remove a bad entry.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lesson_id": {"type": "string", "description": "Lesson ID, e.g. 'L-6e48a9'"},
                "description": {"type": "string"},
                "root_cause": {"type": "string"},
                "resolution": {"type": "string"},
                "prevention": {"type": "string"},
                "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                "projects": {"type": "array", "items": {"type": "string"}},
                "status": {"type": "string", "enum": ["active", "resolved", "escalated_to_rule"]},
                "delete": {"type": "boolean", "description": "Delete the lesson instead of updating it", "default": False}
            },
            "required": ["lesson_id"]
        },
        "handler": lambda args: lesson_update(
            args["lesson_id"], args.get("description"), args.get("root_cause"),
            args.get("resolution"), args.get("prevention"), args.get("severity"),
            args.get("projects"), args.get("status"), args.get("delete", False)
        )
    },
    "lesson_query": {
        "description": "Query lessons learned. Filter by type, project, or status. Optional 'query' searches description/root_cause/prevention by keyword and meaning (hybrid).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["error", "insight", "pattern", "antipattern"]},
                "project": {"type": "string"},
                "status": {"type": "string", "enum": ["active", "resolved", "escalated_to_rule"], "default": "active"},
                "max_results": {"type": "integer", "default": 10},
                "query": {"type": "string", "description": "Optional: Stichwort-/Bedeutungssuche in description/root_cause/prevention"}
            }
        },
        "handler": lambda args: lesson_query(
            args.get("type"), args.get("project"), args.get("status", "active"),
            args.get("max_results", 10), args.get("query")
        )
    },
    "knowledge_stats": {
        "description": "Overview statistics of the knowledge database (node counts, lesson counts, access patterns, "
                        "anlass distribution). anlass_by fields split nodes_by_anlass/lessons_by_anlass into "
                        "selbst/betreiber (self-reported, only as reliable as the caller) vs. hook/skript "
                        "(objective) vs. unbekannt (default / entries older than the field) -- do not treat "
                        "the four as equally trustworthy when reading this.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda args: knowledge_stats()
    }
}


def handle_request(req: dict) -> dict:
    method = req.get("method", "")
    req_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "knowledge-mcp", "version": "1.0.0"}
            }
        }

    if method == "notifications/initialized":
        return None  # No response for notifications

    if method == "tools/list":
        # BEGOD_KNOWLEDGE_PROFIL beschraenkt nur die ANKUENDIGUNG (tools/list),
        # nicht den Aufruf: tools/call bedient jedes Werkzeug in TOOLS weiter,
        # egal ob es hier gelistet wurde. Kein Autorisierungsmechanismus.
        profil = os.environ.get("BEGOD_KNOWLEDGE_PROFIL")
        names = TOOLS.keys()
        if profil == "klein":
            names = ["knowledge_search", "knowledge_read", "knowledge_add"]
        elif profil:
            print(f"BEGOD_KNOWLEDGE_PROFIL unbekannt: {profil!r} — zeige alle Werkzeuge", file=sys.stderr)

        tool_list = []
        for name in names:
            spec = TOOLS[name]
            tool_list.append({
                "name": name,
                "description": spec["description"],
                "inputSchema": spec["inputSchema"]
            })
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tool_list}}

    if method == "tools/call":
        tool_name = req.get("params", {}).get("name", "")
        arguments = req.get("params", {}).get("arguments", {})

        if tool_name not in TOOLS:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps({"error": f"Unknown tool: {tool_name}"})}], "isError": True}
            }

        try:
            result = TOOLS[tool_name]["handler"](arguments)
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps({"error": str(e)})}], "isError": True}
            }

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def main():
    """stdio MCP server — reads JSON-RPC from stdin, writes to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        response = handle_request(req)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
