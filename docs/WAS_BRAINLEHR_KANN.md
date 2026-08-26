# Was brainlehr kann

Erzeugt aus dem Quellcode am 2026-08-26T11:41:17+0200 (Stand `5d9c2588`) von `tool/faehigkeitskarte.py`. **Nicht von Hand bearbeiten** — eine handgepflegte Liste ist nach zwei Sitzungen falsch und dann schlimmer als keine.

## Auf einen Blick

| | |
|---|---:|
| Werkzeuge über MCP | 40 |
| Melder | 62, davon verdrahtet 24 |
| Haken | 23, davon verdrahtet 13 |
| Kernmodule | 136 |
| Module mit Selbsttest | 149 von 221 |

## Werkzeuge — was ein Klient aufrufen kann

Das ist die Bedienoberfläche von brainlehr. Jede Zeile kommt aus der Werkzeugtabelle des Servers selbst, nicht aus einer Doku daneben.

| Werkzeug | Was es tut |
|---|---|
| `annahme_entscheiden` | Eine Annahme bestaetigen oder widerlegen |
| `annahme_erfassen` | Eine ANNAHME festhalten, solange sie noch als Annahme erkennbar ist -- nicht erst, wenn sie sich als falsch herausgestellt hat |
| `annahme_liste` | Offene Annahmen auflisten, schlechtest belegt und aeltest zuerst |
| `einrichtung_starten` | Erststart-Assistent (BDW-P11) |
| `freigabe_setzen` | Decide, for ONE entry, who may see it: 'offen' (may leave the house), 'intern' (default -- stays here) or 'gesperrt' |
| `katalog_holen` | Holt einen der von einrichtung_starten vorgeschlagenen Kataloge (bsi, nasa-llis, wcag) in ein lokales Verzeichnis -- Netzzugriff nur hier, nie ueber einrichtung_starten selbst |
| `kettenerklaerung_erklaeren` | Explain a broken audit-chain link (access_log.ketten_hash) caused by a sanctioned rewrite of an already-logged row -- e.g |
| `knowledge_add` | Add a new knowledge node to the tree |
| `knowledge_anmelden` | Redeem a one-time invitation PIN and receive your own credential |
| `knowledge_browse` | Browse children of a knowledge tree node |
| `knowledge_freigeben` | Undo a knowledge_zurueckziehen: the node reappears in knowledge_search/recall |
| `knowledge_modell` | Read-only: list every knowledge node and lesson written by one model (actor/session/model columns, Auftrag 2026-08-06 Nachtrag) -- isolates one model's entries to judge its quality by outcom… |
| `knowledge_read` | Read full content of a knowledge node (by ID or path), plus title+summary of its direct children (one level, not recursive) -- a branch node's own content is usually empty, the substance liv… |
| `knowledge_relation_add` | Create one explicit evidenced knowledge edge between existing node IDs/paths |
| `knowledge_relation_list` | List only explicit knowledge edges, optionally incident to one node and filtered by relation type/scope |
| `knowledge_relation_remove` | Remove exactly one explicit edge by relation ID |
| `knowledge_relation_update` | Update evidence/provenance/weight/type of one explicit edge by relation ID; endpoints stay stable. |
| `knowledge_search` | Full-text search across knowledge |
| `knowledge_selbstauskunft` | What brainlehr currently is -- every number measured at call time, never maintained: tables and triggers from sqlite_master, tools from this registry, dependencies from requirements.txt |
| `knowledge_sitzung` | Read-only: list every knowledge node and lesson written by one session (actor/session columns, Auftrag 2026-08-06) -- the evaluation path for isolating one writer's entries, e.g |
| `knowledge_stats` | Overview statistics of the knowledge database (node counts, lesson counts, access patterns, anlass distribution) |
| `knowledge_trust_score` | Computed (never stored) earned-trust value in [0.05, 0.95], 0.5 = no signal yet -- distinct from norm_rang (explained by a human/consilium, decides which rule wins) and from confidence (a de… |
| `knowledge_update` | Update an existing knowledge node (title, summary, content, tags, and/or the Normschicht fields norm_rang/gilt_ab/gilt_bis/norm_entscheidung -- see knowledge_add for their meaning) |
| `knowledge_zurueckziehen` | Withdraw a node: clears content and summary (no backup -- the text is gone), keeps title and path, keeps the row (with grund/timestamp/actor) so nothing vanishes without a trace |
| `kurator_lauf` | Background cleanup agent (Hermes curator.py comparison) that ACTS, not just reports like knowledge_lint.py |
| `lesson_query` | Query lessons learned |
| `lesson_record` | Record a lesson learned |
| `lesson_update` | Correct or delete a recorded lesson |
| `project_boundary` | Return one token-capped request boundary for plan/read/edit/build/test/commit |
| `project_change` | After a verified commit, store one compact change receipt and compute the complete transitive chain of statically proven Python import consumers |
| `project_commit_ack` | Append one explicit local acknowledgement for the current staged tree |
| `project_commit_gate` | Read-only check of the opt-in staged-tree gate |
| `project_context` | Load task context progressively and token-efficiently |
| `project_ensure` | Idempotently adopt or initialize a Git project for Brainlehr |
| `prompt_invarianz_planen` | Waehlt off, light oder strong fuer eine Bewertung, Rangfolge oder Entscheidung. |
| `prompt_invarianz_pruefen` | Prueft evidenzbelegte Vergleichslaeufe auf Stabilitaet und Reihenfolgeeffekte. |
| `session_agent_reuse` | Recommend reuse, refresh-delta or a fresh agent from compact technical checkpoint state |
| `session_checkpoint_lesen` | Liest einen Checkpoint und gibt optional eine deterministische Chatwechsel-Empfehlung. |
| `session_checkpoint_schliessen` | Löscht den temporären Checkpoint einer beendeten Sitzung idempotent. |
| `session_checkpoint_setzen` | Setzt einen temporären technischen Sitzungscheckpoint ohne Freitext, Recall oder Modellaufruf. |

## Melder — was das System über sich selbst prüft

Ein Melder ohne Auslöser zählt als keiner. Die Spalte **wirkt** sagt, ob er tatsächlich an einem Ereignis hängt.

| Modul | Zweck | wirkt | Selbsttest | Katalog |
|---|---|---|---|---|
| `melder/abgabepruefung.py` | Ein Stopp-Punkt beendet die Pruefung nicht, er verlegt sie | Stop | ja | — |
| `melder/ablaufpflicht.py` | Die zwei unbelegten Schritte aus docs/ablauf.json bekommen einen | — | — | — |
| `melder/abrufwirkung.py` | Abrufwirkung | — | ja | — |
| `melder/agentenbehauptung.py` | Eine Antwort behauptet eine Handlung, fuer die im selben Zug kein | Stop | ja | — |
| `melder/agentendauer.py` | agentendauer.py | — | ja | — |
| `melder/arbeitsmelder.py` | Ein Melder auf die ARBEIT, nicht auf den Bestand | PostToolUse | ja | — |
| `melder/auftragsregister.py` | Anweisungsregister | — | ja | — |
| `melder/ausloeserlos.py` | Meldet Mechanismen unter melder/, haken/, berichte/, die NIE von selbst | SessionStart | ja | — |
| `melder/bewegungsmelder.py` | Haelt die Zahlen der anderen Melder fest und meldet beim naechsten Lauf | SessionStart | ja | — |
| `melder/client_bootstrap.py` | Generate the three thin public client adapters from one policy bundle | — | — | — |
| `melder/derivatfrische.py` | Meldet abgeleitete Dokumente, die AELTER sind als ihre Quelle | SessionStart | ja | — |
| `melder/dienstwache.py` | Wacht ueber den Dokumentdienst | SessionStart | ja | — |
| `melder/dokumentzugang.py` | Linie A aus docs/PLAN_DOKUMENTABLAGE_2026-08-16.md | — | — | — |
| `melder/eilmeldung_etikett.py` | Prueft, ob ein Titel Dringlichkeit BEHAUPTET, ohne das Etikett zu TRAGEN | SessionStart | ja | — |
| `melder/eilmeldung_faellig.py` | Zeigt beim Sitzungsstart, welche Eilmeldungen verfallen sind, statt in | SessionStart | ja | — |
| `melder/einbettungsaussetzer.py` | Meldet beim Sitzungsstart, wenn die Aussetzer-Sicherung juengst pausiert hat | — | ja | — |
| `melder/faehigkeiten.py` | faehigkeiten.py | — | ja | — |
| `melder/faelligkeit.py` | Was raus muss, unabhaengig davon, was gefragt wurde | SessionStart | ja | — |
| `melder/foederation.py` | foederation.py | — | ja | — |
| `melder/forderung_vorgang.py` | Forderung ans eigene Haus: erkennen (Vorlage), markieren, auflisten | — | ja | — |
| `melder/fremdbaum_cd.py` | Wiederholtes `cd <fremdes Repo>` im Bash-Aufruf | — | ja | — |
| `melder/fremdrollen.py` | Meldet zwei Fehlklassen in den Claude-Code-Fertigkeiten unter | — | ja | — |
| `melder/fremdstandsvergleich.py` | Meldet, wenn eine fremde Software oder ein Gesetzestext seit dem letzten | SessionStart | ja | — |
| `melder/gatestand.py` | Haelt den Lastenkatalog gegen seine eigenen Produktgates: wie viele | — | ja | BDW-C03, BDW-E07, BDW-X01 |
| `melder/kantenstillstand.py` | Melder: die Kantenberechnung steht still | SessionStart | ja | — |
| `melder/kartenstand.py` | Sind die Landkarten noch wahr? | — | — | — |
| `melder/kaskadenanteil.py` | Wie lange arbeitet der teuerste Faden mechanisch weiter, ohne zu delegieren? | Stop | ja | — |
| `melder/kennungskollision.py` | Traegt in `docs/` eine Kennung (S12, B4.3, §4, 104.1.2) zwei VERSCHIEDENE | — | ja | — |
| `melder/klassenausfall.py` | Eine ganze Zielklasse trifft nie | — | ja | BDW-P04 |
| `melder/korrekturlehre.py` | Stop-Waechter: der Betreiber hat korrigiert | Stop | ja | — |
| `melder/landkarten.py` | Fuenf Landkarten des brainlehr-Universums, erzeugt statt gepflegt | — | — | — |
| `melder/messregeln.py` | Ein Bestwert aus vielen Versuchen ist keine Messung | — | ja | — |
| `melder/modellwege.py` | Sind die Modell-Endpunkte erreichbar, auf die brainlehr zeigt? | SessionStart | — | — |
| `melder/neue_achse.py` | Kommt eine neue Achse dazu | SessionStart | — | — |
| `melder/normwiderspruch.py` | Findet Widersprueche zwischen gleichrangigen Normen | — | — | — |
| `melder/nulllinie.py` | Eine leere Ausgabe wird als Befund gemeldet, ohne dass eine Nulllinie | — | ja | — |
| `melder/offene_arbeit.py` | Zeigt beim Sitzungsstart, was offen ist | SessionStart | ja | — |
| `melder/ohne_mechanismus.py` | Welche Lehren wiederholen sich | — | ja | — |
| `melder/plan_bestandsabgleich.py` | Haelt Planzeilen aus docs/PLAN_GESAMT_2026-08-13.md gegen den Code und | — | ja | — |
| `melder/planberuehrung.py` | Meldet, wenn gebaut wird, waehrend der Plan unveraendert bleibt | — | — | — |
| `melder/planmitschrieb.py` | Meldet, wenn Code entsteht, ohne dass der Plan mitwaechst | — | — | BDW-P15, BDW-P19 |
| `melder/pruefer.py` | Der erste Melder, der URTEILT statt zaehlt | SessionStart | ja | — |
| `melder/quelle_gegen_betrieb.py` | Ausgeliefertes Artefakt gegen seine Quelle | — | ja | — |
| `melder/rasterblick.py` | Ein Rastervermerk je Ergebnisdatei | SessionStart | ja | — |
| `melder/rotprobe.py` | Waechter: ein Commit behauptet eine Behebung und nennt keinen Beleg | — | ja | — |
| `melder/rueckfrageschleife.py` | Stop-Waechter: meldet, wenn eine Antwort mit einer Entscheidungsfrage an den | Stop | ja | — |
| `melder/schemastand.py` | Soll gegen Ist: haelt schema.sql gegen die INSTALLIERTEN Schemaobjekte | — | ja | — |
| `melder/selbstbeschreibung.py` | selbstbeschreibung.py | — | ja | — |
| `melder/sichtbarkeit.py` | Jeder Lese- und Schreibvorgang am Speicher wird eine Zeile im Gespraech | SessionStart, PostToolUse | ja | — |
| `melder/spaltenabgleich.py` | J3 | — | ja | — |
| `melder/speicherherkunft.py` | Melder: traegt eine Antwort eine Aussage aus dem Speicher, ohne ihn zu nennen? | — | ja | — |
| `melder/systembenutzer_probe.py` |  | — | — | — |
| `melder/unbelegter_eingang.py` | Ein entfernter/ersetzter Eingang wird an seinen Konsumenten unbelegt weiter behauptet | — | ja | — |
| `melder/unverdrahtet_swift.py` | Findet Swift-Ansichten und -Typen, die gebaut, aber von nirgends gerufen werden | — | ja | — |
| `melder/vektorstand.py` | Ein Vektor, der einen Text beschreibt, den es so nicht mehr gibt | SessionStart | ja | — |
| `melder/verbundkarte.py` | Schritt 1 aus docs/PLAN_DIAGRAMME_2026-08-16.md | — | — | — |
| `melder/vermutungswaechter.py` | Stop-Waechter: meldet eine VERMUTUNG, die als Befund dasteht | Stop | ja | — |
| `melder/vier_nenner.py` | vier_nenner.py | — | ja | — |
| `melder/vorschlagsmelder.py` | Melder: nur die NEUEN Vorschlaege aus berichte/vorschlag.py | — | ja | — |
| `melder/wirkkette.py` | J2 | — | ja | — |
| `melder/wissensverlauf.py` | Wissensverlauf | SessionStart, Stop | ja | — |
| `melder/zugriffsmuster.py` | Ungewoehnliche Zugriffsmuster auf den Wissensbestand | — | ja | BDW-E25 |

## Haken — was bei jedem Prompt und jedem Werkzeugaufruf läuft

Diese Module bestimmen, was ohne Zutun in den Kontext gelangt.

| Modul | Zweck | wirkt | Selbsttest | Katalog |
|---|---|---|---|---|
| `haken/agentenanker_abruf.py` | agentenanker_abruf.py | — | ja | — |
| `haken/agentenanker_einspielung.py` | agentenanker_einspielung.py | — | ja | — |
| `haken/antwort_abruf.py` | antwort_abruf.py | UserPromptSubmit, Stop | ja | — |
| `haken/auftrag_recall_hook.py` |  | SubagentStart, UserPromptSubmit | ja | — |
| `haken/auftragshypothese_waechter.py` | PreToolUse-Haken (Matcher: Agent) | PreToolUse | ja | — |
| `haken/auszug_nachziehen.py` | Stop-Haken: den Auszug nachziehen, wenn der Bestand juenger ist | Stop | — | — |
| `haken/eilmeldung_frisch.py` | Stellt FRISCHE Eilmeldungen mitten in eine laufende Sitzung zu | UserPromptSubmit, PostToolUse | ja | — |
| `haken/existenzpruefung.py` | existenzpruefung.py | — | ja | — |
| `haken/knowledge_capture_hook.py` |  | Stop | — | — |
| `haken/knowledge_recall_hook.py` |  | UserPromptSubmit | ja | BDW-P06, BDW-P08 |
| `haken/kontextstand.py` | Meldet, wenn das Kontextfenster voll laeuft | — | — | — |
| `haken/kurator_taeglich.py` | kurator_taeglich.py [--force] [--heute ISO8601] / --selbsttest | — | ja | — |
| `haken/mcp_veraltet.py` |  | SubagentStart, UserPromptSubmit | — | — |
| `haken/mehrstufiger_abruf.py` | S12 (docs/PLAN_DESTILLE_2026-08-09.md): zwei billige Stufen VOR einem | — | ja | — |
| `haken/messauswertung_waechter.py` | Ausloeser fuer den Schritt "beim Auswerten einer Messung" | — | ja | — |
| `haken/messung_frageform_abrufguete.py` | Aufgabe 75 (Linie B) | — | — | — |
| `haken/ort.py` | Wo liegt brainlehr | — | — | — |
| `haken/regelrouting.py` | Regel-Routing: spielt eine Regel ein, WENN sie gebraucht wird | PreToolUse | ja | — |
| `haken/regelwechsel.py` | Meldet mitten in der Sitzung, wenn sich eine Regeldatei geaendert hat | SubagentStart, UserPromptSubmit | — | — |
| `haken/stand_format_waechter_hook.py` | PostToolUse-Haken: STAND.md gegen ihr Pflichtformat pruefen | PostToolUse | — | — |
| `haken/stash_guard_hook.py` | PreToolUse-Guard (Bash): `git stash` in JEDER schreibenden Form verhindern | PreToolUse | — | — |
| `haken/suchpfad_abruf.py` | S9 (docs/PLAN_DESTILLE_2026-08-09.md): Kandidaten fuer den Abruf ueber | — | ja | — |
| `haken/worktree_identitaet.py` | WorktreeCreate-Haken: Identitaets- und Regeldateien reisen mit | SessionStart, WorktreeCreate | ja | — |

## Kern — worauf alles aufsetzt

| Modul | Zweck | Selbsttest |
|---|---|---|
| `kern/abloesung.py` | Eine Abloesung ist selbst ein Wissensgegenstand | ja |
| `kern/abrufguete.py` | Abrufguete auf dem Pruefkorpus (runs/pruefkorpus.jsonl, 45 Faelle) -- | ja |
| `kern/actor_project_boundary.py` | Fail-closed local actor/project checks | — |
| `kern/analyzer_registry.py` | Optional local analyzer registry: explicit commands, timeout and no fallback | — |
| `kern/anfrage_erweiterung.py` | anfrage_erweiterung.py | ja |
| `kern/ankerverfahren.py` | Ankerverfahren | ja |
| `kern/anmeldung.py` | Einen Teilnehmer anmelden | ja |
| `kern/auditanker.py` | Auditanker | ja |
| `kern/aufbewahrung.py` | Aufbewahrungsfristen je Datenklasse | ja |
| `kern/ausloeser.py` | ausloeser.py | ja |
| `kern/ausschreibekatalog.py` | ausschreibekatalog.py | ja |
| `kern/ausweis.py` | ausweis.py | ja |
| `kern/baustein.py` | Der Baustein-Vertrag | ja |
| `kern/bauvermeidung.py` | bauvermeidung.py | ja |
| `kern/belegsprache.py` | Eine Frage, eine Wortliste: woran erkennt man einen Beleg im Text? | ja |
| `kern/belegvertrag.py` | Belegvertrag | — |
| `kern/bereinigung.py` | Was das Haus verlaesst, wird angesehen | ja |
| `kern/bestandteile.py` | kern/bestandteile.py | — |
| `kern/betriebsprofil.py` | Betriebsprofil | ja |
| `kern/build_embeddings.py` | build_embeddings.py | — |
| `kern/build_node_index.py` |  | ja |
| `kern/code_retrieval.py` | Revision-bound routing and metadata for the optional CodeRank code channel | — |
| `kern/codekanten.py` | Welche Datei betrifft diese Lehre | ja |
| `kern/codeql_policy.py` | Explicit eligibility gate for optional CodeQL SARIF evidence | — |
| `kern/codestand.py` | Ermittelt den Codestand (Commit, Zweig, schmutzig) zur LAUFZEIT fuer | — |
| `kern/connector_register.py` | connector_register.py | — |
| `kern/coverage_provenance.py` | Conservative coverage provenance for code evidence | — |
| `kern/dependency_evidence.py` | Small, offline dependency evidence reader | — |
| `kern/designtokens_latex.py` | LaTeX-Erzeuger fuer den Gestaltungsvorrat (ADR-015) | ja |
| `kern/doctor.py` | doctor | — |
| `kern/dokument.py` | Der Baustein-Vertrag, abgebildet auf ein CRDT-Dokument | ja |
| `kern/dokumentdienst.py` | Der Dokumentdienst | ja |
| `kern/dokumentenablage.py` | Dokumentenablage: drei Schichten, und nur die mittlere geht in den Index | ja |
| `kern/domaene.py` | Domaenenpaket-Importer (PLAN_OPENLEHR_2026-08-14.md H8a) | — |
| `kern/driftwaechter.py` | F6 im Gesamtplan, EIN Modul fuer beide Haelften: die schnelle Darstellung | ja |
| `kern/eilmeldung.py` | Eilmeldung senden | ja |
| `kern/einrichtung.py` | Erststart im Chat | ja |
| `kern/einschleusung.py` | einschleusung.py | ja |
| `kern/embeddings.py` | Lokale Embeddings via Ollama + Brute-Force-Cosine-Fusion mit FTS5/LIKE | — |
| `kern/endgueltig_entfernen.py` | endgueltig_entfernen.py | ja |
| `kern/eskalation_vorlage.py` |  | — |
| `kern/evidence_adapters.py` | Normalize bounded, revision-tagged evidence from optional local analyzers | — |
| `kern/evidence_graph.py` | Canonical graph-v2 merge/reconciliation without analyzer execution or writes | — |
| `kern/evidence_projections.py` | Small, source-bound projections for optional runtime evidence | — |
| `kern/fenstergroesse.py` | Misst, ab welcher Ollama-Kontextfenstergroesse (num_ctx) brainlehr nicht | ja |
| `kern/fix_namensraum_knoten.py` | fix_namensraum_knoten.py | — |
| `kern/fremdimport.py` | Fremdbestände holen | ja |
| `kern/fundstelle.py` | fundstelle.py | ja |
| `kern/gattung_filter.py` | gattung_filter.py | — |
| `kern/gegenstand.py` | Ein Gegenstand hat eine bedeutungslose ID; sein Name ist ein Attribut mit | ja |
| `kern/gegenstand_plankennungen.py` | Die Plankennungen als GEGENSTAENDE | ja |
| `kern/geheimnis.py` | geheimnis.py | — |
| `kern/geltungsbereich.py` | geltungsbereich.py | — |
| `kern/graph_envelope_store.py` | Small, atomic JSON store for revision-bound graph envelopes | — |
| `kern/hebb_kanten.py` | Hebbsche Kanten: recall_log.jsonl -> knowledge_relations | ja |
| `kern/herkunft_belegung.py` | herkunft_belegung.py | ja |
| `kern/herkunft_normentscheider.py` | Wer hat entschieden | ja |
| `kern/kanalguete_messung.py` | Messwerkzeug fuer docs/PLAN_KANALGUETE_2026-08-15.md | — |
| `kern/kanarienvogel.py` | kanarienvogel.py | ja |
| `kern/kanten_aus_bedeutung.py` | Kanten aus Bedeutung: knowledge_relations aus vorhandenen Embeddings ziehen | — |
| `kern/kanten_aus_lehren.py` |  | — |
| `kern/kanten_herkunft_rueckwirkend.py` | kanten_herkunft_rueckwirkend.py | ja |
| `kern/kettenerklaerung.py` | kettenerklaerung.py | ja |
| `kern/knowledge_lint.py` | Knowledge-Lint | ja |
| `kern/konfidenz.py` | konfidenz.py | ja |
| `kern/kundenschluessel.py` | kundenschluessel.py | ja |
| `kern/lehrenpaket.py` | lehrenpaket.py | ja |
| `kern/lesson_recorder.py` |  | — |
| `kern/liefermenge.py` | Liefermenge des Abrufs (Auftrag 2026-08-09, Aufgabe 1) | ja |
| `kern/meisterschaft.py` | Titelverteidiger-Mechanik fuer die Abrufkette (Betreiber-Entwurf 2026-08-08) | ja |
| `kern/messlauf_abrufguete.py` | Misst knowledge_recall_hook.query() gegen den Pruefkorpus (45 Faelle | ja |
| `kern/messparameter.py` | Parameterblock fuer Ergebnisdateien unter runs/ (Auftrag 2026-08-07 | ja |
| `kern/migrate_knowledge.py` |  | — |
| `kern/migrate_normfelder.py` | migrate_normfelder.py | ja |
| `kern/migrate_relations.py` | Add explicit knowledge relations and access provenance; safe and idempotent | — |
| `kern/nachrangung.py` | Nachrangung: umordnen, was die Fusion geliefert hat | — |
| `kern/nachtlaeufer.py` | nachtlaeufer.py | ja |
| `kern/namensfrage.py` | Eine Namensfrage erkennen und den Eigennamen herausloesen | — |
| `kern/normachsen.py` | Die drei Achsen der Normordnung | ja |
| `kern/normbestand.py` | normbestand.py | ja |
| `kern/normbezug.py` | normbezug.py | ja |
| `kern/normfundstelle.py` | normfundstelle.py -- aus "§ 16 Abs | ja |
| `kern/normkraft.py` | normkraft.py | ja |
| `kern/normrang.py` | normrang.py | ja |
| `kern/planbindung.py` | Ein Melder auf die BINDUNG zwischen Plan und Speicher | ja |
| `kern/planentscheidung.py` | Erzeugt Knoten aus ENTSCHEIDENDEN Planabschnitten und schreibt die | ja |
| `kern/planordnung.py` | Ein Plan ist eine FOLGE, der Wissensspeicher eine MENGE (Auftrag | ja |
| `kern/planstatus.py` | Ablage fuer ERLEDIGUNG eines Planabschnitts | ja |
| `kern/project_analysis_loop.py` | Small in-memory cadence controller for revision-bound code analysis | — |
| `kern/project_boundary_cli.py` | CLI entry point for the client-neutral, request-local boundary contract | — |
| `kern/project_context.py` | Small, client-neutral project capsule and bounded code probe | — |
| `kern/project_impact_cli.py` | Render a revision-bound impact graph from the same typed JSON used by MCP | — |
| `kern/prompt_invarianz.py` | Deterministisches Routing fuer prompt-sensible Entscheidungen | — |
| `kern/pruefkorpus.py` | Pruefkorpus fuer Abrufguete (Plan hub/docs/PLAN_ABRUFGUETE_2026-08-07.md | ja |
| `kern/pruefkorpus_rivalen.py` | Pruefkorpus mit erzwungenen Rivalinnen (AUFGABE 68) | ja |
| `kern/pruefkorpus_v3.py` | Pruefkorpus V3 | ja |
| `kern/pruefspruch.py` | Ein Prüfspruch gehört dem Prüfer, nicht dem Geprüften | ja |
| `kern/rangfolge.py` | rangfolge.py | ja |
| `kern/raum_daten.py` | raum_daten.py | ja |
| `kern/regelpaket.py` | regelpaket.py | ja |
| `kern/reifegrad.py` | reifegrad.py | ja |
| `kern/release_identity.py` | Offline, deterministic release identity evidence | — |
| `kern/relevanzlage.py` | Sagen, wie belastbar ein Suchergebnis ist | — |
| `kern/risikoeinstufung.py` | risikoeinstufung.py | — |
| `kern/rueckwirkung.py` | Gemeinsame Bauform fuer Rueckwirkungs-Zaehler | ja |
| `kern/satz.py` | Der Satzweg: aus einem Dokument (`kern/dokument.py`) wird LaTeX-Quelle | ja |
| `kern/satzwache.py` | Die Ableitungswache: prueft das gesetzte Blatt GEGEN die Baustein-Quelle | — |
| `kern/schema_nachzug.py` | Fehlende Spalten aus schema.sql nachziehen | ja |
| `kern/schluesselablage.py` | schluesselablage.py | ja |
| `kern/schnappschuss.py` | Ein Lauf liest einen festgehaltenen Stand | ja |
| `kern/selbstauskunft.py` | Was brainlehr ueber sich selbst sagt | — |
| `kern/session_checkpoint.py` | Temporärer Sitzungszustand und deterministische Chatwechsel-Empfehlung | — |
| `kern/sicherung_s12.py` | Urfassung sichern, bevor S12 einen Knotentext ueberschreibt | ja |
| `kern/sicherungen.py` | Aufbewahrungsregel fuer die automatischen Datenbanksicherungen | ja |
| `kern/sortierregel.py` | Welche Lehre gehoert in den Codepfad, welche bleibt im Nachschlagewerk? | ja |
| `kern/speicher.py` | Eine Tuer zur Wissensdatenbank statt hundert | ja |
| `kern/spracherkennung.py` | Sprache eines Textes erkennen | — |
| `kern/suche_postgres.py` | Die rechte Seite des Paritaetsmessers: dieselbe Suche in Postgres | ja |
| `kern/teilnehmer.py` | Teilnehmerkennungen fuer das gemeinsame Dokument | ja |
| `kern/teilung_s12.py` | Teilung des Bestands in behandelt/unbehandelt | — |
| `kern/tokenkosten.py` | tokenkosten.py | — |
| `kern/trennung.py` | trennung.py | — |
| `kern/uebernahmeregister.py` | Uebernahmeregister | — |
| `kern/umschrift_pruefstein.py` | Faellt beim Umschreiben Sachgehalt weg? Deterministisch geprueft, nicht | ja |
| `kern/umschrift_s12.py` | S12 Schritt 3: die behandelte Haelfte nach drei Schreibregeln umschreiben | ja |
| `kern/verfallsrate.py` | Verfallsrate je Ast | ja |
| `kern/vertrauen.py` | Der Vertrauensregler | — |
| `kern/werkzeugrechte.py` | werkzeugrechte.py | ja |
| `kern/wiedereinstieg.py` | Wiedereinstieg nach Verdichtung: spielt zurueck, was in DIESER Sitzung | — |
| `kern/wirkung.py` |  | — |
| `kern/wissensnutzen.py` | Misst, was brainlehr BEITRAEGT | ja |
| `kern/wissensnutzen_blind.py` | Wie wissensnutzen.py, aber Abruf entsteht aus der AUFGABE, nicht aus der | ja |
| `kern/zahlenbezug.py` | zahlenbezug.py | ja |
| `kern/zeitfenster.py` | zeitfenster.py | ja |
| `kern/zeitmarke.py` | Die eine Stelle, an der ein Zeitstempel entsteht | ja |
| `kern/zitatpruefer.py` | zitatpruefer.py | — |

## Abgleich mit dem Lastenkatalog

40 Katalogzeilen werden im Code ausdrücklich genannt. Eine Zeile ohne Nennung hat keinen Code, der sich auf sie beruft — das ist die Gegenrichtung zur Belegspalte, die sagt, ob geprüft wurde.

| Katalogzeile | genannt in |
|---|---|
| `BDW-C03` | melder/gatestand.py |
| `BDW-E03` | kern/trennung.py |
| `BDW-E06` | kern/ausweis.py, kern/trennung.py |
| `BDW-E07` | kern/schluesselablage.py, melder/gatestand.py |
| `BDW-E12` | kern/aufbewahrung.py |
| `BDW-E13` | kern/aufbewahrung.py |
| `BDW-E15` | kern/sicherungen.py |
| `BDW-E18` | kern/schluesselablage.py |
| `BDW-E22` | kern/trennung.py |
| `BDW-E23` | kern/trennung.py |
| `BDW-E25` | melder/zugriffsmuster.py |
| `BDW-F07` | kern/domaene.py |
| `BDW-F08` | kern/connector_register.py |
| `BDW-P04` | melder/klassenausfall.py |
| `BDW-P06` | haken/knowledge_recall_hook.py |
| `BDW-P08` | haken/knowledge_recall_hook.py |
| `BDW-P09` | kern/betriebsprofil.py |
| `BDW-P10` | kern/einrichtung.py, kern/spracherkennung.py |
| `BDW-P11` | kern/einrichtung.py |
| `BDW-P12` | kern/einrichtung.py, kern/fremdimport.py |
| `BDW-P13` | kern/verfallsrate.py |
| `BDW-P15` | kern/dokumentenablage.py, melder/planmitschrieb.py |
| `BDW-P19` | melder/planmitschrieb.py |
| `BDW-U04` | kern/connector_register.py |
| `BDW-X01` | melder/gatestand.py |
| `BDW-X02` | melder/gatestand.py |
| `BDW-X03` | melder/gatestand.py |
| `BDW-X04` | melder/gatestand.py |
| `BDW-X05` | melder/gatestand.py |
| `BDW-X06` | melder/gatestand.py |
| `BDW-X07` | melder/gatestand.py |
| `BDW-X08` | melder/gatestand.py |
| `INT-ACT-001` | kern/ausloeser.py |
| `INT-DNST-001` | kern/domaene.py |
| `INT-REG-001` | kern/domaene.py |
| `INT-SNAP-001` | kern/messlauf_abrufguete.py, kern/schnappschuss.py |
| `INT-UPD-001` | kern/domaene.py |
| `INT-UPD-002` | kern/domaene.py |
| `INT-VER-001` | kern/domaene.py |
| `INT-ZZ-001` | melder/gatestand.py |
