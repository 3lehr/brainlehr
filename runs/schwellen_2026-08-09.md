# Drei Schwellen aus vorhandenen Daten abgeleitet

Stand: 2026-08-09T19:49:40+0200. Alles unten selbst gemessen (Skripte/DB im
Repo, lesend), nichts aus dem Auftrag uebernommen ohne Gegenprobe.

## Schwelle 1 — Aufnahmegrenze fuer Pruefkorpus-Faelle (Wortueberlappung)

**Zahl: 27,8 % (= exakter Maximalwert des alten Korpus, `runs/pruefkorpus.jsonl`).**

Gegenprobe der Auftragszahlen (`pruefkorpus.tokenize`, Schnittmenge / Tokenzahl
der Aufgabe, Ziel = `node_text`/`lesson_text`, Zuordnung ueber `target_id` als
**Pfad** bei Knoten bzw. **id** bei Lehren — bei Lookup ueber die Node-`id`
statt `path` waeren faelschlich 20 von 35 Zielen "fehlend" gewesen):

| Korpus | n (mit Ziel) | Mittelwert | Min | Q1 | Median | Q3 | Max |
|---|---|---|---|---|---|---|---|
| `pruefkorpus.jsonl` (alt) | 35 | 10,7 % | 0,0 % | 7,1 % | 8,7 % | 13,6 % | **27,8 %** |
| `pruefkorpus_haiku_2026-08-09.jsonl` (neu) | 55 | 34,1 % | 5,3 % | 23,8 % | 31,6 % | 42,9 % | 70,6 % |

Beide Mittelwerte bestaetigt (10,7 % bzw. 34,1 %), Nenner 35 bzw. 55 ebenfalls.

**Herleitung in drei Saetzen.** Der alte Korpus hat einen scharfen oberen
Rand bei 27,8 % — keiner seiner 35 Faelle liegt darueber, die Spannweite
0–27,8 % ist eng und ohne Ausreisser nach oben. Eine Aufnahmegrenze am
Maximum des alten Korpus laesst also per Konstruktion 35/35 (100 %) alter
Faelle durch, waehrend sie 35 von 55 neuen Faellen (63,6 %) verwirft und nur
20 von 55 (36,4 %) aufnimmt — die neuen Faelle liegen im Median (31,6 %) klar
ueber der alten Verteilung, die Grenze trennt also tatsaechlich zwei
unterschiedliche Populationen statt nur zu labeln. Die Trefferquoten
(16/35 vs. 51/55) selbst flossen in diese Ableitung nicht ein.

**NICHT geeicht gegen:** die Trefferquote (16/35 vs. 51/55) — genau das ist
die harte Auflage: eine Grenze aus der Ueberlappungsverteilung, nicht aus dem
Ergebnis, das sie später filtern soll.

**Falsch waere die Schwelle, wenn:** ein kuenftiger "guter" (niedrig
ueberlappender, schwerer) Fall regelmaessig oberhalb 27,8 % noetig waere, um
ein reales Zielwissen ueberhaupt zu formulieren — dann wuerde die Grenze
echte, schwierige Faelle verwerfen statt nur zirkulaere/leichte. Das ist mit
n=35 nicht ausgeschlossen, nur nicht beobachtet.

## Schwelle 2 — Zuwachs beim Reifegrad

**Zahl: 0 (der heute mechanisch — ohne neuen Pruefvermerk — erreichbare
Zuwachs). Schwelle: jeder Zuwachs > 0 abgeleiteter Faelle zaehlt als echt.**

Heutiger Stand (`python3 reifegrad.py bericht`, nicht die Auftragszahl
uebernommen):

| | erklaert | abgeleitet | unbestimmt | gesamt |
|---|---|---|---|---|
| Knoten | 34 | 141 | 1.856 | 2.031 |
| Lehren | 0 | 56 | 661 | 717 |
| **Summe** | **34** | **197 (7,17 %)** | **2.517 (91,6 %)** | **2.748** |

**Abweichung von der Auftragsfakten-Zeile gemeldet, nicht uebernommen:**
"43 % abgeleitet, 34 erklaert, 218 unbestimmt" trifft nur beim erklaert-Wert
der Knoten (34 = 34 ✓). Abgeleitet liegt heute bei 7,17 %, nicht 43 %;
unbestimmt bei 2.517, nicht 218. Die genannte Zahl stammt erkennbar aus
einem fruehen, viel kleineren Bestand (34+218 waere bei 43 % ein Gesamt von
rund 440 Zeilen, nicht 2.748) — vermutlich vor einem Datenimport gemessen.

**Ableitung des Moeglichen** (die drei Bedingungen aus `bewerten_knoten`/
`bewerten_lehre` einzeln gegen die 2.517 unbestimmten Faelle geprueft):

- *Beobachtbarer Bezug, Knoten:* von 1.856 unbestimmten Knoten haben 1.694
  ueberhaupt einen extrahierbaren Dateikandidaten in `source`
  (`konfidenz._kandidaten_pfade`) — aber nur **4** davon existieren
  tatsaechlich noch auf der Platte, und **keiner dieser 4** liegt in einem
  Git-Repo (Bedingung fuer `beobachtbare_datei`). Mechanisch erreichbar: 0.
- *Beobachtbarer Bezug, Lehren:* 74 von 661 unbestimmten Lehren haben einen
  `node_path`, aber **0** davon existieren auf der Platte. Mechanisch
  erreichbar: 0.
- *Mehrfaches Auftreten (Lehren):* alle 661 unbestimmten Lehren stehen bei
  `occurrences = 1` (0 bei `occurrences >= 2`, 0 bei NULL) — keine ist schon
  "fast da", ein Zuwachs braucht ein tatsaechliches erneutes Auftreten.
  Mechanisch erreichbar: 0.
- *Pruefvermerk:* strukturell fuer jede der 2.517 Zeilen offen — das ist der
  einzige Weg zu `abgeleitet`, der nicht durch fehlende Dateien blockiert
  ist, aber er verlangt eine echte Entscheidung je Fall, keine Ableitung aus
  vorhandenen Daten.

**Herleitung in drei Saetzen.** Die zwei einzigen automatisch pruefbaren
Wege (Datei wieder beobachtbar, Lehre zum zweiten Mal aufgetreten) liefern
beim heutigen Datenstand exakt null Kandidaten — nicht wenige, null. Jede
Erhoehung der 197 abgeleiteten Faelle kann also nur aus tatsaechlich
vergebenen Pruefvermerken stammen, nicht aus einem guenstigen Zufallsfund in
den Daten. Deshalb ist die richtige Schwelle keine Prozentzahl, sondern eine
Nullgrenze: >197 (bzw. >0 Zuwachs) ist per Konstruktion bereits ein Beleg
fuer echte Pruefarbeit, weil die "billige" Quelle nachweislich leer ist.

**NICHT geeicht gegen:** die (nicht reproduzierbare) Auftragszahl "43 %" —
die stammt aus einem fruehen, kleineren Bestand und ist fuer den heutigen
Bestand kein Massstab.

**Falsch waere die Schwelle, wenn:** die 4 auf der Platte vorhandenen, aber
nicht Git-verfolgten Dateien nachtraeglich in ein Repo aufgenommen wuerden —
dann waere ein Zuwachs um bis zu 4 Faelle nicht mehr zwingend Pruefarbeit,
sondern reine Buchfuehrung. Bei aktuellem Datenstand ist das nicht der Fall.

## Schwelle 3 — Wann lohnt eine Abrufverbesserung (Deckel/Zeichen-Verhaeltnis)

**Zahl: Elastizitaet ≥ 1 (prozentualer Trefferzuwachs muss mindestens so
gross sein wie der prozentuale Zeichenzuwachs). Gemessener Bestwert: 0,64 —
liegt darunter.**

Gegenprobe gegen `runs/deckelreihe_2026-08-09.json` (Spalten `guete.LESSON`,
`guete.NODE`, `menge.avg_zeichen`, Nenner 35 durchgehend):

| Deckel | LESSON | NODE | gesamt | avg Zeichen |
|---|---|---|---|---|
| 3/2 | 4/15 | 3/20 | 7/35 | 4.769 |
| 5/3 | 4/15 | 3/20 | 7/35 | 7.287 |
| 7/5 | 4/15 | 3/20 | 7/35 | 11.436 |
| 10/7 | 4/15 | 3/20 | 7/35 | 16.476 |
| 15/10 | 5/15 | 4/20 | 9/35 | 23.788 |

Auftragszahlen bestaetigt: 3/2 bis 10/7 liefern alle 7/35 bei 4.769–16.476
Zeichen, 15/10 bringt als erster Punkt 9/35 bei 23.788 Zeichen.

**Herleitung in drei Saetzen.** Vier von fuenf Deckel-Schritten (3/2→5/3→
7/5→10/7) bringen 0 zusaetzliche Treffer bei wachsenden Zeichen — deren
Elastizitaet ist 0, jeder Zeichen-Mehraufwand dort war umsonst. Der einzige
Schritt mit Gewinn (10/7→15/10) bringt +28,6 % Treffer (7→9 von 35) fuer
+44,4 % Zeichen (16.476→23.788) — eine Elastizitaet von 0,64, also wird
proportional mehr bezahlt als gewonnen. Als Verhaeltnis (nicht als absolute
Zeichenzahl) formuliert, gilt das unabhaengig von der Korpusgroesse: eine
Deckel-Erhoehung lohnt sich nur, wenn der prozentuale Trefferzuwachs den
prozentualen Zeichenzuwachs erreicht oder uebertrifft (Elastizitaet ≥ 1) —
das war bei keinem der vier gemessenen Schritte der Fall, beim besten lag
sie bei 0,64.

**NICHT geeicht gegen:** die absoluten Trefferzahlen (7 vs. 9) oder absolute
Zeichenzahlen (4.769 bis 23.788) — die Schwelle ist ein dimensionsloses
Verhaeltnis aus zwei relativen Aenderungen, kein Zeichen-Budget.

**Falsch waere die Schwelle, wenn:** eine kuenftige Messung (anderer
Korpus, anderer Deckel-Schritt) eine Elastizitaet ≥ 1 zeigt — dann waere
"mehr Zeichen bringt proportional mehr Treffer" doch belegt, und die
Deckel-Erhoehung liesse sich rechtfertigen. Bei den fuenf gemessenen Punkten
ist das nicht eingetreten; die Datenbasis ist mit einem Korpus/einer Reihe
zudem duenn.
