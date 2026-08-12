# Wettbewerbscheck 2026-08-12 — zwei Raster statt eines

Anlass: `runs/wettbewerb_2026-08-09.md` suchte nur nach EIGENSCHAFTEN und übersah
zwei direkte Nachbarn im selben Feld (AgriciDaniel/claude-obsidian,
thedotmack/claude-mem) — Lehre L-402a51. Diese Erhebung fährt zwei Raster:
(1) Eigenschaft, (2) Gattung/Plattform samt Laienbegriffen. Frage ist **nicht**
Überlegenheit, sondern: was messen andere an sich selbst, was messen wir, und
stimmt „fast niemand nennt eine Zahl"?

## Rastervermerk — Suchraum, zuerst

**Indizes:**
- GitHub REST-Suche (`gh api search/repositories`, authentifiziert als `3lehr`) —
  Themen (`topic:`) und Stichwortsuche, sortiert nach Sternen.
- README-Volltext einzelner Treffer per `gh api repos/<owner>/<repo>/readme`,
  nach Kennzahlbegriffen durchsucht (accuracy, recall@, precision, benchmark,
  retrieval quality/score, LongMemEval, LoCoMo, F1, hit rate, %-Werte).
- WebSearch (zwei Anläufe) für die laienhafte, nicht-technische Such-Ecke
  („second brain app", „AI notes app 2026 comparison").

**Raster 1 — Eigenschaft** (Suchbegriffe): `topic:memory-layer`, `topic:llm-memory`,
`topic:agent-memory`, README-Grep nach Kennzahlbegriffen bei den Top-Treffern;
WebSearch `"second brain" AI app benchmark "recall@" OR "retrieval accuracy"
self-reported 2026`.

**Raster 2 — Gattung/Plattform** (GitHub-Topics, je sortiert nach Sternen, Top 8):
`second-brain`, `pkm`, `ai-notes`, `claude-memory`, `personal-knowledge-management`,
`ai-second-brain`, `memory-management`. Dazu Stichwortsuchen `second brain obsidian
claude`, `claude mem persistent context`, `topic:claude-code memory`. Laienbegriffe:
WebSearch `best AI notes app 2026 "second brain" comparison review`.

**Bewusst ausgelassen:**
- Keine Fachdatenbanken (ACM/IEEE), nur GitHub-API und WebSearch (google-artiger Index).
- README-Prüfung ist auf die README-Datei selbst begrenzt — nicht auf Wikis,
  verlinkte Blog-Posts, `docs/`-Ordner oder Closed-Source-Landingpages der
  reinen SaaS-Anbieter (Mem0, Zep — bereits in der Erhebung vom 2026-08-09
  behandelt, hier nicht erneut per README geprüft, da Closed-Source ohne
  GitHub-README-Konvention).
- Kein dritter Suchanlauf bei den WebSearch-Treffern (Listicle-Seiten wie
  Taskade/Buildin/Saner.AI/ContextBolt/Storyflow/NoteLyn wurden nicht einzeln
  per WebFetch geöffnet — Marketing-Listicles sind keine Primärquelle für
  Selbstmessung, nur Snippet-Text verwendet).
- Sterne-/Fork-Zahlen sind Momentaufnahmen von heute (2026-08-12); sie driften
  täglich (claude-obsidian z. B. 10.609 im Auftrag → 10.785 gemessen).

## Positivkontrolle — bestanden

Beide bekannten Nachbarn wurden über Raster 2 gefunden, nicht nur per Direktabruf:

| Name | Fundort (Raster 2) | Sterne (2026-08-12) | Forks | Letzte Bewegung | Lizenz |
|---|---|---|---|---|---|
| AgriciDaniel/claude-obsidian | `topic:second-brain`, `topic:pkm`, `topic:claude-memory`, `topic:ai-second-brain`, Stichwortsuche | 10.785 | 1.251 | 2026-08-01 | MIT |
| thedotmack/claude-mem | Direktabruf + Stichwortsuche `claude mem persistent context` (nicht unter eigenem Topic-Tag `claude-memory` gelistet — führt stattdessen `mem0`, `openmemory`, `supermemory` als Topics) | 90.510 | 7.891 | 2026-08-12 (heute) | Apache-2.0 |

Beide gefunden, Raster bestätigt funktionsfähig.

## Raster 1 — Eigenschaft: misst wer die eigene Abrufgüte?

Bestätigt und verschärft den Befund vom 2026-08-09: die Eigenschaft ist in der
**Infrastruktur-Memory-Branche** (nicht Consumer-Apps) laut, öffentlich und mit
Zahl versehen — deutlich mehr Anbieter als am 2026-08-09 gefunden:

| Projekt | Sterne | Zahl | Fundstelle |
|---|---|---|---|
| supermemoryai/supermemory | 28.876 | „#1 auf LongMemEval, LoCoMo, ConvoMem"; 95 % Recall@15 bei 99,4 % Kontextreduktion | README, Abschnitt „Benchmarks" |
| MemTensor/MemOS | 10.691 | LoCoMo 88,83; LongMemEval 89,20; „führt in OmniMemEval, 14 kommerzielle Produkte" | README, Abschnitt „Benchmarks" |
| maximem-ai/maximem_synap_sdk | 60 | LongMemEval 92 %, LoCoMo 93,2 % | README + verlinkter Blogpost |
| XortexAI/XMem | 233 | eigene LoCoMo- und LongMemEval-S-Tabellen gegen genannte Konkurrenten | README, Abschnitt „Benchmarks" |
| topoteretes/cognee | 29.972 | eigene CI-Benchmarks gegen BEAM-Langkontext-Test, Tabelle mit Vorgänger-SOTA | README, Abschnitt „Benchmarks" |

Das ist **kein neuer Nullbefund** — es bestätigt und verbreitert Eigenschaft 1
aus dem 2026-08-09-Befund (dort: Mem0, Zep). Fünf weitere, teils sehr populäre
Projekte tun dasselbe, lauter beworben als brainlehr.

**Layperson-Ecke (Consumer-„second brain"-Apps):** Die WebSearch-Listicle-Treffer
(Taskade, Buildin, Saner.AI, ContextBolt, Storyflow, NoteLyn — durchweg
SEO-/Affiliate-Charakter, schwache Quellen) nennen für Notion, Obsidian, Mem,
Tana, Logseq, NotebookLM **keine** Abrufgüte-Zahl — nur Feature-Vergleiche
(„beste für Recherche", „beste für Struktur"). Für diesen Ausschnitt (reine
Consumer-Notiz-Apps) hält die Vermutung „fast niemand nennt eine Zahl" —
aber diese Quellen sind Marketing-Listicles, keine Primärbelege, und daher nur
mit dieser Einschränkung verwendbar.

## Raster 2 — Gattung/Plattform: der eigentliche Befund

Hier liegt der wichtigste Fund der Erhebung, und er ist unbequem:

**eugeniughelbur/obsidian-second-brain** (3.969 ★, 497 Forks, MIT, zuletzt bewegt
2026-08-08) — gefunden unter `topic:second-brain`, `topic:claude-memory`,
`topic:ai-second-brain` und der Stichwortsuche „second brain obsidian claude".
Genau dieselbe Gattung wie brainlehrs nächstes Umfeld (persistentes Gedächtnis
für Claude Code, als Klartext/Markdown, kein SaaS). Das Projekt:

- führt einen eigenen Befehl `/obsidian-retrieval-eval`, der laut README
  „vault search quality -- recall@k + MRR on natural-language questions, with
  the concrete failures and ranked fixes" misst (README Zeile 304).
- veröffentlicht konkrete, im Repo nachvollziehbare Zahlen: „keyword recall@10
  1.0, paraphrased-question recall@10 77%, and non-English queries went from
  13% to 63% recall@5" gegen einen ~2.350-Notizen-Bestand (README Zeile 794).
- legt den Prüfkorpus offen: „a reproducible 300-note synthetic corpus and
  three query sets, so the search numbers are something you can run yourself
  rather than something this README claims" (README Zeile 872, verweist auf
  `scripts/eval/BENCHMARK.md` und `scripts/eval/BASELINE.md` im Repo).

Das ist die Eigenschaft „misst und veröffentlicht die eigene Abrufgüte" —
**innerhalb der engeren Gattung von brainlehr**, nicht nur in der weiteren
Infrastruktur-Branche, UND mit einem reproduzierbaren, im Repo liegenden
Prüfkorpus statt nur einer Marketing-Zahl. Das ist ein direkterer Treffer als
alles, was die Erhebung vom 2026-08-09 fand.

**Zweiter, schwächerer Fund:** huytieu/COG-second-brain (836 ★, MIT) nennt
„95%+ source accuracy" — aber das ist eine unbelegte Marketingzeile ohne
Methodik-Verweis, kein Prüfkorpus, keine Reproduzierbarkeit gefunden. Anderer
Belastbarkeitsgrad als eugeniughelbur.

**Die beiden bekannten Positivkontroll-Nachbarn selbst (claude-obsidian,
claude-mem):** README-Grep ergab **keinen** Treffer für Kennzahlbegriffe in
beiden READMEs — beide belegen KEINE eigene Abrufgüte-Messung in der README
(Umfang: nur README geprüft, siehe Grenzen oben — Wikis/verlinkte Docs nicht
durchsucht).

## Einordnung für die geplante Aussage

Die Behauptung „wir veröffentlichen ~20 % Abrufgüte, eine schwache Zahl, aber
fast niemand nennt überhaupt eine" hält in dieser Form **nicht mehr**:

1. In der Infrastruktur-Memory-Branche ist Selbstmessung + Veröffentlichung
   Standard und lauter als bei brainlehr (Raster 1, bereits am 2026-08-09
   bekannt, hier um fünf weitere Belege verbreitert).
2. Innerhalb der engeren Gattung „persistentes Klartext-Gedächtnis für
   Claude Code / second brain" gibt es mindestens einen direkten Nachbarn
   (eugeniughelbur/obsidian-second-brain), der genau das tut — mit
   reproduzierbarem Prüfkorpus im Repo, nicht nur einer Marketingzahl.

Was nach dieser Erhebung noch als Unterscheidungsmerkmal in Frage kommt (nicht
abschließend geprüft, nur als engere, ehrlichere Formulierung benennbar): eine
laufende Selbstmessung im echten Betrieb (nicht ein einmaliger Lauf gegen
einen synthetischen Prüfkorpus), mit Trennung von Treffer- und
Zeichenmengen-Anteil. Diese engere Formulierung wurde in dieser Erhebung nicht
gezielt gegen eugeniughelbur oder die Infrastruktur-Anbieter geprüft — dafür
bräuchte es einen dritten, gezielten Suchanlauf auf genau diese Unterscheidung.

## Kurzfassung — Tabelle aller in dieser Erhebung geprüften Nachbarn

| Name | Fundort/Raster | Sterne | Letzte Bewegung | Lizenz | Misst & veröffentlicht eigene Abrufgüte? |
|---|---|---|---|---|---|
| AgriciDaniel/claude-obsidian | R2 (Positivkontrolle) | 10.785 | 2026-08-01 | MIT | Nicht gefunden (nur README geprüft) |
| thedotmack/claude-mem | R2 (Positivkontrolle) | 90.510 | 2026-08-12 | Apache-2.0 | Nicht gefunden (nur README geprüft) |
| eugeniughelbur/obsidian-second-brain | R2 | 3.969 | 2026-08-08 | MIT | Ja — `/obsidian-retrieval-eval`, recall@k+MRR, reproduzierbarer 300-Notizen-Korpus im Repo |
| huytieu/COG-second-brain | R2 | 836 | 2026-08-07 | MIT | Teilweise — „95%+ source accuracy" genannt, keine Methodik/Korpus gefunden |
| supermemoryai/supermemory | R1/R2 | 28.876 | 2026-08-12 | MIT | Ja — LongMemEval/LoCoMo/ConvoMem, Tabelle im README |
| MemTensor/MemOS | R1/R2 | 10.691 | 2026-08-12 | Apache-2.0 | Ja — LoCoMo/LongMemEval-Tabelle im README |
| topoteretes/cognee | R1/R2 | 29.972 | 2026-08-12 | Apache-2.0 | Ja — eigene BEAM-CI-Benchmarks im README |
| maximem-ai/maximem_synap_sdk | R1 | 60 | 2026-08-10 | Apache-2.0 | Ja — LongMemEval/LoCoMo, README + Blogpost |
| XortexAI/XMem | R1 | 233 | 2026-06-03 | BSD-3-Clause | Ja — eigene Benchmark-Tabellen im README |
| khoj-ai/khoj | R2 | 36.461 | 2026-08-02 | AGPL-3.0 | Verweis auf externen Blogpost („excellent performance on modern retrieval and reasoning benchmarks"), keine Zahl im README selbst |
| breferrari/obsidian-mind | R2 | 4.326 | 2026-08-03 | MIT | Nicht gefunden (README-Grep: 0 Treffer) |
| reorproject/reor | R2 | 8.573 | 2025-05-13 (inaktiv) | AGPL-3.0 | Nicht gefunden (README-Grep: 0 Treffer) |
| Consumer-Apps (Notion, Obsidian, Mem, Tana, Logseq, NotebookLM) | R1 (Laienbegriffe) | — | — | — | Nicht gefunden in Listicle-Snippets (schwache Quelle, nur Feature-Vergleiche) |

Datei: `/Volumes/daten/Begod2026/brainlehr/runs/wettbewerb_2026-08-12.md`
