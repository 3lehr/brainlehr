# AI handoff

## 2026-08-27T00:15:00+0200 — docs(requirements): verify P21 adapter boundary

- Files: `docs/REQUIREMENTS_BRAINLEHR.md`, `AI_HANDOFF.md`.
- Why: canonical P21 must point at the separate Hermes adapter evidence, not
  claim a core-package import or license boundary without a current test.
- Verified: Hermes commit `501a8c3`; detached adapter snapshot `python3 -m
  pytest -q tests/test_provider.py -m 'not braucht_brainlehr'` — `50 passed,
  2 deselected`, including AST no-core-import and host-path checks.
- Remaining risk: P21 is an adapter boundary only; P99–P104 are separate
  Brainlehr runtime gates.

## 2026-08-27T00:10:00+0200 — fix(package): enforce P20 source boundary

- Files: `tests/test_paketbau.py`, `docs/REQUIREMENTS_BRAINLEHR.md`, `AI_HANDOFF.md`.
- Why: the archive guard rejected its one intended policy document together
  with arbitrary documentation, masking P20's real no-data boundary.
- Verified: isolated build with hatchling plus `tests/test_paketbau.py`,
  socket-denied `kataloge()` and no-source `katalog_holen()` — `6 passed`.
  Wheel/sdist carry no DB or catalog data; only the explicit policy JSON is
  permitted below `docs/`.
- Remaining risk: P21 is verified in the separate Hermes adapter repository;
  P99–P104 remain unimplemented.

## 2026-08-26T23:35:00+0200 — fix(test): restore catalog decoder syntax

- Files: `tests/test_requirements_brainlehr.py`, `AI_HANDOFF.md`.
- Why: `e56c13d5` left eight P67–P70 dictionary fragments inside a test body,
  making a clean checkout unparseable. The decoder now owns the exact currently
  catalogued P67–P70, P74 and P99–P104 rows, accepts three-digit IDs and treats
  explicit `NOT IMPLEMENTED` as an open gate.
- Verified: detached staged snapshot `python3 -m py_compile
  tests/test_requirements_brainlehr.py` and `python3 -m pytest -q
  tests/test_requirements_brainlehr.py tests/test_code_retrieval_benchmark.py`
  → `12 passed`; `git diff --check` passed. No DB/MCP write or push.
- Remaining risk: this only restores catalog-decoder coverage; P99–P104 product
  implementation stays `NOT IMPLEMENTED; NOT RUN`.

## 2026-08-26T23:05:19+0200 — docs(requirements): record P99–P104 contract tranche

- Files: `tests/test_code_retrieval_benchmark.py`,
  `docs/REQUIREMENTS_BRAINLEHR.md`, `docs/PLAN_GESAMTBAU_2026-08-21.md`,
  `AI_HANDOFF.md`.
- Added stable IDs BDW-P99–BDW-P104. P99–P103 are MUSS; P104 is MUSS-NICHT;
  all are DECIDED while every product gate remains explicitly `NOT IMPLEMENTED`
  and `NOT RUN`.
- Semantics cover strict `NONE`/validated `brainlehr:link` AI comments with
  human-comment preservation, registry/anchor validation and lazy budgeted
  lineage, immutable local-digest Merkle-DAG joins, separated rationale/index/
  failure/responsibility lifecycle, and sealed leak-free BGE annotation versus
  CodeRank raw-rank-only RRF ablation. MUST-NOT covers freeform AI comments,
  invented IDs, self-proof, secrets and raw prompt/transcript leakage.
- Red proof before the contract correction: focused catalog test failed because
  its required row semantics were absent. Green proof: `python3 -m pytest -q
  tests/test_code_retrieval_benchmark.py` → `10 passed`; `git diff --check`
  passed. No DB/MCP write, staging, commit or push performed.
- AI-Assisted-By: ChatGPT Codex
- AI-Agent: /root/terra_release_orchestrator/luna_docs_contract_build

## 2026-08-26T22:30:00+0200 — docs(retrieval): defer CodeRank tranche

- P30/P31 bleiben mit bestehenden IDs kanonisch; der aktuelle BGE-M3 PASS-Baseline-Befund bleibt unverändert und behauptet keine CodeRank-Aktivierung.
- BGE-M3 bleibt Prosa/Wissen; CodeRank ist nur ein separater komplementärer Code-Spezialist. H0 ist kein Fusionsnutzen; H1 verlangt einzigartige relevante CodeRank-Treffer und rank-only Fusion besser als BGE-only und CodeRank-only auf einem versiegelten Code-Test.
- Die nächste Tranche muss Prosa-Routing/-Ranking BGE-identisch, getrennte Vektorräume, finite vorab deklarierte Dev-only gewichtete-RRF-/Router-Parameter, genau einen versiegelten Test, exakten Missing/Stale-Fallback, Full-Repo-Train/Dev/Test, Zeit/RAM, leave-one-repo-out, leak-freie DE/EN-Prosa-/Code-/Signatur-/Consumer-/Fehler-/Impact-/No-hit-Matrizen, Betriebs-/Index-/Security-/Staleness-/Leak-Gates und die Ablation `stripped`/`comments-only`/`combined` belegen.
- Kein Modell-Download, keine Aktivierung, kein Tuning und keine Änderung am aktuellen PASS-Baseline-Status in dieser Tranche.


## 2026-08-26T22:02:00+0200 — docs(requirements): verify P74 Hermes runtime

- Files: `docs/REQUIREMENTS_BRAINLEHR.md`, `AI_HANDOFF.md`.
- Why: P74 is now accepted on bounded real Hermes evidence: the host
  `MemoryManager`/Brainlehr seam gives primary foreground exactly one recall;
  cron, subagent, oneshot, background-review, unknown and empty context give
  zero writes, while empty/timeout/error stay visible and Built-in Memory stays
  separate.
- Verified: `/Volumes/daten/Begod2026/hermes-brainlehr/tests/test_provider.py`
  on Python 3.11.15, 3.12.13 and 3.13.3 — each `50 passed, 2 skipped`;
  `tests/test_hermes_real_boundary.py` passes against the host Hermes classes
  with fake transport. No secrets, prompts/transcripts/raw code or temporary
  product DB are persisted. Hermes restarted after `ebe2fe8b` (commit 21:53:11;
  host PID 92182 started 21:56:57, MCP child PID 92469 started 21:56:59).
- Boundary: stale Codex server/session PIDs were observed and left untouched;
  no UI/session process was killed. No source or untracked test is included.
- Next test: rerun P74 only after a future Hermes/provider or lifecycle change.
- AI-Assisted-By: ChatGPT Codex
- AI-Agent: /root/terra_release_orchestrator/luna_commit_p74_evidence


## 2026-08-26T21:25:39+0200 — docs(requirements): keep P42 planned until tracked

- Files: `docs/REQUIREMENTS_BRAINLEHR.md`, `AI_HANDOFF.md`.
- Why: the former P42 `PASS` was withdrawn because the real runner, regression test,
  and fixture are untracked. The manifest therefore keeps tree-sitter, SCIP, and
  Semgrep planned/non-callable; no code or untracked artifact is staged.
- Verified: direct P42 tools were exercised, but there is no tracked acceptance
  evidence, so the canonical product gate remains `NOT RUN`.
- Remaining risk: P42 cannot be accepted until the runner, test, and fixture are
  tracked and the full regression is rerun.
- Next test: stage only the verified tracked P42/docs hunk after that evidence exists.

## 2026-08-26T18:00:00+0200 — feat(evidence): run Joern locally and revoke leaked retrieval route

- Files: local-only Joern wrapper/fixture/adapter registration, leak-free multilingual query
  gate, disabled CodeRank router, hardened OTLP/Metroviz provenance checks, P31/P43/P62, ADR
  and invalidated-measurement notice.
- Why: Joern/CPG remained mandatory after Docker was unavailable; review then found target
  identifiers leaked into the frozen multilingual retrieval queries, invalidating activation.
- Decision: use Joern 4.0.612 only from `/Volumes/daten/brainlehr-tool-cache/joern`, not Git;
  normalize typed CPG edges without DOT `CODE` fields. The v2 leak-free rerun retains BGE-M3:
  CodeRank/RRF/router each lose at least one mandatory non-regression gate; no caller override
  selects CodeRank.
- Verified: installer SHA-256 `be5958d056483ff4a606469a290d3eb373b5c9bb24d410e11655007c51dc59d4`;
  ZIP SHA-256 `e3b9a90ee34fe8d5a1bc586687394d3d8b18cd261b61e2737bcb3412fe22f986`;
  CPG SHA-256 `e168b781211b2fa7209c95f2adcec60e113efcdb10513dd92c060486d4fe40a1`;
  focused command `python3 -m pytest -q tests/test_multilingual_fixtures.py
  tests/test_code_retrieval_benchmark.py tests/test_code_retrieval_router.py
  tests/test_project_boundary.py tests/test_evidence_adapters.py
  tests/test_requirements_brainlehr.py` → 42 passed; `git diff --check` → pass.
- Remaining risk: macOS sandbox-exec denies network but must permit JVM filesystem reads; the
  benchmark decision is measurement provenance, not a signed security attestation.
- Next test: run catalog/client/public partitions, generated maps, isolated commit, private-origin
  push and project receipt.

## 2026-08-26T17:00:00+0200 — feat(retrieval): validate seven languages and bind runtime projections

- Files: frozen multilingual fixtures/benchmark/tests, separate CodeRank metadata router,
  impact projection CLI/config/tests, P31/P43/P47/P62 catalog rows, ADR and measurement record.
- Why: P31 could not complete on a Python-only corpus; runtime-trace and Metroviz were still
  planned rather than callable revision-bound projections.
- Decision: the fixed router uses CodeRank only for explicit signature/code-consumer queries;
  prose and ambiguity remain BGE-M3. CodeRank and normal knowledge vectors remain separate,
  carry revision/tree/model metadata and reject stale records. OTLP spans must be sanitized and
  bound to graph revision/tree hash; Metroviz is a derived graph route only.
- Verified: seven native syntax checks; clean idle rerun reproduces all 28 accuracy matrices
  exactly (report hash in `messungen/code_retrieval_benchmark_2026-08-26.md`); focused suite
  currently reports 42 passed for fixture/benchmark/router/project-boundary/project-context.
- Remaining risk: Joern has no local executable; it is a coverage gap. The separate CodeRank
  runtime needs a local model/cache and remains a retrieval hint, never an impact edge.
- Next test: run catalog/client/public-context partitions, regenerate maps, make the isolated
  commit, push only the private origin branch, then record the append-only project receipt.

## 2026-08-26T16:35:00+0200 — docs(map): refresh generated maps and record an immutable plan-marker finding

- Files: `docs/karten/bestand.{md,json}`, `docs/karten/code-brainlehr.{md,json}`, `docs/ablauf_vermerke.json`, this handoff.
- Why: the push gate correctly found the generated maps stale after the evidence commits. It also found that `d93b4836` did not name its plan/ADR in its immutable message; the visible vermerk records the actual P31/P40–P62 catalog and ADR instead of rewriting the commit.
- Verified: `python3 melder/landkarten.py --code brainlehr hub`; `python3 melder/ablaufpflicht.py origin/brainlehr/b4-ausweis..HEAD` reports `Jeder Commit nennt Plan und Belegweg (2 geprüft).`
- Remaining risk: `melder/kartenstand.py --still` was not used as a completion claim after it exceeded the short-run budget; the pre-push hook remains the final authoritative map-currentness gate. The base commit independently reproduces the slow `tests/test_abrufwirkung.py` (six passed then no progress at `melder/abrufwirkung.py:124`) and the ADR-034 generated-file assertion failure.
- Next test: push through the unmodified private pre-push hook; fetch `origin/brainlehr/b4-ausweis` and compare heads.

## 2026-08-26T16:20:00+0200 — chore(context): retain native entry points after live adoption

- Files: `.brainlehr.json`, this handoff.
- Why: the live `project_ensure` after `d93b4836` discovered the two package entry points that must remain explicit project capabilities while preserving the registered runtime-trace evidence contract.
- Verified: `project_ensure` reports the current manifest/capsule at `d93b4836`; `python3 -m pytest -q tests/test_project_context.py`.
- Remaining risk: canonical test partitioning isolated two unrelated test-environment problems: `tests/test_abrufwirkung.py` was terminated after 60 seconds without progress in `melder/abrufwirkung.py:124` (six cases had passed), and `tests/test_adr034_verdrahtung.py::test_occurrences_grenzwert_2_3_4` fails because no expected generated instructions file is found. Neither path is changed by this commit.
- Next test: record the manifest commit as a separate append-only project receipt, then push only `origin/brainlehr/b4-ausweis`.

## 2026-08-26T16:00:00+0200 — feat(evidence): close bounded registry, offline projection, and language-scope gates

- Files: P31/P48 requirements, benchmark manifest/tests, session capability registry, analyzer registry/tests, impact CLI/projection tests, and this handoff.
- Why: The revision-bound evidence work must keep tool output and agent reuse outside the semantic knowledge path while making language coverage and host limitations visible.
- Decision: Python remains the only measured language goldset. TypeScript, Rust, Swift, Dart/Flutter, Java and Go are explicit required-core gaps; SQL/Shell/YAML/HCL are declarative fixtures and C/C++/C#/PHP/Kotlin/Ruby are extension gaps. The registry recommends only same-agent compatible follow-up or a delta; it cannot spawn and carries no transcript. Analyzer output is file-bounded and hash-only, with scrubbed environment and host-network isolation reported as a gap. Cytoscape artifacts copy a local asset beside the deterministic HTML.
- Verified: P31/P48/requirements `18 passed`; focused graph/adapter/boundary/client group `50 passed`; analyzer group `11 passed`; projection group `14 passed`; `git diff --check` passed at each focused gate. An explicit all-tracked test invocation was interrupted after 65 passed in 211.79 s when legacy `melder/abrufwirkung.py` showed no progress for >90 s; it is not evidence of a new failure. The untracked `korpora/` collection was intentionally excluded.
- Remaining risk: Joern needs an executable local runtime; host-network isolation is not enforced; non-Python retrieval tests are required gaps rather than a production result. These remain visible coverage gaps, not completed claims.
- Next test: refresh the live project capsule/receipt after the commit, regenerate the allowlisted public context against that revision, and run the repository push gates.

## 2026-08-26T14:40:00+0200 — wip(evidence): establish v2 graph and optional-channel seams

- Files: P40–P50 catalog rows, graph/adapters/registry/CodeQL policy, fixtures, Cytoscape projection test and ADR.
- Why: The project context is being widened into one revision-bound evidence graph before analyzer channels are allowed to influence code impact.
- Verified: focused graph/adapter/registry/CodeQL tests; local SCIP and Semgrep measurements are recorded in ADR.
- Remaining risk: this is an uncommitted vertical foundation. Real Joern/OTLP import-run and vendored Cytoscape asset/current export gates remain open; no push is permitted until P40–P50 gates are complete.

## 2026-08-26T14:15:00+0200 — feat(context): debounce transient overlays and generate thin client bootstraps

- Files: `kern/project_analysis_loop.py`, `kern/project_context.py`, P38–P39 requirements, policy/generator/public client templates, focused tests and ADR.
- Why: Current code work needs revision-bound context between edit and verification without making every edit a durable Brainlehr fact; the three supported clients need one small, reviewable contract instead of drifting large prompts.
- Decision: The in-memory loop coalesces completed edits, discards stale work, separates staged from working state and requests one post-commit receipt. The generated policy bundle is the only instruction source; recalled/code/tool text is data and the adapters merely map Claude/Hermes/Codex lifecycle differences.
- Verified: `python3 -m pytest -q tests/test_project_boundary.py tests/test_project_context.py tests/test_requirements_brainlehr.py tests/test_session_checkpoint.py tests/test_werkzeugrechte_durchsetzung.py`; `python3 melder/client_bootstrap.py --check`.
- Remaining risk: No daemon sees arbitrary editor events; timing/run evidence still requires a registered, verified tool. Hosted ChatGPT cannot accept a repository-controlled system prompt.
- Next test: run full focused export/capability/push gates, then after commit record the live project receipt and regenerate public facts from that committed source.

## 2026-08-26T13:30:00+0200 — feat(impact): one typed graph and host-only agent reuse recommendation

- Files: `kern/project_context.py`, impact CLI, `kern/session_checkpoint.py`, MCP/rights contracts, P35–P37, tests and ADR.
- Why: Code/mixed work now has one revision-bound graph for compact machine context and deterministic Mermaid projection; compatible live agents can be recommended for reuse without retaining a conversation.
- Decision: Graphs contain only typed evidence, revision and hash. Metroviz is planned until its source schema is available. Agent reuse is a host recommendation; independent reviews, stale roles/revisions and saturated contexts go fresh.
- Verified: `python3 -m pytest -q tests/test_session_checkpoint.py tests/test_project_boundary.py tests/test_project_context.py tests/test_requirements_brainlehr.py tests/test_werkzeugrechte_durchsetzung.py` (37 passed).
- Remaining risk: Runtime/timing remains a registered-evidence gap; no heavy OSS analyzer, Metroviz adapter or host agent lifecycle integration was added.
- Next test: after commit, refresh the live capsule/receipt and generate/export public descriptions against the committed source revision.

## 2026-08-26T13:00:00+0200 — feat(project-boundary): keep modality local and gate staged impact explicitly

- Files: `kern/project_context.py`, `kern/project_boundary_cli.py`, `tool/project_boundary.py`, `knowledge_mcp_server.py`, `kern/werkzeugrechte.py`, package metadata, `.brainlehr.json`, P32–P34 requirements, architecture decision, and focused tests.
- Why: A repository alone cannot identify user intent. Clients now receive a small, deterministic `knowledge|code|mixed|unknown` contract without retaining prompts, thinking, or a user profile; opt-in code projects can make a conscious, diff-bound acknowledgement before commit.
- Decision: Explicit mode wins; a non-empty staged tree is the only server-verified automatic code signal; then comes named operation, otherwise unknown. The acknowledgement is local, append-only and bound to base+staged-diff SHA-256; it does not replace the post-commit `project_change` receipt.
- Verified: `python3 -m pytest -q tests/test_project_boundary.py tests/test_project_context.py tests/test_requirements_brainlehr.py tests/test_werkzeugrechte_durchsetzung.py tests/test_public_context_export.py tests/test_selbstbeschreibung_update.py tests/test_paketbau.py` (34 passed, 1 skipped); `python3 -m py_compile kern/project_context.py kern/project_boundary_cli.py knowledge_mcp_server.py kern/werkzeugrechte.py tool/project_boundary.py`.
- Remaining risk: A local CLI/hook is not a security boundary; runtime/build/timing evidence remains a registered-tool gap. The supplied Metroviz source schema was inaccessible, so P34 registers only a planned projection and no renderer.
- Next test: after commit, refresh project capsule/receipt, self-description, public export and generated capability map; then run the complete push gates.

## 2026-08-26T12:15:00+0200 — test(code-retrieval): separate modality matrices

- Files: `tests/fixtures/code_retrieval_goldset.json`, `messungen/code_retrieval_benchmark.py`, P31 requirement/decision documentation, and focused tests.
- Why: The prior code-model screen measured only English prose→Python. Four frozen matrices now make language, query/document modality, negatives, model prefix and activation rule explicit; Python paths no longer enter candidate model text.
- Decision: No second channel. CodeRankEmbed only wins code/signature→Python; it loses both prose→Python matrices and the German Brainlehr-prose control, so it fails the declared all-code-win plus prose-nonregression threshold.
- Verified: focused tests (6 passed); local 52-case run at `/Volumes/daten/code-retrieval-matrices-2026-08-26.json`, with 12k-character chunks and batch size four.
- Remaining risk: The frozen corpus is a compact screening field, not a universal or production-retrieval quality claim.
- Next test: rerun all four unchanged matrices against any locally available licensed candidate before changing production retrieval.

## 2026-08-26T11:35:00+0200 — docs(map): refresh generated inventory

- Files: `docs/karten/bestand.{md,json}` and this handoff.
- Why: The pre-push freshness gate correctly found the generated inventory stale after the new project-context evidence. Regenerated from the committed source graph; no hand-maintained capability text changed.
- Verified: `python3 melder/landkarten.py --code brainlehr hub`; `python3 melder/kartenstand.py --still`; focused 38-test suite and all push gates pass.

## 2026-08-26T11:25:00+0200 — chore(project): complete declared local tools

- Files: `.brainlehr.json` and this handoff.
- Why: The live project adoption found the two installed entry points that the capsule had not declared. The existing planned runtime-evidence declaration remains unchanged.
- Verified: `project_ensure` discovers the two commands and retains the explicit planned runtime-trace boundary; focused 38-test suite, capability map, document gate, plan gate, and `git diff --check` pass.

## 2026-08-26T11:15:00+0200 — docs(guard): record immutable P30 plan-gate finding

- Files: `docs/ablauf_vermerke.json` and this handoff.
- Why: The verified P30 commit was already written without naming its plan/ADR, so `melder/ablaufpflicht.py` correctly reported the formal gap. History is not rewritten because its append-only receipt already exists.
- Decision: Keep the finding visible and answer it with the repository's append-only guard record; the exact P30 requirement and architecture decision remain in the commit diff.
- Verified: `python3 melder/ablaufpflicht.py origin/brainlehr/b4-ausweis..HEAD` reports the finding as noted; JSON parse and `git diff --check` pass.

## 2026-08-26T11:00:00+0200 — test(code-retrieval): retain only the measured baseline

- Files: `tests/fixtures/code_retrieval_goldset.json`, `messungen/code_retrieval_benchmark.py`, P30 requirements/decision documentation, and focused tests.
- Why: A second model is useful only if it beats the existing local channel on frozen repository code. The 10-positive/3-negative symbol goldset compares the same 181 candidates, records code truncation, and writes no vectors to the database.
- Verified: `python3 -m pytest -q tests/test_requirements_brainlehr.py tests/test_code_retrieval_benchmark.py` (5 passed). Local BGE-M3: Recall@1 0.80, MRR 0.8643, 27.266 s; local CodeRankEmbed: 0.60, 0.7007, 30.349 s. No second channel was activated.
- Remaining risk: This is a small repository-specific screening set, not a universal code-search claim. Add a candidate only after it wins the same frozen set and a broader measured set.
- Next test: rerun the benchmark unchanged when another locally licensable candidate becomes available.

## 2026-08-26T09:30:00+0200 — docs(public-context): record final hardened snapshot

- Files: `docs/public-knowledge/brainlehr-context.json`, `docs/karten/bestand.{md,json}`, `docs/ablauf_vermerke.json`, and this handoff.
- Why: The public snapshot was regenerated only after its allowlisted source commit `48b130ac` existed, so `source_git_commit` is reproducible; the changed public nodes also update the generated inventory map.
- Verified: the exporter returned `written` then `current`; `python3 melder/kartenstand.py --still` returned `demo: ok`.
- Guard record: `ec382fcb` predates its complete plan reference in its message; its explicit ADR/requirements evidence and immutable receipt are recorded in `docs/ablauf_vermerke.json` instead of rewriting history.
- Remaining risk: the public snapshot deliberately describes only static-analysis limits. Runtime, build and schema dependencies need separately registered analyzers.

## 2026-08-26T09:14:00+0200 — docs(requirements): refresh P23–P28 gate counts

- Files: `docs/REQUIREMENTS_BRAINLEHR.md` and this handoff.
- Why: P29 added boundary, relative-import, receipt-supersession and export-provenance checks; the canonical acceptance evidence must state the current focused-test counts.
- Verified: `python3 -m pytest -q tests/test_project_context.py tests/test_public_context_export.py tests/test_requirements_brainlehr.py` (17 passed).
- Next test: refresh the allowlisted public artifact only after this source commit exists, so its `source_git_commit` is reproducible.

## 2026-08-26T09:15:00+0200 — docs(public-context): regenerate hardened public evidence

- Files: `docs/public-knowledge/brainlehr-context.json`, `docs/karten/bestand.{md,json}`, and this handoff.
- Why: The hardened source commit refreshed the public architecture/workflow nodes and added its append-only project receipt; the public snapshot and generated knowledge map must therefore follow the verified local database state.
- Verified: `python3 melder/selbstbeschreibung.py --anlegen`; live `project_ensure` refreshed the capsule; `project_change` recorded `359c3280` with `coverage_gap`; exporter returned `written` then `current`; `python3 melder/landkarten.py --code brainlehr hub` regenerated the affected map.
- Remaining risk: `coverage_gap` is expected here because the implementation commit changes non-Python files; runtime/build/schema dependencies still require registered analyzers.
- Next test: run the focused suite and all push gates, then push only `origin/brainlehr/b4-ausweis`.

## 2026-08-26T09:00:00+0200 — feat(project-context): harden bounded evidence contracts

- Files: `kern/project_context.py`, `knowledge_mcp_server.py`, `pflege/export_public_context.py`, `melder/selbstbeschreibung.py`, P23–P29 requirements/decision docs, and focused tests.
- Why: The reviewed context workflow needed honest static-analysis coverage, immutable correction history, relative-import evidence, and repository-bound public export inputs before any larger analyzer work.
- Verified: `python3 -m pytest -q tests/test_project_context.py tests/test_public_context_export.py tests/test_requirements_brainlehr.py` — 17 passed before the full gate run.
- Remaining risk: Static imports still do not prove runtime data flow; pattern screening is deliberately not a PII/secret guarantee.
- Next test: run the full focused gate, refresh the live capsule/change receipt, regenerate the allowlisted public artifact, and push only the private branch.

## 2026-08-25T22:00:00+0200 — docs(public-context): refresh provenance after acceptance evidence

- Files: `docs/public-knowledge/brainlehr-context.json` and this handoff.
- Why: `docs/AI_DECISIONS.md` and the canonical requirements are declared sources of the public architecture/workflow nodes. After their PASS evidence changed, the two affected nodes were refreshed before exporting so the committed snapshot remains non-stale at its own revision.
- Verified: refreshed `/brainlehr/faehigkeiten/public-architecture` and `/brainlehr/faehigkeiten/public-workflow`; exporter returned `written` then `current`; `python3 melder/kartenstand.py --still` passed.
- Remaining risk: Any later allowlisted source change intentionally rejects export until its generated node is refreshed; this is the declared release gate.
- Next test: alter a declared source in a fixture and prove export rejects without overwriting the last valid artifact.

## 2026-08-25T21:45:00+0200 — chore(push): refresh generated guards for the private catch-up branch

- Files: `docs/karten/`, `docs/ablauf_vermerke.json`, and this handoff.
- Why: The private branch is 143 commits ahead of `origin`; the required pre-push guards found generated maps stale and historical commits whose immutable messages predate the plan/evidence marker rule. The visible per-commit records answer those findings without rewriting history or bypassing a guard.
- Verified: `python3 melder/landkarten.py --code brainlehr hub`; `python3 melder/kartenstand.py --still`; `python3 melder/dokumentzugang.py --still`; `python3 melder/ablaufpflicht.py origin/brainlehr/b4-ausweis..HEAD`.
- Remaining risk: The five document-reference nodes used to clear document access are live local knowledge only, as intended; neither the database nor their source metadata is committed.
- Next test: push the guarded branch and retain the hook output as the final remote verification.

## 2026-08-25T21:30:00+0200 — docs(public-context): publish the verified safe slice

- Files: `docs/public-knowledge/brainlehr-context.json`, `docs/REQUIREMENTS_BRAINLEHR.md`, `docs/AI_DECISIONS.md`, and this handoff.
- Why: The public repository needs a reviewable, deterministic snapshot of exactly the allowlisted public Brainlehr descriptions, not the SQLite database.
- Verified: `python3 melder/selbstbeschreibung.py --anlegen` refreshed 14 generated nodes; two exporter runs against `brainlehr.db` returned `written` then `current` for three allowlisted nodes. The focused automated suite remains 24 passed.
- Remaining risk: Any source change makes the export intentionally stale until the generator and exporter are rerun; this is a release gate, not an automatic publication path.
- Next test: change an allowlisted source in a test fixture, prove rejection leaves this artifact untouched, then regenerate after the node update.

## 2026-08-25T21:25:00+0200 — fix(public-context): refresh existing generated nodes

- Files: `melder/selbstbeschreibung.py`, `tests/test_selbstbeschreibung_update.py`, and this handoff.
- Why: The public export correctly rejected stale nodes, but the generator counted a duplicate-path response as an update without calling `knowledge_update`; an existing generated description could therefore remain stale forever.
- Verified: `python3 -m pytest -q tests/test_selbstbeschreibung_update.py tests/test_public_context_export.py tests/test_project_context.py tests/test_requirements_brainlehr.py tests/test_werkzeugrechte_durchsetzung.py` — 24 passed; `python3 -m py_compile melder/selbstbeschreibung.py pflege/export_public_context.py kern/project_context.py knowledge_mcp_server.py`; `python3 tool/faehigkeitskarte.py --pruefen`; `git diff --check`.
- Remaining risk: The generated public artifact still needs a post-commit generator run, then the exporter validates source freshness before it writes.
- Next test: run `python3 melder/selbstbeschreibung.py --anlegen`, export the allowlisted artifact, and prove the second export is byte-identical.

## 2026-08-25T21:15:00+0200 — feat(public-context): export an allowlisted DB handoff

- Files: `pflege/export_public_context.py`, `melder/selbstbeschreibung.py`, `docs/public-knowledge/brainlehr-nodes.json`, `tests/test_public_context_export.py`, the canonical requirements, architecture decisions, capability map, and this handoff.
- Why: Public release documentation must be reproducible from verified public DB nodes without exposing the database, local provenance, sessions, operator instructions, or unrelated released material.
- Verified: `python3 -m pytest -q tests/test_public_context_export.py` — 3 passed; live `python3 melder/selbstbeschreibung.py --anlegen` created and released the two allowlisted architecture/workflow nodes.
- Remaining risk: The first generated JSON artifact must be produced against the committed source revision; the exporter rejects a stale one rather than updating it silently.
- Next test: after the implementation commit, regenerate `docs/public-knowledge/brainlehr-context.json` and verify a second run is byte-identical.

## 2026-08-25T21:00:33+0200 — feat(project-context): retain versioned impact evidence

- Files: `kern/project_context.py`, `knowledge_mcp_server.py`, `kern/werkzeugrechte.py`, `pyproject.toml`, `tests/test_project_context.py`, `tests/test_requirements_brainlehr.py`, `docs/REQUIREMENTS_BRAINLEHR.md`, `docs/AI_DECISIONS.md`, `docs/WAS_BRAINLEHR_KANN.md`, `.brainlehr.json`, and this handoff.
- Why: A fresh coding context must discover only task-relevant verified project context, and every verified change must make direct and indirect consumers visible without pretending that imports or vector proximity prove runtime data flow.
- Verified: `python3 -m pytest -q tests/test_project_context.py tests/test_requirements_brainlehr.py tests/test_werkzeugrechte_durchsetzung.py` — 20 passed; `python3 -m py_compile kern/project_context.py knowledge_mcp_server.py`; `python3 tool/faehigkeitskarte.py --pruefen`.
- Remaining risk: Only Python static-import edges are presently analyzed. Non-Python, call, schema, trace and I/O contracts remain explicit `coverage_gap`s until a project registers a verified analyzer.
- Next test: Register a project-specific trace or schema analyzer with an evidence artifact, then prove its typed edge joins the same bounded impact traversal without becoming a raw-code index.

## 2026-08-24 — test(ort): align legacy-DB warning test

- Change: no warning for a fresh directory; warn only after an actual
  `knowledge.db` fallback. This matches `haken/ort.py` and preserves the
  migration signal without confusing first boot.
- Verified: `python3 -m pytest -q tests/test_ort_env_kompat.py` (7 passed).
- Remaining: public release `c578eda9` has the runtime behavior, but this
  private test correction still needs normal release propagation.

## 2026-08-18T05:00:00+0200 — feat(vertrag): four INT gates green

- Commits: `cdef550b` (INT-VER-001), `2ea89fe6` (INT-UPD-001, INT-DNST-001) und
  im Nachbarrepo `openlehr_einzelunternehmer` `cc750e3` (Paketversion +
  INT-GATE-001). Kein Push.
- Stand der Gates: `INT-VER-001`, `INT-UPD-001`, `INT-DNST-001`, `INT-GATE-001`
  grün. Offen und als `xfail(strict=True)` sichtbar: `INT-UPD-002`
  (Importkennung und Rücknahme). Ungebaut und nur als Katalogzeile:
  `INT-REG-001` (Domänenregistry), `INT-SNAP-001` (Snapshotgrenze),
  `INT-API-001/002` und `INT-VER-002` haben noch kein eigenes Laufzeitgate.
- Format: `contract_version` ist Pflichtschlüssel, `_VERTRAG_VERSION = 1`,
  unbekannte Major fail-closed. Beide realen Pakete tragen die `1`.
- Zwei Funde, die kein Plan genannt hatte: `exportiere()` erzeugte ein Paket,
  das der eigene Prüfer abgewiesen hätte; und das Atelier hätte einen reinen
  Aktualisierungs-Import als „enthielt nichts Neues“ gemeldet. Beides behoben,
  Letzteres als reine Funktion `DomaeneImportUebersetzung.wirkung` in
  BrainlehrCore, damit es prüfbar ist statt im Bildschirmpfad zu liegen.
- Verified: `94 passed, 1 xfailed` (Domäne, Vertrag, Rechte, Schichtregel),
  `swift test` 241 passed (vorher 240), openlehr 21 passed. Rot-Probe für
  INT-GATE-001 gefahren: `BRAINLEHR_PFAD=/tmp/gibtsnicht` → 1 failed statt
  1 skipped. `tests/test_alle_selftests.py` bleibt ausgenommen — fremde,
  bereits vorher rote Arbeitskopie im Arbeitsbereich.
- Remaining risk: Der Reimport aktualisiert, nimmt aber nichts zurück. Ein
  falsch importiertes Paket ist heute nur von Hand aus dem Bestand zu
  schneiden, und niemand weiß danach, was dazugehörte.
- Next test: `INT-UPD-002` — Importkennung auf jeder geschriebenen Zeile,
  `nimm_import_zurueck(kennung)` entfernt genau diesen Import und lässt in
  Kraft gesetzte Regeln stehen (oder verweigert, solange eine gilt).

## 2026-08-18T05:20:00+0200 — test(vertrag): pin BDW-F07 interface gates red

- Files: `docs/REQUIREMENTS_INTERFACE_KOMPAT.md` (neu), `docs/REQUIREMENTS_BRAINLEHR.md`,
  `tests/test_interface_kompat_katalog.py` (neu), `tests/test_requirements_brainlehr.py`.
  Kein Produktcode, kein fremder Dirty-Pfad, kein Push. Commit `82665929`.
- Why: Der Interface-/Compatibility-Katalog aus der Übergabe existiert jetzt als
  genau ein untergeordneter Teilkatalog zu `BDW-F07` — zehn `INT-*`-IDs mit
  Producer/Consumer-Matrix, `contract_version` v1, Kompatibilitätsmatrix,
  additiv/brechend, Update/Migration/Rollback, Dienst-Lifecycle, Snapshotgrenze
  und nicht-skippendem Cross-Repo-Gate. Wissensknoten `7733f71b`.
- Red: Vier `xfail(strict=True)`-Gates halten die gemessenen Lücken fest —
  `INT-VER-001` (kein `contract_version` in `kern/domaene._PFLICHTSCHLUESSEL`),
  `INT-UPD-001` (`INSERT OR IGNORE`), `INT-DNST-001` (`dienst` geprüft, nie
  persistiert), `INT-GATE-001` (`pytest.skip` im OpenLehr-Gegentest).
- Verified: `python3 -m pytest -q` über die Reproduktionsmenge der Übergabe plus
  die neuen Gates — vorher 80 passed, danach 81 passed, 4 xfailed.
  Beinahefehler: Die erste Fassung von `INT-VER-001` war XPASS(strict), weil das
  Probepaket schon an der Regelform scheiterte; korrigiert, seither echtes Rot.
- Remaining risk: Die Lücken 1–9 der vorigen Übergabe bleiben offen; dieser
  Commit misst sie, er behebt keine. Swift- und OpenLehr-Suiten wurden nicht neu
  gefahren, weil ihr Code unberührt blieb.
- Next test: `INT-VER-001` grün machen — `contract_version` als Pflichtschlüssel
  in `kern/domaene.py`, unbekannte Major fail-closed, beide realen Pakete
  (`pakete/steuer.domaene.json`, `openlehr_einzelunternehmer/wissen/…`) auf `1`.

## 2026-08-18 — Claude: kanonischer Produktstand und nächste Integrationsnaht

### Ziel und belastbarer Stand

- Einzige normative Produktquelle ist `docs/REQUIREMENTS_BRAINLEHR.md`: 53
  eindeutige `BDW-*`-IDs. Zielbild A ist ein governierter Local-first-Kern;
  Enterprise ist ein Profil desselben Kerns, Föderation folgt später.
- `DECIDED` bezeichnet nur den Katalogstatus. Alle Produktgates stehen weiterhin
  auf `NOT RUN`; aus dem Katalog folgt keine Implementierungsabnahme.
- Relevante Historie: `0ff92e5b` (ehrliche Relevanzlage), `4460ce22`
  (stale Module/Reload und kanonische MCP-Konfiguration), `64667778` +
  `494a57f3` (Research-Katalog und Zielbild-Research), `7fcce636`
  (kanonischer Root-Lastenkatalog).
- Codex konfiguriert nur noch den kanonischen MCP-Namen `brainlehr` über
  `/Volumes/daten/Begod2026/brainlehr/knowledge_mcp_server.py`. Bereits laufende
  Tasks können weiterhin alte importierte Module oder alte Prozessgenerationen
  verwenden und müssen einzeln neu gestartet werden. Kein globaler Prozess-Kill.

### Heute belegte Brainlehr–Atelier–OpenLehr-Naht

- Rollenmodell: Brainlehr trägt Geltung, Beleg und Governance; `openlehr_X`
  liefert Fachwissen und Fachwerkzeuge; Atelier trägt gemeinsame Darstellung,
  Einstellungen und unabtretbare Sicherheitsgrenzen.
- Atelier ist kein separates Repo, sondern die Swift-App unter `app/` in diesem
  Brainlehr-Repo.
- Reale Strecke:

  ```text
  openlehr_X/wissen/*.domaene.json
    -> kern.domaene.pruefe
    -> POST /api/domaene-import
    -> Speicherung mit Wirkung Null
    -> GET /api/domaene-oberflaeche
    -> Atelier zeichnet die plattformblinde Beschreibung nativ
  ```

- Fokussierter Integrationslauf vom 2026-08-17: Brainlehr 78 + OpenLehr 21 +
  Atelier 240 = **339 PASS, 0 FAIL**.

### Kritische Lücken — nicht als gebaut behandeln

1. Es gibt keinen versionierten repoübergreifenden Vertrag.
2. `contract_version` und Compatibility-Matrix fehlen.
3. Reimport nutzt `INSERT OR IGNORE`; gleiche IDs werden nicht aktualisiert.
4. `dienst` ist Pflicht und wird validiert, aber weder persistiert noch gestartet.
5. Eine allgemeine Domänenregistry fehlt; Atelier ist noch auf
   `einzelunternehmer` festgelegt.
6. `faehigkeiten` ist in ADR-011 geplant, aber nicht im realen Domänenmanifest.
7. Der OpenLehr→Brainlehr-Vertragstest darf bei fehlendem Brainlehr-Pfad skippen.
8. Snapshot-Ziel `cb24f119` ist nicht normativ und nicht implementiert; die
   aktuelle Suche liest bei jedem Aufruf die gegenwärtige DB.
9. Der Root-Lastenkatalog ist kein Interfacevertrag und reicht allein nicht aus.

### Nächste sichere Aktion

1. Zuerst `docs/REQUIREMENTS_BRAINLEHR.md`, ADR-007, ADR-011, ADR-012,
   ADR-013, ADR-014, ADR-024 und den OpenLehr-Vertrag
   `/Volumes/daten/Begod2026/openlehr_einzelunternehmer/docs/openlehr/OPENLEHR_KERNEL_UND_APP_VERTRAG_V1.md`
   lesen. Alte `STAND`-/`PLAN`-Dateien sind Evidenz, nicht kanonische Quelle.
2. Unterhalb von `BDW-F07` genau einen Interface-/Compatibility-Katalog anlegen;
   keinen zweiten Root-Lastenkatalog. Er braucht stabile Interface-IDs,
   Producer/Consumer-Matrix, `contract_version` v1, Regeln für additive und
   brechende Änderungen, Update/Migration/Rollback, Dienst-/Capability-Lifecycle,
   Snapshotgrenze und verpflichtende nicht-skippende Cross-Repo-Gates.
3. Nur wirklich offene Entscheidungen an den Betreiber geben; die 53 bereits
   entschiedenen BDW-Auswahlen nicht erneut erfragen. Vor Produktcode zuerst rote
   Vertragstests schreiben.

Erste Reproduktion:

```sh
cd /Volumes/daten/Begod2026/brainlehr
python3 -m pytest -q tests/test_domaene.py tests/test_domaene_dienst_oberflaeche.py tests/test_domaene_oberflaeche_reist.py tests/test_entscheidungen_server_domaene_import.py tests/test_bestandteile.py tests/test_app_schichtregel.py tests/test_werkzeugrechte_durchsetzung.py

cd /Volumes/daten/Begod2026/openlehr_einzelunternehmer
.venv/bin/python -m pytest -q apps/openlehr/tests/test_skill_manifest.py apps/openlehr/tests/test_view_types_manifest_sync.py dienst/tests/test_euer_vorschlag.py

cd /Volumes/daten/Begod2026/brainlehr/app
/usr/bin/xcrun swift test --quiet
```

### Arbeitsbaum, Checkpoint und Referenzen

- Der Arbeitsbaum war vor dieser Übergabe bereits fremd verschmutzt:
  `NODE_INDEX.md`, `antwort_treffer.json`, `auszug/bestand_2026-08-10.jsonl`,
  `bereinigung_log.jsonl`, `runs/messlauf_abrufguete_v2.json`,
  `spikes/univer_i3_min/probe4/{bundle.js,ergebnis.json}` und
  `tests/test_alle_selftests.py` sowie vorhandene ungetrackte Lauf-, PDF-, Log-
  und `node_modules`-Artefakte. Nicht bereinigen, nicht stagen.
- Exakte Commitgrenze dieser Übergabe: ausschließlich `AI_HANDOFF.md`; keine
  Produktdatei, kein fremder Dirty-Pfad, kein Push.
- Temporärer technischer Checkpoint:
  `codex-brainlehr-20260818-claude-handoff`, Ablauf
  `2026-08-19T02:32:44.288933Z` (24 h). Aktive Anforderung `BDW-F07`, offener
  Evidenzbezug `cb24f119`, nächste Aktion `CREATE-INTERFACE-COMPAT-CATALOG`.
- Brainlehr-Referenzen: `868ea08e` kanonischer Root, `34ddffa9` Katalogtest,
  `cd571222` Lastenkatalog-Regel, `cb24f119` Snapshot-Ziel, `L-53f886`
  Relevanz/Reload, `L-da2ebc` Decoder-Beinahefehler.

### Commit-Metadaten

- Subject: `docs(handoff): brief Claude on integration boundary`
- Files: ausschließlich `AI_HANDOFF.md`.
- Why: Claude braucht einen kurzen, belegten Einstieg vom kanonischen Produktziel
  bis zur nächsten roten repoübergreifenden Vertragsprobe.
- Verified: Pfade und Commits vorhanden; Markdown-Struktur geprüft;
  `git diff --check`; staged Numstat vor Commit.
- Remaining risk: Die neun Integrationslücken oben bleiben offen; insbesondere
  erzwingt noch kein Gate Versionskompatibilität oder Snapshot-Isolation.
- Next test: Ein v1-Domänenpaket muss in einem nicht-skippenden Cross-Repo-Test
  gegen genau einen gemeinsamen Vertrag bestehen; unbekannte Major-Version rot.

## 2026-08-17 — test(prompt): add invariance gates

- Files: prompt core, public agent templates, requirements catalog and focused tests.
- Verified: focused pytest gates.

## 2026-08-17 — fix(orchestrator): require completion gates

- Files: `docs/AI_DECISIONS.md`, this handoff; global `~/.codex/AGENTS.md`.
- Why: require a single ID-based catalog and visible conflict gates for complex artifacts.
- Verified: exact global-text assertions and `git diff --check`.
- Next test: use one catalog ID in an implementation, test, and acceptance gate.

## 2026-08-17T17:13:07+02:00 — fix(orchestrator): require completion gates

- Files: `docs/AI_DECISIONS.md`, this handoff; additionally the non-repository `~/.codex/AGENTS.md`.
- Why: background child finals were available before the next parent turn, but were integrated only after a user status prompt. Brainlehr cannot wake an idle Codex turn, and an escalated readability lesson was not automatically present in Codex governance.
- Verified: primary thread timing showed child completion 592/844 seconds before the user-triggered parent turn; exact assertions confirm the global completion and human-readable artifact gates; the receiving task read Brainlehr node `38f0ca59` and acknowledged the handoff.
- Remaining risk: a behavioral instruction is not a host callback. The Codex orchestrator still needs an idempotent last-child-terminal → parent-continuation gate for a mechanical guarantee.
- Next test: spawn three synthetic children with staggered finals and no user input; require exactly one parent continuation containing all finals, one PASS/FAIL decision, and the next authorized action.

## 2026-08-17T13:47:39+02:00 — feat(ui): link Brainlehr references locally

- Files: `berichte/entscheidungen_server.py`, `tests/test_eintrag_detailseite.py`, this handoff.
- Why: Codex does not render Markdown or HTML hover titles, but normal links open the browser. The existing loopback-only Brainlehr service now resolves `/eintrag/<kennung>` for knowledge nodes and lessons without adding a public data surface.
- Verified: `python3 -m pytest -q tests/test_eintrag_detailseite.py tests/test_entscheidungen_server_herkunft.py tests/test_entscheidungen_server_ausweis.py` → 19 passed; production DB rendering for `L-186d02` and `922d64e9` succeeded; restarted `de.brainlehr.dienst`; live GET returned 200 and a forged Host returned 403.
- Remaining risk: Links work only on the machine running the loopback service. The OpenAI Secure MCP Tunnel remains separate and still needs the operator-owned runtime credential before any authenticated remote detail view can exist.
- Next test: click `http://127.0.0.1:8799/eintrag/L-186d02` from Codex and confirm Chrome displays the lesson.

## 2026-08-17T13:26:46+02:00 — feat(mcp): gate prompt-invariance profile

- Files: `kern/prompt_invarianz.py`, `knowledge_mcp_server.py`, `kern/werkzeugrechte.py`, focused tests, `docs/AI_DECISIONS.md`, this handoff.
- Why: Claude keeps the complete default MCP, while ChatGPT Secure MCP Tunnel and Hermes can expose exactly two provider-neutral prompt-invariance tools. The profile is enforced at `tools/call`, not merely hidden from `tools/list`.
- Verified: focused pytest set → 17 passed; `kern/werkzeugrechte.py --selftest` green; real stdio probe listed/called both prompt tools and rejected `knowledge_search` with `profil:prompt-invariance`; Python compile green.
- Remaining risk: The OpenAI-hosted endpoint still requires the operator's Platform login, `tunnel_id`, Runtime-API-Key and ChatGPT Developer Mode. No secret was read or stored.
- Next test: run `tunnel-client doctor`, confirm managed runtime is healthy/ready, then list and call exactly the two tools from ChatGPT.

## 2026-08-16T21:20:06+02:00 — fix(mcp): expose operator instruction contract

- Files: `knowledge_mcp_server.py`, `tests/test_weisungszitat_beleg.py`, `AI_HANDOFF.md`.
- Why: `knowledge_add()` and `knowledge_update()` accepted `betreiber_weisung`, but the public `TOOLS` schemas omitted it and both MCP handlers discarded it. No client restart could expose or use the field.
- Red: `python3 -m pytest -q tests/test_weisungszitat_beleg.py::test_mcp_vertrag_reicht_betreiber_weisung_an_beide_werkzeuge` — 1 failed because the property was absent.
- Verified: `python3 -m pytest -q tests/test_weisungszitat_beleg.py tests/test_version.py tests/test_project_id_enum_stale.py` — 25 passed; a fresh `handle_request(tools/list)` reports `betreiber_weisung` for both tools and the test proves both handlers forward it.
- Remaining risk: Already-running MCP processes keep their imported `TOOLS` table; clients need one more restart to load this server change. The missing `begod/knowledge/` tree prevented the BeGood JSON sync path, so the reusable finding is recorded as Brainlehr lesson `L-9d668e` instead.
- Next test: Restart Codex and inspect the actually loaded `knowledge_add` and `knowledge_update` tool metadata for `betreiber_weisung`.

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
# 2026-08-17 — public Claude/Hermes prompt templates

- Change: added `auszug-offen/prompts/CLAUDE.md` and `HERMES.md` with one shared
  prompt contract plus client-specific anchors; added a drift/leak regression
  test in `tests/test_public_prompt_templates.py`.
- Why: the public export needs reusable client templates without copying local
  paths or credentials, while shared instructions must remain invariant.
- Verified: `python3 -m pytest -q -p no:cacheprovider tests/test_public_prompt_templates.py`
  — 2 passed.
- Remaining risk: the templates are intentionally short and do not replace the
  full client documentation.
- Next test: run the public-export test subset before publishing an export.
# 2026-08-17 — feat(mcp): persist session checkpoints

- Files: `schema.sql`, `kern/session_checkpoint.py`, `knowledge_mcp_server.py`, `tests/test_session_checkpoint.py`
- Why: preserve a compact, ordered resume point without misclassifying in-progress work as durable knowledge.
- Verified: `python3 -m pytest -q tests/test_session_checkpoint.py` — 2 passed.
- Remaining risk: existing long-running MCP processes need restart to advertise the new tools.
- Next test: invoke both checkpoint tools through a fresh MCP process.

# 2026-08-17T20:07:46+02:00 — fix(session): make checkpoints temporary and typed

- Files: `schema.sql`, `kern/session_checkpoint.py`, `kern/werkzeugrechte.py`, `knowledge_mcp_server.py`, `haken/kontextstand.py`, `tests/test_session_checkpoint.py`, `docs/REQUIREMENTS_SESSION_CHECKPOINT.md`, `docs/AI_DECISIONS.md`, `README.md`, three public agent templates, and this handoff.
- Why: the preceding append-only free-text checkpoint contradicted the approved privacy and token boundary. The replacement stores one TTL-limited technical row and returns a deterministic save/integrate/rollover recommendation.
- Verified: focused checkpoint, MCP-rights, and agent-template suite — 19 passed; fresh JSON-RPC set/reject path passed; installed schema and all 57 trigger SQL definitions were read from `sqlite_master`.
- Remaining risk: already-running MCP processes must restart before their advertised tool list includes `session_checkpoint_setzen`, `session_checkpoint_lesen`, and `session_checkpoint_schliessen`. Brainlehr recommends but cannot itself open a new host thread.
- Known unrelated failure: the wider schema subset has one pre-existing `kanalguete_messung.py:rowid` assertion failure in `tests/test_erstinstallation_spalten.py`; 98 other tests passed.
- Next test: after MCP restart, call the three tools from Claude, Codex/ChatGPT, and Hermes and compare their recommendation payloads.

# 2026-08-17T21:06:50+02:00 — fix(search): stop claiming an empty knowledge base

- Files: `docs/PLAN_KANALGUETE_2026-08-15.md`, `kern/relevanzlage.py`, `tests/test_relevanzlage.py`, and this handoff.
- Why: the visible result is fused from FTS, nodes, and lessons, but `bestandslage` receives only node-embedding scores. The Q2 operator case returned the relevant `cd571222` at FTS rank 1 while claiming `nichts_passendes`; the classifier now reports the honest `uneindeutig` boundary without mixing uncalibrated BM25 and cosine values.
- Verified: the MUST-LAGE-001 regression was red first; focused search/scope/channel suite — 54 passed; `python3 kern/relevanzlage.py` — `demo: ok`; direct Q1/Q2/Q3 path retained the same scores and top IDs while Q2 changed to `uneindeutig`.
- Remaining risk: already-running MCP processes may keep the old imported Python module until restart. `schwach` remains the existing calibrated intermediate label and was not redefined.
- Next test: restart the Brainlehr MCP server and repeat Q2 through the external MCP boundary; then rerun the 40/40 calibration before any future score or threshold change.

# 2026-08-17T21:30:00+02:00 — fix(mcp): detect stale imported relevance code

- Files: `haken/mcp_veraltet.py`, `tests/test_mcp_veraltet_laufzeitmodule.py`, `docs/PLAN_KANALGUETE_2026-08-15.md`, and this handoff; additionally the non-repository `~/.codex/config.toml` (backup beside it).
- Why: two Codex registrations of the same stdio server held different process generations. In one task the documented `brainlehr` alias still returned `nichts_passendes`, while the legacy `knowledge` alias and a fresh process returned `uneindeutig` for the same Q2 results and scores. The stale-process hook watched only the wrapper mtime and therefore missed the later change to imported `kern/relevanzlage.py`.
- Red: `python3 -m pytest -q tests/test_mcp_veraltet_laufzeitmodule.py` failed because no runtime-file set or latest-runtime-mtime boundary existed.
- Verified: focused relevance/hook/version suite — 12 passed; Python compile and `git diff --check` passed; the exact fresh stdio command from the parseable Codex TOML returned `uneindeutig` in both `brainlehr` and `buckeberg`; `codex mcp list` now contains exactly the README-canonical `brainlehr` registration for this server.
- Remaining risk: already-running task processes retain both their old code and the removed alias until that task/client is restarted. There is no local `codex mcp reload/restart` command; no global process kill was attempted. The hook is a Claude `UserPromptSubmit` integration, not a Codex hot-reload mechanism.
- Next test: restart one affected Codex task/client and call Q2 through `mcp__brainlehr__knowledge_search`; require `uneindeutig`, then repeat the client-specific restart gate for Claude and Hermes without touching unrelated owners.

# 2026-08-17T21:40:00+02:00 — docs(research): establish one target-picture catalog

- Files: `docs/RESEARCH_ZIELBILD_2026-08-17.md` and this handoff.
- Why: product genealogy, 2025/2026 memory research, enterprise security, product boundaries, gap analysis, target alternatives, and the decision wizard need one stable evidence map before any new synthesis or UI question is produced.
- Verified: the catalog contains one contiguous `RQ-001`–`RQ-018` scale, explicit source/status rules, and gates for all requested research and wizard deliverables; `git diff --check` passed.
- Remaining risk: all RQ rows begin open by design. They are research identifiers, not binding product requirements and must later be transferred rather than copied into a second requirements scale.
- Next test: populate each RQ with primary evidence, then reject any wizard question lacking an RQ or binding internal source.

# 2026-08-17T21:55:00+02:00 — docs(research): complete Brainlehr target-picture evidence

- Files: `docs/RESEARCH_ZIELBILD_2026-08-17.md` and this handoff. The derived interactive wizard is an external conversation artifact under `/Users/lehrmacbook/.codex/visualizations/2026/08/17/01a010f0-d6a0-73c0-a545-bea4fc2f1316/` and is intentionally not committed.
- Why: the product purpose was distributed across accepted ADRs, missing ADR references, implementation, plans and untrusted recall. Current agent-memory research and enterprise controls also needed to become explicit evidence before asking the operator to decide a root Lastenkatalog.
- Verified: all `RQ-001`–`RQ-018` gates pass; primary-source URLs and the local BSI Grundschutz++ commit/control IDs are recorded; the Wizard contains 53 unique questions in six categories, no preselection, one inline data source and no network access. `node --check`, responsive browser checks at 736 × 900 and 360 × 900, native keyboard interaction, persistence and summary counters passed. Focused relevance/deployment suite: 25 passed. The known vector-inventory gate remains 1 failed, 3 passed because one node and one lesson have no vector.
- Decision: recommend target picture A, a layered governed local-first memory core, while keeping B as a separately gated enterprise profile and C as research until convergence/revocation/rights tests pass. ADR-025/026 are absent and therefore are not treated as accepted primary decisions.
- Remaining risk: this research does not bind a product scope. The operator must choose among the stable `BDW-*` options; selected results then move into one future root Lastenkatalog without copying the `RQ-*` scale.
- Next test: use the Wizard once, create the root Lastenkatalog from the returned ID/value set, and close the two-vector inventory defect separately.

# 2026-08-17T22:08:09+02:00 — docs(requirements): establish one Brainlehr root catalog

- Files: `docs/REQUIREMENTS_BRAINLEHR.md`, the two subordinate `docs/REQUIREMENTS_*.md` catalogs, `tests/test_requirements_brainlehr.py`, `docs/AI_DECISIONS.md`, and this handoff.
- Why: the operator completed all 53 Wizard choices. The product needed one normative, self-contained catalog that decodes those exact values without making Research, plans or local test IDs compete as a second source of truth.
- Red: `python3 -m pytest -q tests/test_requirements_brainlehr.py` — 2 failed because the Root did not exist.
- Verified: the same command — 2 passed. It checks 53 unique `BDW-*` IDs, the exact supplied key and decoded option text, allowed norm/status, deterministic `AC1`, conservative `NOT RUN`, overview text and both subordinate links. `BDW-E17=later` was counter-checked against the global Wizard option and correctly remains `DEFERRED: Später entscheiden`.
- Decision: target picture A is the local-first governed core; Enterprise is a profile, SSO/SCIM/roles are pilot-gated, and federation is `SOLL später`. The catalog is versionable, but evidence, security, conflict and test gates are not optional.
- Remaining risk: all product gates start `NOT RUN`; this commit is a requirements decision, not an implementation release. The single interpretation review may revise existing IDs, never fork them.
- Next test: derive the first implementation tranche from MUST/PILOT dependencies and record each product-gate result on its existing BDW ID.
## 2026-08-26T14:35:00+0200 — fix(audit): preserve legacy chain gaps with a bounded cutover

- Files: `kern/audit_segment.py`, `migrationen/migrate_audit_segment_p70.py`, `schema.sql`,
  P67–P70 migration/test material and canonical requirements.
- Why: only UTC-only breaks had a proven execution event. The remaining 19 model+timestamp and
  31 missing-pre-UTC breaks must stay visible instead of receiving made-up explanations.
- Decision: a local, append-only segment anchor binds a hash-only 50-ID manifest and validates
  only the new segment. It never edits old `access_log` or `chain_explanations` rows.
- Verified: focused P67–P70 suite `17 passed`; live path hygiene `4 passed`; copy append/tamper
  and restore succeeded; production anchor `40f35ebd-0a2d-4194-91dc-565dadecec24` reports
  integrity `ok`, FK `0`, `historical_unresolved=50`, and healthy current segment.
- Remaining risk: the local digest is not an external TSA/signature; remaining historic classes
  are deliberately unresolved. P2 dashboard/feedback redesign is not part of this release slice.

# 2026-08-26T22:00:00+0200 — fix(hermes): fail closed on missing agent context

- Files: `integrations/hermes/plugin/brainlehr_provider.py`, `tests/test_hermes_plugin.py`.
- Why: installed Hermes routes must explicitly pass `agent_context`; missing, empty, unknown, cron, subagent, oneshot, and background labels must never inherit foreground write permission.
- Verified: focused context tests `10 passed`; full plugin suites `60 passed`; installed symlink path matrix on Python 3.11/3.12/3.13 `54 passed` each; `git diff --check` passed.
- Remaining risk: Hermes `skip_memory=True` routes do not instantiate an external provider; full process/restart E2E remains outside this adapter seam.
- Brainlehr evidence used: `73a222b` source-of-truth behavior commit; near miss `L-e95b8a`.
