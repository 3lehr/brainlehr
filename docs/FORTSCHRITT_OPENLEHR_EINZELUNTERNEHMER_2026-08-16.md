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
