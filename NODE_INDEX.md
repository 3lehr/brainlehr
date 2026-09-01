# Knoten-Index (generiert — nicht von Hand editieren)

Quelle: `shared-knowledge/build_node_index.py`. Knoten: 5270 in 30 Aesten · Lehren: 1213 · erzeugt: 2026-08-23T17:51:30+02:00

Landkarte, keine Volltexte. Gezielt nachladen: `knowledge_read <path>`, `knowledge_search <begriff>`, `lesson_query <begriff>`.

## Landkarte (Ast: Anzahl Knoten)

- /germanquad: 2713
- /nasa-llis: 1638
- /brainlehr: 316
- /methodik: 174
- /apps: 107
- /ops: 94
- /shared: 55
- /openlehr: 46
- /plaene: 17
- /arch: 16
- /simulation-akademie-messaufbau-kein: 15
- /testing: 10
- /fahrtenbuch: 9
- /tools: 8
- /werkzeuge: 8
- /agents: 7
- /frontend: 7
- /domaenen: 5
- /probe: 5
- /backend: 4
- /dokumente: 3
- /lessons: 3
- /begod: 2
- /stadtwerke: 2
- /aka: 1
- /bebetter: 1
- /domaenenimporte: 1
- /probe2: 1
- /testdatenknoten-schreibrechtepruefung: 1
- /woanders: 1

## Lehren gebuendelt (1213 gesamt)

nach Art: antipattern 619, insight 214, error 202, pattern 178
nach Projekt: systemweit 556, fahrtenbuch 349, brainlehr 311, openlehr 287, hub 229, buckeberg 146, shared 74, wohlair 57, +27 weitere Projekte (205)

## Juengste 15 Knoten

- 2026-08-23 /apps/fahrtenbuch/s03-gps-tcp-elm-belegt-s04-reconnect — S03 GPS-TCP-ELM belegt, S04-Reconnect rot
- 2026-08-23 /apps/fahrtenbuch/build-103-testflight-availability-has-a — Build 103 TestFlight availability has a device boundary
- 2026-08-23 /apps/fahrtenbuch/flutter-legacy-testflight-build-103-ist — Flutter Legacy TestFlight Build 103 ist validiert
- 2026-08-23 /apps/fahrtenbuch/dashboard-nutzt-genau-einen-festen — Dashboard rotiert alle Meldungen in einem festen oberen Slot
- 2026-08-23 /apps/fahrtenbuch/legacy-flutter-ist-wieder-ziel-app-fuer — Legacy Flutter ist wieder Ziel-App für TestFlight Build 103
- 2026-08-23 /methodik/direktiven/eilmeldung-an-brainlehr-zwei-mcp-server — EILMELDUNG an brainlehr: Zwei MCP-Server in Hermes zeigen nach /tmp und werden alle fuenf Minuten vergeblich neu gestartet
- 2026-08-23 /apps/fahrtenbuch/native-testflight-build-102-validiert — Native TestFlight Build 102 validiert
- 2026-08-23 /probe/zweite-schnappschussprobe-2026-08-23 — Zweite Schnappschussprobe 2026-08-23
- 2026-08-23 /probe/schnappschussprobe-determinismus-2026 — Schnappschussprobe Determinismus 2026-08-23
- 2026-08-21 /apps/fahrtenbuch/native-ble-suche-zeigt-alle-funde — Native BLE-Suche zeigt alle Funde virtuell geprüft (2026-08-21)
- 2026-08-21 /apps/fahrtenbuch/native-dongle-suche-zeigt-alle — Native Dongle-Suche zeigt alle Bluetooth-Geraete und erlaubt Auswahl
- 2026-08-21 /brainlehr/brainlehr-laeuft-in-hermes-nie-allein — brainlehr laeuft in Hermes nie allein — fuenf Beruehrpunkte, gemessen
- 2026-08-21 /methodik/direktiven/eilmeldung-an-brainlehr-ein-dokument — EILMELDUNG an brainlehr: Ein Dokument, das einen Beschluss ZITIERT, ist eine prüfbare Behauptung — und niemand prüft sie
- 2026-08-21 /fahrtenbuch/native-swift-testaudit-trennt-funktions — Native Swift Testaudit trennt Funktions- und UI-Evidenz
- 2026-08-21 /ops/verwalterwahl-weg-im-buckeberg-zum-2027/der-laufende-verwaltervertrag-beruft — Der laufende Verwaltervertrag beruft sich auf eine Ermächtigung, die das Protokoll nicht ausweist

## Juengste 15 Lehren

- 2026-08-23 [error] Beim Kuratieren des Android-GATT-Testbefunds wurde lesson_record einmal mit dem nicht erlaubten Anlass 'test' aufgerufen; der…
- 2026-08-23 [antipattern] Review caught that the S03/S04 handoff claimed T0 priority was preserved when T1 requests were promoted, but the mutex only prevented newly…
- 2026-08-23 [antipattern] Eine Zahl aus einem grep OHNE Zeilenanker erhoben, dabei Kommentarzeilen mitgezaehlt -- und darauf eine Entscheidung gebaut, die genau das…
- 2026-08-23 [error] ASC audit initially required fastlane rather than spaceship, leaving the ConnectAPI global token setter unloaded; it failed before any…
- 2026-08-23 [antipattern] Eine vom Werkzeug ERZEUGTE Datei ueberschrieben, ohne sie vorher zu lesen -- und dabei genau die Faehigkeit geloescht, nach der der…
- 2026-08-23 [error] ASC audit selected the system Ruby after sourcing shell configuration, so fastlane could not load; the command failed before issuing a…
- 2026-08-23 [error] ASC read-only audit almost queried Info.plist through the duplicated ios/ios path after changing to ios; the path check showed no file was…
- 2026-08-23 [error] Nach Fahrtenbuch Build 103 wurde dem Betreiber gemeldet, der Build sei in der bestehenden internen Testgruppe erreichbar. Der Betreiber sah…
- 2026-08-23 [insight] Beim Abschlussaudit für Fahrtenbuch Build 103 wurde ein nicht vorhandenes Skript `begod/scripts/validate_beta_test_json.py` als…
- 2026-08-23 [antipattern] Release-Evidenz-Commit: eine leere Shell-Variable wurde als Git-Pathspec übergeben; Git brach vor dem Staging ab, daher wurde kein…
- 2026-08-23 [antipattern] Eine Accessibility-Bedingung kombinierte Nullable-Coalescing und OR ohne Klammern; fokussierter Flutter-Test und Analyzer stoppten den…
- 2026-08-23 [antipattern] Beim Entfernen des CarHome-Kalenderhinweises wurde der gemeinsame calendar_service-Import zunächst mit entfernt; der fokussierte…
- 2026-08-23 [antipattern] Zwei Fehlermeldungen an ein fremdes Projekt vorbereitet, beide mit Fundstellen und Belegstand geschrieben, beide beim Nachpruefen falsch.…
- 2026-08-23 [antipattern] Beinahe eine Falschaussage ueber eine NICHT zugestellte Eilmeldung gemacht, weil ich den Datenbanknamen getippt statt den Aufloeser gefragt…
- 2026-08-23 [antipattern] Ein Paket zwei Tage lang fuer fertig gehalten, ohne es je zu installieren. Der erste echte Erstlauf -- Rad bauen, frische virtuelle…
