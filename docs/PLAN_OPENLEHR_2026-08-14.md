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

**Bindend:** H1 vor H2 und H3 (beide hängen am Vertrag). H4 vor jeder Aussage
„läuft richtig". H5 vor jedem neuen Bildschirm. H6 vor H5s Sortierung — ohne
Fristenrechnung ist „nach Wichtigkeit" nicht entscheidbar.

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
