# ADR-003: Die Erstanlage trägt dasselbe Schema wie der Betrieb

**Datum:** 2026-08-10T12:30:00+0200
**Status:** angenommen
**Betrifft:** `schema.sql`, `knowledge.db` im Betrieb, `tests/test_brainlehr_umzug.py`

## Lage, gemessen

`tests/test_brainlehr_umzug.py::test_erstanlage_traegt_dasselbe_schema_wie_der_betrieb`
war rot und nannte zwei Tabellen, die eine Neuanlage aus `schema.sql` nicht
trägt, der Betrieb aber schon: `knowledge_versions` und `schema_migrations`.

Ein frischer Klon von `github.com/3lehr/brainlehr` (`3f3a791`) plus
`python3 schnellstart.py` läuft durch (Rückgabewert 0, Gegenprobe „was kannst
du" antwortet mit 10 Treffern). Der Unterschied ist also kein Installations-
fehler, sondern eine stille Abweichung im Schema.

Ein Vergleich der Tabellenlisten meldet sechs Unterschiede. Vier davon sind
keine: `lost_and_found` und `mycel_naehe|narbe|richtung` sind der Rohauswurf
der Bergung vom 2026-08-07; `kern/doctor.py` und der Test schließen sie
namentlich aus. Wer die Sechs für den Befund hält, hat sein eigenes Prüfwerkzeug
gemessen statt der Sache.

## Entscheidung

**`knowledge_versions` wird samt seiner beiden Trigger aus dem Betrieb
entfernt, statt in `schema.sql` nachgebaut zu werden.** Er ist ein reiner
Zähler (id, version), 2029 Zeilen, alle auf 1 — und niemand liest ihn: die
einzige Fundstelle im ganzen Baum ist ein erklärender Kommentar in
`migrationen/migrate_fassungen.py`. Abgelöst wurde er am 2026-08-09 von
`knowledge_fassungen`, das die alte Fassung tatsächlich aufhebt. Zwei Trigger
auf jedem Schreibweg zu unterhalten, deren Ergebnis niemand abruft, ist Kosten
ohne Nutzen.

**`schema_migrations` wird umgekehrt in `schema.sql` aufgenommen**, samt einer
Marke für die Erstanlage. Grund ist die Reihenfolge, nicht der Bestand: Die
Marke muss stehen, **bevor** die erste Migration läuft — danach lässt sich
nicht mehr feststellen, welcher Stand vorher galt. Genau das ist im Betrieb
passiert und steht dort wörtlich in der einzigen Zeile der Tabelle
(„nachtraeglich markiert -- welcher Stand vor dieser Marke galt, ist nicht mehr
feststellbar"). Dieser Grund gilt bei null Datensätzen wie bei einer Million.

## Verworfen

- **Beide Tabellen in `schema.sql` nachbauen.** Verworfen: baut einen Zähler
  ohne Leser in jede künftige Installation ein und macht die Ablösung durch
  `knowledge_fassungen` wieder rückgängig.
- **Beide aus dem Betrieb entfernen.** Verworfen: nimmt `schema_migrations`
  seine einzige Aufgabe, nämlich vor der nächsten Migration schon dazusein.
- **Den Test lockern (Unterschiede erlauben).** Verworfen: er ist das einzige
  Werkzeug, das diese Klasse von Abweichung überhaupt findet — sie fällt sonst
  lautlos aus, weil eine Neuanlage keinen Fehler meldet, sondern nur anders ist.

## Folgen

Eine Neuanlage und ein gewachsener Betrieb tragen wieder dasselbe Schema. Jede
Messung, die gegen eine frische Instanz fährt, misst damit dieselbe Sache wie
im Betrieb — vorher war das nicht so, ohne dass es jemandem auffallen konnte.

Preis: Die Fassungszählung aus `knowledge_versions` ist weg. Sie war für keinen
Zweck mehr in Gebrauch; wer eine Zählung braucht, bekommt sie aus
`knowledge_fassungen`, wo auch der Inhalt steht.
