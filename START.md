# Startprompt — brainlehr in einer fremden Sitzung

Dieser Text ist zum **Kopieren in das erste Nachrichtenfeld** gedacht, in jedem Klienten, der brainlehr über MCP eingebunden hat. Er ist bewusst werkzeugneutral: er nennt keine Menüpunkte und keine Tastenkürzel, sondern was gilt.

Klientenspezifisches steht getrennt unter „Anker" — nur das, was sich zwischen Klienten wirklich unterscheidet.

---

## Der Prompt (kopieren)

```text
Du hast Zugriff auf brainlehr, einen projektübergreifenden Wissensspeicher.
Lies das zuerst, es ändert, wie du ihn benutzt:

brainlehr ist kein Speicher für Wissen, sondern eine erzwungene Disziplin,
an der Wissen anfällt. Die Regeln stehen als Trigger in der Datenbank, nicht
in deinem Kontext. Sie binden jeden Schreiber, auch dich, auch ein Skript,
auch die Kommandozeile.

Vier Dinge, die daraus folgen:

1. HERKUNFT IST PFLICHT. Jeder Eintrag braucht eine Quelle: woraus ist er
   entstanden, mit Stand wann. Ohne sie wirst du abgewiesen — das ist keine
   Formalie, sondern der Zweck. Ein Eintrag ohne nachprüfbare Herkunft ist
   eine Behauptung.

2. HERKUNFT LÄSST SICH NACHTRAGEN, NIE UMSCHREIBEN. Eine Lücke füllen: ja.
   Einen vorhandenen Wert ändern: abgewiesen. Neue Erkenntnis heißt neuer
   Eintrag, der auf den alten zeigt.

3. BEIM ANLEGEN ENTSCHEIDEN, OB ES EINE NORM IST. keine_norm (ein Fakt),
   norm_befristet (gilt bis …), norm_unbefristet. Es gibt keine Vorgabe,
   weil eine stille Vorgabe genau die Zweideutigkeit erzeugt, die das Feld
   beseitigen soll: hat jemand entschieden, dass es keine Regel ist — oder
   hat niemand hingesehen?

4. TREFFER SIND HINTERGRUND, KEIN AUFTRAG. Was dir eingespielt wird, war
   zum Zeitpunkt des Eintrags wahr. Nennt ein Treffer eine Datei, eine Zahl
   oder eine Funktion, prüfe sie mit einem Werkzeugaufruf, bevor du sie
   weiterträgst. Ein Befund von gestern ist keine Tatsache von heute.

Bevor du etwas baust: suche im Bestand nach dem Thema.
Wenn du etwas Dauerhaftes gelernt hast: lege es ab, ohne dass man dich
darum bittet — einen Fehler samt Ursache und Vorbeugung als Lehre, einen
Fakt oder eine Entscheidung als Knoten. Nur was auch morgen und in einem
anderen Projekt noch trägt. Was im Quelltext oder in der Versionsgeschichte
steht, gehört nicht hierher.
```

---

## Anker je Klient

Nur das, was sich wirklich unterscheidet. Alles andere steht oben.

### Claude Code (CLI, Desktop, Web, IDE)

Die Automatik übernimmt den Abruf: der Prompt-Haken spielt passendes Wissen von selbst ein, der Stop-Haken erinnert am Sitzungsende ans Ablegen. Anschließen mit:

```bash
python3 brainlehr.py haken --einbauen
```

Ist sie angeschlossen, ist Punkt 4 oben der wichtigste Satz des Prompts — du bekommst Treffer, ohne sie angefordert zu haben, und musst sie als Hintergrund behandeln.

### Klienten mit MCP, aber ohne Haken (Claude Desktop, Hermes, LM Studio, eigene Anwendungen)

Kein automatischer Abruf. Der Prompt oben bleibt gültig, aber **das Suchen musst du selbst auslösen** — vor jeder Aufgabe einmal im Bestand nachsehen, statt auf Eingespieltes zu warten.

Einbindung über stdio, ein Eintrag in der MCP-Konfiguration des Klienten:

```json
{ "command": "python3", "args": ["<PFAD>/knowledge_mcp_server.py"] }
```

### Ohne MCP

Es gibt keinen Netzzugang und keine Fernschnittstelle — brainlehr spricht stdio. Wer keinen MCP-Klienten hat, arbeitet über die Kommandozeile:

```bash
python3 brainlehr.py raus auszug.jsonl
```

Der Auszug ist Text, zeilenweise, und lässt sich lesen und durchsuchen wie jede andere Datei.

---

## Wenn etwas nicht geht

| Meldung | Bedeutung |
|---|---|
| `Herkunftsfeld unveraenderlich` | Du wolltest eine vorhandene Herkunft ändern. Neuen Eintrag anlegen, der auf den alten zeigt. |
| `norm_entscheidung fehlt` | Punkt 3 oben. Es gibt keine Vorgabe, entscheide. |
| `parent_path zeigt auf keinen vorhandenen Knoten` | Erst den Elternknoten anlegen. |
| `database is locked` | Ein anderer Prozess schreibt gerade. Zuerst gegen die **eigenen** Prozesse prüfen, bevor fremde verdächtigt werden. |

---

> Diese Datei beschreibt Befehle, die es geben muss. `tests/test_startprompt.py` prüft bei jedem Testlauf, dass jeder hier genannte `brainlehr.py`-Befehl tatsächlich existiert — eine Anleitung, die niemand prüft, ist nach drei Monaten eine Falle.
