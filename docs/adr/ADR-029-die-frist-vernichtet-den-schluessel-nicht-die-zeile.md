# ADR-029: Die Frist vernichtet den Schlüssel, nicht die Zeile

**Status:** angenommen
**Datum:** 2026-08-18T20:51:22+0200
**Entscheider:** abgeleitet aus drei bestehenden Entscheidungen (siehe unten), nicht neu gefragt
**Betrifft:** `BDW-E12` bis `BDW-E16` (Aufbewahrung, Löschung, Legal Hold, Backup, Restore)

## Der Widerspruch, der aufgelöst werden muss

Die Bestandsaufnahme vom 2026-08-18 (`runs/bestandsaufnahme_vier_buendel.json`,
Commit `f1ba7ba7`) fand im Bündel Aufbewahrung eine Kollision im eigenen
Bestand:

| Stelle | tut |
|---|---|
| `knowledge_widerruf_archiv` (`schema.sql:1544`) | behält `title`, `summary`, `content` **für immer** |
| `kern/sicherungen.py` | löscht nach Alter und Anzahl |
| `kern/bereinigung.py` | **meldet** nur, löscht nicht |
| `BDW-E13-AC1` | verlangt automatische, fristbasierte Löschung über Primärdaten, Indizes, Caches und Kopien |

Das Archiv ist damit das Gegenteil einer Löschfrist — und es steht dort aus
einem guten Grund: Am 2026-08-13 wurde als Defekt gemeldet, dass
`knowledge_zurueckziehen` `content` und `summary` leert. Wer einen falschen
Eintrag korrigiert, vernichtet damit den Beweis des falschen Eintrags. Das
Archiv ist die Antwort darauf.

Eine Frist, die das Archiv leert, macht diesen Defekt rückgängig. Ein Archiv
ohne Frist macht jede Aufbewahrungsregel wirkungslos. Beide Seiten haben
recht.

## Nicht gefragt, sondern hergeleitet

Diese Entscheidung wurde **nicht** dem Betreiber vorgelegt, und das ist die
Anwendung einer Regel von heute (`L-c85b08`, auf Regelrang eskaliert): Erst
prüfen, ob bestehende Entscheidungen die Frage bereits **gemeinsam**
beantworten. Hier tun sie es, und keine von ihnen allein:

1. **`BDW-P08` / ADR-Beschluss zur Ablösung** (2026-08-18, Betreiber wörtlich:
   *„das abgeloeste nicht komplett wegschmeissen"*): Das Abgelöste bleibt
   lesbar und wird gekennzeichnet, nicht gelöscht.
2. **Der Widerrufsdefekt** (2026-08-13): Eine Korrektur darf den Beweis der
   Korrektur nicht vernichten.
3. **`kern/kundenschluessel.py`** (2026-08-18, `BDW-E09` PASS): Der Schlüssel
   entscheidet die Löschung, nicht der Datensatz. Schlüssel weg → Inhalt
   unlesbar, **Tatsache bleibt**.

Punkt 3 ist der Schlüssel im Wortsinn: Er macht 1 und 2 mit einer Löschfrist
vereinbar, ohne dass eine Seite nachgibt.

## Entscheidung

**Eine Aufbewahrungsfrist vernichtet den SCHLÜSSEL, nicht die ZEILE.**

Konkret für jeden Inhalt, der einer Frist unterliegt:

- Der Inhalt wird unter einem Schlüssel abgelegt (`kern/kundenschluessel.py`).
- Läuft die Frist ab, wird der **Schlüssel** vernichtet. Die Zeile bleibt: Kennung,
  Zeitpunkt, Grund des Widerrufs, die Tatsache, dass es den Eintrag gab.
- Der Chiffretext darf stehen bleiben. Er ist ohne Schlüssel wertlos, und sein
  Verbleib belegt, dass nicht heimlich gelöscht wurde.
- **Legal Hold** (`BDW-E14`) ist damit eine Sperre auf der Schlüsselvernichtung,
  kein Sonderweg an den Daten vorbei — und deshalb prüfbar.

Was daraus folgt und leicht übersehen wird: **Ein Backup ist damit automatisch
mitgelöscht**, ohne dass es angefasst werden muss (`BDW-E15`). Eine Sicherung,
die nur den Chiffretext enthält, wird durch die Schlüsselvernichtung genauso
unlesbar wie der Bestand. Das ist der Punkt, an dem klassische Löschfristen
regelmäßig scheitern: Sie erreichen die Kopien nicht.

## Alternativen, und warum sie verworfen wurden

**Das Archiv nach Frist wirklich leeren.** Macht den Defekt vom 2026-08-13
rückgängig — die Korrektur eines falschen Eintrags vernichtet wieder ihren
eigenen Beweis. Verworfen.

**Das Archiv von jeder Frist ausnehmen.** Dann ist die Aufbewahrungsregel eine
Absichtserklärung: Der Inhalt, den sie löschen soll, liegt vollständig in der
Tabelle daneben. Verworfen.

**Nur den `content` leeren, `title` und `summary` behalten.** Wirkt wie ein
Kompromiss, ist aber der schlechteste Weg: Der Titel eines zurückgezogenen
Eintrags trägt oft genau die Aussage, um die es geht („Frau X hat Y"). Eine
Teillöschung, die den Kern stehen lässt, erfüllt keine Frist und zerstört
trotzdem Beweismaterial. Verworfen.

## Preis, ausdrücklich

Verschlüsselte Inhalte sind **nicht durchsuchbar**. Der Volltextindex kann
keinen Chiffretext lesen. Wer einen Eintrag unter Frist stellt, nimmt in Kauf,
dass er ab diesem Moment nur noch über seine Metadaten auffindbar ist — oder
der Index muss die Klartextfelder führen, und dann ist er selbst
löschpflichtig. **Diese Frage ist offen und gehört in die Umsetzung von
`BDW-E07`**, das genau deshalb nur auf TEILWEISE steht: Daten belegt, Index
und Backup nicht.

Zweiter Preis: Ein vernichteter Schlüssel ist unwiederbringlich. Es gibt keinen
Weg zurück, und das ist beabsichtigt — sonst wäre es keine Löschung. `sichern()`
und `wiederherstellen()` existieren für den geplanten Fall, nicht für den
Notfall danach.

## Woran sich Erfolg messen lässt

Nicht an einer gebauten Frist, sondern an drei Proben:

1. Nach Fristablauf ist der Inhalt unlesbar **und** der Chiffretext
   nachweislich noch vorhanden (nicht heimlich gelöscht).
2. Nach Fristablauf ist weiter abfragbar, **dass** es den Eintrag gab.
3. Ein Legal Hold verhindert die Schlüsselvernichtung — und das schlägt fehl,
   wenn jemand den Hold umgeht, statt still durchzulaufen.

Die ersten beiden sind in `tests/test_kundenschluessel.py` bereits belegt; die
dritte fehlt und ist der nächste Bauschritt.
