# AI architecture decisions

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
