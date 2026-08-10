# AI handoff

## 2026-08-10T22:48:00+02:00 — test(enigma): pin synthetic housekeeper confidentiality contract

- Files: `tests/test_enigma_hausmeister_contract.py`
- Why: The public MCP read path needs an executable, PII-free red acceptance case before an Enigma purpose-projection boundary is built.
- Verified: `pytest -q tests/test_enigma_hausmeister_contract.py` — 1 expected failure; `pytest -q --runxfail tests/test_enigma_hausmeister_contract.py` exposes the current raw content and metadata leak; focused existing identity/right/derivation suite passed (20 tests).
- Remaining risk: Identity binding only proves who called; this server still has no purpose, responsibility, recipient, or response projection decision.
- Next test: Implement one closed purpose/recipient gate and make Z0–Z8 green without exposing content, source, path, times, IDs, or edges.

## 2026-08-10T20:38:19+02:00 — docs(brainlehr): record client-documentation source gates

- Files: `docs/FREMDBESTAENDE.md`, `docs/PLAN_KLIENTENDOKU_2026-08-10.md`
- Why: Claude Code, Codex/ChatGPT, and Hermes documentation must be treated as linked, dated source material rather than copied into the repository.
- Verified: `git diff --check`; official Anthropic, OpenAI, and Nous Research pages opened on 2026-08-10; SQLite check confirmed the existing source nodes still have `gattung='arbeitsbestand'`.
- Remaining risk: `knowledge_add` and `knowledge_update` do not expose `gattung`; do not bypass their audit path with direct SQLite just to mark external documentation as `nachschlagewerk`.
- Next test: Add a tested MCP classification field, then create or reclassify one distilled node per client and verify all three are excluded from automatic recall.

## 2026-08-10T20:40:00+02:00 — test(compliance): recognize active Claude-Code knowledge MCP

- Files: `tests/test_agent_compliance.py`
- Why: The external compliance check only recognised the historical VS-Code `knowledge-mcp` entry, although the active Hub Claude-Code client declares the same server as `knowledge` in `.mcp.json`. It also classified the generated global lessons instruction as a narrow file.
- Verified: `python3 -m pytest -q tests/test_agent_compliance.py tests/test_caveman_integration.py` — 174 passed; the two remaining failures are the known, uncommitted Hub Caveman-policy contradictions below.
- Remaining risk: Hub's untracked `begod/knowledge/meta/caveman_policy.json` allows agent definitions and sets `ultra`, contrary to its `.github/instructions/caveman.instructions.md` and the failing policy tests; do not overwrite those foreign changes.
- Next test: After the Hub owner resolves that policy conflict, rerun `python3 -m pytest -q tests/test_caveman_integration.py`.

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
