# Plan: `openlehr_einzelunternehmer` — die erste benannte Domäneninstanz

**Stand** 2026-08-16T10:27:56+0200
**Zweig** `brainlehr/b4-ausweis`
**Grundlage** `docs/STARTPROMPT_OPENLEHR_EINZELUNTERNEHMER_2026-08-16.md`
**Bindend** ADR-007 (zwei Schichten) · ADR-013 (Domäne = Repo mit drei Teilen) ·
ADR-023 (Mitstart ist eine Einstellung im Kern) · Knoten `806132da` (Namensregel) ·
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
heute gibt (es ist eines) — es hängt an der Reihenfolge. Inhalt: was gestartet wird,
worauf es hört, woran man erkennt, dass es lebt; Pfade **nur** als Platzhalter
(ADR-023 §3), absolute Pfade werden vom Prüfer abgewiesen. Der Oberflächen-Teil
bekommt sein Feld, auch wenn er zunächst leer bleibt.

**B2 — Herkunftsregister, bevor die erste Regel übernommen wird.**
*Bindend gegenüber B4.* Nach `73f8a1c0` trägt jede aus dem Bestand übernommene
Regel `herkunft: legacy|neu` und `status: unbelegt|belegt`, ohne Vorgabewert —
fehlt eines, wird abgewiesen. Nachträglich lässt sich nicht rekonstruieren, welche
Regel damals geprüft war und welche nur mitgeschrieben wurde. Dazu ein Skript, das
die unbelegten Übernahmen zählt und die Zahl nach `STAND.md` schreibt.

**B3 — Repo anlegen, leer, mit Gerüst.** `git init`, drei Verzeichnisse nach
ADR-013, Manifest nach B1, `.venv`, Prüflauf. Kein Code aus dem Bestand.

**B4 — Erster senkrechter Schnitt: ein Beleg wird einer EÜR-Zeile zugeordnet.**
Ein einziger Fachweg von der Eingabe bis zur Zuordnung, mit eigenem Test, der gegen
eine **bewusst falsche** Fassung ROT war. Übernommen werden aus dem Bestand nur
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

**`openlehr_legacy` umbenennen und weiterbauen** (Historie per `subtree split`
mitnehmen). *Verworfen* — aber nicht leichtfertig: **ADR-013 hat genau diesen Weg
ausdrücklich gewählt** und „Neues Repo ohne Historie" verworfen, mit dem guten
Argument, `git log` sei für 43 237 Zeilen das Wertvollste, was mitkommen kann. Dem
steht die **spätere** Rang-1-Weisung `73f8a1c0` vom 2026-08-16 entgegen: der Bestand
gilt als ungeprüft, 4 575 grüne Tests belegen nur, dass der Code tut, was jemand
aufgeschrieben hat. Auflösung: Die Historie bleibt **lesbar** — `openlehr_legacy`
liegt nebenan und wird nicht gelöscht —, sie wandert nur nicht als Ausgangszustand
mit. Sie ist damit *Begründung*, nicht *Beweis*, exakt die Abgrenzung, die
`73f8a1c0` selbst zieht.
→ **Das ist eine Abweichung von einer angenommenen ADR und gehört dem Betreiber
vorgelegt** (§6, offene Frage 1). Bis zur Entscheidung wird B3 nicht ausgeführt.

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
4. **Kein Abschreiben:** `git log` des neuen Repos enthält keinen Commit, der Code
   aus `openlehr_legacy` einträgt. Übernommene Daten tragen ihre Herkunft im
   Manifest.

## §6 Offene Fragen — beide gehören dem Betreiber

1. **Historie mitnehmen oder nicht?** ADR-013 sagt ja, `73f8a1c0` legt nein nahe
   (§4). Der Plan geht von *nein* aus und hält B3 an, bis das entschieden ist.
   Fällt die Entscheidung auf *ja*, ändert sich §4 und B3, nicht der Rest.
2. **Reicht der senkrechte Schnitt B4 als erster Fachfall**, oder soll ein anderer
   den Anfang machen? Die EÜR-Zuordnung ist gewählt, weil sie den kürzesten Weg von
   Eingabe zu Ergebnis hat und das einzige Fachmodul ist, das im heutigen Manifest
   schon als `herkunft` steht.

## §7 Fortschreibung

Nach der Umsetzung wird hier nachgetragen, was anders kam als geplant und warum.
Getroffene Entscheidungen wandern zusätzlich als ADR nach `docs/adr/`.

**Der Satz, der in jeden Agentenauftrag zu diesem Plan gehört:**

> „Sieht der Code anders aus als hier beschrieben, halte dich an den Code und melde
> die Abweichung."
