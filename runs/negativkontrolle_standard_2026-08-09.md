# Fehlerquote auf Negativkontrollen bei LLM-Richter-Messungen — Rechercheergebnis

Datum: 2026-08-09T00:00:00+0200 (Recherchezeitpunkt der Sitzung)

## Fragestellung

Ein Sprachmodell beurteilt, ob ein abgerufener Wissenseintrag bei einer Aufgabe geholfen hätte.
Zur Güteprüfung werden absichtlich falsche Paare (Aufgabe A + Antwort zu B) untergemischt.
Gesucht: eine belegte oder etablierte Grenze für die zulässige Fehlerquote auf solchen
Negativkontrollen, ab der die Richter-Messung als unbrauchbar zu verwerfen ist — und die
dafür üblichen Kennzahlen.

## Ergebnis vorab

**Es gibt in keinem der drei Suchräume eine feststehende, allgemein anerkannte Zahl für genau
diesen Fall** (LLM-Richter + konstruierte Negativkontrolle). Die Frage wird in der Literatur
anders behandelt, als in der Ausgangsfrage unterstellt: Statt einer festen Ausschluss-Schwelle
berichten die meisten Arbeiten die gemessene Fehlerquote deskriptiv (als Ergebnis, nicht als
Gütekriterium) oder umgehen das Problem, indem sie relative Rangfolgen statt absolute
Fehlerquoten bewerten. Nur ein Nachbarfeld — die Labordiagnostik — hat eine wirklich
statistisch hergeleitete Regel, und die ist an eine Vorlaufmessung gebunden, nicht an eine
geliehene Prozentzahl.

---

## Suchraum 1 — LLM-als-Richter-Literatur

**Gesucht:** Übereinstimmung mit menschlichem Urteil, Positionsverzerrung, Selbstbevorzugung,
Kalibrierung, bekannte Negativkontrollen/Ablenkungsdokumente.

Befunde:

- **Keine einheitliche Kennzahl, aber ein wiederkehrendes Begriffspaar:** False Positive Rate
  (FPR) und False Negative Rate (FNR) des Richters gegen eine menschliche Referenz. Konkrete
  gemessene Werte streuen stark nach Aufgabe:
  - Video-QA-Benchmark: FPR 1,5 % (Richter gilt als "sehr konservativ").
  - Legal-QA-Aufgabe: FP 0,90 % (bei TP 61,2 %, FN 10,8 %, TN 27,1 %).
  - HotPotQA (Gemma-2-27b): FPR 4 %, FNR 1 %.
  - Mathe-Bewertung (GPT-4o): FPR 0 %, FNR 10 %.
  - Gemini-1.5-Pro: FPR 4 %, FNR 0 %.
  - Sicherheitsbewertung: Verhältnis FP:FN ≈ 43:3 (~14:1), ausgesprochen konservativer
    Bias (Richter markiert eher zu oft als "unsicher").
  → Diese Zahlen sind **Messergebnisse einzelner Studien**, keine Akzeptanzschwellen. Keine der
  Quellen sagt "ab X % ist die Messung zu verwerfen".
- **Konstruierte Negativpaare als Validitätsprüfung sind belegte Praxis, aber ohne Zahl:**
  In RAG-Evaluationsarbeiten werden Frage, Antwort, Referenzantwort und Kontext absichtlich aus
  verschiedenen Datensätzen gemischt, um zu prüfen, ob der Richter falsche Antworten erkennt
  (genau das Verfahren aus der Ausgangsfrage). Die eingesehenen Arbeiten (u. a. GroUSE,
  RAGBench-Umfeld) beschreiben das Verfahren, geben aber in den online einsehbaren Auszügen
  **keine feste Fehlerquote als Ausschlusskriterium** an — die Prüfung wird durchgeführt, das
  Ergebnis wird berichtet, nicht gegen einen Schwellenwert freigegeben oder verworfen.
- **Kalibrierungsmaßstab aus einem Nachbarbereich, nicht aus der LLM-Richter-Literatur selbst:**
  Cohen's Kappa nach Landis & Koch (1977) — Skala 0–0,20 gering, 0,21–0,40 mäßig, 0,41–0,60
  moderat, 0,61–0,80 substanziell, 0,81–1,0 fast vollständig. Substanzielle Übereinstimmung
  (κ ≥ 0,61) wird oft als informelle Mindestschwelle für "brauchbare Übereinstimmung mit
  Menschen" zitiert. **Ausdrücklich als Faustregel zu kennzeichnen:** Landis und Koch selbst
  lieferten laut Sekundärliteratur keine Evidenz für ihre Einteilung, sie beruht auf
  persönlicher Einschätzung; manche klinischen Felder halten sie für zu lax (κ < 0,60 gilt dort
  bereits als unzureichend). Außerdem misst Kappa Mensch-Richter-Übereinstimmung auf echten
  Fällen, nicht die Fehlerquote auf absichtlich falschen Paaren — die Übertragung auf die
  gestellte Frage ist eine Analogie, kein Beleg.
- Bekannte Angriffsvektoren, die zeigen, dass die Frage in der Literatur ernst genommen wird:
  Positionsverzerrung ist systematisch nachgewiesen und nicht zufällig; "One Token to Fool
  LLM-as-a-Judge" zeigt, dass Richter durch triviale Textmanipulation getäuscht werden können.
  Auch das stützt eher "es braucht eine Validitätsprüfung" als "es gibt eine Zahl dafür".

**Einordnung:** Faustregel vorhanden (κ ≥ 0,61, mit Herkunftsvorbehalt), belegter Wert für die
konkrete Frage (Fehlerquote auf Negativkontrollen) **nicht** gefunden.

---

## Suchraum 2 — Informationsrückgewinnung (IR)

**Gesucht:** Prüfung mit absichtlich unpassenden Dokumenten; welche Fehlerquote gilt dort als
Ausschlusskriterium.

Befunde:

- **TREC-Pooling** behandelt nicht-beurteilte Dokumente standardmäßig als irrelevant — das ist
  strukturell das Gegenteil des gefragten Problems (dort wird eine fehlende Bewertung zur
  Negativ-Annahme, nicht eine Negativkontrolle zur Prüfung des Bewerters) und liefert keine
  Fehlerquoten-Schwelle.
- **Voorhees (2000), "Variation in Relevance Judgments and the Measurement of Retrieval
  Effectiveness":** Drei unabhängige menschliche Gutachter je TREC-4-Thema zeigen erhebliche
  Uneinigkeit in absoluten Relevanzurteilen. Praktische Obergrenze menschlicher Übereinstimmung
  liegt bei rund 65 % Precision bei 65 % Recall — Menschen selbst stimmen bei Relevanzurteilen
  nur begrenzt überein. **Trotzdem** bleiben Systemvergleiche (relative Rangfolgen zwischen
  Suchsystemen) stabil trotz dieser Uneinigkeit.
- **Konsequenz für die Methodik des Feldes:** IR akzeptiert seit Jahrzehnten hohe Uneinigkeit in
  Einzelurteilen, **weil die Zielgröße eine andere ist** — nicht "ist jedes einzelne Urteil
  richtig", sondern "bleibt die Rangfolge der verglichenen Systeme stabil". Eine feste
  Fehlerquoten-Schwelle für einzelne Relevanzurteile als Ausschlusskriterium wurde in der
  eingesehenen Literatur nicht gefunden — das Feld hat die Frage durch einen anderen Maßstab
  ersetzt, nicht durch eine Zahl beantwortet.

**Einordnung:** Keine Faustregel und kein belegter Wert für "Fehlerquote X ist Ausschluss".
Stattdessen ein **methodischer Ausweg**, der so in Suchraum 1 nicht auftaucht: Prüfe
Rangfolgen-/Entscheidungsstabilität statt Einzelfehlerquote, wenn Einzelurteile ohnehin verrauscht sind.

---

## Suchraum 3 — Diagnostik / Laborpraxis

**Gesucht:** Regel, wenn eine Negativkontrolle anschlägt.

Befunde:

- **Prinzip:** Eine Negativkontrolle, die anschlägt, entwertet laut Sekundärliteratur den
  gesamten Lauf ("compromised by a lack of specificity") — in der Diagnostik ist das Anschlagen
  einer Negativkontrolle in der Regel ein Hart-Kriterium für die einzelne Kontrolle, nicht
  gradualisiert.
- **Statistisch hergeleitete Schwellen existieren dort tatsächlich, aber sie werden aus der
  eigenen Rauschverteilung berechnet, nicht importiert:** Bei Schwellenwerten auf Basis von
  Standardabweichungen vom Negativkontroll-Mittelwert gilt: 3 SD → rechnerisch 0,3 % Chance auf
  einen falschen Ausreißer, 5 SD → < 1 : 1 000 000. Diese Prozentsätze sind **aus der
  gemessenen Streuung der jeweiligen eigenen Kontrollreihe abgeleitet**, nicht als
  Universalwert von außen übernommen.
- **Westgard-Multiregel-QC (klinische Chemie):** Die 1-2s-Regel (ein Kontrollwert außerhalb
  ±2 SD) ist ausdrücklich **kein** Ausschlusskriterium für sich allein — bei normalem Rauschen
  liegt ungefähr 1 von 20 guten Läufen ohnehin außerhalb dieser Grenze (reiner Zufallstreffer).
  Sie ist ein Warnsignal, das erst zusammen mit weiteren Regeln (2-2s, R-4s, 4-1s, 10-x) zu
  einer Ablehnung führt. Die Praxis kombiniert mehrere Regeln statt einer einzigen
  Prozent-Schwelle.

**Einordnung:** Das ist der einzige Suchraum mit einer **belegten, quantitativen Methode** —
aber die Methode ist ein *Verfahren zur Herleitung* einer Schwelle aus der eigenen
Grundrauschmessung (SD-basierte Kontrollkarten, Multiregel-Kombination), kein einzelner
importierbarer Prozentsatz. Der einzig konkret zitierbare Prozentsatz (1 in 20 bei 2 SD) ist
explizit *kein* Ausschlusswert, sondern der Erwartungswert für falsche Alarme bei normalem
Betrieb — er beschreibt, wie oft man selbst bei einwandfreiem System mit Fehlalarmen rechnen
muss, nicht, ab wann etwas kaputt ist.

---

## Faustregel vs. belegter Wert — Zusammenfassung

| Aussage | Status |
|---|---|
| κ ≥ 0,61 ("substanziell") als brauchbare Mensch-Richter-Übereinstimmung | Faustregel, Ursprung selbst unbelegt (Landis & Koch räumen fehlende Evidenz ein) |
| FPR-Werte 0–14 % in einzelnen LLM-Richter-Studien | Gemessene Einzelwerte, keine Schwelle |
| 65 %/65 % als Obergrenze menschlicher Relevanzübereinstimmung (Voorhees 2000) | Belegter empirischer Befund, aber keine Ausschluss-Schwelle für Richter |
| 3 SD → 0,3 %, 5 SD → <0,0001 % Fehlalarmquote | Belegte Formel, aber bezogen auf die *eigene* Rauschverteilung, nicht universell |
| 1-2s-Regel (1 von 20) | Belegter Erwartungswert für Fehlalarme bei intaktem System — ausdrücklich kein Ausschlusskriterium für sich allein |

---

## Vorschlag

**Vorschlag:** Keine geliehene Prozentzahl übernehmen — weder die 0,61-Kappa-Faustregel (falsche
Zielgröße: sie misst Mensch-Richter-Übereinstimmung auf echten Fällen, nicht Fehlerquote auf
konstruierten Negativpaaren) noch eine der 0–14 % FPR-Zahlen aus einzelnen LLM-Studien (aus
anderen Aufgaben, nicht übertragbar). Stattdessen das Verfahren aus der Diagnostik übernehmen,
nicht deren Zahl: Vor der eigentlichen Messung eine Vorlaufmessung mit z. B. 50–100 absichtlich
falschen Paaren fahren, die empirische Fehlerquote mit Konfidenzintervall (Wilson-Score wegen
kleiner Stichprobe) bestimmen, und die Ausschlussgrenze aus diesem eigenen Grundrauschen
ableiten statt aus der Literatur zu importieren. Begründung: Die Negativpaare sind per
Konstruktion eindeutig (Aufgabe A kann durch die Antwort zu einer fremden Aufgabe B nicht
sinnvoll geholfen worden sein) — das ist näher an einem Spezifikationstest mit bekanntem
Soll-Ergebnis (nahe 0 %) als an einem Feld mit echter Grenzfall-Uneinigkeit wie bei
IR-Relevanzurteilen. Ein pragmatischer Startwert für die erste Vorlaufmessung, ausdrücklich als
Faustregel ohne dedizierten Beleg: unter ~5 % Fehlerquote auf eindeutigen Negativpaaren als
Arbeitsschwelle, danach durch die eigene Vorlaufmessung ersetzen.

**Bedingung, unter der dieser Vorschlag falsch wäre:** Wenn die konstruierten Negativpaare nicht
eindeutig unähnlich sind — wenn also Aufgabe A und Aufgabe B thematisch so nahe beieinander
liegen, dass die Antwort zu B tatsächlich teilweise auch A hätte helfen können. Dann ist die
Analogie zum eindeutigen Spezifikationstest falsch, "richtig" ist nicht mehr eindeutig 0 %, und
es müsste stattdessen wie in der IR-Praxis (Suchraum 2) auf Rangfolgen-/Entscheidungsstabilität
statt auf eine absolute Fehlerquote geprüft werden.

---

## Rastervermerk je Suchraum

- **Suchraum 1 (LLM-als-Richter):** WebSearch zu "agreement with human judgment / position bias
  / calibration 2024", "negative control distractor false positive rate benchmark reliability",
  "RAG evaluator judge validity check mismatched context negative control"; WebFetch auf
  arxiv 2510.09738 ("Judge's Verdict") und arxiv 2409.06595 (GroUSE) — beide PDF-Extraktionen
  lieferten keine im Volltext auffindbaren Zahlenschwellen, nur Methodenbeschreibung.
  Keine Anbieterseite als Beleg verwendet.
- **Suchraum 2 (IR):** WebSearch zu "relevance judgment false positive rate irrelevant document
  pooling TREC" und gezielt zu Voorhees (2000)/TREC-Assessor-Übereinstimmung. Quelle: NIST-
  Publikationsseite und Sekundärzitate der Originalarbeit; Originalarbeit selbst nicht per
  Volltext-Fetch gegengelesen, nur über Suchergebnis-Zusammenfassungen mehrerer unabhängiger
  Treffer (NIST, ERIC, ACM, arXiv-Nachfolgearbeiten) abgeglichen.
- **Suchraum 3 (Diagnostik/Labor):** WebSearch zu "negative control assay acceptance criteria
  false positive rate laboratory diagnostics" und gezielt zu Westgard-Regeln/1-in-20. Quellen:
  westgard.com (Fachseite eines Praxisanbieters für Laborqualitätskontrolle — als Fachquelle,
  nicht als Werbetext für ein Produkt gewertet, da rein methodisch), NCBI/PMC-Artikel zu
  Immunhistochemie-Kontrollen. Keine Herstellerwerbung für ein Testkit als Beleg verwendet.
