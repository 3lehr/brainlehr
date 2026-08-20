# Konsil — Stellungnahme aus der Meteorologie

Fach: probabilistische Vorhersage und Verifikation (Ensemble, Kalibrierung,
Brier-Zerlegung, Zuverlässigkeitsdiagramm, Ranghistogramm, Kosten-Verlust-Modell).
Verfasst 2026-08-20. Grundlage ist ausschließlich
`runs/konsil_zweites_signal_material.md`. Nichts am Repo geändert.

Kennzeichnung durchgehend:
**[ETABLIERT]** = Lehrbuchstand meines Fachs, mit Namen ·
**[ÜBERTRAGUNG]** = meine Hypothese, hier ungeprüft ·
**[VERMUTUNG]** = Einschätzung ohne Beleg.

---

## 0. Der eine Satz vorweg

Mein Fach hat 1950 aufgehört, „morgen regnet es" zu sagen, und angefangen,
„70 Prozent" zu sagen — nicht weil es besser wusste, sondern weil ein
Ja/Nein-Urteil sich nicht ehrlich bewerten und nicht rational verwenden lässt.
Dieses System steht heute vor 1950. Es gibt einen **Schalter** aus, wo es eine
**Zahl** ausgeben müsste. Praktisch alles, was ich unten sage, folgt daraus.

---

## 1. Übersetzung

### Die Zuordnung, die trägt

| Meteorologie | hier |
|---|---|
| Vorhersage | der ausgelieferte Treffersatz plus (heute fehlend) eine Wahrscheinlichkeit, dass er die Frage beantwortet |
| Ereignis / Eintreten | „das Eingespielte war für diese Arbeit sachlich brauchbar" |
| Beobachtung | das Handurteil bzw. der Prüfkorpus |
| Vorhersagemodell | Stichwortkanal + Bedeutungskanal + RRF |
| Ensemble | genau diese zwei Kanäle, zwei Mitglieder |
| Ensemble-Streuung | die Uneinigkeit der Kanäle |
| Verifikationsarchiv | 45 Fälle + 12 000 Fälle + 21 000 Protokollzugriffe |
| Klimatologie | die Grundrate: „wie oft ist ein beliebig gelieferter Treffer brauchbar" |
| Warnschwelle | die Ensemble-Pflicht |
| Kosten-Verlust-Verhältnis | falsch liefern gegen falsch schweigen — hier ausdrücklich offen |

### Wo sie NICHT trägt — vier Bruchstellen, alle vier folgenreich

**(a) Zwei Vorhersagegrößen sind zu einer verschmolzen.** **[ETABLIERT]** In
meinem Fach ist die erste Frage jeder Verifikation: *Was genau ist das
Ereignis?* „Niederschlag" und „Niederschlag > 5 mm" sind verschiedene
Vorhersagegrößen mit verschiedener Güte, und man darf ihre Bewertungen nicht
mischen. Ihr Material zeigt in derselben Tabelle zwei Größen:

- Größe A: *„liegt überhaupt etwas Passendes im Bestand?"* — der Kosinuswert
  hat hier deutliche Trennschärfe (0,4435–0,5410 gegen 0,5497 aufwärts).
- Größe B: *„ist das Gelieferte richtig?"* — dort hat er keine (0,5970 gegen
  0,6030, siehe (d)).

Der Satz „Er sagt zuverlässig, ob etwas da ist, nichts darüber, ob es richtig
ist" ist nicht der Befund, den es zu erklären gilt — er ist die Auflösung.
Es sind zwei Vorhersagen, und heute steuert eine Schwelle für Größe A eine
Entscheidung, die von Größe B abhängt. In meinem Fach ist das der klassische
Fehler, die Schwelle für „Regen ja/nein" an eine Warnung für „Starkregen" zu
hängen.

**(b) Die Beobachtung ist selbst fehlerhaft, und zwar messbar.** 3 der 20
„Fehler" waren Fehlurteile des Prüfkorpus — 15 Prozent Etikettenrauschen.
**[ETABLIERT]** Bei uns heißt das Beobachtungs- bzw. Repräsentativitätsfehler,
und die Folge ist hart: sobald der Beobachtungsfehler in die Größenordnung
des Vorhersagefehlers kommt, sind alle Gütemaße nach unten verzerrt und die
**Obergrenze der messbaren Güte sinkt**. Mehr Fälle helfen dagegen nicht.
Die 12 „teilweise"-Fälle sind schlimmer als Rauschen: das Ereignis ist dort
gar nicht binär. **[ÜBERTRAGUNG]** Solange die Zielgröße nicht dreistufig
(brauchbar / teilweise / daneben) protokolliert und verifiziert wird, wird
jedes Verfahren gegen ein Etikett optimiert, das die eigentliche Frage
(„hat es der Arbeit genützt?") nicht abbildet.

**(c) Es gibt keine stationäre Klimatologie.** **[ETABLIERT]** Modellausgabe-
statistik (MOS) muss nach jedem Modellwechsel neu angepasst werden; die
Gleichungen veralten still, wenn das zugrunde liegende Modell sich ändert.
Hier ändert sich der „Modelllauf" laufend: der Bestand wächst, das
Einbettungsmodell kann getauscht werden. **Jede kalibrierte Schwelle, die Sie
einziehen, ist damit ein wartungspflichtiges Objekt mit Verfallsdatum** —
das ist ein Preis, kein Detail. Wer die Kalibrierung einführt, muss zugleich
sagen, wann sie neu erhoben wird.

**(d) Ein Unterschied, den man nicht deuten darf.** Der Satz „Ihr Median
(0,6030) liegt sogar **über** dem der echten Treffer (0,5970)" trägt nicht.
n = 20 gegen n = 14, Spannweiten praktisch deckungsgleich (0,5555–0,6374
gegen 0,5497–0,6375), Differenz 0,006. **[ETABLIERT]** Das ist bei diesen
Stichprobengrößen nicht von Null unterscheidbar. Die richtige Aussage ist
„keine Trennschärfe", nicht „umgekehrte Trennschärfe". Wer die Umkehrung
baut, baut auf Rauschen.

**(e) Und die fehlerfreie Schwelle bei 0,545 ist keine.** Sie wurde an
derselben Stichprobe gefunden, an der sie geprüft wird — 10 gegen 14 Fälle,
Lücke zwischen 0,5410 und 0,5497, also 0,0087. **[ETABLIERT]** In der
Verifikation heißt das *in-sample*; die Fehlerfreiheit ist eine Eigenschaft
der Stichprobe, nicht der Schwelle. **[VERMUTUNG]** An 12 000 Fällen wird
diese Lücke sich schließen und die Schwelle wird Fehler machen. Das ist kein
Argument gegen sie — nur gegen die Zahl „fehlerfrei".

---

## 2. Was die Anfragegüte-Vorhersage übersieht

### 2.1 Rangkorrelation ist kein zulässiges Gütemaß für eine Entscheidung

**[ETABLIERT]** Murphy (1973) zerlegt den Brier-Score in

> **Brier = Zuverlässigkeit − Trennschärfe + Unsicherheit**

Zuverlässigkeit (reliability, Kalibrierung): sagt „0,7" in 70 Prozent der
Fälle das Richtige? · Trennschärfe (resolution): unterscheiden die Vorhersagen
überhaupt Lagen mit verschiedener Eintrittsrate? · Unsicherheit: die Grundrate,
nicht beeinflussbar.

Kendalls τ misst — bestenfalls — einen Teil der **Trennschärfe** und ist
gegenüber jeder monotonen Verzerrung blind. Es sagt **nichts** über
Zuverlässigkeit. Ein Fach, das seine eigene Nutzbarkeit an τ misst, hat einen
von drei Termen gemessen und den entscheidenden weggelassen. τ = 0,10 heißt
folglich nicht „unbrauchbar", sondern: *über die Nutzbarkeit wurde nichts
ausgesagt.* Die Übersichtsarbeit hat recht mit „marginale Gewinne" — für
Ranglisten. Für eine **Schweigen/Sprechen-Entscheidung** ist es die falsche
Kennzahl.

**[ETABLIERT]** Ergänzend: τ und r sind keine *proper scoring rules*. Man kann
sie durch Manipulation verbessern, ohne besser vorherzusagen. Brier-Score und
Log-Score sind streng proper — das ist der Grund, warum mein Fach seit
Brier (1950) nichts anderes mehr für Bewertungszwecke akzeptiert.

### 2.2 Die direkte Antwort auf Ihre Frage

*Ist ein System mit schlechter Korrelation, aber guter Kalibrierung womöglich
brauchbarer als eines mit guter Korrelation?* — **Ja, aber nicht, weil es mehr
weiß. Weil es weniger schadet.** **[ETABLIERT]**

- Eine **kalibrierte, aber trennschärfelose** Vorhersage ist rechnerisch die
  Klimatologie: sie sagt immer die Grundrate. Ihr wirtschaftlicher Wert über
  der Klimatologie ist **null** — aber er ist **nie negativ**. Man kann auf
  ihr eine rationale Entscheidung aufbauen; sie ist nur nicht besser als
  „immer dasselbe tun".
- Eine **unkalibrierte** Vorhersage kann Wert **unter** null haben: sie führt
  zu Entscheidungen, die schlechter sind als die Grundraten-Entscheidung.

**[ÜBERTRAGUNG]** Und genau das ist der Zustand C. Auf den 35 lösbaren Fragen
liefert B in 15 Fällen richtig — die Grundrate „einfach immer sprechen" ist
also rund 43 Prozent Treffer auf lösbaren Fragen. C liefert **1 von 35**. C
wählt aus den lösbaren Fragen nicht die aussichtsreichen aus, sondern
praktisch keine; und die eine Größe, an der es hängt, hat für „richtig?"
nachweislich keine Trennschärfe. **Der heutige Auslieferungszustand ist auf
der lösbaren Teilmenge nicht ein vorsichtiges System, sondern ein
unkalibriertes.** Er tut, was ein Meteorologe „ein Warnsystem, das an der
falschen Größe hängt" nennt: es schweigt nicht dort, wo es unsicher ist,
sondern dort, wo die Kanäle uneins sind — und die Uneinigkeit korreliert mit
der Richtigkeit nicht.

Nebenbefund, der das stützt: die Zeile „Zahl übereinstimmender Kanäle
(durchweg 0)" heißt, dass das Kriterium der Ensemble-Pflicht auf dem gesamten
Prüfkorpus **konstant** ist. **[ETABLIERT]** Eine konstante Größe kann keine
Trennschärfe haben — sie kann nur eine Vorhersage abschneiden. Ein Filter auf
einer im Prüfkorpus konstanten Größe ist keine Entscheidung, sondern ein
pauschaler Abschlag.

### 2.3 Sharpness subject to calibration

**[ETABLIERT]** Gneiting, Balabdaoui & Raftery (2007) formulierten das
Leitprinzip: *maximiere die Schärfe unter der Nebenbedingung der
Kalibriertheit.* Erst kalibrieren, dann schärfen — nie umgekehrt. Übertragen:
Zuerst muss das System sagen können „hier bin ich zu 30 Prozent brauchbar",
und diese 30 Prozent müssen stimmen. Ob es je 90-Prozent-Fälle findet
(Schärfe), ist die **zweite** Frage. Die heutige Debatte springt direkt zur
zweiten.

---

## 3. Das Ensemble aus zwei Mitgliedern

### 3.1 Was mein Fach mit Streuung tut — und was es nicht tut

**[ETABLIERT]**

1. **Streuung ist ein Prädiktor, kein Tor.** Der Streuung-Güte-Zusammenhang
   (spread–skill) ist real, aber **schwach**: Streuung sagt den *Erwartungswert*
   des Fehlers voraus, nicht den Fehler. **[VERMUTUNG, Erinnerung an
   Größenordnungen, nicht nachgeschlagen]** typische gemeldete Korrelationen
   liegen deutlich unter 0,6. Eine Größe mit dieser Eigenschaft als **binäres
   Ausschlusskriterium** zu verwenden, ist ein Kategorienfehler: man verwandelt
   eine Verteilungsaussage in ein Urteil. **Das ist exakt, was die
   Ensemble-Pflicht tut.**
2. **Ensemble-Mittel schlägt Einzelmitglied**, und der Gewinn ist beim Sprung
   von einem auf zwei Mitglieder am größten. Ihre RRF-Fusion nutzt das. Die
   Ensemble-Pflicht **wirft danach genau die Fälle weg, für die das Ensemble
   gebaut wurde** — die uneinigen. Zwei Mechanismen mit gegenläufiger Absicht
   in derselben Kette.
3. **Ranghistogramm (Talagrand-Diagramm).** Man trägt auf, an welcher Stelle
   im Ensemble die Beobachtung liegt. Flach = richtig dosierte Streuung,
   U-förmig = unterdispersiv (das System ist zu selbstsicher, die Wahrheit
   liegt zu oft außerhalb).
4. **Kein Mitglied wird verworfen.** Auch ein systematisch schlechteres
   Mitglied trägt Information, sobald es kalibriert gewichtet wird.
5. **Gerichtete statt zufälliger Störung.** Ensemble-Störungen werden nicht
   zufällig gezogen, sondern entlang der Richtungen größter Sensitivität
   (bred vectors, Toth & Kalnay 1993; singuläre Vektoren, ECMWF). Zufällige
   Störung erzeugt zu wenig Streuung pro Lauf.
6. **Verzögertes Ensemble (lagged ensemble).** Ein zusätzliches Mitglied
   gratis, indem ein bereits vorhandener älterer Lauf mitgezählt wird.

### 3.2 Was davon hier trägt

- Punkt 1 und 2 **sofort und ohne Kosten**: Ensemble-Pflicht von Tor auf
  Merkmal umstellen. Kein zusätzlicher Lauf nötig.
- Punkt 3 **sofort und ohne Kosten**, als Diagnose: Für alle Archivfälle mit
  bekannter Wahrheit den **Rang des richtigen Eintrags** in der fusionierten
  Liste protokollieren, inkl. der Kategorie „gar nicht in den Top-k". Das
  beantwortet die Frage, die Ihr Material **nicht** beantwortet: Lagen die 20
  Ziele überhaupt in der Kandidatenliste? Steht die Wahrheit meist auf Rang
  3–15, ist Ihr Problem die **Sortierung**; steht sie meist gar nicht drin,
  ist es der **Abruf** — und dann ist jede Arbeit an der Schwelle vergeblich.
  **[ÜBERTRAGUNG]** Ich halte das für die billigste und aufschlussreichste
  Einzelmessung im ganzen Vorschlagsbündel.
- Punkt 5 **mit dem einen erlaubten Zweitlauf**: Die Störungsrobustheit aus
  Ihrem Material ist der richtige Zweig, aber die Umsetzung entscheidet.
  **[ÜBERTRAGUNG]** Störung nicht als weißes Rauschen auf den Anfragevektor,
  sondern gerichtet — entlang der Hauptachse der lokalen Trefferwolke, also
  in die Richtung, in der die Nachbarschaft ohnehin auseinanderfällt. Analog
  zu bred vectors: eine zufällige Störung in 1024 Dimensionen trifft die
  empfindliche Richtung fast nie.
- Punkt 6 **[ÜBERTRAGUNG]**: Sie haben 21 000 Protokollzugriffe. Wo sich
  Anfragen ähneln, ist der frühere Trefferliste-Zustand ein kostenloses
  drittes Mitglied. Ob es genug Wiederholungen gibt, weiß ich nicht — das
  wäre zu messen.

---

## 4. Vier Verfahren

Reihenfolge ist bindend: V1 vor V2 vor V3. V4 ist unabhängig und kann parallel.

---

### V1 — Modellausgabestatistik (MOS): aus dem Tor eine Zahl machen

**[ETABLIERT]** Glahn & Lowry (1972). Man sagt nicht das Wetter aus dem
Modell vorher, sondern die **Fehlerstatistik des Modells** aus seinen eigenen
Ausgaben: eine Regression von der beobachteten Eintrittshäufigkeit auf die
Modellgrößen, angepasst am Archiv. Das Modell wird nicht besser — seine
Aussage wird ehrlich.

**Kernidee hier.** Eine logistische Regression schätzt
p(brauchbar | Merkmale) aus: bester Kosinus, bester bm25, RRF-Rangabstand,
Rangabstand zum Zweiten, Streuung der Top-k-Kosinuswerte, Anfragelänge,
Anfragetyp, Zahl der Kandidaten. **Ausgabe ist eine Wahrscheinlichkeit, kein
Ja/Nein.** Getrennt geschätzt für die zwei Vorhersagegrößen aus Abschnitt 1(a):
p(etwas Passendes vorhanden) und p(das Gelieferte ist brauchbar).

**Daten.** Der 12 000-Fälle-Korpus zum Anpassen, sauber getrennt in
Anpassungs- und Prüfteil, geblockt nach Themen (siehe 4.5). 45 Fälle **nur**
als Rauchprobe.

**Kosten.** Anpassung offline, Minuten. Zur Anfragezeit ein Skalarprodukt
über rund 10 Merkmale — unter einer Mikrosekunde. Kein Modellaufruf, kein
Netz. Erfüllt alle harten Randbedingungen.

**Prüfung an den 45.** Zuverlässigkeitsdiagramm ist bei n=45 nicht sinnvoll
(siehe 4.5). Zulässig sind nur drei Fragen: (i) Liegt der mittlere
vorhergesagte Wert in der Nähe der beobachteten Rate — grobe Kalibrierprobe?
(ii) Ist der Brier-Skill-Score gegen „immer die Grundrate" nicht **negativ**?
(iii) Reproduziert das Verfahren die 3 Fehlurteile des Prüfkorpus als hohe
Wahrscheinlichkeit — das wäre ein gutes Zeichen und ein Beleg gegen das
Etikett, nicht gegen das Verfahren.

**Was es NICHT leistet.** τ bleibt vermutlich niedrig. Der Gewinn ist nicht
Trennschärfe, sondern Kalibriertheit — und damit die Möglichkeit, V3
überhaupt anzuwenden.

---

### V2 — Isotone Kalibrierung: die Zahl geraderücken

**[ETABLIERT]** Nichtparametrische, monoton erzwungene Anpassung der
Vorhersagewahrscheinlichkeit an die beobachtete Häufigkeit; in der
Statistik Zadrozny & Elkan (2002), in der Vorhersageverifikation seit
Jahrzehnten als Kalibrierung am Zuverlässigkeitsdiagramm gebräuchlich.

**Kernidee hier.** Auch nach V1 bleibt Restverzerrung. Die isotone Regression
bildet die Rohwahrscheinlichkeit auf die im Archiv beobachtete Häufigkeit ab,
ohne eine Funktionsform anzunehmen; sie kann die Rangfolge nicht ändern (also
τ nicht verbessern) — sie macht die Zahl **wahr**. Genau deshalb ist sie hier
richtig: die Rangfolge ist das, was Sie nicht reparieren können, die Zahl das,
was Sie brauchen.

**Daten.** Ausschließlich Archivpaare (Vorhersagewert, beobachtetes Ergebnis).

**Kosten.** Nachschlagetabelle, praktisch null. Neigt bei kleinen Stichproben
zur Überanpassung — deshalb erst ab einigen hundert Fällen anwenden und
kreuzweise validieren.

**Prüfung an den 45.** Gar nicht. Bei n=45 ist isotone Regression garantiert
überangepasst. Prüfung nur am 12 000-Korpus, mit Aufteilung.

---

### V3 — Kosten-Verlust-Modell: die Schwelle aus dem Nutzen ableiten

**[ETABLIERT]** Murphy (1977); Richardson (2000); Zhu et al. (2002) zum
wirtschaftlichen Wert von Ensembles. Ergebnis: Bei Kosten C für die
Vorsichtsmaßnahme und Verlust L bei unvorbereitet eintretendem Ereignis ist
die **optimale Handlungsschwelle p\* = C/L** — und zwar unabhängig davon, wie
gut die Vorhersage ist, solange sie kalibriert ist. Der *relative
wirtschaftliche Wert* wird über den ganzen Bereich von C/L aufgetragen; das
ergibt eine Kurve, die zeigt, **für welche Nutzergruppen** das System besser
ist als die beiden trivialen Strategien „immer handeln" und „nie handeln".

**Kernidee hier — und das ist meine wichtigste Übertragung.** Ihre offene
Randbedingung 5 („wie ungleich teuer, ist nicht festgelegt") **muss nicht
beantwortet werden, um zu entscheiden.** Sie tragen den Wert über das ganze
Verhältnis „Kosten eines falschen Einspielens : Kosten eines falschen
Schweigens" auf, von 1:100 bis 100:1. Dann liest man ab: In welchem Bereich
schlägt das System beide trivialen Strategien? Ist der Bereich breit, ist die
genaue Zahl gleichgültig. Ist er schmal, wissen Sie genau, welche Frage dem
Betreiber vorzulegen ist — und es ist eine viel leichtere Frage als „was
kostet ein Fehler": es ist „liegt Ihr Verhältnis links oder rechts von 5:1?".

**[ÜBERTRAGUNG]** Und die Umkehrung ist unbequem, deshalb steht sie hier:
Zustand C **hat die offene Frage bereits beantwortet**, nur unausgesprochen.
Wer bei 45 Fällen 44-mal schweigt, handelt so, als koste ein falsches
Einspielen ein Vielfaches eines falschen Schweigens. Die genaue implizite
Zahl lässt sich heute nicht ausrechnen — gerade weil kein kalibriertes p
vorliegt —, aber die Größenordnung ist eine Behauptung, die jemand getroffen
hat. Sie steht in keinem Dokument. **Randbedingung 5 ist nicht offen, sie ist
unprotokolliert.**

**Daten.** Kalibriertes p aus V1/V2 plus die beobachteten Ergebnisse. Kein
zusätzlicher Rechenaufwand zur Anfragezeit.

**Kosten.** Nur Auswertung.

**Prüfung an den 45.** Als Anschauung zulässig, als Beleg nicht: bei n=45
schwankt jeder Punkt der Wertkurve so stark, dass sich Bereiche nicht
abgrenzen lassen. Zeichnen Sie sie mit Bootstrap-Band und zeigen Sie das Band —
es wird breiter sein als die Kurve.

---

### V4 — Gestörter Zweitlauf als gerichtete Ensemble-Störung

**[ETABLIERT]** Zhou & Croft (CIKM 2006) für die Suche; in meinem Fach die
gesamte Ensemble-Erzeugung: Anfangszustand stören, Lauf wiederholen,
Streuung als Unsicherheitsmaß. Gerichtete Störung (bred vectors,
Toth & Kalnay 1993) schlägt zufällige deutlich.

**Kernidee hier.** Einen zweiten Abruf mit gestörtem Anfragevektor fahren und
die **Überlappung der beiden Trefferlisten** als kontinuierliches Merkmal in
V1 geben — nicht als Tor. Die Störung gerichtet wählen: entlang der
Hauptachse der lokalen Nachbarschaft der Kandidaten, nicht als isotropes
Rauschen. Damit vereinigt V4 zugleich den zweiten in Ihrem Material genannten
Zweig (Kohärenz der Nachbarschaft), denn die Hauptachsenrichtung ist eine
Aussage über genau diese Geometrie.

**Daten.** Einbettungen aller Einträge (vorhanden), ein zweiter Suchlauf.

**Kosten.** Verdopplung der Abrufkosten. Kein Modellaufruf — die Störung ist
Vektorarithmetik. Damit innerhalb Randbedingung 4, aber es ist der einzige
Vorschlag, der überhaupt etwas kostet. **[ÜBERTRAGUNG]** Deshalb: erst V1–V3
bauen und messen. Bringt die Kalibrierung schon genug, ist V4 verzichtbar —
und dann sind die 45 Fälle zu klein, um seinen Restgewinn nachzuweisen.

**Prüfung an den 45.** Nur als Vorzeichenprobe. Der Zusatzgewinn eines
Merkmals in einer Regression ist an 45 Fällen grundsätzlich nicht belegbar.

---

### 4.5 Stichprobengröße — was mein Fach verlangen würde

**[ETABLIERT]** Die Verifikation ist eine Schätzung mit Vertrauensbereich, und
für binäre Ereignisse ist der Bereich bei kleinen Stichproben brutal.

- **Reine Arithmetik zu Ihren Zahlen:** Bei 15 Treffern aus 45 ist der
  Standardfehler des Anteils rund 0,07, das 95-Prozent-Intervall also grob
  **±14 Prozentpunkte**. Zwei Betriebsarten, die sich um 10 Prozentpunkte
  unterscheiden, sind an 45 Fällen **nicht unterscheidbar**. Die Tabelle in
  Ihrem Material zeigt weit größere Unterschiede (15 gegen 1) — die sind real.
  Alles Feinere ist es nicht.
- **Zuverlässigkeitsdiagramm:** Faustregel meines Fachs — **mindestens rund
  100 Fälle je Klasse**, bei 5 bis 10 Klassen also **500 bis 1000 Fälle als
  Untergrenze**, und das nur für eine grobe Kurve.
- **Brier-Skill-Score-Unterschiede** in der Größenordnung weniger Hundertstel:
  **einige Tausend Fälle**. **[VERMUTUNG]** Das ist die Größenordnung, in der
  sich V1 gegen V1+V4 entscheiden wird — Ihr 12 000-Korpus reicht dafür, die
  45 nicht annähernd.
- **Es zählen Ereignisse, nicht Fälle.** Für die Größe „richtig geschwiegen"
  haben Sie 10 Ereignisse. Zehn. Jede Aussage darüber, auch die fehlerfreie
  Schwelle bei 0,545, steht auf zehn Beobachtungen.
- **Unabhängigkeit.** **[ETABLIERT]** Bei uns sind benachbarte Tage und
  benachbarte Gitterpunkte nicht unabhängig; die effektive Stichprobe ist
  kleiner als die gezählte, und Vertrauensbereiche werden mit einem
  **blockweisen Bootstrap** gerechnet. **[ÜBERTRAGUNG]** Ihre Anfragen aus
  demselben Sachgebiet sind ebenso wenig unabhängig. Blockweise nach Thema
  bootstrappen, sonst sind alle Intervalle zu schmal — auch die am
  12 000-Korpus.

**Verdikt zu den 45 Fällen:** Sie sind eine ausgezeichnete **Fehlersuche** und
ein gutes Werkzeug, um grobe Kaputtheit zu erkennen. Sie sind **kein
Verifikationsarchiv**. Der Wert Ihrer 45 lag bisher nicht in den Zahlen,
sondern im Handnachsehen der 20 Fälle — das ist die beste Arbeit im ganzen
Material, und sie ist qualitativ. **[ÜBERTRAGUNG]** Genau die sollte
fortgesetzt werden: auf 100 bis 150 handgelesene, dreistufig etikettierte
Fälle. Das ist mehr wert als 12 000 automatisch etikettierte, wenn die
Etiketten das falsche Ereignis beschreiben.

---

## 5. Meine unbequemste Frage

**Sie verifizieren den Abruf. Sie haben nie das Ereignis verifiziert, das
zählt.**

Mein Fach hat diesen Fehler ein halbes Jahrhundert lang gemacht: Wir haben die
Vorhersage gegen die Beobachtung geprüft und für gut befunden, und erst
Murphy (1993, „What is a good forecast?") hat durchgesetzt, dass eine
Vorhersage drei Arten von Güte hat — Übereinstimmung mit der Wahrheit,
Konsistenz mit dem eigenen Urteil, und **Wert für den, der sie benutzt** — und
dass die dritte weder aus der ersten folgt noch mit ihr korreliert sein muss.

Ihr Ereignis ist heute „der ausgelieferte Eintrag trägt die richtige Kennung".
Das Ereignis, um das es geht, ist „der ungefragt eingespielte Text hat die
Arbeit eines Menschen besser gemacht". Sie haben 21 000 Protokollzugriffe und
wissen bei keinem einzigen, ob er genützt hat.

Und dann steht da diese Zahl: **12 von 20 „teilweise — berührt das Thema,
beantwortet die Frage nicht".** Nicht 5 daneben, nicht 3 richtig — die
**Mehrheit** ist thematisch plausibel und sachlich nutzlos. Bei einer Warnung
wäre das die Sorte, die man nicht widerlegen kann und nicht gebrauchen kann,
und mein Fach hat teuer gelernt: **Solche Vorhersagen zerstören Vertrauen
schneller als falsche.** Eine falsche Warnung wird bemerkt und korrigiert. Eine
plausible, nutzlose wird gelesen, halb geglaubt und färbt das Urteil, ohne dass
je jemand merkt, dass sie nichts enthielt. Genau das ist die Betriebsart, in
der Sie „ungefragt in den Arbeitskontext einspielen".

Die Frage lautet also:

> **Wenn die häufigste Ausgabe Ihres Systems nicht falsch, sondern plausibel
> und nutzlos ist — welche Ihrer 45 Zahlen misst diesen Schaden? Und wenn
> keine: warum wird über die Schwelle diskutiert, bevor jemand die Kosten
> derjenigen Klasse kennt, die den Bestand stellt?**

Zwei Nachbrenner, kürzer:

- Zustand C hat 34-mal geschwiegen und 1-mal gesprochen. Wer hat das
  Verhältnis „falsch sprechen zu falsch schweigen" festgelegt, das dieser
  Betriebspunkt unterstellt — und steht es irgendwo? **[ÜBERTRAGUNG]** Wenn
  nicht: das ist keine offene Frage an ein Konsil, das ist eine unprotokollierte
  Entscheidung, die längst wirkt.
- Und die Größe, an der die ganze Ensemble-Pflicht hängt, ist im Prüfkorpus
  **durchweg 0**. Eine konstante Größe kann nichts trennen. Ist dieser Schalter
  jemals gegen eine Alternative gemessen worden, oder nur gegen „aus"?

---

## 6. Was ich nicht weiß

- Ob der 12 000-Fälle-Korpus dieselbe Zielgröße etikettiert wie die 45 (exakte
  Kennung?). Trifft er dasselbe fehlerhafte Etikett, überträgt sich das
  Etikettenrauschen auf jede daran angepasste Kalibrierung.
- Ob die Ziele der 20 Fehlgriffe überhaupt in der Kandidatenliste lagen. Ohne
  das ist nicht entscheidbar, ob hier ein Kalibrierungs- oder ein
  Abrufproblem vorliegt. **Diese Messung würde ich vor allen vier Verfahren
  ansetzen.**
- Ob die 21 000 Protokollzugriffe wiederkehrende Anfragen enthalten (Grundlage
  für ein kostenloses drittes Ensemble-Mitglied).
- Wie stark der Bestand seit Erhebung der Kosinuswerte gewachsen ist. Bei
  wachsendem Bestand verschiebt sich die Verteilung der Bestwerte
  systematisch nach oben — jede feste Schwelle wandert dann von selbst.
  **[VERMUTUNG]**, aber leicht zu prüfen: Bestwerte gegen Erhebungsdatum
  auftragen.
- Nichts davon habe ich im Repo nachgemessen; der Auftrag war Lesen, nicht
  Ändern, und ich habe mich auf das Konsil-Material beschränkt.

---

## Zusammenfassung in fünf Zeilen

1. Es sind zwei Vorhersagegrößen, nicht eine — und die Schwelle für die eine
   steuert die Entscheidung über die andere.
2. τ = 0,10 misst einen von drei Termen der Güte; über Nutzbarkeit ist damit
   nichts gesagt.
3. Ersetzen Sie das Tor durch eine kalibrierte Zahl (V1+V2). Kosten: praktisch
   null, keine harte Randbedingung verletzt.
4. Die offene Kostenfrage muss nicht beantwortet werden — die Wertkurve über
   alle Kostenverhältnisse zeigt, ob sie überhaupt zählt (V3).
5. 45 Fälle sind eine Rauchprobe, kein Archiv: ±14 Prozentpunkte, zehn
   Ereignisse in der entscheidenden Klasse. Die 100 bis 150 **handgelesenen**
   Fälle wären mehr wert als die 12 000 automatisch etikettierten.
