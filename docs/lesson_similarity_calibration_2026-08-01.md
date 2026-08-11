---
Erstellt: 2026-08-01T06:45:00+0200
Autor: BEGOD-Implementer (hub/subagent-bericht-caveman)
Zweck: Kalibrier-Auswertung fuer lesson_recorder.py-Aehnlichkeitserkennung.
Keine Datenbankaenderung -- reine Auswertung gegen eine Kopie von brainlehr.db.
---

# Kalibrierung: Aehnlichkeitserkennung ueber die 366/367 Lessons

## Ausgangsbefund (gemessen, 2026-08-01)

`shared-knowledge/brainlehr.db`, Tabelle `lessons_learned`: **367** Zeilen
insgesamt, **366** mit `occurrences=1`, **0** mit `auto_rule_generated=1`,
**0** mit `status='escalated_to_rule'`. Ursache: `lesson_recorder.py` verglich
Dubletten nur ueber `type` + byte-identische `description` -- zwei Formulierungen
desselben Vorfalls sind nie zeichengleich.

**Abweichung vom Auftrag:** Der Auftrag beschreibt dieses Problem fuer
`lesson_recorder.py` (die CLI). Es existiert eine zweite, unabhaengige
Implementierung in `shared-knowledge/knowledge_mcp_server.py` (dem MCP-Server
hinter dem tatsaechlich genutzten Werkzeug `mcp__knowledge__lesson_record`) --
und dort wurde exakt dieses Problem bereits am 2026-07-30 in Commit
`feaf79cb0` geloest: Wortmengen-Jaccard-Vergleich (`_find_similar_lesson`,
Schwelle `SIMILARITY_THRESHOLD=0.18`), expliziter `same_as`-Merge-Pfad
(`_bump_lesson`), Eskalation ab 3 Vorkommen auf `status='escalated_to_rule'`.
`lesson_recorder.py` selbst ist **totes Werkzeug**: `grep -rl lesson_recorder`
im ganzen Repo findet ausser sich selbst keinen Aufrufer (kein Hook, kein
Skript, kein MCP-Tool-Eintrag) -- nur Doku/Archiv-Dateien erwaehnen den Namen
beilaeufig. Die 0/366-Messung oben gilt unabhaengig davon, welche der beiden
Implementierungen man betrachtet: `knowledge_mcp_server.py`s Fix war neuer als
der letzte Grossteil der Lessons und wurde bislang von niemandem per
`same_as` genutzt.

Vorgehen in diesem Auftrag: `lesson_recorder.py` wie zugewiesen fixiert --
durch Kopplung an die in `knowledge_mcp_server.py` bereits kalibrierte
Erkennung (Import, kein Nachbau), damit beide Wege (CLI und MCP-Tool) dieselbe
Schwelle und denselben `same_as`-Mechanismus teilen und nicht auseinanderlaufen.

## Kalibrierung gegen die echten aktiven Lessons

Lauf gegen eine **Kopie** von `brainlehr.db` (keine Schreiboperation auf das
Original). Aktive Lessons (`status='active'`): **320** von 367 (47 sind
`resolved`/`escalated_to_rule` und fliessen nicht in den Vergleich ein, da
`_find_similar_lesson` nur aktive Lessons desselben Typs vergleicht).

| Schwelle | Paare >= Schwelle |
|---|---|
| 0.20 | 5 |
| **0.18 (gewaehlt)** | **6** |
| 0.15 | 10 |
| 0.12 | 25 |
| 0.10 | 47 |
| 0.08 | 112 |

Bei Schwelle 0.18: **6 Paare, 6 Gruppen** (jede Gruppe genau 2 Mitglieder,
keine Kette laenger als 2) -- Sichtpruefung aller 6 Paare von Hand:

**Alle 6 Paare bei 0.18 sind inhaltlich richtige Zusammengehoerigkeiten** (kein
falscher Treffer im Bestand bei dieser Schwelle):

1. `L-a27cc9` / `L-14a742` (Score 0.24) -- beide `flutter build ipa`/
   `xcodebuild -exportArchive`-Codesign-Fehler beim IPA-Export.
2. `L-287c56` / `L-3d72a5` (Score 0.27) -- **Beispiel richtige Zusammenlegung**:
   beide "Subagent-Wiederverwendung spart NICHT linear", fast wortgleiche
   Kernaussage, nur anders formuliert.
3. `L-1b46fe` / `L-a41de9` (Score 0.28) -- beide "Signatur/Schutzschicht gebaut,
   Grenze offen" (derselbe benannte Antipattern, zwei OpenLehr-Vorkommen).
4. `L-21849b` / `L-ab05b4` (Score 0.25) -- beide "Dedupe-/Latch-Flag vor dem
   Erfolgs-Guard gesetzt" bei asynchronen Callbacks.
5. `L-c3989d` / `L-a08f87` (Score 0.22) -- beide fahrtenbuch-Vollbild-Dialog
   beim DB-Schluessel-Lesefehler.
6. `L-affae1` / `L-9f5e60` (Score 0.19) -- beide "parallele Agenten, TABU-Liste
   blockiert alle" am selben Tag (2026-07-30).

**Beispiel falsche Zusammenlegung** (tritt erst bei zu niedriger Schwelle auf,
NICHT bei 0.18): Bei Schwelle 0.11 wuerden `L-f54650` ("fahrtenbuch_legacy:
Kalender-Export-Mechanismus nutzt MethodChannel ... fuer den ICS-Export") und
`L-692936` ("fahrtenbuch_legacy: Play Console verlangt Google Play Billing
Library >=8.0.0") als "aehnlich" markiert (Score 0.11/0.118) -- zwei voellig
verschiedene Themen, die nur den Praefix "fahrtenbuch_legacy" und ein paar
generische Woerter teilen. Bei 0.18 erscheint dieses Paar korrekt NICHT.
Aehnlich bei 0.12: `L-68b9bb` (Dart-Enum-Map Typsicherheit) vs. `L-a82bc8`
(openhood Status-Parsing degradiert zu "gray") -- verschiedene Bugs, gleiches
Flutter-Vokabular.

**Fazit Kalibrierung:** Schwelle 0.18 (uebernommen aus `knowledge_mcp_server.py`,
dort bereits am 2026-07-30 gegen denselben Bestand kalibriert) traf im aktuellen
Bestand **6 von 6 Paaren richtig, 0 falsch**. Eine niedrigere Schwelle haette ab
etwa 0.12 begonnen, erkennbar verschiedene Fehler zusammenzuwerfen.

## Rueckwirkende Gruppierung -- NICHT durchgefuehrt

Wie im Auftrag verlangt: keine Datenbankaenderung, keine Massenzusammenfuehrung.
Falls jemand die 6 Gruppen oben tatsaechlich per `same_as` nachtraeglich
mergen will, sind das 6 manuelle `lesson_recorder.py record --same-as <id>`-
bzw. `mcp__knowledge__lesson_record(..., same_as=...)`-Aufrufe -- keiner davon
automatisch ausgefuehrt.

## Gegenproben (durchgefuehrt, nicht im Dauerbestand der Testsuite)

1. **Wiedererkennung zurueckgenommen** (`git stash` auf `lesson_recorder.py`,
   alter Code ohne Kopplung an `knowledge_mcp_server.py`): 4 von 5 Tests in
   `tests/test_lesson_recorder.py` wurden rot (`same_as` unbekannt, Text-Anhang,
   Eskalation, Wiedererkennungs-Hinweis) -- die Erkennung ist also
   testwirksam, nicht zufaellig gruen.
2. **Schwelle testweise auf 0 gesetzt** (`kms._find_similar_lesson.__defaults__ = (0.0,)`
   in einer isolierten Python-Session, keine Dateiaenderung): Test
   `test_different_topics_similar_words_not_merged` wurde rot -- das
   Kalender-Export- und das Play-Billing-Lesson wurden bei Schwelle 0
   faelschlich als "aehnlich" gemeldet (Score 0.12). Der Test faengt also
   tatsaechlich falsche Zusammenlegungen, nicht nur "irgendein" Verhalten.
