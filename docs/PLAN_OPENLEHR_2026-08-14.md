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

**H1 — Der Belegvertrag wird brainlehr-Kern.** `_belegt` / `_selbsttest_regeln`
aus `euer_zuordnung.py` als allgemeine Form nach `brainlehr/kern/` (Arbeitsname
`belegvertrag.py`): eine Regelmenge lädt nur, wenn jede Regel ihre Fundstelle
wörtlich in einer benannten Quelle wiederfindet; ein Widerspruch ergibt
„unbekannt", nie den bequemen Wert. `euer_zuordnung.py` benutzt danach den Kern
und behält sein Verhalten — Gegenprobe: Fundstelle in einer Regel verfälschen →
Import muss weiter `ValueError` werfen.

**H2 — `classifier.py` an den Vertrag.** Jede der 12 Regeln bekommt entweder
eine Fundstelle oder den Ausgang `unklar`. **Rot vor grün:** zuerst ein Test, der
gegen den heutigen Stand rot ist (Regelmenge ohne Fundstelle lädt heute
klaglos). *Hängt an H1.*

**H3 — Die Naht schließen.** Ein Steuersatz entsteht in `ingest.py` nur noch als
gültiger Wert oder als Klärungsfall; die Menge {0, 7, 19} steht an **einer**
Stelle und wird von beiden Seiten gelesen. Gegenprobe: OCR-Text mit „9 % MwSt"
→ Klärungsfall, nicht stille Übernahme. *Hängt an H1.*

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

- **H8a** `kern/domaene.py`: lesen, gegen den Vertrag prüfen, annehmen oder mit
  **Grund** ablehnen. Rot vor grün: eine Domäne mit unbelegter Regel muss
  abgewiesen werden, und der Grund muss die Regel benennen.
- **H8b** Menüpunkt „Domäne importieren…" im atelier, Dateiauswahl, Ergebnis in
  Nutzersprache — *„Die Regel ‚Bewirtung' nennt keine Quelle"*, nicht ein
  Fehlertext aus dem Inneren.
- **H8c** openlehr exportiert seine Steuerregeln als erstes echtes Paket. Erst
  damit ist der Weg belegt statt behauptet.

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
