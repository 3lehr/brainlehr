# Plan: das zweite Signal — und warum zuerst etwas anderes gebaut wird

**Angelegt:** 2026-08-20T15:20:00+0200
**Anlass:** Betreiber, wörtlich: *„lass uns das so umsetzte wie du empfielst
update die test und den pplan dazu!"* — Freigabe der Reihenfolge, die das
Konsil vom selben Tag empfiehlt.
**Vorlauf:** `runs/konsil_zweites_signal_synthese.md` (sechs Opus-Rollen),
`runs/qpp_stand_2026-08-20.md`, Knoten `28ada6ca` und `a363ae52`.

---

## Der gemessene Ist-Stand

Alle Zahlen vom 2026-08-20, Prüfkorpus mit 45 Fällen, drei Betriebsarten.

| | richtig geliefert | falsch geliefert | richtig geschwiegen | falsch geschwiegen |
|---|---|---|---|---|
| B — spricht immer | 15 | 30 | 0 | 0 |
| **C — heutiger Auslieferungszustand** | **1** | **0** | **10** | **34** |
| Schwellenschicht (gemessen, nicht gebaut) | 15 | 20 | 10 | 0 |

Dazu die Zahlen, die die Lage erklären:

- **Die beiden Suchkanäle sind sich in 1 von 45 Fällen einig**
  (`runs/kanaleinigkeit_2026-08-20.json`, beide Betriebsarten). Die
  Ensemble-Pflicht verlangt genau diese Übereinstimmung. Sie ist damit kein
  Qualitätsfilter, sondern ein Aus-Schalter.
- Von 20 Fehlgriffen bei lösbaren Fragen sind **3 brauchbar** (der Korpus
  urteilt zu streng), **12 teilweise** (Thema getroffen, Frage nicht
  beantwortet), **5 daneben** (`runs/beurteilung_bf_cf_2026-08-20.json`).
- Der beste Kosinuswert trennt „liegt etwas im Bestand" fehlerfrei und
  „ist es richtig" gar nicht — Median der Fehlgriffe 0,6030 gegen 0,5970 bei
  den echten Treffern.
- `NOISE_FLOOR_MAD_MULT = 2.0` ist vermessen und im Auslieferungszustand
  **wirkungslos** über den ganzen zulässigen Bereich
  (`runs/rauschteppich_sweep_2026-08-20.json`).

## Die Entscheidung, und sie ist ein Verzicht

**Es wird kein zweites Bewertungssignal gebaut.** Keine der sechs Rollen
empfiehlt es als nächsten Schritt, und vier von sechs verschieben die Frage
mit derselben Begründung: *es ist nicht gemessen, ob der Abruf überhaupt
wirkt.* In keiner Zahl dieses Hauses steht, ob je ein Einspieler eine Arbeit
verbessert hat.

Solange das offen ist, sind die 34 falschen Stillen **keine belegten
Ausfälle**, und ein Signal, das sie beheben soll, behebt möglicherweise
nichts.

## Die Schritte, in bindender Reihenfolge

### S1 — Aufgriffsquote messen (Voraussetzung für alles Weitere)

**Warum zuerst, und die Reihenfolge ist nicht verhandelbar:** Wird zuerst
die Ausgabe umgestellt, gibt es keine Nulllinie mehr. Nachträglich lässt
sich nicht rekonstruieren, wie oft ein Einspieler vorher aufgegriffen wurde.
Der Schnappschuss muss stehen, bevor der erste Umbau ihn entwertet.

Gegenstand: das Zugriffsprotokoll (rund 21 000 Einträge) und
`recall_log.jsonl`. Gefragt ist, wie oft ein eingespielter Eintrag später
nachweislich verwendet wurde — zitiert in einem Auftrag, einer
Commit-Nachricht oder einem geschriebenen Eintrag.

**Vorsicht, bereits einmal passiert:** Bei einer früheren Messung dieser Art
hatten sechs Scheintreffer die Kausalität verkehrt herum (der Commit erzeugte
den Eintrag, und die „spätere Einspielung" war das eigene Echo). Diese Fälle
müssen vor der Zählung ausgeschlossen und benannt werden.

**Erfolgsmaß:** eine Zahl mit Nenner und Bezugsrahmen, getrennt nach starken
und schwachen Treffern, plus eine Stichprobe von Hand.

### S2 — Abgestufte Ausgabe statt Ja/Nein

Zwei Rollen kommen unabhängig darauf (Forensik: zwei Ausgabestufen;
Alarmmanagement: IEC 60601-1-8, niedrigpriore Alarme sind rein visuell).
Beide rechnen dasselbe vor: 12 der 20 Fehlgriffe wandern von „Ausfall" zu
„korrekt berichteter schwacher Befund" — **ohne eine Zeile Suchlogik**.

Der Grundsatz dahinter, und er ist der eigentliche Ertrag des Konsils:
**nicht die Fehlerrate senken, sondern den Preis des Fehlers.** Die
Fehlerrate ist heute nachweislich nicht senkbar; der Preis schon.

Layout (dem Betreiber am 2026-08-20 vorgelegt):

```
<knowledge-recall>
Aus dem Speicher, ungeprüft. Trifft das hier zu? …

EINSCHLÄGIG
- [/pfad] [3 Tage alt] Titel: Zusammenfassung …
- ⚠ LESSON (…): Beschreibung → Prävention …

NUR FUNDSTELLEN — ungeprüft, ob sie hierher gehören
- [/pfad] Titel
- L-xxxxxx Titel
</knowledge-recall>
```

Vorlesereihenfolge: stark vor schwach. Kein Treffer verschwindet.

Die Trennmarke existiert bereits: `STARK_AB = 0.586` in
`kern/relevanzlage.py`. Sie wird **nicht neu kalibriert** — die heute
gefundene 0,545 steht bei n=24 mit einer Lücke von 0,0087 und ist nach
Wilson mit einer Trefferquote von 78 % vereinbar. Eine auf denselben Daten
nachjustierte Schwelle misst nur noch sich selbst.

**Die Ensemble-Pflicht entfällt als Auslieferungssperre.** Sie prüft ein
Kriterium, das in 44 von 45 Fällen nicht erfüllt ist.

### S3 — Den offenen Messfehler klären

Der Radaringenieur hat im Code nachgesehen: Der Befund „Abstand zum Median
trennt nicht" wurde gegen den Median der **Kandidatenliste** gerechnet
(`statistics.median(werte)` in `messungen/kreuztabelle_bc.py`), nicht gegen
den Hintergrund aller 5217 Einträge. Nur der zweite wäre eine
Rauschschätzung. Damit ist die naheliegendste Familie von Verfahren
(CFAR-Normalisierung) **nie geprüft worden**.

Kostet einen Lauf. Fällt der Befund anders aus, ändert das S4.

### S4 — Die Handbeurteilung blind wiederholen

Zwei Rollen unabhängig (Forensik nennt Dror/Linear Sequential Unmasking,
Radar rechnet 15 % Labelfehler gegen einen strittigen τ von 0,10): Die
Beurteilung der 20 Fehlgriffe lief, während die Kosinuswerte im selben
Auftrag standen. Sie war zudem einseitig — nur die Fehlgriffe wurden
nachgesehen, die 15 Treffer nicht.

Bevor diese Beurteilung als Referenz für irgendetwas dient, wird sie blind
und beidseitig wiederholt.

## Alternativen, samt Ablehnungsgrund

| Weg | abgelehnt, weil |
|---|---|
| Zweites Signal sofort bauen (Kohärenz der Nachbarschaft) | Vier Rollen verschieben es; ohne S1 ist unbekannt, ob es ein Problem behebt. Bleibt der aussichtsreichste Kandidat, wenn S1 Bedarf zeigt. |
| Schwelle 0,545 in den Auslieferungsweg | n=24, Lücke 0,0087, nach Wilson mit 78 % vereinbar. Dieselbe Fehlerklasse ist im Kopf von `relevanzlage.py` bereits dokumentiert. |
| Ensemble-Pflicht nur lockern statt ersetzen | Behebt den Aus-Schalter nicht — das Kriterium bleibt eines, das praktisch nie erfüllt ist. |
| Kostenverhältnis festlegen | Vier Rollen zeigen, dass es nicht festgelegt werden muss (Wertkurve, Entscheidungskurve, Neyman-Pearson). *Welches* Verhältnis gilt, bleibt Betreibersache — aber als ausgelegter Parameter, nicht als Zahl im Code. |
| Betriebsart B zurückholen | Wird von der Schwellenschicht strikt dominiert: gleiche Treffer, 10 Fehllieferungen weniger. |

## Was bewusst nicht getan wird, samt Preis

- **Keine Neukalibrierung der Ähnlichkeitsschwelle `0,65`.** Sie stammt aus
  einer Erhebung über zwei Millionen Paare; wer sie anfasst, entwertet die
  Messung, die sie begründet.
- **Kein Modellaufruf pro Anfrage.** Preis: die Verfahren mit den besten
  berichteten Korrelationen (bis 0,89) bleiben unerreichbar. Der Abruf hängt
  an jedem Prompt, ein Aufschlag von Sekunden ist nicht tragbar.
- **Keine Erweiterung des Prüfkorpus in diesem Schritt.** Preis: alle Zahlen
  bleiben bei ±14 bis ±16 Prozentpunkten, 15/35 und 20/35 sind nicht
  unterscheidbar. Der zweite Korpus mit über 12 000 Fällen liegt bereit und
  ist der nächste Kandidat — aber er misst eine leichtere Aufgabe
  (Wortüberlappung 40,0 % gegen 8,7 %) und ersetzt den harten Korpus nicht.

## Woran sich Erfolg messen lässt

1. **S1:** Es existiert erstmals eine Zahl zur Frage, ob der Abruf wirkt —
   mit Nenner, Bezugsrahmen und Stichprobe. Auch ein Nullbefund ist ein
   Ergebnis und wird als solcher festgehalten.
2. **S2:** Falsches Schweigen fällt von 34 auf 0, ohne dass die falschen
   Lieferungen über 20 steigen. Nachgewiesen am selben Prüfkorpus, im
   Auslieferungszustand gemessen — nicht in einer Betriebsart, die niemand
   ausliefert.
3. **S2, zweiter Beleg:** Die mittlere Zeichenmenge je eingespieltem Block
   steigt nicht, obwohl mehr Treffer erscheinen. Sonst wurde der Preis des
   Fehlers nicht gesenkt, sondern nur verschoben.
4. **S3:** Die CFAR-Frage ist beantwortet — trennt der Abstand zum
   Hintergrundmedian, oder nicht? Beides ist ein Ergebnis.
5. **S4:** Die blinde Wiederholung bestätigt die vier Klassen, oder sie tut
   es nicht. Weicht sie ab, ist jede Folgerung dieses Tages neu zu prüfen.

## Nachtrag nach der Umsetzung

### S1 bis S4 abgeschlossen, S5 kam dazu — Stand 2026-08-20T18:00:00+0200

| | Ergebnis |
|---|---|
| **S1** Aufgriffsquote | **247 von 1275 = 19,4 %**. Lehren 30,5 %, Knoten 8,2 %. Drei Läufe nötig — erzeugte Dateien hatten die Quote von 61,9 auf 19,4 aufgebläht. |
| **S2** abgestufte Ausgabe | gebaut, **Schalter aus**. 5876 → 2876 Zeichen bei gleichen Treffern. Protokoll-Lücke geschlossen: `recall_log` führt jetzt den Kosinuswert je Kennung. |
| **S3** CFAR | **Nullbefund**. Robustes z-Maß über alle 5217 Knoten trennt nicht: [1,99–3,22] gegen [1,78–3,05]. Damit sind drei Verfahren geprüft und drei ausgefallen. |
| **S4** blinde Beurteilung | **Das Messinstrument wackelt.** 7 von 15 „Treffern" sind bei blinder Prüfung keine, 4 von 20 „Fehlgriffen" sind welche, Übereinstimmung 24/35. Gegenüber der ersten Beurteilung weichen 10 von 20 ab. |

**S4 ist der schwerste Befund und er ist unverarbeitet:** Jede Zahl dieses
Tages, die auf der Trefferzählung aufbaut, steht unter Vorbehalt. Der
Engpass ist möglicherweise nicht der Abruf, sondern das Instrument.

### S5 — der Fälligkeitskanal (neu, aus einer Betreiberfrage)

Betreiber, wörtlich: *„wenn die frist abgelaufen ist und vom chat/user noch
nie abgefragt wurde sollte sie mit prio zum prüfen eingespielt werden? ...
wichtige dinge und oder dinge welche direkte auswirkungen haben nichtbeachten
teurer wird sollten schon früher eingespielt werden?"*

Trifft dieselbe Stelle wie die Alarmmedizin im Konsil (IEC 60601-1-8:
Priorität aus Schadensfolge, nie aus Messsicherheit). **Gemessen gestützt:**
Von allen geprüften Größen trennen genau zwei, und beide sind Schadensmaße —
`severity` (critical 42,4 % > high 37,5 % > medium 22,8 % > low 12,0 %) und
`occurrences` (1× 26,2 % < 2–3× 59,4 %).

Gebaut als `melder/faelligkeit.py`, an `SessionStart`, 0,03 s, Deckel 3
Zeilen, Rotation ohne Zustandsdatei. Fünf Klassen, 204 Kandidaten.

**Zwei Konstruktionsfehler, beide erst im echten Lauf sichtbar:** Die erste
Rotation entwertete die Schadensfolge (an ~83 % der Tage nur die schwächste
Klasse). Nach der Behebung fiel die schwächste Klasse ganz weg — vier
Klassen, drei Plätze. Jetzt: Platz eins immer die schwerste Klasse, die
übrigen rotieren.

**Dritter Fehler, vom Betreiber gefunden:** `access_count` ist global — wer
liest, nimmt es allen aus der Liste. 36 Normen waren dadurch unsichtbar.
Neue schwächste Klasse `norm_leser_unbekannt`, Achse ist der **Klient**, nicht
die Sitzung. Die Frage nach dem „anderen Kontextfenster" bleibt ausdrücklich
unbeantwortet — ein neues Fenster kennt per Bauart nichts.

**Was daraus als Lehre bleibt** (`L-6af5ac`): dreimal an einem Tag eine
zweiseitige Größe einer Seite zugeschrieben. Die Datenstruktur verschluckt
die zweite Seite — was einspaltig gespeichert ist, wird einspaltig gedacht.

### Offen

1. **S4 verarbeiten** — der Prüfkorpus urteilt in beide Richtungen falsch.
   Bevor eine weitere Zahl auf ihm aufbaut, gehört er selbst geprüft.
2. **S2 scharfschalten**, sobald das Protokoll ein paar Tage Kosinuswerte
   gesammelt hat. Ein Schalter, keine Arbeit.
3. **Aufgriff nach Stärke auswerten** — geht erst mit den neuen Protokolldaten.

### S2 gebaut, 2026-08-20T16:00:00+0200 — zwei Abweichungen

**Gemessen am echten Abrufweg**, gleiche Anfrage, gleiche Treffer:
Schalter aus 5876 Zeichen (Ausgabe unverändert), Schalter an 2876 Zeichen
mit 8 Fundstellen-Zeilen. Kein Treffer verschwindet.

**Abweichung 1 — der Umbau war unnötig, und beinahe wirkungslos.** Der Plan
ging davon aus, der Ähnlichkeitswert je Treffer müsse erst durchgereicht
werden. Er liegt seit jeher als Feld `bedeutungs_kosinus` an jedem Treffer,
bei Knoten wie bei Lehren. Der begonnene Durchreich-Umbau ist vollständig
zurückgebaut.

Schlimmer als die vergebliche Arbeit war, was sie beinahe verdeckt hätte:
Neun Tests waren grün, weil sie ihr Eingabeformat selbst bauten — nach Pfad
geschlüsselt. Der echte Weg schlüsselt nach Kennung. **Schnittmenge 0.** Die
Stufung hätte im Betrieb nichts getan, bei grüner Suite. Bemerkt durch eine
Messung am echten Weg, nicht durch einen Test. Festgehalten als `L-497059`;
der zehnte Testfall geht jetzt gegen den echten Abrufweg.

**Abweichung 2 — die Schwelle bleibt ungemessen, und das steht im Code.**
Der Plan nannte `STARK_AB = 0.586` als vorhandene Trennmarke. Gemessen lagen
bei einer echten Anfrage **alle 17 Treffer darunter** — die Stufung hätte
alles herabgestuft. `STARK_AB` beschreibt die Lage des ganzen Blocks, nicht
den einzelnen Treffer. Deshalb steht jetzt eine eigene Konstante `STUFE_AB`
mit einem Kommentar, der sie ausdrücklich als ungemessen benennt. Sie ist
zusammen mit dem Schalter aus; die Kalibrierung ist S3/S4.

**Unverändert gültig:** Der Schalter `BRAINLEHR_ABRUF_STUFEN` bleibt auf
`aus`, bis S1 die Nulllinie erhoben hat. Das ist die bindende Reihenfolge,
nicht Vorsicht.
