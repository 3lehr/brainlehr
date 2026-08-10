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

## §5 Nachtrag nach der Umsetzung — 2026-08-10T11:58:32+0200

Der Plan sah **19** Umzuege vor. Gewandert sind **107**, in drei Wellen. Die
Begruendungen standen bis zu diesem Nachtrag nur in Commit-Nachrichten.

| Welle | Commit | Zeit | Dateien | Ziel |
|---|---|---|---|---|
| 1 | `8d37634` | 07:55 | 20 | `migrationen/` |
| 2 | `35cbc7c` | 08:39 | 19 | `berichte/` 5, `messungen/` 7, `pflege/` 7 |
| 3 | `162d1ec` | 10:06 | 68 | `kern/` 50, `melder/` 9, `messungen/` 5, `pflege/` 4 |

Welle 2 ist der hier geplante Umfang. Welle 1 lief ihm voraus (Migrationen und
Einmallaeufe — Vergangenheit, fuer eine Neuanlage nicht noetig, aber nicht
loeschbar, weil sie belegen, **wann** welche Regel dazukam). Welle 1 zaehlte
20 Umbenennungen; die Commit-Nachricht spricht von 15 — die 15 ist die
korrigierte Zahl der *nie importierten* Dateien, nicht die der bewegten.

### Was anders kam als geplant — und warum

**§2 wurde in derselben Sitzung umgeworfen: die 9 verdrahteten und die 49
importierten sind doch gewandert.** Grund war nicht neue Zuversicht, sondern ein
neuer Zweck: das weitergebbare Repo `_brainlehr_open` trug bereits die Ordnung
`kern/ melder/ messungen/ pflege/`. Zwei Baeume mit gleichem Inhalt und
verschiedener Ablage kosten bei jedem Abgleich mehr als der Umzug einmal kostet.
Der in §2 geforderte *eigene Arbeitsgang mit eigener Abnahme* wurde dabei
tatsaechlich gefahren, nicht uebersprungen: Pfade in `~/.claude/settings.json`
automatisch aus dem tatsaechlichen Fundort nachgezogen, JSON vor dem Schreiben
geparst, Sicherung unter `settings.json.vor-umzug`, Abnahme durch
`doctor.probe_tote_pfade`.

**Der Ersetzungsausdruck brauchte `(?<![_\w])`.** Ohne diesen Schutz traf er im
offenen Repo das fuehrende `_` von `_Path` im Pfadblock selbst und machte 173
Dateien unladbar. Das ist der Beleg dafuer, dass die Sorge aus §2 berechtigt war
— sie war nur loesbar, nicht bindend.

**Die Messung in §0 war blind.** „19 ohne jede Fremdnennung" waren tatsaechlich
15: `migrate_relations`, `migrate_knowledge`, `migrate_normfelder` und
`fix_namensraum_knoten` werden sehr wohl importiert. Der Testlauf fand das in
Sekunden, der Regex nicht — ein Negativbefund, der ohne Gegenprobe nichts wert
war.

**Zwei Fehlgriffe unterwegs** (festgehalten als `L-6903d2`): der `sys.path`-Shim
landete erst **vor** `from __future__ import annotations` — das ist ein
SyntaxError, keine Geschmacksfrage — und die Reparatur an Ort und Stelle
verdoppelte eine Zeile. Richtig war: `git checkout` auf den Ausgangsstand, dann
einmal sauber einsetzen, mit `compile()` als Schreibbedingung.

### Der Preis, der wirklich bezahlt wurde

`kanten_aus_bedeutung.py`, `kanten_aus_lehren.py` und `hebb_kanten.py` sind
trotz §0 nach `kern/` gewandert. Der dort benannte Preis ist eingetreten und
heute nachgemessen: `knowledge_relations.source` nennt weiterhin 5814 + 43 + 10
= **5867 Mal den blossen Dateinamen ohne Ordner**, und Herkunftsfelder sind per
Trigger unveraenderlich — korrigieren laesst sich das nicht.

Entschaerft, nicht geheilt: jeder der drei Namen kommt im Baum genau **einmal**
vor (gemessen 2026-08-10T11:55). Die Herkunft bleibt damit aufloesbar, solange
niemand einen zweiten `hebb_kanten.py` anlegt. **Wer das tut, macht 5867
Herkunftsangaben endgueltig mehrdeutig.**

### §4 gegengerechnet

1. **Selbsttests.** Fuer Welle 2 rot-vor-gruen belegt: vorher 10 gruen / 7 rot,
   nachher 12 gruen / 5 rot; die 5 rot gebliebenen tragen denselben Fehlertext
   wie vorher. Zwei waren echte Umzugsfehler (`koederwerte.txt`, `schema.sql` im
   Unterordner statt in der Wurzel) und sind behoben; zwei Dateien wurden durch
   den Umzug gruen, weil sie ihre Wurzel schon vorher eine Ebene zu hoch
   ableiteten. Fuer Welle 3 liegt **keine** gleichwertige Selbsttest-Gegenrechnung
   vor — dort wurde gegen die Testsuite abgenommen.
2. **`doctor`.** Erfuellt: 40 Pfade geprueft, 0 tot (2026-08-10T11:56).
3. **Testsuite.** Vorzustand 762 gruen / 8 rot / 6 Fehler. Nach den drei Wellen
   764 gruen / 9 rot / 6 Fehler. Der eine Neuzugang war `test_doctor`, und er
   hatte recht — allerdings ueber sich selbst: der Test schrieb `WURZEL/doctor.py`
   fest, waehrend `doctor.py` nach `kern/` gewandert war. Ein Umzugsnachzuegler,
   der 1,5 Stunden rot stand. Heute behoben, indem der Test den **Fundort des
   Moduls** benutzt statt einer festen Wurzel — damit ueberlebt er den naechsten
   Umzug. Damit wieder 8 rot / 6 Fehler, gleichauf mit dem Vorzustand.
4. **`ls *.py | wc -l`.** Ziel war 88 → 69. Tatsaechlich **88 → 3**: uebrig
   bleiben die drei Einstiegspunkte `brainlehr.py`, `knowledge_mcp_server.py`
   und `schnellstart.py`.

### Was daraus zu lernen ist

Ein Plan, der eine Grenze mit „das ist ein eigener Arbeitsgang" zieht, ist nicht
widerlegt, wenn dieser Arbeitsgang noch am selben Tag gefahren wird — er hat
seinen Zweck erfuellt, naemlich die Abnahme zu erzwingen, die sonst gefehlt
haette. Verletzt waere er erst, wenn die 9 verdrahteten Melder ohne
Pfadnachzug und ohne `doctor`-Probe umgezogen worden waeren: ihr Ausfall ist
lautlos und von „nichts zu melden" nicht zu unterscheiden.
