# Die Anwendung in Schichten — und was davon je System neu gebaut werden muss

Stand 2026-08-12T19:55:00+0200. Anlass: Betreiberfrage, wörtlich — *„sollten
wir hier nicht zuerst einen plan erstellen und die app in teilbereiche
aufteilen, immerhin muss sie verschiedene aufgaben erfüllen und später auch
leicht für windows und linux umzubauen sein!"*

Ergänzt `PLAN_MACAPP_2026-08-12.md`, der die Bauform für macOS entscheidet und
über Schichten und andere Systeme nichts sagt.

## Der Befund, der die ganze Aufteilung trägt

**Der plattformübergreifende Teil ist bereits gebaut, und zwar vollständig.**
Der Dienst ist Python, die Oberfläche ist HTML und JavaScript. Beides läuft auf
Windows und Linux ohne eine Zeile Änderung. Ein Benutzer dort kann heute schon
den Dienst starten und die Seite im Browser öffnen — er hat dann alles außer
dem Fensterrahmen.

Daraus folgt die Leitentscheidung, und sie ist keine Geschmacksfrage:

> **Portabilität wird nicht dadurch erreicht, dass man eine portable
> Oberflächenbibliothek wählt, sondern dadurch, dass die Schale nichts
> enthält, was neu erfunden werden müsste.**

Jede Fähigkeit, die in die Schale wandert, muss dreimal gebaut werden. Jede
Fähigkeit, die im Dienst bleibt, keinmal.

## Die vier Schichten

| Schicht | Sprache | Je System neu? | Enthält |
|---|---|---|---|
| **1 Bestand** | SQLite, Schema | nein | Wissen, Lehren, Zugriffe |
| **2 Dienst** | Python | nein | Abruf, Fusion, Ausweise, alle Regeln |
| **3 Bild** | HTML, JS, Canvas | nein | die fünf Ansichten, Puls, Abrufweg |
| **4 Schale** | je System | **ja** | Fenster, Menü, Dienstaufsicht, Systemdialoge |

Schicht 4 zerfällt noch einmal in zwei, und das ist der eigentliche Kniff:

| | Sprache | Je System neu? |
|---|---|---|
| **4a Schalenkern** | Swift, plattformfrei | nein — Swift läuft auf Linux und Windows |
| **4b Schalenhaut** | SwiftUI / GTK / WinUI | ja |

**4a** trägt alles, was man testen kann, ohne ein Fenster zu öffnen: der
Zustand des Dienstes und seine Übergänge, die Wahl des Interpreters, das
Auflösen von Pfaden, das Deuten von Antworten. Heute sind das
`DienstZustand.swift` und `PythonAuswahl.swift` mit zwölf Testfällen.

**4b** trägt nur, was das System selbst mitbringt: Fenster, Menüleiste,
Dateiauswahl, Benachrichtigung. Nichts davon wird nachgebaut — genau die
Begründung, mit der die heutige App auf Systemdialoge setzt.

## Die Regel, die das Ganze zusammenhält — und sie ist prüfbar

**Der Schalenkern darf keine Oberflächenbibliothek kennen.** Kein `import
SwiftUI`, kein `import AppKit` in `BrainlehrCore`. Das ist keine Absicht,
sondern eine Zusicherung, die eine Prüfung durchsetzt: Sobald jemand dort eine
Fensterklasse benutzt, ist die Portierung stillschweigend teurer geworden, und
niemand merkt es — dieselbe Fehlerklasse, an der dieses Projekt heute den
ganzen Tag gearbeitet hat.

Zweite prüfbare Zusicherung: **Die Schale spricht mit dem Bestand nur über den
Dienst.** Kein zweiter Datenpfad, keine SQLite-Verbindung aus Swift. Steht
schon im Plan für macOS; hier wird sie zur Portabilitätsregel, denn eine
Datenbankschicht in der Schale müsste dreimal gebaut werden.

## Die Aufgabenbereiche der Anwendung

Damit der Umfang nicht wandert, und zugleich als Schnitt für die Arbeit:

1. **Wissensraum** — die fünf Ansichten. Schicht 3, Schale zeigt nur.
2. **Ausweise und Einladungen** — Formulare. Schale, weil Systemdialoge; die
   Regeln bleiben im Dienst.
3. **Abrufmonitor** — was gefunden, was verworfen, warum. Schicht 3.
4. **Einstellungen** — die acht Abschnitte. Werte im Dienst, Darstellung Schale.
5. **Offene Arbeit und Eilmeldungen** — Text aus dem Dienst.
6. **Dienstaufsicht** — reine Schale, und der einzige Teil, der ohne Dienst
   arbeiten muss. Deshalb liegt seine Logik in 4a.

Nur Bereich 2 und 6 haben überhaupt Schalenanteil, der über „anzeigen"
hinausgeht. Das ist die Zahl, an der sich die Portierung später bemisst.

## Was das für Windows und Linux konkret heißt

Ehrlich beziffert statt versprochen:

- **Ohne jede Arbeit lauffähig:** Schicht 1 bis 3. Ein Benutzer startet den
  Dienst und öffnet den Browser.
- **Neu zu bauen:** allein 4b — Fenster, Menü, Ausweisformulare. Auf Linux ein
  GTK- oder Qt-Aufsatz, auf Windows WinUI; in beiden Fällen gegen denselben
  Schalenkern.
- **Nicht neu zu bauen, wenn die Regeln oben gelten:** Zustandslogik,
  Interpreterwahl, jede Fachregel.

**Die Alternative, die naheliegt und die abgelehnt wird:** ein einziger
plattformübergreifender Rahmen (Electron, Tauri, Flutter Desktop) statt drei
Schalen. Er spart die dreifache Schale und kostet dafür genau das, was der
Betreiber heute ausdrücklich verlangt hat — eine Anwendung, die sich auf dem
Mac wie eine Mac-Anwendung anfühlt, mit dem Menü, das dort hingehört. Der
Verzicht wird bewusst bezahlt und wäre umzukehren, sobald Windows oder Linux
ein echtes Ziel werden statt einer Möglichkeit.

## Reihenfolge

1. **Bündel und Menüleiste** (läuft) — macOS-Schale vollständig.
2. **Wache für die Schichtregel** — Prüfung, dass der Schalenkern keine
   Oberflächenbibliothek kennt und die Schale keine Datenbank öffnet. Kommt
   VOR den weiteren Ansichten: eine Regel, die erst nach dem Bau eingezogen
   wird, findet nur noch Altlasten.
3. Wissensraum, Ausweise, Monitor, Einstellungen — nach dem bestehenden Plan.

## Woran sich Erfolg messen lässt

- Der Schalenkern übersetzt auf einem System ohne Apple-Bibliotheken. Das ist
  die einzige ehrliche Probe für Portabilität — alles andere ist eine Absicht.
  Sie steht aus, solange kein solches System zur Hand ist, und wird bis dahin
  **als ausstehend geführt, nicht als erfüllt.**
- Die Wache aus Schritt 2 ist rot, bevor sie grün ist.
- Zahl der Schalen-Dateien mit Fachlogik: null.
