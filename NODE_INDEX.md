# Knoten-Index (generiert — nicht von Hand editieren)

Quelle: `shared-knowledge/build_node_index.py`. Knoten: 1980 in 21 Aesten · Lehren: 628 · erzeugt: 2026-08-07T23:10:49+0200

Landkarte, keine Volltexte. Gezielt nachladen: `knowledge_read <path>`, `knowledge_search <begriff>`, `lesson_query <begriff>`.

## Landkarte (Ast: Anzahl Knoten)

- /nasa-llis: 1638
- /methodik: 91
- /apps: 51
- /shared: 43
- /ops: 39
- /brainlehr: 31
- /openlehr: 24
- /arch: 15
- /testing: 9
- /tools: 8
- /frontend: 7
- /agents: 5
- /backend: 4
- /fahrtenbuch: 4
- /lessons: 3
- /begod: 2
- /stadtwerke: 2
- /aka: 1
- /bebetter: 1
- /probe: 1
- /probe2: 1

## Lehren gebuendelt (628 gesamt)

nach Art: antipattern 277, insight 149, error 108, pattern 94
nach Projekt: fahrtenbuch 236, openlehr 205, hub 154, systemweit 74, shared 64, buckeberg 48, wohlair 40, global 39, +22 weitere Projekte (162)

## Juengste 15 Knoten

- 2026-08-07 /brainlehr/drei-orte-fuer-eine-regel-text-findet — Drei Orte fuer eine Regel: Text findet, Code bindet, Mathematik uebersetzt
- 2026-08-07 /brainlehr/warum-der-bedeutungskanal-streut-er — Warum der Bedeutungskanal streut: er trennt Signal von Rauschen, aber nicht die Spitze
- 2026-08-07 /brainlehr/brainlehrs-zugriffsprotokoll-ist — brainlehrs Zugriffsprotokoll ist bereits ein Sicherheits-Ereignisstrom — Sigma passt ohne Umbau
- 2026-08-07 /brainlehr/brainlehr-braucht-ein-eigenes — brainlehr braucht ein eigenes Verzeichnis — Umzug erst bei Ruhe
- 2026-08-07 /brainlehr/der-mehrwert-entsteht-an-der-kante-zur — Der Mehrwert entsteht an der Kante zur Wirklichkeit, nicht zwischen zwei Dokumentsammlungen
- 2026-08-07 /brainlehr/was-der-journalismus-an-formaten-kennt — Was der Journalismus an Formaten kennt und uns fehlt: Unterbrechung, Vorläufigkeit, Korrekturpflicht
- 2026-08-07 /methodik/vier-wissenschaftliche-arbeitsregeln — Vier wissenschaftliche Arbeitsregeln, die uns fehlen — mit Einbauort
- 2026-08-07 /brainlehr/die-rangordnung-braucht-eine-zweite — Die Rangordnung braucht eine zweite Achse: Sein, Sollen, Dürfen
- 2026-08-07 /brainlehr/quellenschutz-und-herkunftsnachweis — Quellenschutz und Herkunftsnachweis ziehen gegeneinander — bisher unbenannt
- 2026-08-07 /brainlehr/kein-vektorindex-solange-der-massstab — Kein Vektorindex, solange der Maßstab gebaut wird — mit Auslöser statt Datum
- 2026-08-07 /tools/ctoc-tokenzahl-fuer-claude-offline — ctoc — Tokenzahl fuer Claude offline schaetzen (rund 4 Prozent Abweichung)
- 2026-08-07 /brainlehr/erster-lueckenlos-belegter-nutzungsfall — Erster lueckenlos belegter Nutzungsfall: Lehre wandert ueber Projekt, Sprache und Technik
- 2026-08-07 /brainlehr/fremder-pruefkorpus-gefunden-1637-nasa — Fremder Pruefkorpus gefunden: 1637 NASA-Lehren, gleiche Bauform wie unsere
- 2026-08-07 /nasa-llis — NASA Lessons Learned Information System (Import)
- 2026-08-07 /nasa-llis/1000 — Space Shuttle Program/Orbiter/Quality Assurance

## Juengste 15 Lehren

- 2026-08-07 [insight] Claude-Code-Harness liefert im SubagentStart/SubagentStop-Hookpayload KEIN Eltern-Feld -- auch nicht bei echt verschachteltem…
- 2026-08-07 [insight] Eskalation einer Lehre zur Regel im Klartext aendert das Verhalten NICHT. Gemessen 2026-08-08 an L-48e414 (Agent stoesst Hintergrundarbeit…
- 2026-08-07 [error] Abruf-Hook (knowledge_recall_hook.py) spielte abgelaufene Wissensknoten (gilt_bis in der Vergangenheit) weiter ein -- nur zurueckgezogene…
- 2026-08-07 [pattern] View-Registry-Migration einer bestehenden dl/Kachel-Zone auf einen Baustein (z.B. kennzahl_kachel) heißt: bestehendes Handmarkup NICHT…
- 2026-08-07 [pattern] L-80e002 behoben: knowledge_trust_score() las recall_log.jsonl (+DB) JE KANDIDAT komplett neu (3 volle Log-Reads pro Aufruf, davon einer…
- 2026-08-07 [insight] openlehr/steuer, dokument_vorschau-Baustein (2026-08-07): Bildschirmwahl per Messung (kleinster Fachlogik-Beruehrpunkt,…
- 2026-08-07 [error] Zwei Kostenaussagen innerhalb einer Stunde behauptet und gemessen widerlegt, beide von mir.
- 2026-08-07 [pattern] aufgaben_zeile-Baustein (openlehr steuer): data-Attribut per dataset.xyzAbc gesetzt, aber per querySelector mit CSS camelCase-Selektor…
- 2026-08-07 [pattern] openlehr jsdom-Bildschirmharness (tests/jsdom/&lt;screen&gt;/harness.js) laedt Skripte per manueller window.eval-Konkatenation, nicht aus…
- 2026-08-07 [error] Die Wissensdatenbank war beschaedigt, und die Beschaedigung lag bereits IM COMMIT. Gefunden 2026-08-07T22:00:00+0200 durch einen Agenten,…
- 2026-08-07 [error] hebb_kanten.py: --db-Kopie-Lauf haette in Live-DB geschrieben (kms.DB_PATH nie gesetzt), zweiter Lauf verlor Wiederholungssignal…
- 2026-08-07 [antipattern] CSS `input:invalid { border-color: var(--danger) }` faerbt jedes leere Pflichtfeld schon vor der ersten Eingabe rot (false positive), nicht…
- 2026-08-07 [antipattern] Eine Umgebungsvariable zum Umlenken des Datenbankpfads existiert, wird aber nur von einem Teil der Skripte geachtet — und erzeugt damit…
- 2026-08-07 [antipattern] Der Erfassungszwang für Wissen greift ausgerechnet bei Mess- und Planungssitzungen nicht. Gemessen 2026-08-07T21:20+0200, Sitzung 32a7545d:…
- 2026-08-07 [pattern] gilt_bis/gilt_ab-Werte in knowledge_nodes sind nicht einheitlich formatiert: der Bestand traegt sowohl volle ISO-Zeitstempel mit Offset…
