# Persona-Walkthrough — Abnahme 2026-08-15T11:49:36+0200

Prüfung, nicht Bau. Nach ux-walkthrough-Pyramide: nur Ebene 1 (Text-/Codeprüfung
+ vorhandene Tests laufen lassen). Kein Browser-, kein Simulator-Klickdurchgang
gefahren — für die geprüften Fragen (Text, Labels, Rückwege, Fehlerpfade)
beantwortet die Textebene sie vollständig; ein Bildschirmfoto hätte nur
Layout/Kontrast zusätzlich gezeigt, danach war nicht gefragt.

Ein grüner automatischer Testlauf ist an keiner Stelle unten als "geprüft am
Bildschirm" verkauft — wo ein Test lief, steht das Kommando und das Ergebnis.

## Gegenstand 1 — entscheidungen.html (Commit ee4645a)

**Befund SICHER, mit Beleg:** `escHtml()` (Zeile 432) ist an allen sechs
Stellen angewandt, an denen fremder Bestandstext per `innerHTML` in die Seite
geht — geprüft per `grep -n "escHtml\|innerHTML" entscheidungen.html`:
Zeile 1431 (Anfragetext des Nutzers selbst), 1531–1533 (Abrufweg-Tooltip:
Titel, Zusatztext, Ausscheidungsgrund, Pfad) und 1550–1552 (Baum-Tooltip:
Titel, Typtext, Pfad, Datum). Alle anderen `.innerHTML`-Zuweisungen im File
setzen entweder auf `''` (Leeren vor Neuaufbau) oder auf einen fest im Skript
stehenden, nicht aus dem Bestand stammenden Text (Zeile 1596 „Fuß"-Erklärung).

Rot-vor-Grün am Code selbst nachgefahren, nicht nur der Commit-Nachricht
geglaubt:

```
python3 -m pytest tests/test_entscheidungen_tooltip_escaping.py -q
→ 23 passed (einschl. der 16 Escaping-Fälle aus O1)
```

**Ein Zahlenwert bleibt unescaped:** `p.h` (Zeile 1551, Anzahl Auslieferungen)
— das ist eine Zahl aus `/api/raum`, keine freie Zeichenkette, insofern kein
Fund. Genannt, damit es nicht wie eine übersehene Stelle aussieht.

**VERMUTET (nur im Rendering entscheidbar):** Der Tooltip (`.fahne`) selbst
erscheint nur bei `pointermove` — kein Tastaturweg zu seinem Inhalt, keine
`aria-live`-Kopplung. Das ist keine Änderung von heute (die ganze
Zeichenfläche ist laut Kopftext „reine Anzeige"), gehört aber in die
Abnahme, weil WCAG 2.2 AA es verlangt: Bedeutung, die nur per Maus-Hover
erreichbar ist, hat keinen Tastaturersatz. Nicht am Text entscheidbar, ob
das die einzige Zugangsmöglichkeit zu diesen Werten ist oder ob die Karten
unten (Abschnitt 1–8) dieselben Fakten redundant zeigen.

**Screen-Trap-Check:** `#klapper` liegt außerhalb `.tafel` und ist immer
sichtbar (Zeile 224) — Rückweg aus dem eingeklappten Zustand vorhanden, laut
eigenem Kommentar im CSS (Zeile 79) bewusst so gebaut.

**Entwickler-Wording-Leak, geringe Priorität:** Der „Fuß"-Text (Zeile
1596–1610) erklärt dem Betrachter unter anderem „572 Treffer im
Abrufprotokoll zeigen auf Pfade, die es seit der Pfadsäuberung nicht mehr
gibt". Das benennt eine interne Wartungsmaßnahme („Pfadsäuberung") im
sichtbaren Text. Eingeordnet als **niedrige Priorität, nicht als Fund im
Sinn der Hausregel**: diese Seite ist ein Werkzeug für den Betreiber selbst
(Wissensraum-Visualisierung mit Reglern für Pulsdauer, Kosinus-Werte,
Varianzanteile), keine Oberfläche für einen fachfremden Endnutzer — die
Erklärung ordnet hier eine Zahl ein, verrät kein Geheimnis, keinen Fehlertext,
keine Zeile/Datei. Bei einer Ausweitung dieser Seite an einen anderen
Personenkreis wäre das neu zu bewerten.

## Gegenstand 2 — app/ (Sandbox, Ausweis-Weg, Bestandteile)

**Sandbox (e184c6a6):** `app/Resources/atelier.entitlements` enthält
ausschließlich `app-sandbox` und `network.client` — gelesen, keine weiteren
Rechte. Deckt sich mit der Commit-Aussage „bewusst minimal".

**Ausweis-Weg (1a9fb0df):** `AusweisDienst.swift` ruft ausschließlich
`URLSession` gegen `127.0.0.1:<DienstAufsicht.port>` auf, kein
`Foundation.Process` mehr. Fehlertexte sind durchgehend Nutzersprache
(„Das hat gerade nicht geklappt. Bitte versuche es erneut.",
„Die Antwort des Ausweis-Dienstes konnte nicht gelesen werden.") — kein
Rohstatus, kein HTTP-Code im sichtbaren Text (Prüfung durch Lesen von
`gepruefteAntwort`, Zeilen 72–80). Origin-Prüfung am Server bestätigt:
`grep` in `berichte/entscheidungen_server.py` zeigt `_herkunft_ok()` vor den
POST-Zweigen `/api/ausweis-anlegen` und `/api/ausweis-einladen` (Zeilen
949 ff.), `log_message()` ist stillgelegt (Zeile 864).

**AusweisAnsicht.swift — geprüft gegen die Kriterienliste:**
- Jedes Formularfeld hat ein sichtbares `TextField`/`SecureField`-Label
  UND ein redundantes `accessibilityLabel` (z. B. Zeile 203 f., 216 f.) —
  kein Feld nur mit Platzhalter.
- Rückweg vorhanden aus jedem erreichbaren Zustand: „Abbrechen" in beiden
  Sheets (Zeile 227, 316), „Erneut versuchen" im Ladefehler-Banner
  (Zeile 43), das Geheimnis-Ergebnis hat einen expliziten Knopf, der
  schließt UND neu lädt (`weiter()`, Zeilen 195–198, 285–288). Keine
  gefundene Sackgasse.
- Fehlerstatus ehrlich: `ladeFehler` wird nur bei tatsächlichem `catch`
  gesetzt, die Erfolgsliste bleibt leer, solange kein Erfolg vorliegt
  (Zeilen 92–103) — kein Fall gefunden, in dem ein Fehler als Erfolg
  angezeigt würde. **VERMUTET, nicht am Text entscheidbar:** ob ein
  simulierter 500er vom Dienst tatsächlich in `ladeFehler` landet, statt
  in einer stillen leeren Liste — dafür müsste der Dienst wirklich
  antworten, das ist ein Ebene-2/3-Test, nicht Textlektüre.
- Bedeutung nie allein über Farbe: Fehler haben zusätzlich ein
  `exclamationmark.triangle.fill`-Symbol UND Text, nicht nur rote Farbe.
- Geheimnis-Anzeige (`GeheimnisErgebnis`) ist der einzige Ort mit einem
  echten Geheimnis im UI — das ist gewollt (Zweck des „Anlegen"-Befehls,
  in Code-Kommentar begründet) und dem Nutzer angezeigt, nicht maskiert;
  deckt sich mit der Hausregel „eigene Daten werden nicht vorenthalten".

**Bestandteile-Filterung (87064fa) — die im Auftrag benannte Kernfrage:**
`app/Sources/BrainlehrCore/BestandteilRegistry.swift`, Zeile 40:
„Entscheidet, welche angeforderten Bestandteile laden DÜRFEN. […]
unbekannte Namen und Einträge mit unerfüllter Auflage werden verworfen —
**ohne Fehlermeldung an den Nutzer**." Das ist eine bewusste, im Code
dokumentierte Entscheidung, kein Aufsichtsversehen.

Bewertung: Für den heute tatsächlich verdrahteten Fall (`.dokumentfenster`,
immer `auflagenErfuellt: true`) bedeutet das praktisch: der Menüpunkt
„Dokument" fehlt genau dann, wenn keine Domäne importiert wurde ODER die
importierte Domäne ihn nicht anfordert — beim frischen Erststart (keine
Domäne importiert, „zwei Ausgangszustände") fehlt er also standardmäßig.
Das liest sich nicht wie ein Fehler, weil kein Fehlerzustand parallel
sichtbar wird (kein Banner, kein Platzhalter „wird geladen") — der Eintrag
ist einfach nicht da, wie ein nicht freigeschaltetes Feature. Kein
SICHERER Fund, weil kein Text und keine sichtbare Lücke etwas Falsches
behauptet.

**VERMUTET, künftig relevant:** Für `.tabellenkalkulation`
(`auflagenErfuellt: false`, ADR-016 Auflage 3 offen) existiert noch kein
Seitenleisten-/Menüeintrag, der gefiltert werden könnte — der stille
Verwurf ist heute folgenlos, weil nichts danach fragt. Sobald ein Eintrag
für dieses Bestandteil verdrahtet wird, entscheidet dieselbe Stelle über
denselben stillen Verwurf, dann greifbar für einen Domänen-Autor, der eine
Anforderung stellt und nie erfährt, dass sie technisch nicht erfüllbar
ist. Kein Fund für heute (nichts im UI hängt daran), aber der Punkt, an
dem die getroffene Entscheidung erstmals sichtbar würde — dem Betreiber
zur Kenntnis, keine Handlung nötig.

Doppelte Sperre (Seitenleiste UND `HauptFenster.body`-Bedingung, Zeilen
64–68 und 109–114) wie im Commit behauptet — beide Stellen gelesen, beide
prüfen `wahl.bestandteile.contains(.dokumentfenster)`.

Rot-vor-Grün am Code nachgefahren:
```
python3 -m pytest tests/test_bestandteile.py -q → 12 passed
```
Die Swift-XCTest-Seite (`app/bauen.sh`, laut Commit 215 Fälle grün) wurde
NICHT neu gebaut — das ist ein Build-Schritt, keine Textprüfung, und damit
außerhalb der für diesen Auftrag gewählten billigsten Kostenstufe. Wer die
Swift-Seite dieser Abnahme braucht, muss `app/bauen.sh` separat fahren.

## Was NICHT geprüft wurde

Kein Klickdurchgang, keine Bildschirmaufnahme (nicht nötig für die gestellten
Fragen — reine Textlektüre + Codepfade beantworteten Rückweg, Labels,
Fehlerehrlichkeit, Entwicklertext-Leck vollständig). Kein Test der
Steuerschnittstelle/`#if DEBUG`-Kontrollschnittstelle, kein Lauf gegen einen
echten `entscheidungen_server.py`-Prozess (Server-Fehlerantworten simuliert
lesen, nicht ausgelöst). Swift-XCTest-Suite nicht neu gebaut (siehe oben).

## Zusammenfassung

| Gegenstand | Ergebnis |
|---|---|
| entscheidungen.html O1-Fix | Vollständig, belegt (16/16 grün, war 15/16 rot laut Test-Historie, hier nur der Endzustand nachgefahren) |
| Ausweis-Weg über Dienst | Sauber, Fehlertexte in Nutzersprache, Origin-Schranke vorhanden |
| Bestandteile-Filterung | Funktioniert wie beschrieben, Stille bei Ablehnung ist bewusst und heute folgenlos — Beobachtungspunkt für später, kein Fund |
| Tooltip-Tastaturzugang | Ungeprüft belassen (vor heute so gebaut), nur im Rendering/Screenreader-Baum entscheidbar |
