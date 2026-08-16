# Fortschritt: `openlehr_einzelunternehmer`

Laufendes Protokoll zum Plan `PLAN_OPENLEHR_EINZELUNTERNEHMER_2026-08-16.md`.
Fortschritte **und** Rückschläge, in der Reihenfolge, in der sie eintraten.
Angelegt 2026-08-16T14:20+0200 auf Betreiberanweisung *„arbeite alle schritte
autonom ab, dokumentiere fortschritte und rückschläge"*.

---

## B1 — Manifestformat um *Dienst* und *Oberfläche* · **fertig**

Commit `37a938e3` (brainlehr). Rot 11/2, danach 58 grün.

**Zwei eigene Fehler unterwegs:**

1. **Der erste Baumdurchlauf flachte verschachtelte Schlüssel ab.** Ich trennte
   Schlüssel und Werte und ersetzte dabei den inneren Schlüssel durch den
   äußeren — `breite_px` und `farbe` kamen durch, zwei von fünf Bauform-Fällen.
   Behoben: der Durchlauf ist flach, Schlüssel **und** Werte sind Text. Die
   Bauform steht im Wert (`popover`), das Aussehen im Schlüssel (`breite_px`) —
   wer nur eine Seite liest, übersieht die Hälfte.
2. **Mein Test war gröber als der Prüfer.** Er verlangte für Farbwerte das Wort
   „Bauform"; der Prüfer sagte zu Recht „Aussehen". Bauform ist die falsche
   *Ebene*, ein Farbwert die falsche *Zuständigkeit*. Geändert wurde der Test.

**Was der Pflichtcharakter sofort kostete** — und das war der Beweis, dass die
Reihenfolge stimmt: `exportiere()` und drei Testvorlagen brachen, weil sie
unvollständige Pakete bauten. Hier billig, nach dem ersten fremden Import nicht.

## B2 — Übernahmeregister · **fertig**

Commit `05f249e8` (brainlehr), `kern/uebernahmeregister.py`. Rot 12/3, danach 16 grün.

**Der erste rote Lauf war wertlos und wurde verworfen:** ein `ImportError`
zeigt, dass eine *Datei* fehlt, nicht dass eine *Regel* fehlt. Ersetzt durch
eine arglose Fassung, die jeden Vektor annimmt — erst dagegen ist der rote Lauf
ein Beleg.

**Mangel gefunden, als die Tests schon grün waren**, und zwar an der *Ausgabe*
statt am Rückgabewert: `--zaehle` meldete „1 belegt" für einen Vektor, den die
Prüfung ablehnt. Diese Zahl geht nach `STAND.md` — sie hätte die Schuld kleiner
gemacht, also genau in die Richtung, gegen die der Mechanismus gebaut ist.
Beanstandete zählen jetzt getrennt.

## B3 — Schnitt mit Historie · **fertig, nach drei Rückschlägen**

Ergebnis: `/Volumes/daten/Begod2026/openlehr_einzelunternehmer`, **847 Commits**,
Historie ab 2026-04-29, `.git` **7,3 MB**, keine Fernverweise.

### Rückschlag 1 — der Klon brach ab

`git clone --no-local` endete mit *„possible repository corruption on the remote
side"*. `git fsck` war jedoch **sauber**. Die Ursache stand im Klon-Log, nicht
im Fehlertext: *„could not fetch 42a5c924… from promisor remote"*.

**Befund: `openlehr_legacy` ist ein Teilklon** (`partialclonefilter=blob:none`,
`promisor=true`), sein Herkunftsort ist `github.com/Lehrmeister/3lehr-monorepo` —
nicht das Desktop-Verzeichnis, das ältere Notizen nennen. Die Objekte liegen
nicht alle lokal.

**Das hätte den Plan still beschädigt.** „Mit Historie" aus einem Teilklon heißt:
die Historie ist nicht vollständig da. Ein Schnitt hätte fehlende Blobs
mitgenommen oder abgebrochen — im schlechteren Fall unbemerkt.

### Rückschlag 2 — und die Entwarnung, gemessen statt gehofft

Ein lokaler Klon (ohne `--no-local`, also ohne `upload-pack`) lief durch.
Gezählt: **21 fehlende Objekte von 28 301**. Jedes einzelne davon liegt in einem
Pfad, den der Schnitt **wegwirft** (`docs/PROMPT_*`, `scripts/`, `CLAUDE.md`,
`.claude/`, `tools/`) — keines unter `apps/openlehr`, `docs/openlehr`,
`tests/steuer` oder `conftest.py`. Erst damit war der Schnitt zulässig.

### Rückschlag 3 — der Schnitt gelang, das Ergebnis war trotzdem falsch

Nach `git filter-repo`: 1566 → 847 Commits, Baum sauber — aber `.git` blieb bei
**295 MB** für ~16 MB Quelltext. `gc --prune=now` änderte nichts.

**Ursache:** Der 300-MB-Pack trägt eine `.promisor`-Datei. Git räumt
Promisor-Packs grundsätzlich nicht ab, weil es sie für den lazily gefüllten
Speicher hält. Die geschnittene Historie steckte längst im 6-MB-Pack daneben;
die fünf größten Objekte (51, 40, 39, 35, 27 MB) waren **von keinem Ref
erreichbar**.

**Behoben ohne Handarbeit an Packdateien:** ein frischer Klon nimmt nur
Erreichbares mit — 295 MB → 7,3 MB, 847 Commits unverändert. Die zwölf Zweige
wurden vorher lokal angelegt, damit ihre Historie das Lösen der Herkunft
überlebt.

**Warum das nicht bloß Kosmetik ist:** Ein Domänen-Repo soll importiert werden
(ADR-013). 295 MB unerreichbarer Fremdhistorie hätten jeden Empfänger begleitet
— und was einmal in der Historie eines verteilten Repos liegt, ist nicht mehr
einzufangen (ADR-013, Punkt 2).

### Ein eigenes Abnahmekriterium war falsch

Der Plan verlangte *„`git log` reicht bis 2026-02 zurück"*. Gemessen reicht sie
bis **2026-04-29** — das ist openlehrs erster eigener Commit. Die 2026-02 war
der erste Commit des **Monorepos**, also eines anderen Gegenstands. Das
Ergebnis ist richtig, mein Maßstab war es nicht; der Plan ist berichtigt.

### Abnahme B3

| Kriterium | Ergebnis |
|---|---|
| Historie reicht zurück | 2026-04-29 (openlehrs erster Commit) ✅ |
| Fremde Apps in der Historie | `fahrtenbuch`, `openhood`, `pflegelotse`, `drg`, `markusx25`, `wohlairr`, `begod-homepage` — je **0 Commits** ✅ |
| Fernverweise | 0 ✅ |
| Absolute Pfade / `begod/` gelöst | **nein — offen**, siehe unten |

## B3a — Register unmittelbar nach dem Schnitt · **fertig**

Commit `021d4f8`, sitzt **direkt** auf dem geerbten Kopf `97bff23` — zwischen
Schnitt und Register liegt kein dritter Commit, wie der Plan es verlangt.

Ein Sammeleintrag `register/_geerbte_flaeche.json` deckt die ganze Fläche ab:
585 Python-Dateien, 130 Module unter `daemon/steuer`, 45 Testdateien. Geprüft
mit dem Werkzeug aus B2: **1 Übernahme, 1 unbelegt**.

Er wird nie auf `belegt` gesetzt. Er verschwindet, wenn jede einzelne Regel
ihren eigenen Eintrag mit Test und Rot-Probe hat.

## Offen und ausdrücklich nicht erledigt

- **Die Auswärtsbindungen.** 24 Dateien mit absoluten Pfaden, 70 Fundstellen
  `begod/` in 15 Dateien (gemessen in `docs/openlehr/schnittgrenze_2026-08-14.md`).
  Sie zeigen seit dem Schnitt ins Leere. Der Plan führt das unter B3; es ist
  **nicht** gemacht.
- **`pyproject.toml` und die CI-Dateien** blieben im Monorepo — sie waren
  geteilt. Das neue Repo hat keine Testkonfiguration.
- **Ein Testlauf im neuen Repo hat nie stattgefunden.** Der Stand ist „geerbt,
  nicht ausgeführt", nicht „läuft".

## B4 — Erster senkrechter Schnitt · **fachlich fertig, Zeichner offen**

Commit `cd95578` (Domänen-Repo). Rot 7/3 gegen eine arglose Fassung, danach 10 grün.

**Der Fachweg:** eine gerechnete Größe bekommt eine amtliche EÜR-Zeile
vorgeschlagen, samt Fundstelle. **Die Regel, die den Schnitt trägt:** Die
Fundstelle muss *wörtlich* im amtlichen Text stehen — sonst ist sie kein Zitat,
sondern eine Behauptung, und es gibt keinen Vorschlag.

**Blaupause eingehalten:** `euer_zuordnung.py` (410 Zeilen, DB-gebunden) wurde
gelesen, nicht kopiert; die neue Fassung hängt an einer anderen Schnittstelle.
Übernommen wurden **nur Daten** — der amtliche Feldkatalog mit 61 Feldern.

**Die Beschreibungsform ist damit entschieden, nicht mehr vermutet** (das war
B4s Auftrag): Rollen tragen (`tabelle`, `spalten`, `art: betrag|zitat|text`),
Bauformen braucht die Beschreibung nicht. Das Manifest besteht brainlehrs
Prüfer aus B1 einschließlich der Plattformblindheit nach ADR-024 — geprüft
gegen den **echten** Prüfer, nicht gegen eine Nachbildung.

**Erste Regel von `unbelegt` auf `belegt`**, mit Test *und* Rot-Probe.
Registerstand: 2 Übernahmen, 1 unbelegt, 1 belegt.

**Offen:** der native Zeichner. Der Bildschirm ist beschrieben und nirgends zu
sehen.

## B5 — Der Schalter (ADR-023) · **nicht angefasst, fremd gehalten**

`DienstAufsicht.swift` steht im Agentenregister auf Sitzung `13451282`, Agent
`a8eab9c98545a8272`, **ohne Stopp-Ereignis** — letzter Eintrag
2026-08-15T04:58, also vor 33 Stunden. `HauptFenster.swift` hält Sitzung
`1d718e1f`, letzter Eintrag vor 7 Stunden.

Die Hausregel ist eindeutig: *Agent ohne Stopp-Ereignis → läuft noch → Finger
weg.* 33 Stunden sehen nach einer Sitzung aus, die ohne Stopp-Eintrag endete —
aber das ist eine Vermutung, und die Regel kennt diese Ausnahme nicht. **B5
bleibt liegen und gehört dem Betreiber.**

## B6 — Fremdprobe · **fertig, mit dem lehrreichsten Befund des Tages**

**Erster Lauf: 10 Tests grün am fremden Pfad. Das war ein Fehlbefund.**

Grün waren sie, weil mein eigener Test `brainlehr` unter
`/Volumes/daten/Begod2026/brainlehr` fest verdrahtet hatte — und dieser Pfad
existiert auf *dieser* Maschine weiterhin. Die Fremdprobe hat nicht das Repo
gemessen, sondern die Maschine, auf der sie lief. Auf einem fremden Rechner
wäre sie rot gewesen, ohne dass die Probe es gemerkt hätte.

Das ist genau die Fehlerklasse „der Prüfstand misst mit": Ein Aufbau, der
schmaler ist als die Wirklichkeit, liefert eine Zahl statt eines Fehlschlags.

**Behoben** (Commit `91fc942`): Der Prüfer der Trägerschicht wird über
`BRAINLEHR_PFAD` gesucht, ersatzweise als Nachbarverzeichnis. Fehlt er, wird
der Test **übersprungen** — mit dem Satz *„ÜBERSPRUNGEN heißt UNGEPRÜFT, nicht
in Ordnung"* im Grund. Ein stiller Durchlauf wäre hier schlimmer als ein
Fehlschlag.

**Abnahme wiederholt:** am fremden Pfad 9 grün, 1 übersprungen mit sichtbarem
Grund, kein absoluter Pfad mehr, Dienst `exit 0`.

## Gesamtstand

| Schritt | Stand |
|---|---|
| B1 Manifestformat | fertig (`37a938e3`) |
| B2 Übernahmeregister | fertig (`05f249e8`) |
| B3 Schnitt mit Historie | fertig, drei Rückschläge |
| B3a Register nach dem Schnitt | fertig (`021d4f8`) |
| B4 Senkrechter Schnitt | fachlich fertig (`cd95578`), Zeichner offen |
| B5 Schalter | **blockiert** — fremd gehaltene Dateien |
| B6 Fremdprobe | fertig (`91fc942`) |

**Was ausdrücklich nicht erledigt ist:** die Auswärtsbindungen im geerbten Code
(24 Dateien mit absoluten Pfaden, 70 Fundstellen `begod/`), `pyproject.toml`
und CI, ein Testlauf über den geerbten Bestand, und der native Zeichner.

---

## Nachtrag: die offenen Punkte aus dem Gesamtstand, abgearbeitet

### Testkonfiguration und erster Lauf über den geerbten Bestand · **fertig**

Commit `6a66179` (Domänen-Repo). Der Stand war „geerbt, nicht ausgeführt" —
jetzt ist er gemessen: **347 grün, 3 rot.**

**Vier Läufe bis dahin, jeder an einem anderen Hindernis** — und das Hindernis
selbst ist der Befund: **Fünf Pakete, die der Code importiert, stehen in keiner
der beiden `requirements`-Dateien** — `cryptography`, `caldav`, `icalendar`,
`python-multipart`, `keyring`. Ohne sie sammelt pytest **42 von 45** Dateien
nicht einmal ein. Jeder, der diese Domäne importiert, steht vor demselben Wall.
Genau dafür war der erste Lauf im neuen Repo Pflicht und nicht Kür.

**Lücke, nicht überspielt:** `pyarrow` baut auf Python 3.14 nicht (kein Wheel),
der Goldkorpus-Test bleibt **ungelaufen**. Ungelaufen heißt ungeprüft, nicht
bestanden.

**Die drei Fehlschläge — meine erste Einordnung war falsch und ist berichtigt.**
Ich hatte `test_ascii_umschrift_scan` als Schnittfolge bezeichnet; das war
geraten. Gemessen überschreiten **drei Dateien ihre eigene Grundlinie**:
`classifier.py` (8 statt 6 Umlaute), `finanzamt/typenkatalog.py` (2 Umlaute und
7 Bindestriche statt 0/0), `finanzamt_intake.py` (2 statt 1). **Vorbestehend,
nicht vom Schnitt.** Alle drei Fehlschläge sind damit Fachbefunde, keiner nennt
einen absoluten Pfad oder `begod/`.

Die Grundlinie wird **nicht** angehoben — das wäre genau der Freispruch, gegen
den eine Ratsche gebaut ist. Der Befund gehört zur unbelegten Fläche.

**Und was die Zahl nicht bedeutet:** 347 grüne geerbte Tests machen nichts
`belegt`. Der Registerstand bleibt 1 belegt, 1 unbelegt.

### Auswärtsbindungen · **gemessen, bewusst nicht behoben**

Im neuen Repo gezählt, statt die Zahl aus der Schnittgrenzen-Messung
weiterzutragen — und sie stimmt dort nicht mehr:

| | Schnittgrenze 2026-08-14 (Monorepo) | gemessen im neuen Repo |
|---|---|---|
| Dateien mit absoluten Pfaden | 24 | **12** |
| Verweise nach `begod/` | 70 Fundstellen in 15 Dateien | **144 Zeilen in 50 Dateien** |

Beide Zahlen weichen ab, in **beide** Richtungen: Die absoluten Pfade sind
weniger, weil ein Teil der gezählten Dateien gar nicht mitkam. Die
`begod/`-Verweise sind mehr, weil die alte Zahl nur `daemon/` erfasste, nicht
`tests/` und `scripts/`. Eine übernommene Zahl hätte hier in beide Richtungen
falsch geführt.

**Bewusst nicht behoben, mit Grund:** 50 Dateien umzubauen heißt zu
entscheiden, was `begod/` ersetzt — ein Zustandsverzeichnis, ein Ort für
Zugangsdaten, ein Wissensordner. Das ist eine Entwurfsentscheidung an Code, der
**vollständig `unbelegt`** ist und dessen Tests den Umbau nicht decken würden.
Ihn im Schnelldurchgang zu machen, erzeugt genau den stillen Schaden, gegen den
das Register gebaut ist. **Der Umbau gehört an die einzelne Übernahme** (wie
B4 sie vorführt), nicht in einen Sammellauf.

### B5 · **weiterhin blockiert, erneut geprüft**

`DienstAufsicht.swift`: Agent `a8eab9c98545a8272`, letzter Eintrag
2026-08-15T04:58, **weiterhin kein Stopp-Ereignis**. Unverändert Finger weg.

## Endstand

| Schritt | Stand |
|---|---|
| B1 Manifestformat | fertig |
| B2 Übernahmeregister | fertig |
| B3 Schnitt mit Historie | fertig |
| B3a Register danach | fertig |
| B4 Senkrechter Schnitt | fachlich fertig, Zeichner offen |
| B5 Schalter | **blockiert — fremd gehalten** |
| B6 Fremdprobe | fertig |
| Testlauf geerbter Bestand | fertig — 347 grün, 3 rot |
| Auswärtsbindungen | gemessen, Umbau bewusst vertagt |

**Was der Betreiber entscheiden muss:** B5 (fremd gehaltene Datei) · der native
Zeichner · ob das Domänen-Repo nach GitHub geht (Außenwirkung, nicht meine
Entscheidung) · der Rang von `3c524455` und `460725f0`.


---

## Ablage

Zustand des Domänen-Repos als Wissensknoten `378587c6`. Lehren: `L-4f01fb`
(Teilbaum-Schnitt aus einem Teilklon), `L-31fce7` (Fremdprobe maß den
Wirtsrechner), `L-1c5e26` (Identität der Quelle nicht gemessen).
