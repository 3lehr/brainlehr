# ADR-031: Verschlüsselt wird die Spalte, nicht die Datenbank — und der Index ist der eigentliche Gegner

Datum: 2026-08-19T21:58:59+0200
Status: VORGESCHLAGEN (Umsetzung offen, Reihenfolge in `docs/PLAN_GESAMT_2026-08-13.md`)

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
