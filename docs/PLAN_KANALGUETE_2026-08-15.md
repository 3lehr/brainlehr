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
