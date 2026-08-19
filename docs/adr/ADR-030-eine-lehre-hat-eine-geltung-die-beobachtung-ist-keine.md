# ADR-030: Eine Lehre hat eine Geltung — ihre Beobachtungszeit ist keine

**Status:** angenommen
**Datum:** 2026-08-19T14:05:00+0200
**Entscheider:** Betreiber (Anstoß und Beispiel), Ausführung Assistent
**Betrifft:** `BDW-P05`, `BDW-R05`, `lessons_learned`, ADR-Reihe zu `BDW-P08`

## Der Anstoß, wörtlich

> „ja weill lehren ja auch wissen ist und oder eine teilmenge davon? es könnte
> ja die akte lehren geben? zudem auch hier eine geltungsdauer, bei der swift
> app entwicklung kamm zb . das apple näcshtes jahr etwas umstellt. das währe
> dann ein echtes wichtiges ablaufdatum?"

## Was ich zwei Nachrichten vorher vorgeschlagen hatte — und warum es falsch war

Ich hatte vorgeschlagen, für `BDW-P05` die vorhandenen Lehrenfelder als
Herkunft und Geltung **zuzuordnen**: `session`/`actor` als Quelle, `status` als
Status, `first_seen`/`last_seen` als Geltung.

Die ersten beiden tragen. Der dritte ist ein **Kategoriefehler**:

- `first_seen` sagt, **wann die Lehre beobachtet wurde**.
- Geltung sagt, **bis wann sie zutrifft**.

Eine Lehre über Flutter, beobachtet am 2026-07-19, kann im Frühjahr 2027 falsch
werden, weil die Plattform sich ändert. Ihr `first_seen` weiß davon nichts und
wird sich nie ändern. Wer das eine als das andere ausgibt, liefert eine
Geltungsangabe, die niemals abläuft — schlimmer als gar keine, weil sie
Sicherheit vortäuscht.

## Die Messung, die den Umfang zeigt

Gemessen 2026-08-19 über den vollen Bestand (1112 Lehren): **358 Lehren
(32,2 %) hängen an einer fremden Plattform oder Version** — iOS, macOS, Xcode,
Swift, SwiftUI, CarPlay, Flutter, Dart, Android, Gradle, SQLite, Ollama,
Claude Code. Das sind genau die, bei denen ein Ablaufdatum kein Schmuck ist,
sondern die Aussage selbst.

`lessons_learned` führt heute **weder `gilt_ab` noch `gilt_bis`**. Vorhanden
sind nur `status`, `first_seen`, `last_seen`.

## Warum das kein Widerspruch zu `BDW-P08` ist

`BDW-P08` (belegt) sagt: **Wissen verfällt nicht durch Zeit, es wird durch
einen Nachfolger abgelöst.** Das bleibt richtig und wird hier nicht angetastet.

Ein `gilt_bis` ist kein Verfall. Es ist eine **benannte Entscheidung mit
Datum** — „Apple stellt zum 1. April um, ab dann gilt dieser Satz nicht mehr".
Der Unterschied ist derselbe wie zwischen einem Lebensmittel, das schlecht
wird, und einem Vertrag, der ausläuft: das eine passiert, das andere wurde
vereinbart. Knoten haben genau dafür bereits `norm_befristet` mit `gilt_bis`;
Lehren fehlt nur das Feld.

## Entscheidung

**`lessons_learned` bekommt `gilt_ab` und `gilt_bis`, mit derselben Bedeutung
wie bei Knoten.** Leer bleiben ist der Normalfall und heißt „unbefristet" —
nicht „unbekannt".

Nicht entschieden und ausdrücklich offen: ob Lehren und Knoten langfristig
**eine** Tabelle werden sollen. Der Betreiber hat die Frage gestellt („es
könnte ja die akte lehren geben"), und sie ist berechtigt — seit heute tragen
beide Tabellen `gedaechtnisart`, also denselben Begriff. Das ist ein eigener
Umbau mit eigener Messung und wird hier nicht nebenbei mitentschieden.

## Preis, ausdrücklich

Ein Feld, das niemand füllt, ist eine gebaute Regel ohne Wirkung — genau die
Fehlklasse, die dieses Haus an sechs Spalten schon gemessen hat. `gilt_bis` auf
Lehren wird deshalb nur dann etwas wert, wenn es beim Erfassen **gefragt** wird,
wo es zutrifft. Ohne diesen Schritt bleibt es leer und zählt zu Recht als
wirkungslos.

## Woran sich Erfolg messen lässt

1. Eine Lehre mit gesetztem `gilt_bis` in der Vergangenheit wird im Abruf als
   abgelaufen gekennzeichnet — wie ein Knoten heute schon.
2. Von den 358 plattformabhängigen Lehren trägt nach einem Jahr ein messbarer
   Anteil ein Ablaufdatum; bleibt er bei null, war das Feld die falsche Antwort.
3. `BDW-P05` kann die Geltung für Lehren dann prüfen, statt sie zu überspringen.

---

## Nachtrag 2026-08-19T14:35:00+0200 — die Geltung einer Plattform-Lehre ist eine VERSION, kein Datum

Der Betreiber, unmittelbar nach der Entscheidung oben:

> „‚vergleicht Versionen und Stände' dann brauchen wir aber auch ein
> zusatztfeld: ab welcher ‚version' gilt diese regel usw?"

**Das ist richtig und schärfer als das, was zwei Absätze weiter oben steht.**
Eine Lehre über Flutter gilt nicht „bis zum 1. April 2027". Sie gilt „für
Flutter bis 3.19" oder „seit Ollama 0.32". Das Datum ist ein Stellvertreter,
die Version ist die Sache selbst.

Und der Unterschied ist nicht akademisch, sondern entscheidet über die
Prüfbarkeit:

- Ein **Datum** muss jemand im Voraus kennen. Wer am Tag des Erfassens nicht
  weiß, dass Apple im Frühjahr umstellt, trägt nichts ein — und das Feld
  bleibt leer.
- Eine **Versionsgrenze** ist gegen einen Anbieter-Feed maschinell prüfbar.
  Gemessen am 2026-08-19: GitHub-Releases für Flutter, Ollama und Swift
  antworten mit HTTP 200 und liefern Version plus Datum als JSON.

## Was die Messung dazu ergab, und sie verbietet die naheliegende Umsetzung

Über den vollen Bestand (1112 Lehren):

| | |
|---|---|
| Lehren mit Produktbezug | **252** |
| davon mit einer konkreten Version im Text | **12 (4,8 %)** |
| ohne Version | 240 |

Häufigste Produkte: Flutter 64 · Python 56 · CarPlay 43 · iOS 33 · Dart 26 ·
Android 25 · Swift 19 · macOS 18.

**Die 12 sind zudem größtenteils unbrauchbar.** Eine der gefundenen
„Versionen" lautet `127.0.0` — das stammt aus der Adresse `127.0.0.1`. Andere
sind Bibliotheksstände, nicht Plattformstände.

**Daraus folgt: Ein Versionsfeld rückwirkend aus dem Text zu füllen ist
ausgeschlossen.** Es wäre zu 95 % leer und im Rest teilweise falsch — genau
die gebaute Regel ohne Wirkung, vor der der Preis-Abschnitt oben warnt, nur
mit dem Zusatz, dass sie auch noch täuscht.

## Die Entscheidung, in zwei Teilen statt einem

**Erstens, rückwirkend möglich: `bezug`.** Welches fremde Produkt eine Lehre
überhaupt betrifft, ist aus dem Text zuverlässig zu gewinnen — 252 Treffer,
gegen eine feste Namensliste, ohne Modell. Damit kann ein Melder sagen:
*„Flutter hat sich seit deinem letzten Stand bewegt; diese 64 Lehren nennen
Flutter."* Das ist eine **Prüfliste**, keine Ablösung.

**Zweitens, nur vorwärts: `gilt_bis_version` (und `gilt_ab_version`).** Sie
werden **beim Erfassen** gesetzt, wo der Schreibende es weiß — nicht
nachträglich geraten. Leer heißt „nicht versionsgebunden", nicht „unbekannt".

## Was ausdrücklich NICHT gebaut wird

Keine automatische Ablösung. Ein Versionssprung bei Ollama sagt nichts
darüber, ob eine bestimmte Lehre dadurch falsch wird — das kann ein Vergleich
nicht entscheiden und ein Skript nicht wissen. Es darf einen **Anlass**
melden. Wer daraus eine Automatik macht, baut genau das System, das am
2026-08-19 an einem fremden Produkt kritisiert wurde: eines, das immer etwas
liefert und nie weiß, ob es stimmt.
