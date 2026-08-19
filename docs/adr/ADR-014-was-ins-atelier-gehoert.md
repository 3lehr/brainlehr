# ADR-014: Was ins atelier gehört — Gemeinsames und Unabtretbares, sonst nichts

**Stand** 2026-08-14T21:36:26+0200
**Status** Angenommen
**Betrifft** `atelier` (`app/`), jede Domäne
**Entscheider** Betreiber, 2026-08-14

## Die Vorgabe, wörtlich

> *„dann müssen wir eben atelier schlanker machen! atelier nur noch security und
> darstellung (3dgraph usw.) + einstellungen die llm grundeinstellungen: apis
> usw. sowie grundeinstellungen für das brainlehr.."*

## Die Regel dahinter, und sie ist schärfer als die Liste

Die drei genannten Dinge haben ein gemeinsames Merkmal, und daraus wird die
Regel, die auch den vierten und fünften Fall entscheidet:

> **Ins atelier gehört, was alle Domänen GEMEINSAM haben — oder was keine Domäne
> über sich selbst entscheiden darf. Alles andere ist Domäne.**

| Beispiel | Grund |
|---|---|
| **Sicherheit**, Ausweis, Freigabe | *unabtretbar* — eine Domäne, die ihre eigene Zulassung erteilt, ist keine Schranke |
| **Darstellung**: Rahmen, Navigation, Wissensraum-Ansicht, **Dokumentfenster** | *gemeinsam* — nur so sieht jede Domäne aus wie ein Teil derselben Anwendung |
| **Modellzugänge**: welches Modell, welche Schnittstelle, was das Haus verlassen darf | *unabtretbar* — sonst hätte jede Domäne ihre eigenen Zugangsdaten und ihre eigene Antwort auf die Frage, ob Daten hinausgehen |
| **brainlehr-Grundeinstellungen** | *gemeinsam* — sie gelten für den Speicher unter allen Domänen |
| Belegkategorien, Fristenrechnung, Steuerlogik, Korrekturregeln | **Domäne** |

**Was das für F19 bedeutet, und es ist ein Gewinn:** Die Entscheidung *„lokale
KI, Auswärtsgang nur mit Zustimmung in den Einstellungen"* liegt damit an
**genau einer** Stelle. Keine Domäne kann sie umgehen, keine muss sie
wiederholen. Eine Schranke, die an fünf Orten gepflegt wird, ist an vier davon
irgendwann veraltet.

## Nachtrag am selben Tag: „gemeinsam" ist nicht dasselbe wie „immer da"

Betreiber, unmittelbar danach:

> *„nein dokumentenfenster wird auch aus dem atelier rausgeschmießen! weill vll
> gibt es in zukunft auch openlehr_projekX ohne dokumente"*

**Die Fassung oben war zu grob**, und der Einwand trifft: Sie kannte nur
*gemeinsam* und *fachlich*. Es fehlt die Sorte dazwischen — **gemeinsam gebaut,
aber nicht immer gebraucht.** Eine Domäne ohne Dokumente soll kein
Dokumentfenster tragen.

Der Kern ist damit kleiner, und es sind drei Sorten statt zwei:

| | | |
|---|---|---|
| **Kern** — immer da | Sicherheit, Rahmen und Navigation, Einstellungen (Modellzugänge, brainlehr-Grundeinstellungen) | ohne das gibt es keine Anwendung |
| **Bestandteil** — gemeinsam gebaut, auf Anforderung geladen | **Dokumentfenster**, Raumdarstellung des Wissens, künftige | eine Domäne fordert an, was sie braucht |
| **Domäne** | alles Fachliche | — |

**Warum das Dokumentfenster ein Bestandteil wird und nicht in die Domäne
wandert** — nach der Regel aus H12, nicht nach Geschmack: Beide bisher
genannten Domänen erzeugen Dokumente (Steuerchaos: Rechnung und
Behördenbrief · Korrekturator: das Korrekturblatt für die Berufsschullehrerin).
In der Domäne läge es beim zweiten Kind kopiert. **Was beim zweiten Kind kopiert
wird, wandert nach unten.**

Damit ist beides erfüllt: `openlehr_projektX` ohne Dokumente lädt es schlicht
nicht, und wo es geladen wird, sieht es überall gleich aus.

**Was das kostet, und es ist neue Arbeit:** Das atelier braucht einen
Mechanismus für anforderbare Bestandteile, den es heute nicht hat. Die
Anforderung steht im Manifest der Domäne (ADR-013) — dieselbe Stelle, an der
schon Wissen und Werkzeug deklariert werden. ADR-010 bleibt inhaltlich
unberührt: Das Fenster ändert seinen Ort, nicht seine Bauform.

## Der ehrliche Befund zum Wort „schlanker"

**Im atelier ist heute nichts Fachliches, das entfernt werden müsste.** Gemessen
sind es 17 Swift-Dateien unter `Sources/Atelier`, alle tragen Rahmen,
Navigation, Ausweis, Dienstaufsicht, Quellen- und Wissensraum-Ansichten,
Dokumentfenster und den Domänen-Import. Keine einzige kennt Steuerrecht.

**Die Regel wirkt also vorwärts, nicht rückwärts** — sie räumt nicht auf, sie
verhindert. Und sie tut das an der Stelle, an der es sonst passiert wäre: beim
ersten Domänen-Bildschirm, der „nur schnell" nativ gebaut wird, weil es gerade
einfacher ist.

**Was tatsächlich fehlt:** Der Einstellungsbildschirm trägt heute nur den
Betrachtungsabstand. Modellzugänge und brainlehr-Grundeinstellungen sind **neu
zu bauen**, nicht umzuräumen.

## Der Preis

Jedes Darstellungsbedürfnis einer Domäne, das das atelier nicht kennt, ist
**Arbeit an der Trägerschicht** — und damit langsamer, als es die Domäne selbst
hinschreiben könnte. Das ist der bewusst bezahlte Gegenwert dafür, dass keine
Domäne die Anwendung beschädigen und keine aus der Reihe tanzen kann.

Die Gegenprobe, wenn der Preis zu hoch wird: Braucht eine Domäne wirklich ein
eigenes Bedienelement, oder braucht sie nur einen Fachbildschirm? Fachbildschirme
sind Web (ADR-013) und kosten die Trägerschicht **nichts**.


---

## Präzisierung 2026-08-19T19:15:00+0200 — „Raumdarstellung" meint die Technik, nicht den Bildschirm

**Anlass:** Bei der Umsetzung eines Katalogs nach dieser ADR entstand ein
Widerspruch. Die Tabelle oben nennt „Raumdarstellung des Wissens" als
**Bestandteil**. Ein Bestandteil wird nur geladen, wenn **eine Domäne ihn
anfordert** (`SeitenleistenEintrag.bestandteil`, gefiltert in
`AtelierApp.sichtbareEintraege`). Wörtlich umgesetzt verschwände damit
brainlehrs **eigener** Wissensraum aus der Seitenleiste, sobald keine Domäne
ihn nennt.

**Die Zweideutigkeit:**

| Lesart | Folge |
|---|---|
| die **Darstellungstechnik**, die eine Domäne für ihr Wissen anfordern kann | Bestandteil |
| brainlehrs **eigener Wissensbildschirm** | Kern |

**Entschieden: die erste.** Die Begründung steht in der Liste selbst —
„Dokumentfenster, Raumdarstellung des Wissens, künftige" nennt drei **Sorten
von Darstellung**, die eine Domäne anfordert. brainlehrs eigener
Wissensbildschirm ist keine anforderbare Sorte, sondern das, worauf die
Anwendung steht.

**Folge:** Der heutige Wissensraum-Bildschirm bleibt **Kern**. Die Zeile in
der Bestandteil-Tabelle gilt für eine künftige, von einer Domäne anforderbare
Raumdarstellung — die es noch nicht gibt.

**Warum das hier steht und nicht nur im Plan:** Die Umsetzung wäre ohne diese
Klärung entweder falsch gewesen (ein Kernbildschirm verschwindet) oder die
ADR-Zeile wäre unerfüllt geblieben. Ein Widerspruch, den man beim Bauen
findet, gehört in die Entscheidung zurück, nicht in den Bauplan.

**Entscheider:** Betreiber, 2026-08-19 („so wie du sagst! go!" auf eine
Vorlage, die genau diese Frage stellte — Knoten `5bc4a203`).
