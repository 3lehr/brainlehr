# AI handoff

## 2026-08-16T21:07:47+02:00 — test(brainlehr): pin Weisungszitat red fixture

- Files: `tests/test_weisungszitat_beleg.py`, `AI_HANDOFF.md`; additionally updated the non-repository Codex instruction file `~/.codex/AGENTS.md` with the verified client contracts.
- Why: The historical red test loaded moving `HEAD:schema.sql`; after the feature commit, that schema already accepted `weisungszitat`, so the test no longer represented the pre-feature state. It now reads the parent of the feature commit that introduced the contract.
- Red: `python3 -m pytest -q tests/test_beinahefehler.py tests/test_weisungszitat_beleg.py tests/test_relevanzlage.py` — 1 failed, 41 passed; `test_rot_alter_stand_kennt_weisungszitat_nicht` did not raise.
- Verified: the same command — 42 passed; installed near-miss and Weisungszitat triggers were read from `sqlite_master`; Codex `knowledge_read(7b02ef68)` succeeded; configuration contains two current Brainlehr paths and no obsolete `hub/shared-knowledge` path.
- Remaining risk: The current Codex process still exposes the pre-update `knowledge_add` schema without `betreiber_weisung`; the app must restart to reload MCP tool metadata. The duplicate `knowledge` and `brainlehr` server entries were left intact because their intended compatibility boundary is not documented.
- Next test: After restarting Codex, inspect the loaded `knowledge_add` schema for `betreiber_weisung`, then perform no write unless a real rank-1/2 operator instruction needs recording.

## 2026-08-11T11:40:45+02:00 — fix(enigma): block projected reads when locked

- Files: `knowledge_mcp_server.py`, `kern/werkzeugrechte.py`, `tests/test_enigma_hausmeister_contract.py`, `docs/AI_DECISIONS.md`, `AI_HANDOFF.md`
- Why: `freigabe='gesperrt'` was ignored by the shared room-planning projection and still returned utility data. The lock now wins before role/tag projection, access-count mutation, or response delivery. The new visibility tool is assigned to the administrative write right instead of remaining unreachable or becoming ordinary writer authority.
- Red: `python3 -m pytest -q tests/test_enigma_hausmeister_contract.py -k gesperrter -vv` — 1 failed, 1 deselected; the locked synthetic node returned `nutzinformation`. First combined rights run — 1 failed, 28 passed; `freigabe_setzen` had no central rights mapping.
- Verified: targeted locked-node run — 1 passed, 1 deselected; `python3 -m pytest -q tests/test_enigma_hausmeister_contract.py tests/test_lehre_freigabe.py tests/test_werkzeugrechte_durchsetzung.py tests/test_ausweis_identitaet.py` — 29 passed.
- Remaining risk: This is a synthetic P1 read-path test. Search/browse, C0/C2/C3/C4, independent storage edges and P2 remain unmeasured; no anonymity, legal, compliance or production-security claim. The complete suite was not rerun because the unrelated untracked `tests/test_stammformen.py` remains foreign and red.
- Next test: Register a separate locked-node mutation for search/browse previews before expanding any Enigma claim.

## 2026-08-11T11:06:37+02:00 — fix(enigma): project credential-bound reads

- Files: `kern/ausweis.py`, `knowledge_mcp_server.py`, `tests/test_enigma_hausmeister_contract.py`, `docs/AI_DECISIONS.md`, `AI_HANDOFF.md`
- Why: The real public `knowledge_read` path returned raw protected content and metadata to the synthetic housekeeper. A narrow credential role now fixes purpose and field server-side and returns only the tagged utility projection or one metadata-free denial.
- Red: `python3 -m pytest -q --runxfail tests/test_enigma_hausmeister_contract.py -vv` — 1 failed; all three synthetic records returned raw content and metadata. `python3 -m pytest -q tests/test_brainlehr_umzug.py::test_erstanlage_traegt_dasselbe_schema_wie_der_betrieb -vv` — 1 failed; live-only empty tables `documents`, `chunks`, `bundle_cache` were absent from a fresh schema.
- Verified: `python3 -m pytest -q tests/test_brainlehr_umzug.py::test_erstanlage_traegt_dasselbe_schema_wie_der_betrieb tests/test_enigma_hausmeister_contract.py tests/test_werkzeugrechte_durchsetzung.py tests/test_ausweis_identitaet.py tests/test_enigma_two_process_spike.py` — 22 passed.
- Live-DB remediation: all three spike tables and associated `chunks_fts` had zero rows and no external schema/code references; structure-only recovery SQL is in ignored `backups/knowledge.db.spike-schema-vor-entfernung-20260811T110337+0200.sql`, then the artifacts were removed atomically. `schema.sql` was not expanded.
- Remaining risk: Projection policy is measured only with synthetic data. Search/browse, independent storage edges, C0/C2/C3/C4, and P2 remain unmeasured; no anonymity, legal, compliance, or production-security claim.
- Next test: Run the complete `python3 -m pytest -q tests/` suite, then design the next cheapest C0/C2/C3/C4 falsification without widening this projection.

## 2026-08-11T08:20:00+02:00 — solved: the 5.02 s per test was ONE hung transaction

- Files: none changed. Diagnosis + one process killed.
- Yesterday's full test run took 1276 s instead of 101 s, at 2 % CPU, uniformly 5.02 s per test. I blamed 21 concurrent MCP processes (wrong, withdrawn) and then measured 0.000 s lock acquisition and called it unproblematic (also wrong — measured in a quiet moment).
- Actual cause, measured while it was happening: PID 80063 (child of Claude Desktop, running 1:10 h) held a SQLite write lock WITHOUT writing — the WAL did not grow. Every other write burned the full `busy_timeout` of 5000 ms: `BLOCKED after 5.168 s: database is locked`. After killing that one process: same lock acquired in **0.001 s**.
- 5.02 s next to a 5000 ms busy_timeout was never a coincidence. The question nobody asked was not "how many processes" but "does one HOLD something without working".
- If your writes to `knowledge.db` ever hang for ~5 s: `lsof knowledge.db`, check whether `knowledge.db-wal` is growing. Not growing + writes failing = hung transaction, not contention.
- Lesson `L-2bdfea` (now 2 occurrences, both diagnoses recorded including the wrong ones).

## 2026-08-11 — test(enigma): falsify surviving key copy

- Files: `tests/test_enigma_crypto_shredding_spike.py`, `AI_HANDOFF.md`
- Why: Smallest synthetic P1 harness measures the baseline and kills a surviving `KEY_COPY`.
- Verified: `python3 -m pytest -q tests/test_enigma_crypto_shredding_spike.py` — 2 passed.
- Remaining risk: Four mutations and C0–C4 overall remain NOT_MEASURED; `A-c0edbd` remains open.
- Next test: `DETERMINISTIC_MASTER_DERIVATION`.

## 2026-08-11 — test(enigma): reject crypto shred bypasses

- Files: `tests/test_enigma_crypto_shredding_spike.py`, `AI_HANDOFF.md`
- Why: Extend the synthetic P1 harness so surviving key copies, deterministic master derivation, plaintext cache/log/vector consumers, shared blobs, and restoration without a current anchor are rejected.
- Verified: `python3 -m pytest -q tests/test_enigma_crypto_shredding_spike.py` — 8 passed.
- Remaining risk: This is only a synthetic harness; C0–C4, physical consumers/egress, and the P2 host boundary remain NOT_MEASURED; `A-c0edbd` remains open.
- Next test: Exercise the same mutation oracles against an independently implemented serving boundary, once one exists.

## 2026-08-11 — test(enigma): reject stale snapshot restore

- Files: `tests/test_enigma_crypto_shredding_spike.py`, `AI_HANDOFF.md`
- Why: The synthetic restore oracle previously checked only anchor presence; it now rejects snapshots older than the authenticated monotonic tombstone and accepts only a current sanitized snapshot.
- Verified: `python3 -m pytest -q tests/test_enigma_crypto_shredding_spike.py` — 8 passed.
- Remaining risk: This remains a synthetic harness; C0–C4, physical consumers/egress, and the P2 host boundary are NOT_MEASURED; `A-c0edbd` remains open.
- Next test: Exercise stale-anchor semantics against an independently implemented serving boundary, once one exists.

## 2026-08-11 — test(enigma): measure logical two-store boundary

- Files: `tests/test_enigma_two_process_spike.py`, `AI_HANDOFF.md`
- Why: A synthetic Pipe-based keyholder/workstore harness measures the existing crypto-shredding kills across distinct processes and exposes the same-UID direct-vault limitation.
- Verified: `python3 -m pytest -q tests/test_enigma_two_process_spike.py` — 1 passed.
- Remaining risk: `logical_two_store_only` is not P2: the parent can directly read the synthetic vault under the same UID (`P2_SHARED_ROOT_SAME_UID`). C0–C4 and a physical P2 boundary remain NOT_MEASURED.
- Next test: Repeat the harness with genuinely separate local UIDs and an external anchor.
- Harness repair: an initial IPC timeout came from `stop` returning no acknowledgement; a second failure was a vault-startup race. Both are test-only: explicit stop replies and a public-IPC initialization handshake.

## 2026-08-11 — test(enigma): exercise real IPC boundary state

- Files: `tests/test_enigma_two_process_spike.py`, `AI_HANDOFF.md`
- Why: Correct the review finding that parent-side flags were not boundary evidence: Workstore now owns public gate/restore/serve/introspection commands, real cache/log/vector data, shared A key/blob mutation, and session restart evidence.
- Verified: `python3 -m pytest -q tests/test_enigma_two_process_spike.py` — 1 passed.
- Remaining risk: Synthetic same-UID vault remains directly readable (`P2_SHARED_ROOT_SAME_UID`); logical two-store is not P2, and C0–C4 remain NOT_MEASURED.
- Next test: Repeat with separate local UIDs and an external anchor.
- Repair: key-mutant probe initially invoked the mutation after deletion, masking it; it now invokes mutation pre-delete and verifies its exact post-delete public kill.

## 2026-08-11 — test(enigma): prove stale handle revocation

- Files: `tests/test_enigma_two_process_spike.py`, `AI_HANDOFF.md`
- Why: Prove stale Pipe closure and the real post-unlink vault-FD mutation; Workstore receives only opaque handle evidence and rejects it as `CACHE_FD_SESSION`.
- Verified: `python3 -m pytest -q tests/test_enigma_two_process_spike.py` — 1 passed.
- Remaining risk: The old vault FD remains readable after unlink by design; this is a detected mutation that blocks denial-pass, not a repair. Same-UID direct vault read remains `P2_SHARED_ROOT_SAME_UID`.
- Next test: Separate local UIDs plus an externally anchored vault process.

## 2026-08-11 — test(enigma): observe stale fd independently

- Files: `tests/test_enigma_two_process_spike.py`, `AI_HANDOFF.md`
- Why: Replace self-reported stale-handle state with a host-side `lsof` observation of the parent’s still-readable unlinked synthetic vault FD.
- Verified: `python3 -m pytest -q tests/test_enigma_two_process_spike.py` — 1 passed.
- Remaining risk: The open FD is intentionally a detected mutation; it blocks denial-pass. Same-UID direct vault read remains `P2_SHARED_ROOT_SAME_UID`; no P2 claim.
- Next test: Repeat under separate local UIDs with an external anchor.

## 2026-08-11 — test(enigma): isolate boundary process lifecycles

- Files: `tests/test_enigma_two_process_spike.py`, `AI_HANDOFF.md`
- Why: Repair the invalid lifecycle baseline from `cfea586`: every Keyholder/Workstore run now owns a fresh Pipe, the parent closes each child end immediately, and the clean baseline is measured before any stale FD exists.
- Verified: `python3 -m pytest -q tests/test_enigma_two_process_spike.py` — 3 passed; `python3 -m pytest -q tests/test_enigma_two_process_spike.py -k 'crypto_mutants or fd_and_same_uid_mutants'` — 2 passed, 1 deselected.
- Remaining risk: The independently observed unlinked FD blocks denial-pass as `CACHE_FD_SESSION`, and same-UID direct vault access remains `P2_SHARED_ROOT_SAME_UID`; this proves only `logical_two_store_only`, not P2. C0–C4 remain NOT_MEASURED.
- Next test: Repeat the same boundary checks with separate local UIDs and an external anchor.
- Root cause repaired: the prior test opened `old_fd` before claiming baseline PASS and reused `kp_child` across processes, so its baseline and lifecycle evidence were invalid.

## 2026-08-11 — test(enigma): enforce grant projection boundary

- Files: `tests/test_enigma_two_process_spike.py`, `AI_HANDOFF.md`
- Why: Repair `C1_DIRECT_UNGRANTED_DECRYPT` by removing raw public decrypt operations, separating Serving from privileged Control IPC, and validating server-registered grants before every protected read.
- Red: `python3 -m pytest -q tests/test_enigma_two_process_spike.py -k 'c1_missing_grant or c1_wrong_purpose'` — 2 failed, 3 deselected: raw `a` returned `SYNTHETIC-A`; a wrong-purpose request produced no denial response.
- Verified: `python3 -m pytest -q tests/test_enigma_two_process_spike.py -k c1` — 3 passed, 3 deselected; full file — 6 passed; mutation/control separation selection — 3 passed, 3 deselected.
- Remaining risk: This is a synthetic P1 harness only. Same-UID direct vault access remains `P2_SHARED_ROOT_SAME_UID`; no P2, anonymity, legal, compliance, or production-security claim. C0/C2/C3/C4 remain unmeasured after this C1 repair.
- Next test: Re-run the independently defined C1 diagnostic against the Serving channel, then proceed only to the next cheapest C0–C4 kill.
- C1 matrix: exact 1/4, 2/4, 4/4 projections; 16 one-factor grant mutations plus missing grant, nonce replay, revoked replay, deleted subject, raw/control-command denial; denial is always `{content: None, metadata: None, protected_edge_reads: 0}` and does not increment protected reads.

## 2026-08-11T08:15:00+02:00 — operator: act, do not ask (applies to Codex too)

- Files: `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md` (both backed up first).
- The operator granted a standing licence to act without presenting first, for as long as this is a single-user test environment. Revocation word: **`es wird ernst`**. Explicitly extended to Codex: *"chatgpt soll das gleiche machen! sage ihm das, bring ihm das bei!"*
- Not covered, independently: passwords (operator types them), effects on THIRD parties, and anything the agent itself considers wrong. The burden of evidence is unchanged — red before green stays.
- Also added there: **short agreement is a decision**. A one-word "ja" carries the content of YOUR question; record it when it is irreversible, overrides an earlier rule, holds beyond the session, or involves money — otherwise write nothing.
- Nodes `21011af9` (licence) and `c4f49007` (short agreement), lesson `L-27ffc8`.


## 2026-08-11T07:35:00+02:00 — finding: the parallel-session reporter is blind to non-Claude clients

- Files: none changed (the hook lives in `hub/`, which carries 109 uncommitted files of someone else's work).
- What happened: at session start `projekt_waehler_hook.py` reported "keine weitere offene Claude-Sitzung gemessen (lsof)" — while 8 live parent sessions were running (14 of the 21 MCP processes under `codex`) and a Codex session had made FIVE commits overnight, touching exactly the test files this session was tracking as open.
- Why it is blind: its stronger question ("not where someone stands, but where they reach") is fed by the agent register, and that register is filled by `agent_register_hook.py` — a Claude Code hook. A foreign client never triggers it. Measured over 24 h, the register knows three sessions (28 / 15 / 8 file events), all Claude; the Codex session with five commits appears with zero.
- The wording is literally correct — it says "Claude session". That is what makes it misleading: it reads as an all-clear.
- Proposed fix, no new machinery: add one client-independent source. `git log --since <last own state>` sees every commit regardless of client, and would have reported the five commits with their file list.
- Recorded as lesson `L-87532c`; coordination state in node `23456f3b`.


## 2026-08-11T07:22:00+02:00 — note: coordination now also lives in the store

- Node `23456f3b` (`/brainlehr/zwei-sitzungen-arbeiten-parallel-an`) carries the
  CURRENT division of work and is overwritten as it changes. This file carries
  the individual event and grows. Two questions, two places: "who is where right
  now" vs. "what just happened".
- Read it with `knowledge_read 23456f3b` before touching a file the other
  session might hold.


## 2026-08-11T07:15:00+02:00 — measure(locks): the 21 server processes cost nothing measurable

- Files: none changed. Measurement only.
- Why: Yesterday a full test run took 1276 s instead of 101 s, at 2 % CPU and exactly 5.02 s per test — a wait, not computation. I attributed it to 21 concurrent `knowledge_mcp_server` processes contending for `knowledge.db` and recommended cleaning them up first. That recommendation was wrong and I am withdrawing it.
- Verified now, with 21 processes running: plain read 0.001 s (2081 nodes) · `BEGIN IMMEDIATE` write lock 0.021 s · the server's own `_write_lock()` (flock on `knowledge.db.lock`) acquired in 0.000 s. SQLite/WAL is not the bottleneck, and the file lock is not held.
- The 21 processes belong to 8 live parent sessions (mostly `codex`, two Claude Desktop, two python). None is orphaned — killing them would interrupt your running sessions, not free a resource.
- Remaining risk: the 5.02 s per test from yesterday is therefore NOT explained. It was reproducible and uniform, so something serialised those runs; the candidate is no longer the lock. Unmeasured: whether it was the `--durations` path, an embedding call with a network timeout, or a per-test fixture. Do not repeat "too many processes" as the cause — it is measured false.
- Next test: instrument one slow test with a timestamp before/after each fixture, rather than guessing again.

## 2026-08-11T07:10:00+02:00 — note: parallel sessions, division of files

- Files: none. Coordination note.
- Working here (Claude Code, worktree `hallo-acd761`): measurement of lock/process contention, and the question whether stdio should become a shared HTTP server for multi-session use (node `3b4c7f68` names exactly this trigger).
- NOT touching, assumed yours: `tests/test_enigma_*`, `docs/FREMDBESTAENDE.md`, `docs/PLAN_KLIENTENDOKU_2026-08-10.md`, `AI_HANDOFF.md` beyond appending.
- Shared and not separable by worktree: `knowledge.db` and the README of the giveable repo. Both were edited by both of us yesterday.
- Note: six `git worktree` trees exist but both sessions were writing in the main tree.


## 2026-08-10T23:00:00+02:00 — test(enigma): extend synthetic contract to consent and trade-secret gates

- Files: `tests/test_enigma_hausmeister_contract.py`
- Why: The red Enigma acceptance case must distinguish a broad Stufe-0 release, a narrow field/purpose release, and a non-personal trade secret; none may be exposed by the raw public read path without its own gate.
- Verified: `pytest -q tests/test_enigma_hausmeister_contract.py` — 1 expected failure; `pytest -q tests/test_enigma_hausmeister_contract.py --runxfail` — 1 failure, raw content and metadata returned for all three synthetic records; `pytest -q tests/test_ausweis_identitaet.py` — 7 passed.
- Remaining risk: Tags are test labels, not enforcement. `knowledge_read` has no purpose, recipient, field, provider, or trade-secret decision and remains red by design.
- Next test: Add one closed gate/projection boundary, then require A deny, B minimal utility response, and trade-secret deny before lifting this xfail.

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
