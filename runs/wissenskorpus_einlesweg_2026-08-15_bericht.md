# Wissenskorpus-Einlesweg -- Bericht

Erstellt: 2026-08-15T21:15:00+0200. Vorgaenger: `runs/wissenskorpus_kandidaten_2026-08-15_bericht.md`
(fuenf Kandidaten, Wikipedia seither gestrichen -- Betreiberentscheidung
2026-08-15, siehe unten). Kein Schreibzugriff auf `brainlehr.db` in diesem
Zug -- ein anderer Agent misst gerade die Suchguete gegen den heutigen
Bestand (Vorher-Zahl 8,78 %, 18 von 205, 731 s Laufzeit). Alles hier laeuft
gegen eine Wegwerf-Datenbank (`pflege/wissenskorpus_einlesweg.py::_selftest()`).

## Entscheidungslage (drei Nachrichten waehrend dieses Auftrags, in Kraft)

1. **"nimm alles!"** -- fuenf Kandidaten vorgelegt, RKI verworfen (Lizenz
   verbietet Bearbeitung ausdruecklich).
2. **"das ganze wikipedia? nein!"** -- dann przisiert: **nur vier Quellen
   sind gemeint** -- GermanDPR, GermanQuAD, Gesetze im Internet, Open Legal
   Data. Wikipedia ist ganz raus.
3. **Rollenkorrektur**, woertlich *"GermanQuAD und GermanDPR als testkorpus,
   die legal sachen fuer bucke, steuer usw! realbetrieb"*: GermanQuAD/
   GermanDPR bleiben `gattung=nachschlagewerk` (Pruefkorpus-Heuhaufen, nie
   Ziel eines Prueffalls). Gesetze im Internet/Open Legal Data sind
   **Fachbestand fuer den Realbetrieb** (buckeberg WEG-Recht, openlehr
   Steuer) -- sie sollen gefunden werden, nicht ausgefiltert. Dazu die
   Systemkritik: *"dann haben wir aber ein fehler im unseren system!"* -- ein
   sehr grosser Heuhaufen, der jede Anfrage verschlechtert, ist ein Fehler,
   kein hinzunehmender Nebeneffekt (Ursache gemessen, Knoten `d84b6b64`: die
   Fusionsformel gewichtet den Rang INNERHALB eines Kanals, nicht dessen
   Guete -- ein Agent repariert das GERADE). Menge ist deshalb nicht mehr das
   Hauptkriterium fuer GermanQuAD/GermanDPR; sie bleibt Kriterium fuer
   Gesetze im Internet/Open Legal Data, weil dort die Ratio-Frage weiterhin
   explizit vorgelegt werden soll ("du entscheidest sie NICHT allein").

## 1. Bestand heute, gemessen (nicht die Zahlen aus CLAUDE.md/Gedaechtnis)

```
SELECT COUNT(*) FROM knowledge_nodes WHERE zurueckgezogen=0            -> 2211
  davon gattung='arbeitsbestand'                                       ->  570
  davon gattung='nachschlagewerk'                                      -> 1641
knowledge_embeddings (Vektoren)                                        -> 3911
  dim=1024, Blobgroesse je Vektor gemessen                             -> 4096 Bytes
brainlehr.db, Dateigroesse                                             -> 86.261.760 Bytes (82 MB)
```

**Abweichung zur Betreiber-Referenzzahl 251 "offene eigene Knoten":** eigene
Messung liefert 570 (gattung=arbeitsbestand gesamt) bzw. 277
(gattung=arbeitsbestand UND norm_entscheidung='offen'). Keine der beiden
trifft 251 exakt -- **gemeldet statt stillschweigend uebernommen.** Fuer die
Ratio-Rechnungen unten wird 251 verwendet (Betreiberweisung), mit der
gemessenen Zahl 570 als Gegenprobe in Klammern.

Verhaeltnis eigen:Heuhaufen HEUTE: 251:1641 = **1:6,54** (gemessen: 570:1641
= 1:2,88).

## 2. Embedding-Kosten, real gemessen (nicht dokumentiert uebernommen)

Lokal per Ollama (`bge-m3`, dieselbe Instanz, die `kern/build_embeddings.py`
nutzt) direkt gemessen, Batch wie im Produktivlauf:

| Textart | Batch | ms/Text gemessen | ms/Text dokumentiert (build_embeddings.py-Kommentar) |
|---|---|---|---|
| kurze Frage (~12 Woerter) | 33 | 15,5 | 17,7-18,6 (Batch 32) |
| lange Passage (~90 Woerter) | 11 | 30,7 | -- (nicht separat dokumentiert) |

Beide Messungen liegen in derselben Groessenordnung wie die vorhandene
Dokumentation -- **korroboriert, nicht neu erfunden.**

## 3. Quelle fuer Quelle: Groesse gemessen, Vorschlag, Lizenz, Bezugsweg

### GermanQuAD -- PRUEFKORPUS, "voll" (Betreiberweisung, nicht verhandelbar)

- **Groesse:** 13.722 Fragen (11.518 train + 2.204 test), bestaetigt per
  HF-API-`description`-Feld (`huggingface.co/api/datasets/deepset/germanquad`).
  Passagen (die tatsaechlich zu importierende Einheit, siehe §4): 2.540 +
  474 = **3.014 eindeutige Kontext-Passagen**.
- **Lizenz:** CC BY 4.0, bestaetigt im `tags`-Feld der HF-API
  (`license:cc-by-4.0`) UND im Dataset-Card-Metadatenblock (WebFetch,
  Vormittagsbericht). Namensnennung Pflicht.
- **Bezugsweg BLOCKIERT, gemessen:** Der im HF-Loading-Script (`germanquad.py`)
  hinterlegte Rohdaten-Pfad `https://germanquad.s3.amazonaws.com/GermanQuAD.zip`
  antwortet **HTTP 404**. Der HF-Datasets-Viewer verweigert den Zugriff
  ausdruecklich ("runs arbitrary Python code", Parquet-Konvertierung fehlt).
  **Das ist ein gemessener Befund** -- kein Konto-/Anmeldeversuch unternommen
  (Grenze). Ein echter Import braucht einen anderen Bezugsweg (z.B. `pip
  install datasets` + `datasets.load_dataset`, was diese Umgebung nicht
  hat, oder eine alternative Spiegelquelle).
- **Kosten (Passagen only, Fragen werden nicht importiert, siehe §4):**
  3.014 × 30,7 ms ≈ **92,5 s** (~1,5 Min). Speicher: 3.014 × 4.096 Bytes ≈
  **12,3 MB**.

### GermanDPR -- PRUEFKORPUS, "voll" (Betreiberweisung, nicht verhandelbar)

- **Groesse:** 10.300 Frage-Antwort-Paare (9.275 + 1.025), Lizenz CC BY 4.0
  (`cc-by-4.0` im Dataset-Card-Block).
- **Kontext-Passagen je Frage: NICHT gemessen** -- derselbe Bezugsweg wie
  GermanQuAD ist wahrscheinlich betroffen (nicht einzeln gegengeprueft,
  Zeitbudget). Die im DPR-Papier (Moeller et al. 2021) beschriebene Struktur
  traegt typischerweise 1 positiven + mindestens 1 harten Negativ-Kontext je
  Frage -- **geschaetzt 2 Passagen/Frage als Untergrenze, Unsicherheit hoch
  (Faktor 1-3x), weil nicht an der Quelle nachgezaehlt.**
- **Kosten (geschaetzt, Unsicherheit explizit hoch):** 10.300 × 2 = ~20.600
  Passagen × 30,7 ms ≈ **632 s** (~10,5 Min). Speicher: 20.600 × 4.096 Bytes
  ≈ **84,4 MB**.

**GermanQuAD + GermanDPR zusammen:** Zeit ≈ 725 s (~12 Min), Speicher ≈
96,7 MB. Neue nachschlagewerk-Knoten ≈ 3.014 + 20.600 = **23.614** (Punkt-
schaetzung, DPR-Anteil unsicher).

**Ratio-Wirkung (gemessen/berechnet, NICHT als Grund zum Kuerzen -- Betreiber-
weisung: Menge ist hier kein Kriterium mehr, nur zu berichten):**

| | eigen (Betreiber-Referenz 251) | eigen (gemessen 570) | Heuhaufen | Anteil eigen am Pool |
|---|---|---|---|---|
| heute | 251 | 570 | 1.641 | 13,3 % (25,8 %) |
| nach QuAD+DPR | 251 | 570 | 25.255 | **0,98 %** (2,21 %) |

Der eigene Bestand faellt beim Betreiber-Referenzwert unter 1 % des Gesamt-
pools -- **hier vorgelegt, nicht stillschweigend gekuerzt.** Die Rangfolge-
Reparatur (`d84b6b64`), an der gerade gearbeitet wird, ist der Grund, warum
das nicht automatisch ein Ablehnungsgrund ist.

### Gesetze im Internet -- FACHBESTAND fuer den Realbetrieb, Groesse gemessen

- **"Alles" bedeutet, gemessen:** `gii-toc.xml` erfolgreich geladen
  (1.286.559 Bytes), **6.127 Gesetze/Verordnungen** (Auszaehlung der
  `<link>`-Eintraege) im gesamten konsolidierten Bundesrecht. Das ist die
  Gesetzesebene -- die Paragraphenebene (die fuer einen Pruefkorpus eigent-
  lich passende Einheit, ein Gesetz hat oft dutzende bis hunderte §§) wurde
  **nicht ausgezaehlt** (haette das Laden aller 6.127 Einzel-XML-Dokumente
  verlangt, Zeitbudget). Die tatsaechliche Knotenzahl bei Volleinlesung liegt
  also deutlich UEBER 6.127.
- **Lizenz:** gemeinfrei nach §5 Abs. 1 UrhG (Gesetzestext selbst, kein
  Website-Vermerk -- Impressum/Hinweise-Seiten geprueft, keine explizite
  Lizenzangabe, Gemeinfreiheit folgt aus dem Gesetzesinhalt).
- **Bezugsweg funktioniert, gemessen:** `gii-toc.xml` + XML-Einzeldokumente
  je Gesetz, DTD `/dtd/1.01/gii-norm.dtd`.
- **BLOCKIERT fuer den Realbetrieb-Import, unabhaengig von der Groessenfrage:**
  siehe §5 -- `gattung` kennt keinen Wert fuer "fremder, aber findbarer
  Fachbestand".

### Open Legal Data -- FACHBESTAND fuer den Realbetrieb, Groesse gemessen (korrigiert)

- **"Alles" bedeutet, gemessen (praeziser als der Vormittagsbericht, der
  "100k-1M" schaetzte):** HF-`dataset_info` gelesen -- voller Dump
  `dump-20221018` = **251.038 Entscheidungen**, 12.675.871.374 Bytes (11,8 GB)
  unkomprimiert, 5.606.739.471 Bytes (5,2 GB) Downloadgroesse.
- **Schema-Abweichung zum Vormittagsbericht:** Felder sind `id, slug, court{
  city, id, jurisdiction, level_of_appeal, name, slug, state}, file_number,
  date, created_date, updated_date, type, ecli, content, markdown_content,
  reference_markers` -- **KEIN eigenes "Leitsatz"-Feld**, anders als der
  fruehere Bericht annahm. Kriterium 1 (Fakt mit Kennung) traegt trotzdem
  ueber `ecli`/`file_number`, nur nicht ueber einen separaten Leitsatz.
- **Kleine Stichprobenkonfigurationen vorhanden:** `dump-20221018-1k`
  (1.000 Zeilen, 68.786.169 Bytes -> **~68,8 KB/Entscheidung** im Schnitt)
  und `dump-20221018-10k` (10.000 Zeilen).
- **Downloadversuch BLOCKIERT, gemessen:** Resolve-URL der 1k-Konfiguration
  antwortet **HTTP 401 (Unauthorized)** -- auch fuer die kleine Stichprobe,
  ohne Anmeldeversuch (Grenze: keine Zugangsdaten gesucht/benutzt). Ein
  echter Import braucht einen geklaerten Zugang.
- **Vorschlag (dies ist die Quelle, bei der etwas anderes als "alles"
  vorgeschlagen wird, Betreiberweisung: "du entscheidest sie NICHT
  allein"):** NICHT die vollen 251.038 Entscheidungen. Begruendung, in
  Zahlen: 11,8 GB Rohtext ist zwei Groessenordnungen ueber allem anderen in
  diesem Auftrag (GermanQuAD+GermanDPR zusammen ≈ 97 MB Vektoren); bei
  durchschnittlich 68,8 KB/Entscheidung braeuchte ein Volltext-Embedding
  zwingend Chunking (Ollama-Kontext 2048 Tokens, `bge-m3@ctx2048`, ein Text
  dieser Laenge sprengt das um ein Vielfaches) -- eine Aufgabe, die dieser
  Auftrag nicht geloest hat. **Vorschlag: die vorhandene 1k- oder
  10k-Sample-Konfiguration** (sobald der 401-Zugang geklaert ist), nicht der
  volle Dump. Ratio-Rechnung bei 10.000 Entscheidungen (falls je 1 Knoten,
  ohne Chunking): Heuhaufen +10.000 -> eigener Anteil (Referenz 251) faellt
  von 13,3 % auf 251/(251+11.641) = **2,1 %** -- spuerbar, aber nicht im
  Promillebereich wie bei GermanQuAD+GermanDPR. Bei den vollen 251.038 waere
  der Anteil 251/(251+252.679) = **0,099 ‰** -- das waere die Verduennung,
  vor der die Betreiberweisung ausdruecklich warnt.

## 4. Die Bruecke: Frage-Antwort-Paar -> Pruefkorpus-Fall mit bekanntem Label

Umgesetzt in `pflege/wissenskorpus_einlesweg.py`, belegt in
`tests/test_wissenskorpus_einlesweg.py` (pytest-Wrapper um den Selbsttest
der Datei). Mechanik:

- Nur die **Antwort-Passage** wird als `knowledge_nodes`-Zeile importiert
  (gattung='nachschlagewerk', norm_rang bleibt NULL, source traegt die
  Namensnennung). Die **Frage** wird NICHT importiert -- sie lebt aus-
  schliesslich als Pruefkorpus-Prompt (`qa_zu_pruefkorpus_fall()`), mit
  `target_id` = Pfad der importierten Passage, Label **"ja"** (Antwort im
  Bestand, VORHER bekannt, nicht aus dem Suchergebnis abgeleitet -- genau
  die Anti-Zirkularitaet, die `kern/pruefkorpus.py` fuer den eigenen Bestand
  schon durchsetzt).
- GermanDPR-Hard-Negatives werden EBENFALLS als Knoten importiert (sie
  muessen im Heuhaufen liegen) und erzeugen einen Fall der Kategorie
  `hard_negative`: dieselbe Frage, `target_id` bleibt der richtige Treffer,
  zusaetzlich `distraktor_pfad` -- ein Treffer auf den Distraktor statt auf
  `target_id` ist ein Fehlalarm, kein Erfolg.
- `negativfall()` bleibt fuer Themen ohne jeden Bestandsbezug (Label
  "nein") -- Gegenstueck, keine Aenderung an `kern/pruefkorpus.py` selbst
  (das Skript ist laut Grenzen nur lesend anzufassen).

**Zahl (aus der Stichprobe im Selbsttest, 2 Paare -- die Rechnung skaliert
linear mit echten Daten sobald der Bezugsweg geklaert ist):** 2 Frage-
Antwort-Paare -> 3 importierte Passagen-Knoten (1 Antwort ohne Hard-Negative,
1 Antwort + 1 Hard-Negative) -> 2 Pruefkorpus-Faelle, davon 1×
`qa_bruecke` (Label ja, kein Distraktor) und 1× `hard_negative` (Label ja,
Distraktor-Pfad zeigt auf einen tatsaechlich im Bestand liegenden Knoten --
im Test nachgeprueft, nicht nur behauptet). Hochgerechnet auf volle
GermanQuAD+GermanDPR-Groesse (sobald ladbar): **13.722 + 10.300 = 24.022
Pruefkorpus-Faelle mit VORHER bekanntem Label "ja"**, ein Bruchteil davon
(GermanDPR-Anteil mit Hard-Negative) zusaetzlich mit Distraktor.

## 5. Befund, der ueber die Groessenfrage hinausgeht: `gattung` hat nur zwei Werte

Gemessen (nicht vermutet): `gattung` ist per DB-Trigger
(`knowledge_nodes_gattung_check_bi`/`_bu`, `schema.sql`) auf genau zwei Werte
begrenzt -- `arbeitsbestand`, `nachschlagewerk`. `nachschlagewerk` wird an
DREI Stellen im echten Suchpfad aus jedem Abruf gefiltert
(`SQL_ARBEITSBESTAND_NUR` aus `kern/gattung_filter.py`, verwendet in
`haken/knowledge_recall_hook.py`, `haken/suchpfad_abruf.py`,
`haken/mehrstufiger_abruf.py`).

Fuer **Gesetze im Internet/Open Legal Data als Fachbestand** (Betreiber-
korrektur: sollen gefunden werden) ist BEIDES falsch: `nachschlagewerk`
filtert sie aus jedem Abruf (genau das Gegenteil des Zwecks), `arbeitsbestand`
behauptet eigenes Wissen dieses Hauses, was Gesetzestexte/Gerichtsent-
scheidungen nicht sind.

Ein dritter Wert braucht eine Aenderung an `schema.sql` (Trigger-Whitelist)
UND an den drei `haken/`-Lesestellen -- **beide Dateiarten sind in diesem
Auftrag tabu** (`schema.sql` heute von einem anderen Agenten geaendert,
`haken/` gerade in Arbeit an der Rangfolge-Reparatur `d84b6b64` -- exakt die
Stelle anzufassen waere die Kollision, vor der die Grenzen warnen).

**Belegt statt behauptet** (`pflege/wissenskorpus_einlesweg.py::_selftest()`,
Abschnitt "Fachbestand-Blocker"): ein Importversuch mit einem erfundenen
gattung-Wert `'fremdbestand'` wird vom DB-Trigger abgelehnt. **Nebenbefund
beim selben Testlauf:** ein zweiter, unabhaengiger Trigger
(`knowledge_nodes_normrang_herkunft_bi`, Knoten `dd367fd1`) verlangt
zusaetzlich `norm_art`, sobald `source` ein Gesetz/eine Verordnung nennt --
ein naiver Import von Gesetzestexten stoesst also auf **mindestens zwei**
unabhaengige Schema-Huerden, nicht nur die gattung-Frage.

**Empfehlung** (keine Umsetzung -- ausserhalb der Grenzen dieses Auftrags):
ein dritter gattung-Wert (Arbeitstitel `fremdbestand`: fremde Herkunft,
soll gefunden werden, ist kein eigenes Wissen) und eine Anpassung der drei
`haken/`-Filterstellen von "nachschlagewerk ausschliessen" auf
"nachschlagewerk UND arbeitsbestand-fremd-noch-nicht-entschieden
einschliessen" -- am besten VON demselben Agenten, der gerade an der
Fusionsformel arbeitet, weil beides denselben Code beruehrt.

## 6. Was beim Einlesen schiefgehen kann, und woran man es merkt

- **Bezugsweg fehlt:** GermanQuAD/GermanDPR sind ueber den dokumentierten
  S3-Pfad nicht ladbar (404, gemessen). Merkbar an: Importlauf bricht vor
  dem ersten Knoten ab, keine stillen Platzhalter -- `_selftest()` demons-
  triert die Mechanik nur an handschriftlichen, laengen-realistischen
  Platzhaltertexten (im Code klar so benannt), nicht an echten Datensatz-
  inhalten.
- **DPR-Kontextanzahl unsicher:** die Kostenschaetzung fuer GermanDPR
  (Faktor 1-3x Unsicherheit) kann bei echtem Import deutlich abweichen.
  Merkbar an: `importiere_qa_stichprobe()`-Ruckgabewert
  `knoten_importiert` weicht stark von der Vorabschaetzung ab -- das ist
  das Signal, die Kostenrechnung mit echten Zahlen zu wiederholen, BEVOR
  der volle Lauf gegen die Produktivdatenbank startet.
- **gattung-Blocker fuer Fachbestand:** ein Importversuch von Gesetze im
  Internet/Open Legal Data OHNE vorherige Schema-Entscheidung schlaegt am
  DB-Trigger fehl (belegt, siehe §5) -- das ist der GEWUENSCHTE Fehlschlag,
  kein Bug. Ein Workaround, der `gattung='arbeitsbestand'` setzt, um den
  Trigger zu umgehen, waere die Fehlerklasse `L-051d71` (Schranke mit ihrer
  Nebenwirkung statt ihrem Zweck begruendet) und ist hier ausdruecklich
  NICHT getan worden.
- **Open Legal Data 401:** ein spaeterer Lauf, der diesen Fehler einfach
  wiederholt (statt den Zugang zu klaeren), verschwendet Zeit still -- die
  Fehlermeldung selbst nennt "Unauthorized", nicht "nicht gefunden";
  verwechselbar, wenn nur der Exit-Code geprueft wird statt der Text.
- **Ratio-Verwaesserung bei GermanQuAD+GermanDPR:** eigener Anteil faellt
  auf unter 1 % (§3). Solange die Rangfolge-Reparatur (`d84b6b64`) nicht
  abgeschlossen ist, kann das die Abrufguete-Messung des parallel laufenden
  Agenten verzerren, falls beide Aenderungen zusammentreffen -- ein Grund
  mehr, den Import erst nach dessen Abschluss und mit ausdruecklicher
  Freigabe zu starten (Auftragsgrenze: kein Schreibzugriff in diesem Zug).

## 7. Belegdateien

- `pflege/wissenskorpus_einlesweg.py` -- Einlesweg + Bruecke, `--selftest`
  gruen (rot-vor-gruen belegt im Selbsttest selbst: 0 Knoten vor Import,
  3 danach).
- `tests/test_wissenskorpus_einlesweg.py` -- pytest-Wrapper, `pytest
  tests/test_wissenskorpus_einlesweg.py -q` -> 1 passed.
- `quellen/fremdquellen.json` -- vier neue Eintraege (germanquad, germandpr,
  gesetze-im-internet, open-legal-data), je mit `geprueft_am`/`geprueft_wie`.
- `NOTICE` -- Namensnennung je Quelle ergaenzt.
- `.gitignore` -- `rohdaten/wissenskorpus/` ergaenzt (fuer einen spaeteren
  echten Download, aktuell leer -- kein Download ist in dieser Sitzung
  gelungen).
