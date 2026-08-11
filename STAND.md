# STAND brainlehr — 2026-08-11T12:40:00+0200

Zuletzt: erster S18-Vorschlag eingeloest (Commit a816d2d). `vorschlag.py`
nannte `L-a69129` als faelligsten Pruefstein; er ist jetzt gebaut — `rolle`
ist Pflichtparameter von `schreiblauf._call_with_retry`, ohne Vorgabewert
(der Vorgabewert war das zweite Vorkommen der Lehre). Rolle `beantworten`
auf dem lokalen Ollama-Weg wird abgewiesen. Vier Antwortlaeufe sind damit
GESPERRT statt still falsch zu messen: `bedeckung.py`, `wissensnutzen.py`,
`wissensnutzen_blind.py`, `pruefkorpus_v3.py::answer`. Sie gehoeren in den
Hauptfaden (Subagent mit Betriebsmodell) — ein Python-Skript kann keinen
Haiku-Subagenten starten. Das ist der naechste Bauschritt, kein Nebenschaden.

Offen (Messung ersetzt die alte Zahl): 15 von 82 menschlichen Nachrichten
(18,3 %) erreichten den `UserPromptSubmit`-Haltepunkt nicht, obwohl das Modell
sie empfing und beantwortete — Knoten `/brainlehr/18-prozent-der-nachrichten-
erreichen`, gemessen 2026-08-11 in Sitzung c5d06d04. Damit ist die alte
Erklaerung (waehrend laufender Arbeit eingereiht) widerlegt: es ist kein
Zustellungsproblem und kein Warteschlangeneffekt, sondern Ausfall des
Haltepunkts ohne erkennbares Muster. Betroffen sind genau die Nachrichten,
aus denen nie eine Lehre entstehen kann. Folge fuer die Arbeitsweise: die
gezielte Suche darf nicht am Haken haengen.

Ebenfalls offen aus dem 2026-08-11-Checkpoint (`/brainlehr/claude-checkpoint-
2026-08-11-mittag`): die Zweckprojektion prueft die Spalte `freigabe` nicht —
ein als `gesperrt` markierter Eintrag kann ueber sie ausgeliefert werden.
Die Freigabe-Achse ist angewandt (alle Knoten auf `intern`), die Projektion
haelt sie noch nicht.

Zwei Melder, die jede Sitzung anschlagen und Bestandsarbeit sind, keine
Fehler: 17 Ergebnisdateien ohne Gegenprobe-Vermerk, 30 ohne Rastervermerk.
S1c ist gebaut, der Altbestand nicht nachgezogen. Entweder nachtragen oder
einen Stichtag ziehen ("vor S1c = ohne Vermerk, kein Befund").

Wartet auf: `~/.claude.json` -> `mcpServers.knowledge.env` (actor, tippt der
Betreiber selbst) · Papernetz-Umfang · sechs Knoten Rang 4/6.

Fallen: ein Protokoll taugt erst als Nenner, seit es den Negativfall schreibt
(`L-cb3f28`); eine Widerlegung erst, wenn ihr Einzelfall im Nenner steht
(`L-bd4e5f`, Verfahren dagegen `L-1c9dc8`). Und: der Arbeitsbaum hat KEINE
eigene `knowledge.db` — wer hier eine anlegt, misst gegen eine leere
Datenbank. Die echte liegt in `/Volumes/daten/Begod2026/brainlehr/`,
`BEGOD_KNOWLEDGE_DB` sticht sie (`haken/ort.py`).

Uebergabe wird seit hub-Commit 4dea71518 beim Sitzungsstart genannt.
