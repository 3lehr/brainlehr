"""Temporärer Sitzungszustand und deterministische Chatwechsel-Empfehlung.

Nur technische IDs werden gespeichert. Das ist kein Chatlog und kein zweiter
Wissensspeicher; die Tabelle ist weder an FTS noch an Recall angebunden.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS session_checkpoints (
    session_id TEXT PRIMARY KEY,
    project TEXT NOT NULL,
    context_fraction REAL NOT NULL CHECK(context_fraction BETWEEN 0 AND 1),
    topic_fingerprint TEXT NOT NULL,
    active_requirement_ids TEXT NOT NULL DEFAULT '[]',
    expected_child_ids TEXT NOT NULL DEFAULT '[]',
    terminal_child_ids TEXT NOT NULL DEFAULT '[]',
    unresolved_evidence_ids TEXT NOT NULL DEFAULT '[]',
    used_knowledge_ids TEXT NOT NULL DEFAULT '[]',
    open_gate_ids TEXT NOT NULL DEFAULT '[]',
    role_capability TEXT NOT NULL DEFAULT '',
    source_revision TEXT NOT NULL DEFAULT '',
    terminal_state TEXT NOT NULL DEFAULT 'active' CHECK(terminal_state IN ('active', 'terminal')),
    next_authorized_action TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status = 'active'),
    updated_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_session_checkpoints_expiry
    ON session_checkpoints(expires_at);
"""

FIELDS = {
    "session_id", "project", "context_fraction", "topic_fingerprint",
    "active_requirement_ids", "expected_child_ids", "terminal_child_ids",
    "unresolved_evidence_ids", "used_knowledge_ids", "open_gate_ids",
    "role_capability", "source_revision", "terminal_state", "next_authorized_action",
}
LIST_FIELDS = {
    "active_requirement_ids", "expected_child_ids", "terminal_child_ids",
    "unresolved_evidence_ids", "used_knowledge_ids", "open_gate_ids",
}
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
SECRET_PREFIXES = ("sk-", "ghp_", "github_pat_", "bearer-", "api-key-")


@dataclass(frozen=True)
class AgentCapability:
    """Ephemeral routing record; deliberately contains no prompt or transcript."""
    agent_id: str
    task_id: str
    project_id: str
    task_fingerprint: str
    role_capability: str
    source_revision: str
    tree_hash: str
    checkpoint_session_id: str
    terminal_state: str = "active"
    open_gate_ids: tuple[str, ...] = ()
    fresh: bool = True


class AgentCapabilityRegistry:
    """Small host-side registry for compatible follow-ups; never spawns agents."""

    def __init__(self):
        self._entries: dict[tuple[str, str], AgentCapability] = {}

    def register(self, **values) -> AgentCapability:
        allowed = set(AgentCapability.__dataclass_fields__)
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"nicht erlaubte Agent-Felder: {', '.join(sorted(unknown))}")
        required = ("agent_id", "task_id", "project_id", "task_fingerprint",
                    "role_capability", "source_revision", "tree_hash", "checkpoint_session_id")
        normalized = dict(values)
        for field in required:
            normalized[field] = _id(field, normalized.get(field))
        normalized["terminal_state"] = normalized.get("terminal_state", "active")
        if normalized["terminal_state"] not in {"active", "terminal"}:
            raise ValueError("terminal_state muss active oder terminal sein")
        gates = normalized.get("open_gate_ids", ())
        if not isinstance(gates, (list, tuple)):
            raise ValueError("open_gate_ids muss eine ID-Liste sein")
        normalized["open_gate_ids"] = tuple(_id("open_gate_ids", gate) for gate in gates)
        entry = AgentCapability(**normalized)
        self._entries[(entry.project_id, entry.task_fingerprint)] = entry
        return entry

    def recommend(self, *, project_id: str, task_fingerprint: str, role_capability: str,
                  source_revision: str, tree_hash: str, independent_review: bool = False) -> dict:
        key = (_id("project_id", project_id), _id("task_fingerprint", task_fingerprint))
        current_role = _id("role_capability", role_capability)
        current_revision = _id("source_revision", source_revision)
        current_tree = _id("tree_hash", tree_hash)
        entry = self._entries.get(key)
        if independent_review or entry is None:
            return {"action": "fresh_agent", "reason": "independent review" if independent_review else "no compatible entry"}
        if entry.terminal_state == "terminal" or entry.role_capability != current_role:
            return {"action": "fresh_agent", "reason": "terminal state" if entry.terminal_state == "terminal" else "incompatible role"}
        if entry.source_revision != current_revision or entry.tree_hash != current_tree:
            return {"action": "refresh_delta", "load": "diff_and_direct_neighbors", "agent_id": entry.agent_id, "task_id": entry.task_id}
        return {"action": "reuse_followup", "load": "direct_neighbors_only", "agent_id": entry.agent_id, "task_id": entry.task_id}

    def get(self, project_id: str, task_fingerprint: str) -> dict | None:
        entry = self._entries.get((_id("project_id", project_id), _id("task_fingerprint", task_fingerprint)))
        return asdict(entry) if entry else None


def _zeit(value: str | None = None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    # strftime statt isoformat(): isoformat() haengt Mikrosekunden an, wenn
    # das datetime-Objekt welche traegt -- die Ratsche
    # tests/test_zeitform_utc.py verlangt genau 'YYYY-MM-DDTHH:MM:SSZ' ohne
    # Bruchteile (gemessen 2026-08-21: session_checkpoints.updated_at/
    # expires_at fielen darueber durch, obwohl schon auf UTC+Z stand).
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _id(name: str, value: object, *, leer: bool = False) -> str:
    if leer and value in (None, ""):
        return ""
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError(f"{name} muss eine technische ID ohne Freitext sein")
    lower = value.lower()
    if lower.startswith(SECRET_PREFIXES):
        raise ValueError(f"{name} sieht wie ein Geheimnis aus und wird nicht gespeichert")
    return value


def _ids(name: str, values: object) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list) or len(values) > 64:
        raise ValueError(f"{name} muss eine Liste mit höchstens 64 IDs sein")
    result = [_id(name, value) for value in values]
    if len(result) != len(set(result)):
        raise ValueError(f"{name} enthält doppelte IDs")
    return result


def ensure_schema(conn: sqlite3.Connection) -> None:
    expected = {
        "session_id", "project", "context_fraction", "topic_fingerprint",
        "active_requirement_ids", "expected_child_ids", "terminal_child_ids",
        "unresolved_evidence_ids", "used_knowledge_ids", "open_gate_ids",
        "role_capability", "source_revision", "terminal_state", "next_authorized_action", "status",
        "updated_at", "expires_at",
    }
    existing = {row[1] for row in conn.execute("PRAGMA table_info(session_checkpoints)")}
    if existing and existing != expected:
        # Checkpoints sind ausdrücklich temporär. Eine alte Freitext-Bauform
        # darf nicht neben der Datenschutzgrenze weiterbestehen.
        conn.execute("DROP TABLE session_checkpoints")
    conn.executescript(TABLE_SQL)


def setzen(conn: sqlite3.Connection, data: dict, *, now: str | None = None,
           ttl_seconds: int = 86_400) -> dict:
    extra = set(data) - FIELDS
    if extra:
        raise ValueError(f"nicht erlaubte Checkpoint-Felder: {', '.join(sorted(extra))}")
    if not 60 <= ttl_seconds <= 604_800:
        raise ValueError("ttl_seconds muss zwischen 60 und 604800 liegen")
    session_id = _id("session_id", data.get("session_id"))
    project = _id("project", data.get("project"))
    topic = _id("topic_fingerprint", data.get("topic_fingerprint"))
    action = _id("next_authorized_action", data.get("next_authorized_action"), leer=True)
    role = _id("role_capability", data.get("role_capability"), leer=True)
    revision = _id("source_revision", data.get("source_revision"), leer=True)
    terminal_state = data.get("terminal_state", "active")
    if terminal_state not in {"active", "terminal"}:
        raise ValueError("terminal_state muss active oder terminal sein")
    try:
        fraction = float(data.get("context_fraction"))
    except (TypeError, ValueError):
        raise ValueError("context_fraction muss eine Zahl zwischen 0 und 1 sein") from None
    if not 0 <= fraction <= 1:
        raise ValueError("context_fraction muss zwischen 0 und 1 liegen")
    lists = {name: _ids(name, data.get(name, [])) for name in LIST_FIELDS}
    timestamp = _zeit(now)
    row = {
        "session_id": session_id, "project": project,
        "context_fraction": fraction, "topic_fingerprint": topic,
        **{name: json.dumps(value, separators=(",", ":")) for name, value in lists.items()},
        "role_capability": role, "source_revision": revision,
        "terminal_state": terminal_state, "next_authorized_action": action, "status": "active",
        "updated_at": _iso(timestamp),
        "expires_at": _iso(timestamp + timedelta(seconds=ttl_seconds)),
    }
    conn.execute(
        """INSERT INTO session_checkpoints
           (session_id, project, context_fraction, topic_fingerprint,
            active_requirement_ids, expected_child_ids, terminal_child_ids,
            unresolved_evidence_ids, used_knowledge_ids, open_gate_ids, role_capability,
            source_revision, terminal_state, next_authorized_action, status, updated_at, expires_at)
           VALUES (:session_id, :project, :context_fraction, :topic_fingerprint,
                   :active_requirement_ids, :expected_child_ids, :terminal_child_ids,
                   :unresolved_evidence_ids, :used_knowledge_ids, :open_gate_ids, :role_capability,
                   :source_revision, :terminal_state, :next_authorized_action, :status, :updated_at, :expires_at)
           ON CONFLICT(session_id) DO UPDATE SET
             project=excluded.project, context_fraction=excluded.context_fraction,
             topic_fingerprint=excluded.topic_fingerprint,
             active_requirement_ids=excluded.active_requirement_ids,
             expected_child_ids=excluded.expected_child_ids,
            terminal_child_ids=excluded.terminal_child_ids,
            unresolved_evidence_ids=excluded.unresolved_evidence_ids,
            used_knowledge_ids=excluded.used_knowledge_ids, open_gate_ids=excluded.open_gate_ids,
            role_capability=excluded.role_capability, source_revision=excluded.source_revision,
            terminal_state=excluded.terminal_state,
            next_authorized_action=excluded.next_authorized_action,
             status=excluded.status, updated_at=excluded.updated_at,
             expires_at=excluded.expires_at""",
        row,
    )
    conn.commit()
    return lesen(conn, session_id, now=now) or {}


def _prune(conn: sqlite3.Connection, now: str | None = None) -> int:
    cur = conn.execute("DELETE FROM session_checkpoints WHERE expires_at <= ?", (_iso(_zeit(now)),))
    conn.commit()
    return cur.rowcount


def lesen(conn: sqlite3.Connection, session_id: str, *, now: str | None = None) -> dict | None:
    session_id = _id("session_id", session_id)
    _prune(conn, now)
    row = conn.execute("SELECT * FROM session_checkpoints WHERE session_id = ?", (session_id,)).fetchone()
    if row is None:
        return None
    result = dict(row)
    for name in LIST_FIELDS:
        result[name] = json.loads(result[name])
    return result


def schliessen(conn: sqlite3.Connection, session_id: str) -> bool:
    session_id = _id("session_id", session_id)
    cur = conn.execute("DELETE FROM session_checkpoints WHERE session_id = ?", (session_id,))
    conn.commit()
    return cur.rowcount > 0


def empfehlen(checkpoint: dict, current_topic_fingerprint: str) -> dict:
    current = _id("current_topic_fingerprint", current_topic_fingerprint)
    expected = set(checkpoint.get("expected_child_ids", []))
    terminal = set(checkpoint.get("terminal_child_ids", []))
    pending = sorted(expected - terminal)
    base = {"recommend_new_chat": False, "pending_child_ids": pending}
    if pending:
        return {"action": "integrate_children", **base}
    if current != checkpoint["topic_fingerprint"]:
        complete = (bool(checkpoint.get("active_requirement_ids"))
                    and not checkpoint.get("unresolved_evidence_ids")
                    and bool(checkpoint.get("next_authorized_action")))
        if complete:
            return {"action": "recommend_new_chat", "recommend_new_chat": True,
                    "pending_child_ids": []}
        return {"action": "complete_handoff", **base}
    if checkpoint["context_fraction"] >= .88:
        return {"action": "secure_all", **base}
    if checkpoint["context_fraction"] >= .75:
        return {"action": "secure_findings", **base}
    return {"action": "continue", **base}


def reuse_empfehlen(checkpoint: dict, *, project_id: str, task_fingerprint: str,
                    role_capability: str, source_revision: str,
                    independent_review: bool = False) -> dict:
    """Recommend reuse to the host; it never spawns agents or reads transcripts."""
    current = {
        "project": _id("project_id", project_id),
        "topic": _id("task_fingerprint", task_fingerprint),
        "role": _id("role_capability", role_capability, leer=True),
        "revision": _id("source_revision", source_revision, leer=True),
    }
    compact = {
        "project_id": checkpoint["project"], "task_fingerprint": checkpoint["topic_fingerprint"],
        "role_capability": checkpoint.get("role_capability", ""),
        "source_revision": checkpoint.get("source_revision", ""),
        "used_node_or_lesson_ids": checkpoint.get("used_knowledge_ids", []),
        "open_gate_ids": checkpoint.get("open_gate_ids", []),
        "terminal_state": checkpoint.get("terminal_state", "active"),
    }
    if independent_review or checkpoint.get("terminal_state") == "terminal":
        reason = "independent review" if independent_review else "terminal agent state"
        return {"action": "fresh_agent", "reason": reason, "checkpoint": compact}
    if checkpoint["context_fraction"] >= .75:
        return {"action": "fresh_agent", "reason": "context saturation", "checkpoint": compact}
    if current["project"] != checkpoint["project"] or current["topic"] != checkpoint["topic_fingerprint"]:
        return {"action": "fresh_agent", "reason": "project or task changed", "checkpoint": compact}
    if current["role"] != checkpoint.get("role_capability", ""):
        return {"action": "fresh_agent", "reason": "incompatible role", "checkpoint": compact}
    if current["revision"] != checkpoint.get("source_revision", ""):
        return {"action": "refresh_delta", "reason": "source revision changed",
                "load": "diff_and_direct_neighbors", "checkpoint": compact}
    return {"action": "reuse_followup", "reason": "compatible project task role and revision",
            "load": "direct_neighbors_only", "checkpoint": compact}


def demo() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    checkpoint = setzen(conn, {
        "session_id": "demo-1", "project": "brainlehr", "context_fraction": .5,
        "topic_fingerprint": "topic-1", "active_requirement_ids": ["MUST-DEMO-1"],
        "next_authorized_action": "ACTION-DEMO-1",
    })
    assert empfehlen(checkpoint, "topic-1")["action"] == "continue"
    assert empfehlen(checkpoint, "topic-2")["recommend_new_chat"]


if __name__ == "__main__":
    demo()
