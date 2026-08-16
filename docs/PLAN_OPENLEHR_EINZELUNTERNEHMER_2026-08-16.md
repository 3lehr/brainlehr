# Plan: `openlehr_einzelunternehmer` — die erste benannte Domäneninstanz

**Stand** 2026-08-16T12:59:23+0200 (Erstfassung 10:27:56, fortgeschrieben nach
der Betreiberentscheidung „Mit Historie.", Knoten `3c524455`)
**Zweig** `brainlehr/b4-ausweis`
**Grundlage** `docs/STARTPROMPT_OPENLEHR_EINZELUNTERNEHMER_2026-08-16.md`
**Bindend** ADR-007 (zwei Schichten) · ADR-013 (Domäne = Repo mit drei Teilen) ·
ADR-023 (Mitstart ist eine Einstellung im Kern) · **ADR-024 (V1 nativ,
Beschreibung plattformblind)** · Knoten `806132da` (Namensregel) ·
Knoten `73f8a1c0` (Rang 1: Bestand gilt als ungeprüft)

---

## §0 Existenzprobe — Ergebnis: es gibt nichts zu übernehmen

Gemessen 2026-08-16T10:20+0200, gesucht nach der **Sache**, nicht nach dem Namen:

| Suche | Befehl | Ergebnis |
|---|---|---|
| Verzeichnis | `ls -d /Volumes/daten/Begod2026/openlehr*` | `openlehr_legacy`, `openlehr_stale_2026-07-22`, `openlehr.worktrees` — **kein** `openlehr_einzelunternehmer` |
| Historie | `git log --all --grep=einzelunternehmer -i` | 3 Commits, **alle nur Dokumentation** (`c7b93aa9`, `bbb87fc9`, `fce68481`) |
| Verbundweit | `hub/scripts/symbolindex.py einzelunternehmer` | keine Treffer |

**Es existiert kein Code.** Der Name ist beschlossen (`806132da`), die Bauform ist
beschlossen (ADR-013, ADR-023) — gebaut ist davon nichts.

## §1 Gemessener Ist-Stand

### Was brainlehr heute schon trägt

| | gemessen |
|---|---|
| atelier (Swift) | `app/Sources/`, **36** Dateien; darunter `DomaeneImportDienst.swift`, `DienstAufsicht.swift`, `AusweisDienst.swift` |
| Domänen-Lader (Python) | `kern/domaene.py` — `importiere()` / `pruefe()` / `speichere()` / `setze_in_kraft()` / `exportiere()`, Wirkung Null verdrahtet |
| einziges Manifest im Haus | `pakete/steuer.domaene.json` — **6 Felder**: `domaene`, `bezeichnung`, `herkunft`, `stand`, `quellen` (3), `regeln` (4) |
| Dienst-Startbeschreibung | `dienst/de.brainlehr.dienst.plist` — mit Platzhalter `__REPO_PFAD__` |

**Die Lücke, und sie ist die wichtigste Zahl dieses Plans:** Das Manifest deckt von
den drei Teilen aus ADR-013 **genau einen** ab — *Wissen*. Für *Dienst* und
*Oberfläche* existiert im Format heute kein Feld. ADR-023 §2 hat das bereits
festgestellt; hier ist es der erste Schritt, weil ohne ihn nichts anderes gebaut
werden kann (§3).

### Was in `openlehr_legacy` liegt (Blaupause, nicht Vorlage)

**Zuerst die Berichtigung, weil sie den ganzen Schnitt bestimmt:**
`openlehr_legacy` ist **nicht** das openlehr-Repo, sondern das ganze
3lehr-Monorepo — 13 Apps unter `apps/`, **1566 Commits**, 318 MB `.git`, erster
Commit 2026-02-16 (gemessen 2026-08-16T10:40+0200). openlehr liegt darin als
`apps/openlehr`. „Mit Historie" heißt deshalb **Teilbaum-Schnitt**, nicht Klon.

Erhebung 2026-08-15 an Commit `21b00d8f`, Knoten `bf4c87c9`, per `create_app()`
gezählt. Heutiger Kopf des Zweigs `merge/daten-features`: `d5c24182`
(2026-08-16T05:27:54+0200).

| | |
|---|---|
| Endpunkte gesamt | 329 |
| davon echte Steuerfachlichkeit | **102** |
| **Entwicklungsassistent** (`/v1/ide`, plan_coach, orchestrator, goals, roadmap, konsile) | **56 — zweite Domäne, nicht Kern** |
| Kern (Ausweis, Rahmen, Navigation, Dienstaufsicht, Modellzugänge) | 78 |
| Bestandteil | 93 |
| `daemon/steuer/` | **102 Python-Module** (nachgezählt 2026-08-16T10:24+0200), 43 787 Zeilen laut `bf4c87c9` |

Die Zahl 102 taucht zweimal auf und meint zweierlei: 102 Steuer-**Endpunkte** und
102 Steuer-**Module**. Zufall, kein Zusammenhang — hier benannt, damit sie später
niemand verrechnet.

## §2 Was gebaut wird, und was ausdrücklich nicht

**Gebaut wird** ein eigenes Repo `openlehr_einzelunternehmer` mit den drei Teilen
aus ADR-013: *Wissen* (Manifest, reine Daten), *Dienst* (eigener Python-Prozess,
Steuerfachlichkeit), *Oberfläche* (Beschreibung — das atelier zeichnet).

**V1 ist nativ** (ADR-024, Betreiber 2026-08-16). Das atelier zeichnet mit seinen
eigenen Swift-Bausteinen; eine Weboberfläche ist ein späterer, zusätzlicher
Zeichner derselben Beschreibung. Damit sind openlehrs vorhandene Webbildschirme
endgültig nur noch Blaupause — sie zeigen, was ein Bildschirm können muss, und
werden nicht ausgeliefert.

**Nicht gebaut wird, mit Preis:**

| nicht getan | Preis |
|---|---|
| **Der Entwicklungsassistent** (56 Endpunkte) | Er bleibt vorerst nur in `openlehr_legacy` lauffähig. Er ist eine **eigene Domäne** (ADR-013) und hieße `openlehr_entwickler` — ihn hier mitzunehmen wäre genau die Falle aus `bf4c87c9`. ADR-023 führt seine Zukunft ausdrücklich als offen. |
| **Neubau des Kerns** (78 Endpunkte) | Sie werden **gelesen** als Anforderungsliste ans atelier, nicht portiert (H12). Solange das atelier eine Fähigkeit nicht hat, fehlt sie. |
| **ELSTER-Übertragung, Bank-Import, OCR** | Die teuersten Außenanbindungen bleiben im ersten Schnitt draußen. Ohne sie ist die Domäne nicht fertig, aber lauffähig und messbar. |
| **Datenmigration aus dem Bestand** | Es gibt keinen Nutzbetrieb (`f6d00767`), also nichts zu migrieren. |
| **`apps/openlehr/macos/`** | Tote Snapshot-Referenz (`6e22ac48`). Wird nicht angefasst. |

## §3 Reihenfolge, und wo sie bindend ist

**B1 — Manifestformat um *Dienst* und *Oberfläche* erweitern.**
*Bindend, und zwar als Erstes.* Begründung steht wörtlich in ADR-013 §„Was daraus
sofort folgt": ein Format nachträglich um ein Pflichtfeld zu erweitern **macht jedes
verteilte Repo ungültig**. Das Argument hängt nicht daran, wie viele Manifeste es
heute gibt (es ist eines) — es hängt an der Reihenfolge.

- **Dienst:** was gestartet wird, worauf es hört, woran man erkennt, dass es lebt.
  Pfade **nur** als Platzhalter (ADR-023 §3), absolute Pfade weist der Prüfer ab.
- **Oberfläche:** das Feld entsteht jetzt, seine Inhaltsform erst bei B4 am ersten
  echten Bildschirm (ADR-024). Was jetzt schon feststeht, ist die **Schranke**: der
  Prüfer lehnt jede Beschreibung ab, die eine Bauform oder Plattform nennt
  (`NSTableView`, `popover`, `sidebar`, `modal`, Pixel, Farben, Schriftgrößen).
  Ohne diese Regel ist der Test rot. Das ist der Preis dafür, dass ein zweiter
  Zeichner (Web) später ein Schritt bleibt und kein zweiter Bau wird.

**B2 — Herkunftsregister, bevor die erste Regel übernommen wird.**
*Bindend gegenüber B4.* Nach `73f8a1c0` trägt jede aus dem Bestand übernommene
Regel `herkunft: legacy|neu` und `status: unbelegt|belegt`, ohne Vorgabewert —
fehlt eines, wird abgewiesen. Nachträglich lässt sich nicht rekonstruieren, welche
Regel damals geprüft war und welche nur mitgeschrieben wurde. Dazu ein Skript, das
die unbelegten Übernahmen zählt und die Zahl nach `STAND.md` schreibt.

**B3 — Der Schnitt: `apps/openlehr` mit Historie herauslösen.** Entschieden am
2026-08-16T10:40+0200 (`3c524455`), damit ADR-013 unverändert.

- Werkzeug: `git-filter-repo` (liegt unter `/opt/homebrew/bin/`, gemessen). Es
  rechnet die 167 gemischten Commits (24 % von 698) auf die behaltenen Pfade um
  — das ist genau der Fall, für den es gebaut ist.
- Mit hinein, laut `schnittgrenze_2026-08-14.md`: `apps/openlehr`,
  `docs/openlehr` (12 MB), `tests/steuer` (2,1 MB, 44 Dateien), die
  Wurzel-`conftest.py`.
- **Nicht** hinein: die zwölf fremden Apps, `macshell/.build` (342 MB, ohnehin
  ungetrackt), `__pycache__`, `node_modules`.
- Danach die 24 Dateien mit absoluten Pfaden und die Auswärtsbindungen nach
  `begod/` (70 Fundstellen in 15 Dateien) auflösen — sie zeigen nach dem Schnitt
  ins Leere und sind in der Schnittgrenzen-Messung einzeln benannt.

**B3a — Register setzen, unmittelbar danach.** *Bindend, und die Reihenfolge ist
hier das Ganze.* Weil der Code jetzt physisch daliegt, sieht er
vertrauenswürdig aus; das Register aus B2 ist das einzige, was Blaupause von
Werkbank trennt. Es markiert die geerbte Fläche geschlossen als
`herkunft: legacy`, `status: unbelegt`. **Prüfbar als Satz: zwischen
Schnitt-Commit und Register-Commit liegt kein dritter Commit.**

**B4 — Erster senkrechter Schnitt: ein Beleg wird einer EÜR-Zeile zugeordnet.**
Ein einziger Fachweg von der Eingabe bis zur Zuordnung, **nativ gezeichnet**
(ADR-024), mit eigenem Test, der gegen eine **bewusst falsche** Fassung ROT war.
Hier — und erst hier — wird die Inhaltsform der Oberflächen-Beschreibung
entschieden, am echten Bildschirm statt an der Vermutung. `kern/baustein.py`
(`absatz`, `ueberschrift`, `tabelle`, `grafik`, `feld`) ist Kandidat, aber
ungemessen: er ist der Dokument-Vertrag aus ADR-010, nicht als Bildschirmsprache
erprobt. Übernommen werden aus dem Bestand nur
**Daten** (Beispielbelege, Grenzwerte, das ELSTER-Feldverzeichnis
`elster_feldkatalog_2024.json`) — **nie Testlogik**, sonst wandert der blinde Fleck
mit. Fachliche Blaupause: `euer_zuordnung.py`, gelesen, nicht kopiert.

**B5 — Der Schalter aus ADR-023.** Einstellung im Kern, vier sichtbare Zustände
(*aus* · *startet* · *läuft* · *kommt nicht hoch*), Voreinstellung *aus*. Berührt
`DienstAufsicht.swift` und die Einstellungen im atelier — **andere Dateien als
B1–B4**, darf also nebenherlaufen. Einzige Kopplung: er braucht das Dienst-Feld aus
B1.

**B6 — Fremdprobe.** Das Repo an einen anderen Ort kopieren und dort starten. Ist
irgendwo ein absoluter Pfad, fällt er genau hier auf und nirgends sonst.

## §4 Verworfene Wege

**Neues Repo ohne Historie anlegen.** *Verworfen durch den Betreiber,
2026-08-16T10:40+0200, wörtlich „Mit Historie."* (`3c524455`). Die Erstfassung
dieses Plans hatte den umgekehrten Weg vorgeschlagen und den Konflikt vorgelegt:
ADR-013 wählt ausdrücklich die Herauslösung **mit** `git log`, die spätere
Rang-1-Weisung `73f8a1c0` erklärt den Bestand für ungeprüft.

**Die Auflösung ist die Unterscheidung zweier Gegenstände, nicht ein Vorrang.**
ADR-013 redet über die *Lesbarkeit der Herkunft* — warum sieht eine Zeile so aus,
wer hat sie wann geändert. `73f8a1c0` redet über den *Belegstatus einer Regel* —
ist ihr Verhalten durch einen Test gedeckt, der gegen eine falsche Fassung rot war.
Eine mitgewanderte Historie beweist keine Regel, und ein fehlender Beleg entwertet
keine Historie. Beide gelten unverändert nebeneinander; die Last trägt B3a.

**Innerhalb von brainlehr bauen, ohne eigenes Repo.** *Verworfen*: Der Betreiber hat
das Repo als Verteilungseinheit entschieden (ADR-013, wörtlich). Ohne eigenes Repo
gibt es nichts zu importieren, und die Namensregel `openlehr_<Lage>` (`806132da`)
hätte keinen Gegenstand.

**Zuerst die 102 Steuer-Endpunkte vollständig aufnehmen, dann bauen.** *Verworfen*:
Eine vollständige Aufnahme kostet Tage und altert ab dem ersten Commit. Der
senkrechte Schnitt (B4) beantwortet dieselbe Frage — trägt die Bauform? — an einem
echten Fall und lässt sich wiederholen. Die Aufnahme wächst dann pro Schnitt.

**Steuer gegen Rest trennen.** *Verworfen als Denkfigur*: Sie schiebt den
Entwicklungsassistenten in den Kern und damit ins atelier (`bf4c87c9`). Es sind
**vier** Sorten — Steuer, Entwicklungsassistent, Kern, Bestandteil —, nicht zwei.

## §5 Woran sich Erfolg messen lässt

1. **Fremdstart:** Das Repo liegt an einem anderen Pfad als beim Betreiber, der
   Schalter steht *aus*, wird umgelegt, und der Zustand geht über *startet* nach
   *läuft*. Kein absoluter Pfad im Manifest.
2. **Nichtdefekt:** Wer den Schalter nicht umlegt, sieht *aus* und weiß, was zu tun
   ist — an keiner Stelle den Eindruck eines Defekts (Erfolgsmaß aus ADR-023).
3. **Belegstand:** Die Zahl der übernommenen Regeln mit `status: unbelegt` steht in
   `STAND.md` und ist zu jedem Zeitpunkt abrufbar. Der erste senkrechte Schnitt hat
   mindestens eine Regel von `unbelegt` auf `belegt` gebracht — mit protokollierter
   Rot-Probe.
4. **Kein stilles Erben:** Zwischen Schnitt-Commit und Register-Commit liegt kein
   dritter Commit (B3a), und nach dem Schnitt trägt keine Datei mehr einen absoluten
   Pfad oder einen Verweis nach `begod/`. Ein `git log` einer beliebigen geerbten
   Datei reicht bis 2026-02 zurück — das ist der Gegenwert der Entscheidung und
   zugleich ihr Nachweis.

## §6 Offene Fragen

1. ~~**Historie mitnehmen oder nicht?**~~ **Entschieden 2026-08-16T10:40+0200:
   mit Historie** (`3c524455`). B3 ist frei.
2. **Reicht der senkrechte Schnitt B4 als erster Fachfall**, oder soll ein anderer
   den Anfang machen? Die EÜR-Zuordnung ist gewählt, weil sie den kürzesten Weg von
   Eingabe zu Ergebnis hat und das einzige Fachmodul ist, das im heutigen Manifest
   schon als `herkunft` steht.
3. **Neu, entstanden beim Ablegen der Entscheidung:** Der Wächter
   `knowledge_nodes_normrang_herkunft_bi` verlangt für Rang 1 einen menschlichen
   Entscheider — `knowledge_add` setzt `norm_entschieden_von` aber automatisch aus
   der Modellkennung und bietet keinen Eingang für den Menschen. Eine vom
   Assistenten geführte Sitzung kann eine Betreiberweisung damit nicht als solche
   ablegen; `3c524455` steht deshalb als `keine_norm` und untertreibt seinen Rang.
   Zu beheben ist entweder der fehlende Eingang oder der Rang von Hand.

## §7 · Aufträge, fertig zum Übergeben

Ein Auftrag pro Schritt, in der Form, die dieses Haus verlangt. **B1 ist am
2026-08-16 erledigt** und steht hier als Muster für die übrigen. In jeden
Auftrag gehört wörtlich: *„Sieht der Code anders aus als hier beschrieben,
halte dich an den Code und melde die Abweichung."*

### B2 — Herkunftsregister

| | |
|---|---|
| **Darf ändern** | neues Modul im Zielrepo (`herkunft.py` o. ä.), `STAND.md` |
| **Fakten** | `73f8a1c0`: jede übernommene Regel trägt `herkunft: legacy\|neu` und `status: unbelegt\|belegt`, **ohne Vorgabewert** — fehlt eines, wird die Datei abgewiesen. Ein Skript zählt die unbelegten Übernahmen und schreibt die Zahl nach `STAND.md`. |
| **Abnahme** | Rot vor grün: ein Testvektor ohne `status` wird abgewiesen (vorher angenommen). Gegenprobe: vollständiger Vektor läuft durch. Grenzwert: `status: belegt` ohne zugehörigen Test ist ebenfalls Ablehnung. |
| **Tabu, zusätzlich** | `kern/domaene.py` (gehört B1, ist fertig) · alles unter `app/Sources/` (gehört B5) · `kern/embeddings.py` und der Suchpfad (fremde Linie, Kanalgüte) |

### B3 — Schnitt mit Historie

| | |
|---|---|
| **Darf ändern** | nur das NEUE Repo `openlehr_einzelunternehmer`; `openlehr_legacy` bleibt unangetastet |
| **Fakten** | Quelle ist das 3lehr-Monorepo `openlehr_legacy` (13 Apps, 1566 Commits, 318 MB `.git`), openlehr liegt darin als `apps/openlehr`. Werkzeug `git-filter-repo` unter `/opt/homebrew/bin/`. Mit hinein: `apps/openlehr`, `docs/openlehr`, `tests/steuer`, Wurzel-`conftest.py`. Die Wegweiser stehen gemessen in `openlehr_legacy/docs/openlehr/schnittgrenze_2026-08-14.md`: 698 berührende Commits, davon 167 gemischt; 24 Dateien mit absoluten Pfaden; 70 Fundstellen `begod/` in 15 Dateien. |
| **Abnahme** | Im neuen Repo reicht `git log` einer beliebigen geerbten Datei bis 2026-02 zurück. Keine der zwölf fremden Apps ist im Baum **oder in der Historie**. Kein absoluter Pfad, kein Verweis nach `begod/`. |
| **Tabu, zusätzlich** | `openlehr_stale_2026-07-22/` · löschen im Quellrepo · alles in brainlehr |

### B3a — Register setzen, unmittelbar danach

| | |
|---|---|
| **Darf ändern** | nur das neue Repo |
| **Fakten** | Die geerbte Fläche wird geschlossen als `herkunft: legacy`, `status: unbelegt` markiert. Grund: der Code liegt nach B3 physisch da und sieht dadurch vertrauenswürdig aus — 4 575 grüne Tests belegen nur, dass er tut, was jemand aufschrieb (`73f8a1c0`). |
| **Abnahme** | Zwischen Schnitt-Commit und Register-Commit liegt **kein dritter Commit** (`git log --oneline` zeigt sie benachbart). Die Zahl der unbelegten Übernahmen steht in `STAND.md`. |
| **Tabu, zusätzlich** | irgendeinen Vektor auf `belegt` setzen, bevor B4 seine Rot-Probe gefahren hat |

### B4 — Erster senkrechter Schnitt (Beleg → EÜR-Zeile), nativ

| | |
|---|---|
| **Darf ändern** | neues Repo (Dienst + Manifest-Oberflächenteil), `app/Sources/Atelier/` für den Zeichner |
| **Fakten** | Fachliche Blaupause ist `euer_zuordnung.py` — **gelesen, nicht kopiert** (H12). Übernommen werden nur DATEN (Beispielbelege, Grenzwerte, `elster_feldkatalog_2024.json`), **nie Testlogik**. Gezeichnet wird nativ (ADR-024). Hier wird die Inhaltsform der Oberflächen-Beschreibung entschieden; `kern/baustein.py` (`absatz`, `ueberschrift`, `tabelle`, `grafik`, `feld`) ist Kandidat, aber ungemessen. |
| **Abnahme** | Ein Test, der gegen eine **bewusst falsche** Fassung der Zuordnung ROT war und danach grün ist — die Rot-Ausgabe wird mitgeliefert. Mindestens eine Regel wandert dadurch von `unbelegt` auf `belegt`. Grenzwert: eine Buchung genau auf der Zuordnungsschwelle und je eine darunter/darüber. |
| **Tabu, zusätzlich** | Testdateien aus `openlehr_legacy` übernehmen · ELSTER-Übertragung, Bank-Import, OCR · die Sperrliste in `kern/domaene.py` aufweichen, damit eine Beschreibung durchkommt (Harness-Abweichung ist ein Befund, nicht selbst umgehen) |

### B5 — Der Schalter (ADR-023)

| | |
|---|---|
| **Darf ändern** | `app/Sources/Atelier/DienstAufsicht.swift`, Einstellungen im atelier |
| **Fakten** | Vier sichtbare Zustände: **aus** · **startet** · **läuft** · **kommt nicht hoch**. Voreinstellung **aus**. `DienstAufsicht.swift` kennt heute genau einen Dienst — den eigenen; daraus wird eine Aufsicht über *n*. Der Schalter liegt im Kern, nie in der Domäne (ADR-014). |
| **Abnahme** | Wer den Schalter nicht umlegt, sieht *aus* und einen Satz, was zu tun ist — an keiner Stelle den Eindruck eines Defekts. Umlegen führt über *startet* nach *läuft*. Ein Dienst, der nicht hochkommt, endet sichtbar in *kommt nicht hoch*, nicht in *startet*. |
| **Tabu, zusätzlich** | `kern/domaene.py` · das neue Repo · Entwicklerbegriffe im sichtbaren Text (keine Prozess-, Datei- oder Fehlernamen) |

### B6 — Fremdprobe

| | |
|---|---|
| **Darf ändern** | nichts — reine Messung; Funde werden gemeldet, nicht behoben |
| **Fakten** | Das Repo wird an einen anderen Pfad kopiert und dort gestartet. Absolute Pfade fallen genau hier auf und nirgends sonst. |
| **Abnahme** | Start gelingt am fremden Pfad; das Manifest enthält keinen absoluten Pfad. Schlägt es fehl, ist das Ergebnis ein Befund mit genannter Fundstelle, kein stiller Fix. |
| **Tabu, zusätzlich** | den Fehler unterwegs reparieren, statt ihn zu melden — sonst misst der Lauf sich selbst |

## §8 Fortschreibung

Nach der Umsetzung wird hier nachgetragen, was anders kam als geplant und warum.
Getroffene Entscheidungen wandern zusätzlich als ADR nach `docs/adr/`.

**Der Satz, der in jeden Agentenauftrag zu diesem Plan gehört:**

> „Sieht der Code anders aus als hier beschrieben, halte dich an den Code und melde
> die Abweichung."
