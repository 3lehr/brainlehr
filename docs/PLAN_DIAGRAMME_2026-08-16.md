# Plan: Diagramme, die sich selbst erzeugen — 2026-08-16T06:05:00+0200

**Verhältnis zum geltenden Plan:** unabhängig neben `docs/PLAN_GESAMT_2026-08-13.md`
(Linien H/I/J berühren sich nicht mit dieser Frage). Löst nichts ab.

**Anlass, wörtlich vom Betreiber:** *„Wir haben inzwischen so viel Code Pfade Apps
usw. und selbst keinen Überblick mehr!"* — und die Bedingung dazu: *„Was müssen wir
machen das diese automatisch mit möglichst wenig ki entstehen und aktuell bleiben?"*

## Der gemessene Ist-Stand

| | |
|---|---|
| `hub/scripts/codemap.py` | erzeugt `CODEMAP.md` **mit Mermaid** — aber nur Flutter/Dart (`lib/`). brainlehr, hub, openlehr: nichts |
| `hub/tools/flowmaps/` | 8 Journey-Dateien + `flowmap_stale_check.py` + `serve_metroviz.py`. Nur Flutter-Apps |
| Knowledge-DB | 9795 Kanten — davon **9495** `aehnlich_bedeutung`. Als Graph wertlos (Tapete). Zeichenbar: 257 `abgeleitet_von`, 43 `lesson_mentions_file` |
| `melder/wirkkette.py` | kennt drei Stufen von „verdrahtet" — als Text, nicht als Bild |
| Verbunddiagramm | **existiert nicht** (`symbolindex.py verbund` → keine Treffer, `git log --grep` leer) |
| atelier | `WKWebView` lädt `127.0.0.1:8799`, fünf Ansichten aus `entscheidungen.html`, native Seitenleiste (`WissensraumBlick`-enum) |

## Die Reihenfolge, und wo sie bindend ist

1. **Verbundkarte** (`melder/verbundkarte.py`) — welche App/welches Repo redet mit
   welchem, worüber: DB-Datei, HTTP-Port, MCP über stdio, LaunchAgent. Fehlt komplett,
   größter Nutzen.
2. **Anzeige im atelier** — sechste Ansicht neben den fünf bestehenden.
   **Bindend nach 1:** ohne Erzeugnis nichts anzuzeigen.
3. **Codemap für Python-Repos** — `codemap.py` kann nur Dart; das Pendant über `ast`
   deckt brainlehr, hub, openlehr ab.
4. **Wirkketten als Graph** — Ausbau von `wirkkette.py`, kein Neubau. Ereignis → Hook →
   Skript → Wirkung; eine Kante, die ins Nichts läuft, ist die Fehlerklasse dieses
   Hauses in Bildform.

## Die Alternativen, samt Ablehnungsgrund

**Mermaid-Text erzeugen, im Browser rendern** — gewählt. Python schreibt Text, das
`WKWebView` rendert. Dieselben Blöcke rendert GitHub in `.md` ohne Zutun: ein
Erzeugnis, zwei Anzeigeorte.
- *Verworfen: serverseitig zu SVG rendern.* Bräuchte Node und `mmdc` — eine ganze
  Werkzeugkette mehr für dasselbe Bild.
- *Verworfen: CDN für `mermaid.min.js`.* `entscheidungen.html` enthält heute **keine
  einzige** externe Bibliothek; das bleibt so. Die Datei wird lokal abgelegt und vom
  Dienst ausgeliefert (~3 MB, vom Betreiber am 2026-08-16 ausdrücklich genehmigt).
- *Verworfen: ein Modell die Diagramme schreiben lassen.* Es ist die Frage des
  Betreibers selbst — ein erzeugtes Diagramm altert nicht, ein geschriebenes schon.
  Und ein Modellaufruf je Ansicht kostet bei jeder Änderung erneut.

**Erzeugt statt gepflegt** — wie `NODE_INDEX.md` und `melder/selbstbeschreibung.py`.
Das Erzeugnis wird **committet**, damit der Diff zeigt, was sich an der *Architektur*
geändert hat, nicht nur am Code. Das ist der eigentliche Gewinn und der Grund, warum
das Erzeugnis nicht bloß zur Laufzeit entsteht.

**Kein Veraltungs-Wächter nötig**, solange nichts von Hand gesetzt wird: was bei jedem
Lauf neu aus dem Quelltext entsteht, kann nicht veralten. Erst handgesetzte Anker
brauchen einen — `flowmap_stale_check.py` ist dafür das fertige Vorbild im Haus.

## Was bewusst NICHT getan wird

- **Kein Diagramm aus den 9495 Ähnlichkeitskanten.** Ein Graph, in dem fast jeder
  Knoten mit fast jedem verbunden ist, zeigt nichts. **Preis:** die Bedeutungsnachbarn
  bleiben unsichtbar; wer sie sehen will, braucht eine Ansicht mit Auswahl, nicht ein
  Übersichtsbild.
- **Kein Umbau von `codemap.py` auf Mehrsprachigkeit.** Ein zweites, kleines Skript für
  Python ist billiger als eine Abstraktion über zwei Sprachen. **Preis:** zwei Skripte
  mit ähnlichem Zweck.
- **Keine Interaktivität** (Zoomen, Filtern, Klicken) in Schritt 1 und 2.

## Woran sich Erfolg messen lässt

1. **Null Modellaufrufe** in der Erzeugungskette — prüfbar, nicht behauptet.
2. Die Karte nennt jede Verbindung, die es **wirklich** gibt: Gegenprobe an drei
   bekannten Kanten (atelier→8799, MCP-Klient→`brainlehr.db`, LaunchAgent→Dienst).
   Fehlt eine, ist die Karte ein Bild statt einer Karte.
3. Ein zweiter Lauf ohne Codeänderung erzeugt ein **byte-identisches** Ergebnis
   (sonst rauscht der Diff und niemand liest ihn mehr).
4. Die Karte zeigt **auch, was nicht verbunden ist** — ein Melder ohne Auslöser, ein
   Dienst ohne Klient. Eine Karte, die nur Vorhandenes zeigt, verschweigt genau den
   Befund, der dieses Haus beschäftigt.

---

## Fortschreibung 2026-08-16T06:40:00+0200 — Schritt 1 steht

`melder/verbundkarte.py` erzeugt `docs/VERBUNDKARTE.md`. Lauf über alle 27 Repos:
22 s, 27 126 Zeichen.

**Die vier Erfolgskriterien, gemessen:**

1. **Null Modellaufrufe** — das Modul importiert nur `argparse/json/os/re/sys/pathlib`.
   Kein Klient, kein `embeddings`. Prüfbar mit einem `grep` auf die Importzeilen.
2. **Die drei bekannten Kanten** sind da: `atelier → 8799` ✔, `MCP knowledge →
   knowledge_mcp_server.py` ✔, `launchd de.brainlehr.dienst → entscheidungen_server.py` ✔.
   **Die erste fehlte im ersten Lauf** — das atelier schreibt `127.0.0.1:\(port)`, der
   Regex fand nur Ziffern. Genau dafür war die Gegenprobe da; aufgelöst wird der Name
   jetzt im selben Dateitext.
3. **Byte-identisch** bei zweitem Lauf ✔ (`cmp` grün). Deshalb trägt das Erzeugnis
   auch keinen Zeitstempel.
4. **Zeigt Unverbundenes** ✔ — gestrichelt, und die Tabellen sagen „**niemand**".

### Drei Fehlalarme, die der erste Lauf produzierte, und was daraus wurde

- **„Port 0000, lauscht: bundle.js"** — eine Ziffernfolge aus minifiziertem Fremdcode.
  → erzeugte/gebündelte Dateien werden übersprungen, Ports auf 1024–65535 begrenzt.
- **Vier Kanten `openlehr_legacy → Port 4242`** — vier Dateien desselben Repos.
  → Kanten auf Repo-Ebene entdoppelt.
- **Ollama (11434) und MySQL (3307) als „Waisen"** — sie sind Fremddienste, keine
  toten Bausteine. → Waise heißt jetzt nur noch: *im Verbund gebaut und von niemandem
  gerufen*. Der umgekehrte Fall trägt die Kennzeichnung „(fremd)". Der Fehlalarm saß
  ausgerechnet in der Spalte, auf die es ankommt.

### Der Befund, den die Karte selbst liefert

**`knowledge.db` wird von 10 Repos gelesen** — darunter `_brainlehr_open`,
`_probe_head`, `openlehr_stale_2026-07-22`. Und **36 Ports** verteilen sich über einen
Verbund, in dem `fahrtenbuch`, `hub` und `openlehr_legacy` dieselben `begod/scripts/`
tragen. Das Bild ist deshalb voll, und das ist keine Schwäche der Darstellung: der
Verbund besteht zu großen Teilen aus Kopien voneinander. Wer eine engere Sicht
braucht, nimmt `--nur brainlehr hub`.

**Offen, Schritt 2:** die Anzeige im atelier. Das Erzeugnis liegt vor, die sechste
Ansicht ist noch nicht gebaut.

---

## Fortschreibung 2026-08-16T07:05:00+0200 — Einordnung korrigiert, Betreiberentscheidung

**Der Betreiber hat die Verbundkarte an der falschen Stelle gefunden**, wörtlich:
*„davon abgesehen gehört es nicht unter wissensraum! du verstehst? es steht ja eine
stufe darüber, ist info über die app, das gesamte brainlehr universum und nicht über
den wissensraum der datenbank!"*

Er hat recht, und der Fehler ist eine Ebenenverwechslung: der **Wissensraum** ist die
Sicht auf den Datenbestand (Knoten, Bedeutung, Spuren). Die Landkarten beschreiben das
**System, das diesen Bestand hält** — eine Ebene darüber. Ein sechster Blick neben
„Baum" und „Bedeutung" behauptet eine Gleichrangigkeit, die es nicht gibt.

**Entschieden am 2026-08-16 (AskUserQuestion, beide Fragen):**

- **Inhalt: alle vier.** Verbund-Infrastruktur · Aufbau der Anwendung · Code-Struktur
  je Repo · der Wissensbestand selbst.
- **Ort: eigener Punkt in der Seitenleiste**, eine Ebene über dem Wissensraum.

### Was daraus folgt

1. **Neuer Seitenleisteneintrag `landkarten`** in `SeitenleistenEintrag` — Kern, kein
   Bestandteil.
2. **Rückbau im Wissensraum:** `WissensraumBlick.verbund`, der Knopf `b5` und
   `verbundBlock` in `entscheidungen.html` verschwinden wieder. Sie waren die falsche
   Ebene, nicht bloß ein unglücklicher Platz.
3. **Eigene Seite `/landkarten`** vom Dienst statt eines Blocks in
   `entscheidungen.html`: die Landkarten teilen mit dem Wissensraum keine Bedienung,
   keine Regler und keine Zeichenfläche. Das löst nebenbei den Befund von heute früh,
   dass die laufende Punktwolke die Karte aus dem Fenster schob.
4. **Vier Erzeuger, ein Ablageort** (`docs/karten/`), damit die Auswahl in der Ansicht
   sich aus dem Vorhandenen ergibt statt aus einer gepflegten Liste.

**Unverändert gilt:** erzeugt statt gepflegt, null Modellaufrufe, kein Zeitstempel im
Erzeugnis, committet für den Diff.

---

## Fortschreibung 2026-08-16T07:20:00+0200 — drei Anforderungen des Betreibers

Wörtlich: *„1 filterbar machen · 2 interaktiv, damit meine zoomen, pfade visuell
nachzeichnen lassen, also wenn weg an A startet welches sind die möglichen wege zum
ziel, wo läuft er ins leere usw! · 3 wie bekommen wir das hin, dass die graphen auch
bei neuem code usw noch aktuell sind?"*

### Was Punkt 2 an der Bauform ändert

**Mermaid rendert, es rechnet nicht.** Ein Bild kennt keine Wege. Für „welche Wege
führen von A zum Ziel" und „wo läuft es ins Leere" braucht die Seite den Graphen als
**Daten** neben dem Bild — dieselbe Erhebung, zweite Ausgabe:

```
docs/karten/<name>.md     Mermaid, für Auge, GitHub und Diff
docs/karten/<name>.json   Knoten und Kanten, für Filter und Wegsuche
```

Beides aus **einem** Lauf, sonst laufen sie auseinander. Die Seite färbt danach die
SVG-Knoten, die Mermaid ohnehin mit Kennungen versieht — kein zweites Zeichenwerk.

- *Verworfen: eine Graph-Bibliothek (cytoscape, d3).* Sie brächte Layout und
  Interaktion mit, aber ein zweites Zeichenverfahren neben Mermaid — und die
  `.md`-Dateien, die GitHub rendert, wären dann nicht mehr dasselbe Bild wie in der
  App. **Preis:** Zoomen und Ziehen schreibe ich selbst (wenige Zeilen auf einem
  SVG-`transform`), und das Layout bleibt, was Mermaid daraus macht.
- *Verworfen: Wegsuche auf dem Server.* Ein Klick soll sofort antworten; die Daten
  liegen ohnehin schon im Browser.

### Punkt 3 ist der eigentliche — und er ist derselbe Fehler wie überall hier

Eine erzeugte Karte veraltet nicht *im Erzeugnis*, sondern **zwischen zwei Läufen**.
Wenn niemand läuft, ist sie so falsch wie eine handgezeichnete — nur mit der
Behauptung von Genauigkeit. Die Frage ist also nicht „wie erzeugen wir", sondern
**„woran hängt der Lauf?"**

Drei Kandidaten, gemessen an der Hausregel *„an welcher Stelle würde die Regel
gebrochen, und was steht dort?"*:

1. **Prüfer statt Erzeuger** — die Karten werden beim Prüflauf **neu erzeugt und mit
   den abgelegten verglichen**. Weicht etwas ab, ist die Karte veraltet, und das ist
   ein Befund mit Dateinamen. Kein Zeitplan, keine Verabredung. **Gewählt.**
2. Automatisch mitschreiben bei jedem Commit — verlockend, aber es schreibt Dateien
   in fremde Commits und verschiebt die Frage nur: wer prüft, dass der Haken hängt?
3. Zeitgesteuert — ein Lauf, der niemandem auffällt, wenn er ausbleibt. Genau die
   Bauform, die dieses Haus zwölfmal als „gebaut, laufend, wirkungslos" gemessen hat.

**Verdrahtet wird Kandidat 1 dort, wo es weh tut, bevor es nach außen geht:** als
`pre-push`-Prüfung neben `push_guard.py`. Der Befund lautet dann nicht „Karte alt",
sondern „`docs/karten/verbund.md` weicht vom Quelltext ab — `python3
melder/landkarten.py`".

**Die Abnahme dazu, sonst ist es wieder nur eine Absicht:** eine Datei ändern, die in
eine Karte eingeht, `git push` versuchen, und sehen, dass die Prüfung anschlägt. Ohne
diese Gegenprobe existiert die Durchsetzung nicht.
