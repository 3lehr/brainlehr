# Abstract: brainlehr

Stand der Messung: 2026-08-16, Zweig `brainlehr/b4-ausweis`.

## Was brainlehr sein möchte

brainlehr versteht sich nicht in erster Linie als Wissensspeicher, sondern als
**Aufsicht über die eigene Arbeitsweise**: eine Instanz, die prüft, ob das, was
man sich vornimmt, tatsächlich wirkt — nicht nur gebaut und gemeldet wird. Der
Anlass dafür (`CLAUDE.md`) war ein Befund von brainlehr über sich selbst:
zwölf Fälle „gebaut, laufend, meldend, wirkungslos" an einem einzigen Tag
(2026-08-13).

Architektonisch trägt brainlehr laut ADR-007 die untere von zwei Schichten im
Verbund: „Was gilt, und ob es belegt ist" — Ausweis, Freigabe, Norm mit Rang
und Geltung, Herkunft, Widerruf, Aufsicht. Das Unterscheidungskriterium zur
oberen Schicht (openlehr, die fachlichen Instanzen) ist bewusst schmal
gehalten: **brainlehr kann nein sagen** — Freigabe verweigert, Norm greift,
Trigger blockiert, Melder schlägt an. openlehr kann das nicht, es stellt nur
bereit.

Vier Fragen sollen laut `CLAUDE.md` jede Instanz beantworten: Wer fragt hier
(Ausweis)? Worüber wird Wissen geführt? Was ist ein Treffer wert (heute noch
offen, Schwelle 0,65 pauschal für Code wie Rechtssatz)? Was darf nach außen
(Freigabestufen offen/intern/gesperrt, Vorgabe `intern`)?

## Was es schon ist — gemessen

**Bestand** (`brainlehr.db`, gelesen über `haken/ort.py::DB`, 32 Tabellen):
5034 Knoten (`knowledge_nodes`), 963 Lehren (`lessons_learned`), 9936
Kanten (`knowledge_relations`), 16144 Zugriffe (`access_log`), 55 Datenbank-
Trigger. Diese Zahlen liegen deutlich über den in `CLAUDE.md` selbst
genannten (2166 Knoten, 833 Lehren, „über 6100" Kanten, „10000" Zugriffe) —
die Projektbeschreibung veraltet also schneller, als sie fortgeschrieben
wird, ein Beispiel für genau das Muster, das das System an anderer Stelle
selbst sucht.

**Gebaut:** 33 Melder-Skripte (`ls melder/*.py`), 95 Dateien unter `kern/`,
224 Testdateien unter `tests/`, 24 ADRs, 99 Markdown-Dokumente unter `docs/`,
davon 48 mit Präfix `PLAN`.

**Der zentrale Ehrlichkeitsbefund, selbst gemessen (`melder/ausloeserlos.py`):
Von 33 Meldern haben 29 keinen Auslöser** — keinen Eintrag in
`settings.json`, keinen geplanten Lauf, keinen Aufrufer, der selbst einen
Auslöser hat. Nur 4 sind tatsächlich verdrahtet. Ein Melder ohne Auslöser
zählt nach eigener Definition (`CLAUDE.md`) als keiner — der Bestand belegt
das an sich selbst, nicht nur behauptet.

**Was wirkt, belegt am `pre-push`-Hook:** Er ruft den geteilten
`push_guard.py`, prüft Messauswertungen neuer `runs/*.json` gegen
`melder/messregeln.py` und vergleicht Landkarten unter `docs/karten/` gegen
eine Neuerzeugung. Das ist ein Mechanismus, der bei einem Verstoß tatsächlich
blockiert — laut `STAND.md` an Rollout-Fehlern selbst zweimal falsch positiv
grün gemessen, beim dritten (korrekten) Testaufbau griff er nachweislich.

**Offene Stellen, laut `STAND.md`/ADRs unverändert:** Die Relevanzschwelle
(„was ist ein Treffer wert") ist für Code und Rechtssatz identisch, obwohl
als Lücke benannt. Der Bedeutungskanal der Suche steuert laut eigener Messung
nur 4 von 585 Endplätzen bei, der Stichwortkanal dominiert. Eine gebaute
Fusionsfunktion (`fuse_semantic_led()`) lag laut `STAND.md` vom 2026-08-12
bis mindestens zum aktuellen Fenster unverdrahtet im Code.

**Fazit in einem Satz:** Der Anspruch — Aufsicht statt Speicher — ist an
mindestens einer Stelle belegt (Melder-Selbstprüfung, Push-Wächter); an der
Mehrheit der eigenen Melder (29 von 33) ist er noch Absicht ohne Mechanismus.
