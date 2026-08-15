# ADR-022 — Der Orchestrierungsweg wird gezeichnet, und der Wissensabruf erreicht die Arbeiter

**Status:** angenommen
**Datum:** 2026-08-15T18:06:57+0200
**Entschieden von:** Betreiber („JA ADR!")
**Betrifft:** die Auftragsvergabe an Agenten, `haken/knowledge_recall_hook.py`, die Wissenserfassung
**Verwandt:** ADR-023 (Modell-Kaskade), ADR-024 (drei Wissensschichten), `L-229bb2`, `L-79ec88`

## Anlass

Ein Video vom 2026-08-15 („Die AI Bubble findet gerade Graphentheorie für sich",
The Morpheus Tutorials, 44:34) beschreibt **Harness Engineering**: den
Arbeitsablauf um ein Sprachmodell herum als Graphen aus Jobs und Übergängen.
Der Ton wurde lokal transkribiert (7132 Wörter), die Auswertung hält seine
Bauteile gegen die gemessene Arbeitsweise dieses Tages.

**Seine These, mit seinen Zahlen:** Im ARC-AGI-3-Benchmark stand ein Modell bei
7,8 % und dasselbe Modell mit angepasstem Harness bei knapp 40 % — vorbei am
Spitzenreiter mit 30,2 %. Ein anderes Modell gewann über 10 % im Terminal Bench,
nur weil jemand den Harness nachbesserte. **Modellvergleiche sagen wenig; das
Drumherum entscheidet.**

*Nebenbefund zur Quelle: Der Titel nennt Graphentheorie, der Inhalt ist Harness
Engineering — 26 Nennungen gegen 4. Der Graph kommt vor, aber als Ablaufdiagramm
für Agenten, nicht als Wissensgraph. Wer nur den Titel liest, bereitet sich auf
das falsche Thema vor; genau das ist hier zuerst passiert.*

## Der gemessene Ist-Stand dieses Tages

Rund zwanzig Agentenläufe. Was davon Harness war und nicht Modell:

| | |
|---|---|
| Agenten auf bereits Gebautes angesetzt | **5** (`97`, Dienststart, `H4`, `H5`, `H7`) — `L-229bb2` |
| Zahlen, die ein Agent mir korrigierte | **6**, alle zählbar gewesen |
| Mechanismen gebaut und ohne Auslöser | mehrfach, darunter die eigene Wache gegen `git stash` |
| Abrufwirkung | **11,1 %** (37 von 334) |
| Lehren ohne zuständigen Regelabschnitt | **490 von 572** |

Keine dieser Zahlen ist eine Aussage über ein Modell. Alle sind Aussagen über den
Ablauf drumherum — und der bestand aus dem Urteil des Orchestrators, aus dem Kopf.

## Entscheidung 1 — Die Existenzprobe ist ein Knoten, kein Vorsatz

Vor jedem Auftrag, der etwas BAUEN soll, steht eine Probe am Repo: existiert die
Sache schon? Gesucht wird nach der **Sache**, nicht nach der Kennung
(`git log --all --grep=`, `hub/scripts/symbolindex.py`).

**Warum als Knoten und nicht als Regel:** Sie stand heute als Lehre im Speicher,
nachdem sie dreimal aufgetreten war — und trat danach noch zweimal auf. Eine
Lehre ist ein Text; sie greift, wenn jemand sie liest. Fünf von zwanzig Läufen
sind eine Ausschussquote von einem Viertel, verursacht durch einen fehlenden
Schritt.

**Gerettet hat in allen fünf Fällen derselbe Satz im Auftrag:** *„Sieht der Code
anders aus als hier beschrieben, halte dich an den Code und melde die
Abweichung."* Er bleibt, er ist kein Beiwerk — aber er ist die Auffangnetz-Hälfte,
nicht die Vermeidungs-Hälfte.

## Entscheidung 2 — Das Quality Gate steht VOR der teuren Arbeit

Aus dem Video übernommen und in dieser Form neu: erst der billige
deterministische Schritt, dann das Modell. Er lässt Tests und Linter laufen,
bevor fünf Prüf-Agenten Token verbrauchen, und misst vorher, welche Tests schon
kaputt waren — sonst gilt Vorbestehendes als neu.

**Bei uns existieren die billigen Prüfer alle** — sie heißen `melder/` — und
hängen sämtlich **hinter** der Arbeit. Sie werden vorgezogen, wo es geht.

**Zweiter übernommener Punkt, gemessen von ihm:** Prüf-Agenten parallel statt
nacheinander, Unterschied Faktor 4. Der eigentliche Grund ist aber nicht die
Zeit: Nacheinander bekommt der Bauende je Runde nur EIN Urteil und baut danach
etwas, das der nächste Prüfer erneut beanstandet. Parallel bekommt er alle
Einwände auf denselben Stand.

## Entscheidung 3 — Der Wissensabruf erreicht die Arbeiter, nicht nur den Orchestrator

**Der schwerste Befund dieser Auswertung.** `haken/knowledge_recall_hook.py`
hängt ausschließlich an `UserPromptSubmit` — also nur, wenn ein Mensch etwas
eintippt. Auf `SubagentStart` liegt seit `d6ab2505` nur der *Auftrags*-Abruf.

**Folge, an diesem Tag: alle rund zwanzig Agenten arbeiteten ohne
Wissensabruf.** Der Speicher spricht mit dem Orchestrator und schweigt gegenüber
denen, die die Arbeit machen. Und genau dort traten die fünf Fälle „war schon
gebaut" auf, während das Wissen dazu im Speicher lag.

**Der Einwand dagegen ist gemessen und ernst:** Der Abruf kostet 6,0 Sekunden.
An jede Delegation gehängt wäre er eine Bremse — deshalb wurde er heute
ausdrücklich nicht verdrahtet, mit Vermerk. **Diese Entscheidung wird hiermit
nicht aufgehoben, sondern präzisiert:** Nicht der volle Abruf gehört an den
Agentenstart, sondern ein **verengter** — auf die Dateien und Kennungen des
Auftrags, nicht auf seinen ganzen Text. Was das kostet, ist zu messen, bevor es
verdrahtet wird. Ohne diese Messung bleibt es bei der heutigen Lage, und der
Vermerk gilt weiter.

## Entscheidung 4 — Ein Aggregator mit Schwelle statt Einzelfallurteil

Sein Controller sammelt die Urteile der Prüf-Agenten und entscheidet an einer
Schwelle („mindestens 12 von 13"). Bei uns entschied der Orchestrator jeden Fall
einzeln.

**Warum das zählt, und zwar messbar:** Sechsmal an diesem Tag hat ein Agent eine
Zahl korrigiert, die der Orchestrator behauptet hatte. Jedes Mal ging es gut —
weil der Agent aufmerksam war, nicht weil eine Stelle im Ablauf es erzwang. Ein
Verfahren, das auf der Aufmerksamkeit des Ausführenden beruht, ist kein
Verfahren.

## Was das für die WISSENSGENERIERUNG heißt

Die These „das Drumherum entscheidet" trifft die Wissensseite genauso — und dort
haben wir das Drumherum an der falschen Stelle angeschlossen.

**Wir erzeugen viel und es landet selten.** Heute 17 neue Einträge; die
Abrufwirkung liegt bei 11,1 %; 490 von 572 Lehren gehören keinem Regelabschnitt.
Das sind Harness-Zahlen, keine Modellzahlen.

**Die Erfassung braucht dasselbe Gate wie seine Prüf-Agenten.** Heute wird Wissen
hinterher aus dem Gedächtnis in ein Freitextfeld geschrieben. Ein billiger Schritt
davor — *welchem Arbeitsschritt gehört das? keinem → dann ist es eine Notiz und
kein Wissen* — senkt die Menge und hebt die Trefferquote. Gemessen: 45,1 % der
Lehren hängen an einem Schritt, 54,9 % an keinem.

**Und der Unterschied, der zu unseren Gunsten geht:** Für Code sagt ein Benchmark,
ob der Harness taugt. **Für Wissen gibt es keinen** — das Äquivalent ist, ob ein
Eintrag je wieder benutzt wird, und diese Rückmeldung dauert Wochen oder kommt
nie. Genau dafür entstand heute `melder/abrufwirkung.py` mit Verlauf und
Rücknahme. Damit existiert für ein Harness-Bauteil eine Zahl, die im Video für
seines fehlt.

## Was das Video NICHT behandelt, und wir schon

Er misst Harness-Güte am Benchmark-Ergebnis. Das setzt voraus, dass die Bauteile
überhaupt feuern.

An diesem Tag war die eigene Wache gegen `git stash` gebaut, geprüft und für
wirksam erklärt — und existierte in der Sitzung, in der praktisch die gesamte
Arbeit stattfand, **nie**: Ein Arbeitsbaum kopiert `.claude/` beim Anlegen und
danach nie wieder; der Baum entstand um 05:44, die Wache kam um 11:26. Zwei
Agenten brachen die Regel, beide meldeten es selbst.

**Ein Knoten, der auf dem Diagramm steht und nicht auslöst, ist die Fehlerklasse,
die ein Benchmark nicht findet** — er misst das Ergebnis, nicht die Wirksamkeit
der Teile. Das ist der Beitrag dieses Hauses zu seinem Thema.

## Was bewusst NICHT entschieden wird

- **Kein Ablauf-Rahmenwerk.** Der Graph wird gezeichnet und die vier
  Entscheidungen werden umgesetzt; ein Werkzeug, das ihn ausführt, ist nicht
  beschlossen. **Preis:** Der Ablauf bleibt vorerst eine Auflage an den
  Orchestrator, kein Zwang.
- **Keine Umstellung der Modellwahl.** Seine Agentenklassen decken sich mit
  ADR-023; die Messung Schätzung-gegen-Wirklichkeit läuft seit heute und hat drei
  Datenpunkte mit Abweichungen zwischen −34 % und +88 %. Zu wenig für eine
  Entscheidung.

## Woran sich Erfolg messen lässt

1. Ausschussquote „auf bereits Gebautes angesetzt" — heute 5 von 20.
2. Zahl der Zahlen, die ein Agent dem Orchestrator korrigieren muss — heute 6.
3. Anteil neuer Lehren mit zugeordnetem Arbeitsschritt — heute 45,1 %.
4. Abrufwirkung — heute 11,1 %, und ab der Verengung des Abrufs getrennt für
   Orchestrator und Agenten auszuweisen.

Alle vier sind heute erhoben und damit vergleichbar. Die vierte wird sich
verschieben, sobald die Verschmelzung der Suchkanäle geändert wird — dann sind
die heutigen Werte historisch und als solche zu kennzeichnen.

## Quelle

Transkript lokal erzeugt (`whisper.cpp`, Modell `medium`, deutsch) aus einer vom
Betreiber selbst beschafften Tondatei. Nicht im Repo abgelegt. Die Zahlen des
Videos sind wiedergegeben, wie sie dort genannt wurden, und **nicht
nachgeprüft** — sie stützen hier keine Entscheidung, sondern nur den Anlass.
