# Plan — die Verschmelzung gewichtet Rang statt Güte

**Stand** 2026-08-15T20:30:00+0200
**Betrifft** `kern/embeddings.py::rrf_fuse` und den Suchpfad
**Anlass** Betreiber, 2026-08-15: auf die Feststellung, ein großer Heuhaufen wirke
auf jede Anfrage — *„dann haben wir aber ein Fehler in unserem System!"*
**Verwandt** Knoten `d84b6b64`, ADR-022, `runs/vorher_rrf_2026-08-15.json`

## Warum das ein Fehler ist und keine Randbedingung

Ein Wissensspeicher, bei dem das Hinzufügen **fachfremder** Daten die Antworten auf
**unverwandte** Fragen verschlechtert, ist kaputt. Die erste Reaktion — weniger
laden — war der falsche Weg: Sie hätte einen Umweg um einen Defekt gebaut, der
danach jahrelang stehen bleibt.

## Der gemessene Befund

Deutsche Anfrage im englischen Bestand: **0 von 5** Treffern. Dieselbe auf
Englisch: **5 von 5**.

Nicht die Ursache, jeweils einzeln geprüft:

- **Das Einbettungsmodell trägt.** Es bildet die deutsche Anfrage auf den richtigen
  Knoten ab — Platz 1 von 2151, Ähnlichkeit 0,637 gegen 0,663 englisch.
- **Die Textmenge war es nicht.** Alle 1638 Knoten tragen Volltext, im Mittel 896
  Zeichen.

Die Ursache ist die Formel:

```
Rang 1 allein im Bedeutungskanal:   1/(60+0+1)                 = 0,0164
Rauschen auf Rang 7 und Rang 113:   1/(60+6+1) + 1/(60+112+1)  = 0,0207
```

Das Rauschen gewinnt. Der Stichwortkanal lieferte auf Deutsch **acht** Treffer,
reiner Trigramm-Zufall — „ver" aus *Startverzögerung* traf auf *Verdichtung* —
aber seine Spitzenränge tragen volles Ranggewicht. **Ein Kanal mit acht wertlosen
Treffern verleiht seinem besten dasselbe Gewicht wie einer mit 773 guten.**

## Verworfen, mit Grund

**Nach Trefferzahl gewichten.** Verlockend (8 gegen 773), aber falsch: Eine präzise
Anfrage liefert legitim wenige Treffer. **Preis:** bestraft Genauigkeit.

**Auf die Kanalgröße normieren.** Kehrt den Fehler um — Rang 1 von 8 wäre stärker
als Rang 1 von 773.

**Den Stichwortkanal streichen.** Am 2026-08-09 gemessen: Er rettete über sechs
Verschmelzungsgewichte **keinen einzigen** Fall, den die Vektorsuche verfehlte, und
kostete im Betrieb zwei (13 statt 15). Trotzdem verworfen: Für **exakte Kennungen**
(`L-xxxxxx`, `ADR-nnn`, Paragraphen, Aktenzeichen) ist er der einzige zuverlässige
Weg. Eine Bedeutungssuche findet „ähnlich wie ADR-020" — gebraucht wird aber genau
ADR-020.

## Die Entscheidung — zwei Schritte, getrennt messbar

**Schritt 1: Der Stichwortkanal trägt nur GANZE Treffer bei.** Ein Treffer, der nur
über ein Wortfragment zustande kommt, geht nicht in die Verschmelzung. Für seine
Stärke — exakte Kennungen — sind Trigramme nicht nötig; sie sind ausschließlich die
Quelle des gemessenen Rauschens.

**Schritt 2: Ein Kanal ohne eigene Trennschärfe trägt kein volles Ranggewicht.**
Liegt sein bester Treffer auf demselben Niveau wie sein mittlerer, hat er nichts
unterschieden. Das ist innerhalb eines Kanals messbar, ohne unvergleichbare
Punktwerte zwischen Kanälen zu vergleichen — genau das, wofür RRF ursprünglich
gebaut wurde.

**Warum zwei Schritte und nicht einer:** Schritt 1 ist billig und behandelt den
belegten Einzelfall. Schritt 2 ist der allgemeine Fix und wirkt auf **jede**
Anfrage, auch einsprachige. Zusammen gebaut wäre nicht mehr zuzuordnen, welcher
wirkt.

## Was diesen Plan von allen früheren unterscheidet

**Seit dem 2026-08-15T20:08 ist es messbar.** GermanQuAD liegt im Bestand: **13.722
Fälle mit vorher bekanntem Label**, davon **12.347** mit Antwort im Bestand und
**1.375**, bei denen die Antwort nachweislich **nicht** drin ist (301 Passagen
absichtlich zurückgehalten).

Damit zerfällt die eine Zahl in **drei**:

1. **Trefferquote** — findet die Suche, was da ist?
2. **Falschmeldequote** — meldet sie etwas, das nicht da ist? *Diese Zahl hat dieses
   Haus noch nie erhoben.*
3. **Einsprachiger Fall getrennt** — wird der Normalfall schlechter?

Jede frühere Änderung an der Formel hätte nur eine Zahl gegen eine andere getauscht.

## Bindende Reihenfolge

1. Vorher messen — gegen den **jetzigen** Bestand (4930 Knoten). Die Zahlen vom
   Nachmittag (18 von 205, 8,78 %) gelten für 2217 und sind **nicht** vergleichbar.
2. Schritt 1, messen.
3. Schritt 2, messen.
4. Erst danach entscheiden, ob beide bleiben.

## Was bewusst NICHT getan wird

- **Kein Umbau auf einen anderen Verschmelzungsalgorithmus.** RRF ist nicht das
  Problem; die fehlende Güteangabe ist es. **Preis:** Wenn sich Schritt 2 als
  untragfähig erweist, steht dieser Umbau später doch an.
- **Keine Neuberechnung der Einbettungen.** Das Modell trägt nachweislich.
- **Keine Anpassung von `k=60`.** Am 2026-08-13 gemessen: Die verfehlten Fälle
  liegen im Median auf Rang **104**, mit Ausreißern bis 570. Ein Deckel von 50 holt
  zehn von 22 herein — hier fehlen Größenordnungen, keine Plätze. Eine
  Parameteränderung wäre Kosmetik.

## Woran sich Erfolg messen lässt

Nicht „die Trefferquote steigt". Sondern:

1. Der belegte deutsche Fall trifft — und ein sinnloser weiterhin nicht.
2. Die **Falschmeldequote** sinkt oder bleibt gleich; steigt sie, ist der Fix
   schlechter als das Problem.
3. Einsprachige Anfragen werden **nicht** schlechter. Werden sie es und es lässt
   sich nicht vermeiden: melden, nicht wegkalibrieren.
4. Jede Zahl trägt die Knotenzahl mit, gegen die sie erhoben wurde.

---

## Fortschreibung 2026-08-15T21:45:00+0200 — beide Schritte widerlegt

Gemessen gegen **4930 Knoten**, 40 Fälle mit Antwort im Bestand, 40 ohne, 35
einsprachig (`runs/kanalguete_vorher_schritt1_schritt2_2026-08-15.json`,
Commit `8508dc46`):

| Stufe | Trefferquote | Falschmeldequote | Einsprachig | Leitfall |
|---|---|---|---|---|
| vorher | 39/40 | 40/40 | 4/35 | trifft |
| Schritt 1 | 39/40 | 40/40 | 4/35 | trifft |
| Schritt 2 | 37/40 | 40/40 | 2/35 | **trifft nicht** |

**Schritt 1** — kein messbarer Effekt, weder Nutzen noch Schaden.
**Schritt 2** — verschlechtert alle drei beweglichen Zahlen und verfehlt genau den
belegten Leitfall, den er beheben sollte. **Nicht aktiviert.** Der Code bleibt
rückwärtskompatibel und in keinem Aufrufer verdrahtet; die Vorgabe `None` ist
byte-identisch zur alten Formel.

### Der eigentliche Ertrag war ein Nebenbefund

**Die Falschmeldequote steht bei 40/40 — in jeder Stufe.** Das ist keine
Eigenschaft der Formel: Das System hat **keine Relevanzschwelle**. Jede Anfrage mit
mindestens einem Kandidaten gilt als beantwortet; der Zustand *„dazu habe ich
nichts"* ist nicht ausdrückbar. Keine Umordnung behebt das — dafür braucht es einen
Abschneidepunkt, und der Plan vom 2026-08-12 hat einen solchen bereits einmal
verworfen, weil er mit der Spezifität korreliert.

**Das ist die Frage des Betreibers von heute Abend in ihrer schärfsten Form:**
*„vielleicht gibt es aber auch noch gar nichts zu finden."* Das System kann diese
Antwort nicht geben.

### Zwei Fehler im Auftrag, beide meine

**Die Tabu-Liste schloss die Stelle ein, an der der Fehler vermutlich sitzt.**
`knowledge_mcp_server.py` und der Abrufhaken waren gesperrt — in einem davon liegt
`_fuse_with_keyword_floor()`, ein sättigender Sockel, der dafür sorgt, dass der
**echte** Suchweg eine Änderung an `rrf_fuse` strukturell gar nicht sieht. Der
bauende Agent hat das gemeldet statt es zu umgehen und einen eigenen Messpfad
gebaut; ohne diese Meldung wäre die Messung als Aussage über den Produktivweg
gelesen worden, den sie nie erreicht hat.

**Und der Entwurf kam aus dem Einzelfall statt aus der Verteilung.** Die Rechnung
für den belegten deutschen Fall war korrekt — im Mittel schadet sie. Dieselbe
Klasse wie `L-518fcc`: mit der Zahl angefangen statt mit der Verteilung.

### Was daraus für den nächsten Anlauf folgt

1. **Der Sockel gehört gemessen, nicht die Formel.** Solange `_fuse_with_keyword_floor()`
   sättigt, ist jede Arbeit an `rrf_fuse` folgenlos für den Produktivweg.
2. **Die Relevanzschwelle ist die größere Frage.** Ein System, das nie „nichts"
   sagt, kann seine eigene Trefferquote nicht deuten.
3. **Vor dem nächsten Entwurf die Verteilung**, nicht die Rechnung eines Falls.

---

## Fortschreibung 2026-08-16T04:48:08+0200 — der Sockel ist gemessen, und er sättigt fast immer

Schritt 1 der Reihenfolge oben ist erledigt. `kern/kanalguete_messung.py` trägt jetzt
eine vierte Stufe `echt`, die den Produktivweg **einschließlich** Sockel rechnet
(`knowledge_mcp_server._fuse_with_keyword_floor()` wird importiert, nicht nachgebaut).
Lauf: `runs/kanalguete_sockel_2026-08-16.json`, gegen **4933 Knoten**, 117 Anfragen.

### Die Verteilung

| | |
|---|---|
| Sockel gesättigt | **116 von 117** (99,1 %) |
| Endergebnis identisch mit reiner Stichwortreihenfolge | **116 von 117** |
| Endplätze, die der Bedeutungskanal beisteuert | **4 von 585** (0,7 %) |
| Stichwortkanal, Median | **4740 Kandidaten** — bei `max_results=5` |

**Der Bedeutungskanal ist im Produktivweg praktisch abgeschaltet.** Nicht schwach
gewichtet: abgeschaltet. Der Median sagt auch, warum — die Trigramm-FTS mit
OR-Verknüpfung trifft *4740 von 4933 Knoten*. Der „Stichwortkanal" ist an dieser
Stelle kein Filter mehr, sondern beinahe der Gesamtbestand, und der Sockel gibt ihm
trotzdem unbedingt alle fünf Plätze.

**Damit hat auch die Falschmeldequote 40/40 eine Ursache statt nur einen Namen:** Bei
im Median 4740 Kandidaten je Anfrage *kann* „dazu habe ich nichts" nicht entstehen.
Die Relevanzschwelle (Punkt 2) ist kein zweites, unabhängiges Thema — sie hängt an
derselben Stelle.

### Was das für jede bisher berichtete Zahl bedeutet

Der bisherige Messpfad ließ den Sockel weg. Nebeneinander, **derselbe Lauf**:

| | echt (mit Sockel) | vorher (ohne Sockel) |
|---|---|---|
| Trefferquote | 34/40 | 39/40 |
| einsprachig | **0/35** | 4/35 |
| Leitfall deutsch | **trifft nicht** | trifft |
| Falschmeldequote | 40/40 | 40/40 |

Der echte Weg ist in jeder beweglichen Zahl schlechter, und beim einsprachigen
Normalfall **auf null**. Die Tabelle der Fortschreibung von gestern gilt für einen
Pfad, den das System nie ausführt — das ist keine Nachlässigkeit des Agenten,
sondern die Folge der Tabu-Liste, und genau der Fall, für den die Hausregel
„der Prüfstand ist nie die Wirklichkeit" steht.

### Was daraus folgt — und was ausdrücklich noch NICHT getan ist

1. **Der Sockel ist der Fehler, nicht die Formel.** `kern/embeddings.py::fuse_semantic_led()`
   liegt seit dem 2026-08-12 fertig und unverdrahtet genau dafür da. **Verdrahtet ist
   sie nicht** — das ist der nächste Schritt und braucht eine eigene Messung, weil
   `fusion_echt` heute belegt, dass am Produktivweg gemessen werden muss.
2. **Der Stichwortkanal selbst gehört gemessen.** 4740 von 4933 ist kein Rangproblem.
   Ob ein Kanal, der fast alles trifft, überhaupt Rangbeiträge liefern sollte, ist eine
   andere Frage als die, wie man ihn mit dem Bedeutungskanal verschmilzt.
3. **Nicht gemessen:** Der Prüfstand filtert nicht nach `project_id`/Freigabe, der
   Produktivweg schon. Das kann den Stichwortkanal nur *kleiner* machen; bei einem
   Median von 4740 gegen `max_results=5` ändert es an der Sättigung mit hoher
   Wahrscheinlichkeit nichts, gemessen ist es aber nicht.

---

## Fortschreibung 2026-08-16T05:45:00+0200 — verdrahtet und gemessen: alle drei Kriterien erfüllt

`_fuse_with_keyword_floor()` ruft seit Commit dieser Fortschreibung
`embeddings.fuse_semantic_led()`. Geändert wurde die **geteilte Funktion**, nicht die
Aufrufer — damit erfasst die Umstellung beide Suchwerkzeuge und den Abrufhaken auf
einmal. Gemessen über die Stufe `echt` (4933 → 4935 Knoten, dieselben 117 Anfragen,
`runs/kanalguete_nach_verdrahtung_2026-08-16.json`):

| | vorher | nachher |
|---|---|---|
| Trefferquote | 34/40 | **37/40** |
| einsprachig | 0/35 | **5/35** |
| Leitfall deutsch | trifft nicht | **trifft** |
| sinnloser Fall bleibt draußen | ja | ja |
| Falschmeldequote | 40/40 | 40/40 |
| Endplätze aus dem Bedeutungskanal | 4/585 (0,7 %) | **68/585 (11,6 %)** |
| Ergebnis == reine Stichwortreihenfolge | 116/117 | **0/117** |

Die drei Erfolgskriterien des Plans sind erfüllt: der belegte deutsche Fall trifft,
der sinnlose weiterhin nicht, einsprachig wird **besser** statt schlechter (5/35 liegt
auch über den 4/35 des sockellosen Vergleichspfads), und die Falschmeldequote steigt
nicht. Laufzeit unverändert (0,213 s je Anfrage).

**Was die Umstellung NICHT geheilt hat, und das gehört danebengestellt:** Knoten
`8dc84938` — der Fall, an dem am 2026-08-09 eine frühere Reparatur belegt wurde —
steht weiterhin außerhalb der ersten fünf, jetzt auf **Rang 23** statt 21. Der
`xfail`-Marker in `tests/test_kandidatendiagnose.py` bleibt deshalb stehen, mit
aktualisierter Zahl. Ein Mittelwert, der sich verbessert, ist keine Aussage über den
Einzelfall.

**Ein zweiter Beleg fiel nebenbei an:** `test_diagnose_liefert_dieselbe_liste_wie_der_echte_abrufweg`
war `xfail(strict=True)` und ist jetzt **XPASS** — Diagnosewerkzeug und echter
Abrufweg liefern seit der Umstellung dieselbe Liste. Genau dafür war `strict` gesetzt
(„damit es auffällt, sobald der Abruf ihn wiederfindet"), und es hat funktioniert.

**Vor der Umstellung rot, danach grün** —
`tests/test_kanalguete_flooranalyse.py::test_bedeutungstreffer_ueberlebt_gesaettigten_stichwortkanal`.
Die alte Formel bleibt als historischer Beleg in derselben Datei, ausgeschrieben statt
aufgerufen.

### Damit ist Punkt 2 dran: die Relevanzschwelle

Und sie ist erst **jetzt** formulierbar. Solange die Reihenfolge aus FTS-Rangplätzen
kam, gab es keine Zahl, an der sich abschneiden ließe; die Bedeutungsrangliste trägt
Kosinuswerte. Die Falschmeldequote steht unverändert bei 40/40 — erwartet, sie hing
nie an der Verschmelzung.

**Nicht getan:** Der Stichwortkanal selbst bleibt, wie er ist — im Median 4744 von
4935 Knoten. Ob ein Kanal, der 96 % des Bestands trifft, überhaupt Rangbeiträge
liefern sollte, ist die Frage hinter der Frage; sie braucht eine eigene Messung und
keine dritte Formeländerung aus dem Bauch.

---

## Kanonischer Requirement-Eintrag 2026-08-17 — Aussagegrenze der Relevanzlage

| ID | Typ | Anforderung | Gate | Status |
|---|---|---|---|---|
| MUST-LAGE-001 | MUSS | `bestandslage` darf aus den Kosinuswerten des Bedeutungskanals keine Aussage über das Fehlen passender Treffer im gesamten fusionierten Bestand ableiten. Unterschreiten die Werte die bisherigen Schwellen, muss die Lage als **uneindeutig** bezeichnet werden; eine positive Lage bleibt nur bei den kalibrierten zwei Zeichen (`bester` und `abstand`) zulässig. | `tests/test_relevanzlage.py::test_uneindeutiger_bedeutungskanal_behauptet_keinen_leeren_bestand` und echter Q2-Suchweg | PASS |

**Belegter Konflikt:** Die Anfrage `kanonisch Lage Brainlehr offene Aufgaben Tests`
liefert im Scope `brainlehr` den einschlägigen Knoten `cd571222` auf FTS-Rang 1,
während die nur aus Node-Embeddings berechnete Lage `nichts_passendes` ausgibt
(`bester=0,5372`, `abstand=0,0016`). Projektfilter und FTS-Parser sind damit als
Ursache widerlegt; die Kennzeichnung überschreitet die Aussagekraft ihres
Eingangs. BM25- und Kosinuswerte werden nicht unkalibriert vermischt.

**Verifikation:** Der neue Regressionstest war vor der Änderung rot
(`nichts_passendes != uneindeutig`). Danach bestanden 54 fokussierte Tests aus
`test_relevanzlage.py`, `test_scope_in_query.py`,
`test_knowledge_hybrid_search.py`, `test_stichwortkanal_kurze_anfragen.py`,
`test_kanalguete_schritte.py` und `test_kanalguete_flooranalyse.py`; der reine
Modul-Selbsttest bestand ebenfalls. Der direkte echte Q2-Suchweg liefert weiterhin
`cd571222` auf Rang 1 und jetzt `lage=uneindeutig` bei unveränderten Messwerten
`0,5372/0,0016`; Q1 bleibt `schwach`, Q3 bleibt `passend`.
