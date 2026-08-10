# Plan: Klienten-Dokumentation als Nachschlagewerk — 2026-08-10T17:40:00+0200

Auftrag des Betreibers: „wir sollten die gesamte claude doku im wissen ablegen,
selbiges für chatgpt und hermes."

## §0 Gemessener Ist-Stand

| | |
|---|---|
| Gattung `nachschlagewerk` | existiert, 1640 Knoten (NASA-LLIS) gegen 419 Arbeitsbestand |
| Lizenzampel | `docs/FREMDBESTAENDE.md`, NASA 🟢, ESA/ASRS/FAA ⚪ ungeprueft |
| Ast fuer Klientenwissen | `/shared/claude-code-integration` besteht |
| Erster Knoten neuer Bauform | `88ecf57f` — 31 Haken-Ereignisse gegen 7 verdrahtete |

Der Anlass war eine konkrete Frage (feuert der Wiedereinstieg nach einer
Verdichtung?). Sie kostete zwei falsche Vermutungen von mir und war in einem
einzigen Abruf der Herstellerdoku beantwortet. **Der Ertrag lag nicht im
Wortlaut, sondern im ABGLEICH: 31 Ereignisse gibt es, 7 sind belegt.**

## §1 Die Bauform: destilliert mit Fundstelle, nicht Volltext

Jeder Knoten traegt (a) die Aussage, (b) die vollstaendige URL mit
Abrufzeitpunkt in `source`, (c) den Abgleich mit dem eigenen Bestand.
Gattung `nachschlagewerk`, damit die Eintraege nicht in den automatischen
Abruf drueckten und den Arbeitsbestand verduennen.

**Warum nicht Volltext, drei Gruende:**

1. **Lizenz.** NASA LLIS steht auf gruen, weil US-Regierungswerke gemeinfrei
   sind. Die Dokumentation von Anthropic und OpenAI ist es NICHT. Ein
   Volltextabzug in einem Repo, das weitergegeben werden soll, ist eine
   Altlast, die sich spaeter nicht mehr entfernen laesst — die Historie
   traegt sie weiter. Die Ampel existiert genau fuer diese Vorpruefung.
2. **Haltbarkeit.** Produktdokumentation aendert sich ohne unser Zutun. Ein
   Abzug von heute ist in drei Monaten still falsch. Ein Knoten mit
   Abrufdatum sagt, wann er galt; ein Abzug sagt es nicht.
3. **Nutzen.** Der Wert entsteht am Abgleich mit der eigenen Anlage, und der
   laesst sich nicht abschreiben. „31 gegen 7" steht in keiner Doku.

## §2 Reihenfolge

1. **Ampel vor Import.** Fuer jede Quelle Lizenz und Nutzungsbedingungen
   pruefen und in `docs/FREMDBESTAENDE.md` eintragen — VOR dem ersten Knoten.
   Bei rot oder unklar: Fundstelle verlinken, Aussage in eigenen Worten.
2. **Claude Code zuerst**, weil dort der Bedarf gemessen ist. Vorrang haben
   die Bereiche, an denen heute Fragen offen blieben: Haken (erledigt,
   `88ecf57f`), Einstellungen, MCP-Anbindung, Unteragenten, Faehigkeiten.
3. **ChatGPT/Codex danach.** Bereits im Bestand: `brainlehr-ist-globale-
   standard` und ein Testbefund zur Kontextquelle in Codex 0.144.1.
4. **Hermes zuletzt** — und mit einer offenen Frage: Im Bestand steht Hermes
   nur als „fremdes Harness" aus einem Erstlauf am 2026-08-06. Ob es dafuer
   eine oeffentliche Dokumentation gibt, ist NICHT geprueft. Wenn nein, ist
   der richtige Weg ein Messprotokoll des eigenen Laufs, keine Doku-Aufnahme.

## §3 Was NICHT getan wird — samt Preis

**Kein automatischer Doku-Abgleich (Wachhund auf Aenderungen).** Preis: Ein
Knoten kann veralten, ohne dass es auffaellt. Grund: Vor einem Waechter muss
die erste Fuellung stehen; ein Waechter ohne Bestand ueberwacht nichts.
Stattdessen traegt jeder Knoten sein Abrufdatum, und die vorhandene
Faelligkeitslogik fuer unbeobachtbare Bezuege (L-3faad7) greift.

**Keine Aufnahme in den automatischen Abruf.** Preis: Wer die Doku sucht, muss
sie ausdruecklich abfragen. Grund: Gattung `nachschlagewerk` ist genau dafuer
da — 1640 NASA-Knoten haben gezeigt, was passiert, wenn Heuhaufen und
Arbeitsbestand denselben Kanal teilen.

## §4 Woran sich Erfolg messen laesst

1. Jede aufgenommene Quelle hat VOR ihrem ersten Knoten einen Ampeleintrag.
2. Jeder Knoten nennt URL und Abrufzeitpunkt in `source` — pruefbar per
   Abfrage, nicht per Sichtpruefung.
3. Mindestens ein Knoten je Quelle enthaelt einen ABGLEICH mit der eigenen
   Anlage (wie „31 gegen 7"). Ohne den ist es eine Abschrift.
4. Der Arbeitsbestand waechst dabei NICHT: alle neuen Knoten tragen
   `gattung='nachschlagewerk'`.

## §5 Nachtrag nach der Umsetzung

Stand: 2026-08-10T20:38:19+02:00. Abgerufen wurden ausschließlich die
Herstellerseiten von Claude Code, OpenAI/Codex und Hermes Agent. Die Ampel
steht vor jeder **neuen** Aufnahme in `docs/FREMDBESTAENDE.md`; importiert
wurde kein Dokumentvolltext.

| Quelle | Geprüfter Ertrag | Bestehender eigener Abgleich |
|---|---|---|
| Claude Code | Hooks sind Lebenszyklus-Ereignisse; MCP kann lokale stdio-Server anbinden; Subagents lassen sich über Tools und Skills begrenzen. | `88ecf57f`: 31 dokumentierte Hook-Ereignisse gegen 7 verdrahtete. |
| Codex/ChatGPT | Plugins bündeln Skills, Apps und App-Templates; App-Rechte, Freigaben und Quellsystemrechte bleiben wirksam. | Kein neuer Herstellerknoten: die vorhandene Codex-Entscheidung `a13cd3f4` ist Betreiberregel, keine Herstellerdoku. |
| Hermes Agent | Die offizielle Doku und das MIT-lizenzierte Repository belegen CLI/Gateway, Skills und MCP als getrennte Bausteine. | `81729a24`: MCP-Toolfilter sind klientenseitig; der Server bleibt die Durchsetzungsstelle (`kern/werkzeugrechte.py`). |

Die vier Erfolgskriterien ergeben ausdrücklich **nicht 4/4**:

1. Die Ampel ist jetzt für alle drei Quellen geprüft, aber die vorhandenen
   Claude-/Hermes-Knoten wurden vor dem dokumentierten Ampeleintrag angelegt.
   Das ist kein nachträglich erfülltes „vorher".
2. Die beiden vorhandenen Herstellerknoten nennen URL und Abrufzeitpunkt;
   für Codex fehlt noch ein solcher Knoten.
3. Claude und Hermes enthalten einen überprüfbaren Bestandsabgleich; Codex
   noch nicht.
4. **Nicht erfüllt:** Der MCP-Schreibvertrag bietet beim Anlegen/Aktualisieren
   kein Feld `gattung`. Deshalb stehen die vorhandenen Knoten trotz externer
   Quelle als `arbeitsbestand`; ein rohes SQLite-Update wäre ein Audit-Bypass
   und wurde nicht vorgenommen.

Der nächste kleine, sichere Schritt ist daher kein weiterer Dokuimport,
sondern ein getesteter MCP-Schreibpfad für `gattung`; erst danach können die
drei Destillate korrekt als `nachschlagewerk` angelegt beziehungsweise
umklassifiziert werden.
