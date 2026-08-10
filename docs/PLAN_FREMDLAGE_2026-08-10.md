# Plan: Was ein Fremder sieht — 2026-08-10T16:40:00+0200

Anlass: Vor dem Umschalten des weitergebbaren Repos auf oeffentlich wurde
gemessen, was ein Fremder beim ersten `pytest` bekommt. Nicht 5 rote Tests wie
hier, sondern **20** — und im ersten Anlauf brach die Suite sogar nach 0,62
Sekunden ab, ohne einen einzigen Test zu fahren.

## §0 Gemessener Ist-Stand

Messaufbau: Kopie von `_brainlehr_open` nach `/Volumes/daten/_fremdprobe/`,
also **ausserhalb** des Verbunds, ohne `.git`, ohne Datenbank, aufgesetzt mit
`python3 schnellstart.py` genau nach README.

| Lage | Ergebnis |
|---|---|
| Hauptbaum (hier) | 5 rot / 774 gruen |
| Fremdklon, erster Lauf | **Abbruch beim Einsammeln**, 1 error nach 0,62 s |
| Fremdklon, nach der ersten Weiche | 20 rot / 713 gruen |

Der Abbruch kam von `tests/test_caveman_bulk_minify.py`: sie importiert
`caveman_bulk` aus dem hub, der bei einem Fremden nicht existiert. Die
Schwesterdatei war bereits abgesichert — diese nicht, weil sie einen anderen
Importnamen traegt und das Ersetzungsskript sie stumm uebersprang. Es meldete
das sogar; die Meldung wurde gelesen und nicht verfolgt.

## §1 Die 20 nach Ursache, nicht nach Datei

**A. Brauchen Daten, die ein Fremder nicht hat (9).**
`test_knowledge_search_fold` (7) und `test_lesson_query_fold` (2) suchen nach
Inhalten wie „Existenzgruender" oder „Landesbroschuere Steuertipps". Die stehen
im gewachsenen Bestand, nicht in einer frischen Instanz. Sie pruefen gegen
Betriebsdaten statt gegen eigene Vorrichtungen.

**B. Setzen den Verbund voraus (7).**
`test_startprompt` (4) prueft Dateien und Fehlermeldungen, die im
weitergebbaren Repo fehlen (`START.md` gibt es dort nicht, `recall_log.jsonl`
entsteht erst im Betrieb). `test_pfade_nach_umzug` (1) verlangt ein
`hub/scripts` unter der Verbundwurzel. `test_normbezug_verdrahtung` (1)
braucht DSGVO-Knoten im Bestand. `test_knowledge_recall_hook` (1) ist auch
hier rot.

**C. Messartefakt des Aufbaus (2).**
Die beiden `test_agent_compliance`-Fehler treten auf, weil der Fremdklon auf
DERSELBEN PLATTE liegt wie `/Volumes/daten/Begod2026/hub`. Die Weiche greift
korrekt nur, wenn der Pfad wirklich fehlt. Auf einem fremden Rechner waeren sie
uebersprungen. **Das ist eine Grenze der Messung und wird als solche gefuehrt,
nicht als Befund.**

**D. Zusaetzlich gefunden, nicht in den 20 enthalten:** Der weitergebbare Baum
hinkte dem Hauptbaum hinterher — 22 Dateien wichen ab, darunter `test_doctor.py`
mit einem Fix von heute frueh. Ein Teil der ersten Messung lief also gegen
alte Staende. Abgeglichen am 2026-08-10T16:35 (184 identisch, 22 nachgezogen).

## §2 Was getan wird

1. **Baeume abgleichen** (erledigt) und danach neu messen — sonst jagt jede
   weitere Runde Phantome.
2. **Klasse A** bekommt eine gemeinsame Weiche in `tests/conftest.py`:
   `braucht_bestand()` ueberspringt, wenn die Instanz den Beispielbestand nicht
   traegt, mit der Anleitung `schnellstart.py --bestand` in der Meldung.
   Ausdruecklich KEIN Umbau auf Vorrichtungen: die Tests messen echte
   Abrufguete an echtem Bestand, das ist ihr Zweck. Ein Test, dessen
   Voraussetzung fehlt, ist zu ueberspringen, nicht umzuschreiben.
3. **Klasse B** einzeln: `test_pfade_nach_umzug` portabel machen,
   `test_startprompt` auf Dateien einschraenken, die im jeweiligen Baum
   existieren.
4. **Gegenprobe in BEIDE Richtungen**: nach jeder Aenderung sowohl im
   Hauptbaum (dort muss alles laufen wie bisher) als auch im Fremdklon. Eine
   Weiche, die nur in einer Richtung geprueft ist, verdeckt genauso oft, wie
   sie hilft.

## §3 Was ausdruecklich NICHT getan wird

**Die 5 roten des Hauptbaums bleiben.** Vier davon sind echte Befunde ueber den
hub (applyTo zu breit, knowledge-mcp fehlt in dessen mcp.json,
jesus-guide.agent.md nicht gesperrt, Caveman-Vorgabe ultra statt lite). Sie
gehoeren dort behoben. Der hub traegt gerade 109 uncommittete Dateien auf einem
fremden Zweig — fremde Arbeit wird nicht angefasst.

**Kein Umbau der datenabhaengigen Tests auf synthetische Vorrichtungen.** Preis:
Ein Fremder sieht sie als uebersprungen statt als gruen. Das ist ehrlicher als
ein Test, der etwas anderes misst als vorher und dabei gruen aussieht.

## §4 Woran sich Erfolg messen laesst

1. Fremdklon: `pytest tests/ -q` laeuft durch (kein Abbruch) — bereits erfuellt.
2. Fremdklon: 0 rote Tests. Uebersprungene sind erlaubt und werden gezaehlt.
3. Hauptbaum: unveraendert 5 rot / 774 gruen — keine Weiche darf hier etwas
   stummschalten.
4. `schnellstart.py` im Fremdklon: Rueckgabewert 0 (bereits erfuellt).

## §5 Nachtrag nach der Umsetzung

(wird nach dem Lauf gefuellt)
