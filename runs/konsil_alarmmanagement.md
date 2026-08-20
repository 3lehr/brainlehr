# Konsil: das zweite Signal — Sicht Anästhesie/Intensivmedizin, Alarmmanagement

Stand 2026-08-20T14:06:00+0200. Verfasst ohne Kenntnis der anderen Rollen.

**Kennzeichnung der Quellen, durchgehend:**
`[E]` = etabliert in meinem Fach, mit Namen · `[Ü]` = meine Übertragung, Hypothese ·
`[V]` = reine Vermutung.
Alle Literaturangaben stammen aus dem Gedächtnis und sind hier **nicht** gegen die
Originalarbeiten geprüft — Jahreszahlen und Zahlenwerte bitte vor Weitergabe
nachschlagen. Neue Zahlen habe ich keine erfunden; Größenordnungen sind als
Schätzung markiert.

---

## 0. Vorab: was mein Fach an der Fragestellung sofort anders stellt

Die Frage im Material lautet: *„Das einschlägige Fach kommt auf τ = 0,10 und nennt
den Gewinn marginal. Was übersieht es?"*

Meine Antwort in einem Satz: **τ und r sind Trennschärfemaße (Diskrimination). Ein
abgestuftes Alarmsystem lebt nicht von Diskrimination, sondern von Kalibrierung und
davon, wie teuer ein Fehlalarm für den Empfänger ist.** Wer nur die Trennschärfe
misst, misst die Eigenschaft, die er ohnehin nicht verbessern kann, und übersieht die
beiden, die er frei gestalten darf.

`[E]` Das ist im Frühwarnwesen der Normalfall, nicht die Ausnahme. NEWS2 (Royal
College of Physicians, in der zweiten Fassung seit etwa 2017) hat als Vorhersagemodell
für Tod oder Intensivverlegung eine Trennschärfe, die für einen diagnostischen Test als
mäßig gälte — Größenordnung 0,7 bis 0,8 AUC je nach Endpunkt und Kollektiv, *Erinnerung,
ungeprüft*. Der Score ist trotzdem in nationalen Leitlinien, weil er **kalibriert** auf
eine **gestufte Reaktion** abgebildet ist: 0–4 Routine, 5–6 dringende ärztliche
Beurteilung, ≥ 7 Notfallteam, jeweils mit eigener Messfrequenz. Der Nutzen entsteht in
der Abbildung auf Handlungen, nicht in der Rangkorrelation.

Übersetzt: Ein Prädiktor mit τ = 0,10 ist als **Rangordner** wertlos und kann als
**Bandgrenze** trotzdem tragen — genau das zeigt das Material ja selbst. Die Schwelle
0,545 trennt „etwas Passendes liegt im Bestand" von „nichts liegt da" fehlerfrei über
24 Fälle. Das ist eine brauchbare Bandgrenze. Dass derselbe Wert oberhalb davon nichts
mehr trennt, macht ihn nicht schlecht, sondern **einstufig**. Die Antwort darauf ist im
Alarmwesen nie ein besseres Signal, sondern eine zweite Dimension (Abschnitt 3).

---

## 1. Übersetzung — und wo sie bricht

| Alarmwesen | hier |
|---|---|
| Alarm | der ungefragt eingespielte Treffer |
| Patient | die laufende Aufgabe, nicht der Bestand |
| Messgröße/Sensor | Kosinuswert, bm25, Rangfusion |
| Alarmgrenze | Ensemble-Pflicht bzw. Schwelle |
| technisch richtiger Alarm | Treffer ist thematisch korrekt |
| **handlungsrelevanter Alarm** | Treffer ändert, was als nächstes getan wird |
| Fehlalarm | Einspieler, der nichts ändert oder in die Irre führt |
| stiller Ausfall | Bestand hätte geholfen, schwieg (heute 34/45) |
| Alarmlast pro Bett und Tag | Einspieler pro Sitzung |

`[E]` Die für mein Fach wichtigste Zeile ist die fett gesetzte. Seit den
Alarmarbeiten der 2010er Jahre (Cvach, Übersichtsarbeit 2012; Sendelbach & Funk 2013;
The Joint Commission, National Patient Safety Goal 06.01.01, ab 2014) ist der Endpunkt
**nicht** „war der Alarm technisch richtig", sondern **„war er handlungsrelevant"**.
Die berichteten Anteile nicht handlungsrelevanter Alarme liegen im Bereich von grob
80 bis über 95 Prozent — *Erinnerung, ungeprüft, als Größenordnung zu lesen*. Die
Mehrzahl davon ist technisch völlig korrekt: die Sättigung ist wirklich kurz auf 88
gefallen. Sie ändert nur nichts.

Das ist exakt die Klasse „**teilweise**" im Material: 12 von 20. Thematisch nicht
falsch, sachlich folgenlos. Mein Fach würde die 12 nicht zu den 5 echten Ausfällen
addieren und auch nicht zu den 3 Korpusfehlern — es sind **richtige Alarme ohne
Handlungsfolge**, und sie sind die eigentliche Last.

**Wo die Übersetzung nicht trägt — vier Stellen, und alle vier sind wichtig:**

1. **Es gibt keine Wahrheit, die später eintritt.** Am Monitor entscheidet der
   Krankheitsverlauf innerhalb von Minuten bis Stunden, ob der Alarm recht hatte. Hier
   erfährt niemand je, ob ein Einspieler richtig war — es sei denn, man baut die
   Rückmeldung ausdrücklich (Abschnitt 4, Verfahren 1). Ohne sie hat dieses System
   keinen Verlauf, nur eine Momentaufnahme aus 45 Fällen.
2. **Die Asymmetrie ist umgekehrt zur klinischen.** Am Bett ist der verpasste Alarm
   potenziell tödlich, der Fehlalarm „nur" lästig; deshalb akzeptiert mein Fach
   bewusst grauenhafte Trefferquoten. Hier ist ein falscher Einspieler **kein
   Rauschen**, sondern ein Datum, das der Empfänger verarbeitet. Die klinische
   Entsprechung ist nicht der Fehlalarm, sondern der **falsch zugeordnete
   Laborwert**: der wird nicht überhört, der wird geglaubt und behandelt. `[Ü]`
   Diese eine Verschiebung entwertet einen großen Teil der naiven Analogie „lieber
   einmal zu viel piepsen".
3. **Der Empfänger ermüdet nicht — er ankert.** Dazu Abschnitt 2.
4. **Keine Eskalationskette.** Am Bett gibt es eine zweite Instanz (Pflege → Arzt →
   Notfallteam). Hier gibt es genau einen Empfänger. Alles, was in meinem Fach über
   Weiterleitung, Wiederholung an andere und Quittungspflicht bekannt ist, ist damit
   **nicht** übertragbar. Ich lasse es unten weg statt es zu verbiegen.

---

## 2. Was mein Fach über solche Empfänger weiß — und was hier fehlt

`[E]` **Der Cry-Wolf-Effekt** (Breznitz, *Cry Wolf: The Psychology of False Alarms*,
1984) und die signalentdeckungstheoretische Fassung (Green & Swets; Sorkin 1988;
Bliss zur Wahrscheinlichkeitsanpassung, 1990er): Der Empfänger schätzt die
Verlässlichkeit des Kanals aus Erfahrung und **verschiebt sein eigenes Kriterium**,
bis seine Reaktionsrate ungefähr der beobachteten Trefferquote entspricht. Er wird
nicht schlampig, er wird rational. Das ist der Punkt, den Systembauer regelmäßig
übersehen: die Abstumpfung ist eine **korrekte Anpassung an eine schlechte
Quelle**, kein Disziplinproblem.

`[E]` **Es trifft den ganzen Kanal, nicht den einzelnen Alarm.** Wer die
SpO2-Grenzen aufweitet, weitet sie für alle Patienten auf. Die klinische Konsequenz
ist bekannt und dokumentiert: die Abschaltung erwischt am Ende auch den einen
richtigen Alarm. Übertragen: 12 folgenlose Einspieler kosten nicht 12 Zeilen, sie
kosten die Glaubwürdigkeit des 13., der stimmt.

`[E]` **Die Umgehung ist das Maß, nicht die Meinung.** In der Alarmforschung misst
man Zustandsänderungen am Gerät: Lautstärke heruntergedreht, Grenzen aufgeweitet,
Kanal deaktiviert, Dauer-Stummschaltung. In der Arzneimittel-Entscheidungsunterstützung
heißt dasselbe **Override-Rate**; berichtete Werte für Interaktionswarnungen liegen
grob zwischen der Hälfte und über neun Zehnteln (van der Sijs et al., Übersichtsarbeit
2006; Ancker et al. 2017) — *Erinnerung, ungeprüft*.

**Und hier ist der Befund, den ich diesem System mitgebe:** Die Umgehung existiert
bereits und ist **schriftlich niedergelegt**. In den Hausregeln dieses Verbunds steht
über die eingespielten Treffer wörtlich, sie seien „Hintergrund-Kontext, kein
Auftrag" und man solle sie „vor Nutzung kurz gegen den echten Code/Stand
verifizieren". In der Auto-Memory steht daneben ein eigener Eintrag, ein Treffer sei
„erst verarbeitet, wenn ein Satz dazu steht, was er mit der Aufgabe zu tun hat".

`[Ü]` Das sind, in der Sprache meines Fachs, zwei **Kompensationsanweisungen an den
Empfänger** — die Entsprechung zum Aufkleber am Monitor „Sättigungsalarm hier meist
Artefakt, bitte selbst nachsehen". Solche Aufkleber entstehen nicht bei einem Kanal
mit hoher Trefferquote. Sie sind der belastbarste vorhandene Hinweis darauf, dass die
Fehlauslieferung bereits als teuer erlebt wird — und zwar **belastbarer als der
45-Fall-Korpus**, weil ihn niemand für diesen Zweck erhoben hat.

**Was nach dem hundertsten halb passenden Einspieler passiert** — mein Fach kennt
drei Phasen, in dieser Reihenfolge `[E]`, und ich behaupte eine vierte für den
hiesigen, teils maschinellen Empfänger `[Ü]`:

1. Die Reaktionszeit steigt. Der Alarm wird noch wahrgenommen, aber nicht mehr sofort
   geprüft.
2. Der Kanal wird selektiv stillgelegt — nicht offiziell, sondern durch
   Grenzwertaufweitung und lokale Regeln.
3. **Die gefährlichste Phase: der richtige Alarm wird aktiv umgedeutet.** Nicht
   „überhört", sondern erklärt („wieder Bewegungsartefakt"). Diese Phase erzeugt keine
   Lücke im Protokoll, sondern eine falsche Begründung im Protokoll.
4. `[Ü]` **Beim Sprachmodell als Empfänger fällt Phase 1 und 2 weg und Phase 3
   verschiebt sich.** Es ermüdet nicht über Sitzungen hinweg, es hat kein Gedächtnis
   für die Verlässlichkeit des Kanals, und es kann den Einspieler nicht ignorieren —
   er steht im Kontext und wird verarbeitet. Ein halb passender Treffer wird also
   nicht abgestumpft weggefiltert, sondern **plausibel eingebaut**. Der
   Schutzmechanismus, auf den sich mein Fach seit vierzig Jahren stillschweigend
   verlässt — der Empfänger lernt, schlechte Kanäle zu ignorieren — **existiert hier
   nicht**. Das macht die 12 „teilweise" hier schlimmer als am Krankenbett, nicht
   harmloser.

`[V]` Ich vermute, dass der menschliche Betreiber dieses Systems bereits in Phase 2
ist (die Kompensationsanweisungen oben), und das Modell strukturell nie aus Phase 0
herauskommt. Das ist der ungünstigste denkbare Empfängermix: einer, der nicht mehr
hinsieht, und einer, der alles glaubt.

---

## 3. Abstufung — welche überträgt sich, und welche ist die wirksamste

`[E]` IEC 60601-1-8 (Alarmsysteme in medizinischen elektrischen Geräten) kennt drei
Prioritätsstufen — niedrig, mittel, hoch. Die Zuordnung erfolgt über **zwei**
Dimensionen: **Schwere des möglichen Schadens** × **Zeit bis zum Eintritt**. Die
Verlässlichkeit der Messung kommt in dieser Zuordnung **nicht vor**. Ein Monitor
piepst nicht lauter, weil der Sensor sicherer ist.

**Das ist die wirksamste übertragbare Abstufung, und sie fehlt hier vollständig.**
Dieses System stuft ausschließlich nach Abrufsicherheit (Kosinus, Ensemble-Einigkeit).
Es stuft nie nach **Folge**. Eine Lehre über einen unumkehrbaren Handgriff — Push,
Löschung, Geheimnis im Quelltext — und ein Sachverhalt über einen Funktionsnamen
laufen durch dieselbe Schwelle und werden gleich ausgeliefert oder gleich verschwiegen.

`[Ü]` Daraus die Bauform: **zwei Achsen statt einer.**
- Die **Folgeklasse** des Eintrags bestimmt die Priorität. Sie ist eine Eigenschaft
  des Eintrags, keine der Anfrage — also **einmal statisch vergeben**, nicht zur
  Laufzeit gerechnet, und damit kostenlos im Betrieb.
- Der **Kosinuswert** bestimmt nur noch die **Form** der Auslieferung, nicht das Ob.

Die zweite übertragbare Abstufung, der Rang nach:

`[E]` **Der Likelihood-Alarm** (Sorkin, Kantowitz & Kantowitz, 1988): ein Alarm, der
seine eigene Sicherheit mitgibt, wird nachweislich besser genutzt als ein binärer.
Und die praktische Entsprechung in der Norm: niedrigpriore Alarme sind **rein
visuell**, ohne Ton. Der Fehlalarm wird nicht seltener — er wird **billig**.

`[Ü]` **Das ist der Kern meines Beitrags. Dieses System versucht seit einer
Messreihe, die Fehlerrate zu senken, obwohl das Fach selbst sagt, dass das nicht
geht (τ = 0,10). Mein Fach hat dieselbe Sackgasse vor zwanzig Jahren verlassen und
stattdessen den Preis des Fehlers gesenkt.** Konkret: ein Treffer oberhalb 0,545, für
den keine zweite Evidenz spricht, wird nicht mit Titel, Zusammenfassung und Inhalt
eingespielt, sondern als **eine Zeile**: Kennung, Titel, Ähnlichkeitsband. Nichts
sonst. Damit kosten die 20 Fehlgriffe der Schwellenschicht 20 Zeilen statt 20
Absätzen, und die 34 falschen Stillen fallen ersatzlos weg.

`[E]` **Verzögerung und Persistenzkriterium.** In der Alarmforschung der belegteste
einzelne Handgriff: Ein Sättigungsalarm, der erst nach etwa 15 bis 19 Sekunden
Bestand ausgelöst wird, entfernt einen großen Teil der Fehlalarme, ohne die
handlungsrelevanten zu verlieren (Görges, Markewitz & Westenskow, *Anesthesia &
Analgesia*, 2009 — *Erinnerung, ungeprüft*). Begründung: die klinisch relevante
Entsättigung hält an, das Artefakt nicht.

`[Ü]` Übertragen: die freie zweite Messung ist **der nächste Prompt derselben
Sitzung**. Kein zusätzlicher Lauf, kein Modellaufruf — nur Zustand. Ein Knoten, der
bei zwei aufeinanderfolgenden Prompts wiederkehrt, ist eher wirklich am Thema als
einer, der einmal aufblitzt. Das ist die Randbedingung 4 („ein zweiter Lauf wäre
vertretbar") zum Nulltarif.

`[E]` **Ruhigstellung auf Zeit, gezielt statt global** (Audio-Pause, typischerweise
zwei Minuten; vorausschauendes Aussetzen während bekannter Eingriffe wie Absaugen
oder Umlagern). Wichtig: stillgelegt wird **ein Alarm**, nie der Monitor.
`[Ü]` Übertragen: ein Knoten, der in dieser Sitzung schon einmal eingespielt und
nicht aufgegriffen wurde, wird für den Rest der Sitzung nicht erneut eingespielt.

`[E]` **Angepasste statt vorgegebener Grenzen** (Graham & Cvach 2010 berichten für
patientenindividuelle Grenzen eine deutliche Reduktion kritischer Alarme —
*Erinnerung, ungeprüft*). `[Ü]` Entsprechung: Bandgrenzen je Sachgebiet statt einer
globalen 0,65 — was die Projektbeschreibung als offene Frage 3 ohnehin schon benennt.

**Nicht übertragbar, ausdrücklich:** Eskalationsketten und Weitergabe an eine zweite
Instanz (es gibt keine), akustisch/visuelle Kodierung (kein Kanal dafür),
Quittungspflicht (erzwänge genau die Unterbrechung, die vermieden werden soll).

---

## 4. Vier Verfahren

Alle vier messen am **Empfänger**, nicht am Alarm. Verfahren 1 ist Voraussetzung für
die anderen drei; ohne es sind 2 bis 4 Meinungen.

### Verfahren 1 — Aufgriffsquote und Alarmlast aus dem Betriebsprotokoll
*(Entsprechung: Alarmaudit / Override-Rate)*

**Kernidee.** Jeder ausgelieferte Treffer bekommt rückwirkend ein Urteil aus dem
Protokoll: Ist er im weiteren Verlauf desselben Vorgangs **aufgegriffen** worden?
Operationalisiert über Spuren, die es ohne den Einspieler nicht gäbe — die
Knotenkennung wird genannt, ein nur in diesem Knoten vorkommender Dateipfad oder
Begriff taucht danach in einem Werkzeugaufruf oder in der Ausgabe auf, der Knoten
wird gelesen oder fortgeschrieben. Daneben die reine Last: Einspieler pro Sitzung,
Verteilung, Spitzen.

**Daten.** Das vorhandene Protokoll mit rund 21 000 Zugriffen; dazu die zugehörigen
Sitzungsverläufe. Nichts Neues zu erheben.

**Kosten.** Ein rückblickender Auswertungslauf, keine Modellaufrufe, keine
Laufzeitkosten. Der Dauerbetrieb kostet ein zusätzliches Protokollfeld.

**Prüfung.** Rot vor grün: zwei von Hand gebildete Gruppen aus dem Bestand — Fälle,
in denen der eingespielte Knoten nachweislich die Arbeit verändert hat, und Fälle, in
denen er erkennbar folgenlos blieb. Die Kennzahl muss beide trennen. Tut sie das
nicht, ist die Kennzahl falsch, nicht der Bestand. Positivkontrolle: die Betriebsart B
(liefert immer) muss eine deutlich niedrigere Aufgriffsquote je Einspieler zeigen als C.
**Ehrlich zu benennen:** Das misst Ko-Vorkommen, nicht Ursache. Das Modell hätte den
Dateipfad womöglich ohnehin genannt. Die Kennzahl taugt für **Vergleiche zwischen
Betriebsarten**, nicht als absolute Nutzenaussage.

### Verfahren 2 — Zweiachsige Auslieferung: Folge bestimmt die Stufe, Ähnlichkeit die Form

**Kernidee.** Unterhalb 0,545 wird geschwiegen — das ist gemessen und trennt
fehlerfrei. Oberhalb wird **immer** ausgeliefert, aber in einer Form, die vom Band
abhängt: schmales Band als einzeilige Fundstelle (Kennung, Titel), oberes Band mit
Zusammenfassung. Quer dazu die Folgeklasse des Eintrags: Einträge über Unumkehrbares
(Veröffentlichung, Löschung, Geheimnisse, Geld) werden **eine Stufe höher**
ausgeliefert, auch im schmalen Band, weil im Alarmwesen die Priorität aus der Folge
kommt und nicht aus der Messsicherheit.

**Daten.** Kosinuswerte (vorhanden). Eine einmalige Folgeklassifikation der 5200
Einträge — vermutlich weitgehend aus vorhandenen Marken und Pfaden ableitbar, der
Rest von Hand.

**Kosten.** Laufzeit praktisch null (ein Vergleich, ein Feld). Einmalige
Klassifikationsarbeit; Größenordnung ein Arbeitstag `[V]`.

**Prüfung.** Erstens: Auf den 45 Fällen muss die Schwellenschicht-Zeile reproduziert
werden (15 richtig, 20 falsch, 10 richtig geschwiegen, 0 falsch geschwiegen) — die
Änderung betrifft nur die Form, die Trefferzahlen dürfen sich nicht bewegen.
Zweitens, und das ist die eigentliche Prüfung: die Aufgriffsquote aus Verfahren 1 darf
gegenüber heute **nicht sinken**, während die Zahl der falschen Stillen von 34 auf 0
fällt. Drittens Gegenprobe für die Folgeachse: die als folgenschwer markierte
Teilmenge muss im Protokoll eine messbar höhere Aufgriffsquote haben. Tut sie das
nicht, ist die Klassifikation Zierrat und wird gestrichen.

### Verfahren 3 — Persistenzkriterium über die Sitzung
*(Entsprechung: Alarmverzögerung / Onset-Delay)*

**Kernidee.** Ein Knoten wird in der vollen Form erst ausgeliefert, wenn er bei zwei
aufeinanderfolgenden Abrufen derselben Sitzung oben steht; beim ersten Mal nur als
Fundstelle. Der zweite Lauf ist der nächste Prompt und kostet nichts. Für Einträge
der hohen Folgeklasse gilt das Kriterium **nicht** — dort wird sofort ausgeliefert,
genau wie ein hochpriorer Alarm nicht verzögert wird.

**Daten.** Protokoll mit Sitzungszuordnung; Zustand über zwei Abrufe.

**Kosten.** Ein kleiner Speicher je Sitzung. Preis: eine Verzögerung um genau einen
Zug — der klinische Preis der Alarmverzögerung, dort seit Jahren akzeptiert.

**Prüfung.** Vollständig rückblickend am Protokoll möglich, **ohne etwas zu bauen**:
Wie oft wäre ein tatsächlich aufgegriffener Treffer (Verfahren 1) durch das Kriterium
um einen Zug verzögert worden, und wie viele folgenlose wären ganz entfallen? Ist das
Verhältnis nicht deutlich günstig, wird nicht gebaut. Zusätzlich der Grenzwerttest:
Persistenz über 2 und über 3 Züge — steigt die Aufgriffsquote bei 3 nicht weiter,
bleibt es bei 2.

### Verfahren 4 — Gezielte Ruhigstellung des einzelnen Eintrags
*(Entsprechung: Audio-Pause auf einen Alarm, nicht auf den Monitor)*

**Kernidee.** Ein Knoten, der in einer Sitzung eingespielt und nicht aufgegriffen
wurde, wird in dieser Sitzung nicht erneut eingespielt. Nie wird der Kanal als
Ganzes stillgelegt — die Ruhigstellung ist immer eintragsgenau und immer befristet
(Sitzungsende).

**Daten.** Protokoll.

**Kosten.** Eine Menge im Sitzungszustand.

**Prüfung.** Zuerst die Frage, ob das Verfahren überhaupt gebraucht wird: Wie hoch
ist im Protokoll die Wiederauslieferungsrate identischer Knoten innerhalb einer
Sitzung? Liegt sie nahe null, wird nichts gebaut und das Verfahren gestrichen. Ich
kenne die Zahl nicht und schätze sie nicht.

---

## 5. Das Verhältnis von falsch liefern zu falsch schweigen — bestimmen statt setzen

Mein Fach setzt solche Verhältnisse nicht, es **entlockt** sie. Drei etablierte Wege,
in der Reihenfolge, in der ich sie hier anwenden würde.

**`[E]` (a) Erst kalibrieren, dann entscheiden.** Vor jeder Kostenabwägung steht die
Zuverlässigkeitsdarstellung: Für jedes Kosinusband der Anteil der tatsächlich
aufgegriffenen Treffer — gemessen an den über 12 000 Fällen des zweiten Korpus und
am Protokoll, nicht an den 45. Das Ergebnis ist eine Kalibrierungskurve, kein
Rangmaß. Sie kann brauchbar sein, obwohl τ = 0,10 ist; beides schließt sich nicht
aus. Ohne diese Kurve ist jede Kostenrechnung gegenstandslos, weil die
Eintrittswahrscheinlichkeit fehlt.

**`[E]` (b) Entscheidungskurvenanalyse** (Vickers & Elkin, *Medical Decision Making*,
2006). Ihr Kunstgriff ist genau der hier gesuchte: Statt Kosten in Währung zu
schätzen, wird **eine Schwellenwahrscheinlichkeit** erfragt — „ab welcher Chance,
richtig zu liegen, willst du ausliefern?" Diese eine Antwort **legt das
Austauschverhältnis fest**, denn Schwelle p entspricht dem Verhältnis p : (1−p). Wer
sagt „einer von fünf darf danebengehen", hat 4 : 1 gesagt, ohne je über Kosten
gesprochen zu haben. Die praktikable Formulierung für den Betreiber ist die des
Alarmwesens: **„Wie viele folgenlose Einspieler nimmst du in Kauf, um einen
nützlichen mehr zu bekommen?"** Eine Zahl, eine Minute, und sie ist prüfbar
protokolliert.

**`[E]` (c) Offenbarte Präferenz statt Befragung.** Aussagen über die eigene
Alarmtoleranz sind notorisch unzuverlässig; das Verhalten am Gerät ist es nicht. Der
belastbare Messpunkt ist die **Umgehung**: ab welcher Alarmlast wird der Kanal
aufgeweitet oder abgeschaltet. `[Ü]` Hier liegt dieser Messpunkt bereits vor —
in Gestalt der schriftlichen Kompensationsanweisungen aus Abschnitt 2. Und er lässt
sich sauber nachmessen: Mit Verfahren 1 die Aufgriffsquote gegen die Einspielermenge
auftragen. **Der Punkt, an dem die Aufgriffsquote einbricht, obwohl die
Trefferqualität gleich bleibt, ist der Cry-Wolf-Punkt** — er ist gemessen, nicht
gesetzt, und er ist die härtere Obergrenze als jede erfragte Zahl.

**`[E]/[Ü]` (d) Und: es gibt nicht ein Verhältnis.** In der Anästhesie hat derselbe
Alarm bei Einleitung, in der Erhaltungsphase und bei Ausleitung verschiedenen Wert;
Alarmgrenzen werden phasenweise umgestellt. Übertragen: Die Kosten eines falschen
Einspielers während einer feinen Änderung an einer bekannten Stelle sind hoch (er
lenkt ab und ankert), während einer offenen Frage niedrig (er kostet eine Zeile). Ich
würde deshalb **drei bis vier Aufgabenklassen** bilden und (b) je Klasse einmal
durchführen. Drei Zahlen sind ehrlicher als eine.

**Was ich nicht kann:** Ich kann das Verhältnis nicht herleiten. Es ist eine
Wertentscheidung des Betreibers, und mein Fach liefert nur das Verfahren, sie
konsistent und protokolliert zu treffen. Wer es aus den Daten allein ableiten will,
täuscht sich.

---

## 6. Meine unbequemste Frage

**Für wie viele der 5200 Einträge gibt es überhaupt eine Handlung, die sich ändert,
wenn der Eintrag ankommt?**

`[E]` In der Intensivmedizin ist das die erste Frage jeder Alarmvisite und die
unbeliebteste: Ein Parameter, für den keine Konsequenz hinterlegt ist, wird nicht
überwacht. Nicht leiser gestellt — **gar nicht überwacht.** Wer ihn trotzdem alarmiert
schaltet, erzeugt Last ohne Nutzen und beschädigt die Kanäle, die etwas können.

Dieses System hat 45 Fälle vermessen, fünf Größen geprüft, eine Betriebsart
ausgeliefert und eine Konsilrunde einberufen — und in keiner Zahl des gesamten
Materials kommt vor, ob **je ein einziger Einspieler eine Arbeit verbessert hat**. Der
45-Fall-Korpus misst den Alarm. Das Protokoll mit 21 000 Zugriffen misst den
Empfänger, und aus ihm stammt keine der Zahlen, um die es hier geht.

Daraus folgen zwei Sätze, die ich für unbequem halte:

1. **Die 34 falschen Stillen sind nicht ohne Weiteres 34 Ausfälle.** Sie sind 34
   Fälle, in denen etwas im Bestand lag. Wie viele davon die Arbeit verändert hätten,
   ist ungemessen. Es könnten deutlich weniger sein — dann wäre der heutige
   Auslieferungszustand besser als er aussieht, aus dem falschen Grund.
2. **Solange das ungemessen ist, ist die Frage nach dem zweiten Signal verfrüht.**
   Zur Debatte steht dann nicht die Schwelle, sondern die **Indikation**: Welcher Teil
   dieses Bestands gehört überhaupt an einen Kanal, der ungefragt in laufende Arbeit
   spricht — und welcher gehört an einen, den man **fragt**? Mein Fach überwacht nicht
   alles, was messbar ist. Es überwacht, wofür eine Reaktion hinterlegt ist. Alles
   andere steht in der Kurve und wird gelesen, wenn jemand hinsieht.

Und die Frage darunter, die ich nicht beantworten kann `[V]`: Wenn ein System 5200
Einträge führt, aber nur eine kleine Teilmenge davon je eine Handlung ändert — ist
dann das Abrufproblem gelöst worden, während das eigentliche Problem die
**Aufnahme** ist? Am Monitor entspricht das der Frage, ob man den Fehlalarm
wegfiltert oder die Elektrode richtig klebt. Mein Fach hat zwanzig Jahre am Filter
gearbeitet, bevor es gemerkt hat, dass die Elektrode das billigere Ende war.

---

## Anhang: was ich bewusst nicht getan habe

- **Keine neuen Zahlen.** Ich habe keine Trefferquoten, Schwellen oder Kostenfaktoren
  vorgeschlagen, für die ich keine Messung habe. Die einzige Zahl, die ich
  weiterverwende, ist die gemessene 0,545.
- **Keine Eskalationsmechanik**, obwohl sie das Herzstück des klinischen
  Alarmwesens ist — es gibt hier keine zweite Instanz, an die eskaliert würde.
- **Kein Vorschlag zu Kohärenz oder Störungsrobustheit.** Beides steht im Material
  und ist nicht mein Fach; ich habe dazu nichts beizutragen, was über das dort
  Zitierte hinausgeht.
- **Nichts gebaut, nichts geändert, nichts in den Wissensspeicher geschrieben.**
