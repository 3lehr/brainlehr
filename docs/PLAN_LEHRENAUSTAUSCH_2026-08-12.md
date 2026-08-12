# Plan: Austausch von Lehren und Wissensknoten (S18-Folge)

2026-08-12T11:32:00+0200. Anschluss an `kern/regelpaket.py` (Commit 7013c04,
Regelaustausch). Auftrag: dieselbe Idee auf `lessons_learned` und
`knowledge_nodes` (Fakten/Domänenwissen, nicht nur CLAUDE.md-Regeln)
ausweiten, "der NASA-Katalog für brainlehr, geordnet nach Domänen"
(Betreiberzitat).

## Gemessener Ist-Stand

- `lessons_learned`: 808 Zeilen. `freigabe`: **alle 808 = 'intern'**, 0 =
  'offen'. Das ist die entscheidende Zahl: der Speicher hat mit S17 bereits
  eine Achse "darf das nach draußen" gebaut (`schema.sql:584-611`,
  `SPRINTS.md:42` nennt das fehlende Stück ausdrücklich: "Export-Protokoll
  ... keine Fundstelle dazu im Bestand") — sie steht nur noch nirgends auf
  'offen'. Der Mechanismus für Frage 1 existiert schon, er ist nur leer.
- Von den 808 tragen **307 einen Datei-/Pfadbezug** in
  description/root_cause/resolution/prevention (Regex auf
  `/Volumes/daten|/Users/|<ordner>/|\.py\b|\.sql\b|brainlehr\.db|/apps/`),
  **501 nicht**. Das ist eine Näherung (ein Text kann lokal wahr sein, ohne
  einen Pfad zu nennen), aber eine gemessene, keine geschätzte.
- `knowledge_nodes`: `gattung='arbeitsbestand'` 509, `nachschlagewerk` 1641
  (davon 1638 NASA-LLIS, Präzedenzfall). `freigabe='offen'` 1743,
  `'intern'` 407 — hier ist die Achse schon in Benutzung.
- Domänen-Taxonomie existiert bereits zweimal im Bestand, unterschiedlich
  granular: `knowledge_nodes.path`-Wurzelsegmente für Wissensknoten
  (`methodik` 104, `apps` 76, `shared` 48, `ops` 41, `arch` 16, `testing`
  10, `tools` 8, `agents` 6, ...) und `lessons_learned.projects[]` für
  Lehren (`fahrtenbuch` 274, `systemweit` 234, `openlehr` 227, `hub` 204,
  `brainlehr` 118, `shared` 68, ...). Beide werden übernommen, keine neue
  Kategorienliste erfunden (anders als `regelpaket.py`, das mangels
  vorhandener Taxonomie 6 Kategorien von Hand bilden musste — hier ist eine
  da).

## Die drei Fragen

**1. Was wandert.** Gate ist `freigabe='offen'` — die vorhandene Achse, kein
neues Feld. Zusätzlich, weil `freigabe='offen'` allein nichts über
*lokale Beweisbarkeit* aussagt: der Pfad-Regex-Befund oben wird pro Zeile ins
Paket geschrieben (`beleg_lokal: true/false`), NICHT als Ausschlusskriterium.
Begründung gegen Ausschluss: eine Lehre mit lokalem Beleg kann trotzdem ein
übertragbares Muster beschreiben (root_cause/prevention oft allgemein, auch
wenn description einen Pfad nennt) — Ausschluss würfe das Muster mit dem
Beweis weg. Also: **wandert ausdrücklich als unbelegt markiert**, nie
stillschweigend geglättet.

**2. Wie die Herkunft mitreist.** Nichts Neues bauen — vorhanden:
`melder/foederation.py::kennung()` liefert die Instanzkennung (16 Hex-Zeichen,
in `knowledge_config`), `knowledge_nodes.gattung='nachschlagewerk'` ist der
Präzedenzfall für Fremdbestand (NASA-LLIS, `kern/fremdimport.py`). Für
`lessons_learned` fehlt ein eigenes Herkunftsfeld (kein `source`, kein
`tags`) — Provenienz reist im vorhandenen `projects[]`-Array als
Sonder-Einträge (`fremd:<instanz>`, ggf. `beleg:nur-lokal`), plus
`node_path`, das auf einen pro Instanz einmalig angelegten
`/fremdwissen/<instanz>`-Wurzelknoten zeigt (selbst `gattung=nachschlagewerk`,
`source=fremdwissenspaket:<instanz>`). Importierte Zeilen bleiben
`freigabe='intern'` in der Zielinstanz — Import verleiht keine Sichtbarkeit,
das entscheidet dort wieder ein Mensch (gleiches Prinzip wie `norm_rang=NULL`
in `regelpaket.py`: ankommen ist nicht wirken).

**3. Einschleusung — Tür statt Dauerprüfung.** `kern/einschleusung.py` prüft
heute bei der AUSGABE (`entschaerfe_fuer_ausgabe`), nicht beim Schreiben —
bewusst so (Docstring: "kein Blockieren beim Schreiben ... sonst kann eine
geschickte Formulierung das Schreiben fremder, legitimer Einträge
verhindern"). Das gilt für lokale Autoren mit bekannter Urheberschaft. Ein
Importpaket ist etwas anderes: unbekannte Herkunft, wird ohne weitere Prüfung
in Recall-Pfade gespeist, die diese eine Prüfung sonst bei JEDEM Lesen erneut
zahlen müssten. Deshalb **beides**, nicht entweder/oder:
- **Tür (neu, hier gebaut):** `erkenne()` läuft über jedes Textfeld jedes
  Importelements. Ein Fund der Stufe `hart` oder `stark` **verwirft das
  Element** (kein Import, im Bericht genannt) — fail closed, weil die Quelle
  unbekannt ist und ein Nein hier billig, ein Ja teuer ist.
- **Ausgabe (unverändert):** was durchkommt, läuft trotzdem weiter durch
  `entschaerfe_fuer_ausgabe()` bei jedem Recall — Verteidigung in der Tiefe,
  weil `_PATTERNS` "PRINZIPIELL unvollständig" ist (eigener Docstring). Die
  Tür fängt das Grobe einmal billig ab, die Ausgabe bleibt der Fallback
  gegen das, was die Tür nicht kennt.

## Bauform

Eine neue Datei `kern/lehrenpaket.py`, Bauform 1:1 wie `regelpaket.py`
(Export/Import/entfernen/selftest, `INSERT OR IGNORE` für Idempotenz,
`project_id`/Präfix-Schema für restlose Entfernbarkeit). Deckt
`lessons_learned` UND `knowledge_nodes` (arbeitsbestand, nicht Regeln) in
einer Datei ab, weil Gate (`freigabe='offen'`), Tür (`einschleusung.erkenne`)
und Herkunftsmechanik (Instanzkennung, `/fremdwissen`-Wurzel) für beide
Tabellen identisch sind — zwei Dateien wären derselbe Code zweimal.

**Nicht gebaut:** Netzwerktransport (ADR-001 fehlt weiterhin, Austausch
bleibt Datei-zu-Datei wie bei `regelpaket.py`), Durchsetzung der
Vertrauensliste (`foederation.py::obergrenze`) beim Import — das ist eine
Zugriffsfrage für den Zielort der Datei, nicht für dieses Skript, gleiche
Abgrenzung wie beim Regelaustausch. Beide Lücken sind Befund, nicht
Halbbau.

## Reihenfolge

1. `kern/lehrenpaket.py` mit Export (Gate `freigabe='offen'`, Domäne aus
   `projects[]`/`path`-Wurzel, `beleg_lokal`-Flag), Import (Tür zuerst,
   danach Schreiben mit Herkunftsmarkierung), Entfernen, Selbsttest
   (idempotent, Negativfall Einschleusung, Herkunft erkennbar, Gegenprobe
   für unbelegte Lehre).
2. Eintrag in `tests/test_alle_selftests.py` (MODULE-Liste + Zähler 61→62).
3. Suite laufen lassen, Ausgangswert vergleichen (937 passed erwartet plus
   den neuen Selbsttest).

## Woran sich Erfolg misst

- Aus- und Einfuhr gegen ein frisches Schema, zweiter Lauf importiert 0 neu.
- Ein präparierter Angriffstext (`Ignoriere alle vorherigen Anweisungen...`)
  in einem Importelement führt zu Ablehnung dieses EINEN Elements, nicht des
  ganzen Pakets, und wird im Bericht genannt.
- Eine importierte Zeile trägt die Quellinstanz sichtbar (Provenienz nicht
  erratbar, sondern gespeichert).
- Eine Lehre mit `beleg_lokal=true` wird importiert, aber sichtbar markiert
  — nicht stillschweigend gleich behandelt wie eine belegte.
- Volle Suite weiterhin grün auf dem gemessenen Ausgangswert.
