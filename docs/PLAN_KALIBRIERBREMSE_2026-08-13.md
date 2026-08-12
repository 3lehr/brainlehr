# Kalibrierbremse: verdrahten oder ausbauen

Stand 2026-08-13T02:00:00+0200. Aufgabe 35. Kurzer Plan, weil eine Entscheidung
mit echten Alternativen ansteht und delegiert wird.

## Der gemessene Ist-Stand

| | Befund |
|---|---|
| Aufruf | `query()` ruft `_effective_noise_mult(None, project_counts)` mit **hartcodiertem** `project_id=None` |
| Wirkung | Die Schwellenprüfung erreicht damit **kein einziges Projekt** — die Bremse greift nie |
| Selbstauskunft | Der Docstring sagt es selbst: „HERKUNFT NOCH NICHT VERDRAHTET" |
| Übersteuerungstabelle | `PROJECT_NOISE_OVERRIDES` ist **leer** und trägt den Vermerk „GERATEN, NICHT GEMESSEN" |
| Belegt seit | Commit `1711f01`, im Selbsttest als Widerspruch sichtbar |

## Die Alternativen

**A — Herkunft verdrahten.** Das Arbeitsverzeichnis auf eine Projektkennung
abbilden, damit die Schwellenprüfung ein Projekt sieht. **Bedingung, ohne die
das nicht gemacht wird:** Die Übersteuerungswerte müssen vorher **gemessen**
sein. Sonst wirkt ab dem ersten Tag eine geratene Zahl auf den Abruf — und
niemand merkt es, weil eine wirkende Bremse genauso aussieht wie eine richtige.

**B — Ausbauen.** Bremse und Tabelle entfernen. Eine fertige, getestete, nie
aufgerufene Struktur ist Ballast, der beim nächsten Lesen für wirksam gehalten
wird. Genau diese Fehlerklasse ist heute neunmal gemessen worden.

**C — Stehenlassen wie sie ist.** Abgelehnt, ausdrücklich. Sie sieht dann
weiter aus wie ein Schutz, den es nicht gibt.

## Die Entscheidungsregel statt einer Vorentscheidung

Es wird **nicht vorab** gewählt. Zuerst wird eine Frage beantwortet, und sie
entscheidet:

> **Lässt sich der Schwellenwert je Projekt aus dem vorhandenen Bestand
> messen — oder müsste er geraten werden?**

Messbar → **A**, und die gemessenen Werte kommen mit in denselben Schritt.
Nicht messbar → **B**, weil eine Bremse ohne Skala dieselbe leere Behauptung
wäre wie ein Rang ohne Einheit, gegen den heute eine Sperre gebaut wurde.

## Was bewusst nicht getan wird, samt Preis

- **Kein Schätzwert als Zwischenlösung.** Preis: Bei B ist die Arbeit von
  damals weg. Gewinn: keine Zahl im Abruf, die niemand herleiten kann.
- **Kein Umbau des Abrufpfads über diese Frage hinaus.** Der Pfad wurde gerade
  gemessen; jede weitere Änderung dort macht die Nullmessung unvergleichbar.

## Woran sich Erfolg misst

- Die Frage oben ist mit **Zahlen** beantwortet, nicht mit einer Einschätzung.
- Bei A: rot vor grün — ein Fall, in dem die Bremse greifen **muss**, war
  vorher rot. Und ein Negativfall, in dem sie **nicht** greifen darf.
- Bei B: Die Suite bleibt grün, und kein Aufrufer bleibt zurück — gezählt, nicht
  vermutet.
- In beiden Fällen: Der Selbsttest widerspricht sich danach nicht mehr selbst.

## Ergebnis (2026-08-13, Auftrag 35 ausgeführt)

**Messung statt Vorentscheidung**
(`messungen/kalibrierbremse_messung_2026-08-13.py`, lauffähig): Rohbestand
allein reicht nicht als Kalibriergrundlage. 3 von 28 Projekten reißen die
Knotenschwelle (50): `brainlehr` 99, `nasa-llis` 1638, `shared` 308. Aber die
Größe, die einen Schwellenwert wirklich eicht — ETIKETTIERTE Abruf-Fälle
(Prompt → bekanntes Ziel) je Projekt aus den echten Korpora
(`runs/echtkorpus*.json`) — bleibt weit darunter: `shared` 12, `brainlehr` 8,
`begod` 7, `fahrtenbuch` 4, `openlehr` 2, `buckeberg` 1, macht 34 von 77
gefundenen Zielen insgesamt einem Projekt zuordenbar. ADR-035 kalibrierte
den GEMEINSAMEN Wert schon mit 24 Aufgaben und nannte selbst das die Grenze
einer Parametersuche (mehr Suchraum wäre Überanpassung). Ein Bruchteil davon
je Projekt ist keine Eichung, sondern Raten mit Nachkommastellen.

**Entscheidung: B — ausgebaut.** `_effective_noise_mult()`,
`_project_node_counts()` und `PROJECT_NOISE_OVERRIDES` sind aus
`haken/knowledge_recall_hook.py` entfernt; `query()` nutzt jetzt
unbedingt den gemeinsamen `NOISE_FLOOR_MAD_MULT`. `PROJECT_CALIBRATION_
MIN_SAMPLES` bleibt als bloßer Wert stehen — `kern/messparameter.py` (in
dieser Sitzung tabu) liest ihn ungeprüft für Ergebnisdateien; das Feld dort
zu streichen ist ein eigener, hier nicht ausgeführter Schritt.

**Nebenfund, behoben:** Beim Entfernen des dafür zuständigen xfail-Eintrags
in `tests/test_alle_selftests.py` (der die Kalibrier-Widersprüchlichkeit
maskierte) wurde ein zweiter, unabhängiger, bis dahin durch denselben xfail
verdeckter Fehler sichtbar: der Embedding-Kanal-Selbsttest las `schema.sql`
relativ zu `DB`, was für die isolierte Testkopie (`BRAUCHT_ISOLIERTE_DB`)
fehlschlägt, weil dort kein `schema.sql` daneben liegt. Root-Cause-Fix: liest
jetzt `ort.WURZEL / "schema.sql"`.

**Suite**, im Vordergrund gefahren: 1068 passed, 2 skipped, 11 xfailed, 0
failed (Ausgangslage 1056/2/12/0 — xfailed exakt um den aufgelösten Fall
gesunken, kein neuer Fehlschlag; die Differenz bei passed stammt aus dem
weiterwachsenden Mehr-Sitzungs-Bestand, nicht aus dieser Änderung).
