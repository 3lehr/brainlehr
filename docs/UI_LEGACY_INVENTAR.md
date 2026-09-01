# UI-Legacy-Inventar

**Evidenzbestand, nicht normativ.** Untergeordnet zu `BDW-R03` (`single-webui`)
und ADR-035. Stand 2026-08-28: Es ist weder eine Verschiebungs- noch eine
Löschfreigabe. `übernehmen`, `ersetzen` und `verwerfen` sind nur die
Zuordnung zum Zielmodul der zentralen WebUI; endgültig Legacy wird ein
Eintrag erst mit dem BDW-R03-Gate.

Für dessen ersten, noch offenen Durchstich dokumentiert dieses Inventar nur
Zielmodule für Anmeldung/gesperrt, revalidierten Kontext, Wissensabruf,
Vertrauensregler und wahre Eingriffsherkunft. `BDW-P63`, `BDW-P65` und
`BDW-P66` müssen dabei Module derselben WebUI-Shell bleiben. Eine
Entwicklungsassistent-Zuordnung ist vor einer quellengestützten User Journey
kein V1-Ziel; diese Evidenz ersetzt keine normative Entscheidung.

## Kandidaten

### UI-001 — Atelier, native Brainlehr-App

- **Fundort / Technik / Start:** `atelier@app/Package.swift`;
  SwiftUI/AppKit, Produkt `LehrAtelier`, Start über das Swift-Package.
- **Status / Funktionen:** vorhandener nativer Renderer, durch ADR-035
  Legacy. `app/Sources/LehrAtelier/AtelierApp.swift` startet Dienstaufsicht;
  `HauptFenster.swift`
  weist Quellen, Mehrfachansicht, Bearbeiten, Dokument, Sitzung,
  Wissensraum, Landkarten, Domäne und Ausweise aus.
- **Verträge / Steuerung / Isolation:** `BrainlehrCore` plus lokaler Dienst;
  Domänenimport verlangt Ausweis. `Steuerschnittstelle.swift` ist ein
  explizit aktivierter, Loopback-gebundener **Debug**-Pfad; `Steuerbefehl`
  definiert 16 HTTP-Pfade (18 Command-Varianten), darunter `/inhalt`, `/aktion`,
  `/bildschirm`, `/bildschirme`, `/mitstart`, `/regler` und `/auswahl`.
  Das ist kein produktives, autorisiertes LLM-Gateway. Nutzer-/Kontextbindung
  für alle Ansichten: unbekannt.
- **Betrieb / A11y / Test:** Fehlerbanner und Neustart der Dienstaufsicht;
  sichtbare Labels und Tastaturkürzel. Umfangreiche
  `SteuerbefehlTests.swift` decken Pfaddeutung, sichtbare Aktionsnamen,
  Fehler und die Ablehnung menschlicher Aktionen ab; vollständiger Swift-Lauf
  hier nicht gefahren.
- **Blaupause / Risiko / Zuordnung:** Navigation, Fehler-/Recovery-Zustände,
  A11y-Labels und semantische Domänenansicht **übernehmen** →
  `shell`, `knowledge`, `domain-host`, `identity`; kein Swift-Renderer.
  Sichtbare Aktionsnamen, typed State/View/Action, Warten auf Wirkung und
  stale-screen-Korrektur **übernehmen** → `actions`, `operations`;
  menschliche Ablehnung serverseitig beibehalten. Debug-Loopback und
  native/HTML-Doppelbedienung **ersetzen** durch produktives typed Gateway
  mit Auth, Kontext und Bestätigung.

### UI-002 — Atelier-Teilrenderer: eingebetteter Wissensraum

- **Fundort / Technik / Start:** `atelier@app/Sources/LehrAtelier/WissensraumWebView.swift`
  und `LandkartenAnsicht.swift`; WKWebView gegen den lokalen Dienst. Teil von
  UI-001, nicht separat startbar.
- **Status / Funktionen:** vorhandener alter Rendererpfad:
  Baum, Bedeutung, Spuren, Vergleich und Abrufweg; Landkarten als eigene
  Seite. Der Dienst lädt `127.0.0.1:8799` aus
  `berichte/entscheidungen_server.py`.
- **Verträge / Steuerung / Isolation:** Browsersteuerung geschieht per
  injiziertem Script und DOM-Klick, nicht per typisierter Action. Lokale
  Loopback-Bindung belegt; Session-/CSRF-/Kontextisolation dieses Pfads ist
  im Inventarlauf nicht nachgewiesen.
- **Betrieb / A11y / Test:** Dienstbanner/Retry vorhanden; Web-A11y und
  automatisierter End-to-End-Test unbekannt.
- **Blaupause / Risiko / Zuordnung:** fünf Wissensansichten und die Trennung
  „Wissensraum vs. Systemkarte" **übernehmen** → `knowledge`, `graph`.
  DOM-Klick und in WebView injizierte UI-Regler **ersetzen** → versionierter
  View-/Action-Vertrag.

### UI-003 — lokale Entscheidungsoberfläche

- **Fundort / Technik / Start:** `atelier@berichte/entscheidungen_server.py`,
  `python3 berichte/entscheidungen_server.py --port 8799`; stdlib
  `ThreadingHTTPServer`, nur `127.0.0.1`.
- **Status / Funktionen:** historische Betreiber-/Wissensraumoberfläche;
  laut Modul keine Voraussetzung des übrigen Betriebs. Liefert HTML und
  JSON; alte `/raum`-/`/vergleich`-Wege delegieren auf eine Adresse.
- **Verträge / Steuerung / Isolation:** liest/ruft Kernskripte auf;
  einzelne Schreibwege existieren. Der Quelltext benennt eine alleinige
  Origin-Prüfung als Übergang; vollständige Auth-/Session-Abdeckung ist
  damit **nicht** belegt. Kein LLM-Renderer/LLM-Steuerpfad gefunden.
- **Betrieb / A11y / Test:** `--selftest` vorhanden; visueller A11y-Nachweis
  unbekannt.
- **Blaupause / Risiko / Zuordnung:** eine Adresse, Loopback-Start und
  lesbare Startfehler **übernehmen** → `shell`, `operations`; HTML-/JSON-API
  und direkte Schreibpfade **ersetzen** → typed gateway mit servergebundenem
  Kontext und Bestätigung.

### UI-004 — Brainlehr-Kommandoausgaben

- **Fundort / Technik / Start:** `brainlehr@melder/*.py`, `berichte/*.py` und
  `app/werkzeuge/*.py`; explizite Beispiele: `melder/wissensverlauf.py`,
  `melder/wirkkette.py`, `berichte/vorschlag.py`.
- **Status / Funktionen:** nutzerlesbare Terminalberichte und Werkzeuge,
  aber keine zusammenhängende TUI/kein Produkt-Renderer gefunden.
- **Verträge / Steuerung / Isolation:** variieren je Skript; keine globale
  LLM-, Session- oder A11y-Bauform nachgewiesen.
- **Betrieb / A11y / Test:** CLI-Argumentparser belegt; ein gemeinsamer
  Bedienungs- oder Testnachweis fehlt.
- **Blaupause / Risiko / Zuordnung:** fachliche Berichtstitel und
  Recovery-Texte **übernehmen** → `operations`, `knowledge`; Bedienform
  **ersetzen**, keine 1:1-Terminalemulation.

### UI-005 — Univer-Tabelle, Brainlehr-Spike

- **Fundort / Technik / Start:** `brainlehr@spikes/univer_i3_min/probe4/index.html`
  mit `serve_and_log.mjs`; gebündelte Dateien nur als generiert klassifiziert.
- **Status / Funktionen:** Tabellen-/Spreadsheet-Integrationsprobe, kein
  Produkt-Einstiegspunkt.
- **Verträge / Steuerung / Isolation / Betrieb:** Positivlisten- und
  Screenshot-Artefakte vorhanden; Auth, Kontextisolation, LLM-Steuerung,
  A11y und Produktmonitoring unbekannt.
- **Blaupause / Risiko / Zuordnung:** Erkenntnisse zu Tabellenintegration
  **spike-only** → späteres `tables`-Modul; keine UI-Übernahme.

### UI-006 — OpenLehr Steuer-Weboberfläche (Referenzstand)

- **Fundort / Technik / Start:** `openlehr_einzelunternehmer@apps/openlehr/daemon/static/steuer/`;
  statisches HTML/CSS/JS, vom Steuer-Daemon bedient. Erkennbar sind unter
  anderem Anmeldung, Assistent, Belege, Kennzahlen, Klärungen, Postfach,
  Rechnungen, Suche und Zahlungen.
- **Status / Funktionen:** realer großer Fachbildschirmbestand; für
  Brainlehr nur Legacy-/Vertragsblaupause.
- **Verträge / Steuerung / Isolation:** Primärvertrag
  `docs/openlehr/OPENLEHR_KERNEL_UND_APP_VERTRAG_V1.md` verlangt typisierte
  State-/Action-/View-/Event-Envelopes, servergebundenen Actor/Subject,
  Capability, CAS, Idempotenz und Confirmation; Quelle ist Vertrag, nicht
  Laufzeitnachweis. LLM darf danach Proposal, nicht Wirkung erzeugen.
- **Betrieb / A11y / Test:** gemeinsame JS-Helfer enthalten Sitzungswächter
  und Netzwerkhinweis; umfassende Browser-A11y-/E2E-Abnahme nicht geprüft.
- **Blaupause / Risiko / Zuordnung:** semantische Views, typisierte Actions,
  Bestätigung und Fehler-/Netzwerkzustände **übernehmen** → `domain-host`,
  `actions`, `operations`; Seiten und DOM-Code **ersetzen**.

### UI-007 — OpenLehr macOS-Shell (Referenzstand)

- **Fundort / Technik / Start:** `openlehr_einzelunternehmer@apps/openlehr/macshell/Package.swift`;
  SwiftUI-Paket `OpenLehrApp`, laut Manifest Build-Skeleton mit
  `swift build -c release`.
- **Status / Funktionen:** MenuBar-/Haupt-/Steuer-/Live-Monitor-/Debug-
  Fensterquellen vorhanden; kein fertiger Produktstatus behauptet.
- **Verträge / Steuerung / Isolation:** `OpenLehrCore` mit
  `StreamClient`, `UIState` und `DaemonConfig`; serverseitige Action-Grenze
  folgt dem in UI-006 genannten Vertrag. Konkrete Runtime-Absicherung im
  Inventarlauf nicht ausgeführt.
- **Betrieb / A11y / Test:** `A11y.swift`, `LiveMonitorWindow.swift` und zwei
  Testtargets im Package belegt; deren Lauf ist offen.
- **Blaupause / Risiko / Zuordnung:** Desktop-Wrapper, Live-Status und A11y
  **übernehmen** → späterer `mac-wrapper`; separaten Swift-Produkt-Renderer
  **verwerfen**.

### UI-008 — OpenLehr-Legacy-Arbeitsbaum

- **Fundort / Technik / Start:** `openlehr_legacy@apps/openlehr/daemon/static/steuer/`
  und `apps/openlehr/macshell/`; Revision `d5c24182`.
- **Status / Funktionen:** zweite vorhandene historische OpenLehr-
  Clientversion; gleiche Web-/macOS-Clientfamilie ist quellseitig vorhanden.
  Sie dient nur als Vergleichsversion, nicht als paralleles Ziel.
- **Verträge / Steuerung / Isolation / Betrieb:** gegenüber UI-006 im
  Inventarlauf kein belastbarer Funktionsdelta erhoben; daher unbekannt.
- **Blaupause / Risiko / Zuordnung:** nur für Regression-/Migrationvergleich
  **übernehmen** → `legacy-migration`; Renderer und Screens **ersetzen**.

### UI-009 — OpenLehr-Desktoparchiv

- **Fundort / Technik / Start:** `archive/openlehr_desktop_2026-07-28@`
  `apps/openlehr/daemon/static/steuer/` und `apps/openlehr/macshell/`;
  Revision `2ad1f7d82`.
- **Status / Funktionen:** dritte, datierte historische Clientversion.
  Der Archivbaum enthält zusätzlich `OpenLehrTextAdventureApp.swift` und
  `GameView.swift`; sie bilden eine weitere frühe Clientlinie, keine
  Brainlehr-/OpenLehr-Produktoberfläche.
- **Verträge / Steuerung / Isolation / Betrieb:** wegen Archivstatus nicht
  gestartet; genaue Differenzen, A11y und Tests unbekannt.
- **Blaupause / Risiko / Zuordnung:** Route-/Funktionvergleich
  **übernehmen** → `legacy-migration`; ansonsten **verwerfen**.

### UI-010 — OpenLehr-Nachrichten- und IDE-Adapter

- **Fundort / Technik / Start:** `openlehr_einzelunternehmer@apps/openlehr/channels/telegram.py`,
  `channels/whatsapp.py`, `channels/whatsapp_relay/relay.js` und
  `vscode-extension/`.
- **Status / Funktionen:** nutzerseitige Chat-/Editor-Einstiege, keine
  zentrale grafische Oberfläche; konkrete VS-Code-Aktivierung im Inventarlauf
  nicht ermittelt.
- **Verträge / Steuerung / Isolation:** unterliegen laut OpenLehr-Vertrag
  derselben Action-/State-Grenze; konkrete Adapter-Allowlist und Testbeleg
  sind hier unbekannt.
- **Betrieb / A11y / Test:** nur Quellpfade und Node-Manifeste belegt.
- **Blaupause / Risiko /Zuordnung:** Kanaladapteridee **übernehmen** →
  `integrations`; Chat- oder Editoroberfläche nicht in die zentrale WebUI
  kopieren, daher **ersetzen**.

### UI-011 — OpenLehr-macOS-Snapshot

- **Fundort / Technik / Start:** `openlehr_einzelunternehmer@`
  `apps/openlehr/macos/Sources/OpenLehr/OpenLehrApp.swift`; SwiftUI-
  Snapshot mit `MenuBarExtra`.
- **Status / Funktionen:** die zugehörige README nennt ihn
  UI-Review-Referenz; Kompilierung wurde dort nicht verifiziert. Quellseitig
  sind Chat, Memory, Tools, Settings, Logs und About sichtbar.
- **Verträge / Steuerung / Isolation / Betrieb:** `DaemonBridge` und
  Confirm-Token-Texte existieren; belastbarer Laufzeit- oder A11y-Nachweis
  ist unbekannt.
- **Blaupause / Risiko / Zuordnung:** nur Interaktionsmuster
  **spike-only** → `mac-wrapper`; kein eigener Renderer.

### UI-012 — früher extrahierter OpenLehr-Client

- **Fundort / Technik / Start:** `_repos/openlehr@OpenLehrTextAdventureApp.swift`,
  `GameView.swift`, `daemon/daemon.py`; Revision `46aaf92`.
- **Status / Funktionen:** SwiftUI-Textadventure plus Python-Daemon;
  `RacingGameTests.swift` liegt in derselben Linie. Kein Brainlehr-
  Produkt-UI-Bezug belegt.
- **Verträge / Steuerung / Isolation / Betrieb:** unbekannt, nicht gestartet.
- **Blaupause / Risiko / Zuordnung:** historische Clientlinie, **verwerfen**
  aus zentraler WebUI; nur für Herkunftsvergleich behalten.

### UI-013 — weitere gefundene sichtbare Artefakte

- **Fundort:** `openlehr_legacy@apps/{drg,einprozent_rechner,openhood,pflegelotse,wohlairr}/`,
  `begod/desktop/`, `begod/knowledge/media/ui/`, Landing-Pages und
  `infra/security/targets/`; entsprechende Dateien existieren auch im
  datierten OpenLehr-Desktoparchiv, teils im nicht auflösbaren
  `openlehr_stale_2026-07-22`-Arbeitsbaum.
- **Status / Zuordnung:** eigenständige Domänenprodukte, Landing-/Security-
  Targets oder generierte/Vendor-Inhalte; nicht Brainlehr/OpenLehr als
  Produkt-Renderer. **verwerfen** aus dem zentralen WebUI-Scope.
- **Gap:** kein vollständiger Funktionsinventar dieser fremden Domänen,
  absichtlich nicht als Brainlehr-Funktion behauptet.

## Fähigkeitsabdeckung

| Fähigkeit | Belegbare alte Quellen | Ziel-WebUI-Modul | Gate |
|---|---|---|---|
| Shell, Navigation, Rückweg, Servicefehler | UI-001, UI-003, UI-007 | `shell`, `operations` | Vertikaldurchstich |
| Wissenssuche/-ansichten und Graphen | UI-001, UI-002, UI-003, UI-004 | `knowledge`, `graph` | Vertikaldurchstich |
| Domänenbildschirm und Fachaktionen | UI-001, UI-006 | `domain-host`, `actions` | typed Action/View-E2E |
| Identität, Einladungen, sensible Writes | UI-001, UI-003, UI-006 | `identity`, `actions` | Negativ-/Bestätigungstest |
| Tabellen-/Formularmuster | UI-005, UI-006 | `tables`, `forms` | nur nach Produktbedarf |
| Live-Status, Netz- und Recovery-Meldungen | UI-001, UI-003, UI-006, UI-007 | `operations` | Wiederverbindung/Fehlerlauf |
| Mac-spezifische Funktionen | UI-001, UI-007 | `mac-wrapper` | erst nach WebUI-Gate |
| Fremdkanäle (Chat/IDE) | UI-010 | `integrations` | separates Adapter-Gate |

Jede Zeile ist ein Mapping-Vorschlag, keine migrierte Funktion. Die
vollständige Zuordnung je Route, Import und Funktion bleibt Teil des noch
offenen BDW-R03-Legacy-Gates.

## Menge B/C — Backend ohne sichtbare UI und beschlossene Wahlpunkte ohne UI

Diese zweite Matrix verhindert den Fehlschluss „nicht in einer alten Ansicht =
nicht Teil des Produkts". **B** bedeutet: Code/Vertrag vorhanden, keine
zentrale WebUI belegt. **C** bedeutet: Entscheidung ist bindend oder vertagt,
aber die zugehörige Nutzer-/Adminoberfläche fehlt. `unbekannt` ist kein
Negativbefund.

| ID | Menge, Quelle und heutiger Stand | Wer entscheidet / wann | Sicherheitsgrenze und Ziel-WebUI-Modul / Phase |
|---|---|---|---|
| GAP-UI-001 | **B+C** Ausweis: `kern/ausweis.py`, MCP-Werkzeuge `knowledge_anmelden`, Ausweis-Anlegen/-Einladen; native UI-001/3 zeigt Teilwege, zentrale WebUI fehlt. Widerruf ist laut ADR-017 noch als UI-/Laufzeitnachweis offen. | Betreiber/Admin erzeugt, lädt ein oder widerruft; die Person weist sich im geprüften Vorgang aus. | Geheimnis nie speichern/anzeigen oder über Chat/LLM entgegennehmen; Identitätsstatus/Ablehnungsgrund sichtbar, Rechte/Widerruf serverseitig. → `identity`; zuerst anmelden/gesperrt, Adminverwaltung später. |
| GAP-UI-002 | **B+C** Betriebsprofil: `BDW-P09`, `BDW-C02`, `docs/PLAN_BETRIEBSPROFILE_2026-08-20.md`; Schema-/Wechseltests existieren, keine Web-Auswahl. | Nutzer vor Installation: `standalone`/`multiuser`; Wechsel erst später. | Mandantenachse vor Wechsel, kein zweiter Bestand. → `onboarding`, `settings`; standalone V1, multiuser erst Pilot. |
| GAP-UI-003 | **B+C** Erststart: `BDW-P11`, `kern/einrichtung.py`; Chat-Werkzeug fragt Profil, Sprache, Einbettungsdienst und Kataloge. | Nutzer beim Erststart; gewachsener Bestand nur explizit bestätigen. | Katalogimport getrennt vom Arbeitsbestand; keine stillen Änderungen. → `onboarding`; bestehende Chat-Bauform ist V1-Referenz, Web-Ansicht noch offen. |
| GAP-UI-004 | **B+C** Projekt-/Worktree-Kontext: `knowledge_mcp_server.py::project_attach`, `project_detach`, `project_context_get`; `BDW-P72`, `P75`, `P78`, `P92`. | Nutzer/Agent wählt Projekt und Aufgabe; System erzwingt Lease, Revision und Scope. | Kein fremder/absoluter/untracked Inhalt; Kontext nur servergebunden. → `project-context`, `worktree`; nach Kern-Vertikaldurchstich. |
| GAP-UI-005 | **C** IdP/SSO/SCIM: `BDW-E01`, `E04`, `E05`. | Enterprise-Admin, erst realer Mehrbenutzer-/Enterprise-Pilot. | Externe Subjekt-ID, Deprovisioning, Login/Logout; kein erfundener IdP. → `enterprise-iam`; **DEFERRED BDW-C03**. |
| GAP-UI-006 | **B+C** Rolle/Objekt/Zweck/Kreis: `BDW-E02`, `E03`, `E06`, `E22`, `E23`; RBAC-/Kreisgrundlagen und Negativtests existieren, zentrale Rechteansicht nicht. | Admin vergibt Rollen/Policy; Nutzer wählt weder Rolle noch Zweckgrenze frei. | Default-deny, Tenant-/Kreis-/Zweckprojektion, keine Trefferzahl-Lecks. → `identity`, `policy`; Enterprise-Teile **DEFERRED BDW-C03**. |
| GAP-UI-007 | **C** Transport, Region, DLP und SIEM: `BDW-E08`, `E11`, `E19`, `E20`, `U02`, `U05`, `U08`. | Betreiber je Profil; Admin je Export/Policy; Nutzer sieht Erklärung, überschreibt nicht. | Remote nur vertraulich/authentisiert; Export minimiert/default-deny. → `security`, `export`, `audit`; **DEFERRED BDW-C03**. |
| GAP-UI-008 | **B+C** Modell-/Providerwahl: `BDW-U07`, `U08`, `F09`; lokale Privacy-Projektion ist belegt, Org-Allowlist und sichtbarer Konfliktweg fehlen. | Organisation setzt Allowlist, Nutzer wählt nur daraus. | Kein nicht freigegebener Provider erhält Daten; Org-Grenze gewinnt. → `models`, `policy`; **DEFERRED BDW-C03**. |
| GAP-UI-009 | **B+C** Einbettungsmodell: `docs/PLAN_EINBETTUNGSVARIANTEN_2026-08-16.md`, `kern/build_embeddings.py`, `melder/vektorstand.py`. Kanalgesundheit und Modellwechsel-/Rebuild-Gate sind belegt, keine UI zum Modellstand/Reindex. | System stellt Stale/Differenz fest; Betreiber autorisiert einen sichtbaren Reindex-Job, nicht einen freien Modellwechsel im Browser. | Modell im laufenden Bestand read-only; Digest/Dimension/Smoke vor Reuse, kein Blind-Pull. → `models`, `operations`; nach V1-Vertikaldurchstich. |
| GAP-UI-010 | **B+C** Domänenmitstart: ADR-023, `app/Sources/Atelier/DienstAufsicht.swift`, `BDW-R03`. Native Schalter-/Aufsicht vorhanden, Web-Gegenstück nicht. | Nutzer/Betreiber aktiviert eine Domäne; System überwacht Start/Fehler. | Domänenprozess und Basis-URL nicht aus Browsertext. → `domain-host`, `operations`; erst nach typed Gateway. |
| GAP-UI-011 | **B+C** Dokumentablage: `BDW-P15`, ADR-032, `kern/dokumentenablage.py`; `ablage.<domaene>` ist eine Einstellung, UI fehlt. | Nutzer/Data Owner je Domäne wählt `domaene` oder `brainlehr`. | Prüfsumme immer, Datei nicht im Volltextindex. → `documents`, `settings`; nur wenn Dokumentmodul in V1. |
| GAP-UI-012 | **B+C** Sprache, Dichte, A11y: `BDW-P10`, `P19`, ADR-004, ADR-033. Sprachmetadaten und native Labels existieren, zentrale Umschaltung/Prüfung fehlt. | Nutzer wählt Sprache, dichte Darstellung oder Bewegung im zulässigen Rahmen; Betreiber entscheidet keine erzwungene Übersetzung. | AA ist Vorgabe; Namen, Tastatur, Fokus, Kontrast und Rückweg bleiben invariant. → `settings`, `accessibility`; Grundbedienbarkeit im Vertikaldurchstich. |
| GAP-UI-013 | **B+C** Plugin-Lebenszyklus: ADR-013/026, `app/Sources/BrainlehrCore/BestandteilRegistry.swift`, `BDW-P89`. Semantische Fach-/Action-Pakete sind vorgesehen; zentrale Enable-/Permission-/Update-Fläche fehlt. | Admin/Betreiber aktiviert signierte/registrierte Beiträge; Nutzer startet keinen beliebigen Code. | Closed renderer, Manifest/Capability/Version/Isolation. → `plugins`, `policy`; nach Kernvertrag, kein V1-Vorbau. |
| GAP-UI-014 | **B+C** Sicherung, Restore, Schlüssel und Export: `BDW-E07`, `E09`, `E12`–`E16`, `F07`, `kern/sicherungen.py`. Einzelwege sind belegt, Operatoroberfläche fehlt. | Betreiber/Data Owner konfiguriert Ort/Schlüssel/Hold; System läuft Frist/Backup; Nutzer beantragt Export. | Schlüssel getrennt, Restore isoliert, Hold vor Vernichtung, Portabilität atomar. → `operations`, `security`, `export`; Backup-Medium/offline laut E15 noch Lücke. |
| GAP-UI-015 | **B+C** Vertrauens-/Autonomiemodus: `BDW-R04`, `BDW-U01`, `kern/vertrauen.py`. Regler begrenzt Rückfragen, keine produktive zentrale UI. | Nutzer darf absenken; Organisation setzt später Obergrenze. | Belegpflicht/harte Stopps unveränderlich; keine LLM-Selbstfreigabe. → `trust`, `policy`; Nutzerregler im Vertikaldurchstich, Org-Obergrenze **DEFERRED BDW-C03**. |
| GAP-UI-016 | **C** Persönlich/Firma und Benachrichtigung: `BDW-U03`, `U06`. Ereignisrouting existiert, Sichttrennung/Freigabeoberfläche fehlt. | Nutzer wählt zulässige Kanäle; Admin/Policy steuert Übergang persönlich→Firma. | Explizite Freigabe, Meldung ohne Inhaltsleck. → `notifications`, `policy`; Sichttrennung **DEFERRED BDW-C03**. |
| GAP-UI-017 | **C** Weitere Betriebsprofile und SLO: `BDW-E17`, `E21`. Kein Cloud-/Hybridprofil festgelegt. | Betreiber entscheidet erst bei Aktivierung eines weiteren Profils. | Datenfluss, Residenz, SLO und Restore vorher festlegen/testen. → `deployment`, `operations`; **DEFERRED, nicht implizit bauen**. |
| GAP-UI-018 | **C** Risikofreigaben/Vier-Augen: `BDW-E18`. Matrix ist belegt, keine zentrale Freigabeansicht. | Policy klassifiziert; autorisierte Person bestätigt nur hohe Risiken. | Zweck/Ziel/Klassifikation/Audit vor Wirkung. → `actions`, `approvals`; erst mit echter Wirkung, nicht als leere UI. |
| GAP-UI-019 | **B+C** Zweiter Faktor und Zugriffsmuster: `BDW-E24`, `BDW-E25`, `melder/zugriffsmuster.py`. Mustererkennung ist belegt; zweiter Faktor ist ausdrücklich FUTURE, und keine WebUI zeigt den Status oder eine spätere Wahl. | Betreiber entscheidet erst, wenn der Bestand auf einem nicht selbst verwahrten Gerät liegt; System meldet auffällige Lesemuster. | Kein TOTP als behaupteter Bestandsschutz; Verlust-Rückweg wäre eine Hintertür. → `security`, `operations`; E24 nicht vorziehen, E25 nur nachvollziehbare Statusanzeige. |
| GAP-UI-020 | **C** Herkunft eines Eingriffs: `BDW-P104`, Betreiberkorrektur und Lehre `L-b4d50b`; bisher keine zentrale Darstellung, die Auslöser unterscheidet. | System zeigt vor einer Wirkung den tatsächlichen Auslöser; Betreiber korrigiert nachträgliche Einträge sichtbar als solche. | `BRAINLEHR VERHINDERT` nur bei realem Pre-Action-Hook, Gate oder Server-Denial; sonst `recalled`, `warned`, `recorded-after-operator` oder `recorded-after-test`. → `provenance`, `actions`; Pflicht des Vertikaldurchstichs. |
| GAP-UI-021 | **B+C** Connector-Allowlist: `BDW-U04`, `tests/test_connector_register.py`; Direktaufruf wird bereits abgewiesen, die vorhandene `_erlaubt: set[str]`-Liste ist aber nicht persistent und hat keine Adminoberfläche. | Organisation/Admin pflegt die Allowlist; Nutzer wählt nur daraus. | Nicht gelisteter Connector startet auch per Direktaufruf nicht; keine freie URL-/Code-Eingabe. → `integrations`, `policy`; Administration erst mit Mehrbenutzer-/Org-Gate. |

### Unaufgelöste Extraktion

Die Durchsuchung verwendete die Begriffe `Betreiber`, `Nutzer`, `entschei`,
`later`, `deferred`, `pilot`, `Einstellung`, `Schalter`, `Auswahl` und
`Vorgabe` über Root-Katalog, ADRs, Pläne und die benannten Kernmodule. Sie
ergab die oben aufgelisteten C-Gruppen einschließlich der noch nicht fälligen
E24-Wahl; **nicht** als UI-Obligation gezählt
wurden interne Messparameter, Testschalter, historische Bedienoberflächen,
oder Entscheidungen ohne menschliche Bedienhandlung. Eine Zeile, die nur
eine verborgene technische Konfiguration nennt, ist bewusst nicht als
Nutzerwahl ausgegeben. Die unten angehängte Routen-/Kontrollmatrix schließt
die quellseitige Liste; Laufzeit-, A11y- und Felderprobung bleibt dort, wo
nicht nachgewiesen, ausdrücklich offen und darf vor Ablage alter Clients
nicht still als komplett gelten.

Die im Katalog ausdrücklich aufgeschobenen Gruppen sind abgedeckt:
`BDW-E01/E04/E05` (GAP-UI-005), `E03/E06/E22/E23` (006),
`E08/E11/E19/E20` (007), `E17/E21` (017), `E24/E25` (019) sowie
`BDW-U01` (015), `U02/U05/U08` (007), `U03` (016) und `U07` (008).
`U04` ist als vorhandene, aber nicht persistente Connector-Allowlist in
GAP-UI-021 geführt, nicht als scheinbare „erledigt“-Markierung.

## Vollständigkeits- und Suchprotokoll

| Wurzel | Revision bei Sichtung | Zustand |
|---|---:|---|
| `brainlehr` | `640ceca7` | 179 geänderte/untracked Pfade |
| `atelier` | `e4cbd230` | 2 geänderte/untracked Pfade |
| `openlehr_einzelunternehmer` | `7bfb3cc` | 23 geänderte/untracked Pfade |
| `openlehr_legacy` | `d5c24182` | 37 geänderte/untracked Pfade |
| `archive/openlehr_desktop_2026-07-28` | `2ad1f7d82` | 1 untracked Pfad |
| `openlehr_stale_2026-07-22` | unbekannt | `.git` verweist auf fehlenden Worktree-Adminpfad |
| `_repos/openlehr` | `46aaf92` | nur `OpenLehrTextAdventureApp.swift` auf flacher Suche; kein weiterer Client belegt |

Gesucht wurden bis Tiefe fünf nach Git-Wurzeln, `Package.swift`,
`package.json`, `index.html`, SwiftUI/WebView-/HTTP-Entrypoints sowie
`main.*`/`App.*`. Ausgeschlossen wurden `node_modules`, `build`, `dist`,
`generated` und Vendor-Bäume, außer um ihre Existenz als Spike-/Fremdartfakt
zu klassifizieren. Nicht gelesen wurden Datenbanken, Nutzerdaten,
Geheimnisse, Anhänge oder Agenten-Historien.

**Offene Wurzeln/Gaps:** mögliche weitere Worktrees außerhalb der flachen
Suche; der unauflösbare Stale-Worktree; detaillierte Route-/A11y-/Runtime-
Inventare der OpenLehr-Webclients. Diese Gaps sind vor einer Legacy-Ablage
aufzulösen, nicht durch Annahmen zu schließen.

## Routen- und Kontrollanhang

**Nicht normativ, Quelle vor Ziel.** Die Kennungen sind stabil für dieses
Inventar; sie behaupten keine bereits migrierte WebUI-Route. Methoden und
Kontrollfelder stammen aus den jeweils genannten Quelldateien. Nicht
aufgeführte Parameter bleiben unbekannt.

### UI-001/002 — Atelier-Navigation und Debug-Steuerung

| ID | Sichtbarer Einstieg / Kontrolle | Belegter Inhalt oder Eingabe | Zuordnung |
|---|---|---|---|
| UI-001-R01 | Sidebar `HauptFenster.swift` | Quellen, Mehrfachansicht, Bearbeiten, Dokument, Sitzung, Wissensraum, Landkarten, Domäne, Ausweise | `shell`, `knowledge`, `documents`, `identity`; ersetzen, kein Swift-Renderer |
| UI-001-R02 | `Steuerschnittstelle.swift` | nur `#if DEBUG`, nur nach `BRAINLEHR_STEUERUNG=<port>`, `127.0.0.1`; tatsächlicher Port wird gemeldet | Debug-Blaupause, nie produktiver Netz-/LLM-Zugang |
| UI-001-R03 | `GET /zustand` | gesamter Steuerzustand | typed State übernehmen |
| UI-001-R04 | `GET /gesundheit` | Liveness | Operations übernehmen |
| UI-001-R05 | `POST /ansicht` | erlaubte Ansicht | typed View ersetzen |
| UI-001-R06 | `POST /blick` | erlaubter Blick | typed View ersetzen |
| UI-001-R07 | `POST /dokument` | verbinden/trennen/schreiben/einfügen; Nicht-Loopback-WebSocket wird abgewiesen | Documents: Auth/Bestätigung ergänzen |
| UI-001-R08 | `POST /zeit` | `{versatz:N}` | Testhilfe, nicht V1-Bedienung |
| UI-001-R09 | `POST /mitstart` | `{domaene,ein}`; nur bekannte Domäne | `domain-host`, typed Gateway |
| UI-001-R10 | `POST /neuladen` | Neuladezähler | Operations übernehmen |
| UI-001-R11 | `POST /bildschirm` / `GET /bildschirme` | Nummer bzw. Verzeichnis mit Titel/Gruppe | sichtbare Navigation übernehmen |
| UI-001-R12 | `POST /suche` | Suchbegriff | `knowledge` ersetzen |
| UI-001-R13 | `GET /inhalt` | gezeichneter sichtbarer Inhalt | Renderer-Inspektion, kein WebUI-Vertrag |
| UI-001-R14 | `POST /regler` | `{id,wert}` gegen Kernliste und Wertebereich | `settings`; validierte Controls übernehmen |
| UI-001-R15 | `POST /auswahl` | `{id,wert}` gegen bekannte Auswahlwerte | `settings`; validierte Controls übernehmen |
| UI-001-R16 | `POST /aktion` | sichtbarer Name/Titel plus Formularfelder; nur erlaubte Aktion | `actions`; Confirm/Auth ergänzen |
| UI-001-R17 | `GET /verwerfungen` | verworfene Ladevorgänge | `operations` übernehmen |

`Steuerbefehl.swift` enthält **16 HTTP-Pfade** und 18 Command-Varianten
(` /dokument` hat mehrere Varianten), nicht 17 Pfade. `SteuerbefehlTests.swift`
belegt Methoden-/Feldfehler, sichtbare Aktionsnamen und die 403-Ablehnung
`gesperrteAktionen` („nur ein Mensch“). Viewwechsel und `/aktion` warten auf
die tatsächliche Wirkung; das vermeidet alte/stale Screens bzw. eine vorzeitig
als erfolgreich erscheinende Aktion. Diese Semantik ist übernehmbar, der
Debug-Listener selbst wird ersetzt.

| ID | Teilrenderer | Sichtbare Funktion / geprüfter Kontrollweg | Grenze |
|---|---|---|---|
| UI-002-R01 | `WissensraumWebView.swift` | Wissensraum gegen lokalen Dienst; injiziertes Script/DOM-Klick | durch versionierten State/View/Action-Vertrag ersetzen |
| UI-002-R02 | `LandkartenAnsicht.swift` | Landkarte als eigener Teilrenderer | Graph-Modul übernehmen, WebView nicht |

### UI-003 — lokale Entscheidungsoberfläche

| ID | Methode und Route | Sichtbare Funktion / Eingabe | Grenze |
|---|---|---|---|
| UI-003-R01 | GET `/`, `/entscheidungen.html` | Startseite; `/raum*` und `/vergleich*` leiten hierher um | historische Betreiberfläche |
| UI-003-R02 | GET `/landkarten`, `/api/landkarten`, `/api/landkarte?k=` | Karte, Kartenliste, Kennung (Regex-begrenzt) | Anzeige, kein Datei-Pfad aus Browser |
| UI-003-R03 | GET `/api/stand`, `/api/raum`, `/api/vergleich`, `/api/echtkorpus` | Stand-/Vergleichs-/Korpusansicht | Laufzeitinhalt nicht neu nachberechnet |
| UI-003-R04 | GET `/api/quellenbestand`, `/api/quellenliste`, `/eintrag/<id>` | Quellen/Eintrag; Eintrag nur lokal | Loopback-Prüfung |
| UI-003-R05 | GET `/api/modellzugaenge`, `/api/domaenen`, `/api/domaene-dienst?domaene=`, `/api/domaene-oberflaeche?domaene=` | Modell-/Domänenstatus | Status, nicht zentrale Produkt-API |
| UI-003-R06 | GET `/api/ausweisliste` | Ausweisübersicht | Geheimnis bleibt unsichtbar |
| UI-003-R07 | POST `/api/texterkennung`, `/api/abrufweg`, `/api/fundstelle` | JSON-Eingabe für Text, Abruf, Fundstelle | Origin-Prüfung; Header-Ausnahme je Quelle |
| UI-003-R08 | POST `/api/eskalation`, `/api/eilmeldung`, `/api/siegbedingung`, `/api/nachtschicht` | JSON-Aktion/Quittierung/Parameter | legacy write path, ersetzen |
| UI-003-R09 | POST `/api/domaene-import`, `-entfernen`, `-importe` | Domänen-Paket | Origin plus gültiger Bearer-Ausweis |
| UI-003-R10 | POST `/api/ausweis-anlegen`, `-widerrufen`, `-entwiderrufen`, `-verlaengern`, `-einladen` | Ausweis-JSON | Origin-Prüfung ist laut Quelle Übergang; kein zentraler IAM-Ersatz |

`/statisch/mermaid.min.js` ist Auslieferungsasset, keine Produktroute. Alle
POST-Schreibwege verlangen lokale Origin und (außer expliziter Quell-Allowlist)
gültigen Bearer-Ausweis; das ist Blaupause, nicht ausreichend belegte
produktive Session-/CSRF-Grenze.

### UI-006 — OpenLehr Steuer: vollständiger statischer Seitenbestand

Der aktuelle Baum enthält **19** `index.html`, **38** JS-Dateien und **91**
getrackte Dateien. Jede sichtbare Seite ist genau einmal aufgeführt; die
Shared-Module folgen danach. Die API-Spalte nennt aus dem Seitenskript
extrahierte, tatsächlich aufgerufene Präfixe/Operationen, nicht erfundene
Backend-Abdeckung.

| ID | Seite/Modul | Sichtbarer Zweck | JS-API/Operationen |
|---|---|---|---|
| UI-006-R01 | `anlagegueter/index.html` | Anlagegüter | GET Jahr; POST Asset/Ausscheiden: `/v1/steuer/aveuer/*` |
| UI-006-R02 | `anmelden/index.html` | Anmeldung/Bootstrap | POST select_user, demo enter, bootstrap, logout; UI-Prefs/Capabilities |
| UI-006-R03 | `anzahlungen/index.html` | Anzahlungen | GET Eingänge/Rechnung/Jahr; POST Zuordnen |
| UI-006-R04 | `assistent/index.html` | Steuerassistent | Sitzungen/Nachrichten; Vorschläge; Draft-Accept |
| UI-006-R05 | `belegansicht/index.html` | einzelner Beleg | `/v1/steuer/documents/:ref/*` |
| UI-006-R06 | `belege/index.html` | Belegliste/OCR | documents/summary, preview, discard/restore/classify, PATCH OCR-review |
| UI-006-R07 | `firmendaten/index.html` | Firma/Profil | GET/POST settings/backoffice und profile |
| UI-006-R08 | `jahr/index.html` | Jahres-Workflow | worksheet, export, EÜR-Zuordnung, workflow/year(s) |
| UI-006-R09 | `kennzahlen/index.html` | Kennzahlen | `/v1/steuer/kennzahlen/*`, homeoffice/pauschale |
| UI-006-R10 | `klaerungen/index.html` | Klärungen | clarifications, documents/discard, Resolve |
| UI-006-R11 | `mailansicht/index.html` | Mail ansehen | `/v1/steuer/mail/messages/:id` |
| UI-006-R12 | `ordner/index.html` | Eingang/Import | import/beleg, belege, capture reserve, workflow intake/sort |
| UI-006-R13 | `passwort/index.html` | Passwort zurücksetzen | `/v1/users/:*` |
| UI-006-R14 | `postfach/index.html` | Mail-Autopilot | autopilot mail-accounts/status/schedule/run |
| UI-006-R15 | `rechnungen/index.html` | Rechnungsentwürfe | invoice drafts/preview/from-offer, offers, contacts |
| UI-006-R16 | `stammdaten/index.html` | Kontakte | GET/POST/PUT backoffice/contacts |
| UI-006-R17 | `suche/index.html` | ähnliche Suche | GET `/v1/steuer/similar` |
| UI-006-R18 | `vorsorge/index.html` | Vorsorgeaufwendungen | private/year, entries, confirm; profile |
| UI-006-R19 | `zahlungen/index.html` | CSV/Matching | POST import/csv, workflow/match |

| ID | Shared-Modul / belegte Grenze | Nachweis |
|---|---|---|
| UI-006-R20 | `gemeinsam/api.js`, `sitzungswaechter.js`, `netzwerkhinweis.js`, `mitSperre.js` | Fetch-Helfer, Sessionwächter, Netzstatus, Doppelklicksperre |
| UI-006-R21 | `formular.js`, `tabelle.js`, `liste.js`, `detail_karte.js`, `dokument_vorschau.js`, `dokumentziel.js`, `meldung.js`, `navigation.js` | gemeinsame Anzeige-/Formularmodule |
| UI-006-R22 | HTML-A11y | `aria-labelledby`, `role=status`, `aria-live`, tastatur-scrollbare Tabellenbereiche |

### UI-007/010/011 und historische Linien

| ID | Quelle | Belegter Einstieg / Wirkung | Disposition |
|---|---|---|---|
| UI-007-R01 | macshell `OpenLehrApp.swift`, `MainWindow.swift` | MenuBarExtra und WindowGroup; Tabs Chat, System, IDE, Konsile, Settings, Stiftshütte | späterer Wrapper/Operations, kein zweiter Renderer |
| UI-007-R02 | `SteuerWindow.swift` | neun Panes Status, Belege, Telegram, CSV, Klärungen, Export, Mail, Autonomy, Audit; `/v1/steuer/*` mit user auth grant | Fach-Blueprint, ersetzen |
| UI-007-R03 | `StreamClient.swift`, `LiveMonitor*` | SSE via `URLSession.bytes(for:)`; Debug Events `/v1/debug/events`; Monitor erkennt Code-Write-Ziele | Monitoring-Blaupause |
| UI-010-R01 | Telegram/WhatsApp/Relay/VS-Code | Chat-/Editoradapter; konkrete Produktaktivierung nicht ausgeführt | Integrationsvertrag, keine UI kopieren |
| UI-011-R01 | macOS Snapshot | Skeleton: Chat, Memory, Tools, Settings, Logs, About; `DaemonBridge` POST `/v1/chat/completions`, SSE | spike-only |
| UI-008-R01 | `openlehr_legacy` vs. current | beide 19 HTML/91 statische Dateien; kein belastbares Funktionsdelta im Bounded-Scan | nur Vergleich, unbekannte Deltas offen |
| UI-009-R01 | Desktoparchiv | 1 HTML/16 statische Dateien; nicht mit vollem Steuerbaum vergleichbar | archiviert, nicht raten |
| UI-012-R01 | `_repos/openlehr` | Textadventure + Python-Daemon, keine vergleichbare Steueroberfläche | verwerfen |

Der Stale-Worktree bleibt terminal: `.git` verweist auf fehlende
Worktree-Administration. Keine Datei oder Historie wurde dafür rekonstruiert.

### GAP-UI — vorhandene Eingänge oder ehrliches „nicht gebaut“

| ID | Vorhandener Einstieg / nötige Felder | Zentral-WebUI-Status |
|---|---|---|
| GAP-UI-001 | `kern/ausweis.py --anlegen NAME --art --rollen`, `--einladen NAME --fuer`, `--widerrufen NAME`; MCP `knowledge_anmelden(pin)` | keine zentrale Eingabe; Geheimnis nie Chat/LLM |
| GAP-UI-002 | kein UI-Einstieg belegt | Profilwahl/Wechsel nicht gebaut |
| GAP-UI-003 | MCP `einrichtung_starten(profil,sprache,kataloge,mandant,bestaetigt)`; CLI `kern/einrichtung.py --lage` | Onboarding nicht gebaut |
| GAP-UI-004 | MCP `project_attach(project_root)`, `project_detach`, `project_context_get` | Worktree-Kontrolle nicht gebaut |
| GAP-UI-005 | kein IdP/SSO/SCIM-Einstieg | DEFERRED bis Pilot |
| GAP-UI-006 | kein zentraler Rollen-/Kreis-Eingang | Rechteansicht nicht gebaut |
| GAP-UI-007 | kein DLP/SIEM/Region-Eingang | DEFERRED bis Pilot |
| GAP-UI-008 | kein Provider-Allowlist-Eingang | DEFERRED bis Pilot |
| GAP-UI-009 | `kern/build_embeddings.py [--force]`, `melder/vektorstand.py` | Modellstatus/Reindex-UI nicht gebaut |
| GAP-UI-010 | Debug `POST /mitstart {domaene,ein}` | produktiver Domänenschalter nicht gebaut |
| GAP-UI-011 | `kern/dokumentenablage.py --ort DOMAENE --setzen {domaene,brainlehr}` | Settings-UI nicht gebaut |
| GAP-UI-012 | keine zentrale Preference-Route | Sprache/Dichte/A11y-UI nicht gebaut |
| GAP-UI-013 | keine Plugin-Enable-/Permission-/Update-Route | nicht gebaut |
| GAP-UI-014 | `kern/sicherungen.py --tagessicherung`; Restore-/Export-Controls nicht zentral belegt | nicht gebaut |
| GAP-UI-015 | `kern/vertrauen.py`-Regelwerk, kein zentraler Eingabepfad belegt | nicht gebaut |
| GAP-UI-016 | `kern/risikoeinstufung.py`-Routing, keine Sichttrennung-UI belegt | DEFERRED/teilweise |
| GAP-UI-017 | kein Cloud-/Hybrid-Profil-Eingang | DEFERRED |
| GAP-UI-018 | keine zentrale Freigabe-Route | erst mit echter Wirkung |
| GAP-UI-019 | `melder/zugriffsmuster.py --selftest`; E24 kein Bedienweg | E24 FUTURE, E25 Status nicht gebaut |
| GAP-UI-020 | kein Vorwirkungs-Provenienz-Eingang | not built; Labels nur mit realem Gate |
| GAP-UI-021 | Connector-Register-Test, keine persistente Verwaltungsroute | Administration nicht gebaut |

**Reproduzierbarkeit:** Seiten: `find apps/openlehr/daemon/static/steuer -name
'index.html'`; Skripte: derselbe Befehl mit `-name '*.js'`; API-Strings:
`rg -n 'fetch\\(|/v1/' apps/openlehr/daemon/static/steuer -g '*.js'`; Atelier:
`Steuerdeutung.bekanntePfade` in `app/Sources/BrainlehrCore/Steuerbefehl.swift`.
Diese Befehle lesen nur Quelltext; sie starten keine UI und enthalten keine
Geheimnisse.
