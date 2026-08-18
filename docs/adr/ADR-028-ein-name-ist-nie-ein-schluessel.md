# ADR-028: Ein Name ist nie ein Schlüssel

**Status:** angenommen
**Datum:** 2026-08-18T16:04:33+0200
**Entscheider:** Betreiber
**Betrifft:** brainlehr, und jedes Repo des Verbunds, das Gegenstände benennt

## Betreiberentscheidung

Wörtlich, 2026-08-18: *„und wenn wir für solche sachen immer eine feste id
anlegen? so wie wir es bei personen namen gemacht haben?"* — auf den Befund,
dass niemand mehr sagen konnte, wie oft die Werkbank schon umbenannt worden
war. Zustimmung zur ausgearbeiteten Fassung: *„go!"*

## Anlass, gemessen

Eine Sitzung wog ab, ob `atelier` in `lehrAtelier` umbenannt werden soll, und
führte als Gegenargument an, das sei „die zweite Umbenennung in fünf Tagen" —
aus dem Gedächtnis, mit falsch zitierter ADR-Kennung (025 statt 008).

Gemessen war es die **dritte Namensform desselben Gegenstands**:

| wann | von → nach | Beleg |
|---|---|---|
| 2026-08-14 | `BrainlehrApp` → `Atelier` | ADR-008, `c6c82863` |
| 2026-08-14 | Nachzug, weil halb umbenannt | `1703dce9` |
| 2026-08-18 | `Atelier` → `LehrAtelier` | ADR-027, `7db10b10` |

Alles davon stand in `git log --diff-filter=R`, zwei Sekunden entfernt. Die
Vorgeschichte war nicht unbekannt — sie war **unabgefragt**. Dieselbe Klasse
wie der UTC-Fall vom 2026-08-14 („war das nicht schon einmal beschlossen? —
ja, war es").

## Das Problem ist nicht, dass IDs fehlen

Die Wissensknoten haben beides: `id TEXT PRIMARY KEY` (stabil) und
`path TEXT UNIQUE` (der Name). **Verwiesen wird durchgehend auf den Namen:**

- `kanten.source_path` / `target_path` → `REFERENCES knowledge_nodes(path)`
- `lessons_learned.node_path`, `access_log.node_path`, `planentscheidung.node_path`

`ON UPDATE CASCADE` fängt das innerhalb der Datenbank. Jede Kennung, die
einmal **nach außen** gegangen ist — in eine ADR, einen Commit, einen
Startprompt, eine Nachricht an eine andere Sitzung — zeigt nach einer
Umbenennung ins Leere.

Derselbe Unterschied hat am selben Tag eine vollständige Abrufmessung
entwertet: das Messskript verglich `id` gegen `path`, 20 von 45 Fällen konnten
nie treffen, und das Ergebnis sah nicht kaputt aus, sondern **plausibel
schlecht** (`L-0e0ab6`, inzwischen 10 Vorkommen).

## Entscheidung

Ein Gegenstand hat eine **bedeutungslose ID**. Sein Name ist ein **Attribut
mit Geltungszeitraum** (`gilt_ab`, `gilt_bis`, `beleg`).

Bedeutungslos ist Bedingung, nicht Geschmack: eine sprechende ID
(`atelier-001`) ist wieder ein Name und wird beim nächsten Mal genauso falsch.

Ein Gegenstand trägt **mehrere Namensarten gleichzeitig** — Rufname,
Bündelkennung, Pfad, Anzeigename —, jede mit eigener Geltung. Diese Bedingung
ist nicht dekorativ: beim Bau lieferte `aufloesen()` prompt die Bündelkennung
als Antwort auf die Frage nach dem Rufnamen, weil beide gleichzeitig offen
waren. Der Selbsttest hält den Fall fest.

Umgesetzt in `kern/gegenstand.py`. Die entscheidende Fähigkeit ist
`aufloesen()`: sie beantwortet auch den **alten** Namen. Wer `Atelier` sucht,
findet den Gegenstand, der heute anders heißt, samt Zeitraum — ohne zu wissen,
dass er umbenannt wurde. Das ist die Frage, die niemand stellt, weil niemand
weiß, dass er sie stellen müsste.

## Alternativen, und warum sie nicht reichen

**`git log` genügt.** Es kennt die Kette vollständig und pflegt sie ohne
Zutun — deshalb ist es der Erstbestand (`--aus-git`). Aber es kennt nur
Dateien: eine Bündelkennung, ein Dienstname, eine Domänenkennung stehen dort
nicht. Und es beantwortet nur die Frage, die schon jemand als Umbenennung
erkannt hat.

**Umbenennungen einfach vermeiden.** Genau das war die Empfehlung, die heute
richtig abgelehnt wurde: `lehrAtelier` ist ein besserer Name. Wer Umbenennung
verhindert, um Kennungen stabil zu halten, bezahlt gute Namen mit schlechter
Buchführung.

**Namen als Schlüssel behalten und überall `CASCADE` setzen.** Wirkt bis zur
Repo-Grenze und keinen Schritt weiter — der Fall, der heute weh tat, lag
außerhalb.

## Preis, ausdrücklich

Zwei Tabellen mehr und ein Handgriff bei jeder Umbenennung. Der Bestand ist
kein Argument dafür oder dagegen: der Grund ist die **Reihenfolge**. Ein
Register, das erst nach der vierten Umbenennung entsteht, hat die ersten drei
nicht — und genau die sind die, an die sich niemand erinnert.

Was bewusst **nicht** getan wird: die bestehenden `*_path`-Fremdschlüssel
umzustellen. Das wäre ein Umbau am Herzstück mit ungemessenem Nutzen; die
Kennungen dort sind innerhalb der Datenbank durch `CASCADE` gedeckt. Diese ADR
entscheidet die Bauform für Gegenstände, nicht eine Migration.

## Woran sich Erfolg messen lässt

`aufloesen("<alter Name>")` liefert den heutigen Namen samt Geltungszeitraum,
für jeden Gegenstand, der einmal umbenannt wurde. Misslingt das bei der
nächsten Umbenennung, wurde sie nicht eingetragen — und das ist der Befund,
nicht die Ausrede.
