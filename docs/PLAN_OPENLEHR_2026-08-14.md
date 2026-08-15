# Linie H — openlehr als erste Instanz auf brainlehr

Erstellt 2026-08-14T21:36:26+0200. Ausführung zur **Linie H** in
`docs/PLAN_GESAMT_2026-08-13.md`. Grundlage: `docs/STARTPROMPT_OPENLEHR_INTEGRATION_2026-08-14.md`,
ADR-007 (zwei Schichten), Betreiberauftrag *„schau an was openlehr schon hat und
wie wir es als ,plugin' in brainlehr und atelier integriert bekommen ohne
Altlasten mitzuschleppen"*.

## §0 Gemessener Ist-Stand (2026-08-14, Werkzeuglauf, nicht geschätzt)

Rohdaten: `openlehr/docs/openlehr/messung_steuer_verdrahtung_2026-08-14.json`
und `…_fachwissen_2026-08-14.json`.

| Messung | Wert |
|---|---|
| Umfang `apps/openlehr/daemon/steuer/` | **128** `.py`, **43 237** Zeilen (Startprompt sagte 102/40 651 — Code gilt) |
| **Tote Module** (0 Importeure, 0 Testnennung, 0 Route) | **0** |
| Nur von Tests erreicht | 7 (Companion-Transporte, `encryption/*`, `kalender/homeoffice.py`, `view_envelope.py`) |
| Größte Dateien | `router.py` 5841 · `api.py` 5662 · `db.py` 2526 · `ingest.py` 2404 · `chaos.py` 988 |
| 9-%-Satz (Prüfstein aus dem Papernetz) | **nirgends**. Einzige 9 ist Kirchensteuer, `tax_estimate.py:145`. USt-Werte durchweg {0, 7, 19} |

**Der Befund, der die Bauform bestimmt:** *Altlast ist hier nicht als toter Code
zu haben.* Die naheliegende Erwartung — ein Ordner voller nie erreichter Module,
die man beim Umzug einfach liegen lässt — ist gemessen falsch. Die Trennung muss
über **Belegbarkeit** laufen, nicht über Erreichbarkeit.

Und dafür liegt der Maßstab bereits im Code:

- **`euer_zuordnung.py` ist der Vertrag, den brainlehr fordert — schon gebaut.**
  Jede `VORSCHLAG_REGEL` trägt eine `fundstelle`; `_selbsttest_regeln()` läuft
  **beim Import** (Modulebene) und wirft `ValueError`, wenn die Fundstelle nicht
  wörtlich in der amtlichen Zeile steht. `AUSSCHLUSS_REGELN` ist bewusst leer,
  statt eine Ablage zu raten. Ein Konflikt bei `kleinunternehmer` ergibt `None`,
  nicht `False`. Das ist „verweigern können" im Sinne von ADR-007, in Python.
- **`classifier.py:113–137` ist der Gegenfall.** 12 Händler-/Stichwortregeln,
  Feld `fundstelle` existiert dort **nicht**, keine Testdatei `test_classifier*`
  gefunden. Immerhin gibt es den Ausgang `unklar` (Tankstelle, Kraftstoff,
  Versicherung) — die Weigerung ist da, der Beleg fehlt.
- **Die Naht liegt zwischen `ingest.py` und `api.py`.** Das OCR-Muster
  `_UST_LINE_DETERMINISTISCH_RE` liest `(\d{1,2})\s*%` — jede zweistellige Zahl.
  Die Prüfung auf {0, 7, 19} steht erst in `api.py::_ocr_rate` (Zeile ~1516).
  **Satz und Gültigkeit leben in verschiedenen Dateien**, und genau das ist die
  Fehlerklasse aus `L-473ba2` (sechs von acht Fehlern an der Naht).
- **`chaos.py:313–493` prüft bereits andere Module auf Quellenbindung**
  (`bfh_fotograf_freiberuflichkeit`). Das ist brainlehr-Funktion, die heute in
  openlehr wohnt.

## §1 Die Trennlinie, aus der Messung abgeleitet

Nach ADR-007 gehört nach **brainlehr**, was verweigern können muss. Gemessen
heißt das:

| bleibt openlehr | zieht nach brainlehr |
|---|---|
| `router.py`, `api.py`, `db.py` (Gerüst: Routen, Serialisierung, Ablage) | Der **Belegvertrag** aus `euer_zuordnung.py` — Regel ohne Fundstelle lädt nicht |
| Erfassung, Anzeige, Bedienung, PDF-Ausgabe | Die **Prüfinfrastruktur** aus `chaos.py:313–493` |
| Heuristik ohne Fachanspruch (`beleg_seiten.py` Stitching, `matching.py` `day_tolerance=7`) | Der **Gültigkeitsbereich** eines Steuersatzes (heute `api.py::_ocr_rate`) |

Nicht übernommen wird eine Kopie: der Vertrag zieht um, die Regeln bleiben, wo
sie fachlich hingehören — sie hängen sich an ihn.

## §2 Die Schritte, in bindender Reihenfolge

**H1 — erledigt.** `kern/belegvertrag.py` (brainlehr-Commit `0c2457c`, Nachbesserung
`3bc7cef`). `_belegt`/`_selbsttest_regeln` aus `euer_zuordnung.py` sind als
allgemeine Form im Kern, Import wirft `ValueError` bei verfälschter Fundstelle.

**H2 — erledigt.** openlehr-Commit `46e7fbd8` (`classifier.py`-Regeln tragen
`fundstelle`), Test `apps/openlehr/tests/test_classifier.py`.

**H3 — erledigt.** openlehr-Commit `a070b562`. `GUELTIGE_UST_SAETZE` in
`ingest.py`, Naht zu `api.py::_ocr_rate` geschlossen.

**H4 — Der Prüfkorpus mit bekanntem Sollergebnis** (F24, vom Betreiber
angenommen): erfundene Belege, deren Ergebnis feststeht, mit absichtlichen
Fallen — falscher Steuersatz, fehlende Fundstelle, doppelter Beleg. „100 %
richtig" heißt: der Korpus läuft vollständig durch **und** die Fallen werden von
selbst gemeldet. Bis dahin keine echten Daten.

**H5 — Bestandsaufnahme als E2E-Journey, vor den Bildschirmen.** F25 ist
„Steuer", aber der erste Ausschnitt ist **Erfassung, nicht Abgabe**: was liegt
überhaupt vor. Die Journey wird rot geschrieben und bleibt rot, bis die Domäne
läuft (Regel 1 aus `L-473ba2`).

**Der Zuschnitt steht seit der Antwort zu F30** (*„noch nicht geöffnet, wir
müssen auf alles vorbereitet sein"*): Die Journey deckt den **Fächer der
Behördenpost** ab, nicht einen Musterfall — Schätzungsbescheid, Erinnerung,
Zwangsgeldandrohung, Vollstreckungsankündigung, Bußgeldbescheid,
Beitragsbescheid. Ein ungeöffneter Brief ist ein Brief mit **möglicherweise
laufender Frist**.

**H6 — Die Fristenrechnung ist die erste Fachfunktion, nicht die
Steuerrechnung.** Folgt aus F27 (*„der Wichtigkeit nach abarbeiten"*) und F30:
Wichtigkeit ist hier kein Geschmack, sondern eine Rechnung aus **Frist und
Folge**. Was zuerst gebraucht wird, ist nicht „was schulde ich", sondern „was
verfällt zuerst". Eine Frist ohne belegte Rechtsgrundlage darf dabei nicht
entstehen — dieselbe Regel wie bei einer Zahl (§1).

**H7 — Die Modellgrenze, aus F19.** Betreiber: *„gerne per lokaler KI,
verlassen nur mit Zustimmung in den Einstellungen"*. Vorgabe ist damit
**lokal**; ein Auswärtsgang ist ein Einstellungsschalter, der ab Werk **aus**
steht. Eine Prüfung stellt sicher, dass kein Belegtext einen auswärtigen
Empfänger erreicht, solange der Schalter aus ist — Gegenprobe in beide
Richtungen, sonst ist der Schalter Zierde.

**H8 — „Domäne importieren" im atelier.** Betreiber, 2026-08-14: *„ich will so
haben das im atelir ein button oder menü punkt gibt domäne impoertieren!"*

**Das ändert die Integrationsform, und zwar zum Kleineren.** Bis hierher stand
im Plan ein Code-Import (openlehr importiert `belegvertrag.py`), und dafür fehlt
brainlehr die Lieferform — kein `pyproject.toml`, kein `kern/__init__.py`.
Der Menüpunkt löst das ersatzlos: **openlehr liefert kein Modul, sondern ein
Paket aus Regeln und ihren Belegen.** Die `.pth`-Frage entfällt.

**Der Importknopf ist zugleich die erste Stelle, an der ADR-007 sichtbar
wirkt:** Eine Domäne, deren Regeln keine belegte Fundstelle tragen, wird
**abgewiesen** — nicht mit einer Warnung, sondern gar nicht erst übernommen.
`kern/belegvertrag.py` ist genau dafür gebaut.

Das Paketformat, damit beide Seiten dagegen bauen können (eine JSON-Datei):

```json
{
  "domaene": "steuer",
  "bezeichnung": "Steuer und Belege",
  "herkunft": "openlehr/apps/openlehr/daemon/steuer/euer_zuordnung.py",
  "stand": "2026-08-14T21:36:26+0200",
  "quellen": {"<ziel_id>": {"bezeichnung": "…", "hinweistext": "…"}},
  "regeln": [{"id": "…", "ziel_id": "…", "fundstelle": "…", "wirkung": {}}]
}
```

`quellen` und `regeln` sind genau die zwei Argumente von `pruefe_regeln` — das
Format ist nicht erfunden, es ist der Vertrag in Dateiform.

- **H8a — erledigt.** `kern/domaene.py` (brainlehr-Commit `ec476f2`), Test
  `tests/test_domaene.py`.
- **H8b — erledigt.** Menüpunkt „Domäne importieren…" im atelier
  (brainlehr-Commit `6dba281`), `app/Sources/Atelier/DomaeneImportDienst.swift`.
- **H8c — erledigt.** `pakete/steuer.domaene.json` (brainlehr-Commit `ec476f2`)
  trägt vier Regeln als erstes echtes Paket.

**H10 — „Domäne exportieren", der Zwilling des Importknopfs.** Betreiber:
*„und wie exportieren wir unser openlehr aus dem atelier wenn es fertig ist?"*

**Was im atelier wächst, ist Wissen — also genau die Sorte, die nach ADR-012
frei reisen darf.** Der Exportknopf erzeugt ein Wissenspaket, nie ein Werkzeug.

Drei Schranken, und die erste ist der eigentliche Grund für diesen Schritt:

1. **Ein Exportpaket enthält niemals Belege.** Beim Import ist die Trennung
   zwischen Regel und Beleg gleichgültig — alles bleibt auf einem Rechner.
   **Beim Export ist sie der ganze Unterschied.** „Betriebsausgaben" ist eine
   allgemeine Fundstelle; „Rechnung Müller, 1234,56 €" sind die Daten des
   Betreibers. Die Schranke läuft **vor** dem Schreiben und verweigert im
   Zweifel — ein Paket, das versehentlich einen Betrag oder einen Namen trägt,
   ist nach der Weitergabe nicht mehr einzufangen.
2. **Vorschau, dann drückt der Mensch.** Export ist Außenwirkung im Sinne der
   Antwort aus Runde 1 (*„dinge ohne menschen versenden"* — das darf nie
   passieren). Er sieht, was im Paket steht, bevor es entsteht.
3. **Erzeugt, nie von Hand gepflegt.** Dieselbe Regel wie in ADR-011: Das Paket
   entsteht aus dem Bestand und trägt Stand und Herkunft, damit ein Empfänger
   sieht, wie alt es ist. Ein handgepflegtes Paket ist die zweite Wahrheit.

**Nicht jetzt zu bauen** — vier Regeln sind nichts zum Exportieren. Fällig wird
H10, sobald H2 die Klassifikationsregeln belegt hat, also sobald es etwas gibt,
das ein anderer brauchen kann.

**Offen, und nicht von mir zu entscheiden:** Was im atelier gemeinsam mit dem
Modell entsteht, wirft dieselbe Frage auf wie die Berufsschul-Idee — wem gehört
das Ergebnis, und wozu darf es verwendet werden. Vor der ersten Weitergabe an
einen Menschen zu klären, nicht danach.

**H12 — openlehr wird ein eigenes Repo** (ADR-013). Gemessen 2026-08-14,
Rohdaten in `openlehr/docs/openlehr/schnittgrenze_2026-08-14.md`:

| Messung | Wert |
|---|---|
| Umfang | 390 MB — davon **342 MB `macshell/.build`** (gitignored, 0 versioniert), 17 MB `__pycache__`, 15 MB `node_modules`. **Echter Inhalt ~16 MB** |
| Historie | **698** Commits berühren `apps/openlehr`, davon **167 gemischt** (24 %) |
| Auswärtsbindungen | **70** Treffer in 15 Dateien auf `begod/` über `ProjectPaths.root()`; **30+** `sys.path`-Griffe `parents[N]`; **14** Shell-Skripte mit `../../..` |
| Absolute Pfade | **24** Dateien. Zwei zeigen auf `/Users/…/Documents/OpenLehr/…` — **existiert im Repo nicht**, also schon heute gebrochen |
| Muss mit, liegt außen | `docs/openlehr` 12 MB · `tests/steuer` 2,1 MB / 44 Dateien (importiert `apps.openlehr.daemon.steuer.*` direkt) · Wurzel-`conftest.py` mit openlehr-eigener Vorrichtung · 2 CI-Dateien |
| Geheimnisse / Personenbezug | keine gefunden — **ausdrücklich keine vollständige Suche**, Fixtures nicht durchsucht |

### H12 neu gefasst 2026-08-14: Blaupause statt Herauslösung

Betreiber: *„der vorhandene Code ist ja auch Wissen, es muss nicht alles neu
gedacht werden"* — und auf die Frage nach einem neuen Repo: *„sollten wir dann
gleich ein neues repo anlegen und das alte _legacy nennen?"*

**Damit fällt die Herauslösung weg, und das ist eine Vereinfachung, keine
Einschränkung.** Historie schneidet man mit, wenn man **Code** mitnimmt. Eine
Blaupause wird am alten Ort gelesen. Die 698 Commits, davon 167 gemischte, und
der ganze `filter-repo`-Aufwand entfallen ersatzlos.

**Blaupause heißt gelesen, nicht kopiert und nicht weggeworfen.** Der Code ist
die genaueste Beschreibung der Anforderung, die existiert — genauer als jedes
Pflichtenheft, weil er unter Druck entstanden ist. `router.py` ist nicht
wertvoll, weil es routet, sondern weil es die feldgeprüfte Liste dessen ist, was
gebraucht wurde. Dazu die Historie: `git log -S` beantwortet „warum sieht diese
Zeile so aus".

**Kein `_legacy`.** In diesem Verbund ist dieses Muster zweimal schiefgegangen:
`apps/fahrtenbuch_legacy` heißt so und **ist die einzige aktive Fahrtenbuch-App**
(Umbenennung verworfen, 2005 Dateien nennen den Pfad); `apps/_legacy/` **und**
`apps/_legacy_2/` liegen parallel, weil ein Neuanfang begonnen und das Alte nur
danebengelegt wurde (`L-ad0dda`). Der Name ist ein **Versprechen über die
Zukunft**, das nichts erzwingt — wird es nicht eingelöst, lügt er.

**Stattdessen:** Das neue Repo entsteht **neu und leer**. Das alte bleibt
unangetastet unter `3lehr-monorepo/apps/openlehr`. Keine Umbenennung, weil
verschiedene Repos einander nicht in die Quere kommen. Das Alte ist nicht
„legacy", es ist die Quelle.

**Was von der Messung bestehen bleibt und wofür sie jetzt zählt:** Die 24
absoluten Pfade, die 70 `begod/`-Bindungen und die zwei Verweise auf ein
nicht existierendes Verzeichnis sind keine Umzugslast mehr — sie sind die
**Liste dessen, was beim Neubau nicht wiederholt werden darf**.

**Die Reihenfolge der alten Fassung galt für eine Herauslösung:**

1. **Zuerst die Auswärtsbindungen lösen — im Monorepo, wo die Tests noch
   laufen.** Nach dem Schnitt ist die Gegenprobe weg: Ob eine gelöste Bindung
   noch dasselbe tut, lässt sich nur dort messen, wo beide Seiten existieren.
   Wer erst schneidet, repariert danach blind.
2. **Dann schneiden**, mit Historie (`git filter-repo`), nicht kopieren.
3. **Dann erst** Manifest, Dienststart, Oberflächenbeschreibung.

**Die Entscheidung, die vor Schritt 1 steht** — und sie ist eine Sichtung, kein
Umbau: Von den 15 Dateien mit `begod/`-Bindung gehören nicht alle ins neue Repo.
`stiftshuette_parity_matrix.py` etwa liest `begod/desktop/lib/*.dart`, vergleicht
also gegen eine **andere App** — das ist Monorepo-Werkzeug und bleibt zurück.
Jede der 15 bekommt genau eine von drei Marken: *zieht um* · *bleibt* ·
*wird ersetzt*.

**Bindend:** H1 vor H2 und H3 (beide hängen am Vertrag). H4 vor jeder Aussage
„läuft richtig". H5 vor jedem neuen Bildschirm. H6 vor H5s Sortierung — ohne
Fristenrechnung ist „nach Wichtigkeit" nicht entscheidbar. H8a vor H8b und H8c.
H2 vor H10 — vorher gibt es nichts zu exportieren. **H12 Schritt 1 vor
Schritt 2**, siehe oben.

## §2a · Aufträge, fertig zum Übergeben

Ergänzt 2026-08-15, weil `tests/test_planform_ratsche.py` neue Plandateien auf
die vierzeilige Auftragsform prüft (Vorbild `docs/PLAN_MACAPP_2026-08-12.md`).
Nur die noch **offenen** Schritte (H4, H5, H6, H7, H10) bekommen einen
Auftrag — H1–H3, H8a–H8c sind erledigt und tragen oben ihre Commit-Kennung
statt eines Auftrags.

**Für alle Aufträge gleichermaßen gilt:**

- Arbeitsort `/Volumes/daten/Begod2026/brainlehr`, Zweig `brainlehr/b4-ausweis`.
- Zuerst `CLAUDE.md` (brainlehr und global) lesen, dann diesen Plan.
- „Sieht der Code anders aus als hier beschrieben, halte dich an den Code und
  melde die Abweichung."
- Kein `git add -A`, kein Push, kein `git stash`.
- `/Volumes/daten/Begod2026/openlehr` ist ein **eigenes Repo** — Änderungen dort
  laufen als eigener Auftrag in diesem Repo, nicht nebenbei aus brainlehr.
- Rot vor grün: der neue Test läuft vor der Änderung fehl, danach besteht er.

### Schritt H4 — Prüfkorpus mit bekanntem Sollergebnis

| | |
|---|---|
| **Darf ändern** | `/Volumes/daten/Begod2026/openlehr/apps/openlehr/scripts/`, neue Tests unter `/Volumes/daten/Begod2026/openlehr/tests/steuer/` |
| **Tabu zusätzlich** | `router.py`, `api.py`, `db.py` — kein Umbau des Gerüsts für diesen Schritt |
| **Fakten** | `docs/openlehr/korpus_kandidaten_2026-08-14.md`: von vier gesuchten Korpus-Sorten ist genau eine brauchbar (KoSIT xrechnung-testsuite, Apache-2.0), drei sind leer (Steuerbescheide mit Werten, Behördenpost mit Fristen, Belegdatensätze für Texterkennung). `apps/openlehr/scripts/steuer_goldkorpus_aoschu_materialize.py` und `apps/openlehr/tests/test_steuer_goldkorpus_aoschu_materialize.py` existieren bereits als Vorbild für „Korpus materialisieren + prüfen". Für Bescheide mit Frist gibt es noch keinen erfundenen Korpus — er muss neu entstehen (§6, Antwort zu F31). |
| **Abnahme** | Ein Lauf über den Korpus meldet **100 % richtig** nur, wenn alle absichtlich eingebauten Fallen (falscher Steuersatz, fehlende Fundstelle, doppelter Beleg) einzeln als gemeldet erscheinen — nicht nur die Endsumme. Negativfall: eine Falle, die stillschweigend durchläuft, lässt den Test rot bleiben. |

### Schritt H5 — Bestandsaufnahme als E2E-Journey

| | |
|---|---|
| **Darf ändern** | `/Volumes/daten/Begod2026/openlehr/apps/openlehr/tests/`, `/Volumes/daten/Begod2026/openlehr/apps/openlehr/daemon/steuer/` (nur additiv) |
| **Tabu zusätzlich** | Bestehende WP4-Tests (`test_wp4_behoerdenpost.py`) nicht umschreiben, nur erweitern |
| **Fakten** | `apps/openlehr/tests/test_wp4_behoerdenpost.py` (426 Zeilen) deckt heute **eine** Postsorte ab — Mahnung (Intake, `vendor_match`, `frist_plausibel`, Entwurf mit LLM-Fallback, `output_scan`). Der laut §6/F30 geforderte Fächer hat sechs Sorten: Schätzungsbescheid, Erinnerung, Zwangsgeldandrohung, Vollstreckungsankündigung, Bußgeldbescheid, Beitragsbescheid — fünf fehlen. |
| **Abnahme** | Ein Journey-Test pro fehlender Postsorte, rot geschrieben (Regel 1 aus `L-473ba2`: rot bleibt, bis die Domäne läuft) und mit `xfail` markiert, nie stillschweigend übersprungen. Rot-Probe: Test vor jeder Fachimplementierung ausführen, muss fehlschlagen. |

### Schritt H6 — Fristenrechnung als erste Fachfunktion

| | |
|---|---|
| **Darf ändern** | `/Volumes/daten/Begod2026/openlehr/apps/openlehr/daemon/steuer/kalender/`, zugehörige Tests |
| **Tabu zusätzlich** | `kern/belegvertrag.py` — die Fundstelle-Pflicht für eine Rechtsgrundlage wird wiederverwendet, nicht neu erfunden |
| **Fakten** | `apps/openlehr/daemon/steuer/kalender/fristen.py` (76 Zeilen) schreibt heute nur iCal-Termine (`write_deadline_event`) — keine Wichtigkeits- oder Fristrechnung aus Frist×Folge. `tests/steuer/test_kalender_fristen.py` existiert und deckt nur diesen iCal-Teil ab. |
| **Abnahme** | Eine Frist ohne belegte Rechtsgrundlage (keine Fundstelle) muss die Berechnung mit „unbekannt" verweigern, nicht mit einem Rateergebnis — Gegenprobe: Testfall ohne Fundstelle liefert `None`/Fehler, nicht eine Zahl. Grenzwertprobe: Frist heute, morgen, in der Vergangenheit. |

### Schritt H7 — Die Modellgrenze (F19: lokal, Auswärtsgang nur per Schalter)

| | |
|---|---|
| **Darf ändern** | `/Volumes/daten/Begod2026/openlehr/apps/openlehr/daemon/steuer/llm_runtime.py`, zugehörige Tests |
| **Tabu zusätzlich** | `gemma4_ocr_bridge.py` nur lesend zur Orientierung, keine Änderung in diesem Schritt |
| **Fakten** | Gemessen: `apps/openlehr/daemon/steuer/llm_runtime.py` und die Aufrufer (`api.py`, `gemma4_ocr_bridge.py`, `db.py`) sprechen ausschließlich `ollama` — kein Treffer für `gemini`, `openai`, `remote` oder einen Einstellungsschalter (`grep -rn "erlaubt_extern\|remote_erlaubt\|auswaerts\|external_allowed\|allow_remote"` liefert 0 Treffer). Die Vorgabe „lokal" ist heute Zufall der Implementierung, nicht ein geprüfter Schalter. |
| **Abnahme** | Ein neuer Schalter (Vorgabe **aus**) und ein Test, der bei ausgeschaltetem Schalter jeden Versuch, einen Belegtext an ein nicht-`ollama`-Backend zu schicken, ablehnt. Gegenprobe in beide Richtungen: Schalter aus → Versuch schlägt fehl; Schalter an → derselbe Versuch geht durch. Ohne diese Gegenprobe ist der Schalter Zierde (§0-Formulierung). |

### Schritt H10 — Domäne exportieren

| | |
|---|---|
| **Darf ändern** | `kern/domaene.py`, neue Datei `kern/domaene_export.py`, `tests/test_domaene.py` oder neue Testdatei dafür |
| **Tabu zusätzlich** | `pakete/steuer.domaene.json` nicht von Hand nachbessern — es ist bereits das erzeugte Beispiel (H8c) |
| **Fakten** | `kern/domaene.py` hat heute `importiere()` und `pruefe()` (`kern/domaene.py:26`, `:42`), aber **keine** Export-Funktion — `grep -n "export" kern/domaene.py` liefert 0 Treffer. Voraussetzung laut §2 „H2 vor H10" ist erfüllt (H2 erledigt). |
| **Abnahme** | Export erzeugt ein Paket im selben Format wie `pakete/steuer.domaene.json` (`domaene`/`bezeichnung`/`herkunft`/`stand`/`quellen`/`regeln`). Negativfall: eine Regel mit Beleg-Rohdaten statt einer allgemeinen Fundstelle (z. B. ein Betrag oder Name im `fundstelle`-Feld) muss den Export verweigern, nicht stillschweigend mitnehmen — das ist die Schranke aus §2, Punkt 1 „Ein Exportpaket enthält niemals Belege". |

## §3 Verworfene Wege

- **Modulweise Umzug nach Dateigröße** (`router.py` zuerst) — verworfen: die
  vier größten Dateien sind Gerüst, ihr Umzug bewegt Zeilen, nicht Verantwortung.
- **Toten Code als Altlast identifizieren** — verworfen, weil gemessen: 0 Treffer.
- **Papernetz (31 Knoten) sofort nach brainlehr** — zurückgestellt, F12 ist
  unbeantwortet; ein Umzug vor der Antwort erzeugt zwei Wahrheiten.
- **Steuer-Oberfläche anfassen** — nicht in dieser Linie (F10 offen).

## §4 Was bewusst nicht getan wird, samt Preis

- **Kein Umbau an `router.py`/`api.py`.** Preis: die Naht H3 wird an einer
  5662-Zeilen-Datei genäht statt in einem frischen Modul. Der Monolith bleibt
  also einer — die Boy-Scout-Regel greift erst, wenn eine Aufgabe den Block
  ohnehin anfasst.
- **Die 7 nur von Tests erreichten Module bleiben liegen.** Preis: sie können
  Attrappen sein, die nur ihren eigenen Test bedienen. Nicht gemessen.
- **Kein Anfassen der 12 ungepushten Commits** auf `merge/daten-features`.

## §5 Woran sich Erfolg misst

1. Eine Regelmenge ohne Fundstelle lädt in **keinem** der drei Module mehr
   (H1–H2), belegt durch je eine Gegenprobe, die vorher rot war.
2. „9 % MwSt" im OCR-Text erzeugt einen Klärungsfall, keine Zahl (H3).
3. Der Prüfkorpus meldet alle eingebauten Fallen von selbst (H4).

## §6 Beantwortet 2026-08-14T21:36:26+0200 (wörtlich) — und was daraus folgt

> **F29** *„kei steuerberater"* · **F30** *„noch noch nicht geöffenet, wir müssen
> auf alles vorbereitet sein!"* · **F31** *„finde einen!"* · **F19** *„gerne per
> lokaler ki, verlassen nur mit zustimmung in den einstellungen"*

**F29 — das System steht allein, und das ändert seine Aufgabe.** Ohne Berater
gibt es niemanden, dem eine Frist zusätzlich auffällt. **Mein Widerspruch,
einmal vorgebracht und danach nicht wiederholt:** Bei Steuerrückständen seit
2024 entscheidet bei einer Selbstanzeige die Reihenfolge über Straffreiheit —
das ist keine Software-Frage. Der Betreiber hat entschieden; gebaut wird
entsprechend, mit **einer** Auflage in der Bauform: Das System **markiert die
Stellen, an denen ein Berater nötig wäre**, statt sie stillschweigend zu
überschreiten. Es berät nicht und erstattet keine Selbstanzeige.

**F30 — „auf alles vorbereitet" ist eine Mengenaussage, keine Stimmung.** Der
Zuschnitt von H5 folgt daraus (Fächer statt Musterfall), H6 entsteht daraus neu.

**F31 — gesucht, ein Treffer, und drei Sorten leer.** Kandidaten in
`openlehr/docs/openlehr/korpus_kandidaten_2026-08-14.md`:

| gesucht | Ergebnis |
|---|---|
| Rechnungen | **KoSIT xrechnung-testsuite**, Apache-2.0 belegt, Sollergebnis belegt (Validator prüft Konformität) — brauchbar |
| Steuerbescheide mit Werten | **leer.** Nur unausgefüllte BMF-Vordrucke |
| Behördenpost mit Fristen | **leer** bei Originalbescheiden. Es gibt Musterbriefe der Verbraucherzentralen („Max Mustermann"), keine amtlichen Bescheide mit Sollergebnis |
| Belegdatensätze für Texterkennung | **leer** für deutsch + Lizenz + PII-frei. `German_invoices_dataset` (97 Zeilen) trägt neben Platzhaltern einen echten Namen — untauglich |

**Das ist der eigentliche Befund, nicht das Fehlen:** Genau die Dokumentsorte,
um die es geht — der Bescheid mit Werten und laufender Frist — ist öffentlich
nicht als Korpus zu haben. **H4 trägt damit die Hauptlast**, der echte Korpus
deckt nur die Rechnungsseite ab. Ein Bescheid-Korpus muss erfunden werden, und
zwar mit demselben Anspruch: bekanntes Sollergebnis, eingebaute Fallen.
ZUGFeRD/Factur-X 2.4 ist ein offener Faden — Lizenz und PII stehen auf der
Downloadseite nicht, also vor Gebrauch nachschlagen.

**F19 — Vorgabe lokal, Auswärtsgang nur per Schalter**, ab Werk aus (H7).

### Weiter offen
Keine Frage an den Betreiber mehr offen. Nächste Entscheidung entsteht erst,
wenn die Korpus-Kandidaten mit ihren Lizenzen vorliegen.
