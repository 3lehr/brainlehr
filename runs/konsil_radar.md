# Konsil „Das zweite Signal" — Stellungnahme aus der Radar- und Sonar-Detektionstheorie

Stand 2026-08-20T22:40:00+0200. Verfasst ohne Kenntnis der übrigen Rollen und
ihrer Antworten.

**Kennzeichnung durchgängig:** `[GEMESSEN]` = in meinem Fach etabliert und
publiziert, mit Verfahrensnamen · `[ÜBERTRAGUNG]` = meine Hypothese für diesen
Fall, ungeprüft · `[VERMUTUNG]` = Meinung ohne Beleg · `[GEPRÜFT]` = ich habe
es heute im Repo nachgesehen, Fundstelle genannt · `[MODELLWISSEN]` = aus dem
Gedächtnis zitiert, nicht nachgeschlagen, deshalb mit Vorbehalt.

---

## 0. Die zwei Sätze, auf die ich hinauswill

**Ihr habt keinen kaputten Detektor. Ihr habt einen funktionierenden Detektor
und keinen Klassifikator.** Der beste Kosinuswert trennt „ist überhaupt ein
Ziel im Beam" bei 0,545 fehlerfrei. Genau das ist in meinem Fach die Aufgabe
eines Detektionsstatistiks, und mehr wird ihm nie zugetraut. Dass er die
gelieferten Echos nicht *klassifiziert*, ist kein Befund, sondern der
Normalzustand seit 1945.

**Und: eure 20 Fehlgriffe sind kein Rauschproblem, sondern ein Clutterproblem.**
Der Unterschied ist in meinem Fach der teuerste Unterschied überhaupt, und er
entscheidet, welche Verfahren helfen können und welche prinzipiell nicht.
Gegen Rauschen hilft eine bessere Schwelle. Gegen Clutter hilft **keine**
Schwelle — nur eine zweite, physikalisch andere Beobachtungsachse. Das ist die
Lehre, für die mein Fach fünfzehn Jahre und sehr viel Geld gebraucht hat.

---

## 1. Übersetzung in meine Sprache

### Was worauf abbildet

| Euer System | Mein Fach |
|---|---|
| Anfrage | Sendeimpuls, Beleuchtung eines Raumausschnitts |
| Ein Eintrag im Bestand | eine Auflösungszelle (Range-Doppler-Bin) |
| Kosinuswert eines Eintrags | Amplitude des Rückstreuechos in dieser Zelle |
| Der gesuchte Eintrag | das Ziel |
| Die ~5200 übrigen Werte | Hintergrund |
| „Ausliefern oder schweigen" | Detektionsentscheidung H1/H0 |
| Ensemble-Pflicht (Betriebsart C) | eine sehr hoch gesetzte feste Schwelle |
| Betriebsart B | Schwelle bei minus unendlich, jedes Bin meldet |

Bis hierher trägt die Übersetzung sauber. Jetzt die Stelle, an der eure
Fallgruppen sich sortieren, und sie ist der Kern:

| Eure Fallgruppe (n) | Mein Fach |
|---|---|
| verhinderte Fehler, 10 — Frage ohne Antwort im Bestand | **kein Ziel im Beam.** Reines Rauschen. |
| verworfene Treffer, 14 | **Ziel vorhanden, Echo schwach.** Detektionsverlust. |
| „brauchbar, nur anders", 3 | Ziel detektiert, **Ground-Truth-Zuordnung falsch** |
| „teilweise", 12 | **Clutter.** Reale, starke Rückstreuung von etwas, das nicht das Ziel ist. |
| „daneben", 5 | teils Clutter, teils Rauschspitze über der Schwelle |

**Und damit erklärt sich der Befund, der euch irritiert, restlos und ohne
Rätsel:** Rauschen ist schwach (Median 0,4843). Ziele sind mittelstark
(0,5970). **Clutter ist stärker als das Ziel** (0,6030). Genau so sieht jedes
Bodenradar aus, das über eine Stadt schaut: Häuser, Zäune und Strommasten
liefern Echos, die den eines Flugzeugs um Größenordnungen übertreffen. Ein
Amplitudenschwellwert findet dann zuverlässig die Stadt und nie das Flugzeug.
Dass euer stärkster Ausfall bei 0,6374 liegt — dem höchsten Wert der Gruppe —
ist in dieser Lesart kein Ausreißer, sondern der Erwartungswert. `[ÜBERTRAGUNG,
aber eine mit sehr guter Passung]`

### Wo die Übersetzung NICHT trägt — vier Bruchstellen

Das ist der Teil, den ich für den nützlichsten halte, weil er sagt, welche
meiner Angebote man nicht kaufen soll.

**(1) Ich habe ein physikalisches Rauschmodell, ihr habt keins.**
Thermisches Rauschen ist kTB, Rayleigh-verteilt, stationär, ergodisch,
zielunabhängig — deshalb kann CFAR eine *Garantie* aussprechen („konstante
Falschalarmrate", nicht „ungefähr konstant"). Die Verteilung eurer Kosinuswerte
ist nicht hergeleitet, sondern beobachtet, und sie hängt von der Anfrage *und*
von der Zusammensetzung des Bestands ab. Damit überträgt sich CFAR **als
Normalisierungsheuristik, nicht als Garantie**. Wer den Namen kauft und die
Garantie mitzukaufen glaubt, hat sich geirrt. `[GEMESSEN, dass es an dieser
Voraussetzung hängt]`

**(2) Bei mir ist Clutter nie ein Teil des Ziels.** Ein Bodenecho ist nicht zu
60 % ein Flugzeug. Eure Klasse „teilweise" ist es aber genau: sachlich in der
Nähe, nutzlos für die Frage. Die Detektionstheorie setzt H0 und H1 als
**disjunkt** voraus; ein Zwischenzustand ist im Formalismus nicht vorgesehen.
Zwölf von zwanzig Fehlgriffen sind bei euch dieser Zwischenzustand. **Hier hat
mein Fach am wenigsten anzubieten**, und ich sage das ausdrücklich, damit die
Übertragung nicht überzogen wird.

**(3) Meine Referenzzellen sind garantiert nachbarschaftlich, eure nicht.**
CFAR schätzt den Hintergrund aus Zellen, die *räumlich* neben der Prüfzelle
liegen — deshalb enthalten sie mit hoher Wahrscheinlichkeit kein zweites Ziel.
Im Einbettungsraum ist „Nachbarschaft" semantisch: die Umgebung des Ziels ist
exakt der Ort, an dem euer Clutter wohnt. Das sogenannte **Masking** —
zielhaltige Referenzzellen heben die Schwelle und löschen die Detektion —
ist bei mir der Sonderfall (Mehrzielsituation) und bei euch der **Regelfall**.
Konsequenz, und sie ist hart: Ein Mittelwert-CFAR (CA-CFAR) ist hier
unbrauchbar. Nur zensierte Verfahren (OS-CFAR, TM-CFAR) kommen in Frage.
`[GEMESSEN: Masking und die Überlegenheit der Ordnungsstatistik bei
Mehrzielsituationen sind Standardstoff; Rohling 1983, „Radar CFAR thresholding
in clutter and multiple target situations". [MODELLWISSEN] für die genaue
Zitatstelle.]`

**(4) Integrationsgewinn überträgt sich NICHT.** Das ist die wichtigste
Bruchstelle, weil sie einen der beiden im Material genannten Vorschläge direkt
betrifft. Ich gewinne Empfindlichkeit, indem ich viele Impulse auf dasselbe
Ziel integriere — kohärent geht der Signal-Rausch-Abstand mit N, inkohärent
etwa mit √N. Das funktioniert **nur, weil jede Impulswiederholung eine
unabhängige Rauschrealisierung liefert**. Euer System ist deterministisch: ein
zweiter Lauf derselben Anfrage gegen denselben Bestand liefert exakt dasselbe
Ergebnis und damit **null Bit** neue Information. Wer „zweiter Lauf" sagt, muss
sagen, **wo die Unabhängigkeit herkommt** — sonst integriert er Nullen.
Die Störungsrobustheit (Zhou & Croft) ist genau deshalb kein
Integrationsverfahren, sondern das Analogon zur **Frequenzagilität**: man
verstimmt den Sender, um das Clutter zu dekorrelieren, während das Ziel
korreliert bleibt. Das ist eine völlig andere Denkfigur, und sie steht und
fällt damit, ob die Störung wirklich dekorreliert. `[GEMESSEN für den
Radarteil; ÜBERTRAGUNG für die Folgerung]`

---

## 2. Was die Anfragegüte-Vorhersage aus meiner Sicht übersieht

Vier Dinge. Das erste ist das größte.

### 2.1 Sie vermischt Detektion und Klassifikation und misst dann die Mischung

In meinem Fach sind das **zwei getrennte Stufen mit getrennten Merkmalen und
getrennten Gütemaßen**, und niemand käme auf die Idee, sie in einer Zahl zu
bewerten:

- **Detektion:** Ist in dieser Zelle etwas? Merkmal: Amplitude (bzw. ihr
  normalisiertes Verhältnis zum Hintergrund). Gütemaß: ROC, Pd bei gegebener
  Pfa.
- **Klassifikation:** Was ist es? Merkmale: **niemals Amplitude** — sondern
  Doppler-Spektrum, Polarisation, Range-Profil, Bewegungsverhalten über die
  Zeit. Gütemaß: Verwechslungsmatrix.

Euer Befund lautet, in meine Sprache übersetzt: *„Die Amplitude löst die
Detektion perfekt und die Klassifikation gar nicht."* Das ist kein Skandal,
sondern eine Bestätigung der Lehrbuchlage. Das Fach QPP kommt auf τ = 0,10, weil
es mit einem **Detektionsstatistik** eine **Klassifikationsfrage** stellt. Ein
τ von 0,10 ist unter dieser Bedingung nicht enttäuschend, sondern erwartbar.

**Praktische Folgerung, und sie kostet euch nichts:** Trennt die Messung. Zwei
ROC-Kurven statt einer Kreuztabelle:
- ROC-A: „liegt überhaupt eine Antwort im Bestand?" (35 lösbar gegen 10 nicht).
  Auf dieser Kurve ist euer Kosinuswert **hervorragend** — 0,545 trennt
  fehlerfrei.
- ROC-B: „ist das Ausgelieferte richtig?" (15 gegen 20). Auf dieser Kurve ist er
  **wertlos**, und das lässt sich aus euren eigenen Zahlen ablesen: die Träger
  überlappen zu rund 93 % (0,5555–0,6374 gemeinsam bei einer Trefferspanne von
  0,5497–0,6375), und die **Mediane sind vertauscht** (0,6030 falsch gegen
  0,5970 richtig). Aus Median und Spannweite lässt sich eine AUC nicht
  berechnen — was sie aber ausschließen, ist eine AUC nennenswert über 0,5.
  `[Arithmetik auf euren Zahlen, keine neuen Zahlen]`

Solange beide Fragen in einer Tabelle stehen, sieht ein perfekter Detektor wie
ein Versager aus.

### 2.2 Sie bewertet Betriebspunkte statt Kurven

B, C und die Schwellenschicht sind **drei Punkte**. Mein Fach hat die
ROC-Kurve 1954 unter anderem deshalb erfunden, weil der Vergleich zweier
Detektoren an je einem Betriebspunkt systematisch in die Irre führt: Man kann
jeden Detektor durch Schwellenverschiebung an jedem einzelnen Maß beliebig gut
aussehen lassen. `[GEMESSEN: Peterson, Birdsall & Fox 1954, „The theory of
signal detectability"; Marcum 1947/1960 für die Pd-Pfa-Tafeln. [MODELLWISSEN]
für die Jahreszahlen.]`

Ihr habt eine kontinuierliche Statistik und 45 gelabelte Fälle. **Die volle
Kurve kostet euch einen Sweep über die vorhandenen Zahlen, keinen einzigen
neuen Lauf.** Dass sie nicht im Material steht, ist die auffälligste Lücke des
Dokuments.

### 2.3 Sie fragt nach einem Kostenverhältnis, das niemand kennen kann

Eure Randbedingung 5 sagt: falsch liefern und falsch schweigen sind ungleich
teuer, wie ungleich ist offen. **Mein Fach hat diese Frage vor achtzig Jahren
für unbeantwortbar erklärt und sie umgangen** — das ist der Übergang von der
Bayes-Entscheidung zum **Neyman-Pearson-Kriterium**: Man legt *kein*
Kostenverhältnis fest. Man fixiert die **Falschalarmrate** auf einen Wert, den
der Bediener aushält, und maximiert die Entdeckungswahrscheinlichkeit bei
genau dieser Rate. `[GEMESSEN, Neyman & Pearson 1933; CFAR heißt wörtlich
„constant false alarm rate" und ist die technische Umsetzung genau dieser
Entscheidung.]`

Der Grund für diesen Umweg ist derselbe wie bei euch: **Kosten sind
unbeobachtbar, Raten sind beobachtbar.** Niemand kann sagen, was ein
abgeschossenes Zivilflugzeug gegen einen durchgelassenen Bomber „kostet". Aber
jeder Bediener kann sagen, wie viele Fehlalarme pro Stunde er verkraftet, bevor
er den Schirm ignoriert.

**Für euch heißt das:** Fragt nicht „wie viel teurer ist eine falsche
Einspielung als ein Schweigen". Fragt den Betreiber: **„Wie viele nutzlose
Einspielungen pro 100 Prompts erträgst du, bevor du anfängst, den Block
grundsätzlich zu überlesen?"** Diese Frage ist beantwortbar, und die Antwort
lässt sich direkt gegen euer Protokoll mit 21 000 Zugriffen rechnen — jede
Schwelle ergibt dort eine Einspielrate pro Prompt. Das ist eine
Betriebsgröße, keine Philosophie.

Und der Grund, warum diese Größe die richtige ist, ist ebenfalls in meinem Fach
gemessen worden, nicht ausgedacht: **Die Vigilanzforschung ist an Radarschirmen
entstanden** (Mackworth 1948, Clock Test). Das harte Ergebnis lautet, dass die
Entdeckungsleistung eines Bedieners bei seltenen Ereignissen **innerhalb der
ersten halben Stunde messbar abfällt** — und der Abfall hängt an der
Ereignisrate, nicht an der Wichtigkeit. `[GEMESSEN; [MODELLWISSEN] für die
Zahlen im Detail.]` Übertragen: Ein System, das zu oft Belangloses einspielt,
zerstört nicht einen einzelnen Arbeitsschritt, sondern die **Aufmerksamkeit für
alle folgenden Einspielungen** — auch für die richtigen. Das ist die eigentliche
Asymmetrie, und sie wirkt nicht pro Fall, sondern kumulativ über die Sitzung.

### 2.4 Sie schätzt Raten aus zweistelligen Stichproben

Mein Fach hat eine Faustregel für den Aufwand, eine Falschalarmrate zu
belegen, und sie ist unbequem: Um Pfa = 10⁻⁶ zu **messen**, braucht man in der
Größenordnung 10⁷ unabhängige Rauschzellen. Deshalb wird Pfa in der Praxis nie
gemessen, sondern aus dem Verteilungsmodell **hergeleitet** und nur
stichprobenartig geprüft. `[GEMESSEN, Standardpraxis.]`

Eure „10 von 10 richtig geschwiegen" ist eine schöne Zahl. Das exakte
binomiale 95-%-Intervall dazu reicht nach unten bis **0,69** (zweiseitig:
0,025^(1/10) = 0,6915). `[Arithmetik, nachrechenbar.]` Mit anderen Worten: Die
Daten sind mit einer wahren Schweigequote von 70 % verträglich.

Und die Schwelle selbst: Zwischen 0,5410 (höchster verhinderter Fehler) und
0,5497 (niedrigster verworfener Treffer) liegen **0,0087**, gestützt auf **zwei
Beobachtungen**. In meinem Fach heißt ein so gesetzter Wert
„auf der eigenen Realisierung angepasst" und wird grundsätzlich als
optimistisch behandelt, bis er an unabhängigen Daten steht.

**Das ist keine theoretische Sorge, sondern in eurem eigenen Quelltext
dokumentiert.** `[GEPRÜFT: `kern/relevanzlage.py`, Kopfkommentar]` — dort steht,
dass eine erste Fassung derselben Messung „12 gegen 12 Fälle eine saubere
Trennung" zeigte, „die bei 40 gegen 40 verschwand". Dieselbe Fehlerklasse,
dasselbe Modul, vier Tage vorher. Der zweite Prüfkorpus mit über 12 000 Fällen
liegt laut Randbedingung 3 vorhanden und kostenlos nutzbar bereit.

---

## 3. Vier Verfahren, die ich für anwendbar halte

Alle vier halten die Randbedingungen ein: kein Modellaufruf, alles lokal,
höchstens ein zweiter Lauf.

---

### V1 — Kosinuswert durch OS-CFAR-Normalisierung ersetzen

**Kernidee.** Der Rohwert 0,60 bedeutet nichts, solange man nicht weiß, was der
Bestand für *diese* Anfrage überhaupt hergibt: Eine allgemein formulierte
Anfrage hebt den ganzen Hintergrund, eine spezifische senkt ihn. Man ersetzt
den Absolutwert durch das Verhältnis des Spitzenwerts zu einem **robusten
Schätzer des Hintergrunds derselben Anfrage** — konkret zur k-ten
Ordnungsstatistik über alle ~5200 Werte (z. B. Median und normierter
Medianabstand, MAD), wobei die obersten Prozent zensiert werden, damit das Ziel
seinen eigenen Hintergrund nicht anhebt. Genau das ist OS-CFAR, und es ist die
Standardantwort auf „unbekannter, anfrageabhängiger Rauschpegel".

**Was es an Daten braucht.** Nichts Neues. `[GEPRÜFT:
`knowledge_mcp_server.py`, `_embedding_ranking()` liest **alle** Zeilen aus
`knowledge_embeddings` und berechnet den Kosinus zu jeder — die vollständige
Score-Verteilung über den ganzen Bestand liegt zur Anfragezeit bereits im
Speicher und wird über `werte.extend(...)` sogar schon durchgereicht.]

**Was es kostet.** Ein Median und ein MAD über eine Liste, die schon existiert:
ein Sortiervorgang, den der Code ohnehin ausführt. **Praktisch null.**

**Der wichtige Zusatzbefund, und er ist der eigentliche Ertrag dieses
Vorschlags.** Ihr habt so etwas schon, aber mit dem falschen Nenner.
`[GEPRÜFT: `kern/embeddings.py`, `channel_discrimination()` rechnet
`(top − median) / (top − min)`.]` Drei Einwände aus meinem Fach:
1. Der Nenner ist die **Spannweite**, und die enthält mit `min` die
   **extremste Ordnungsstatistik überhaupt** — der varianzreichste Schätzer,
   den man wählen kann. Ein einziger Ausreißer nach unten skaliert die ganze
   Statistik. Ordnungsstatistik-CFAR verwendet bewusst einen Rang bei etwa
   75 % der Stichprobe, nie das Extremum. `[GEMESSEN]`
2. `top` steht in Zähler **und** Nenner. Damit sättigt die Größe und kann einen
   sehr starken Ausschlag nicht mehr von einem starken unterscheiden — die
   Dynamik, auf die es ankommt, wird weggekürzt.
3. Ein robustes z-Maß `(top − Median) / (1,4826 · MAD)` hat keine dieser
   Eigenschaften und ist derselbe Einzeiler.

**Und eine Frage, die vor allem anderen zu klären ist:** Im Material steht,
„Abstand zum Median der **Trefferliste**" trenne nicht. Der Median der Top-k
und der Median über alle 5200 sind zwei völlig verschiedene Größen — nur der
zweite ist eine Hintergrundschätzung, der erste ist eine Formstatistik der
Trefferwolke. **Wenn gegen den Top-k-Median gemessen wurde, ist CFAR nicht
geprüft worden.** Das ist vor jedem weiteren Schritt zu klären.

**Prüfung an den 45 Fällen.** Für jeden Fall die vorhandenen Kosinuswerte
sichern, `(top − Median_alle) / (1,4826 · MAD_alle)` bilden, ROC-A sweepen.
Erfolgsmaß: trennt es die 10 Rauschfälle von den 35 Zielfällen **mit größerem
Abstand** als der Rohwert (also nicht nur fehlerfrei, sondern mit breiterer
Lücke)? Eine fehlerfreie Trennung habt ihr schon; gesucht ist **Marge**, denn
nur Marge überlebt den Wechsel auf den 12 000er-Korpus.
**Erwartung offen. Auf ROC-B — richtig gegen falsch geliefert — erwarte ich
keinen Gewinn**, weil V1 ein Detektionsverfahren ist. `[ÜBERTRAGUNG]`

---

### V2 — Punktziel gegen Flächenclutter: die Konzentration des Echos messen

**Kernidee.** Das ist mein Hauptvorschlag, weil er die einzige Klasse angeht,
die Amplitude prinzipiell nicht lösen kann. In der Radartechnik unterscheidet
man ein **Punktziel** von **Flächenclutter** nicht an der Stärke, sondern an
der **Verteilung der Rückstreuung über die Auflösungszellen**: Ein Flugzeug
konzentriert sein Echo auf wenige Zellen, Bodenclutter verteilt es gleichmäßig
über viele. Übertragen: Ein Eintrag, der eine Frage *beantwortet*, trägt die
Ähnlichkeit in **einer** Passage; ein Eintrag, der nur *thematisch nah* ist,
verteilt sie gleichmäßig über alle seine Passagen. Gemessen wird also nicht
„wie ähnlich", sondern „**wie konzentriert**" — etwa als Verhältnis der besten
Passagenähnlichkeit zur mittleren über die Passagen desselben Eintrags, oder
als Gini-/Entropiemaß über die Passagenwerte.

**Warum ich das für die Klasse „teilweise" (12 von 20) für den aussichtsreichsten
Weg halte:** Genau diese Einträge sind per Handbefund „berührt das Thema,
beantwortet die Frage nicht". Das ist die Definition von Flächenclutter.
`[ÜBERTRAGUNG — dies ist eine Hypothese, kein Ergebnis.]`

**Was es an Daten braucht.** Einbettungen auf **Passagenebene** statt auf
Eintragsebene. Einmalig offline zu erzeugen, kein Netz, dasselbe Modell.

**Was es kostet — und hier bin ich ehrlich unsicher.** Bei etwa 5200 Einträgen
und geschätzt 3–8 Passagen je Eintrag `[SCHÄTZUNG]` wächst die Zahl der
Vektoren auf grob 15 000–40 000, der Anfrage-Scan also um Faktor 3–8. In eurer
heutigen Umsetzung ist das **nicht** vernachlässigbar: `[GEPRÜFT:
`kern/embeddings.py`, `cosine_similarity()` ist reines Python — Summenschleifen
über 1024 Elemente je Eintrag, und die **Norm der Anfrage wird für jeden der
5200 Einträge neu berechnet**.]` Ein Faktor 5 auf einem Pfad, der an jedem
Prompt hängt, ist eine Betriebsfrage und keine Kleinigkeit. Zwei Auswege, beide
sauber: die Anfragenorm einmal berechnen und Vektoren normiert speichern (dann
ist der Kosinus ein reines Skalarprodukt), oder den Passagen-Scan nur auf die
Top-k des ersten Durchgangs anwenden — das ist ohnehin die
CFAR-typische **Zwei-Stufen-Architektur**: billige Detektion über alles,
teure Klassifikation nur auf den Detektionen. Damit fällt der Aufschlag auf
k·Passagen statt 5200·Passagen und ist praktisch null.

**Prüfung an den 45 Fällen.** Die 15 richtigen gegen die 12 „teilweise" plus 5
„daneben" — das ist die eigentliche ROC-B. Erfolgsmaß: AUC deutlich über 0,5.
**Positivkontrolle mitführen:** die 3 als „brauchbar, nur anders" erkannten
Fälle müssen sich wie Treffer verhalten, nicht wie Clutter; tun sie es nicht,
ist zuerst das Merkmal verdächtig. Ich halte 45 Fälle für zu wenig, um daraus
eine Schwelle zu setzen — aber für genug, um zu sehen, ob **überhaupt ein
Trenneffekt** existiert. Das ist die richtige Frage in dieser Phase.

---

### V3 — Zwei Läufe mit dekorrelierender Störung (Frequenzagilität)

**Kernidee.** Ein zweiter Lauf hilft nur, wenn er etwas Unabhängiges sieht (s.
Bruchstelle 4). Die Radaranalogie ist nicht Integration, sondern
**Frequenzagilität**: Man verstimmt den Sender leicht, weil Clutter dabei
dekorreliert, während das Ziel korreliert bleibt. Übertragen heißt das: die
**Anfrage** stören — Teilanfrage aus einem Satzteil, ausgelassenes Schlüsselwort,
umgestellte Reihenfolge — und messen, wie stabil die Trefferliste bleibt
(Rangkorrelation oder Überlappung der Top-k). Ein Eintrag, der die Frage
tatsächlich beantwortet, sollte oben bleiben; ein thematischer Nachbar,
der nur an einem Stichwort hängt, sollte wegkippen.

**Was es an Daten braucht.** Nichts Neues, aber eine zweite
Anfrageeinbettung — also ein Aufruf des Einbettungsmodells, kein
Sprachmodellaufruf. Ob das in eurem Zeitbudget liegt, kann ich nicht
beurteilen und behaupte es nicht. **Wenn nicht**, gibt es die billigere
Variante: die Störung im **Vektorraum** statt am Text (Anfragevektor leicht
auslenken, z. B. entlang der Hauptkomponenten des Bestands). Dann kostet es nur
einen zweiten Scan.

**Was es kostet.** Ein zweiter Durchgang je Anfrage — laut Randbedingung 4
vertretbar. Damit ist das Budget aber **aufgebraucht**: V3 und ein anderes
Zwei-Lauf-Verfahren schließen sich aus.

**Prüfung an den 45 Fällen.** Stabilitätsmaß je Fall berechnen, ROC-B sweepen.
**Die entscheidende Vorprüfung ist eine andere, und ohne sie ist der Rest
wertlos:** Erzeugt die Störung überhaupt Varianz? Wenn die gestörte
Trefferliste in 40 von 45 Fällen identisch ist, ist die Störung zu schwach und
das Merkmal konstant — das ist derselbe Fehler wie ein Prüfstand, der ein Feld
fest verdrahtet. Erst die Varianz messen, dann die Trennschärfe.
`[GEMESSEN, dass Dekorrelation die Voraussetzung ist; ÜBERTRAGUNG, dass eine
Textstörung sie leistet.]`

---

### V4 — Track-before-Detect: über die Sitzung integrieren statt über die Anfrage

**Kernidee.** Mein Fach detektiert schwache Ziele nicht in einem Blick, sondern
**über die Zeit**: Man senkt die Schwelle je Einzelblick weit ab, akzeptiert
viele Rohdetektionen und meldet erst, wenn sich über N Blicke eine konsistente
Spur bildet (binäre M-aus-N-Integration, Track-before-Detect). Eine
Clutterspitze ist ortsfest oder zufällig, ein Ziel bleibt konsistent. Übertragen:
Eine Sitzung ist eine **Spur**. Ein Eintrag, der über mehrere aufeinander
folgende Prompts derselben Sitzung immer wieder in den Kandidatenkreis kommt,
ist etwas anderes als einer, der bei einem Prompt zufällig oben steht — auch bei
gleichem Kosinuswert.

**Warum das hier besonders passt.** Es löst euer Kernproblem ohne jedes neue
Merkmal: Ihr könnt die Schwelle **drastisch senken** (also die 14 verworfenen
Treffer zurückgewinnen) und die Fehlalarmrate trotzdem halten, weil die
zweite Bedingung — Wiederkehr — sie wegfiltert. Genau dafür wurde das Verfahren
erfunden. `[GEMESSEN für Radar; ÜBERTRAGUNG hier. Faustregel aus der Literatur:
optimales M ≈ 1,5·√N. [MODELLWISSEN], vor Gebrauch nachschlagen.]`

**Was es an Daten braucht.** Eine Sitzungskennung und einen Ringpuffer über die
letzten N Anfragen. Sonst nichts.

**Was es kostet.** Nichts an Rechenzeit. Der Preis ist ein anderer und muss
benannt werden: **Latenz in der Sache.** Ein Eintrag wird frühestens beim
M-ten Prompt eingespielt. Wer eine einmalige Frage stellt, bekommt nie eine
Antwort. Das ist ein echter Verlust, kein Rundungsfehler.

**Prüfung — und hier ist die unangenehme Wahrheit: an den 45 Fällen geht es
nicht.** Die 45 Fälle sind Einzelschüsse; ein Verfahren, das über Sitzungen
integriert, ist an Einzelschüssen prinzipiell nicht prüfbar. **Ich sage das
ausdrücklich, statt eine Prüfvorschrift zu erfinden, die nichts prüft.**
Prüfbar ist es am **Betriebsprotokoll mit 21 000 Zugriffen**, sofern sich
daraus Sitzungen und ihre Reihenfolge rekonstruieren lassen — das habe ich
nicht nachgesehen und behaupte es nicht. Falls nicht rekonstruierbar, ist V4
heute nicht prüfbar und gehört zurückgestellt, nicht geraten.

---

### Reihenfolge, wenn ich entscheiden müsste

1. **Zuerst die Messung reparieren** (§2.1/2.2: zwei ROC-Kurven, Schwelle am
   12 000er-Korpus). Kostet keinen Codeumbau und entscheidet, ob V1–V4
   überhaupt an der richtigen Größe gemessen werden. Wer das überspringt,
   optimiert gegen eine Mischgröße.
2. **V1**, weil praktisch gratis und weil die vorhandene Fassung einen
   nachweisbar schlechten Nenner hat.
3. **V2**, weil es als einziges die Mehrheitsklasse „teilweise" adressiert.
4. **V3 oder V4**, nicht beide — das Zwei-Lauf-Budget gibt es nur einmal.

---

## 4. Was aus meiner Sicht NICHT geht

**(1) Keine Funktion der Score-Geometrie wird ROC-B lösen. Das ist eine
prinzipielle, keine technische Grenze.** Alle betrachteten Größen — bester
Wert, Abstand zum Zweiten, Abstand zum Median, Kanalübereinstimmung,
Trefferzahl — sind Funktionen desselben Arguments: der Menge der
Ähnlichkeitswerte zwischen Anfragevektor und Bestandsvektoren. Wenn zwei Fälle
in dieser Menge (nahezu) übereinstimmen und in der Wahrheit auseinanderfallen,
kann **keine** Funktion darauf sie trennen — nicht mit einer besseren Schwelle,
nicht mit einem gelernten Modell, nicht mit mehr Daten. Eure Zahlen zeigen
genau diese Deckung: 93 % gemeinsamer Träger, vertauschte Mediane, der
schlimmste Ausfall am oberen Rand. **Der Informationsgehalt ist nicht schlecht
ausgewertet, er ist nicht vorhanden.** Weiterzusuchen heißt, ein Ziel im
Bodenclutter durch Verstärkerdrehen finden zu wollen — das ist der Fehler,
gegen den mein Fach die Doppler-Verarbeitung erfunden hat. `[GEMESSEN als
Prinzip: die Datenverarbeitungsungleichung; ÜBERTRAGUNG in der Anwendung.]`

**(2) Ein Detektor kann nicht wissen, ob das Ziel im Beam war.** Eure 20
Fehlgriffe heißen „lösbar", weil ein Label das sagt. Wenn das Label falsch ist
oder wenn die richtige Antwort im Bestand in einer Form vorliegt, die die
Frage nicht beantwortet, dann ist der Detektor **nicht im Irrtum** — er meldet
korrekt, was da ist. Kein Verfahren der Welt findet ein Ziel, das nicht
beleuchtet wurde. Bei drei von zwanzig Fällen habt ihr das selbst schon
festgestellt. Siehe §5.

**(3) Deterministische Wiederholung bringt nichts.** Zwei identische Läufe
gegen einen unveränderten Bestand liefern null zusätzliche Information. Jedes
Zwei-Lauf-Verfahren muss die Quelle seiner Unabhängigkeit **explizit
benennen**, sonst ist der zweite Lauf verbrannte Zeit. Das ist Rechnen, keine
Meinung.

**(4) Eine Falschalarmrate unterhalb von etwa 1/45 ist an 45 Fällen nicht
belegbar** — und an 24 Fällen (14+10) erst recht keine Schwelle mit 0,0087
Breite. Das ist Stichprobentheorie und lässt sich durch keine Cleverness
umgehen. Der 12 000er-Korpus ist nicht eine nette Ergänzung, sondern die
Voraussetzung dafür, überhaupt von einer Rate zu sprechen.

**(5) Die Frage „wie sehr könnte ich mich irren" bleibt für den Einzelfall
unbeantwortbar.** Beantwortbar ist ausschließlich die **Rate über viele Fälle**.
Genau deshalb heißt es CFAR und nicht „Confidence per Detection". Ein System,
das dem Menschen eine Zahl je Einspielung zeigt, verspricht etwas, das die
Detektionstheorie nicht liefern kann — und würde damit außerdem eine
Konfidenzzahl auf den Bildschirm bringen, was eure eigenen Hausregeln
untersagen. Der Betriebspunkt gehört ins Protokoll, nicht in die Oberfläche.

---

## 5. Meine unbequemste Frage

**Ihr habt eure Wahrheitsdaten nur dort überprüft, wo der Detektor ihnen
widersprochen hat. Bei 3 von 20 nachgesehenen Fällen war nicht der Detektor im
Irrtum, sondern das Label. Warum glaubt ihr, dass die 15 als „richtig
geliefert" verbuchten Fälle einer Prüfung standhielten — und wie hoch wäre eure
Trefferquote, wenn ihr sie mit derselben Sorgfalt gelesen hättet wie die
Fehlgriffe?**

Warum das die unbequemste ist: 3 von 20 sind 15 % Labelfehler **in der einzigen
Teilmenge, die je von Hand gelesen wurde** — und die Prüfung war
**einseitig**. Sie konnte nur Fehler der Sorte „als falsch gebucht, war
richtig" finden. Die Gegenrichtung — „als richtig gebucht, war falsch" — hat
niemand gesucht, weil dort niemand einen Anlass sah. In meinem Fach ist das
eine Kalibrierung, die man nur an den Punkten vornimmt, an denen das Gerät
Alarm schlägt: Sie kann das Ergebnis ausschließlich nach oben korrigieren, und
deshalb ist sie keine Kalibrierung, sondern eine Selbstbestätigung. Solange die
Wahrheitsdaten eine **beidseitig** geprüfte Fehlerquote nicht kennen, hat jede
Zahl dieses Konsils einen Boden, der in derselben Größenordnung liegt wie die
Effekte, um die gestritten wird — **15 % Labelfehler gegen einen τ von 0,10.**

Zwei Fragen als Anhang, weil sie am selben Nerv hängen:

- **Wie viele der 21 000 protokollierten Einspielungen waren „teilweise"?** Ihr
  messt, was ausgeliefert wurde. Ihr messt nicht, was es beim Menschen bewirkt
  hat. Die Randbedingung 5 — „falsch liefern und falsch schweigen sind nicht
  gleich teuer" — ist nicht offen, weil die Antwort schwierig wäre, sondern
  weil die Wirkungsseite **nie erhoben** wurde. Ein thematisch naher, sachlich
  nutzloser Treffer ist möglicherweise **teurer als Schweigen**, weil er den
  Menschen nicht ratlos lässt, sondern in eine Richtung lenkt. Ein Fehlalarm,
  der wie eine Detektion aussieht, ist gefährlicher als ein leerer Schirm.
- **Die Zeile „Schwellenschicht" in eurer Vierfeldertafel (15/20/10/0) — ist
  das eine Messung oder eine Rechnung?** Sie folgt exakt aus der Kreuztabelle
  bei einer Schwelle, die auf ebendiesen 45 Fällen gesetzt wurde. Wenn ja, ist
  sie keine dritte Betriebsart, sondern die Vorhersage des Modells über seine
  eigenen Trainingsdaten — und gehört so beschriftet. Am 2026-08-16 ist genau
  das schon einmal passiert (12 gegen 12 sauber getrennt, bei 40 gegen 40
  verschwunden); es steht im Kopf von `kern/relevanzlage.py`.

---

## 6. Was ich nicht weiß

- Ob eure Einbettungen passagenweise vorliegen oder erzeugt werden können — V2
  hängt daran, ich habe es nicht geprüft.
- Ob sich aus dem 21 000er-Protokoll Sitzungen mit Reihenfolge rekonstruieren
  lassen — V4 hängt daran, ich habe es nicht geprüft.
- Wie viel Zeit euer Abruf heute tatsächlich braucht. Alle meine Kostenaussagen
  sind relativ („ein zweiter Scan", „ein Sortiervorgang mehr"), nie absolut. Ich
  habe nichts gemessen, was Millisekunden hätte.
- Ob die Klasse „teilweise" wirklich der Flächenclutter ist, für den ich sie
  halte. Das ist der Angelpunkt von V2 und bleibt bis zur Messung eine
  Hypothese.
- Ob die im Material genannte Kohärenz der Nachbarschaft (arXiv 2310.11405)
  dasselbe misst wie mein V2. Von der Beschreibung her klingt es verwandt
  (Geometrie der Trefferwolke statt Spitzenwert), aber sie betrachtet die Wolke
  **zwischen** Einträgen, V2 die Verteilung **innerhalb** eines Eintrags. Ob das
  ein Unterschied ums Ganze oder eine Variante ist, kann ich ohne Lektüre der
  Arbeit nicht sagen.
