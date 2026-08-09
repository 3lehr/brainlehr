# Selbsttests eingeordnet 2026-08-09T20:37:49+0200

Messauftrag, keine Reparatur. Grundlage: runs/selbsttest_rundlauf_2026-08-09.md
(73 Selbsttests, 52 gruen, 21 rot). Jede der 21 roten Dateien wurde hier erneut
mit `python3 <datei> --selftest` gefahren (macOS-`timeout` existiert nicht,
stattdessen ein Python-Wrapper mit `subprocess.run(..., timeout=N)`) und der
Fehler gegen den umgebenden Code gelesen, nicht nur die Fehlermeldung zitiert.

Kein `git add`, kein `git commit`. `git status --short` am Ende dieser Datei
belegt, dass an den 21 gepruefte Dateien nichts geaendert wurde.

Legende: **A** Waechter spricht (Bestand/Befund hat sich geaendert, Test
korrekt) · **B** einmaliges Skript ohne Gegenwart (Migration bereits erledigt,
Test veraltet, folgenlos) · **C** echter Defekt (Code oder Test kaputt, betrifft
Genutztes) · **?** nicht entscheidbar ohne Bau.

---

## Klasse A — Waechter spricht (2)

### abrufguete.py
```
AssertionError: L-a9ccd0 sollte laut Befund ein Fehlgriff sein, war aber ein Treffer -- Bestand oder Befund hat sich geaendert, neu pruefen
```
Bereits im Auftrag als Beispiel genannt. Der Selbsttest fragt live gegen
`knowledge.db` ab, ob eine konkrete Lesson (L-a9ccd0) fuer eine konkrete Aufgabe
NICHT gefunden wird; sie wird jetzt gefunden. Das ist die gewollte
Funktionsweise des Werkzeugs, kein Codefehler.

### haken/mehrstufiger_abruf.py
```
AssertionError: Voraussetzung der Warnung verletzt: L-606b63 muss bei AUS im Ergebnis sein
```
Gleiches Muster wie abrufguete.py: `_selftest()` oeffnet die echte `knowledge.db`
read-only (`file:{ort.DB}?mode=ro`) und ruft `knowledge_recall_hook.query()`
ueber einen echten, langen Aufgabentext. Die Testvoraussetzung ("L-606b63 wird
bei abgeschaltetem mehrstufigem Abruf gefunden") ist eine Aussage ueber den
heutigen Bestand/Embeddings, keine Aussage ueber den Code. Sie ist jetzt falsch
-- der Bestand hat sich seit dem Schreiben des Tests veraendert.

---

## Klasse B — einmaliges Skript ohne Gegenwart (4)

Alle vier sind additive Ein-Mal-Migrationen aus "Auftrag 2026-08-06"
(`.venv/bin/python shared-knowledge/<datei> --apply` laut eigenem Docstring).
Gegenprobe: `PRAGMA table_info` auf der echten `knowledge.db` zeigt, dass die
Zielspalten aller vier Migrationen LAENGST vorhanden sind (`anlass`,
`quell_hash`, `norm_rang`/`gilt_ab`/`gilt_bis`, `zeilen_hash`/`ketten_hash`).
Die Migration ist erledigt; die Selbsttests pruefen gegen den `schema.sql`-Stand
von damals und sind seither durch spaetere Trigger/Spalten (z.B. die
`norm_entscheidung`-Pflicht, "Auftrag 2026-08-08") ueberholt.

### migrate_anlass.py
```
AssertionError: Anlass-Block an knowledge_nodes nicht wie erwartet gefunden
```
Sucht einen Textblock in `schema.sql`, der die `anlass`-Spalte einfuehrt, mit
einem Muster, das nicht mehr passt (der Block wurde seither ergaenzt/umgebaut,
Zeile 116 traegt die Spalte weiterhin: `anlass TEXT NOT NULL DEFAULT 'unbekannt'`).
Migration ist in der Live-DB laengst vollzogen.

### migrate_normfelder.py
```
AssertionError: Normschicht-Block im schema.sql nicht wie erwartet gefunden
```
Gleiches Muster: `norm_rang`/`gilt_ab`/`gilt_bis` existieren in `schema.sql`
(Zeilen 37-39) und in der Live-DB, nur der Text-Anker des Tests passt nicht mehr
zum heutigen Kommentarblock.

### migrate_quellhash.py
```
AssertionError: Quellhash-Block im schema.sql nicht wie erwartet gefunden
```
`quell_hash TEXT` existiert in `schema.sql` (Zeile 109) und in der Live-DB
(PRAGMA-Abfrage bestaetigt). Gleicher Anker-Drift wie oben.

### migrate_auditkette.py
```
sqlite3.IntegrityError: knowledge_nodes.norm_entscheidung fehlt: beim Anlegen entscheiden, ob dieser Knoten eine Norm ist -- keine_norm (Fakt), norm_befristet (Norm mit Enddatum) oder norm_unbefristet (Norm ohne Ende)
```
`_selftest()` legt testweise einen `knowledge_nodes`-Datensatz ohne
`norm_entscheidung` an; das ging beim Schreiben des Skripts (2026-08-06), bevor
der `norm_entscheidung`-Pflicht-Trigger (2026-08-08) dazukam. `zeilen_hash`/
`ketten_hash` (das eigentliche Migrationsziel) existieren in der Live-DB bereits
-- die Migration selbst ist erledigt, nur die Testvorrichtung ist veraltet.

---

## Klasse C — echter Defekt (15)

Dringlichkeitsreihenfolge unten, mit Pruefung gegen `~/.claude/settings.json`
(Haltepunkte/Hooks): **keine** der 15 Dateien ist dort direkt als Kommando
verdrahtet, bis auf `wissensverlauf.py` (siehe dort) -- dessen Aufrufe laufen
aber ueber `differenz`/`aufzeichnen`, nicht `--selftest`, und sind mit
`2>/dev/null || true` stillgelegt, decken den hier gefundenen Fehler also nicht
auf.

### 1. normrang.py -- am dringlichsten
```
sqlite3.IntegrityError: knowledge_nodes.source darf nicht leer sein: Herkunft angeben (Datei, Konsil oder Recherche, aus der dieser Knoten stammt)
```
`import normrang` findet sich in `knowledge_mcp_server.py` -- dem laufenden
MCP-Server dieser Sitzung (die `mcp__knowledge__*`-Werkzeuge). Der Selbsttest
legt bewusst einen Knoten mit `source=None` an, um den Grenzfall "keine Quelle"
zu pruefen; das ging vor dem `source`-Pflicht-Trigger (schema.sql,
`knowledge_nodes_source_check_bi`). **Was heute nicht abgesichert ist, aber
abgesichert scheint:** normrang.py's eigener Umgang mit dem Fall "kein Quelltext"
wird seit diesem Trigger gar nicht mehr erreicht -- der Selbsttest bricht vorher
ab. Die produktive Rang-Ableitung selbst (`anwenden()`) ist von diesem
Testfehler nicht direkt betroffen, mangels Testlauf aber auch nicht mehr belegt.

### 2. normbestand.py
```
sqlite3.IntegrityError: knowledge_nodes.source darf nicht leer sein: Herkunft angeben (Datei, Konsil oder Recherche, aus der dieser Knoten stammt)
```
Gleicher Trigger, gleiches Muster wie normrang.py. Importiert von
`knowledge_lint.py` (55 Importeure im ganzen Repo) und von `migrate_quellhash.py`.
Auch hier: die Testvorrichtung (`_init_temp_db`) selbst verletzt den seit
2026-08-08 geltenden `source`-Pflicht-Trigger, nicht die produktive Logik.

### 3. knowledge_lint.py
```
AssertionError: set()
```
(vollstaendig: `assert "/shared/verfallen" in decay_paths, decay_paths` ->
`AssertionError: set()`). 55 Importeure im Repo, das meistgenutzte der 15.
Ursache gefunden: die Fixture in `_selftest_db()` (Kategorie 14,
Konfidenzverfall) setzt fuer den Testknoten `/shared/verfallen` die `source`
auf `"Testvorrichtung _selftest_db (knowledge_lint.py, kein echter Fund)"` --
`konfidenz.bewerten()` erkennt Regime 1 (verfallsfaehig) nur an Quellen im Muster
`"erzeugt aus <Datei> ..."` (konfidenz.py Zeile ~130/637ff). Die Testvorrichtung
faellt dadurch in Regime 3 (unbeobachtbar, kein Verfallswert) und taucht nie in
`confidence_decay` auf. Die Ursache liegt in der Test-Fixture von
knowledge_lint.py, nicht in konfidenz.py (das laut vorigem Rundlauf gruen ist)
und nicht in echten, korrekt formatierten `source`-Werten im Live-Bestand.
**Was nicht abgesichert scheint:** die Kategorie-14-Integration (Konfidenzverfall
im Lint-Gesamtlauf) ist seit dieser Drift ungeprueft, obwohl `knowledge_lint.py`
selbst in 55 Dateien als gruen vorausgesetzt wird.

### 4. wissensverlauf.py
```
AssertionError: {'ts': '2026-08-09T18:33:07+0000', 'corpus_size': 43, 'orphans': 1, 'stale': 3, 'never_pulled_nodes': 0, 'never_pulled_lessons': 0, 'vector_gaps': 55, 'near_duplicate_lessons': 5, 'path_hygiene': 2, 'truncated_embeddings': 1, 'avg_degree': 0.0, 'cross_project_lessons': 2, 'confidence_default_count': 11}
```
(Assertion: `confidence_default_count == 9`, tatsaechlich 11.) Nutzt zum Aufbau
der Test-DB `knowledge_lint._selftest_db()` mit; dessen eigener Kommentar
("K3 Konfidenz-Alter: 11 Knoten ... die urspruenglichen neun plus die beiden
Kategorie-10-Fixtures") zeigt: die Fixture wurde bewusst auf 11 erweitert, der
harte Erwartungswert 9 in `wissensverlauf.py` wurde dabei nicht nachgezogen.
Zwei Test-Dateien sind auseinandergelaufen. `wissensverlauf.py` ist in
`~/.claude/settings.json` an zwei Hooks verdrahtet (`differenz`, `aufzeichnen`),
beide mit `2>/dev/null || true` -- ein echter Ausfall wuerde dort lautlos
verschluckt, nur eben nicht durch DIESEN Fehler, da die Hooks nicht
`--selftest` aufrufen.

### 5. deckelreihe.py -- zwei unabhaengige Fehler in derselben Datei
```
AssertionError: der erste Punkt der Reihe muss der Ist-Stand sein, sonst fehlt die Nulllinie
```
`REIHE[0]` ist hart auf `(3, 2)` gesetzt, `haken/knowledge_recall_hook.py`
setzt `MAX_NODES=10`/`MAX_LESSONS=7` (Zeilen 310f) -- die Voreinstellungen sind
seit dem Schreiben von `deckelreihe.py` gestiegen, die "Nulllinie" der Messreihe
ist stehen geblieben. Zusaetzlich, unabhaengig davon: der normale Lauf ohne
`--selftest` bricht schon frueher mit
`AttributeError: 'list' object has no attribute 'get'` ab, weil
`abrufguete.lade_korpus()` heute `tuple[list[dict], int]` zurueckgibt (Dublettenzahl
als zweiter Wert), `deckelreihe.py` aber wie vor dieser Signaturaenderung
unentpackt `faelle = abrufguete.lade_korpus()` schreibt. Beide Fehler sind
echte Codedrift, keine Bestandsfrage.

### 6. trichter_gitter.py
```
AttributeError: 'list' object has no attribute 'get'
```
Gleiche Ursache wie der zweite Fehler in deckelreihe.py:
`abrufguete.lade_korpus()` liefert seit der Aenderung ein Tupel
`(faelle, dubletten)`, `trichter_gitter.py`s `demo()` entpackt es nicht.

### 7. liefermenge.py
```
TypeError: list indices must be integers or slices, not str
```
Dieselbe Ursache ein drittes Mal: `faelle = ag.lade_korpus()[:5]` schneidet das
Tupel `(faelle, dubletten)` statt der Fallliste, danach schlaegt
`fall["task"]` fehl, weil `fall` die ganze Fallliste ist. Drei Aufrufer
(deckelreihe.py, trichter_gitter.py, liefermenge.py) haben dieselbe API-Aenderung
in `abrufguete.lade_korpus()` verpasst -- ein gemeinsamer Fehler, nicht drei
verschiedene.

### 8. entscheidungen_server.py
```
KeyError: 'rows'
```
`_vergleich_neueste_datei()` sucht per `glob("ab_vergleich_abruf_*.json")` und
nimmt den alphabetisch letzten Treffer. Das Glob trifft ungewollt auch
`runs/ab_vergleich_abruf_2026-08-07.json.gegenprobe.json` (ein spaeter
angelegtes Gegenprobe-Ergebnis, kein Vergleichslauf), das alphabetisch NACH der
echten Datei `ab_vergleich_abruf_2026-08-07.json` sortiert und deshalb faelschlich
als "neueste" gewaehlt wird. Diese Datei hat keinen `"rows"`-Schluessel. Echter
Filterfehler im Glob-Muster, betrifft die eingebaute Vergleichsanzeige des
Servers (laut eigenem Docstring "reines Zubehoer, keine Voraussetzung fuer die
uebrigen Werkzeuge", nicht in `~/.claude/settings.json` verdrahtet).

### 9. wiederherstellung.py
```
sqlite3.OperationalError: error in trigger knowledge_nodes_normrang_herkunft_bi after drop column: no such column: NEW.norm_rang
```
Die Testvorrichtung entfernt bewusst vor einem `ALTER TABLE ... DROP COLUMN
norm_rang` funf benannte Trigger (Nachtrag laut Code-Kommentar vom 2026-08-08),
weil DROP COLUMN sonst an Triggern scheitert, die `NEW.norm_rang` lesen. Seither
kam ein sechster solcher Trigger dazu (`knowledge_nodes_normrang_herkunft_bi`,
schema.sql Zeile 906), der nicht in die Drop-Liste aufgenommen wurde. Die
eigentliche Pruef-Funktion `pruefe()` legt selbst keine Spalten um, ist von
diesem Fehler nicht direkt betroffen -- nur der "veraltetes Schema"-Testfall
(Szenario 2 von 3) kann nicht mehr aufgebaut werden.

### 10. messparameter.py
```
ModuleNotFoundError: No module named 'knowledge_recall_hook'
```
`sys.path.insert(0, str(HUB / "scripts"))` mit `HUB = SHARED_KNOWLEDGE.parent`,
also `/Volumes/daten/Begod2026/scripts` -- existiert nicht. Das eigentliche
Modul liegt in diesem Repo unter `haken/knowledge_recall_hook.py` (so wie es
`abrufguete.py` korrekt referenziert: `sys.path.insert(0, str(WURZEL / "haken"))`).
`messparameter.py` traegt noch den alten, nie an dieses Repo-Layout angepassten
Pfad.

### 11. messlauf_abrufguete.py
```
ModuleNotFoundError: No module named 'knowledge_recall_hook'
```
Identischer Pfadfehler wie messparameter.py (`HUB / "scripts"` statt
`haken/`).

### 12. messlauf_abrufguete_v2.py
```
ModuleNotFoundError: No module named 'knowledge_recall_hook'
```
Importiert `messlauf_abrufguete` als Modul und erbt dessen Fehler von dort
(kaskadierend, keine eigene Ursache).

### 13. knowledge_recall_replay.py
```
ModuleNotFoundError: No module named 'knowledge_recall_hook'
```
Gleicher Pfadfehler (`HUB / "scripts"`) wie messparameter.py/messlauf_abrufguete.py.

### 14. pruefkorpus_v3.py
```
ModuleNotFoundError: No module named 'knowledge_recall_hook'
```
Gleicher Pfadfehler wie die drei vorigen Dateien.

### 15. fenstergroesse.py
```
ModuleNotFoundError: No module named 'wiedereinstieg'
```
Anderer, aber verwandter Fehler: `import wiedereinstieg` erwartet ein Modul,
das in diesem Repo (`brainlehr`) an keiner Stelle existiert (nur im
Nachbarprojekt `hub/scripts/wiedereinstieg.py`, unerreichbar von hier). Nur
eine Testdatei (`tests/test_fenstergroesse_persistenz.py`) importiert
`fenstergroesse.py` ueberhaupt -- ausserhalb der Tests hat der Bruch keine
bekannte Wirkung, betrifft aber die einzige vorhandene Testdatei fuer dieses
Modul.

---

## `git status --short` (Beleg: keine bestehende Datei veraendert)

```
$ git status --short
```
(siehe Ausgabe unten in der Sitzung -- war zum Zeitpunkt der Erstellung dieser
Datei leer bis auf die neue Datei selbst)
