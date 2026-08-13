# Wo gilt ein Satz? Der Rechtsraum als Achse

Stand 2026-08-13T12:30:00+0200. Betreiberanweisung, zum zweiten Mal: *„dann
müssen wir es abbildbar machen"*. Beim ersten Mal war es das Delfin-Beispiel —
*„bei Gesetzen gibt es mehrere Wahrheiten, jedes Bundesland, jeder Staat hat
andere Gesetze"*.

## Der gemessene Ist-Stand

| | |
|---|---|
| Feld für örtliche Geltung | **existiert nicht** |
| `kern/geltungsbereich.py` | vorhanden, behandelt **Projekt**-Zugehörigkeit (`project_id`, `lessons_learned.projects`), nicht den Rechtsraum |
| Knoten als Norm entschieden | `norm_unbefristet` 76 · `norm_befristet` 2 · `keine_norm` 169 · **`offen` 1919** |
| `norm_art` (eigen/fremd) | **0** von 2166 |
| `gilt_bis` | **2** von 2166 |

## Die Bauform — und warum sie schon da ist

Ein einzelnes Textfeld `land = "Niedersachsen"` wäre falsch, aus zwei Gründen,
die beide aus dem Bestand kommen:

**Erstens: Ein Satz gilt oft in mehreren Räumen zugleich.** Der Speicher hält
bereits einen Beleg dafür — fünf Existenzgründer-Broschüren verschiedener
Landesfinanzministerien beschreiben denselben Vorgang, und drei enthalten ein
Kapitel, das die vierte nicht hat. Die **Schnittmenge** ist Pflicht, jede
**Abweichung** ein Befund. Ein einwertiges Feld kann das nicht ausdrücken.

**Zweitens: Räume sind geschachtelt.** Gemeinde ⊂ Land ⊂ Bund ⊂ EU. Eine
Bundesnorm gilt in Niedersachsen, ohne dass „Niedersachsen" dort steht. Ein
Zeichenkettenvergleich beantwortet die Frage „gilt das hier?" deshalb falsch.

**Beides ist gelöst, wenn man das übernimmt, was brainlehr ohnehin benutzt: den
hierarchischen Pfad.** Knoten heißen `/methodik/direktiven/...`; ein Rechtsraum
heißt dann `/EU/DE/NI`. Damit ist „gilt das in Niedersachsen?" ein
**Präfixvergleich** — dieselbe Mechanik, die der Speicher für Äste schon hat.
Kein Ortstabelle, kein Auflöser, keine neue Abfragesprache.

## Die Alternativen

**A — Ein Textfeld je Knoten.** Abgelehnt: einwertig und flach, scheitert an
beiden Gründen oben.

**B — Eine eigene Tabelle für Rechtsräume mit Beziehungen.** Abgelehnt für
jetzt: Sie wäre richtig und ist zu groß für einen Bestand, in dem `norm_art`
bei 0 steht. Erst füllen, dann normalisieren.

**C — Hierarchischer Pfad als Mehrfachwert (gewählt).** Nutzt das vorhandene
Idiom, erlaubt Mehrfachgeltung, beantwortet die Enthaltensfrage per Präfix.

## Die Grenze, die diesen Plan vor der zwölften leeren Spalte bewahrt

**Nur fremde Normen bekommen einen Rechtsraum.** Eine eigene Hausregel braucht
kein Bundesland. Damit schrumpft die zu füllende Menge von 2166 auf die
Handvoll fremder Zitate — und genau das ist der Unterschied zwischen einer
Spalte, die gefüllt wird, und `norm_art` mit 0.

**Deshalb ist `norm_art` die Vorbedingung**, nicht der Rechtsraum: Ohne die
Unterscheidung eigen/fremd weiß niemand, für welche Zeilen die Angabe überhaupt
verlangt wird.

**Und: „keine Angabe" darf nicht wie „gilt überall" aussehen.** Das ist
dieselbe Doppeldeutigkeit, gegen die `norm_entscheidung` eingeführt wurde —
`norm_rang` NULL hieß einmal „Fakt" und einmal „noch nicht entschieden", und
diese Verwechslung hat einen ganzen Umbau gekostet. Ein leerer Rechtsraum ist
**unbekannt**, nicht **universell**. Wer „gilt überall" meint, schreibt `/`.

## Was bewusst nicht getan wird, samt Preis

- **Keine Liste aller Rechtsräume der Welt.** Angelegt wird, was vorkommt.
  Preis: Der Baum ist anfangs lückenhaft. Gewinn: keine gepflegte Tabelle, die
  veraltet — genau die Bauform, an der der alte Agentenindex dreifach
  auseinanderläuft (81 Dateien, 75 Einträge, 77 Zeilen).
- **Keine Auflösung von Konflikten zwischen Räumen.** Wenn Bund und Land sich
  widersprechen, wird das **ausgewiesen**, nicht entschieden. Der Speicher hält
  Widersprüche aus, das ist eine seiner erklärten Fähigkeiten.
- **Keine Rückwirkung auf die 1919 offenen Knoten.** Sie bleiben offen; das ist
  eine eigene Frage.

## Woran sich Erfolg misst

- **Rot vor grün:** Eine Anfrage „gilt in `/EU/DE/NI`" findet vorher gar nichts
  (kein Feld) und nachher eine Norm, die nur `/EU/DE` trägt — der Präfixvergleich
  ist der ganze Punkt.
- **Negativfall:** Eine Norm mit `/EU/AT` erscheint dort **nicht**.
- **Grenzwert:** leerer Rechtsraum ≠ `/`. Beide Fälle getrennt geprüft.
- **Mengenprobe:** Nach der Einführung ist die Spalte bei den fremden Normen
  gefüllt und bei den eigenen leer — gezählt, nicht angenommen.

## Aufträge, fertig zum Übergeben

**Für alle Aufträge gleichermaßen gilt:** Arbeitsort
`/Volumes/daten/Begod2026/brainlehr`, Zweig `brainlehr/b4-ausweis`. Zuerst
`CLAUDE.md` lesen, dann diesen Plan. „Sieht der Code anders aus als hier
beschrieben, halte dich an den Code und melde die Abweichung." Kein `git add
-A`, kein Push, kein `git stash`. Committen mit expliziter Pfadliste. Volle
Suite im Vordergrund mit `timeout=600000`. Datenbanknamen über `kern/speicher`.

### Schritt 1 · `norm_art` füllen — die Vorbedingung

| | |
|---|---|
| **Darf ändern** | `knowledge_mcp_server.py` (Schreibpfad `knowledge_add`/`knowledge_update`), `schema.sql`, deren Tests |
| **Tabu zusätzlich** | `melder/` (gesamt), `kern/kanten_aus_bedeutung.py`, `kern/ausschreibekatalog.py`, `docs/` |
| **Fakten** | `norm_art` existiert seit dem Auftrag 2026-08-07/08 (Knoten `dd367fd1`) als zweite, von `norm_rang` **unabhängige** Achse und ist bei **0** von 2166 gefüllt. 78 Knoten sind als Norm entschieden, 1919 stehen auf `offen`. |
| **Abnahme** | Rot vor grün: Ein neuer Knoten, der ein fremdes Gesetz zitiert, wird ohne `norm_art` **abgewiesen oder gemeldet** — vorher nicht. Negativfall: eine eigene Regel ohne fremdes Zitat läuft unverändert durch. Grenzwert: die 1919 `offen`en Knoten werden **nicht** angefasst. |

### Schritt 2 · Rechtsraum als hierarchischer Pfad

| | |
|---|---|
| **Darf ändern** | `schema.sql`, `kern/geltungsbereich.py` (Erweiterung, nicht Umbau), der Abrufpfad an der Filterstelle, deren Tests |
| **Tabu zusätzlich** | alles aus Schritt 1, sobald dieser steht |
| **Fakten** | `kern/geltungsbereich.py` löst heute die **Projekt**-Menge auf und kennt zwei Formen (`project_id` einwertig, `lessons_learned.projects` als JSON-Feld, 191 Einträge mit mehr als einem Projekt, einer davon kaputt). Diese Zweiformigkeit ist die Vorlage für den Mehrfachwert — nicht neu erfinden. |
| **Abnahme** | Präfixvergleich belegt: `/EU/DE` wird von einer Anfrage nach `/EU/DE/NI` gefunden, `/EU/AT` nicht. Leerer Rechtsraum ≠ `/`, beide getrennt geprüft. Und die Mengenprobe: gefüllt bei fremden Normen, leer bei eigenen. |
