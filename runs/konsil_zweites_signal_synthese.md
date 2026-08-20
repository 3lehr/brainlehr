# Konsil „das zweite Signal" — Zusammenschau

Stand 2026-08-20T15:00:00+0200. Sechs Opus-Rollen, gleiches Material
(`runs/konsil_zweites_signal_material.md`), keine kannte die anderen oder
deren Antworten. Einzelgutachten: `konsil_radar.md`, `konsil_forensik.md`,
`konsil_meteorologie.md`, `konsil_psychometrie.md`,
`konsil_alarmmanagement.md`, `konsil_skeptiker.md`.

Diese Zusammenschau ist nach **Konvergenz** geordnet, nicht nach Rolle. Was
mehrere Fächer unabhängig und mit **verschiedener Begründung** sagen, steht
oben. Einzelstimmen stehen unten und sind als solche gekennzeichnet.

---

## 1. „τ = 0,10" ist keine Absage — vier Rollen, vier verschiedene Gründe

Das stärkste Konvergenzergebnis des Konsils, und es widerlegt die
Zusammenfassung, mit der der Auftraggeber ins Konsil ging.

| Rolle | Begründung |
|---|---|
| Forensik | τ ist ein Populationsmaß über eine Referenzpopulation, in der die entscheidende Varianz **nicht existiert** — in gängigen IR-Korpora hat jede Anfrage per Konstruktion eine Antwort. Anwesenheit/Abwesenheit ist dort eine Konstante. |
| Meteorologie | τ misst nur **einen von drei** Termen der Brier-Zerlegung (Murphy 1973) und ist keine proper scoring rule. Es ist blind gegen jede monotone Verzerrung. |
| Psychometrie | **Varianzeinschränkung** (Thorndike 1949): Der Prädiktor wird auf der Menge geprüft, die er selbst selektiert hat. Der Abfall ist die vorhersagbare Folge der Selektion, nicht ein Mangel des Prädiktors. |
| Alarmmanagement | τ und r sind **Trennschärfemaße**. Abgestufte Alarmsysteme leben von Kalibrierung plus gestufter Reaktion. NEWS2 hat mäßige Diskrimination und steht trotzdem in Leitlinien. |

**Folgerung:** τ = 0,10 darf weder als Entwarnung noch als Absage zitiert
werden. Es sagt nichts über die Nutzbarkeit in einem System, das die
Ja/Nein-Entscheidung ohnehin treffen muss.

## 2. Zwei Konstrukte, nicht ein schwaches Signal — drei Rollen, ein Bild

| Rolle | Formulierung |
|---|---|
| Radar | **Detektion** („ist ein Ziel im Beam") und **Klassifikation** („was ist es") sind zwei Stufen mit getrennten Merkmalen und getrennten Gütemaßen. Der Kosinuswert löst die erste fehlerfrei und die zweite gar nicht — Lehrbuchzustand, kein Versagen. |
| Forensik | **Quellenebene** („Material dieser Art existiert") gegen **Handlungsebene** („es beantwortet die Frage"), Evett/Cook-Hierarchie, ENFSI 2015. Korrekte Ebenenzuordnung, keine Enttäuschung. |
| Psychometrie | **Deckung** gegen **Passung** — zwei Konstrukte, zwei Signale nötig. Der Kosinuswert ist ein *starker* Prädiktor für das erste. |

**Folgerung:** Die Gefahr besteht darin, einen guten Befund als schlechten zu
verbuchen und wegzuwerfen. Gesucht ist nicht ein *besseres* Signal, sondern
ein **zweites, orthogonales**.

Radar nennt die Bedingung, unter der das überhaupt gehen kann: Gegen Clutter
— Störechos, die **stärker** sind als das Ziel — hilft keine Schwelle,
sondern nur eine andere Beobachtungsachse. Bei Radar ist das Doppler oder
Polarimetrie. Die 20 Fehlgriffe sind Clutter, kein Rauschen: ihr Median
(0,6030) liegt über dem der echten Treffer (0,5970).

## 3. Die 12 „teilweise" sind die gefährlichste Gruppe — vier Rollen

Nicht die 5 echten Ausfälle. Plausibel, thematisch passend, sachlich
nutzlos — und deshalb **nicht verworfen**, sondern gelesen und halb
geglaubt.

Alarmmanagement fügt den Punkt hinzu, der die Analogie an ihrer Grenze
zeigt: Beim Menschen greift Abstumpfung als Schutz. Beim Modell als
Empfänger fällt dieser Schutz weg — es stumpft nicht ab, es **baut halb
passende Treffer plausibel ein**. Die Gruppe ist hier also schlimmer als am
Krankenbett.

## 4. Die offene Kostenfrage muss gar nicht beantwortet werden — vier Rollen

Das Material stellte sie als offene Frage („falsch liefern und falsch
schweigen sind nicht gleich teuer, aber wie ungleich, ist nicht
festgelegt"). Vier Rollen umgehen sie auf drei verschiedenen Wegen:

- **Meteorologie:** Wertkurve über *alle* Kostenverhältnisse (Murphy 1977,
  Richardson 2000) zeigt, ob das Verhältnis überhaupt zählt.
- **Alarmmanagement:** Entscheidungskurvenanalyse (Vickers & Elkin) — die
  Schwellenwahrscheinlichkeit legt es fest, ohne dass über Kosten geredet
  wird. Zusatz: es gibt **nicht ein** Verhältnis, sondern eines je
  Aufgabenklasse.
- **Radar:** Das Fach hat die Frage 1933/1954 für unbeantwortbar erklärt und
  umgangen — **Neyman-Pearson** fixiert die Falschalarmrate statt eines
  Kostenverhältnisses.
- **Psychometrie/Skeptiker:** rechnerisch. Betriebsart B wird von der
  Schwellenschicht **strikt dominiert** und fällt ohne jedes Kostenmodell
  weg. Die Schicht schlägt den heutigen Zustand C, sobald das Verhältnis
  unter etwa 0,7 liegt.

**Folgerung:** Die Frage, die im Material als offen markiert war, ist die
falsche Frage. Sie wird nicht beantwortet, sondern durch eine Kurve ersetzt.

Forensik widerspricht an einem Punkt und behält recht: *welches* Verhältnis
gilt, ist nach *R v T* eine Entscheidung des Betreibers, kein Gutachten —
aber sie gehört als einstellbarer Parameter mit ausgelegter Fehlerkurve
vorgelegt, nicht im Code versteckt.

## 5. Der Nutzen wurde nie gemessen — vier Rollen, und das ist die eigentliche Lücke

| Rolle | Formulierung |
|---|---|
| Meteorologie | Murphy 1993 unterscheidet drei Arten von Güte. Verifiziert wird hier nur die zweite (Übereinstimmung), nie die dritte (Wert für den Nutzer). |
| Alarmmanagement | Für wie viele der 5200 Einträge existiert überhaupt eine Handlung, die sich ändert, wenn sie ankommen? **In keiner Zahl steht, ob je ein Einspieler eine Arbeit verbessert hat.** |
| Forensik | Gemessen wurde, ob das Gelieferte richtig ist — nie, ob das Liefern gewirkt hat. |
| Psychometrie | Nennt eine Entscheidung, die aufgrund dieser 45 Fälle anders ausfiel — und ob der Unterschied größer war als ±16 Punkte. |

**Folgerung, und sie ist unbequem:** Die 34 falschen Stillen sind nicht
ohne Weiteres 34 Ausfälle. Zur Debatte steht damit nicht die Schwelle,
sondern die **Indikation**.

## 6. 45 Fälle sind eine Rauchprobe, kein Archiv — alle sechs

- Meteorologie: ±14 Prozentpunkte; Zuverlässigkeitsdiagramm braucht 500–1000,
  Brier-Unterschiede von Hundertsteln einige Tausend. Blockweiser Bootstrap
  nötig wegen Themenabhängigkeit.
- Psychometrie: effektiv **~24 statt 45 Items** — 20 nie gelöste Items haben
  p=0 und tragen null Information; sie werden in jedem IRT-Verfahren vor der
  Kalibrierung entfernt. ±16 Prozentpunkte. **15/35 und 20/35 sind nicht
  unterscheidbar.** Der perfekte Wert 10/10 ist nach der Regel der Drei mit
  einer wahren Fehlerrate von 30 % vereinbar.
- Forensik: Wilson-Intervall — die „fehlerfreie Trennung" bei 14 gegen 10
  Fällen ist mit einer unteren Schranke von rund **78 %** vereinbar. Starker
  Hinweis, kein bewiesener Nulldurchsatz.
- Radar und Skeptiker: die Lücke 0,0087 ist ein Zehntel der gruppeninternen
  Spannweite; ein einziger Gegenfall zerstört sie. Und dieselbe Fehlerklasse
  ist im Kopf von `kern/relevanzlage.py` bereits dokumentiert.

## 7. Nachgemessen: der Befund, den zwei Rollen aus einer Nebenzeile holten

Meteorologie und Skeptiker hoben unabhängig hervor, dass die Zahl
übereinstimmender Kanäle „durchweg 0" war — belegt war das nur für 24 der
45 Fälle.

**Nachgemessen über alle 45, in beiden Betriebsarten**
(`runs/kanaleinigkeit_2026-08-20.json`):

> Fälle mit mindestens einer Überschneidung der Top-5 beider Kanäle:
> **1 von 45 (2,2 %)** — in Zustand B wie in Zustand C.

Und Zustand C liefert in genau **1 von 35** Fällen aus. Die Ensemble-Pflicht
verlangt Übereinstimmung, die Kanäle sind sich praktisch nie einig — sie ist
damit **kein Qualitätsfilter, sondern ein Aus-Schalter**. Beide Rollen hatten
recht, aus einer Zeile, die im Material unter „nicht trennend" abgelegt war.

Meteorologie benennt zusätzlich den methodischen Fehler: eine **konstante**
Größe kann nicht trennen, sie kann nur pauschal abschneiden.

---

## Einzelstimmen, die kein zweiter bestätigt hat — trotzdem festgehalten

**Radar, zwei prüfbare Code-Befunde** (im Repo nachgesehen, nicht behauptet):

1. `channel_discrimination()` in `kern/embeddings.py` ist beinahe ein
   CFAR-Verfahren, hat aber den falschen Nenner: `(top − median)/(top − min)`
   benutzt mit `min` die varianzreichste Ordnungsstatistik und kürzt `top`
   gegen sich selbst. Ein robustes z-Maß über MAD wäre derselbe Einzeiler.
2. **Der Median-Befund dieses Tages könnte die falsche Größe gemessen
   haben.** Im Material heißt es, „Abstand zum Median der Trefferliste"
   trenne nicht — der Top-k-Median und der Median über alle 5200 Einträge
   sind aber verschiedene Größen, und nur der zweite ist eine
   Hintergrundschätzung. Nachgesehen: `messungen/kreuztabelle_bc.py` rechnet
   `statistics.median(werte)` über die **Kandidatenliste**. Damit ist die
   CFAR-Frage nie geprüft worden. **Offener Punkt.**

**Radar, zur Kostenfrage:** Die beantwortbare Form lautet „wie viele nutzlose
Einspielungen pro 100 Prompts, bevor der Block grundsätzlich überlesen wird"
— rechenbar gegen das 21 000er-Protokoll. Die Vigilanzforschung (Mackworth
1948) ist an Radarschirmen entstanden und sagt: der Schaden wirkt **kumulativ
über die Sitzung**, nicht pro Fall.

**Alarmmanagement, die stärkste einzelne Bauformidee:** Die Priorität eines
Alarms kommt in IEC 60601-1-8 aus **Schadensfolge × Zeit**, nie aus der
Messsicherheit. Ein Monitor piepst nicht lauter, weil der Sensor sicherer
ist. Dieses System stuft ausschließlich nach Abrufsicherheit — zwei Achsen
statt einer. Und der Rat, der daraus folgt: **nicht die Fehlerrate senken
(geht nachweislich nicht), sondern den Preis des Fehlers.** Alles über der
Schwelle wird ausgeliefert, aber das schmale Band nur als einzeilige
Fundstelle. Dann kosten 20 Fehlgriffe 20 Zeilen statt 20 Absätze, und die 34
falschen Stillen entfallen.

Forensik kommt über einen anderen Weg zur selben Bauform: zwei getrennte
Ausgabestufen verschieben 12 der 20 Fehlgriffe von „Ausfall" zu „korrekt
berichteter schwacher Befund" — **ohne eine Zeile Suchlogik**.

**Alarmmanagement, Empfängerbefund:** Die Umgehung existiert bereits
schriftlich. In den Hausregeln steht, Recall-Treffer seien „Hintergrund-
Kontext, kein Auftrag" und vorher zu verifizieren. Das ist der Aufkleber am
Monitor — und er ist belastbarer als der 45-Fall-Korpus.

**Psychometrie, zwei Sofortgewinne ohne neuen Lauf:** Abruf- und
Ablehnungsgüte nie summieren (zwei Dimensionen). Und die bereits vorhandene
vierstufige Handnachsicht **polytom** auswerten statt dichotom.

**Skeptiker, die Decke:** Ein Signal wählt nur aus, was der Abruf ohnehin
fand. Obergrenze jeder rein schaltenden Schicht = Trefferzahl von B, also 15
von 35 (18 mit Handkorrektur). **57 % der lösbaren Fragen bleiben in jedem
Ausbau unerreichbar** — dagegen ist ein Konfidenzsignal per Konstruktion
machtlos. Er nennt selbst die Grenze seines Arguments: für ein Signal, das
einen zweiten Lauf auslöst, gilt die Decke nicht.

---

## Zwei methodische Warnungen an die eigene Arbeit

**Die Handbeurteilung war nicht blind.** Forensik (Dror, Linear Sequential
Unmasking) und Radar heben unabhängig hervor: Die 20 Fehlgriffe wurden
beurteilt, während die Kosinuswerte im selben Auftrag standen. Nachgesehen:
`messungen/beurteilung_bf_cf.py` reicht `bester_kosinus` je Fall mit aus. Das
Urteil konnte also vom Wert beeinflusst sein. **Der Referenzstandard für
alles Weitere ist damit angreifbar.**

**Die Prüfung war einseitig.** Nur die Fehlgriffe wurden nachgesehen, die 15
Treffer nicht (Skeptiker, Radar). Korrekturen konnten daher nur in eine
Richtung wirken. Radar rechnet vor: 15 % Labelfehler gegen einen strittigen
τ von 0,10.

## Was daraus als nächstes folgt

Keine Rolle empfiehlt, sofort ein zweites Signal zu bauen. Vier von sechs
verschieben die Frage:

1. **Erst messen, ob es wirkt** — Aufgriffsquote aus dem 21 000er-Protokoll
   (Alarmmanagement, Meteorologie, Forensik, Psychometrie). Ohne diese Zahl
   ist unbekannt, ob die 34 falschen Stillen überhaupt Schaden sind.
2. **Die billigste Bauform zuerst** — abgestufte Ausgabe statt Ja/Nein.
   Verschiebt 12 der 20 Fehlgriffe, ohne die Suche anzufassen (Forensik,
   Alarmmanagement, unabhängig).
3. **Den offenen Messfehler klären** — CFAR gegen den Hintergrundmedian statt
   gegen den Kandidatenmedian (Radar). Kostet einen Lauf.
4. **Die Handbeurteilung blind wiederholen**, bevor sie als Referenz für
   irgendetwas dient.

Die Ensemble-Pflicht in ihrer heutigen Form ist nach Punkt 7 kein
Streitpunkt mehr: sie prüft ein Kriterium, das in 44 von 45 Fällen nicht
erfüllt ist.
