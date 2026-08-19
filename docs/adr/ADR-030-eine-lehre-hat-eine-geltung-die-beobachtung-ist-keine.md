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
