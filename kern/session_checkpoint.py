"""Small, durable hand-off records for a model session.

The checkpoint is deliberately plain text: it is a resume pointer, not a
second knowledge graph.  Callers provide an already-open sqlite connection so
the MCP write lock and transaction remain the single owner of consistency.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone


def save(conn: sqlite3.Connection, *, session: str, summary: str,
         open_tasks: str = "", decisions: str = "", actor: str | None = None,
         model: str | None = None, checkpoint_id: str | None = None) -> dict:
    if not session.strip() or not summary.strip():
        raise ValueError("session und summary duerfen nicht leer sein")
    row = conn.execute(
        "SELECT COALESCE(MAX(sequence), 0) + 1 FROM session_checkpoints WHERE session = ?",
        (session,),
    ).fetchone()
    ident = checkpoint_id or str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    sequence = int(row[0])
    conn.execute(
        "INSERT INTO session_checkpoints "
        "(id, session, sequence, summary, open_tasks, decisions, actor, model, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (ident, session, sequence, summary, open_tasks, decisions, actor, model, created_at),
    )
    return {"id": ident, "session": session, "sequence": sequence,
            "summary": summary, "open_tasks": open_tasks, "decisions": decisions,
            "actor": actor, "model": model, "created_at": created_at}


def latest(conn: sqlite3.Connection, session: str) -> dict | None:
    row = conn.execute(
        "SELECT id, session, sequence, summary, open_tasks, decisions, actor, model, created_at "
        "FROM session_checkpoints WHERE session = ? ORDER BY sequence DESC LIMIT 1", (session,)
    ).fetchone()
    return dict(row) if row else None
