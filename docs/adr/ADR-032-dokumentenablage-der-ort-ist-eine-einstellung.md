# ADR-032 — Die Dokumentenablage kommt, und ihr Ort ist eine Einstellung

Angelegt 2026-08-21T07:05:00+0200.
Status: **entschieden** (Betreiber, 2026-08-21).

## Anlass

Betreiberentscheidung, woertlich: *„aber brainlehr soll muss auch
dokumentenablage sein, siehe buckeberg weg und openlehr_einzelunternehmer
doemaene"* — und auf die Frage nach dem Ablageort: *„der user soll einstellen
koennen?"*

Damit sind zwei Dinge entschieden: **dass** es eine Ablage gibt, und **dass
der Ort keine Grundsatzentscheidung ist, sondern eine Einstellung je
Domaene**.

## Was dagegen sprach, und warum es nicht dagegen spricht

`hub/docs/adr/ADR-026-brainlehr-zweckbestimmung.md:41` haelt fest: „Kein
Dokumentenarchiv. Quellen bleiben, wo sie sind; brainlehr haelt Verweis und
Pruefsumme, nicht die Kopie."

**Dieser Satz verbietet den Volltext im WISSENSINDEX, nicht die Ablage.** Der
Unterschied ist keine Wortklauberei, er ist gemessen: Am 2026-08-21 wurden 951
BSI-Controls als `nachschlagewerk` eingelesen. Kein einziger Katalogknoten
tauchte in irgendeinem Ergebnis auf -- und die Trefferquote fiel trotzdem von
14/35 auf 13/35, weil bm25 korpusrelativ ist und schon die blosse Anwesenheit
fremder Zeilen die Rangfolge der eigenen verschiebt (`L-f8b529`). Ein
Verwaltervertrag ueber 40 Seiten taete dasselbe, nur staerker.

**ADR-026 bleibt damit in Kraft, in seinem eigentlichen Sinn**, und diese ADR
ist seine Umsetzung statt seine Aufhebung.

## Gemessener Ist-Stand (2026-08-21)

| | |
|---|---|
| Tabelle fuer Dateien | **keine** -- 36 Tabellen, keine davon |
| `symbolindex` ueber den Verbund zu „Dokumentenablage" | **0 Treffer** |
| `kern/dokument.py` (852 Zeilen) | das Dokument**fenster** (CRDT, Bausteine, Anmerkungen) -- Verfassen, nicht Verwahren |
| `quell_hash` gesetzt | **49 von 5 240 = 0,9 %** |

Die letzte Zahl ist die wichtigste: Der Mechanismus, der „Verweis und
Pruefsumme" ueberhaupt traegt, ist gebaut und praktisch unbenutzt. Eine Ablage
darauf zu setzen heisst zuerst, ihn scharf zu machen.

Zwei Suchwege, weil eine Existenzaussage im NEGATIVEN zwei braucht
(`L-39574b`): Struktur (Tabellenliste) und Begriff (`symbolindex`, sucht nach
Taetigkeit statt nach Dateinamen).

## Entscheidung

**Drei Schichten, und nur die mittlere geht in den Volltextindex.**

| Schicht | Inhalt | Index |
|---|---|---|
| Ablage | die Datei selbst, unveraendert, mit Pruefsumme | keiner |
| Knoten | Verweis, Pruefsumme, Herkunft, Geltung, **kurze Zusammenfassung** | Arbeitsbestand |
| Auszug | eine einzelne belegte Stelle, mit Fundstelle | **eigener Dokumentindex** |

**NACHTRAG, Betreiberentscheidung vom selben Tag, und sie ist besser als der
erste Entwurf:** *„warum bauen wir fuer dokumente nicht einen zweiten
vektorraum? den ich explizit per prompt aufrufen kann? zb mit der frage: zeige
mir alles was mit Frau Doeldissen zu tun hat?"*

Die Auszuege gehen damit NICHT in den Arbeitsindex, sondern in einen
**zweiten, eigenen Vektorraum**, der nur auf ausdrueckliche Frage geoeffnet
wird. Das loest das Verduennungsproblem an der Wurzel statt am Filter -- und
genau dort sitzt es: Am 2026-08-21 wurde gemessen, dass die Gattung
`nachschlagewerk` am FILTER wirkt und nicht am INDEX; dieselbe Menge als
`arbeitsbestand` lieferte exakt dieselbe Trefferzahl (`L-f8b529`). Ein zweiter
Raum kann per Bauart nicht verduennen, weil er in der taeglichen Suche gar
nicht vorkommt.

**Was ein zweiter Raum zusaetzlich moeglich macht**, und was im ersten Entwurf
fehlte: Dokumente duerfen dort in der Koernung liegen, die zu Dokumenten
passt -- Abschnitte statt Ganzdateien --, ohne Ruecksicht darauf, was das mit
der Rangfolge des Arbeitsbestands macht. Die beiden Raeume muessen sich in
nichts gleichen.

**Die Grenze, die dabei gemessen werden MUSS, bevor jemand sich darauf
verlaesst:** Die Beispielfrage ist eine NAMENSfrage. Einbettungen sind
ausgerechnet bei Eigennamen schwach -- sie finden Bedeutungsnaehe, und ein
Name hat keine. Wer „alles zu Frau Doeldissen" ueber einen reinen Vektorraum
sucht, bekommt aehnlich KLINGENDE Stellen. Der Dokumentraum braucht deshalb
beides: Vektoren fuer die Sachfrage und einen exakten Namensweg (FTS,
Entitaetenliste) fuer die Personenfrage. Welcher Anteil welcher Frage gehoert,
ist zu messen und nicht zu setzen.

**Der ORT der Ablage ist eine Einstellung je Domaene**, nicht je Haus:

* `ablage.<domaene> = domaene` — die Datei bleibt, wo sie ist (buckeberg
  `dokumente/`). Die Domaene bleibt autark, brainlehr haelt Verweis und
  Pruefsumme. **Vorgabewert**, weil er nichts bewegt.
* `ablage.<domaene> = brainlehr` — die Datei wandert in brainlehrs Ablage.
  brainlehr wird zur einzigen Wahrheit; die Domaene haengt dafuer an
  brainlehr.

Bauform uebernommen von `mitstart.<domaene>` (ADR-023) -- dort ist eine
Einstellung je Domaene bereits entschieden und gebaut. Kein zweites Muster.

**Was die Einstellung NICHT entscheidet:** ob eine Pruefsumme gefuehrt wird.
Die wird immer gefuehrt, an beiden Orten. Sonst gaebe es eine Stellung, in der
zwei Wahrheiten nebeneinander altern und nichts es merkt -- genau der Zustand,
den ADR-026 verhindern wollte.

## Warum die Einstellung und nicht eine feste Wahl

Weil die richtige Antwort je Domaene verschieden ist und keine von beiden
falsch:

* **buckeberg** fuehrt WEG-Vertraege, die dort ohnehin liegen und dort
  gelesen werden. Ein Umzug brächte nichts und naehme der Domaene ihre
  Eigenstaendigkeit.
* **openlehr_einzelunternehmer** fuehrt Steuerbelege mit
  **Aufbewahrungsfristen**. Dort ist eine Ablage mit Fristenwerk der Zweck,
  nicht das Beiwerk -- und `kern/aufbewahrung.py` existiert bereits.

Eine Hausentscheidung haette eine der beiden Domaenen zu etwas gezwungen, das
ihr nicht entspricht.

## Was das kostet

* `quell_hash` wird fuer Dokumentknoten zur **Pflicht** -- heute ist es bei
  0,9 % gesetzt. Ohne diese Verschaerfung ist die Ablage eine Kopie mit
  Absichtserklaerung.
* Ein Melder, der eine Datei findet, deren Pruefsumme nicht mehr stimmt.
  Ohne ihn merkt niemand, dass Verweis und Wirklichkeit auseinandergelaufen
  sind -- und ein unbemerkter Auseinanderlauf ist schlimmer als gar keine
  Pruefsumme, weil er Sicherheit vortaeuscht.
* Bei `= brainlehr` eine echte Ablage samt Umzugsweg und Rueckweg.

## Verworfen

* **Volltext des Dokuments in `content`.** Gemessen schaedlich, siehe oben.
  Der Auszug mit Fundstelle leistet dasselbe fuer den Menschen und kostet den
  Index fast nichts.
* **Feste Hausentscheidung fuer einen Ort.** Zwingt eine der beiden Domaenen.
* **Ablage ohne Pruefsumme.** Waere eine Kopie, und Kopien altern getrennt.

## Abnahme

1. Ein Dokument wird in beiden Stellungen abgelegt, und in BEIDEN findet der
   Speicher es ueber seine Zusammenfassung.
2. Negativfall: Ein Dokumentknoten ohne `quell_hash` wird abgewiesen.
3. Gegenprobe in beide Richtungen: Wird die Datei nach der Ablage veraendert,
   MELDET der Waechter das -- und wird sie nicht veraendert, meldet er nichts.
4. Die Trefferquote des Arbeitsbestands bleibt gleich, gemessen gegen
   dieselbe Nulllinie (heute 14/35) mit demselben Fragensatz. Das ist die
   Probe, die ADR-026 einloest.
