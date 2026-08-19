# ADR-031: Verschlüsselt wird die Spalte, nicht die Datenbank — und der Index ist der eigentliche Gegner

Datum: 2026-08-19T21:58:59+0200
Status: UMGESETZT (2026-08-19, alle drei Schritte: `aa8d954d`/`689ed19f`, `6760901e`, `16ac76c1`)

## Der gemessene Anlass

`ae182bfc` und `27ac332e`, beide 2026-08-19: `kern/kundenschluessel.py`
(AES-GCM, Schlüsselvernichtung, Legal Hold) und `kern/aufbewahrung.py`
(Fristlauf, minimierter Nachweis) sind vollständig gebaut, grün getestet — und
an keinen Schreibpfad des Bestands angeschlossen. Gemessen am echten Weg:

- `knowledge_nodes.summary/.content` sind TEXT; der Klartext steht in den
  Rohbytes der Datei.
- `knowledge_fts` gibt ihn ohne Schlüssel heraus.
- Die Sicherung erbt ihn (der eigene Ordner aus `bdf329c7` trennt den Ort,
  nicht die Lesbarkeit).
- `fristlauf()` hat keinen Parameter, über den ihm der Bestand bekannt werden
  könnte.

Zwei Katalogzeilen (`BDW-E07`, `BDW-E13`) standen deshalb zu günstig und sind
seit heute FAIL.

## Die Entscheidung

**Verschlüsselt wird je Knoten die Spalte, nicht die Datei.** Kein SQLCipher,
keine verschlüsselte Ablage als Ganzes.

Grund: Eine verschlüsselte Datei ist im Betrieb entschlüsselt — sie schützt
gegen den gestohlenen Datenträger und gegen nichts sonst. Die Fragen, die
`BDW-E07` und ADR-029 stellen, sind aber pro Datensatz gestellt: *dieser*
Rechtsfall, *diese* Frist, *dieser* Schlüssel. Eine Ganzdatei-Verschlüsselung
kann auf keine davon antworten, und ein Crypto-Shredding wird mit ihr
unmöglich: Ein Schlüssel für alles ist ein Schlüssel, den man nie vernichten
kann.

## Der Punkt, an dem es scheitern wird, wenn man ihn übersieht

**Der Volltextindex.** Er ist der stille Weg um jede Spaltenverschlüsselung
herum: Solange `knowledge_fts` den Klartext indiziert, gibt er ihn heraus —
egal was in der Spalte steht. Belegt in
`tests/test_e07_bestand_im_klartext.py::test_e07_der_index_gibt_den_klartext_ohne_schluessel_heraus`.

Daraus folgt die unbequeme Hälfte der Entscheidung: **Ein verschlüsselter
Knoten ist über die Volltextsuche nicht auffindbar.** Das ist kein Mangel der
Umsetzung, sondern der Preis. Wer beides will, baut einen durchsuchbaren
Klartextindex neben die Verschlüsselung und hat sie damit aufgehoben.

Deshalb gilt Verschlüsselung **nicht** für den Arbeitsbestand, sondern nur für
Knoten, die ausdrücklich als sensibel markiert sind (WEG-Rechtsfälle aus
buckeberg, Steuerdaten aus openlehr — genau die Daten Dritter, die
`CLAUDE.md` als die härtere Grenze dieses Repos benennt). Für sie ist
Unauffindbarkeit richtig; für den Arbeitsbestand wäre sie eine Selbstverstümmelung.

## Verworfene Alternativen

- **Ganzdatei (SQLCipher).** Siehe oben: beantwortet keine der gestellten
  Fragen, verhindert Crypto-Shredding.
- **Blindindex über Wortstämme** (durchsuchbare Verschlüsselung). Löst das
  Auffindbarkeitsproblem und leckt dabei die Wortverteilung — bei
  Rechtsfällen mit Namen ist das kein theoretischer Angriff. Nicht ohne Not.
- **Nichts tun und die ACs streichen.** Wäre ehrlich, aber `BDW-E07` steht auf
  MUSS und begründet sich aus fremden Daten, nicht aus einem Wunsch.

## Reihenfolge, bindend

1. Spalte `chiffre` und Markierung `sensibel` ins Schema, **bevor** der erste
   sensible Knoten geschrieben wird. Nachträglich lässt sich nicht
   rekonstruieren, welcher Knoten sensibel gemeint war.
2. FTS-Trigger so ändern, dass sensible Knoten **nicht** indiziert werden —
   **vor** dem ersten verschlüsselten Schreibvorgang, sonst steht der
   Klartext bereits im Index und bleibt dort.
3. Erst danach `fristlauf()` an den Bestand hängen.

Schritt 2 vor Schritt 3: Ein Fristlauf, der den Schlüssel vernichtet, während
der Index noch Klartext hält, erzeugt einen Nachweis über eine Löschung, die
nicht stattgefunden hat. Das ist schlimmer als keine Löschung.

## Woran der Erfolg gemessen wird

`tests/test_e07_bestand_im_klartext.py` schlägt um: Die heute grünen
Zusicherungen („Klartext lesbar") müssen für einen sensiblen Knoten rot
werden, für einen normalen grün bleiben. Der Test ist absichtlich so gebaut,
dass er das anzeigt, statt angepasst zu werden.


## Nachtrag nach der Umsetzung (2026-08-19)

Drei Dinge kamen anders, als diese ADR sie beschrieb:

1. **Die Reihenfolge war wichtiger als gedacht, aber aus einem anderen Grund.**
   Hier stand, der Index sei der Gegner. Beim Bauen zeigte sich: es sind
   **sechs** Orte, nicht einer. Unter der Insert-Zeile von `knowledge_add`
   reichen Vektor, Hinweisindex, Ähnlichkeitssuche, Wikilink-Auswertung und
   das Zugriffsprotokoll denselben Text weiter — `log_access` schreibt
   `summary` und `content` wörtlich in `affected_row`. Wer an der Spalte
   verschlüsselt, verschlüsselt die Spalte und streut den Klartext daneben.
   Die Ersetzung sitzt deshalb ganz am Anfang der Funktion, und der Test sucht
   in den **Rohbytes** der Datei statt in einer Spalte. Knoten `1fdbd6fb`.

2. **Der Schlüssel brauchte einen eigenen Ort, nicht nur eine eigene Spalte.**
   Diese ADR sagte dazu nichts. `kern/schluesselablage.py` legt ihn in eine
   getrennte Datei: läge er im Bestand, wäre jede Sicherung eine Bytekopie von
   Schloss **und** Schlüssel, und eine Vernichtung wäre aus jeder alten
   Sicherung wiederherstellbar — genau das, was Crypto-Shredding verhindern
   soll.

3. **Zwei Trigger statt einem waren falsch.** Der erste Entwurf teilte den
   UPDATE-Trigger in zwei mit je einer `WHEN`-Bedingung. SQLite sichert die
   Reihenfolge zweier AFTER-UPDATE-Trigger nicht zu; lief der einfügende
   zuerst, löschte der andere den Eintrag gleich wieder. Jetzt ein Trigger mit
   der Bedingung am `WHERE`. Lehre `L-7a5c00`.

**Das Erfolgsmaß von oben ist eingelöst**, aber anders verteilt als
angekündigt: `tests/test_e07_bestand_im_klartext.py` bleibt grün und beschreibt
weiterhin den gewöhnlichen Knoten (Klartext, Absicht). Der Gegenbeleg für den
sensiblen Knoten steht in `tests/test_adr031_sensible_knoten_ohne_index.py`
(16 Fälle). Der eine Test, der umschlagen musste, ist umgeschlagen und wurde
**umgedreht statt angepasst**: er verlangt jetzt, dass der Schreibweg da ist.
