# Prüfauftrag an Deep Research — 2026-08-09T10:40:00+0200

Zweck: eine eigene starke Behauptung widerlegen lassen, nicht bestätigen.
Behauptung (Claude Opus 5, brainlehr, 2026-08-09): *„Als Wissensspeicher, der
Verantwortung tragen soll, gibt es kein Vergleichsobjekt. Die Konkurrenz löst
'was wurde gesagt'. brainlehr löst 'was gilt, wer hat das entschieden, seit
wann, wie sicher, wie nehme ich es zurück'."*

Der Auftrag unten ist bewusst so geschrieben, dass ein Treffer die Behauptung
**kippt**. Wer nur bestätigende Quellen sucht, hat den Auftrag verfehlt.

---

## Prompt (zum Kopieren)

```
Ich prüfe eine Behauptung über den Stand der Technik bei KI-Gedächtnis- und
Wissensspeichersystemen. Deine Aufgabe ist es, sie zu WIDERLEGEN, nicht zu
bestätigen. Beginne mit der Annahme, dass sie falsch ist, und suche gezielt
nach Gegenbeispielen.

DIE BEHAUPTUNG:
"Es existiert kein Gedächtnis- oder Wissensspeichersystem für KI-Agenten, das
gleichzeitig alle folgenden sechs Eigenschaften auf Ebene der EINZELNEN
gespeicherten Aussage führt und im Abruf auch verwendet."

DIE SECHS EIGENSCHAFTEN (alle sechs müssen im selben System vorliegen):

1. HERKUNFT je Aussage: welcher Akteur, welches Modell, welche Sitzung, welcher
   Klient sie geschrieben hat, und aus welchem ANLASS (auf Anweisung eines
   Menschen vs. selbst beschlossen) — als abfragbare Felder, nicht als Freitext
   im Inhalt.

2. NORMATIVE GELTUNG: ein Rang, der ausdrückt, WER eine Regel erlassen hat
   (globale Hausregel vs. Projektentscheidung vs. Einzelfall), und eine
   getrennte Kategorie für die ART der Aussage (Tatsachenbeschreibung vs.
   Gebot vs. Erlaubnis). Bei Konflikt zwischen zwei gespeicherten Aussagen
   entscheidet das System anhand dieser Felder, welche vorgeht.

3. ZEITLICHE GELTUNG: gilt-ab und gilt-bis je Aussage, mit automatischer
   Meldung abgelaufener Regeln.
   (Hinweis: Zep/Graphiti hat bi-temporale Kanten. Prüfe, ob das die
   Anforderung erfüllt oder nur die Zeitachse ohne Normativität abbildet.)

4. BELEGRANG: eine Pflichtangabe, WIE GUT eine Aussage belegt ist — gemessen
   vs. aus fremdem Bericht übernommen vs. plausibel vs. geraten — plus eine
   Pflichtangabe, WAS ES KOSTET, wenn die Aussage falsch ist.

5. RÜCKNEHMBARKEIT MIT SPUR: eine Aussage kann zurückgezogen werden, wobei
   Grund, Zeitpunkt und zurückziehender Akteur erhalten bleiben und jede frühere
   Fassung nachlesbar bleibt. Reines Löschen (delete by id) erfüllt das NICHT.

6. SELBSTMESSUNG IM BETRIEB: das System meldet ungefragt eigene Mängel gegen
   die obigen Regeln — zum Beispiel "X Prozent der Regeln hat sich eine
   Maschine selbst gegeben, ohne dass ein Mensch zugestimmt hat" oder "ein
   gebautes Unterscheidungsmerkmal ist bei allen Datensätzen leer und damit
   wirkungslos". Ein Benchmark-Ergebnis in einem Paper erfüllt das NICHT —
   gefordert ist eine laufende Messung gegen den eigenen Produktivbestand.

SUCHE GEZIELT IN DIESEN RICHTUNGEN (die Behauptung könnte an jeder kippen):

a) Agenten-Gedächtnis: Mem0, Zep/Graphiti, Letta/MemGPT, LangMem, Cognee,
   MemoryOS, A-MEM, HippoRAG, MemGPT-Nachfolger, OpenAI/Anthropic/Google
   Memory-Funktionen. Was führen sie tatsächlich je Aussage?

b) Semantic Web / Provenance: PROV-O (W3C), Nanopublications, RDF-Reification,
   named graphs, PAV-Ontologie, Wikidata-Referenzen und -Ränge (deprecated/
   normal/preferred!), SHACL. Diese Welt kennt Herkunft seit Jahren — die
   entscheidende Frage ist, ob ein LAUFENDES SYSTEM für KI-Agenten sie
   einsetzt, nicht ob ein Standard existiert.

c) Deontische Logik und Regelmaschinen: Defeasible Logic, LegalRuleML,
   Rechtsinformatik-Systeme (Catala, Blawx, DAPRECO, Oracle Policy Automation),
   Business-Rule-Engines mit Prioritäten/Vorrangregeln. Bilden sie
   Sein/Sollen/Dürfen ab UND werden sie als Agentengedächtnis benutzt?

d) Argumentationssysteme und Belegqualität: Toulmin-Modell in Software,
   GRADE/Evidence-Level in medizinischen Wissensbanken, Bayesian Truth
   Serum, Belief-Revision-Systeme (AGM), Truth Maintenance Systems (JTMS/ATMS
   — die kannten Begründungsketten und Rücknahme schon in den 1980ern; laufen
   sie heute irgendwo als LLM-Gedächtnis?).

e) Betriebliche Datenverwaltung: Data Lineage (OpenLineage, Marquez),
   Data Contracts, Great Expectations, Feature Stores, Datenkataloge (DataHub,
   Amundsen, OpenMetadata), Bitemporal Databases (XTDB, Datomic).
   Führen sie Herkunft je ZEILE und melden sie eigene Regelverstöße?

f) Regulatorisch getriebene Systeme: EU AI Act Artikel 12 (Protokollierung),
   Artikel 13 (Transparenz), Medizin/Pharma-Wissensbanken mit Audit-Trail,
   Luft- und Raumfahrt (NASA Lessons Learned), FDA 21 CFR Part 11
   (elektronische Aufzeichnungen). Hier ist Nachweispflicht gesetzlich — gibt
   es dort ein KI-Wissenssystem, das die sechs Punkte erfüllt?

g) Wissenschaftliche Arbeiten 2023–2026 zu: "provenance-aware memory for LLM
   agents", "normative reasoning multi-agent memory", "epistemic status
   tracking language models", "self-auditing knowledge base", "retractable
   knowledge LLM", "confidence calibration knowledge graph agent".

LIEFERE:

1. Jedes System, das MEHR ALS DREI der sechs Punkte erfüllt — mit einer
   Tabelle System × sechs Punkte, jede Zelle belegt mit Dokumentationslink
   oder Quelltextstelle. Vermutungen ausdrücklich als solche kennzeichnen.

2. Den STÄRKSTEN Einzeltreffer: welches existierende System kommt der
   Behauptung am nächsten, und welche der sechs Punkte fehlen ihm genau?

3. Falls kein System alle sechs erfüllt: die Kombination aus zwei bis drei
   existierenden Bauteilen, mit der ein Fachmann das nachbauen würde — und wie
   lange das ungefähr dauern würde. Wenn die Antwort "in zwei Wochen aus
   fertigen Teilen" lautet, ist die Behauptung praktisch widerlegt, auch wenn
   heute niemand es gebaut hat.

4. Die gegenteilige Sicht, ernst genommen: Gibt es einen GUTEN GRUND, warum
   niemand das baut? Etwa dass Herkunftsfelder je Aussage sich in der Praxis
   als zu teuer erweisen, dass Nutzer sie nie pflegen, dass sie den Abruf
   verschlechtern, oder dass gescheiterte Vorläufer existieren (Semantic Web,
   Expertensysteme der 1980er, CYC). Nenne die Fehlschläge namentlich.

5. Ein klares Urteil in einem Satz: WIDERLEGT / TEILWEISE WIDERLEGT /
   NICHT WIDERLEGT — und bei "nicht widerlegt" ausdrücklich dazu, wie
   gründlich gesucht wurde und wo eine Lücke in der Suche bleiben könnte.

WAS ICH NICHT WILL:
- Keine Zusammenfassung, was RAG oder Vektordatenbanken sind.
- Keine Aufzählung von Systemen, die nur Punkt 1 oder nur Punkt 3 erfüllen,
  ohne Tabelle.
- Keine Marketing-Behauptungen von Anbieterseiten als Beleg für erfüllte
  Punkte — nur Dokumentation, Quelltext, Schema oder Paper.
- Keine Höflichkeit gegenüber meiner Behauptung. Sie ist stark formuliert und
  soll fallen, wenn sie fällt.
```

---

## Warum der Auftrag so gebaut ist

Drei Stellen, an denen er sich von einer Bestätigungssuche unterscheidet:

- **Er nennt die eigene These als zu widerlegende**, nicht als Suchrichtung.
  Hausregel: ein Auftrag lässt messen, nicht bestätigen.
- **Er nennt den stärksten bekannten Gegenkandidaten selbst** (Zep/Graphiti,
  bi-temporal) samt der Frage, ob das reicht. Wer den Gegner verschweigt,
  bekommt ihn nicht zu sehen.
- **Punkt 3 der Lieferung kippt die Behauptung auch ohne Fundstück**: Wenn
  sich das aus fertigen Teilen in zwei Wochen bauen lässt, ist „es gibt kein
  Vergleichsobjekt" praktisch wertlos, selbst wenn es stimmt.

Erwartung, damit sie prüfbar ist statt nachträglich angepasst: Punkte 1, 3 und
5 werden **je einzeln** irgendwo erfüllt sein (PROV-O, XTDB/Datomic, TMS).
Punkt 2 und 4 vermute ich nur in der Rechtsinformatik, dort aber ohne Bezug zu
Agentengedächtnis. Punkt 6 halte ich für den unwahrscheinlichsten. Fällt
Punkt 6 irgendwo, war meine Behauptung falsch.
