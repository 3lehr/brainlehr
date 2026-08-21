# Auswertung: YouTube-Video „acht Hermes-Funktionen" — 2026-08-21T15:22:40+0200

Quelle: `video_de.txt`, 42533 Zeichen, deutsche Auto-Untertitel,
https://www.youtube.com/watch?v=ScoibCUIpjk. Auto-Untertitel sind eine
SCHWACHE Quelle — Eigennamen sind verstümmelt ("Hermis" = Hermes, "Cendly"/
"Cendieferweise" = Calendly, "Cloud Code"/"Cloud" = Claude Code, "Chimika 3" =
Kimi K2, "Son"/"Sonnet" korrekt, "GPT 5.6 Soul/Luna" = vermutlich GPT-5.1
Codex/o-Varianten, unklar). Wo eine Behauptung gegen den Quelltext unter
`/Users/lehrmacbook/.hermes/hermes-agent` geprüft werden konnte, steht Datei
und Fund; sonst steht ausdrücklich "nur aus dem Video, nicht am Code geprüft".

**Befund vorweg: es sind genau acht Funktionen**, wie angekündigt. Der
Sprecher zählt sie selbst durch (erste bis achte Funktion), keine Lücke,
keine Dopplung.

## Teil 1 + 2 — die acht Funktionen

### 1. Hermes Bots (Bot Mode)
Mehrere benannte Agenten mit eigenem Modell, eigenem Job und eigenem
Gedächtnis, einzeln oder im Gruppenchat mit gegenseitigem @-Mention.
Zitat: *"Jeder mit eigenem Namen, eigenem Job, eigenem Modell und auch einem
eigenen Gedächtnis."*
Code geprüft: `tools/bot_mode_probe.py:1-4` — "When the desktop's Bot Mode
manages this install (any profile carries a `ui_meta['hermes-bots']` block
...) a bot's canonical 'Bot Chat' session ... gets a short 'Messaging other
agents' section". Bot Mode existiert, Mechanismus bestätigt.
**Einordnung: RISIKO.** Der bekannte Knoten `5d0c5cd4` hält als *ungemessenen
nächsten Schritt* fest: "Hermes führt Agententeams ... ob jeder davon einen
eigenen Speicherabruf auslöst, ist nicht geprüft." Bot Mode ist genau der
Mechanismus, der das auslösen würde — ein Gruppenchat mit vier gepingten
Bots kann vier `prefetch_all`-Aufrufe gegen brainlehr in einem Zug erzeugen,
ohne gemeinsamen Deckel (Punkt 2 desselben Knotens). Das ist kein neuer
Fünferpunkt, sondern die konkrete Ursache für die dort offene Frage.

### 2. Kanban-Board
Natives Projektmanagement-Board; Agenten und Nutzer legen Tickets an, jeder
Bearbeitungsschritt wird als Karte sichtbar.
Zitat: *"das Ganze heißt Bot Mode ... genauso wie das Canban Board"* /
*"die Agenten können ihr Tickets anlegen"*.
Code geprüft: `tools/kanban_tools.py`, `hermes_cli/kanban.py`,
`hermes_constants.py:129` ("kanban dispatcher in `hermes_cli/kanban_db.py`")
— umfangreich vorhanden, über 40 Testdateien allein unter `tests/hermes_cli/`
und `tests/gateway/`.
**Einordnung: EGAL.** Reines Projektmanagement für Coding-Subagenten, berührt
weder Speicherpfad noch Kalibrierung noch Belegkette.

### 3. H-Mode / lokales Gateway (Bildschirmwahrnehmung)
Minimiertes Chatfenster, das per Screenshot sieht, was auf dem Bildschirm
des Nutzers passiert, wenn Hermes lokal (nicht auf einem Server) läuft.
Zitat: *"hat aber die Möglichkeit alles zu sehen, was auf unserem Bildschirm
passiert."*
Nur aus dem Video, nicht am Code geprüft — "H Mode"/Tastenkürzel Strg+Shift+H
wurde nicht im Quelltext verifiziert.
**Einordnung: EGAL.** Visuelle Bildschirmwahrnehmung ohne Bezug zu Speicher,
Wissen oder Kalibrierung.

### 4. Computer Use (Maus-/Tastatursteuerung)
Hermes steuert Maus und Tastatur des Rechners selbst, um Aufgaben in Apps
ohne API/CLI zu erledigen, und legt sich dafür einen Skill an.
Zitat: *"dann funktioniert das auch mittlerweile mittels der Computeruse
Funktion."*
Code geprüft: `tools/computer_use_tool.py:1-6` — Shim registriert
`computer_use`-Toolset, echte Implementierung in `tools/computer_use/`
(`schema.py`, `tool.py`, `permissions.py`, `browser_route.py`). Existiert.
**Einordnung: EGAL.** Aktionsausführung auf dem Betriebssystem, kein
Speicherpfad, keine Wissensfrage.

### 5. Sprachsteuerung (Voice, Wake-Word)
Freie Konversation per Sprache inkl. Weckwort ("Hey Hermes") und
Sprachausgabe über ElevenLabs.
Zitat: *"können wir Hermes auch lediglich per Sprache steuern ... und er kann
uns auch per Sprache antworten."*
Code geprüft: `tools/wake_word.py:1-19` — drei Engines (openwakeword,
sherpa, porcupine), alle "fully on-device"; `tools/tts_tool.py`,
`tools/voice_mode.py` vorhanden.
**Einordnung: EGAL.** Ein-/Ausgabemodalität, ändert nichts an Speicher- oder
Kalibrierungslogik.

### 6. Nativer Browser in der Desktop-App
Hermes öffnet, liest und steuert einen eingebauten Browser-Tab, kann
Formulare ausfüllen, Kommentare vorlesen, Paper gemeinsam mit dem Nutzer
lesen.
Zitat: *"wir haben einen eingebauten Browser hier in der Desktop App."*
Code geprüft: `tools/browser_tool.py`, `tools/browser_cdp_tool.py`,
`tools/browser_use_cli.py` vorhanden.
**Einordnung: CHANCE.** Bestätigt indirekt das eigene Design aus `BDW-P12`
(Fremdimporte erfinden keine Herkunft, tragen nur den Weg): Wenn per Browser
recherchierte Inhalte über den Hermes-Adapter (`sync_turn`, laut `STAND.md`
per Vorgabe aus, im Zustand "an" trägt es den WEG statt einer Quelle) in
brainlehr einfließen, ist genau diese Zurückhaltung nötig — ein Browser
liefert keine geprüfte Quelle, nur einen Fundort.

### 7. In-App-Vorschau erzeugter Programme/Dokumente
Selbstgebaute Apps (z. B. ein Snake-Spiel) oder Dokumente (PDF) werden direkt
im rechten Vorschaufenster angezeigt und getestet, ohne externes Programm.
Zitat: *"und er soll mir das Ganze hier im Preview anzeigen, damit ich es
testen kann."*
Code geprüft: `apps/desktop/src/app/chat/right-rail/preview-pane.tsx`
existiert (Fund über Dateisuche, Inhalt nicht gelesen).
**Einordnung: EGAL.** UI-Feature zum Testen erzeugter Artefakte, kein Bezug
zu Wissensverwaltung.

### 8. Artifacts-Dashboard
Zentrale, sessionübergreifende Ablage aller von Hermes erzeugten Dateien,
Bilder und Links, mit Rücksprung in die erzeugende Session.
Zitat: *"all diese Sachen werden hier unter den Artifacts abgespeichert,
damit du sie immer schnell findest."*
Code geprüft: `apps/desktop/src/app/artifacts/index.tsx`,
`apps/desktop/src/app/artifacts/artifact-utils.ts` vorhanden.
**Einordnung: CHANCE.** Vergleichbares Ziel wie `BDW-P15`
(Dokumentenablage: Datei + Knoten + Auszug, Pflicht-`quell_hash`) — aber ohne
erkennbares Herkunfts-/Prüfsummenkonzept aus dem Video oder den geprüften
Dateinamen. Interessant als Vergleichsobjekt für die eigene Ablage, nicht als
Bedrohung.

## Teil 3 — zwei Listen

### (a) Wo sind sie uns voraus
- Multi-Agent-Orchestrierung mit geteiltem, für den Nutzer sichtbarem
  Gruppenkontext (Bot Mode) — Usability, die kein eigenes Konzept hat.
- Volle Betriebssystem- und Browsersteuerung (Computer Use, nativer
  Browser, H-Mode) — wir haben nichts, das den Rechner selbst bedient.
- Freie Modellwahl pro Agent, bis hin zu lokalen Modellen auf eigener
  Grafikkarte — Modell-Agnostik als gelebtes Produktfeature, nicht nur als
  Testanforderung wie unser `BDW-R05`.
- Vollständiges Sprachinterface (Wake-Word, TTS, freie Konversation).
- Natives Kanban für Subagenten-Fortschritt, sofort sichtbar ohne Zusatzbau.
- Artifacts-Dashboard: sessionübergreifende Dateisuche, die bei uns fehlt.

### (b) Was ihnen fehlt, das wir haben
- Keine Herkunftspflicht bei Importen — kein Gegenstück zu `BDW-P12`
  (Fremdimporte tragen den Weg, erfinden keine Quelle).
- Kein Geltungszeitraum/Norm-Rang und keine dokumentierte Ablösung von
  Wissen — kein Gegenstück zu `BDW-P07` (Name mit Geltungszeitraum) und
  `BDW-P08` (Ablösung mit Grund, Altes bleibt lesbar).
- Keine vier Gütegatter für Retrieval (Treffer/Falschmeldung/Enthaltung/
  Aktion) — kein Gegenstück zu `BDW-P04`.
- Kein manipulationsgeschütztes, versioniertes Audit über Wissenseinträge —
  kein Gegenstück zu `BDW-E10`.
- Keine Fälligkeits-/Vorgangsachse im Gedächtnis selbst (nur Kanban-Tickets
  für Coding-Aufgaben, kein "was ist wann von wem zu tun" als Wissensobjekt
  wie `BDW-P17`).
- Kein Gesamtdeckel über mehrere Speicher-Anbieter — bereits bekannt
  (`5d0c5cd4`, Punkt 2), hier nicht neu gezählt.
