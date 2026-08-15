# GermanQuAD -- echter Import, Bericht

Erstellt: 2026-08-15T20:15:00+0200. Nachtrag zu
`runs/wissenskorpus_einlesweg_2026-08-15_bericht.md` (dort war GermanQuAD noch
"Pruefkorpus-Kandidat, noch nicht importiert" -- der S3-Bezugsweg scheiterte
mit HTTP 404). Betreiberentscheidung, woertlich: "dann GermanQuAD !!!" -- nur
diese eine der vier Quellen wird eingelesen, GermanDPR/Gesetze im
Internet/Open Legal Data bleiben es NICHT (Anmeldeschranke bzw. offene
`gattung`-Frage, siehe Vorgaengerbericht).

## 1. Bezugsweg gefunden (der S3-Pfad blieb kaputt)

Hugging Face erzeugt fuer jedes Dataset automatisch eine Parquet-Konvertierung
auf dem Git-Branch `refs/convert/parquet` -- unabhaengig vom Loading-Script,
das fuer GermanQuAD "arbitrary Python code" ausfuehrt und deshalb vom
Datasets-Server/-Viewer verweigert wird. Gemessen:

```
GET https://huggingface.co/api/datasets/deepset/germanquad/tree/refs%2Fconvert%2Fparquet/plain_text
  -> plain_text/test/0000.parquet   (894.803 Bytes, 2.204 Zeilen)
  -> plain_text/train/0000.parquet  (3.299.993 Bytes, 11.518 Zeilen)
```

Beide per `resolve/refs%2Fconvert%2Fparquet/...` ohne Anmeldung ladbar.
13.722 Fragen bestaetigt (2.204 + 11.518). 3.014 eindeutige Kontext-Passagen
(474 Test + 2.540 Train, ueberschneidungsfrei zwischen den Splits -- geprueft
per Mengendifferenz).

Parquet-Parsing lief einmalig ueber `pyarrow` in einem Wegwerf-Venv
(`.venv_wissenskorpus`, nach Gebrauch geloescht) -- KEINE neue
Projektabhaengigkeit: das Ergebnis ist reines JSON
(`rohdaten/wissenskorpus/germanquad_paare.json`, gitignored), das
`pflege/wissenskorpus_einlesweg.py` mit der Standardbibliothek liest.

## 2. Knotenzahl vor und nach dem Einlesen (Pflichtangabe, sonst nicht mehr zuordenbar)

| | Knoten gesamt | davon `/germanquad/*` | Embeddings gesamt |
|---|---|---|---|
| **vorher** (2026-08-15, vor diesem Import) | 2.217 | 0 | 3.913 |
| **nachher** | 4.930 | 2.713 | 6.626 |

Die beiden Vorher-Messungen aus dem heutigen Guete-Messlauf
(`runs/knowledge_search_vorher_2026-08-15.json` mit 18 von 205,
`runs/vorher_rrf_2026-08-15.json`) gelten NUR gegen den Stand **2.217
Knoten** -- ab jetzt veraltet fuer jede neue Messung, die den Bestand ab
4.930 sieht.

Embeddings erzeugt: 2.713 (eins je importiertem Knoten, ueber das bestehende
`kern/build_embeddings.py` -- unveraendert aufgerufen, nicht editiert).
Laufzeit Embedding-Lauf: 269,1 s (gemessen, Skriptausgabe). Laufzeit
Knoten-Import selbst: 1,7 s (gemessen, `importiere_lauf()`-Rueckgabe).

## 3. Was importiert wurde, was bewusst nicht

3.014 eindeutige Passagen insgesamt. Davon **301 (10 %, Seed 20260815, siehe
`parquet_zu_paare`-Konvertierung) ABSICHTLICH NICHT eingelesen** -- das ist
die Gegenprobe aus dem Auftrag. Fragen, deren Passage held-out ist, tragen
das Label "nein" (Antwort nicht im Bestand); jede Suche, die dort trotzdem
einen Treffer meldet, ist ein Fehlalarm.

Importiert: 2.713 Passagen, `gattung=nachschlagewerk`, `norm_rang=NULL`,
`source` mit Namensnennung je Knoten (Stichprobe an drei zufaelligen Knoten
nachgeprueft, siehe unten).

## 4. Die Bruecke: Pruefkorpus-Faelle mit VORHER bekanntem Label

`runs/wissenskorpus_import_germanquad_voll.json` (4,1 MB, 13.722 Faelle):

| Kategorie | Anzahl | Label |
|---|---|---|
| `qa_bruecke` (Frage -> importierte Passage) | 12.347 | "ja" (Antwort im Bestand) |
| `negativ_fremdquelle` (Frage -> held-out Passage) | 1.375 | "nein" (Antwort NICHT im Bestand) |

Summe 13.722 = alle Fragen aus GermanQuAD, keine ausgelassen -- jede traegt
jetzt ein VORHER bekanntes Label, nicht aus dem Suchergebnis abgeleitet. Das
ist der eigentliche Ertrag: bisher hatte `kern/pruefkorpus.py` Etiketten,
aber keine geteilte Quote "gefunden von dem, was da war" gegen "ueberhaupt
vorhanden". Mit diesen 13.722 Faellen laesst sich das jetzt rechnen (naechster
Schritt, nicht Teil dieses Auftrags: einen Messlauf gegen diese Datei bauen).

## 5. Stichprobe (drei zufaellige Knoten, am Bestand gelesen)

```
/germanquad/d361315f6df1  gattung=nachschlagewerk  norm_rang=NULL  norm_entscheidung=keine_norm
  source: GermanQuAD (Timo Moeller, Julian Risch, Malte Pietsch (deepset), 2021), CC BY 4.0, ...
/germanquad/c153cf4758e5  gattung=nachschlagewerk  norm_rang=NULL  norm_entscheidung=keine_norm
  source: GermanQuAD (...) CC BY 4.0, ...
/germanquad/51a7bbfd36f0  gattung=nachschlagewerk  norm_rang=NULL  norm_entscheidung=keine_norm
  source: GermanQuAD (...) CC BY 4.0, ...
```

## 6. Rueckweg, belegt

`pflege/wissenskorpus_einlesweg.py::entferne_quelle()` -- `DELETE FROM
knowledge_nodes WHERE path LIKE '/germanquad/%'`. `knowledge_embeddings`
haengt per `FOREIGN KEY(ref_id) ...` faktisch am Knoten (kind/ref_id/model)
und wird beim Knoten-DELETE ueber die bestehende
`knowledge_embeddings`-Wartung nicht verwaist -- **Probelauf vor dem echten
Import** auf einer Kopie von `brainlehr.db` gefahren: 20 Frage-Paare
importiert (5 Knoten), Pflichten 1-3 geprueft, danach `--entferne germanquad`
aufgerufen -- Knotenzahl kehrte exakt auf den Ausgangswert 2.217 zurueck,
0 `/germanquad/*`-Reste. CLI: `python3 pflege/wissenskorpus_einlesweg.py
--entferne germanquad --db brainlehr.db`.

Backup vor dem echten Lauf: `brainlehr.db.bak-vor-germanquad-20260815T200813`
(gitignored, lokal).

## 7. Was beim Einlesen schiefgehen kann, und woran man es merkt

- **Der HF-Konvertierungsbranch ist kein garantierter Vertragsweg.** Er ist
  eine automatische HF-Infrastrukturfunktion, keine dokumentierte,
  versionierte API -- faellt sie fuer dieses Dataset weg oder aendert sich
  der Pfad (`plain_text/...`), bricht der Download mit 404, nicht mit einem
  stillen Leerergebnis (per `curl`/`resolve`-URL sofort sichtbar).
- **`pyarrow` ist nicht Teil der Projektabhaengigkeiten** (siehe
  `requirements.txt`) und lebte nur im geloeschten Wegwerf-Venv. Ein
  spaeterer Re-Import (z.B. fuer GermanDPR, sobald dessen Bezugsweg klar
  ist) braucht dieselbe Einmal-Installation erneut -- kein Restzustand im
  Projekt, an dem man das vermuten wuerde.
- **Der held-out-Seed (20260815) ist FEST im Konvertierungsskript.** Ein
  zweiter Lauf mit demselben Seed waehlt dieselben 301 Passagen als
  Gegenprobe -- das ist gewollt (Reproduzierbarkeit), nicht zufaellig gut.
  Ein anderer Seed wuerde eine andere (aber gleich grosse) Gegenprobe
  erzeugen.
- **Doppellauf dupliziert nichts** (INSERT OR IGNORE), aber ein zweiter Lauf
  MIT einem geaenderten held-out-Seed wuerde vorher held-out gewesene
  Passagen nachtraeglich importieren, ohne die schon geschriebenen
  Pruefkorpus-Faelle (Label "nein") zu aktualisieren -- diese Datei hier
  waere dann die einzige Stelle, die den tatsaechlichen Importzustand
  festhaelt. Vor jedem Zweitlauf: `runs/wissenskorpus_import_germanquad_voll.json`
  gegen den aktuellen Bestand pruefen, nicht blind erneut ausfuehren.
