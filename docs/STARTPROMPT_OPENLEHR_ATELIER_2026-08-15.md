# Startprompt — was kann openlehr, und was davon gehört ins atelier

*Für ein frisches Kontextfenster. Alles ab „ANFANG DES PROMPTS" kopieren.*

---

## ANFANG DES PROMPTS

Lies zuerst `~/.claude/CLAUDE.md`, dann
`/Volumes/daten/Begod2026/brainlehr/docs/DEFINITION_ATELIER_OPENLEHR_2026-08-15.md`
vollständig. Dort steht der Auftrag im Zusammenhang; dieser Prompt nennt nur, was
sonst Zeit kostet.

**Deine Aufgabe:** Erheben, was openlehr kann — und je Fähigkeit die Trennlinie
nach ADR-014 ziehen: gehört sie ins atelier, bleibt sie in openlehr, oder ist sie
ein Bestandteil, den mehrere Domänen anfordern. **Du baust in diesem Zug nichts.**

### Wo die Sachen wirklich liegen — drei Fallen, alle gemessen

**Die Steuer-Anwendung liegt in `/Volumes/daten/Begod2026/openlehr`, Unterordner
`apps/openlehr/`, Zweig `merge/daten-features`.** Das ist ein eigenständiges Repo
(`.git` ist ein Verzeichnis), `origin` zeigt auf `Lehrmeister/3lehr-monorepo`.

**Falle 1:** Es gibt ein Repo `3lehr/openlehr` — **darin liegt etwas anderes.**
Inhalt: `GameView.swift`, `Model`, `Makefile`; einziger Commit vom 2026-08-11,
Nachricht „openlehr aus openlehr/ (Monorepo-Wurzel) gelöst". Ein Wissensknoten
behauptet, openlehr lebe dort. **Er führt in die Irre.**

**Falle 2:** Das Fernziel `sicherung` zeigt auf `3lehr/mosaikplan` — ein fremdes
Projekt. Ein Push dorthin legt openlehr-Code in ein unbeteiligtes Repo.
**Push nur nach `origin`, und nur auf ausdrückliches Wort.**

**Falle 3:** Im Arbeitsbaum liegen fremde uncommittete Dateien. `git status --short`
zuerst lesen und die Liste merken. Testläufe schreiben dort außerdem Berichte nach
`docs/openlehr/reports/` — nie `git add -A`.

### Die vier Stufen, streng getrennt

1. **Fachlogik vorhanden** — die Funktion existiert.
2. **Erreichbar** — ein Endpunkt ruft sie. **Grep nach dem FUNKTIONSNAMEN über die
   Routendateien, nicht nach dem Modulnamen.** Treffer nur unter `tests/` heißt:
   nicht erreichbar. Diese Verwechslung war hier zweimal teuer (`L-b38d85`).
3. **Bedienbar** — ein Bildschirm führt hin.
4. **Nachweislich richtig** — es gibt eine E2E-Journey vom Eingang bis zum
   Erzeugnis, und sie ist heute grün.

**Stufe 4 ist die wichtigste, und grün allein ist dort kein Beleg.** Am 2026-08-08
förderte ein Tag Prüfarbeit acht Fehler zutage, sechs davon an der Naht zwischen
Oberfläche und Fachlogik — das Rechnungschreiben war aus der Oberfläche heraus
tot, während 386 jsdom- und über 300 pytest-Tests grün waren (`L-473ba2`). Am
2026-08-15 waren elf Tests drei Tage rot, ohne dass jemand sie sich zu eigen
machte. **Fahre den Testlauf zuerst und halte die Zahl mit Nenner fest.** Wo keine
E2E-Journey existiert, lautet der Stand „nicht nachgemessen", nicht „funktioniert".

### Was bereits entschieden ist und nicht neu verhandelt wird

- **ADR-014** — ins atelier gehört, was alle Domänen gemeinsam haben oder was keine
  über sich selbst entscheiden darf. Eine Rechnungsnummer ist Steuersache, ein
  Dokumentfenster nicht.
- **ADR-016** — EÜR und UStVA werden **Tabelle**, nicht Funktion. Betreiber
  wörtlich: *„nein ich will genau das ein excel im atelier auf betriebsystem
  ebene!"* Grund: Eine Formel ist eine sichtbare Belegkette. Positivliste steht
  (37 von 511 Funktionen), Import entsperrt, **es fehlt der Bildschirm.**
  Auflage 4: benannte Bereiche sind Pflicht, `=SUMME(erloese)*ust_satz`.
- **ADR-018** — Wirkung Null. Eingelesenes trägt `norm_rang=NULL` und gilt nicht,
  bis es jemand in Kraft setzt.
- **H12** — Blaupause statt Herauslösung. openlehr wird **gelesen**, nicht kopiert.
  *„der vorhandene Code ist ja auch Wissen"* — `router.py` ist die feldgeprüfte
  Liste der Anforderung, genauer als jedes Pflichtenheft.

### Die Betreiberentscheidung vom 2026-08-15T21:15, noch nicht umgesetzt

Wörtlich: *„du setzt sie selbst in kraft, bzw opus und sol darf das. gerne
dokumentiert und durch menschen revedeirbar im atelier"*

Damit darf ein Modell `setze_in_kraft()` rufen. **Das ist eine Schemaänderung:**
Drei Trigger verlangen heute für `norm_rang` 1/2 einen menschlichen Entscheider.
**Erweitern statt streichen** — der Betreiber hat zwei Modelle benannt, nicht
„jeder"; ein gelöschter Trigger könnte diesen Unterschied nie wieder herstellen.
Einzelheiten im Knoten `4834d01f`.

### Vor jedem Bauauftrag: Existenzprobe

Fünfmal wurde am 2026-08-15 ein Agent auf etwas angesetzt, das bereits gebaut war
(`L-229bb2`) — jedes Mal, weil dem Plan geglaubt wurde statt dem Repo. **Suche nach
der SACHE, nicht nach der Kennung:** `git log --all --grep=`, und
`python3 /Volumes/daten/Begod2026/hub/scripts/symbolindex.py <begriff>` sucht nach
Tätigkeit statt nach Dateinamen.

Und in jeden Agentenauftrag gehört der Satz, der in allen fünf Fällen gerettet hat:
*„Sieht der Code anders aus als hier beschrieben, halte dich an den Code und melde
die Abweichung."*

### Offene Fragen, die dem Betreiber gehören

- **Der Name der Steuerdomäne ist entschieden, nicht offen:**
  `openchaos_einzelunternehmer`. Zwei Einwände wurden vorgebracht und beide vom
  Betreiber entkräftet — *„doch er ordnet das chaos!"* (der Name beschreibt, was
  hereinkommt, und verspricht dessen Ordnung) und *„du hast unrecht, weil es für
  deutsches steuerrecht gemacht ist"*. **Nicht neu aufrollen.** Die Regel dahinter
  gilt für jede künftige Domäne und steht als Knoten `bab2dd96`: Die Sprache eines
  Namens folgt der **Reichweite** des Benannten. Kern und Bestandteil sind
  international lesbar, weil sie jede Domäne tragen; eine Domäne, die an eine
  Rechtsordnung gebunden ist, darf und soll das im Namen sagen. Ein englischer
  Name wäre dort nicht neutraler, sondern unehrlicher — er verspräche eine
  Portabilität, die es nicht gibt.
- Ob `3lehr/openlehr` (das mit dem falschen Inhalt) aufgeräumt wird.

## ENDE DES PROMPTS
