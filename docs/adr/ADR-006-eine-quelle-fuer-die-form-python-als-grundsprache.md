# ADR-006: Eine Quelle für die Form, Python als Grundsprache

**Stand** 2026-08-13T22:30:48+0200
**Status** Angenommen
**Betrifft** `kern/`, `app/Sources/BrainlehrCore/`, `shared-knowledge/schema.sql`, jede künftige Sprachfassung
**Entscheider** Betreiber, 2026-08-13, wörtlich: *„Ich bin bei Datenbank Schema, py als
Grundsprache weil weit verbreitet, generell aber offen. Wer Rust braucht soll Rust benutzen"*

## Die Frage

Der Startprompt zur Grundarchitektur (`docs/STARTPROMPT_GRUNDARCHITEKTUR_2026-08-13.md`)
nennt als „offenen Nerv": Fachlogik existiert doppelt, in Swift und in Python. Daraus
seine Frage 2: *Wo lebt die Fachlogik — Swift-Bibliothek, Python hinter einem Dienst,
oder ein Schema, aus dem beides erzeugt wird?*

Solange diese Frage offen ist, ist jede Aussage über Schichten Papier — eine Schicht,
die zweimal existiert, ist keine.

## Der gemessene Ist-Stand — der Startprompt lag falsch

Nachgemessen am 2026-08-13T22:30, Zweig `brainlehr/b4-ausweis`. Der Startprompt führt
zwei Doppelungen. **Eine davon ist keine.**

| Behauptet | Gemessen |
|---|---|
| **Fundstellen-Modell doppelt** (`Fundstelle.swift` ↔ `kern/fundstelle.py`) | **Keine Doppelung der Logik.** `Fundstelle.swift` (97 Zeilen) ist ein `Decodable`-Struct, das die Antwort von `POST /api/fundstelle` dekodiert. Der eigene Dateikopf sagt es wörtlich: *„Die App BESTELLT diese Antwort, sie rechnet sie nicht selbst."* `kern/fundstelle.py` (512 Zeilen) rechnet — dreistufig, gepflegt vor gerechnet vor „weiß ich nicht". Das ist bereits eine Dienstgrenze, keine zweite Fassung. |
| **Lesbarkeitsrechnung doppelt** (`Anzeigeform.swift` ↔ `lesbarkeit.py`) | **Zutreffend, aber bewusst und begrenzt.** Beide lesen `app/Resources/lesbarkeit.json`. Die Datei begründet es selbst: *„Die Formel steht zweimal — sie ist fünf Zeilen und in beiden Sprachen trivial. Die ZAHLEN stehen einmal, denn sie sind das, was sich ändert."* |

**Der Rest von `BrainlehrCore` hat gar kein Gegenstück:** `DienstZustand`, `Quelldokument`,
`Sichtbarkeit`, `Sitzungsstrom`, `Sitzungswahl`, `Verschmelzung`, `RepoWurzel`,
`PythonAuswahl` existieren nur in Swift. `AusweisProtokoll.swift` bezeichnet sich selbst
als *„reine Brücke zu pflege/ausweis_helfer.py"* — also ebenfalls Dienstgrenze.

**Und ein Fehlalarm aus reiner Namensgleichheit:** `Rangfolge.swift` ordnet Quellen für
die Anzeige, `kern/rangfolge.py` liefert Rangsignale für den Wissensabruf. Gleiches Wort,
zwei Gegenstände, kein gemeinsamer Code. Wer nach Dateinamen misst, zählt sie als
Doppelung — dieselbe Fehlerform wie `L-9e1d80` (Suche nach Modulnamen, verdrahtet nach
Vorgangsnamen).

**Die tatsächliche Doppelung ist damit:** eine bewusste Formel von fünf Zeilen — und
**ein unerzwungener Feldvertrag**: die zwölf Felder von `Fundstelle` stehen in Swift
getippt und werden in Python erzeugt; **nichts prüft, dass beide dasselbe meinen.**

## Entscheidung

1. **Das Datenbankschema ist die Quelle der Form.** Felder, Typen, Bedingungen und
   Beziehungen stehen in `shared-knowledge/schema.sql` und werden dort durchgesetzt —
   nicht in einem Serverprozess. Das ist keine neue Regel, sondern die Verallgemeinerung
   einer bestehenden (`brainlehr/CLAUDE.md`: *„Guards gehören als Datenbank-Trigger"*).
2. **Python ist die Grundsprache.** Fachlogik lebt in `kern/`. Das benennt den
   vorhandenen Schwerpunkt: `kern/`, der MCP-Server, alle Melder und Haken sind Python.
3. **Andere Sprachen sind ausdrücklich erlaubt** — Swift für die Oberfläche, Rust wo
   Rust gebraucht wird.
4. **Die Bedingung, ohne die 3. die Entscheidung aufhebt:** Eine zweite Sprache darf das
   Schema **lesen**, nie **neu behaupten**. Sobald eine Feldliste oder eine Bedingung ein
   zweites Mal getippt dasteht, ohne dass etwas die Übereinstimmung erzwingt, ist die
   Trennung still verloren.

## Was daraus konkret zu tun ist

**Nicht** Fachlogik verlagern — die liegt bereits richtig. Sondern **den Feldvertrag
erzwingen**, an der einen Stelle, an der er heute unerzwungen ist.

Kleinste Form, die fehlschlägt, wenn beide Seiten auseinanderlaufen: **eine
Golden-JSON-Datei, zwei Verwender.** `kern/fundstelle.py` erzeugt sie aus einem echten
Fall; ein pytest-Fall prüft die Schlüsselmenge, ein XCTest-Fall dekodiert dieselbe Datei
nach `Fundstelle`. Rot-vor-Grün ist beweisbar: ein Feld in Python ergänzen oder umbenennen
→ die Swift-Seite fällt.

Kein Codegenerator. Er wäre selbst Software, die gepflegt und geprüft werden muss, und
beim ersten Sonderfall schreibt jemand doch von Hand daneben.

## Alternativen, samt Ablehnungsgrund

| Weg | Abgelehnt weil |
|---|---|
| **Alles nach Swift**, Python nur Werkzeug | Kehrt den gemessenen Schwerpunkt um. `kern/` ist 76 Module; Swift-Core 12 Dateien, davon 10 ohne Gegenstück. Und Swift bindet an eine Plattform, die die Fachlogik nicht braucht. |
| **Vollständige Erzeugung beider Fassungen aus einem Schema** | Die meiste Mechanik für den unsichersten Gewinn. Bei gemessenen fünf doppelten Formelzeilen ist ein Generator teurer als das Problem. |
| **Gar keine zweite Sprachfassung**, alles über eine lokale Schnittstelle | Ist für `Fundstelle` und `Ausweis` bereits der Zustand und bleibt es. Als **generelle** Regel abgelehnt: `DienstZustand`, `Anzeigeform` und `Sichtbarkeit` müssen zur Laufzeit bei jeder Fensteränderung entscheiden — ein Prozessaufruf je Größenänderung ist die falsche Bauform. |
| **Doppelung hinnehmen, die KI zieht nach** | Beantwortet die Aufwandsfrage statt der Ergebnisfrage (Hausregel „zweimal ist die Grenze"). Das Schreiben war nie teuer; teuer ist, dass zwei Fassungen **unbemerkt** auseinanderlaufen. Belegt: `L-473ba2` (sechs von acht Fehlern in der Naht bei 686 grünen Tests), `L-5431a3` (zwei gleichnamige Klassen, monatelang die tote gepflegt). Diese Kosten sinken nicht, wenn Code billiger wird — sie steigen. |

## Was das kostet

- **Die Formel bleibt zweimal.** Ein Datenbankschema trägt Felder, keine Formeln.
  `Anzeigeform.swift` gegen `lesbarkeit.py` ist von dieser Entscheidung **nicht** gedeckt;
  dort bleibt `lesbarkeit.json` die gemeinsame Quelle. Tragbar, solange die Formel kurz
  und stabil ist — und ausdrücklich neu zu bewerten, wenn sie wächst.
- **Prozessgrenzen bleiben.** Wo Swift Python ruft, kostet das Startreihenfolge und
  Latenz, und die App ist ohne den Dienst tot. `DienstZustand.swift` und
  `DienstAufsicht.swift` existieren genau deshalb.
- **Schemazwang trifft jeden Schreibpfad, nicht nur den bequemen.** Belegt: `L-73dc51` —
  ein nachträglicher Trigger auf `knowledge_nodes` ließ 76 von 448 Tests aus 11 Dateien
  fallen, dazu zwei Produktionsskripte und zwei Messläufer, alle mit rohem SQL. Vor jedem
  neuen Zwang gilt: `grep -rn "INSERT INTO <tabelle>"` über das ganze Repo, erst danach
  der Trigger.
- **Ein Zwang, der zu streng ist, blockiert fremde Sitzungen.** Am selben Tag gemessen:
  der `norm_art`-Trigger weist deutsche Pluralformen ab. Ein Schema ist Durchsetzung —
  Durchsetzung ohne Negativprobe sperrt Arbeit aus, statt sie zu ordnen.

## Woran sich Erfolg misst

- Ein Feld in `kern/fundstelle.py` umbenennen lässt den Swift-Test fallen. Vorher fiel
  nichts.
- Keine Sprachfassung außer Python enthält eine Feldliste oder Bedingung, die nicht aus
  einer gemeinsamen Quelle stammt oder gegen sie geprüft wird.
- Jeder neue Schemazwang bringt seine Gegenprobe mit: ein gültiger Fall, der weiterhin
  durchgeht, benannt und getestet — nicht nur der ungültige, der fällt.
