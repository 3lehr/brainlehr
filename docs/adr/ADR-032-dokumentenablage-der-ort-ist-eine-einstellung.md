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

## NACHTRAG 2026-08-21T10:05 — der Konsil hat entschieden, gegen den Vorschlag

Der Betreibervorschlag oben (zweiter Vektorraum, „warum bauen wir fuer
dokumente nicht einen zweiten vektorraum?") wurde in einem Konsil mit drei
Linsen gemessen. **Ergebnis 2 zu 1 gegen ihn.** Das steht hier, weil es eine
Betreiberentscheidung umstoesst und er widersprechen koennen muss.

| Linse | Empfehlung | tragendes Argument |
|---|---|---|
| Abrufguete | **C** | Der Verlust ist NICHT gattungsabhaengig (dieselbe Menge als `arbeitsbestand` liefert dieselbe Zahl) und er **saettigt**: 951→13/35, 2 853→12/35, 9 510→12/35 |
| Betrieb | A | Wachstum, Loeschzyklus, `sensibel`-Kopplung |
| Irrtumskosten | **C** | siehe unten — Falsifizierbarkeit |

**Das entscheidende Argument ist die Falsifizierbarkeit, und es wurde
nachgestellt, nicht abgeleitet:**

Eine Kopie wurde in zwei Raeume geteilt (887 Arbeit / 4 354 Dokument), dann
die `gattung` eines Knotens gewechselt, ohne seinen Vektor umzuziehen.
Ergebnis: Der Knoten steht in **keinem** Raum — 0 von 0, ohne Fehlermeldung.
Auf `knowledge_embeddings` haengen nur zwei Modellsperren, kein weiterer
Trigger. Es ist exakt das Muster, das `schema.sql:392-397` fuer `sensibel`
bereits dokumentiert: „der Eintrag verschwindet, ohne dass ein neuer
entsteht."

**In C ist dieser Zustand nicht herstellbar.** Derselbe Wechsel laesst
FTS-Zeile und Vektorzeile unberuehrt; nur der Filter entscheidet anders.

**Und das Messinstrument selbst faellt aus:** `melder/vektorstand.py` meldet
gegen den Bestand „5 241 gesamt, 0 ohne Einbettung" — ein aussagekraeftiger
Nullwert. Gegen den A-Aufbau meldet er **4 354 ohne Einbettung**, also 4 354
Falschmeldungen. Und nach naivem Mitziehen ueber beide Tabellen ist er fuer
genau den A-eigenen Fehler blind: Fuer den umgezogenen Knoten meldet er
„Einbettung vorhanden: 1", waehrend der Knoten in keinem abfragbaren Raum
steht.

> **A scheitert erst, wenn jemand einen einzelnen Knoten vermisst — kein Log,
> keine Kennzahl. C scheitert in einer Messung.**

**Was damit gilt:** Die Auszuege gehen NICHT in einen zweiten Vektorraum. Die
drei Schichten bleiben (Ablage · Knoten · Auszug), der Auszug liegt im
vorhandenen Index. Der gemessene Hebel gegen die Verduennung ist ein anderer
und von dieser Frage unabhaengig: getrennte Kandidatenbudgets fuer Knoten und
Lehren statt einer gemeinsamen Liste von 17
(`haken/suchpfad_abruf.py:169-171`).

## NACHTRAG 2026-08-21 — `sensibel` ist fuer Dokumente Dritter das falsche Werkzeug

Unabhaengig vom Konsil gemessen, mit dem echten Modell gegen 5 241
Bestandsvektoren, Eigenname „Doeldissen":

Ein sensibel gefuehrter Dokumentabschnitt, dessen Name **nicht im Titel**
steht, landet auf Rang **854** (blosser Name), **1 130** (natuerliche Frage),
**2 571** (Umlautschreibung) — und steht im Volltextindex gar nicht. Steht der
Name im Titel, ist er Rang 1, weil der Titel nicht verschluesselt wird.

**Kein Leck, sondern Unauffindbarkeit** — und diese Praezisierung korrigiert
eine Annahme aus der Betriebslinse: `knowledge_add(sensibel=True)` ersetzt
`summary` durch „(verschluesselt)" und leert `content` **vor** dem Einbetten
(`knowledge_mcp_server.py:4048-4059`, selbst nachgeprueft). `build_embeddings`
kennt das Feld nicht, sieht aber nur den Platzhalter.

**Daraus folgt fuer `BDW-P15`:** Dokumente Dritter werden ueber `mandant` und
`kreis` (`kern/trennung.py::sichtbar_sql`, seit B3 an 12 Stellen erzwungen)
oder ueber `freigabe` geschuetzt — **nicht** ueber `sensibel`. Das sind
Abfragefilter: umkehrbar, und sie lassen den Kanal intakt, der Namen findet.
`sensibel` ist die Verschluesselung des Inhalts und damit ein anderes
Werkzeug fuer eine andere Frage.

**Die Falle ist heute unbetreten:** gemessen traegt **kein einziger** der
5 241 Knoten `sensibel = 1`. Die Ruecknahme 1→0 bringt den FTS-Eintrag
korrekt und ohne Duplikat zurueck.

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
