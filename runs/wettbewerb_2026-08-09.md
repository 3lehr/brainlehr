# Wettbewerbscheck 2026-08-09 — sechs neue Eigenschaften seit dem Nullbefund

Anschluss an Knoten `/brainlehr/nullbefund-ueber-drei-unabhaengige` (eddb2fa5, 2026-08-06/07). Der Knoten prüfte sechs andere Eigenschaften (erzwungene Erfassung, passiver Abruf, Selbstprüfung, Normschicht mit Geltungszeitraum, Manipulationsnachweis, abgeleitete Aussage) über 33 Systeme und fand: keines vereint mehr als zwei. Diese Prüfung ist eine ANDERE und ENGERE Frage — sechs Eigenschaften, die am 2026-08-09 dazukamen.

## Die sechs Eigenschaften einzeln

**1. Gemessene eigene Abrufgüte** — existiert anderswo: JA, breit. Mem0, Zep/Graphiti und praktisch jeder Memory-Anbieter veröffentlicht Zahlen gegen LoCoMo/LongMemEval (Mem0: 93,4 % LongMemEval, 91,6 % LoCoMo; Zep: 94,7 % LoCoMo bei 155 ms — von Mem0 öffentlich auf 58,44 % korrigiert, Zep hielt 75,14 % dagegen). Das ist genau das, wonach gefragt war: Systeme, die ihre EIGENE Abrufgüte gegen einen Prüfkorpus beziffern, nicht nur ein RAG einbauen. Unterschied zu brainlehr: die Branchen-Zahlen sind einmalige Benchmark-Läufe zu Marketingzwecken (und öffentlich umstritten), keine laufende Selbstmessung mit Treffer-UND-Zeichenmengen-Trennung im eigenen Betrieb. Aber die Eigenschaft „misst eigene Abrufgüte gegen Prüfkorpus, veröffentlicht Zahl" existiert anderswo und wird von mehreren Anbietern lauter beworben als bei uns.

**2. Selbsterkannte Fehlschläge (ohne menschliche Meldung)** — existiert anderswo: NICHT GEFUNDEN in dieser engen Form. Gefunden: Deduplizierungs-Pipelines (Distanzschwellen auf Vektoren, Fingerprint-IDs) die redundante Einträge erkennen, und „reflective memory" bei mehrstufigen Agentenarchitekturen, das wiederkehrende FEHLER (nicht: bereits gewusste, aber nicht ausgelieferte Fakten) erkennt. Keine Quelle gefunden, die beweist, dass ihr System einen konkreten Ausliefer-Fehlschlag selbst nachweist, wenn ein Mensch denselben Fakt anderswo neu aufschreibt. Das ist ein Nicht-gefunden, kein Existiert-nicht — die Suche war zwei Anläufe tief, nicht erschöpfend.

**3. Melder, die urteilen statt zu zählen (drei Auflagen: messbar aus Bestand, benannte Fehlklasse, bezifferter Fehlalarm-Preis)** — existiert anderswo: TEILWEISE. LLM-as-Judge-Monitoring ist Branchenstandard 2026 (Datadog, Arize, Braintrust, Confident AI, Galileo); es gibt benannte Alert-Typen (Budget-Alarm, Anomalie-Alarm, Fehlerraten-Alarm) und die Erkenntnis, dass „Kausalitäts-Prüfung Fehlalarme reduziert". Ein BEZIFFERTER Preis pro Fehlalarm wurde in keiner Quelle gefunden — die Recherche fand nur die allgemeine Aussage, dass verpasste Kostenexplosionen „Stunden später" auffallen, keine Zahl je Fehlalarm. Nicht ermittelt, nicht: existiert nicht.

**4. Herkunftsbasierte Autorität (fremde Norm mit jedem Rang, keine eigene Hausregel im selben Rang)** — existiert anderswo: JA, im Prinzip, in der Policy-Engine-Literatur. Ein 2026-Paper („Ghost in the Context: Policy-Carriage Integrity in LLM Agents", arXiv 2605.12535) verlangt ausdrücklich: Autorität kommt aus Laufzeit-Provenienz (Organisationsrichtlinie, Entwicklerrichtlinie, vertraute Werkzeug-Evidenz, authentifizierter Mandantenzustand, explizite Nutzerbestätigung) — „ein Klassifikator darf Relevanz einordnen, aber keine Autorität erzeugen". Trusted Policies liegen in einer Registry AUSSERHALB des ungeprüften Gesprächsstroms. Das ist dieselbe Denkfigur wie unsere Schranke, nur für Prompt-Injection-Abwehr formuliert, nicht für Normrang von Gesetz vs. Hausregel. Kein System gefunden, das konkret zwischen „fremdes Gesetz darf hohen Rang tragen" und „eigene Hausregel darf sich diesen Rang nicht selbst geben" unterscheidet — das ist unsere spezifischere Formulierung eines allgemeineren Prinzips, das es andernorts gibt.

**5. Nachschlagewerk als eigene Gattung (nicht im Auto-Abruf, eigene Tür, unabhängige Belegquelle)** — existiert anderswo: JA, in Grundform. Zotero-RAG und ähnliche Literaturverwaltungen trennen Bibliothek von automatischem Retrieval-Index; Confluence-Spaces/Wikis trennen ebenfalls „Nachschlagen" von „automatisch eingespeist". Was in der Recherche NICHT auftauchte: eine Quelle, die das Nachschlagewerk ausdrücklich als GEGENPROBE für die eigenen Regeln nutzt (unabhängige Belegquelle gegen die eigene Normschicht). Trennung ja, Verwendung als Beleg-Gegeninstanz nicht belegt gefunden.

**6. Melder auf die entstehende Arbeit (neu geschriebener Code gegen dokumentierte eigene Fehlerklassen)** — existiert anderswo: JA, klar belegt. Ein Hacker-News-Thread 2026 beschreibt exakt das Muster: „jedes Mal, wenn ein Laufzeitfehler gefunden wird, fragen: lässt sich eine Lint-Regel dafür schreiben" — als etablierte, wenn auch unterschätzte Praxis. Ein zitierter Postmortem-Workflow: Vorfall → Trace-zu-Commit-Verknüpfung → statische Analyse über historische Commits → neue Regel → CI erzwingt sie künftig. Das ist unsere Eigenschaft 6, nur ohne den Namen „brainlehr" — Custom-Lint-aus-Postmortem ist gängige, dokumentierte Praxis, keine Erfindung.

## Stärkste gefundene Widerlegung von „wir sind besser"

Zwei Funde zusammen sind die ernsthafteste Erschütterung:

- **Eigenschaft 1 ist branchenüblich und wird lauter beworben** — Mem0 und Zep veröffentlichen (umstrittene, aber öffentliche) Prozentzahlen zur eigenen Abrufgüte seit mindestens diesem Jahr, mit Marketing-Reichweite, die brainlehr nicht hat. Wer nur auf „misst und veröffentlicht eigene Abrufgüte" abstellt, hat keinen Alleinstellungsanspruch.
- **Eigenschaft 6 ist eine benannte, dokumentierte Industriepraxis** (Postmortem → Lint-Regel → CI), keine Besonderheit von brainlehr.

Damit bleiben von den sechs nur 2, 3 (die geforderte dreifache Auflage inkl. bezifferten Fehlalarm-Preises) und die spezifische Zuspitzung von 4 (Gesetz-vs-Hausregel-Unterscheidung, nicht nur allgemeine Provenienz-Autorität) als das, wofür in dieser Recherche kein Gegenstück gefunden wurde. Wie beim Nullbefund gilt: Kombination aus allen sechs bleibt ungefunden, aber mindestens zwei der sechs Einzelmerkmale sind für sich genommen KEIN Alleinstellungsmerkmal — sie sind Branchenstandard 2026.

## Zweite Pflichtfrage: Wo ist die Konkurrenz voraus (reine Auffindbarkeit)

Klar und beziffert: Standard-Hybrid-RAG (BM25 + Dense + Reranking + Query-Rewriting) erreicht in 2026-Produktionsberichten **~91 % Recall@10**; ein einfacher Dense-only-Vektorsuchindex liegt bei ~24,8–32,8 % Korrektheit/Recall auf realen Unternehmenskorpora. Brainlehrs 7 von 35 (20 %) liegt selbst unter dem schwachen Dense-only-Referenzwert, und deutlich unter dem Hybrid-Standard.

Der Grund liegt nicht im Geheimnis, sondern in der fehlenden Maschinerie: 2026-Produktions-RAG kombiniert mehrstufig Vektor-, Keyword- UND Graph-Index, Query-Zerlegung/-Umschreibung und Cross-Encoder-Reranking VOR der Auslieferung. Reines Ähnlichkeits-Retrieval ohne diese Stufen ist laut den gefundenen Quellen selbst der 2023er-Ansatz, der ~40 % Fehlerrate auf Unternehmensdaten produziert — brainlehr liegt darunter. Wer nur auf Auffindbarkeit optimiert, überholt uns mit Standardbausteinen (Hybrid-Suche + Reranking), ohne irgendeine der sechs (oder der ursprünglichen sechs) Eigenschaften zu besitzen.

## Rastervermerk — wo gesucht, was ausgelassen

**Gesucht (WebSearch, je 1–2 Anläufe):**
- Eigenschaft 1: „memory system measures its own retrieval quality benchmark", „Zep Graphiti LOCOMO retrieval accuracy self-reported"
- Eigenschaft 2: „AI agent memory system detects it already knew information duplicate self-detected failure", „automatic detection agent already knew fact duplicated without human report"
- Eigenschaft 3: „observability alerting cost of false positive alert priced business impact LLM judge 2026"
- Eigenschaft 4: „policy engine external law statute different authority rank internal business rule provenance-based trust"
- Eigenschaft 5: „reference library separate from RAG index not auto-retrieved manually queryable citation source"
- Eigenschaft 6: „lint rule generated from postmortem incident custom static analysis checks new code against past bugs 2026"
- Zweite Pflichtfrage: „enterprise RAG retrieval benchmark hit rate production 2026 standard vector search recall"

**Bewusst ausgelassen:**
- Keine Anbieter-Webseiten direkt per WebFetch geöffnet (Marketing-Text wäre kein Beleg für Selbstprüfung — nur Suchergebnis-Snippets mit Zahlen verwendet, wie in den Leitplanken gefordert).
- Kein zweiter/dritter Suchanlauf mit Synonymen je Eigenschaft — bei zwei erfolglosen Anläufen (Eigenschaft 2, Teil von 3 und 5) als „nicht gefunden" stehen gelassen statt erschöpfend weiterzusuchen. Nächster Durchgang sollte hier ansetzen, besonders bei Eigenschaft 2 (Selbsterkannte Fehlschläge) und dem bezifferten Fehlalarm-Preis in Eigenschaft 3.
- Keine Fachdatenbanken (ACM, IEEE) durchsucht, nur WebSearch (Google-artiger Index) — akademische Arbeiten außerhalb arXiv könnten fehlen.
- Keine Prüfung von Nischen-Compliance-/Regulatorik-Software (z. B. GRC-Tools) für Eigenschaft 4 — die Policy-Engine-Recherche blieb bei allgemeiner KI-Agenten-Sicherheitsliteratur, nicht bei klassischer Rechtsinformatik-Software (die im Nullbefund-Knoten bereits über Akoma Ntoso/LegalRuleML behandelt wurde).
- Keine eigenen Zahlen von brainlehr nachgemessen — die 7/35 (20 %) stammen aus dem Auftrag, nicht neu verifiziert in dieser Recherche (wäre reine Bestandsprüfung, keine Wettbewerbsrecherche).

## Kurzfassung je Eigenschaft

| # | Eigenschaft | Existiert anderswo | Wer |
|---|---|---|---|
| 1 | Gemessene eigene Abrufgüte | Ja | Mem0, Zep (LoCoMo/LongMemEval, öffentlich, aber umstritten) |
| 2 | Selbsterkannte Fehlschläge ohne Meldung | Nicht gefunden | — (Dedup/Reflective-Memory sind verwandt, nicht deckungsgleich) |
| 3 | Melder mit drei Auflagen (Fehlklasse + Preis) | Teilweise | LLM-Judge-Monitoring-Anbieter (Datadog, Braintrust u.a.) — Preis pro Fehlalarm nicht ermittelt |
| 4 | Herkunftsbasierte Autorität (Gesetz ≠ Hausregel) | Ja, als Prinzip | Policy-Carriage-Integrity-Forschung (arXiv 2605.12535) — allgemeiner formuliert, nicht Gesetz-vs-Hausregel-spezifisch |
| 5 | Nachschlagewerk als eigene Gattung | Ja, Trennung; Beleg-Nutzung nicht gefunden | Zotero-RAG, Wiki/Confluence-Spaces |
| 6 | Melder auf entstehende Arbeit (Code gegen Fehlerklassen) | Ja | Postmortem-zu-Lint-Praxis, dokumentiert (HN-Thread, Static-Analysis-Workflows) |

Datei: `/Volumes/daten/Begod2026/brainlehr/runs/wettbewerb_2026-08-09.md`
