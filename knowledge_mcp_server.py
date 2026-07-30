#!/usr/bin/env python3
"""
Knowledge MCP Server — Shared Knowledge Database Access for AI Agents.

Erstellt: 2026-03-25T16:30:00+01:00
Transport: stdio (JSON-RPC 2.0)
DB: SQLite + FTS5 Baumstruktur

Tools:
  - knowledge_browse(path)        → Kinder-Knoten (nur Titel+Summary)
  - knowledge_read(node_id)       → Volltext eines Knotens
  - knowledge_search(query, scope)→ FTS5 Suche, gibt Summaries zurück
  - knowledge_add(parent_path, title, summary, content, project_id, tags)
  - knowledge_update(node_id, summary, content)
  - lesson_record(type, description, root_cause, resolution, prevention, severity, projects)
  - lesson_update(lesson_id, description, root_cause, resolution, prevention, severity, projects, status, delete)
  - lesson_query(type, project, status)
  - knowledge_stats()             → Übersichts-Statistiken
"""

import json
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "knowledge.db"
CET = timezone(timedelta(hours=1))


def now_iso() -> str:
    return datetime.now(CET).strftime("%Y-%m-%dT%H:%M:%S+01:00")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def log_access(conn: sqlite3.Connection, node_path: str | None, action: str,
               query: str | None = None, project_id: str | None = None):
    conn.execute(
        "INSERT INTO access_log (node_path, action, query, project_id, timestamp) VALUES (?,?,?,?,?)",
        (node_path, action, query, project_id, now_iso())
    )
    conn.commit()


# ─── MCP Tool Implementations ────────────────────────────────────────────

def knowledge_browse(path: str = "/", project_filter: str | None = None) -> dict:
    """Browse children of a knowledge tree node. Returns titles and summaries only (token-efficient)."""
    conn = get_db()
    log_access(conn, path, "browse", project_id=project_filter)

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

    conn.close()
    return {"path": path, "children": results, "count": len(results)}


def knowledge_read(node_id: str) -> dict:
    """Read full content of a knowledge node. Use browse first to find the right node."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM knowledge_nodes WHERE id = ? OR path = ?",
        (node_id, node_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"error": f"Node not found: {node_id}"}

    conn.execute("UPDATE knowledge_nodes SET access_count = access_count + 1 WHERE id = ?", (row["id"],))
    log_access(conn, row["path"], "read")
    conn.commit()

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
        "created_at": row["created_at"],
        "updated_at": row["updated_at"]
    }
    conn.close()
    return result


def knowledge_search(query: str, scope: str = "all", max_results: int = 10) -> dict:
    """Full-text search across knowledge nodes. Returns summaries (not full content) for token efficiency."""
    conn = get_db()
    log_access(conn, None, "search", query=query)

    if scope == "all":
        rows = conn.execute(
            """SELECT n.id, n.path, n.title, n.summary, n.project_id,
                      rank
               FROM knowledge_fts f
               JOIN knowledge_nodes n ON f.rowid = n.rowid
               WHERE knowledge_fts MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (query, max_results)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT n.id, n.path, n.title, n.summary, n.project_id,
                      rank
               FROM knowledge_fts f
               JOIN knowledge_nodes n ON f.rowid = n.rowid
               WHERE knowledge_fts MATCH ? AND n.project_id IN ('shared', ?)
               ORDER BY rank
               LIMIT ?""",
            (query, scope, max_results)
        ).fetchall()

    results = [{"id": r["id"], "path": r["path"], "title": r["title"],
                "summary": r["summary"], "project": r["project_id"]}
               for r in rows]
    conn.close()
    return {"query": query, "scope": scope, "results": results, "count": len(results)}


def knowledge_add(parent_path: str, title: str, summary: str,
                  content: str = "", project_id: str = "shared",
                  tags: list | None = None, source: str = "") -> dict:
    """Add a new knowledge node to the tree."""
    conn = get_db()
    parent_path = parent_path.rstrip("/")

    # Derive path from parent + slugified title
    slug = title.lower().replace(" ", "-").replace("/", "-")[:40]
    node_path = f"{parent_path}/{slug}" if parent_path != "/" else f"/{slug}"

    # Check for duplicates
    existing = conn.execute("SELECT id FROM knowledge_nodes WHERE path = ?", (node_path,)).fetchone()
    if existing:
        conn.close()
        return {"error": f"Node already exists at path: {node_path}", "existing_id": existing["id"]}

    # Calculate level
    level = node_path.count("/") - 1

    node_id = str(uuid.uuid4())[:8]
    conn.execute(
        """INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, content, level, tags, source, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (node_id, node_path, parent_path, project_id, title, summary, content,
         level, json.dumps(tags or []), source, now_iso(), now_iso())
    )
    log_access(conn, node_path, "add", project_id=project_id)
    conn.commit()
    conn.close()
    return {"id": node_id, "path": node_path, "status": "created"}


def knowledge_update(node_id: str, summary: str | None = None,
                     content: str | None = None, tags: list | None = None) -> dict:
    """Update an existing knowledge node."""
    conn = get_db()
    row = conn.execute("SELECT * FROM knowledge_nodes WHERE id = ? OR path = ?", (node_id, node_id)).fetchone()
    if not row:
        conn.close()
        return {"error": f"Node not found: {node_id}"}

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

    updates.append("updated_at = ?")
    params.append(now_iso())
    params.append(row["id"])

    conn.execute(f"UPDATE knowledge_nodes SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return {"id": row["id"], "status": "updated"}


LESSON_TEXT_FIELDS = ("description", "root_cause", "resolution", "prevention",
                      "severity", "projects", "node_path", "type")
_FIELDS_ALT = "|".join(LESSON_TEXT_FIELDS)
# Zwei Tag-Stile kommen in der Wildnis vor: plain `<root_cause>...</root_cause>`
# und der antml-Tool-Call-Stil `<parameter name="root_cause">...</parameter>`
# (Schliesser dort ist generisch `</parameter>`, traegt keinen Feldnamen).
_FIELD_TAG = re.compile(
    r'<parameter\s+name="(?P<pname>' + _FIELDS_ALT + r')"\s*>'
    r"|</parameter>"
    r"|<(?P<oname>" + _FIELDS_ALT + r")>"
    r"|</(?P<cname>" + _FIELDS_ALT + r")>"
)
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


def _split_tagged(value: str) -> dict:
    """Zerlegt einen Wert an echten Feld-Tag-Grenzen (siehe _is_boundary_tag).

    Kein Zeichen NUTZTEXT geht verloren: jeder Textanteil, der keiner erkannten
    Feldgrenze zugeordnet werden kann (z.B. weil das Zielfeld gerade `current`
    None ist — etwa bei einem verwaisten schliessenden Tag), landet unter
    "_head" statt verworfen zu werden. Einzige Ausnahme: ein Anteil, der
    zwischen zwei Tags liegt UND nur aus Leerraum besteht, ist der
    Formatierungs-Zwischenraum der Tags selbst (kein Inhalt) und wird nicht
    extra angehaengt — sonst haeuften sich bei mehreren aufeinanderfolgenden
    Tags leere Zeilen im Ursprungsfeld an.
    """
    matches = [m for m in _FIELD_TAG.finditer(value) if _is_boundary_tag(value, m)]
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
            continue  # keine echte Feldgrenze gefunden (z.B. nur ein Zitat im Fliesstext)
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


def lesson_record(type_: str, description: str, root_cause: str = "",
                  resolution: str = "", prevention: str = "",
                  severity: str = "medium", projects: list | None = None,
                  node_path: str = "") -> dict:
    """Record a lesson learned. If a similar lesson exists, increment occurrences."""
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

    # Check for similar existing lesson (same type + similar description)
    existing = conn.execute(
        "SELECT id, occurrences FROM lessons_learned WHERE type = ? AND description = ? AND status = 'active'",
        (type_, description)
    ).fetchone()

    if existing:
        new_count = existing["occurrences"] + 1
        conn.execute(
            "UPDATE lessons_learned SET occurrences = ?, last_seen = ? WHERE id = ?",
            (new_count, now_iso(), existing["id"])
        )
        log_access(conn, node_path or None, "lesson", query=description)
        conn.commit()

        escalated = new_count >= 3
        if escalated:
            conn.execute(
                "UPDATE lessons_learned SET status = 'escalated_to_rule' WHERE id = ?",
                (existing["id"],)
            )
            conn.commit()

        conn.close()
        return {
            "id": existing["id"],
            "status": "incremented",
            "occurrences": new_count,
            "escalated": escalated,
            "message": f"Lesson seen {new_count}x. {'ESCALATED: Should become a rule in .instructions.md!' if escalated else ''}"
        }

    lesson_id = f"L-{str(uuid.uuid4())[:6]}"
    conn.execute(
        """INSERT INTO lessons_learned (id, node_path, type, severity, description, root_cause, resolution, prevention, occurrences, projects, first_seen, last_seen)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)""",
        (lesson_id, node_path or None, type_, severity, description, root_cause,
         resolution, prevention, json.dumps(projects or []), now_iso(), now_iso())
    )
    log_access(conn, node_path or None, "lesson", query=description)
    conn.commit()
    conn.close()
    return {"id": lesson_id, "status": "recorded", "occurrences": 1}


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
    log_access(conn, None, "lesson_update", query=lesson_id)
    conn.commit()
    conn.close()
    return {"id": lesson_id, "status": "updated"}


def lesson_query(type_: str | None = None, project: str | None = None,
                 status: str = "active", max_results: int = 10) -> dict:
    """Query lessons learned by type, project, or status."""
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
    rows = conn.execute(
        f"SELECT * FROM lessons_learned {where} ORDER BY occurrences DESC, last_seen DESC LIMIT ?",
        (*params, max_results)
    ).fetchall()

    results = [dict(r) for r in rows]
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
    conn.close()

    return {
        "nodes_total": total_nodes,
        "nodes_by_project": by_project,
        "nodes_by_level": by_level,
        "lessons_total": total_lessons,
        "lessons_active": active_lessons,
        "lessons_escalated": escalated,
        "access_patterns": dict(recent_access),
        "db_path": str(DB_PATH),
        "timestamp": now_iso()
    }


# ─── MCP Server Protocol (stdio JSON-RPC 2.0) ───────────────────────────

TOOLS = {
    "knowledge_browse": {
        "description": "Browse children of a knowledge tree node. Returns titles+summaries only (token-efficient). Use '/' for root.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Tree path to browse, e.g. '/' or '/shared/arch'", "default": "/"},
                "project_filter": {"type": "string", "description": "Filter by project: shared|begod|aka|bebetter"}
            }
        },
        "handler": lambda args: knowledge_browse(args.get("path", "/"), args.get("project_filter"))
    },
    "knowledge_read": {
        "description": "Read full content of a knowledge node (by ID or path). Use browse/search first to find the right node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "Node ID or full path"}
            },
            "required": ["node_id"]
        },
        "handler": lambda args: knowledge_read(args["node_id"])
    },
    "knowledge_search": {
        "description": "Full-text search across knowledge. Returns summaries (not full content) for token efficiency.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (FTS5 syntax supported: AND, OR, NOT, phrases)"},
                "scope": {"type": "string", "description": "Scope: 'all' or project name", "default": "all"},
                "max_results": {"type": "integer", "description": "Max results (default 10)", "default": 10}
            },
            "required": ["query"]
        },
        "handler": lambda args: knowledge_search(args["query"], args.get("scope", "all"), args.get("max_results", 10))
    },
    "knowledge_add": {
        "description": "Add a new knowledge node to the tree. Specify parent_path to place it in the hierarchy.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "parent_path": {"type": "string", "description": "Parent node path, e.g. '/shared/arch'"},
                "title": {"type": "string"},
                "summary": {"type": "string", "description": "1-2 sentences summary (token-efficient)"},
                "content": {"type": "string", "description": "Full content (loaded only on read)"},
                "project_id": {"type": "string", "description": "shared|begod|aka|bebetter", "default": "shared"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "source": {"type": "string", "description": "Origin: file path, konsil ID, or research ID"}
            },
            "required": ["parent_path", "title", "summary"]
        },
        "handler": lambda args: knowledge_add(
            args["parent_path"], args["title"], args["summary"],
            args.get("content", ""), args.get("project_id", "shared"),
            args.get("tags"), args.get("source", "")
        )
    },
    "knowledge_update": {
        "description": "Update an existing knowledge node (summary, content, or tags).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "Node ID or path"},
                "summary": {"type": "string"},
                "content": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["node_id"]
        },
        "handler": lambda args: knowledge_update(
            args["node_id"], args.get("summary"), args.get("content"), args.get("tags")
        )
    },
    "lesson_record": {
        "description": "Record a lesson learned. Auto-increments if similar lesson exists. Escalates to rule at 3+ occurrences.",
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
                "node_path": {"type": "string", "description": "Related knowledge node path"}
            },
            "required": ["type", "description"]
        },
        "handler": lambda args: lesson_record(
            args["type"], args["description"], args.get("root_cause", ""),
            args.get("resolution", ""), args.get("prevention", ""),
            args.get("severity", "medium"), args.get("projects"), args.get("node_path", "")
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
        "description": "Query lessons learned. Filter by type, project, or status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["error", "insight", "pattern", "antipattern"]},
                "project": {"type": "string"},
                "status": {"type": "string", "enum": ["active", "resolved", "escalated_to_rule"], "default": "active"},
                "max_results": {"type": "integer", "default": 10}
            }
        },
        "handler": lambda args: lesson_query(
            args.get("type"), args.get("project"), args.get("status", "active"),
            args.get("max_results", 10)
        )
    },
    "knowledge_stats": {
        "description": "Overview statistics of the knowledge database (node counts, lesson counts, access patterns).",
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
        tool_list = []
        for name, spec in TOOLS.items():
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
