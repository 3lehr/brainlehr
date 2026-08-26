# AI architecture decisions

## 2026-08-26 — Evidence adapters are bounded, revisioned inputs; projections are derived offline artifacts

- Context: P40–P62 require a single typed graph without allowing external tools, raw traces, or embeddings to create unverified knowledge. The earlier “adapter-later” research note is superseded by the operator's later decision to provide the listed channels as optional local evidence paths now.
- Decision: Tree-sitter, SCIP, Joern/CPG, OTLP, Semgrep and optional CodeQL normalize outside the knowledge write path. The registry has an executable allowlist, scrubbed environment, CPU/memory/file limits where the host supports them, bounded on-disk hashed output, explicit timeout/outage results and an explicit host-network-isolation gap. Graph evidence is kept out of prose embeddings; only a separately curated human summary may be semantically indexed. Cytoscape output is an offline artifact: the CLI copies a local licensed asset beside revision/hash-bound HTML, never a CDN. Compatible agent work is selected by technical registry data only; a fresh independent reviewer remains mandatory.
- Reason: The safe common denominator is a write-free analyzer boundary and a deterministic projection. Reporting an unavailable sandbox property is safer than treating a local subprocess as isolated.
- Rejected alternatives: analyzer-direct SQLite writes; raw stdout/stderr or OTLP attributes in a receipt; embedding machine graph JSON; an online visualization dependency; or reusing an agent/transcript for an independent review.
- Verification: `python3 -m pytest -q tests/test_code_retrieval_benchmark.py tests/test_session_checkpoint.py tests/test_requirements_brainlehr.py` (18 passed); `python3 -m pytest -q tests/test_project_context.py tests/test_project_boundary.py tests/test_evidence_adapters.py tests/test_evidence_graph.py tests/test_analyzer_registry.py tests/test_codeql_policy.py tests/test_dependency_evidence.py tests/test_graph_envelope_store.py tests/test_actor_project_boundary.py tests/test_release_identity.py tests/test_coverage_provenance.py tests/test_public_prompt_templates.py` (50 passed); Cytoscape CLI artifact test and analyzer runner test subsequently brought their focused group to 14 and 11 passed.
- Boundary: This does not make the host a sandbox, make Joern available without its local runtime, or turn synthetic fixtures into a universal multi-language quality result. The explicit tracked-suite run was stopped after 65 passed because legacy `melder/abrufwirkung.py` remained non-progressing for over 90 seconds; the untracked `korpora/` tree was excluded by construction.

## 2026-08-26 — Revision-bound evidence graph and optional analyzers fail closed

- Context: Static imports alone cannot prove symbols, control/data flow, runtime timing, rule findings or cross-language impact. The operator required real local tool channels while keeping one graph and no automatic knowledge writes.
- Decision: Graph v2 adds typed evidence envelopes and explicit revision conflicts. Optional tree-sitter, SCIP, Joern/CPG, OTLP, Semgrep and CodeQL artifacts normalize at one ABI; missing executable, timeout, invalid input, vendor/generated input or license failure returns a coverage gap. CodeQL is never default: it needs an explicit request plus public-OSI source or declared GitHub Code Security entitlement; private `origin` is not scanned absent that basis. Cytoscape/Mermaid read the graph only.
- Reason: “Incomplete, not wrong” preserves safe impact selection across concurrent revisions and tool outages. A separate evidence adapter can be independently measured without turning embeddings, rules, CPG or traces into the same claim.
- Verification: local `scip-python 0.6.6` generated a 5.4 MiB `kern` index under `/Volumes/daten/brainlehr-tool-cache` and surfaced its missing `[tool.pyright]` coverage warning; Semgrep 1.146.0 ran 151 rules on `project_context.py` with zero findings; `tree-sitter 0.25.10` is locally available. Joern Docker invocation was blocked because the local Docker daemon socket was unavailable; that state is represented as a gap, not a fallback. Cytoscape 3.34.2 (MIT), tree-sitter (MIT), SCIP/scip-python (Apache-2.0), Joern (Apache-2.0), OpenTelemetry (Apache-2.0), Semgrep (LGPL-2.1) and CodeQL terms are recorded from their official repositories.
- Boundary: This is engineering evidence, not a CodeQL-license, BSI, security or compliance certification. The current Cytoscape shell requires a colocated local MIT asset; no CDN or private telemetry payload is used.

## 2026-08-26 — Keep edit analysis ephemeral, revision-bound and non-recursive

- Context: Code context must follow a batch of edits and indirect consumers without writing a receipt for every keystroke or silently replacing the last revision-bound graph.
- Decision: Keep the committed graph immutable and pin a client-local working-tree overlay to `(repo, base_commit, tree_hash, analyzer_version)`. A tiny in-memory controller debounces completed tool batches with latest-wins, cancels stale work, hashes every idempotency event, limits reruns and exposes a circuit-breaker gap. It has no watcher or daemon. Build/test recompute only after a changed overlay hash; commit reads the separate staged snapshot and gate; post-commit requests exactly one append-only `project_change` receipt. Timing exists only after a verified test/run and carries revision plus tree hash.
- Reason: Git hashes are reproducible, while a transient overlay makes current work available without persisting source or transient activity. Origin/correlation guards prevent generated exports, maps and receipts from recursively becoming source-analysis events.
- Rejected alternatives: write on every save or editor event; overwrite a prior graph snapshot; use unbounded background analysis; infer timing from imports; make the analyzer edit code; or treat working and staged trees as the same evidence.
- Verification: `python3 -m pytest -q tests/test_project_boundary.py` proves coalescing, no edit durable writes, same-hash current state, stale-result discard, generated-artifact bypass, staged/unstaged separation, one post-commit request and timing binding.
- Boundary: This controller schedules a client action but does not observe editor/build/test processes itself, write any durable record, or prove runtime data flow. Untracked content stays an explicit overlay gap until staged.

## 2026-08-26 — Generate thin client bootstraps from one untrusted-data boundary

- Context: Claude hooks, Hermes provider callbacks, and Codex AGENTS/skills/MCP expose different lifecycle seams. Their existing long instructions are only partly lazy, and a hosted ChatGPT system prompt cannot be replaced by a repository file.
- Decision: `docs/CLIENT_BOOTSTRAP_POLICY.json` is the sole tracked policy bundle. It generates three short public adapters with the identical MCP boundary fields, policy schema/hash/source revision and lazy T0–T4 ladder. Only this bundle may define machine-coded `must`; recalled knowledge, code, comments and tool evidence remain untrusted data. Adapters map native lifecycle only, retain neither prompts nor hidden reasoning, and report estimated token caps rather than billing telemetry.
- Reason: One hash-checked source removes prompt drift while keeping the always-on text small. Policy identity lets a client reject stale generated text without storing a conversation or trusting data as instructions.
- Rejected alternatives: three hand-maintained large prompts; a persistent user modality profile; placing an instruction in recalled knowledge; claiming a universal pre-send hook; or replacing the hosted ChatGPT system prompt.
- Verification: `python3 melder/client_bootstrap.py --check`; `python3 -m pytest -q tests/test_public_prompt_templates.py tests/test_project_boundary.py` check three generated adapters, bounded measurements, stale rejection, policy metadata and strict operation parsing.
- Boundary: This is a documented adapter contract, not a guarantee that any arbitrary client installs the adapter or that a hosted service exposes hidden lifecycle events.

## 2026-08-26 — Keep task modality request-local and staged acknowledgements narrow

- Context: Project facts can identify a Git worktree but cannot honestly identify the user's intent. The server sees no complete edit/build/test event stream, while raw prompts or persistent modality profiles would retain unnecessary conversation data.
- Decision: Add a deterministic boundary contract: explicit `knowledge|code|mixed` wins; otherwise only a non-empty staged tree is a server-verified code signal, then a named Brainlehr operation, else `unknown`. Knowledge-only performs no repository scan. A project opts into a staged-tree gate through one registered tool; its append-only local acknowledgement binds the base commit and SHA-256 of the staged diff. The post-commit impact receipt remains the authoritative change evidence.
- Reason: This is the smallest client-neutral contract that makes choice visible without pretending to observe hidden thinking or tool activity. It follows BSI guidance `TEST.1.3` at local library commit `12abb438fcdb4f4b63fb3e751e89d7c526e647b5` as engineering guidance for controlled, traceable changes; it is not a certification claim.
- Rejected alternatives: infer code work from cwd/repository/configuration; collect prompts or a durable user profile; install a second mandatory Git hook; or use a local acknowledgement as proof of runtime, build, timing, or data-flow behavior.
- Verification: `python3 -m pytest -q tests/test_project_boundary.py tests/test_project_context.py tests/test_requirements_brainlehr.py tests/test_werkzeugrechte_durchsetzung.py`; CLI and MCP expose the same modes, rejection does not write an acknowledgement, and changing the staged tree invalidates it.
- Boundary: A local hook or CLI can be bypassed and is not a security boundary. Registered tests/traces/contracts are still required for runtime/timing claims.

## 2026-08-26 — Metroviz remains a revision-bound projection, not an analyzer

- Context: A human graph view could make impact distance, edge delta, test evidence, timing contracts and coverage gaps easier to inspect. The requested source-backed Fahrtenbuch Metroviz JSON was not accessible at the supplied path during this change.
- Decision: Register only a planned `metroviz-impact-projection` capability. A future adapter may project one receipt/trace revision into those separately selectable views; the AI client continues to receive a bounded typed subgraph. README flowcharts remain stable explanations, not live architecture evidence.
- Reason: Without the source schema, building an adapter would fabricate a second graph contract. Keeping projection downstream of receipts preserves one evidence source and avoids a renderer or universal analyzer with no measured need.
- Rejected alternatives: a parallel Metroviz store, inferred routes/gates/collisions/dead ends, a renderer without a source contract, or putting dynamic project state into README diagrams.
- Verification: `BDW-P34` records the inaccessible source as an explicit coverage gap; no adapter or renderer is included.
- Boundary: This is a deferred visualization integration, not evidence that Metroviz currently covers Brainlehr projects.

## 2026-08-26 — Reuse a compatible agent by recommendation, never by transcript

- Context: Reusing a live Terra/Luna can avoid restating a compatible task, but the host alone owns agent lifecycle and Brainlehr's existing checkpoint deliberately excludes chat text.
- Decision: Extend the existing TTL checkpoint with technical role/capability, source revision, used node/lesson IDs, open gates and terminal state. A deterministic read path recommends `reuse_followup`, `refresh_delta`, or `fresh_agent`; it never spawns/reuses an agent itself. Same project/task/role/revision reuses a follow-up and loads only direct neighbours; a revision change loads its diff plus direct neighbours. Independent review always starts fresh.
- Reason: It reuses the established compact checkpoint instead of creating an agent memory store. The host receives a compressed final, not a child transcript, so token saving never becomes hidden-context retention.
- Rejected alternatives: store prompts/responses/hidden thinking, keep a permanent agent profile, ask Brainlehr to spawn agents, reuse an agent for an independent review, or wait for capacity instead of doing available work.
- Verification: `python3 -m pytest -q tests/test_session_checkpoint.py` (7 passed); incompatible role, saturation, topic/revision change and independence receive deterministic non-reuse recommendations.
- Boundary: This is a host recommendation, not an OpenAI product-lifecycle guarantee. The orchestration client must check whether a target is actually live and must not stall when reuse is unavailable.

## 2026-08-26 — Research before analyzer dependencies; keep one typed impact graph

- Context: The operator required a primary-source OSS check before heavier graph tooling, and one fresh visual path from the same revision-bound evidence.
- Decision: Keep the Python/AST analyzer as the sole default dependency. `project_change` now returns a deterministic typed graph and hash; Mermaid is a pure projection. Mermaid/Graphviz are presentation options; Semgrep is an optional local verifier. tree-sitter, SCIP and Kythe are adapter-later candidates; OpenTelemetry is adapter-later only for summarized runtime timing. Glean, Joern/CPG, Cytoscape and CodeQL CLI are rejected as defaults.
- Reason: The smallest present graph preserves provenance and local/offline operation. A new service/indexer needs a measured gap first. CodeQL's MIT query repository does not make its separately licensed CLI an unrestricted default dependency.
- Rejected alternatives: embed a Sourcegraph/Glean/Joern service, use semantic similarity as an edge, create a second visualization store, or add a Metroviz adapter without its source schema.
- Verification: Official sources: [SCIP](https://github.com/scip-code/scip) Apache-2.0, [Kythe](https://github.com/kythe/kythe) Apache-2.0, [Glean](https://github.com/facebookincubator/Glean) BSD, [Joern](https://github.com/joernio/joern) Apache-2.0, [Semgrep](https://github.com/semgrep/semgrep) LGPL-2.1, [tree-sitter](https://github.com/tree-sitter/tree-sitter) MIT, [OpenTelemetry Python](https://github.com/open-telemetry/opentelemetry-python) Apache-2.0, [Mermaid](https://github.com/mermaid-js/mermaid) MIT, [Graphviz](https://gitlab.com/graphviz/graphviz) EPL-1.0, [Cytoscape](https://github.com/cytoscape/cytoscape.js) MIT, and [CodeQL CLI terms](https://github.com/github/codeql-cli-binaries/blob/main/LICENSE.md). `python3 -m pytest -q tests/test_project_boundary.py tests/test_project_context.py` proves a stable graph hash and identical Mermaid projection.
- Boundary: This documents research and a minimal interchange seam, not a benchmark or a guarantee that any later adapter is suitable for every repository.

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
