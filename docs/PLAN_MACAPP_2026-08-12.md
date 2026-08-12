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

Nach der Umsetzung: was anders kam als geplant, und warum. Entscheidungen
wandern als ADR nach `docs/adr/`.
