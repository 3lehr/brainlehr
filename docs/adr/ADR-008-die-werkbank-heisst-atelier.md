# ADR-008: Die Werkbank heißt `atelier`

**Stand** 2026-08-14T07:42:03+0200
**Status** Angenommen
**Betrifft** die Mac-Anwendung unter `app/`, künftig jede Oberfläche der Werkbank
**Entscheider** Betreiber, 2026-08-14

## Die Frage

Bisher hieß die Anwendung „die brainlehr-App". Damit ist jeder Satz zweideutig: „brainlehr
kann das nicht" meint mal den Speicher, mal das Fenster. Genau diese Verwechslung wurde
einen Tag zuvor bei `openlehr` aufgelöst (ADR-007) — Schicht und Instanz trugen denselben
Namen. Hier liegt sie ein zweites Mal vor, zwischen **System** und **Werkbank**.

Verschärfend kam die Absicht des Betreibers hinzu, aus dieser Anwendung heraus neue Domänen
zu bauen. Ein Ding, in dem Domänen entstehen, ist keine App zu einem Speicher, sondern ein
eigener Gegenstand — und der braucht einen eigenen Namen.

## Entscheidung

**Drei Namen, drei Gegenstände, keine Überschneidung:**

| Name | Gegenstand |
|---|---|
| **`brainlehr`** | Der Speicher mit seiner Aufsicht. Was gilt, und ob es belegt ist. |
| **`atelier`** | Die Werkbank darauf. Wo Domänen entstehen und wo Mensch und Modell nebeneinander arbeiten. |
| **`open*`** | Der Namensraum der Instanzen: `openlehr` (Steuer), `openWEG` (bei Veröffentlichung). |

## Warum `atelier`

**Es ist dasselbe Wort in Deutsch, Englisch und Französisch.** Keine Übersetzung, keine
Aussprachehürde. Das war die ausdrückliche Auflage des Betreibers: *„bedenke die
englischsprachige Community."* Sie ist keine Höflichkeit — die Konsil-Rolle
`newton-standards` hatte am Vortag festgestellt, dass eine deutschsprachige Außenfläche
eine **Beitragenden-Decke** ist, die keine Architektur anhebt. Ein Gemeinschaftsgehirn
scheitert an einer Aussprachehürde genauso wie an einer Lizenz.

**Es trifft die Sache ohne Erklärung.** Ein Atelier ist der Ort, an dem etwas von Hand
gemacht wird — und an dem Lehrlinge lernen, indem sie **neben** dem Meister arbeiten. Das
ist die Schüler→Lehrer→Universität-Stufung des Betreibers in einem Wort, und es ist die
Bauform „von KI und Menschen gemeinsam bedient": nicht einer belehrt den anderen, beide
arbeiten am selben Stück.

**Es sagt nicht „app", und das ist das tragende Argument.** Nach ADR-006 ist die Oberfläche
die Schicht, die sterben darf — Python ist die Grundsprache, das Schema die Quelle. Ein
Name mit „app" bindet sich an genau das Teil, das weggeworfen werden soll. Wird die Hülle
eines Tages Web statt Swift, ist `brainapp` falsch und `atelier` unverändert richtig.

**Gemessen:** kein einziger Bezeichner im Verbund. Die 66 Fundstellen sind Fließtext, alle
in einem Archiv von Ende Juli 2026.

## Alternativen, samt Ablehnungsgrund

| Weg | Abgelehnt weil |
|---|---|
| **`lehrhaus`** | Semantisch das beste (der Ort zwischen Schule und Universität, an dem man streitend herausfindet, was gilt), sprachlich das schlechteste. Ein Engländer liest „lair house". |
| **`brainapp`** | Frei und sauber, aber „app" beschreibt die Hülle — also das Teil, das nach ADR-006 wegwerfbar ist. Und es sagt nichts darüber, dass darin gebaut wird. |
| **`lehrbench`** | Zwei gemessene Probleme. **„bench" heißt in dieser Codebasis Benchmark** — 33 342 Vorkommen von „Benchmark", 17 630 klein geschrieben; der Name legt bei jeder Suche eine falsche Fährte, ausgerechnet neben einem offenen Konsil-Befund zu Benchmarks. Und der geteilte Stamm `lehr` stellt die Zweideutigkeit wieder her, die der eigene Name beseitigen soll: gesprochen sind `brainlehr` und `lehrbench` beide „das Lehr-Ding". Die Aussprachehürde bleibt zudem erhalten. |
| **`forge`** (956), **`studio`** (1137), **`werkstatt`** (1760) | Zu allgemein, nicht greppbar, im Werkzeugbau verbraucht (SourceForge, Forgejo). |
| **`agora`** (10) | Verlockend wenig belegt, falsche Bedeutung: die Agora ist der Ort des **Streits und der Entscheidung**, nicht des Bauens. Das beschreibt das Konsil, nicht die Werkbank. |
| **`praxis`** | Ernsthafter Zweitplatzierter — dasselbe Wort in beiden Sprachen, trifft die Achse Wissen gegen Anwendung. Verliert an der deutschen Nebenbedeutung: die Praxis ist der Ort, an dem **einer** sein Wissen auf einen Fall anwendet. Hier wird gemeinsam gebaut. |

## Was das kostet — und die bindende Reihenfolge

**Heute ist nur der NAME entschieden, nicht die Umbenennung.** Das ist kein Aufschieben,
sondern eine Sperre aus einer Messung derselben Nacht:

Die Anwendung trägt die Kennung `de.brainlehr.app`. An ihr hängen die gesicherte
Fensterlage (`~/Library/Preferences/de.brainlehr.app.plist`), der gesicherte
Anwendungszustand und die Registrierung bei den Startdiensten. **Und genau dort liegt ein
offener, unverstandener Fehler:** Direkt gestartet erscheint das Fenster (gemessen,
1728×1083, Schicht 0), über `open` nicht. Ursache noch nicht ermittelt; der gesicherte
Fensterzustand ist als Ursache bereits ausgeschlossen.

> **Die Kennung wird nicht umbenannt, bevor dieser Fehler verstanden ist.** Sonst sind
> zwei Ursachen im selben Bereich gleichzeitig unterwegs, und jede Messung danach ist
> nicht mehr zuordenbar.

Weitere Kosten, benannt statt verschwiegen: Verzeichnis `app/`, Binärname, Bündelname und
`bauen.sh` tragen heute `brainlehr`. Solange beides koexistiert, ist der Zwischenzustand
selbst zweideutig — das ist der Preis dafür, die Umbenennung hinter die Fehlersuche zu
stellen, und er ist der kleinere.

## Nachtrag 2026-08-14T08:10 — die Sperre fällt, den Fehler gab es nie

Der Abschnitt oben sperrt die Umbenennung, bis ein Fehler verstanden ist: *„direkt
gestartet erscheint das Fenster, über `open` nicht."* **Diesen Fehler gibt es nicht.**

Nachgemessen in mehreren Läufen: Das Fenster wird **jedes Mal** erzeugt. Was schwankte, war
meine Messung. Drei Anläufe, drei eigene Fehler:

1. `NSApp.windows.filter(\.isVisible).count` meldete 1, während nichts zu sehen war — SwiftUI
   hält Hilfsfenster, die Anwendung hat stets **fünf** Fenster, davon **vier ohne Namen**.
2. `CGWindowList` mit `.optionOnScreenOnly` meldete daraufhin mal 0, mal 1. Daraus habe ich
   **zweimal** einen Fehler in der App geschlossen, den es nicht gab — einmal „`open` ist
   schuld", einmal „direkter Start ist schuld", beide Male aus einem einzigen Lauf je Seite.
3. Die Erklärung kam vom Betreiber: Er wechselte während der Messung Fenster und
   Schreibtisch. `.optionOnScreenOnly` zählt nur, was auf dem **gerade sichtbaren**
   Schreibtisch liegt.

**Die Regel daraus, und sie ist größer als dieser Fall:** Ein Prüfkanal, dessen Wert davon
abhängt, was der **Mensch** gerade tut, ist kein Prüfkanal. Er ist nicht wiederholbar, nicht
vergleichbar, und er verwandelt einen Schreibtischwechsel in einen Befund. Die
Steuerschnittstelle misst deshalb jetzt ausschließlich den Zustand der **Anwendung**
(`hauptfenster()` über `canBecomeMain`) — fünf von fünf Läufen beständig.

Der Betreiber hat den eigentlichen Punkt benannt: *„wollten wir den Weg, dass du meinen
Bildschirm filmst, nicht genau umgehen?"* Genau dafür war die Schnittstelle gebaut, und ich
hatte ihren Zweck selbst unterlaufen.

**Damit ist die Umbenennung nicht mehr gesperrt.** Sie bleibt trotzdem ein eigener Schritt
mit eigener Abnahme — gesicherte Fensterlage, Anwendungszustand und Registrierung bei den
Startdiensten hängen an `de.brainlehr.app` und wandern nicht von selbst mit.

## Woran sich Erfolg misst

- Kein Satz im Verbund ist mehr zweideutig zwischen Speicher und Werkbank.
- `grep -ri atelier` findet ausschließlich die Werkbank — nie den Speicher, nie eine Instanz.
- Ein fremder Beitragender liest den Namen, spricht ihn aus und weiß, was gemeint ist,
  ohne dass jemand ihn übersetzt.
