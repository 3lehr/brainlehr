# AI architecture decisions

## 2026-08-26 — Retain BGE-M3 after modality-expanded code retrieval measurement

- Context: The first frozen screening set covered only English prose→Python. The operator required language and modality separation plus a Brainlehr-prose nonregression control before any separate code channel could be considered.
- Decision: Keep BGE-M3 as the only active semantic channel. The frozen benchmark now reports EN prose→Python, DE prose→the same Python candidates, code/signature→Python, and DE Brainlehr prose→prose; CodeRankEmbed is not integrated.
- Reason: CodeRankEmbed won only code/signature→Python (R@1/MRR 0.70/0.7766 versus BGE-M3 0.60/0.7025). It lost EN prose→Python (0.50/0.6594 versus 0.70/0.7722), DE prose→Python (0.10/0.2536 versus 0.50/0.6684), and the prose control (0.60/0.7183 versus 0.80/0.8750). Thus it fails the predeclared all-code-win and prose-nonregression rule.
- Rejected alternatives: treat the one code-signature win as sufficient; add a second persistent index anyway; put source paths into model inputs; or invent a CodeRank document prefix. The official model card specifies the query-only prefix `Represent this query for searching relevant code` and encodes code without a document prefix.
- Verification: `python3 -m pytest -q tests/test_requirements_brainlehr.py tests/test_code_retrieval_benchmark.py` (6 passed); local 52-case run at `/Volumes/daten/code-retrieval-matrices-2026-08-26.json`; outcome recorded in `L-b32c2a`.
- Boundary: This is a small frozen screening corpus, not a general code-retrieval benchmark or a claim about all languages. Re-run unchanged for each new candidate; only an all-matrix win changes production retrieval.

## 2026-08-26 — Keep BGE-M3 as the only active semantic channel

- Context: The operator requested a separate local code-retrieval model only if a reproducible local comparison actually wins. CodeRankEmbed is a small MIT candidate (768 dimensions, local weights); it was compared with BGE-M3 on the same frozen 10-positive/3-negative symbol goldset and 181 Python-symbol candidates.
- Decision: Do not integrate CodeRankEmbed. BGE-M3 won Recall@1 (0.80 vs 0.60), MRR (0.8643 vs 0.7007), Recall@10 (1.00 vs 0.90), and elapsed time (27.266 s vs 30.349 s). The checked-in goldset and read-only benchmark remain for later candidates; artifacts and runtime stay outside Git.
- Reason: A code-specialized label and external benchmark do not outweigh a direct local loss. Keeping one active semantic channel preserves the existing fallback, model lock, privacy boundary, and package dependency contract.
- Rejected alternatives: activating CodeRankEmbed despite the result; concatenating or comparing cross-model vectors; deriving a dependency edge from semantic similarity; adding a persistent second index before a candidate wins.
- Verification: `python3 -m pytest -q tests/test_requirements_brainlehr.py tests/test_code_retrieval_benchmark.py` (5 passed); local read-only run recorded in `L-6e0c0f`.

## 2026-08-26 — Harden project-context contracts before adding analyzers

- Context: The P23–P28 consilium verified the useful narrow core but found overstrong static-coverage wording, mutable same-commit receipts, relative-import blind spots, and export paths that were not yet bound to tracked repository inputs.
- Decision: Keep the standard-library Python-import analyzer small, name its coverage exactly, record corrections as superseding receipts, and bind public allowlists/sources/output to repository paths. Public content remains allowlisted and known-pattern screened; human review remains mandatory for the semantic/privacy decision.
- Reason: Explicit limits preserve reproducible evidence and prevent a vector or heuristic from being mistaken for runtime data flow. This is less machinery than a universal analyzer, ontology, or secret scanner while closing the present false-negative paths.
- Rejected alternatives: a universal build parser, automatic consumer rewrites, embeddings as dependency edges, mutable receipts, or describing regex screening as a privacy guarantee.
- Verification: `python3 -m pytest -q tests/test_project_context.py tests/test_public_context_export.py tests/test_requirements_brainlehr.py` — 17 passed.
- Boundary: Test labels and semantic summaries remain caller-provided evidence. Runtime, schema, build and I/O dependencies need a registered analyzer plus measured coverage before joining the impact chain.

## 2026-08-25 — Public project knowledge exports only an explicit safe slice

- Context: A public release needs a reproducible architecture handoff from the verified local database, but a public `freigabe` alone is too broad for a concise project context and DB provenance can contain local operational details.
- Decision: `pflege/export_public_context.py` exports only paths named in `docs/public-knowledge/brainlehr-nodes.json`, requires the `brainlehr` scope and `freigabe='offen'`, compares each node timestamp to its declared Git sources, and emits only title, summary, content, update time and public exporter provenance. Missing, stale, private or non-public nodes reject before writing.
- Reason: A tracked allowlist makes the public surface reviewable and deterministic; excluding raw DB metadata makes accidental session, identity, operator instruction and local-path release structurally impossible on this route.
- Rejected alternatives: exporting all open nodes, committing SQLite, a blacklist of private fields, copying `source` provenance verbatim, or quietly retaining an old artifact on failed validation.
- Verification: `python3 -m pytest -q tests/test_public_context_export.py` — 3 passed; a live export wrote the three allowlisted nodes and a second run returned `current`. The tests cover deterministic bytes plus missing, stale, non-public and private-content rejection.
- Boundary: The export verifies its selected node texts, not arbitrary personal data hidden behind an unrecognised text pattern. New public material needs an allowlist entry and explicit review.

## 2026-08-25 — Versioned project context uses evidence, not guessed architecture

- Context: A new context window needs enough verified project knowledge to work safely, while a whole-codebase dump wastes context and import/data-flow heuristics had already produced 35 false positives (`L-503687`).
- Decision: Keep a stable, client-neutral `.brainlehr.json` for explicit registrations and generate Git facts/native entry points into a separate capsule. Context loads summary, selected relations, then selected full text, each with a machine-readable next choice. For code impact, persist one append-only receipt per commit and traverse only versioned, explicitly typed static edges; current analysis covers Python imports and reports all other coverage as a gap.
- Reason: Git revisions and AST positions are reproducible evidence; bounded retrieval saves tokens without concealing the caller's available choices. A static import creates a validation obligation, never a claim of runtime data flow.
- Rejected alternatives: copying raw code or symbol tables into knowledge, recursive branch loading, a global fixed tool catalog, vector similarity as an edge, and heuristic input/output timing from imports.
- Verification: `python3 -m pytest -q tests/test_project_context.py tests/test_requirements_brainlehr.py tests/test_werkzeugrechte_durchsetzung.py` — 20 passed; `python3 -m py_compile kern/project_context.py knowledge_mcp_server.py`; `python3 tool/faehigkeitskarte.py --pruefen`.
- Boundary: LSP/SCIP, schema, runtime-trace and I/O-contract edges need a project-registered analyzer and an explicit evidence artifact before they can participate in the impact chain.

## 2026-08-17T22:08:09+02:00 — One BDW root catalog governs Brainlehr

- Context: Accepted ADRs, plans, two local requirements catalogs and the target-picture research described overlapping parts of Brainlehr, while ADR-025/026 were referenced but absent. The operator supplied a complete 53-value Wizard matrix and selected a new Root purpose decision, a governed core, clear profiles and target picture A.
- Decision: `docs/REQUIREMENTS_BRAINLEHR.md` is the single normative product catalog. Its 53 existing `BDW-*` decision IDs become stable Requirement/Decision IDs; deterministic `-AC1` acceptance IDs are subordinate. Existing local requirement IDs remain implementation gates under the Root. Catalog status and product-test status are separate.
- Reason: Reusing the operator's IDs preserves traceability from question through decision, implementation and acceptance without introducing another numbering system. It also keeps resolved conflicts, pilots and the deferred deployment-profile choice visible.
- Rejected alternatives: promote Research `RQ-*` IDs to product requirements; merge all local test IDs into a new global scale; treat missing ADR-025/026 as accepted; or maintain several independently canonical catalogs.
- Verification: `python3 -m pytest -q tests/test_requirements_brainlehr.py` — 2 passed after the expected red missing-catalog run; the test verifies exactly 53 unique selections, their decoded labels, norm/status fields, `AC1`, `NOT RUN`, overview consistency and both subordinate catalog links.
- Boundary: “Agil und ohne Dogma” permits versioned updates to the same IDs, never removal of evidence, security, conflict or test gates. The catalog binds scope but does not claim implementation acceptance.

## 2026-08-17T20:07:46+02:00 — Keep session checkpoints technical and temporary

- Context: Durable project files already carry requirements and evidence, but hosts need a small recoverable state for context warnings, delegated-child completion, and topic-change recommendations.
- Decision: Reuse the existing Brainlehr SQLite/MCP boundary for one TTL-limited row per session. Persist only validated technical IDs and state; compute the rollover recommendation deterministically. Brainlehr never opens a thread and the checkpoint is never indexed or injected automatically.
- Reason: Disk writes and deterministic checks consume no model tokens, while a raw summary log would duplicate knowledge, retain private conversation text, and create a second source of truth.
- Rejected alternatives: append-only free-text handoff records, full transcript storage, a second memory service, per-prompt checkpoint injection, and automatic host thread creation.
- Verification: `python3 -m pytest -q tests/test_session_checkpoint.py tests/test_werkzeugrechte_durchsetzung.py tests/test_public_prompt_templates.py` passed 19 tests; the installed database exposes the expected 12 checkpoint columns and 57 non-empty trigger definitions in `sqlite_master`.
- Boundary: The MCP result is a recommendation. Claude, Codex/ChatGPT, or Hermes remains responsible for acting on it.

## 2026-08-17 — Deterministic prompt-invariance evidence gate

- Decision: Only measured deterministic runs can recommend a winner; preference and role framing are never evidence.

## 2026-08-17 — Canonical ID-based requirements gate

- Decision: Complex artifact and model work uses one canonical, stable-ID requirements catalog; changes enter it before implementation, conflicts remain visible, and delivery requires every MUST/MUST-NOT gate.
- Verification: installed global instruction checked by exact assertions.

## 2026-08-17 — Keep required delegated batches behind a completion gate

- Context: Background reviewers can finish after the parent has already ended its turn. Their finals remain available, but a queued completion does not by itself guarantee a new parent turn; a later user prompt can accidentally become the discovery mechanism.
- Decision: One live coordinator owns every required batch, including expected child IDs, terminal state, result integration, and the next already-authorized action. The parent may not treat “agents are running” as a terminal state. Escalated human-readability lessons also enter the Codex instruction plane: automated artifact checks supplement, but never replace, operator comprehension and an approved pre-render wireframe after rejection.
- Reason: Brainlehr can preserve and recall the rule only inside a running turn. Scheduling a parent continuation is an orchestrator responsibility, while artifact comprehensibility is an acceptance criterion rather than a renderer property.
- Rejected alternatives: passive child messages (no guaranteed idle-parent wake), repeated progress polling (noise without a completion contract), and a Brainlehr hook pretending to schedule Codex (wrong system boundary).
- Verification: two completed child finals were available 592 and 844 seconds before the next user-triggered parent turn; the global Codex instruction file now contains both gates and was checked by exact assertions. Brainlehr node `38f0ca59` records the full evidence; lesson `L-dafc34` is escalated after three occurrences.
- Boundary: The instruction rule prevents the model from deliberately ending an owned batch early. A hard guarantee still requires the Codex host to enqueue exactly one idempotent parent continuation when the last expected child becomes terminal.

## 2026-08-17 — Keep Claude complete; gate ChatGPT at one MCP choke point

- Context: Brainlehr remains Claude-first, but ChatGPT and Hermes need the same prompt-invariance decision check. A ChatGPT tunnel must not accidentally expose the full private knowledge surface when only those checks are needed.
- Decision: The default stdio MCP remains unchanged for Claude. `BEGOD_KNOWLEDGE_PROFIL=prompt-invariance` lists and permits exactly `prompt_invarianz_planen` and `prompt_invarianz_pruefen`; the restriction is enforced again at `tools/call`. OpenAI Secure MCP Tunnel supplies authenticated HTTPS without a public Brainlehr listener.
- Reason: one provider-neutral core preserves behavior across agents, and one dispatch choke point prevents calls to merely hidden tools.
- Rejected alternatives: a separate ChatGPT HTTP/OAuth server (duplicate transport and auth boundary), profile filtering only in `tools/list` (direct-call bypass), and reducing Claude's default tool set (breaks the primary client).
- Verification: 17 focused tests, rights selftest, and a real stdio lifecycle probe; unauthorized `knowledge_search` returned `profil:prompt-invariance`.
- Boundary: The live OpenAI tunnel cannot be claimed until the operator authenticates and creates its runtime key. This is not a BSI or compliance certification.

## 2026-08-11 — Locked visibility overrides serving projections

- Context: The credential-bound room-planning projection and the later
  `freigabe` write path independently decided whether a node could be served.
  A node marked `gesperrt` still returned its utility projection.
- Decision: `freigabe='gesperrt'` is checked first in the shared projection
  function and always returns the same metadata-free denial. Changing
  `freigabe` through MCP requires `verwaltung:schreiben`.
- Reason: A lock must dominate narrower role/tag grants, and visibility is an
  administrative decision rather than an ordinary content edit.
- Rejected alternatives: filtering the response after projection (too late),
  duplicating the check in each caller (future bypass risk), and assigning
  `wissen:schreiben` (would let every writer change visibility).
- Verification: `python3 -m pytest -q tests/test_enigma_hausmeister_contract.py tests/test_lehre_freigabe.py tests/test_werkzeugrechte_durchsetzung.py tests/test_ausweis_identitaet.py` — 29 passed.
- Boundary: Synthetic P1 evidence only; no P2, anonymity, legal, compliance,
  production-security, or complete C1 claim.

## 2026-08-11 — Bind narrow knowledge projections to credentials

- Context: The synthetic housekeeper acceptance test showed that the real
  `knowledge_read` MCP path returned full content and metadata to a credential
  that only needed one room-planning field.
- Decision: A dedicated `raumplaner` credential role fixes the serving purpose
  and allowed field server-side. A node may narrow this policy with
  `zweck:raumplanung` and `feld:nutzinformation`; every other node receives the
  same metadata-free denial. The credential identity is the recipient.
- Reason: Purpose, field, and recipient must not be freely asserted by the
  request that asks for protected data.
- Rejected alternatives: client-supplied purpose/grant fields (self-asserted
  authority), actor-name special casing (identity-specific policy), and
  filtering after the raw handler response (protected data already read).
- Verification: `python3 -m pytest -q tests/test_brainlehr_umzug.py::test_erstanlage_traegt_dasselbe_schema_wie_der_betrieb tests/test_enigma_hausmeister_contract.py tests/test_werkzeugrechte_durchsetzung.py tests/test_ausweis_identitaet.py tests/test_enigma_two_process_spike.py` — 22 passed.
- Boundary: This is a synthetic P1 contract. It is not a P2, anonymity, legal,
  compliance, or production-security claim; C0/C2/C3/C4 remain unmeasured.
