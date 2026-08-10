# AI handoff

## 2026-08-10T20:33:15+02:00 — test(recall): align selftest fixture with active recall contract

- Files: `tests/test_knowledge_recall_hook.py`
- Why: The active recall path now requires `knowledge_nodes.gattung` and `lessons_learned.session`; it also logs empty recalls. The stale fixture hid SQL errors and asserted the old no-log behavior.
- Verified: `python3 -m pytest -q tests/test_knowledge_recall_hook.py` — 1 passed; `python3 tests/test_knowledge_recall_hook.py` — all five checks passed.
- Remaining risk: The fixture remains a focused schema subset and must follow future columns read by this hook.
- Next test: Run the full Brainlehr pytest suite after the independently modified `tests/test_agent_compliance.py` is settled.

## 2026-08-10T17:33:13+02:00 — feat(mcp): explain reference types at chat start

- Files: `knowledge_mcp_server.py`, `tests/test_version.py`
- Why: Every MCP-connected client should receive one canonical explanation of Brainlehr's four reference types when it initializes the server.
- Verified: `python3 -m pytest -q tests/test_version.py` — 5 passed.
- Remaining risk: MCP clients may ignore the optional `initialize.instructions` field; clients without Brainlehr MCP cannot receive it.
- Next test: Start fresh ChatGPT/Codex, Claude Code, and LM Studio chats and confirm each client surfaces the four-type explanation once.
