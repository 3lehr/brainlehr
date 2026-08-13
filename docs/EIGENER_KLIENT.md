# Was ein eigener Klient könnte, was dieser nicht kann

Angelegt 2026-08-13T13:25:00+0200 auf Betreiberanweisung: *„alles vorbereiten,
um eigenen Client zu bauen und diesen mitzudenken … Primär aber hier zuerst für
Claude entwickeln. Gedankengänge, die mit Claude nicht funktionieren, für
eigenen Client notieren."*

## Wie diese Datei zu lesen ist

**Keine Wunschliste.** Aufgenommen wird nur, was **gemessen** an einer Grenze
gescheitert ist — mit Datum, Fundstelle und dem Satz, der sie belegt. Ein
Eintrag der Form „wäre schön" gehört nicht hierher.

**Die Prüffrage vor jedem Eintrag**, aus der Hausregel vom 2026-08-13: *„MEIN
Aufbau kann das nicht, weil ich X nicht gemessen habe"* — hält der Satz in
dieser Form nicht, war es nie eine Grenze, sondern ein gescheiterter Versuch.

**Die Reihenfolge bleibt:** Zuerst für diesen Klienten bauen. Diese Datei ist
das Auffangbecken für das, was dabei liegen bleibt — nicht die Begründung, ihn
zu verlassen.

## Gemessene Grenzen, Stand 2026-08-13

### 1 · Kein blockierender Haken vor einem Subagenten

`SubagentStart` **kann nicht blockieren**, und seine Ausgabe (`systemMessage`,
stderr) ist **nur dem Nutzer sichtbar, nicht dem Modell**. Ein Wächter dort
meldet, verhindert nichts und sagt mir nichts.

**Wozu wir ihn bräuchten:** Peer Review (Aufgabe 97) — ein Auftrag, der meine
eigene Schlussfolgerung schon enthält, soll abgewiesen werden, **bevor** der
Agent losläuft. Der Umweg über `PreToolUse` auf das Agent-Werkzeug funktioniert
und ist der richtige Weg hier; er hängt aber am Werkzeugnamen statt am Vorgang.

*Eigener Klient:* ein Vorgangs-Haken mit Vetorecht und modellsichtbarer
Rückmeldung.

### 2 · Werkzeugergebnisse sind nicht änderbar

`PreToolUse` kennt `updatedInput` — die **Eingabe** lässt sich vor der
Ausführung ändern. Für die **Ausgabe** gibt es kein Gegenstück; `PostToolUse`
darf beobachten und Kontext danebenlegen, nicht ersetzen.

**Wozu wir es bräuchten:** Der Ausschreibekatalog (Aufgabe 65) will die
**Anfrage** erweitern — das geht. Aber ein Ergebnis zu kürzen, zu maskieren oder
mit seiner Herkunft zu versehen, bevor es in meinen Kontext läuft, geht nicht.
Genau das wäre der Hebel gegen den größten gemessenen Posten: **71 % des
Kontexts sind Werkzeugausgaben.**

*Eigener Klient:* ein Filter zwischen Werkzeug und Modell, in beide Richtungen.

### 3 · Kein Haken für Laden und Entladen einer Fähigkeit

In der Referenz existiert nichts dergleichen. Am nächsten kommen
`InstructionsLoaded` (nur `CLAUDE.md` und `.claude/rules/*.md`) und
`ConfigChange` mit `config_source: "skills"` — beides meldet eine **Änderung der
Quelle**, nicht das Laden einer Fähigkeit im Gespräch.

**Wozu wir es bräuchten:** Die Betreiberfrage vom 2026-08-13, ob brainlehr
sagen kann, *wann eine Fähigkeit geladen oder entladen werden sollte*. Die Daten
dafür lägen vor; der Auslöser fehlt.

### 4 · Kein zentraler Neustart, kein gemeinsamer Serverzustand

MCP über stdio: **jeder Klient startet seinen eigenen Prozess** beim
Sitzungsbeginn. Gemessen: bis zu 30 gleichzeitige Serverprozesse, davon welche
seit **zwei Tagen** laufend. Eine Codeänderung erreicht sie nie.

**Was das heute kostet:** Am 2026-08-13 blockierte ein fehlerhafter Trigger
fremde Sitzungen. Die Datei war korrigiert, die **Datenbank** nicht — und die
laufenden Prozesse hätten selbst dann den alten Code getragen. Guards gehören
deshalb als Datenbank-Trigger gebaut, nicht in den Serverprozess, und jede
Codeänderung muss rückwärtskompatibel sein.

*Eigener Klient:* ein Serverprozess, den alle Sitzungen teilen — oder wenigstens
ein Signal, das laufende Prozesse zum Nachladen zwingt.

### 5 · Regeln werden beim Start gelesen, nicht laufend

`CLAUDE.md` landet beim Sitzungsstart und bei der Verdichtung im Systemprompt.
Ändert der Betreiber sie mitten in der Sitzung, arbeitet das Modell weiter mit
dem alten Stand. **Heute dreimal geschehen** — abgefangen nur durch einen
eigens gebauten Melder, der die Änderung bemerkt und zum Nachlesen auffordert.

*Eigener Klient:* Regeln als lebende Quelle statt als Abzug.

### 6 · Eingespielter Kontext ist unverbindlich

Der Wissens-Abruf spielt bei jeder Nachricht Treffer ein. Sie sind
**Hintergrund**, kein Auftrag — und werden regelmäßig übergangen. Gemessen an
den eigenen Antworten: **10 von 12** geprüften Fällen trugen Inhalt aus dem
eingespielten Block, ohne ihn als Quelle zu nennen.

*Eigener Klient:* eingespielter Kontext mit Quittungspflicht — gelesen,
verworfen mit Grund, oder verwendet mit Zuschreibung.

### 7 · Der Subagent hat nur einen Kanal, und der führt durch mich

Ein Subagent kann seinen Befund **ausschließlich** über seinen Abschlussbericht
loswerden. Er landet in meinem Kontext oder nirgends. Wenn ich ihn falsch lese
oder der Agent im Wartezustand endet — heute mehrfach geschehen — ist der Befund
weg.

*Eigener Klient:* ein Subagent schreibt direkt in Speicher und Aufgabenliste,
nicht durch den Orchestrator hindurch.

### 8 · Abhängigkeiten zwischen Aufgaben sind Prosa

Die Aufgabenliste kennt Status, aber keine **Sperre**. Alle bindenden
Reihenfolgen dieses Tages — `80` vor `69`, `78` vor `73`, `98` vor `92` — stehen
als Text in der Beschreibung. Nichts hindert daran, sie zu übergehen.

*Eigener Klient:* Abhängigkeit als Feld, nicht als Satz.

## Was ausdrücklich KEINE Grenze ist

Damit diese Datei nicht zur Ausrede wird — drei Dinge, die ich zeitweise für
Grenzen hielt und die keine sind:

- **„PostToolUse liefert nichts"** — meine Messung vom 2026-08-13. Die Referenz
  weist dem Ereignis `additionalContext` und den Exit-2-Rückkanal ausdrücklich
  zu. Der Widerspruch ist **ungeklärt**, nicht entschieden; vermutlich habe ich
  in Wahrheit Punkt 2 gemessen (Ausgabe nicht änderbar).
- **„Last lässt sich nicht nachstellen"** — falsch, sie ist herstellbar.
- **„Der Simulator kann das nicht"** — dreimal behauptet, dreimal widerlegt.
  Simulatoren sind Prozesse des Wirtssystems, also greifen dessen Mittel.
