# Beinahefehler zählen, nicht erzählen

**Angelegt** 2026-08-16T16:35:00+0200
**Anlass** Betreiberfrage auf eine Selbstkorrektur im Fluss („Leeres Log — ich habe also
nichts gemessen"): *„Notierst du auch sowas als Lehre/Fehler an brainlehr?"* — und auf die
Antwort „nein, hätte ich nicht": *„Nicht nur nachtragen, alle Chats müssen sowas melden.
Wir verarbeiten, zählen wir sowas dann in brainlehr. Aufgabe für Opus subagent?!"*

## §1 Was genau fehlt — und warum es nicht am Vergessen liegt

Der Fall: Ein Hintergrundlauf schrieb ein leeres Log, ich räumte den Prüfstand im selben
Befehl ab und hätte das Ergebnis beinahe als Beleg verbucht. Bemerkt, korrigiert,
weitergearbeitet — **und nicht erfasst.**

Die zugehörige Lehre `L-871c8a` existierte, war zweimal aufgetreten und wurde mir in
diesem Fenster **eingespielt**. Ich habe sie gelesen und den Fehler zwanzig Minuten später
gemacht. Es ist also kein Wissensproblem.

**Die Erfassungsschwelle ist das Problem.** Eine Korrektur im selben Zug fühlt sich wie
ein Arbeitsschritt an, nicht wie ein Fehler. Erfasst wird, was Schaden angerichtet hat;
„wäre um ein Haar" fällt durch — und das ist ausgerechnet die Klasse mit dem besten
Verhältnis von Erkenntnis zu Schaden.

**Gemessener Ist-Stand** (2026-08-16): 954 Lehren im Bestand. Wie viele davon
Beinahefehler sind, ist **nicht bestimmbar** — es gibt kein Feld dafür. Genau das ist der
erste zu behebende Mangel: Man kann nicht zählen, was man nicht kennzeichnet.

## §2 Was gebaut wird

Drei Teile, in dieser Reihenfolge bindend:

1. **Kennzeichnung.** Ein Beinahefehler ist eine eigene Sorte, kein Unterfall von
   `error`. Merkmal: *bemerkt und behoben, bevor Schaden entstand* — plus die Angabe,
   **woran** er bemerkt wurde. Diese zweite Angabe ist der eigentliche Ertrag: Sie
   unterscheidet „durch eine Zahl aufgefallen" von „durch Zufall" und ist damit die
   einzige Spur zu der Frage, welche Schutzform wirklich trägt.
2. **Erfassungsweg.** Ohne Aufwand im Fluss. Ein Aufruf, ein Satz, weiterarbeiten.
3. **Auszählung.** Ein Bericht, der die Frage beantwortet: Welche Fehlerklassen treten
   als Beinahefehler auf, wie oft, und **was hat sie gefangen**?

## §3 Verworfen, mit Grund

- **Neue Tabelle.** Verworfen: `lessons_learned` trägt die Struktur bereits (Beschreibung,
  Ursache, Behebung, Vorbeugung, Häufigkeit, Eskalation ab 3). Eine zweite Ablage teilt den
  Bestand und macht jede Auswertung doppelt.
- **Automatische Erkennung aus dem Transkript.** Verworfen als *erster* Schritt: Ein Modell,
  das Selbstkorrekturen aus Gesprächsverläufen erkennt, ist ein eigenes Messproblem mit
  eigener Fehlerrate — und niemand hätte eine Nulllinie, gegen die es zu prüfen wäre. Erst
  zählen, was von Hand gemeldet wird; die automatische Erkennung ist der zweite Schritt und
  bekommt dann echte Fälle als Prüfkorpus.
- **Stop-Hook, der bei jeder Sitzung fragt.** Verworfen: Es gibt bereits einen, der `/learn`
  erzwingt. Ein zweiter Zwang an derselben Stelle wird gemeinsam mit dem ersten weggeklickt.

## §4 Reihenfolge, und wo sie bindend ist

1. Feld und Erfassungsweg — **vor** allem anderen. Ohne Kennzeichnung ist jede spätere
   Auszählung eine Schätzung, und rückwirkend lässt sich nicht rekonstruieren, welcher
   Eintrag ein Beinahefehler war.
2. Rückwirkende Sichtung des Bestands: Welche der 954 Lehren sind in Wahrheit
   Beinahefehler? Das ergibt die erste Nulllinie.
3. Bericht.
4. **Erst danach** die Meldung an alle Sitzungen. Eine Aufforderung ohne Erfassungsweg
   erzeugt Meldungen im Chat, also an der flüchtigsten Stelle, die es gibt.

## §5 Was bewusst nicht getan wird

- **Keine Bewertung der Person.** Gezählt wird die Fehlerklasse und was sie gefangen hat,
  nicht wer sie gemacht hat. Eine Erfassung, die wie eine Fehlerliste gegen den Melder
  wirkt, wird sofort untergemeldet — und Untermeldung ist hier schlimmer als keine Zahl,
  weil sie wie eine Zahl aussieht.
- **Keine Vollständigkeit.** Ein Teil der Beinahefehler wird nie gemeldet, weil er nicht
  einmal bemerkt wird. Die Zahl ist eine Untergrenze und wird als solche ausgewiesen.

## §6 Woran sich Erfolg messen lässt

Nicht an der Zahl der Einträge, sondern: **Lässt sich nach vier Wochen sagen, welche
Schutzform die meisten Beinahefehler gefangen hat?** Wenn die häufigste Antwort „durch
Zufall bemerkt" lautet, ist das der wertvollste Befund — dann fehlt an dieser Stelle ein
Mechanismus.

## §7 Nachtrag nach der Umsetzung (2026-08-16T21:40:00+0200)

Gebaut wie geplant, mit zwei Entscheidungen, die der Plan offengelassen hatte.

**Kennzeichnung als zwei Spalten an `lessons_learned`, nicht als `type`-Wert.**
§2 nennt den Beinahefehler „eine eigene Sorte, kein Unterfall von `error`" — das
las sich wie ein fünfter `type`. Beim Bauen kippte es: `type` trägt die
**Fehlerklasse**, und genau die will §6 auszählen („welche Fehlerklassen treten
als Beinahefehler auf"). Ein `type='beinahefehler'` hätte die Klasse
überschrieben und die Frage unbeantwortbar gemacht. Also `beinahefehler`
(0/1) neben `bemerkt_woran` — orthogonal zur Klasse.

**`bemerkt_woran` trägt eine feste Wortliste, keinen Freitext:** `zahl`,
`test`, `waechter`, `gegenprobe`, `wissen`, `betreiber`, `zufall`. Freitext
lässt sich nicht auszählen, und §6 ist eine Auszählfrage. Erzwungen wird die
Angabe von einem **Trigger** (`lessons_learned_beinahe_check_bi/_bu`), nicht
vom Serverprozess: MCP läuft über stdio, jeder Klient hält seinen eigenen
Prozess, es gibt keinen zentralen Neustart.

**Erste Nulllinie: 16 von 959.** Kriterium bewusst eng — der Text sagt selbst,
dass es bemerkt und behoben wurde, bevor das Ergebnis jemanden erreichte, UND
er nennt das Woran. Verteilung: `gegenprobe` 9, `wissen` 3, `zahl` 2,
`waechter` 1, `zufall` 1.

**Was der Plan an dieser Stelle nicht vorhergesehen hat, und es ist der
nützlichste Fund:** Die Wendung, an der sich Beinahefehler im Bestand erkennen
lassen, ist nicht „beinahe" — dieses Wort steht meist in „fast immer" — sondern
**„Aufgefallen ist es nur, weil …"**. Sie nennt das Woran gleich mit. Der
Bestand hat also längst in der Form geschrieben, die §2 verlangt; es fehlte nur
das Feld, das sie zählbar macht.

**Und der Vorbehalt, den der Bericht selbst ausweist:** Die rückwirkende
Sichtung verlangte einen *benannten* Auslöser. Das drückt ausgerechnet
`zufall` — wer zufällig stolpert, schreibt es seltener auf — und hebt
`gegenprobe`. Die Verteilung ist erst mit Meldungen belastbar, die im Fluss
entstehen. Bis dahin ist der niedrige `zufall`-Anteil **kein** Entlastungssignal.

**Offen bleibt §4 Punkt 4:** die Meldung an alle Sitzungen. Der Erfassungsweg
steht jetzt (Werkzeugbeschreibung von `lesson_record` fordert die
Kennzeichnung ausdrücklich ein), damit ist die Voraussetzung erfüllt.
