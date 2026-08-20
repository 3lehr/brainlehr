# Konsil: Psychometrie

Stand 2026-08-20T14:15:00+0200. Rolle: Item-Response-Theorie, Testkonstruktion,
DIF, Reliabilität, Validität. Material: `runs/konsil_zweites_signal_material.md`.
Keine andere Rolle bekannt, keine Absprache.

Kennzeichnung durchgängig: **[E]** etabliert in meinem Fach, mit Namen ·
**[Ü]** meine Übertragung auf diesen Fall, Hypothese · **[V]** reine
Vermutung. Alle Rechnungen unten sind aus den Zahlen des Materials abgeleitet
und als Rechnung ausgewiesen; ich habe nichts gemessen.

---

## 1. Übersetzung: Item, Person, latente Fähigkeit

**[Ü] Die naheliegende Zuordnung:**

| Psychometrie | hier |
|---|---|
| Item | eine Anfrage des Prüfkorpus |
| Antwortverhalten | geliefert/geschwiegen, richtig/falsch |
| Person | eine Betriebsart (B, C, Schwellenschicht) |
| latente Fähigkeit θ | Abrufgüte des Systems |
| Item-Schwierigkeit β | wie schwer diese Anfrage zu bedienen ist |

**Der Kern meines Fachs ist genau diese Zerlegung.** Ein beobachteter
Rohwert ist immer ein Produkt aus beidem. **[E]** Rasch (1960) nennt die
Eigenschaft, die das möglich macht, *spezifische Objektivität*: im
1PL-Modell ist der Vergleich zweier Personen unabhängig davon, welche Items
verwendet wurden, und der Vergleich zweier Items unabhängig davon, welche
Personen sie bearbeitet haben. Das ist keine Feinheit, das ist der ganze
Grund, warum es das Modell gibt. Ein Rohwert („15 von 35") besitzt diese
Eigenschaft nicht — er ist eine Aussage über *Test und System zusammen*.

**Wo die Übersetzung nicht trägt — vier Stellen, und die ersten beiden sind
gravierend:**

1. **Es gibt nur drei Personen.** **[E]** Item-Parameter werden aus der
   Streuung über Personen geschätzt. Faustregeln für stabile
   Rasch-Item-Kalibrierung liegen bei mehreren hundert Personen pro Item
   (**[V]** Größenordnung, je nach Quelle 100–500). Mit n=3 ist keine
   Item-Kalibrierung möglich — nicht ungenau, sondern nicht definiert. Das
   ist der zentrale Engpass, und Abschnitt 4 dreht sich um seine Behebung.
2. **Die drei Personen sind nicht gezogen, sondern geschachtelt.** C ist B
   plus ein Schalter, die Schwellenschicht ist eine dritte Verdrahtung
   derselben Maschine. **[E]** Das Personenmodell setzt eine Zufallsstichprobe
   aus einer Population voraus; hier liegt ein Messwiederholungsdesign an
   *einem* Objekt vor. Formal ist das eher ein Within-Design (→ Abschnitt 4,
   Verfahren 3) als eine Personenstichprobe.
3. **Lokale stochastische Unabhängigkeit ist verletzt.** **[E]** Alle
   IRT-Modelle setzen voraus, dass Items bei gegebenem θ unabhängig sind.
   Hier teilen sich alle Items denselben Bestand: fehlt ein Eintrag, fallen
   alle Anfragen aus, die auf ihn zielen. **[E]** Wainer & Kiely (1987) nennen
   solche Bündel *Testlets*; unbehandelt überschätzen sie die Reliabilität.
   **[Ü]** Bei 45 Items gegen 5200 Einträge dürfte das mild sein, im
   12000er-Bestand wird es relevant und ist dort messbar.
4. **θ ist nicht stabil.** Der Bestand wächst zwischen den Items. **[E]** Eine
   Person, deren Fähigkeit sich während des Tests ändert, verletzt das Modell.
   **[Ü]** Praktische Folge, unabhängig von allem anderen: **jeder Messlauf
   braucht einen eingefrorenen Bestandsschnappschuss mit Kennung**, sonst ist
   die Skala nicht verankert und zwei Läufe sind nicht vergleichbar.

**[Ü] Die Übersetzung, die besser trägt, ist eine andere:** Nicht die
Betriebsart ist die Person, sondern **jede Parametrisierung des Systems**.
Fusionsgewicht, Kanalgewichte, Schwellen, Top-k, Zerlegungsgröße,
Anfrageerweiterung — jede Kombination ist ein Prüfling. Damit ist die
Personenzahl frei wählbar, und die Item-Kalibrierung wird möglich. Das ist der
eine Griff, an dem in meinem Fach alles hängt.

---

## 2. Der Prüfkorpus als Testinstrument

Ich beurteile ihn wie eine Testvorlage, die zur Begutachtung eingereicht
wurde. Sieben Beanstandungen, nach Schwere.

### 2.1 Zwanzig Items ohne Varianz — der schwerste Mangel

**[E]** Ein Item, das *niemand* löst, heißt in der klassischen Testtheorie
ein Item mit **Schwierigkeitsindex p = 0**. Seine
**Trennschärfe** — punktbiseriale Korrelation mit dem Gesamtwert — ist
rechnerisch **null bzw. undefiniert**, weil es keine Varianz hat. In der IRT
ist es ein *extremes Item*: seine Schwierigkeit β geht gegen +∞, JMLE und CMLE
können es nicht schätzen, und alle gängigen Verfahren (Winsteps, ConQuest,
mirt) **entfernen es vor der Kalibrierung**. Die Konsequenz ist in meinem Fach
seit Jahrzehnten unstrittig: **ein solches Item trägt null Information und
gehört aus dem Test entfernt oder durch ein leichteres ersetzt.**

Angewandt: **20 der 35 lösbaren Items werden von keiner Betriebsart gelöst.**
Rechnet man das eine Item hinzu, das *alle drei* lösen („B trifft, C trifft",
n=1), sind **mindestens 20, wahrscheinlich 21 der 45 Items über die drei
geprüften Betriebsarten ohne Varianz** — sie können sich nicht bewegen,
gleichgültig was am System geändert wird.

**Die effektive Testlänge beträgt damit rund 24 Items, nicht 45.** Und von
diesen 24 trennen 14 ausschließlich B von C entlang des einen Schalters. Was
der Korpus heute wirklich misst, ist im Wesentlichen: *ist die
Ensemble-Pflicht eingeschaltet?* Das ist eine binäre Konfigurationsauskunft,
keine Fähigkeitsmessung.

**[E] Testinformationsfunktion.** Ein Test misst nur dort präzise, wo seine
Items liegen. Liegen fast alle Items weit über der Fähigkeit des Prüflings,
entsteht ein **Bodeneffekt** (floor effect): der Standardfehler der
Fähigkeitsschätzung explodiert genau in dem Bereich, in dem gemessen werden
soll. Genau das liegt hier vor. **[Ü]** Der Korpus ist für dieses System zu
schwer — nicht in dem Sinn, dass er unrealistisch wäre (die 6,7 % Median-
Wortüberlappung im Betriebsprotokoll belegen das Gegenteil), sondern in dem
Sinn, dass er **an der falschen Stelle der Skala misst**.

### 2.2 Der Test ist zu kurz, und das lässt sich beziffern

**[E]** Standardfehler eines Anteils: SE = √(p(1−p)/n).

Für die 35 lösbaren Items bei p = 15/35 = 0,4286:
SE = √(0,4286 · 0,5714 / 35) = **0,084**, 95-%-Intervall ≈ **±0,16**,
also **±16 Prozentpunkte** bzw. **±5,7 Items**.

**Praktische Folge:** 15/35 und 20/35 sind mit diesem Korpus **nicht
unterscheidbar**. Eine Systemänderung, die fünf zusätzliche Fälle löst, ist
statistisch nicht von Rauschen zu trennen. Das ist eine harte Grenze der
Aussagekraft, nicht eine Feinheit.

Für die 10 Schweige-Items: **[E]** *Regel der Drei* (Hanley &
Lippman-Hand, 1983) — bei null beobachteten Fehlern in n Versuchen liegt die
obere 95-%-Grenze der wahren Fehlerrate bei 3/n. Hier: 3/10 = **30 %**.

**„10 von 10 richtig geschwiegen" ist vereinbar mit einer wahren
Ablehnungsleistung von 70 %.** Der einzige Wert, in dem C und die
Schwellenschicht perfekt aussehen, ist der am schwächsten belegte des ganzen
Berichts.

### 2.3 Der Test misst zwei Konstrukte und darf nicht summiert werden

**[E]** 35 Items „finde das Richtige" und 10 Items „erkenne, dass nichts da
ist" sind **zwei Dimensionen**. Eindimensionalität ist Voraussetzung jeder
IRT-Skalierung und Bedingung dafür, dass ein Summenwert interpretierbar ist.
Ein Summenwert über zwei Dimensionen ist in meinem Fach kein schwacher Wert,
sondern **kein Wert**.

Die Kreuztabelle zeigt es unmittelbar: C ist auf Dimension 2 am oberen
Anschlag (10/10) und auf Dimension 1 am unteren (1/35). Jede Zahl, die beides
zusammenfasst, verwischt genau den Unterschied, um den es geht.

**[Ü] Verbindlicher Rat, kostenlos umsetzbar:** Abrufgüte und
Ablehnungsgüte werden **immer als Paar berichtet, nie als eine Zahl**, und
jede Zahl trägt ihr Konfidenzintervall mit. Das ist keine Analyse, das ist
eine Berichtsform.

### 2.4 Der Lösungsschlüssel ist nachweislich falsch — bei ~7 % der Items

Die Handnachsicht ergab **3 Fälle „brauchbar, nur anders"**. Das sind in
meiner Sprache **Schlüsselfehler** (mis-keyed items): der Test bewertet eine
richtige Antwort als falsch, weil der Schlüssel exakte Kennungen prüft statt
Sachrichtigkeit.

**[E]** Ein mis-keyed Item bekommt typischerweise eine **negative
Trennschärfe** — die fähigeren Prüflinge fallen häufiger durch. Es ist damit
schlimmer als ein wertloses Item: es zieht den Gesamtwert in die falsche
Richtung. Standardverfahren ist die **Distraktorenanalyse** und die Korrektur
oder Streichung des Items vor jeder weiteren Auswertung.

3 von 45 ≈ **6,7 % Schlüsselfehler**, entdeckt bei einer Durchsicht von nur
20 Fällen. **[V]** Die Rate unter den 25 nicht von Hand nachgesehenen Fällen
ist unbekannt; dass sie null ist, wäre eine Annahme ohne Grundlage.

**[E] Konsequenz für jede Korrelation, die gegen dieses Kriterium gerechnet
wird — und das schließt das τ = 0,10 ein:** *Attenuation durch
Kriteriumsunreliabilität* (Spearman 1904). Die Obergrenze einer
beobachtbaren Korrelation ist r_max = √(r_xx · r_yy). Ist die Reliabilität
des Kriteriums 0,8, liegt die Obergrenze bei √0,8 ≈ 0,89 der wahren
Korrelation; ist sie 0,5, bei ≈ 0,71. **[Ü]** Bevor jemand aus „τ = 0,10"
schließt, das Signal sei schwach, muss die Reliabilität des Kriteriums
bekannt sein. Solange sie unbekannt ist, ist auch unbekannt, wie viel des
niedrigen τ auf den Prädiktor entfällt und wie viel auf den Schlüssel.

### 2.5 Dichotome Bewertung wirft vorhandene Information weg

Die Handnachsicht liefert bereits eine geordnete vierstufige Bewertung:
brauchbar (3) · teilweise (12) · daneben (5) · Ziel strittig (0).

**[E]** Masters' **Partial Credit Model** (1982) und allgemein polytome
Items: eine geordnete Mehrstufenbewertung trägt **mehr Information pro Item**
als eine dichotome. Bei einem Test, der ohnehin an Kürze leidet, ist das der
billigste verfügbare Gewinn — dieselben 45 Fälle, mehr Information, kein
zusätzlicher Lauf.

**[Ü]** Konkret: Bewertung 3 = beantwortet die Frage · 2 = berührt sie
nützlich · 1 = berührt sie nutzlos · 0 = daneben. Damit werden die 12
„teilweise"-Fälle sichtbar, die heute mit den 5 echten Ausfällen in einem
Topf liegen — obwohl das Material selbst feststellt, dass das die
interessanteste Gruppe ist.

### 2.6 Item-Auswahl ohne dokumentiertes Verfahren

**[Ü]** Aus dem Material geht nicht hervor, nach welchem Verfahren die 45
Fälle gezogen wurden. **[E]** Bei jeder Testvorlage ist die
**Blueprint-Frage** die erste: welche Inhaltsbereiche in welchem Anteil,
nach welchem Kriterium, gezogen von wem. Ohne sie ist **Inhaltsvalidität**
nicht beurteilbar — und Inhaltsvalidität ist kein Nebenaspekt, sondern die
Grundlage, auf der man einen Test überhaupt für ein Konstrukt verwenden darf.

Der 12000er-Bestand macht das lösbar: aus ihm lässt sich nach einem
niedergeschriebenen Bauplan ziehen. Aus 45 handverlesenen Fällen nicht.

### 2.7 Kein Außenkriterium

**[E]** Kriteriumsvalidität verlangt einen Maßstab, der **nicht aus dem Test
selbst** stammt. Alle 45 Items sind gegen den eigenen Bestand geschlüsselt.
Der Test kann deshalb per Konstruktion nicht die Frage beantworten, die für
den Nutzen entscheidend ist: *deckt der Bestand ab, was die Nutzer wirklich
fragen?* Das Betriebsprotokoll mit 3759 bzw. 21 000 Zugriffen ist die
naheliegende Quelle für ein solches Kriterium und wird bisher nur zur
Plausibilisierung der Wortüberlappung herangezogen.

---

## 3. Was die Anfragegüte-Vorhersage übersieht

**[Ü] Der Einwand meines Fachs in einem Satz:** QPP korreliert einen
Prädiktor mit der beobachteten Güte **über Anfragen hinweg, bei einem
festgehaltenen System**. Eine Korrelation über Items bei fixierter Person ist
in meiner Sprache keine Vorhersage der Leistung — es ist eine **Schätzung der
Item-Schwierigkeit**, verwechselt mit einer Fähigkeitsaussage. Das erklärt
drei Dinge auf einmal:

**Erstens, warum die Werte niedrig bleiben und trotzdem alles korrekt
gerechnet ist.** Die beobachtete Antwort ist eine Funktion von β **und** θ.
Ein Prädiktor, der ausschließlich Merkmale des Items sieht (der Kosinuswert
ist ein Merkmal der Anfrage-Bestand-Konstellation, nicht des
Auswahlverhaltens), kann bestenfalls den β-Anteil erklären. Der θ-Anteil ist
für ihn Rauschen. **[Ü]** τ = 0,10 ist unter dieser Lesart kein Beleg für
ein schwaches Signal, sondern der zu erwartende Wert, wenn eine von zwei
Varianzquellen prinzipiell unerreichbar ist.

**Zweitens, warum QPP-Prädiktoren notorisch nicht übertragbar sind.** Ein
Prädiktor, der auf System A kalibriert wurde, enthält dessen θ implizit; auf
System B ist er falsch. **[E]** Das ist exakt das Problem, gegen das die
Rasch-Familie mit spezifischer Objektivität antritt.

**Drittens — und das ist der Befund, der hier schon im Material steht:**
Die Zahlen belegen, dass der Kosinuswert ein **valider Indikator für eine
Dimension und ein invalider für eine andere** ist.

| Dimension | Frage | trennt der Kosinus? |
|---|---|---|
| **Deckung** | Liegt überhaupt etwas Passendes im Bestand? | **ja**, Schwelle 0,545 fehlerfrei über 24 Fälle |
| **Passung** | Ist das Gelieferte die richtige Antwort? | **nein**, Mediane 0,635/0,593/0,597 liegen ununterscheidbar |

**[Ü]** Das ist kein schwacher Prädiktor. Das ist ein **starker Prädiktor für
das falsche Konstrukt**. Der Satz im Material — „sagt zuverlässig, ob etwas
Passendes im Bestand liegt; sagt nichts darüber, ob das Gelieferte richtig
ist" — ist eine lehrbuchreife Beschreibung **diskriminanter Validität**: das
Maß korreliert hoch mit dem, was es messen soll (Deckung), und darf gerade
deshalb nicht für ein anderes Konstrukt (Passung) eingesetzt werden.

**Praktische Folge, und sie ist die wichtigste Aussage dieser Stellungnahme:**
Es gibt keinen einen Güteprädiktor zu bauen. Es gibt **zwei getrennte
Entscheidungen**, und sie brauchen **zwei getrennte Signale**:

- **Deckung** → der Kosinus taugt bereits; die Schwellenschicht ist genau
  dieser Entwurf und in den Zahlen dominiert sie B strikt (siehe 3.1).
- **Passung** → braucht ein Signal aus der Beziehung *Anfrage ↔ ausgeliefertem
  Text*, nicht aus dem Rangwert. Der Rangwert ist bereits durch die Auswahl
  maximiert; **[E]** ein Kriterium, nach dem selektiert wurde, verliert seine
  Trennkraft in der selektierten Gruppe (*Varianzeinschränkung*, restriction
  of range — Thorndike 1949). Der beste Kosinus **ist** das
  Selektionskriterium. Dass er innerhalb der ausgewählten Menge nicht mehr
  trennt, ist keine Überraschung, sondern die vorhersagbare Folge der
  Selektion. **[Ü] Das allein erklärt einen erheblichen Teil des τ = 0,10 der
  Literatur, und ich habe in dem Material keinen Hinweis darauf gefunden, dass
  das Fach diesen Effekt korrigiert.**

### 3.1 Zur offenen Kostenfrage (Randbedingung 5) — sie ist rechnerisch klein

**[E]** Die Festlegung eines Cut-Scores ist in meinem Fach **keine empirische,
sondern eine Wertentscheidung**; Standard-Setting-Verfahren (Angoff 1971,
Nedelsky, Bookmark) machen sie nur nachvollziehbar. Die Empirie liefert die
Kurve, der Betreiber liefert die Steigung. **[E]** Der Rahmen dafür ist die
Entscheidungstheorie der Testverwendung (Taylor & Russell 1939): Nutzen =
Trefferwert × Treffer − Fehlerkosten × Fehler.

Rechnung aus den Zahlen des Materials, mit G = Wert einer richtigen
Einspielung und V = Kosten einer falschen:

- **B wird von der Schwellenschicht strikt dominiert.** Gleiche Trefferzahl
  (15), 10 Falschlieferungen weniger, kein Nachteil. B ist ohne jedes
  Kostenmodell aus dem Rennen. **[E]** Dominanz vor Gewichtung — das ist
  der erste Schritt jeder Entscheidungsanalyse.
- **C gegen Schwellenschicht:** Δ = 14 G − 20 V. Die Schwellenschicht ist
  besser, sobald **V/G < 0,7**.

**Die offene Konsilfrage reduziert sich damit auf einen einzigen Satz, den
der Betreiber beantworten kann:** *Ist eine irreführende Einspielung mehr
oder weniger schädlich als 0,7 hilfreiche Einspielungen nützlich sind?*

**[Ü]** Und die Handnachsicht verschiebt die Grenze weiter zugunsten der
Schwellenschicht: von den 20 Falschlieferungen sind 3 in Wahrheit Treffer
(Schlüsselfehler) und 12 „thematisch nah, sachlich nutzlos" — deren Schaden
ist plausibel geringer als der von 5 echten Ausfällen. Rechnet man die 3 als
Treffer, lautet die Bedingung 17 G > 17 V, also **V/G < 1,0**. **[V]** Nur
wenn eine irreführende Einspielung *teurer* ist als eine richtige wertvoll,
gewinnt der heutige Auslieferungszustand — und dafür sehe ich in dem
Material keinen Beleg, nur eine ungestellte Frage.

### 3.2 Lassen sich Item-Parameter für Anfragen schätzen?

**[Ü] Ja — sobald es genug Prüflinge gibt, und die lassen sich erzeugen.**
Der Engpass ist nicht die Anfragezahl (12 000 liegen vor), sondern die
Personenzahl (drei). Jede Parametrisierung des Abrufs ist ein Prüfling; das
Erzeugen von 100–300 Varianten ist Arithmetik über bereits berechneten
Einbettungen, kein Modellaufruf. Damit ist das Datenmuster hergestellt, für
das die Rasch-Familie gebaut wurde. Das ist Verfahren 1.

---

## 4. Vier Verfahren

Alle vier respektieren die Randbedingungen: kein Modellaufruf pro Anfrage,
alles lokal, höchstens ein zweiter Lauf im Betrieb. Die Kalibrierung selbst
läuft **offline und einmalig** — sie kostet im Betrieb nichts.

### Verfahren 1 — Kalibrierung über viele Systemvarianten (Rasch / 1PL)

**[E] Kernidee.** Erzeuge 100–300 Abrufvarianten durch systematische
Variation von Fusionsgewicht, Kanalgewichten, Top-k, Zerlegungsgröße,
Schwellen. Jede Variante ist eine Person, jede der 12 000 Anfragen ein Item;
das Ergebnis ist eine Personen-mal-Item-Matrix. Das Rasch-Modell schätzt
daraus **Item-Schwierigkeit β und System-Fähigkeit θ auf einer gemeinsamen
Logit-Skala**, und wegen spezifischer Objektivität ist β von der Wahl der
Varianten unabhängig.

**Daten.** 12 000er-Korpus mit Schlüssel · Variantengenerator · eingefrorener
Bestandsschnappschuss.

**Kosten. [V]** Größenordnungsschätzung, nicht gemessen: 12 000 × 200 ≈ 2,4
Mio Abrufe. Die Einbettungen existieren bereits; teuer wäre nur ihre
Neuberechnung, und die entfällt. Was bleibt, sind Kosinus, bm25 und Fusion —
Arithmetik. Ich schätze Stunden bis wenige Tage auf einem Gerät, plus
Speicher für die Matrix. Im Betrieb: null.

**Prüfung.** **[E]** Drei Standardproben, alle drei sind rot-vor-grün-fähig:
1. **Split-Half über Varianten** — β aus Variantenhälfte A gegen β aus
   Hälfte B. Bei Modellpassung ist eine hohe Korrelation zu erwarten
   (**[V]** Größenordnung r > 0,9); bricht sie ein, ist die
   Eindimensionalitätsannahme verletzt und das Ergebnis ungültig.
2. **Infit/Outfit-MNSQ** je Item (**[E]** Wright & Linacre 1994, üblicher
   Akzeptanzbereich ca. 0,5–1,5). Items außerhalb passen nicht auf die
   Dimension — genau die sind der interessante Befund, nicht der Ausschuss.
3. **Vorhersageprobe:** β aus Varianten 1–150 schätzen, dann das Verhalten
   von Variante 151 vorhersagen und gegen die Messung halten.

**Was das liefert, was 45 Fälle nicht liefern:** eine
**systemunabhängige Schwierigkeitsskala**. Erst damit ist der Satz „das
System ist besser geworden" von „der Korpus war leichter" trennbar. Das ist
genau die Trennung, die dieses Haus schon einmal gebraucht hat.

### Verfahren 2 — Schwierigkeit vorhersagen, ohne den Fall je gelaufen zu sein (LLTM)

**[E] Kernidee.** Das **Linear Logistic Test Model** (Fischer 1973) zerlegt
die Item-Schwierigkeit in beobachtbare Item-Merkmale: β_i = Σ q_ik · η_k. Man
schätzt einmal die Gewichte η der Merkmale und kann danach die Schwierigkeit
einer **nie gelaufenen** Anfrage vorhersagen. Das ist derselbe Zweck, den QPP
verfolgt — aber gegen ein sauber getrenntes Ziel (Schwierigkeit) statt gegen
ein vermengtes (Güte).

**Daten.** β aus Verfahren 1 · je Anfrage ein Merkmalsvektor. **[Ü]**
Kandidatenmerkmale, alle ohne Modellaufruf berechenbar: Wortüberlappung,
Anfragelänge, IDF-Profil der Begriffe, Zahl der Bestandseinträge im
Kosinusband oberhalb der Schwelle, Nachbarschaftsdichte der Anfrage im
Einbettungsraum, Sachgebiet, Alter des nächstliegenden Eintrags.

**Kosten.** Gering — eine logistische Regression über bereits vorliegende
Größen. Im Betrieb ein Skalarprodukt, also praktisch null.

**Prüfung.** Kreuzvalidierung über Anfragen, die in der Kalibrierung nie
vorkamen. **[E]** Zusätzlich der Likelihood-Ratio-Test LLTM gegen Rasch: er
sagt, welcher Anteil der Schwierigkeitsvarianz durch die Merkmale erklärt
wird. **[V]** In der Praxis meines Fachs liegt dieser Anteil oft bei 0,4–0,7;
für diesen Fall ist er unbekannt.

**Der eigentliche Nutzen ist ein anderer als erwartet:** Wenn die Merkmale die
Schwierigkeit gut erklären, weiß man **warum** eine Anfrage schwer ist — und
kann am Bestand arbeiten statt am Abruf. Ein QPP-Wert sagt nur *dass*.

### Verfahren 3 — Generalisierbarkeitsstudie: wie viel der Zahl beschreibt den Korpus?

**[E] Kernidee.** Die **Generalisierbarkeitstheorie** (Cronbach, Gleser, Nanda
& Rajaratnam 1972) zerlegt die Ergebnisvarianz per Zufallseffekt-Modell in
ihre Quellen: Anfrage, Betriebsart, Sachgebiet, Bewertungsstufe und deren
Wechselwirkungen. Sie beantwortet unmittelbar die Frage, die dieses Haus
schon einmal teuer gelernt hat: **welcher Anteil der berichteten Zahl ist eine
Eigenschaft des Systems und welcher eine Eigenschaft des Prüfkorpus?**

**Daten.** Der 12 000er-Korpus, gekreuzt über wenige Betriebsarten, mit
Gebietsmarkierung und der vierstufigen Bewertung aus 2.5.

**Kosten.** Klein. Ein Varianzkomponentenmodell; die Läufe sind ein Teilmenge
der Läufe aus Verfahren 1.

**Prüfung.** **[E]** Die daran anschließende **D-Studie** (Entscheidungsstudie)
rechnet aus, **wie viele Items für einen Generalisierbarkeitskoeffizienten von
0,8 nötig wären**. Das ist die direkte, quantitative Antwort auf „reichen 45?",
und sie ist mit vorhandenen Daten in wenigen Stunden zu haben.
**[V] Meine Erwartung, ausdrücklich ungeprüft:** die nötige Zahl liegt
deutlich über 45; wenn nicht, ist das der überraschendste Befund des ganzen
Konsils und muss selbst nachgeprüft werden.

**Dieses Verfahren würde ich zuerst fahren.** Es ist das billigste, es braucht
keine neue Modellklasse, und es entscheidet, ob sich der Aufwand für
Verfahren 1 überhaupt lohnt.

### Verfahren 4 — DIF über Sachgebiete

**[E] Kernidee.** **Differential Item Functioning** (Mantel-Haenszel-Verfahren,
Holland & Thissen 1988) prüft: *Bearbeiten Prüflinge gleicher Fähigkeit ein
Item unterschiedlich gut, je nachdem, welcher Gruppe sie angehören?*
Übertragen: **Sind Anfragen aus einem Sachgebiet systematisch schwerer, nachdem
für die Gesamtschwierigkeit kontrolliert wurde?**

**[Ü]** Das ist für einen Bestand mit Code, WEG-Recht, Steuer und Lehre die
schärfste verfügbare Frage: eine gebietsweise Schwäche verschwindet in jeder
Gesamtzahl restlos. Und sie ist hier nicht akademisch — das Material selbst
nennt unter „die vier Fragen" die offene Stelle, dass ein falscher Rechtssatz
anders kostet als ein falscher Funktionsname, während für beides dieselbe
Schwelle 0,65 gilt. **[Ü]** DIF ist das Verfahren, das eine gebietsweise
Schwellenfestlegung empirisch begründen würde, statt sie zu setzen.

**Daten.** 12 000er-Korpus mit Gebietsmarkierung; Fähigkeitsschätzung aus
Verfahren 1 oder ersatzweise der Summenwert.

**Kosten.** Gering, eine Kontingenztafel-Statistik je Item.

**Prüfung.** **[E]** Zwei Auflagen, ohne die DIF-Ergebnisse regelmäßig falsch
sind: (a) **iterative Purification** — die Fähigkeitsschätzung, gegen die
kontrolliert wird, muss selbst DIF-frei sein, also werden auffällige Items
entfernt und neu geschätzt, bis es stabil ist; (b) **Effektstärke statt
Signifikanz** — bei 12 000 Fällen wird alles signifikant; die
ETS-Klassifikation (A/B/C nach Delta) ist der übliche Maßstab.

### Was der 12 000er-Bestand darüber hinaus möglich macht

**[Ü]** Vier Dinge, die mit 45 Fällen prinzipiell nicht gehen — unabhängig
von Sorgfalt:

1. **Dimensionalitätsprüfung.** **[E]** Faktorenanalyse tetrachorischer
   Korrelationen mit Parallelanalyse (Horn 1965). Mit 45 Items und 3
   Prüflingen nicht rechenbar; mit 12 000 Items und 200 Varianten ohne
   Weiteres. Damit ist die Frage aus 2.3 — ein Konstrukt oder zwei? —
   entscheidbar statt argumentierbar.
2. **Ankeritems für Verlaufsmessung.** **[E]** Ein festgelegter Satz
   kalibrierter Items, der bei jedem Lauf mitläuft, verankert die Skala über
   die Zeit. Ohne Anker sind zwei Messläufe an einem wachsenden Bestand
   grundsätzlich nicht vergleichbar — die Skala verschiebt sich mit.
3. **Ein Kurztest, der an der richtigen Stelle misst.** **[E]** Aus einem
   kalibrierten Bestand zieht man gezielt Items nahe der aktuellen Fähigkeit
   und maximiert dort die Testinformationsfunktion. **[Ü]** Ein so gezogener
   45-Item-Korpus wäre bei gleicher Länge und gleichen Kosten ein
   erheblich empfindlicheres Instrument als der heutige — die 20 nie
   gelösten Items werden durch Items ersetzt, die sich bewegen können.
   **Das ist der konkreteste Ertrag dieser ganzen Stellungnahme.**
4. **Getrennte Schwellen je Gebiet**, empirisch begründet statt gesetzt
   (siehe Verfahren 4).

---

## 5. Meine unbequemste Frage

**Nennt eine einzige Entscheidung, die aufgrund dieser 45 Fälle anders
ausgefallen ist, als sie ohne sie ausgefallen wäre — und rechnet nach, ob der
Unterschied größer war als ±16 Prozentpunkte.**

Das ist das 95-%-Intervall dieses Korpus, gerechnet aus seinen eigenen Zahlen
in Abschnitt 2.2. Fällt keine solche Entscheidung ein oder liegt sie innerhalb
des Intervalls, dann hat der Prüfkorpus bisher nichts entschieden. Er hat
bestätigt. Und ein Instrument, das bestätigt statt zu entscheiden, ist in
meinem Fach kein Messinstrument, sondern eine Zeremonie — die aufwendigste
Form, sich selbst recht zu geben.

**Und eine zweite, die daran hängt, weil sie erklärt, warum es so kommen
konnte:** Wer hat die 45 Fälle ausgewählt, und ist das dieselbe Instanz, die
den Bestand gefüllt hat? Wenn ja, misst der Test die Übereinstimmung zwischen
zwei Erzeugnissen desselben Autors. Die Schwierigkeit der Anfragen wäre dann
keine Eigenschaft der Anfragen, sondern eine Eigenschaft der Erinnerung daran,
was im Bestand steht — und die 6,7 % Wortüberlappung des Betriebsprotokolls
belegen zwar, dass die *Formulierung* realistisch ist, aber nicht, dass die
*Auswahl der Themen* es ist. Das sind zwei verschiedene Nachweise, und im
Material finde ich nur den ersten.

---

## Was ich nicht weiß

- Ob der Bestand während der 45 Läufe stabil war. Falls nicht, sind die
  Zahlen nicht das, was sie zu sein scheinen.
- Die Reliabilität des Lösungsschlüssels über alle 45 Fälle (nur 20 wurden
  von Hand nachgesehen). Ohne sie ist keine Attenuationskorrektur möglich und
  jedes τ nur eine untere Schranke unbekannter Tiefe.
- Ob die Schwellenschicht dieselben 15 Fälle löst wie B. Ich habe es
  angenommen; wenn nicht, ändert sich die Zahl der varianzfreien Items, nicht
  aber der Befund.
- Ob 200 Abrufvarianten mit vertretbarem Aufwand herstellbar sind. Das ist
  eine Frage an die Bauform des Abrufs, nicht an mein Fach; falls die
  Parameter nicht ohne Neuberechnung der Einbettungen variierbar sind, fällt
  Verfahren 1 in eine ganz andere Kostenklasse und Verfahren 3 bleibt als
  einziges billiges übrig.
- Die tatsächliche Reliabilität der vierstufigen Handnachsicht. **[E]** Bei
  einem einzigen Beurteiler ist sie unbekannt; zwei unabhängige Durchsichten
  von 20 Fällen mit Cohens κ wären ein Tagwerk und würden dem gesamten
  Befundteil den Boden geben, den er heute nicht hat.

---

## Zusammenfassung in drei Sätzen

Der Kosinuswert ist kein schwacher Prädiktor, sondern ein starker Prädiktor
für ein anderes Konstrukt — Deckung des Bestands, nicht Passung der Antwort —
und dass er innerhalb der von ihm selbst ausgewählten Menge nicht mehr trennt,
ist die vorhersagbare Folge der Selektion, nicht ein Befund über sein Signal.
Der Prüfkorpus misst mit rund 24 statt 45 Items an der falschen Stelle der
Skala und kann Unterschiede unter 16 Prozentpunkten nicht auflösen; sein
einziger perfekter Wert (10/10 Schweigen) ist mit einer wahren Fehlerrate von
30 % vereinbar. Die offene Kostenfrage ist rechnerisch klein — die
Schwellenschicht schlägt den heutigen Auslieferungszustand, sobald eine
irreführende Einspielung weniger als 0,7 richtige aufwiegt, und dominiert die
Betriebsart B ganz ohne Gewichtung.
