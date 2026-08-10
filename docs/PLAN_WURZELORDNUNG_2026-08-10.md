# Plan: Ordnung im Wurzelverzeichnis — 2026-08-10T08:35:00+0200

## §0 Gemessener Ist-Stand (nicht geschaetzt)

88 `.py` liegen flach im Wurzelverzeichnis von brainlehr. Erhoben am
2026-08-10T08:30 mit einer Einmalmessung (Referenzzaehlung je Modul ueber
`~/.claude/settings.json`, `~/.claude.json`, alle `.py` im Baum ohne
`.claude/worktrees/`, sowie `.md`/`.json`/`.jsonl`/`.sh`):

| Klasse | Anzahl | Bruchfolge bei Umzug |
|---|---|---|
| in `~/.claude/settings.json` als absoluter Pfad verdrahtet | 9 | **lautlos** (`2>/dev/null \|\| true`) |
| von anderen Modulen importiert | 49 | laut (`ImportError`) |
| per Zeichenkette in anderen `.py` genannt (Subprozess/Pfad) | 11 | erst zur Laufzeit |
| ohne jede Fremdnennung in `.py` | 19 | nichts |

Die 9 verdrahteten: `build_node_index.py`, `wissensverlauf.py`,
`sichtbarkeit.py`, `normachsen.py`, `pruefer.py`, `rasterblick.py`,
`planbindung.py`, `arbeitsmelder.py` (dazu `knowledge_mcp_server.py` ueber
die MCP-Eintragung in `~/.claude.json`).

**Dateinamen sind hier Herkunft, nicht nur Pfade.** `knowledge_relations.source`
nennt in 5814 Zeilen `kanten_aus_bedeutung.py`, in 43 `kanten_aus_lehren.py`,
in 10 `hebb_kanten.py` — als blossen Dateinamen. Herkunftsfelder sind per
Datenbank-Trigger unveraenderlich. Ein Umzug dieser drei macht 5867
Herkunftsangaben mehrdeutig, ohne dass sie sich korrigieren liessen.

## §1 Was getan wird

Die **19 ohne jede Fremdnennung** wandern in drei Zweckordner. Jede Datei
bekommt den Dreizeiler, den `haken/` und `pruefstand/` schon benutzen:

```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

- `messungen/` — Messlaeufe und Diagnosen: `abnahme.py`, `abrufversagen.py`,
  `ausloeser.py`, `befund_gegen_speicher.py`, `kandidatendiagnose.py`,
  `messlauf_abrufguete_v2.py`, `trichter_gitter.py`
- `pflege/` — Bestandspflege und Betrieb: `dedublierung_lehren.py`,
  `export_offen.py`, `lehren_verdichten.py`, `neuschreibungen.py`,
  `tagkatalog.py`, `umschrift_einspielen.py`, `wiederherstellung.py`
- `berichte/` — Uebersichten und Oberflaeche: `entscheidungen_server.py`,
  `erstverwendung.py`, `nachschlagewerk_suche.py`,
  `tools_vergleich_stapel_vs_einzeln.py`, `vorschlag.py`

Verschoben wird mit `git mv`, damit die Historie je Datei erhalten bleibt.

## §2 Was ausdruecklich NICHT getan wird — samt Preis

**Die 9 verdrahteten bleiben liegen.** Preis: das Wurzelverzeichnis bleibt
unaufgeraeumt. Grund: ihr Umzug verlangt eine Aenderung an
`~/.claude/settings.json` ausserhalb des Repos, und ein falscher Pfad faellt
dort **lautlos** aus — der Haken schluckt den Fehler. Das ist kein Umzug,
das ist ein eigener Arbeitsgang mit eigener Abnahme (`doctor.py`, Probe
„Tote Pfade").

**Die 49 importierten bleiben liegen.** Preis: derselbe. Grund: sie sind
faktisch ein flaches Paket; ein Umzug ohne Paketierung verteilt
`sys.path`-Flickwerk ueber 49 Dateien.

**Die 11 per Zeichenkette genannten bleiben liegen.** Preis: derselbe.
Grund: ihre Aufrufer nennen sie als Text, kein Werkzeug findet das
zuverlaessig — der Bruch zeigt sich erst im Lauf.

**Datierte Dokumente werden nicht umgeschrieben.** `runs/*.md`,
`docs/LAGE_*.md`, `docs/PLAN_*.md` halten fest, was zu ihrem Zeitpunkt galt.
Ein Pfad darin wird nicht nachgezogen; das waere Faelschung eines Protokolls.
Nachgezogen werden nur die lebenden Dokumente: `README.md` und
`docs/RUNBOOK_WIEDERHERSTELLUNG.md`.

## §3 Verworfene Wege

- **Alles verschieben, `sys.path`-Flickwerk ueberall.** Verworfen: 88 Dateien
  mit drei Zeilen Vorspann, und die verdrahteten faellen lautlos aus.
- **Ein echtes Paket (`brainlehr/__init__.py`) bauen.** Verworfen fuer heute:
  aendert jeden Importpfad im Baum und jede Zeile in `settings.json` auf
  einmal — ein Big Bang, gegen die Monolith-Bremse.
- **Gar nichts verschieben, nur dokumentieren.** Verworfen: der Betreiber hat
  Aufraeumen verlangt, und 19 Dateien gehen nachweislich gefahrlos.

## §4 Woran sich Erfolg messen laesst

1. Jede der 19 Dateien laeuft nach dem Umzug mit `--selftest` mindestens so
   gut wie vorher — **vorher gemessen, nicht angenommen** (mehrere standen am
   2026-08-09 schon auf ROT; ein ROT, das vorher ROT war, ist kein Befund).
2. `python3 doctor.py` meldet keine neuen toten Pfade.
3. `python3 -m pytest tests/ -q` unveraendert gegenueber dem Lauf davor.
4. `ls *.py | wc -l` faellt von 88 auf 69.

## §5 Nachtrag nach der Umsetzung

(wird nach dem Lauf gefuellt: was anders kam als geplant, und warum)
