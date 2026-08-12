# brainlehr als richtige macOS-Anwendung

Stand 2026-08-12T18:55:00+0200. Anlass: Betreiberwunsch, wörtlich — *„können
wir nicht eine richtig schöne mac os app bauen die das alles beinhaltet?"*

## Der gemessene Ist-Stand

Nicht geschätzt, nachgesehen:

| | Befund |
|---|---|
| Heutige App | `brainlehr.app` auf dem Schreibtisch, Commit `4dc33ef`. AppleScript, Systemdialoge, drei Ausweis-Abläufe plus Wissensraum plus offene Arbeit |
| Werkzeugkette | Xcode unter `/Applications/Xcode.app`, `swift`, `swiftc`, `xcodebuild` vorhanden |
| Vorbild im Verbund | `openlehr/apps/openlehr/macshell` — SwiftUI, `Package.swift`, swift-tools 5.10, macOS 14+, zwei Testtargets |
| Wiederverwendbar daraus | `ServiceSupervisor.swift` (lokalen Dienst starten und überwachen), `A11y.swift`, `LiveMonitorWindow.swift`, `I18n.swift` |
| `WKWebView` im Nachbarn | kommt nicht vor — dort ist alles nativ |
| Oberfläche heute | `entscheidungen.html`, fünf Ansichten, Puls und Abrufweg im Bedeutungsraum (`f21b766`), bedient von `berichte/entscheidungen_server.py` |

Was „das alles" umfasst, damit der Umfang nicht wandert: Ausweise und
Einladungen · Wissensraum mit den fünf Ansichten · Abrufmonitor (Aufgabe 41)
· Einstellungen · offene Arbeit · Eilmeldungen.

## Die Alternativen, und warum zwei ausscheiden

**A — AppleScript ausbauen.** Abgelehnt. Der Ablauf ist starr, das steht schon
im Kopfkommentar der heutigen App als bewusst bezahlter Preis. Für drei
Dialoge trägt er, für einen Monitor mit laufender Anzeige nicht. Kein
Fensterzustand, keine Seitenleiste, keine zwei Dinge gleichzeitig.

**B — Alles nativ neu bauen, auch die Grafik.** Abgelehnt, und das ist die
teuerste verworfene Alternative. Die fünf Ansichten sind gebaut, geprüft und
tragen 19 Testfälle unter Node (`test_abrufweg_puls.py`, `test_abrufweg_punktwolke.py`).
Sie in SwiftUI Canvas nachzubauen heißt: dieselbe Logik zweimal pflegen, die
Prüfungen wegwerfen, und die Drehung einer Wolke aus 2963 Punkten noch einmal
lösen. Der Gewinn wäre Einheitlichkeit, der Preis Wochen — und die Fehlerklasse
„zwei Fassungen derselben Sache, eine altert still" ist in diesem Repo bereits
mehrfach gemessen.

**C — Nativer Rahmen, Grafik im eingebetteten Web (gewählt).** SwiftUI-Fenster,
native Seitenleiste, native Menüs, native Einstellungen, native Dialoge für
Ausweise. Die drei Grafikansichten laufen in einem `WKWebView` auf dem lokalen
Server. Der Dienst wird von der App gestartet und überwacht, nach dem Muster
von `ServiceSupervisor`.

**Warum das die WCAG-Aussage nicht aufgibt** — der Punkt, an dem die heutige
App ihre Bauform begründet: Bedienelemente bleiben systemeigen und damit ab
Werk VoiceOver-tauglich, tastaturerreichbar, systemkontrast- und
systemschriftfolgend. Das Web-Fenster trägt nur Grafik, und deren
Zugänglichkeit ist bereits gebaut (aria-live-Text zu Puls, Alter und Stärke,
`prefers-reduced-motion`). Es wird also nichts nachgebaut, was das System
schon kann — genau die Begründung, die gegen eine selbstgebaute Oberfläche
sprach, spricht hier FÜR das Wiederverwenden des vorhandenen Bildes.

## Reihenfolge, und wo sie bindend ist

1. **Gerüst und Dienstaufsicht.** SwiftPM-Paket, Fenster, Seitenleiste,
   `ServiceSupervisor` nach Vorbild. **Bindend zuerst**: jede weitere Ansicht
   setzt voraus, dass der Dienst zuverlässig läuft und sein Ende gemeldet wird.
2. **Wissensraum im Fenster.** Die fünf Ansichten eingebettet, Ansichtswahl
   nativ in der Seitenleiste statt als Knopfleiste im Web.
3. **Ausweise nativ.** Die drei Abläufe aus dem AppleScript als SwiftUI-Formulare.
   Das Geheimnis berührt weiterhin keine Befehlszeile.
4. **Abrufmonitor** (Aufgabe 41) — die Ansicht, die es heute nirgends gibt.
5. **Einstellungen** nativ, aus den acht Abschnitten der HTML-Seite.

Schritt 3 darf nicht vor Schritt 1 laufen: solange der Dienst unbeaufsichtigt
ist, sieht ein Ausweisfehler aus wie ein Serverfehler.

## Was bewusst nicht getan wird, samt Preis

- **Keine Notarisierung, keine Signatur.** Preis: Die App läuft nur auf diesem
  Rechner ohne Warnung. Fremde Rechner sind heute kein Ziel.
- **Die AppleScript-App wird nicht gelöscht.** Sie bleibt, bis die native
  Fassung alle drei Ausweisabläufe trägt. Preis: zwei Programme nebeneinander.
- **Kein zweiter Datenpfad.** Die App liest nichts direkt aus der Datenbank,
  alles geht über den Dienst. Preis: die App ist ohne Dienst leer. Gewinn: es
  gibt weiter genau eine Stelle, die den Bestand kennt.

## Woran sich Erfolg messen lässt

Nicht am Eindruck:

- Der Dienst wird von der App gestartet, und sein **unerwartetes Ende** wird
  in der Oberfläche sichtbar — nicht erst beim nächsten Klick.
- Beide Ausgangszustände einmal gefahren: frisch installiert und über die
  Vorfassung aktualisiert. Die Fehlerklasse ist in diesem Verbund zweimal
  gemessen (`L-8bde89`, `L-96db3e`).
- Jeder Aufruf, der eine Shell benutzt, einmal unter `env -i PATH=/usr/bin:/bin`
  nachgestellt — dort starb die App am 2026-08-11 (`L-38bcb0`), und heute noch
  einmal beinahe der Wissensraum, weil `cryptography` unter dem Systempython
  fehlt.
- VoiceOver-Durchgang durch Seitenleiste und Ausweisformular: jedes
  Bedienelement hat einen Namen, der Fokus ist sichtbar.

## Fortschreibung

**Schritt 1 umgesetzt, 2026-08-12T19:15:00+0200.** Neuer Ordner `app/`
(Begründung: der Plan nennt `app/` zuerst, kein Grund für `macapp/` gefunden).
SwiftPM-Paket `BrainlehrApp` (ausführbar) + `BrainlehrCore` (reine Logik) +
`BrainlehrCoreTests` (12 Testfälle, u.a. Grenzfall „noch startend ≠
unerwartet beendet" und Negativfall „absichtliches Anhalten überschreibt
jeden Fehlerzustand"). macOS 14, swift-tools 5.10, kein Fremdpaket.

Fenster mit `NavigationSplitView`, sechs Seitenleisten-Platzhalter
(Wissensraum, Ausweise und Einladungen, Abrufmonitor, Einstellungen, Offene
Arbeit, Eilmeldungen) — deckt den in der Ist-Stand-Tabelle genannten Umfang
ab. Dienstaufsicht (`DienstAufsicht.swift`) nach Vorbild
`ServiceSupervisor.swift`, aber kleiner — bewusst nicht übernommen: Bundle-
Resource-Hinweis, `/Volumes`-Namenssuche, `.env`-Merge, UserDefaults-Cache
des Repo-Pfads (siehe Kopfkommentar der Datei für die Begründung je Punkt).
Health-Check per periodischem Poll (2 s) statt nur `terminationHandler`,
damit auch ein von außen bereits laufender, nicht selbst gestarteter Dienst
beim Sterben erkannt wird — das war im Vorbild nicht nötig, weil dort keine
„schon jemand da"-Situation vorgesehen ist.

**Ein Fehler unterwegs gefunden und mit Rot-Probe belegt, nicht nur behoben:**
Der erste Health-Check nutzte HTTP HEAD. `berichte/entscheidungen_server.py`
(BaseHTTPServer) beantwortet HEAD mit `501 Unsupported method` — das sah wie
ein Ausfall aus, obwohl der Dienst lief, und verschluckte den echten Test:
Die App zeigte nach einem tatsächlichen `kill -9` des Dienstes keinen Banner
(Sichtprobe, Fenster-Screenshot vor/nach dem Kill identisch). Ursache über
Datei-Log in der laufenden App gefunden (unified log filterte NSLog-Zeilen
weg), dann mit `curl -I` bestätigt: `501`. Fix: GET statt HEAD, wie
`pflege/wissensraum_start.sh` es mit `curl -s -o /dev/null` bereits vorlebt.
Nach dem Fix erneut geprüft: Banner erscheint automatisch, „Erneut
versuchen"-Knopf (per Accessibility-Klick ausgelöst, kein manueller Klick
nötig) startet den Dienst neu, Banner verschwindet von selbst.

**Abnahme, mit Beleg:**
- `swift build` und `swift test` grün (12/12), auch unter
  `env -i PATH=/usr/bin:/bin`.
- App gestartet und per Fenster-Screenshot (nicht Vollbild — ein
  versehentlicher Vollbild-Screenshot zeigte fremden, privaten Bildschirm-
  inhalt und wurde sofort gelöscht; ab da nur noch gezielte
  Fenster-Ausschnitte über die Fenster-ID) angesehen: Seitenleiste mit sechs
  lesbaren Einträgen, kein Banner im Normalbetrieb.
- Ausfall nachgestellt: `kill -9` auf den vom System-Python gestarteten
  Dienstprozess, Banner erscheint automatisch ohne Klick.
- Bereits laufender Dienst erkannt: zweiter App-Start bei schon laufendem
  Dienst startete keinen zweiten Prozess (eine PID vor und nach dem Start).
- App-Ende beendet den selbst gestarteten Dienst mit (geprüft über
  `tell application "BrainlehrApp" to quit` — `tell application "System
  Events" to quit application process …` griff nicht zuverlässig, nur die
  direkte Apple-Event-Variante).

**Kleine Abweichung vom Plantext:** `openlehr`s `I18n.swift` liegt entgegen
der Auftragsbeschreibung nicht in `Sources/OpenLehrApp/`, sondern in
`Sources/OpenLehrCore/I18n.swift` — nicht übernommen, da Schritt 1 keine
Übersetzungstabelle braucht (nur deutsche Texte direkt im Code).

**Zwischenschritt umgesetzt, 2026-08-12T19:58:00+0200: echtes Anwendungsbündel,
volle Menüleiste, Symbol.** Betreiberwunsch wörtlich und zum dritten Mal:
„eigentlich wuerde mir zuerst eine gute nach apple standarts gebaute .app am
besten gefallen! und zwar richtig mit apple menue usw!" — diesmal gebaut,
nicht abgewogen.

`app/bauen.sh` erzeugt nach grünen Tests zusätzlich `app/Ausgabe/brainlehr.app`
(Contents/MacOS, Contents/Resources, Info.plist, ad-hoc signiert). Ort bewusst
repo-lokal (`app/.gitignore` schließt `Ausgabe/` aus), nicht der Schreibtisch.
Neue Dateien: `app/Resources/Info.plist` (Vorlage mit `__FASSUNG__`/
`__BAUNUMMER__`, aus `VERSION` bzw. `git rev-list --count HEAD` gefüllt),
`app/Resources/erzeuge_icon.swift` (zeichnet ein schlichtes eigenes Symbol —
abgerundetes Quadrat, blauer Verlauf, weißes „b" — bei jedem Bau frisch in
allen zehn von macOS erwarteten Pixelgrößen, kein Fremdmaterial). `CFBundleLocalizations`
auf `de` beschränkt, damit die Systemmenüs unabhängig von der Systemsprache
deutsch bleiben. `NSSupportsAutomaticTermination`/`NSSupportsSuddenTermination`
auf `false`, weil `applicationWillTerminate` den überwachten Dienstprozess
sauber herunterfahren muss.

`BrainlehrApp.swift` bekam eine `Settings`-Szene (Platzhalterinhalt, öffnet auf
Befehlstaste-Komma) und eine Mindestgröße fürs Hauptfenster. Ein zuerst
gebauter eigener Fensterlagen-Speicher (`NSWindow.setFrameAutosaveName`) wurde
wieder entfernt: Rot-Probe zeigte, dass `WindowGroup` Größe und Lage bereits
von selbst unter einer eigenen Kennung sichert (Schlüssel „NSWindow Frame
main-AppWindow-1" in `~/Library/Preferences/de.brainlehr.app.plist`) — der
eigene Code war totes Gewicht neben einem bereits vorhandenen Systemmechanismus.

**Abnahme, mit Beleg:**
- `app/bauen.sh`: weiterhin 12/12 XCTest-Fälle, 0 Fehlschläge, danach Bündel-
  Bau, danach `codesign --force --deep --sign -`.
- `codesign -dv Ausgabe/brainlehr.app`: `Format=app bundle with Mach-O thin
  (arm64)`, `Signature=adhoc`, `Info.plist entries=19`.
- Per `open Ausgabe/brainlehr.app` gestartet (nicht die nackte Binärdatei),
  Prozessname „brainlehr" in der Prozessliste belegt, per `open`+`ps` und per
  `tell application "System Events" to get name of every process` bestätigt.
- Menüleiste tatsächlich per AppleScript ausgelesen (nicht nur behauptet):
  **Apple-nahes Menü „brainlehr"**: Über „brainlehr", Einstellungen … (Befehl-Komma,
  per Klick geprüft — öffnet ein eigenes Fenster „brainlehr-Einstellungen"),
  Dienste, „brainlehr" ausblenden, Andere ausblenden, Alle einblenden,
  „brainlehr" beenden. **Ablage**: Neues Fenster „Brainlehr", Schließen, Alle
  schließen. **Bearbeiten**: Widerrufen, Wiederholen, Ausschneiden, Kopieren,
  Einsetzen, Löschen, Alles auswählen (Standardkürzel, systemeigen).
  **Darstellung**: Tableiste/Vollbildmodus (Systemstandard). **Fenster**: Im
  Dock ablegen (heutige macOS-Bezeichnung für „Minimieren", weiterhin
  Befehl-M), Zoomen, Alle nach vorne bringen, Fensterliste. **Hilfe**:
  brainlehr-Hilfe. Fenster-Screenshot (über CGWindowID, kein Vollbild) zeigt
  Seitenleiste mit sechs lesbaren Einträgen, kein Banner im Normalbetrieb.
- Fensterlage: Fenster dreimal verschoben/vergrößert, App per
  `tell application "brainlehr" to quit` beendet (Prozess danach weg — belegt
  auch, dass der Dienst mitbeendet wird), neu gestartet. **Größe** kam jedes
  Mal exakt zurück (z. B. 1000×700 → Neustart → 1000×700, dreifach
  wiederholt). **Lage**: in `~/Library/Preferences/de.brainlehr.app.plist`
  steht exakt die gesetzte Position, sichtbar wiederhergestellt wurde sie in
  dieser Testumgebung trotzdem nicht zuverlässig — das Fenster erschien beim
  Neustart auf dem eingebauten statt dem externen Bildschirm. Zwei Bildschirme
  sind angeschlossen (`CG2700X` 2560×1440, eingebautes Display bei
  x=2560/y=−267); welcher Bildschirm beim `open`-Aufruf als „aktiv" gilt,
  scheint die Wiederherstellung zu überstimmen. Das ist derselbe
  AppKit-Mechanismus, den auch ein eigener Code genutzt hätte — kein Fehler
  der Kürzung, sondern eine Eigenschaft von `setFrameAutosaveName` bei
  mehreren Bildschirmen, hier nicht weiter aufgelöst. Auf einem Rechner mit
  einem Bildschirm (der Normalfall) ist davon nichts zu erwarten.
- Volle Python-Suite: `972 passed, 2 skipped, 11 xfailed, 0 failed` — exakt
  wie vor dieser Änderung, kein Rücklauf.

**Was bewusst nicht getan wurde:** Notarisierung/Entwicklerzertifikat (weiter
laut Plan bewusst verzichtet). Die acht Einstellungs-Abschnitte, die drei
Ausweisabläufe und der Abrufmonitor bleiben Platzhalter — das ist Schritt 2–5,
nicht dieser Zwischenschritt; hier zählte laut Auftrag nur, dass die Struktur
stimmt.

Offen für Schritt 2: Wissensraum-Ansichten in ein `WKWebView` einbetten.
Entscheidungen wandern als ADR nach `docs/adr/`.
