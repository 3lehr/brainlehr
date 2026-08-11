# Enigma-Landkarte — Stand 2026-08-11

Bestandsaufnahme, keine Bewertung. Quellen: Wissensspeicher (`knowledge_search`/`knowledge_read`/`lesson_query`),
Repo `/Volumes/daten/Begod2026/brainlehr` (Branch `brainlehr/b4-ausweis`, HEAD `9604617`), Arbeitsbaum
`.claude/worktrees/hallo-01e380` (Branch `claude/wie-geht-es-weiter-3f4066`), `git log --all --grep=enigma`.

## Wichtigster Befund zuerst: zwei verschiedene Orte

Der Arbeitsbaum, in dem dieser Auftrag lief (`hallo-01e380`, Branch `claude/wie-geht-es-weiter-3f4066`),
**enthält keine einzige Enigma-Datei** — `find . -iname '*enigma*'` liefert dort nichts. Der gesamte
Enigma-Code (Tests, Projektionslogik) liegt ausschließlich im Hauptrepo-Checkout auf Branch
`brainlehr/b4-ausweis`, aktuell HEAD `9604617`, mit den Commits `7dec67a`/`ceaa49a`/`d99ad31`/... . Wer in
diesem Arbeitsbaum weiterbaut, baut ohne den vorhandenen Stand und läuft in dieselbe Falle wie in
`L-17b865` beschrieben (Sperre doppelt gebaut, weil sie in einem Nachbar-Arbeitsbaum uncommittet lag).

## Was Enigma laut Wissensspeicher sein soll

- **Ziel-Architektur** (Knoten `d4d8ea8e`, Betreiberentscheidung): lokales Enigma-Gateway vor jeder
  externen API-Anbindung (Claude Code + freigegebene APIs, kein normales ChatGPT), mit Datenklassifikation,
  Projektion, Antwortprüfung, lokaler Rehydrierung.
- **Vier Bausteine** laut Auftrag: Pseudonymisierungs-Proxy, Zweckprojektion, Freigabestufen,
  Kontext-Schnappschüsse. Vergleichbare externe Verfahren (SurrogateShield, LLM-Redactor, LLM Guard,
  Presidio) sind recherchiert (Knoten `36a00cac`, `f559b38c`); Brainlehrs beanspruchter Mehrwert ist die
  Verbindung mit dem gemeinsamen versionierten Graphen und kantenbewusster Offenlegung.

## Einzelne Vorhaben mit Zustand

### 1. Zweckprojektion am `knowledge_read`-Pfad (Rolle `raumplaner`)
- **Was**: Ein beglaubigter Leser mit Rolle `raumplaner` bekommt bei `knowledge_read` nur das Feld
  `nutzinformation`, wenn Zweck- und Feld-Tag exakt passen (`zweck:raumplanung` + `feld:nutzinformation`);
  gesperrte Knoten (`freigabe='gesperrt'`) werden vorher neutral abgelehnt (kein Content, keine Metadaten,
  `access_count` bleibt unverändert).
- **Zustand: umgesetzt**, real verdrahtet — nicht nur synthetisch. Beleg: `knowledge_mcp_server.py`
  Zeilen 1441–1527, Funktionen `_KNOWLEDGE_READ_PROJEKTION`/`_knowledge_read_projection`/`knowledge_read`,
  Commits `ceaa49a` (project credential-bound reads) und `7dec67a` (block projected reads when locked).
- **Rot/Grün**: `tests/test_enigma_hausmeister_contract.py`, 2 Tests, beide grün
  (`python3 -m pytest tests/test_enigma_hausmeister_contract.py -v` → 2 passed). Kein `xfail`-Marker mehr
  im Datei-Kopf — anders als die Lehren `L-f67cd1`/`L-645969` (2026-08-10, "bleibt rot", "als xfail halten")
  nahelegen: der Zustand dort ist überholt, die Behebung kam danach über `ceaa49a`/`7dec67a`.
- **Grenze, die dabeisteht**: Die Projektionstabelle `_KNOWLEDGE_READ_PROJEKTION` kennt nur die eine Rolle
  `raumplaner`. Es ist ein Nachweis für EIN Zweck/Rolle-Paar, keine allgemeine Zweckprojektionsschicht.

### 2. Freigabe-Filter bei Suche/Browse
- **Was**: Ob `knowledge_search` und `knowledge_browse` einen als `gesperrt` markierten Knoten trotzdem mit
  Titel/Summary ausliefern.
- **Zustand: offen/Lücke bestätigt**. Beleg: `grep -n "gesperrt" knowledge_mcp_server.py` zeigt die Prüfung
  nur an Zeile 1450 (innerhalb `_knowledge_read_projection`, also nur für `knowledge_read`).
  `knowledge_search` (Zeile 1854) und `knowledge_browse` (Zeile 1465) enthalten keinen `gesperrt`-Check.
  Deckt sich mit Knoten `cda47024` ("Lesepfad dicht, Suchpfade offen") und `3237d074`.
- **Rot/Grün**: kein Test dazu gefunden (kein Treffer für `search`/`browse` in den drei
  `test_enigma_*`-Dateien).

### 3. Synthetischer Crypto-Shredding-Spike
- **Was**: Eigenständige, in-Test-definierte AES-GCM-Simulation (Vault/Copy/Shared-Blob/Stale-Snapshot),
  prüft ob ein Schlüssel nach "Löschung" wirklich unlesbar wird.
- **Zustand: geplant/Machbarkeitsstudie, nicht mit Produktionscode verbunden.** Beleg:
  `tests/test_enigma_crypto_shredding_spike.py` importiert nur `hashlib`, `secrets`, `cryptography` — keine
  Zeile bindet an `knowledge_mcp_server.py` oder eine reale Speicherschicht. Docstring selbst:
  "Synthetic crypto-shredding falsification spike; no production storage involved."
- **Rot/Grün**: 6 Tests, alle grün (`python3 -m pytest tests/test_enigma_crypto_shredding_spike.py -v`).
  Ein Fehler wurde unterwegs gefunden und behoben: Lehre `L-145930` beschreibt ein Restore-Gate, das
  zunächst grün meldete, obwohl die Epochen-Reihenfolge (`snapshot_epoch < anchor_epoch`) fehlte — nach
  Korrektur (Commit `4db3e5f7...`) prüft der Test das explizit.
- Knoten `61cbb841`: "C0-C4 real bleiben ungemessen" — nur der synthetische Spike ist gemessen.

### 4. Synthetischer Zwei-Prozess-/Grant-Spike (C1)
- **Was**: Simuliert eine getrennte Serving-/Control-Pipe mit Grant-Prüfung (Subject/Fields/Purpose/
  Recipient/Expiry/Nonce) vor "Protected Read", inklusive Denial-/Replay-/Revocation-/Deleted-Matrix.
- **Zustand: geplant/Machbarkeitsstudie, ebenfalls nicht mit Produktionscode verbunden.** Beleg:
  `tests/test_enigma_two_process_spike.py`, Docstring "Synthetic logical-two-store and C1 grant-boundary
  tests; no P2 claim." Eigene `_valid_grant`/`_seal`/`_open`-Hilfsfunktionen, kein Import aus
  `knowledge_mcp_server.py`.
- **Rot/Grün**: 6 Tests, alle grün. Reparatur-Historie sichtbar in Commits `f6f9e39` (Lifecycle-Fix) und
  `d99ad31` (Grant-Projektionsgrenze), dokumentiert in Knoten `662e7e69`/`dc206458`/`6749f21b`/`86f037dd`.
- Ausdrücklich nur "P1 logical_two_store_only"; Same-UID-Direktzugriff bleibt laut Knoten `dc206458`
  erwartungsgemäß als `P2_SHARED_ROOT_SAME_UID` außerhalb des Anspruchs.

### 5. Ausweis-System (`kern/ausweis.py`)
- **Was**: Beglaubigte Identität/Rolle als Grundlage für die Projektion (Ausweisdatei, Geheimnis-Check,
  Rollenzuordnung); von Vorhaben 1 direkt genutzt (`ausweis.loese_auf()`).
- **Zustand: umgesetzt für den Grundmechanismus**, aber mit einer bekannten, benannten Lücke:
  Lehre `L-33d3bd` — das Feld `art=mensch|maschine` schützt NICHT davor, dass sich jeder mit
  Dateizugriff selbst als Mensch einträgt (`ausweis.py --anlegen ... --art mensch` steht offen); es ist ein
  Merkmal, keine Sperre. Die tatsächliche Trennung (Dateirechte, `chown` durch den Betreiber) ist nicht
  gebaut.
- **Rot/Grün**: nicht Gegenstand dieses Auftrags, keine gezielte Prüfung durchgeführt.

### 6. P2/Unternehmensgrenze, Restore-/Reservoir-Governance, Geschäftsgeheimnis-Rekonstruktion
- **Zustand: ausdrücklich pausiert.** Knoten `c39083b1` ("Enigma-Ausbau pausiert bis P2-Sicherheitsgate")
  und `1e4fd2f8` ("Café-Konsil: ergebnisoffener Abschlussstand") benennen als offen: exklusiver
  Datenzugang, fail-closed unbeglaubigte Aufrufe, getrennte Identität/Vollmacht, serverseitiger Scope,
  Audit-/Speichernebenwege mit Recovery, Produkt-Zweckprojektion, Rekonstruktionsrisiko bei
  Geschäftsgeheimnissen. Keiner dieser Punkte hat ein Test-Äquivalent im Repo.

## Widerspruch, benannt statt aufgelöst

Zwei kritische Lehren (`L-f67cd1`, `L-645969`, beide 2026-08-10) sagen wörtlich, der Hausmeister-Vertrag
"bleibt rot" und solle als `xfail` gehalten werden, bis eine geschlossene Zweck-/Empfänger-Projektion
existiert. Der aktuelle Code und die aktuellen Tests widersprechen dem: kein `xfail`, beide Tests grün,
echte Projektionslogik verdrahtet (Punkt 1 oben). Auflösung: Die Lehren sind vom Vortag der Reparatur
und wurden nicht als "gelöst" nachgetragen — sie sind nicht falsch, sondern veraltet. Ihre `prevention`
("als xfail halten bis...") wurde befolgt und dann durch echte Arbeit erledigt, aber kein Knoten sagt das
explizit ("Lehre erledigt"). Ein Leser, der nur die Lehren liest, hält den Pfad für weiterhin offen.

## Steht und trägt (mit Beleg)

- Zweckprojektion für Rolle `raumplaner` an `knowledge_read`: echter Code, 2/2 Tests grün
  (`knowledge_mcp_server.py:1441-1527`, Commits `ceaa49a`, `7dec67a`).
- Gesperrte Knoten werden am `knowledge_read`-Pfad neutral abgelehnt, ohne Content/Metadaten/Zählerstand
  (`test_enigma_hausmeister_contract.py::test_gesperrter_knoten_wird_vor_der_projektion_neutral_abgelehnt`,
  grün).
- Ausweis-Grundmechanismus (Identität/Rolle, beglaubigt vs. unbeglaubigt) ist gebaut und wird vom
  Read-Pfad tatsächlich konsultiert (`ausweis.loese_auf()`), mit einer schriftlich dokumentierten
  Restlücke (`L-33d3bd`).
- Zwei synthetische Machbarkeitsstudien (Crypto-Shredding, Zwei-Prozess-Grant) sind sauber isoliert
  gebaut, 12/12 Tests grün, und ehrlich als "kein P2-Anspruch"/"no production storage involved" markiert.

## Offen — sortiert danach, was andere Punkte blockiert

1. **Suchpfad-Freigabe-Filter fehlt** (`knowledge_search`, `knowledge_browse` prüfen `gesperrt` nicht) —
   blockiert jede Aussage "Freigabestufen wirken", weil ein gesperrter Knoten trotzdem über Titel/Summary
   auffindbar bleibt; betrifft direkt Baustein "Freigabestufen" aus dem Auftrag.
   Kein Test vorhanden.
2. **Zweckprojektion nur für eine Rolle/ein Zweckpaar** (`raumplaner`/`raumplanung`) — jede Ausweitung auf
   reale Rollen (z. B. externe LLM-Anfragen) braucht diese Tabelle erst noch, sonst bleibt "Zweckprojektion"
   im Auftrag ein Türspalt, keine Schicht.
3. **Ausweis-Sperre nicht real getrennt** (`L-33d3bd`) — solange Selbstbedienung möglich ist, hängt die
   ganze Zweckprojektion an einer Identität, die sich jeder mit Dateizugriff selbst geben kann; blockiert
   jede P2-Aussage.
4. **Crypto-Shredding und Zwei-Prozess-Grenze sind nicht mit dem echten Speicher verbunden** — beide Spikes
   beweisen nur, dass das Verfahren in der Simulation funktioniert, nicht dass `knowledge_mcp_server.py`
   es einsetzt. Ohne Verdrahtung bleibt Baustein "Kontext-Schnappschüsse"/Recovery unbelegt am realen Pfad.
5. **Pseudonymisierungs-Proxy (Baustein 1 aus dem Auftrag) und Kontext-Schnappschüsse**: keine Codefunde,
   nur Recherche-/Konzeptknoten (`36a00cac`, `f559b38c`, `dc806436`). Noch reine Planung.
6. **P2-Unternehmensgrenze insgesamt** (`c39083b1`) — ausdrücklich pausiert, unabhängig von den anderen
   Punkten, aber am Ende die Voraussetzung für jeden Produktionsanspruch.
7. **Veraltete Lehren nicht als erledigt markiert** (`L-f67cd1`, `L-645969`) — kein Blocker für den Code,
   aber ein Blocker für jeden, der aus dem Wissensspeicher allein den Zustand ableitet (siehe Widerspruch
   oben).
