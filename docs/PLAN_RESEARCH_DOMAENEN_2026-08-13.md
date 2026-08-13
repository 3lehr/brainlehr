# Vier neue Domänen: Mietrecht, Erneuerbare Energien, Steuerrecht, Pflegelotsen

Angelegt 2026-08-13T20:10:00+0200. Reine Recherche, kein Bauauftrag —
nichts importiert, nichts heruntergeladen, keine andere Datei angefasst.

Betreiberauftrag, wörtlich: *„aber die die ganze mitrecht und erneuerbare
einergien nehmen wir ins wissen mit auf! dann steuerrecht und die domaene der
pflegenlotsenapp! erstelle einen research subplan dafuer!"* Reihenfolge wie
genannt: Mietrecht · Erneuerbare Energien · Steuerrecht · Pflegelotsen-Domäne.
**Ausdrücklich verworfen im selben Zug:** die Epstein-Akten („epstein ist
raus") — hier nicht wieder aufgenommen.

Dieser Plan **ergänzt** `docs/PLAN_RECHTSDOMAENE_2026-08-13.md` (WEG-Recht,
WEG-Verwaltungsrecht, GModG/GEG, Gerichtsstand Amtsgericht Ettlingen /
Landgericht Karlsruhe) und `docs/RECHERCHE_BEISPIELBESTAENDE_2026-08-13.md`
(Kriterien für einen Bestand, Schaufenster gegen Prüfkorpus). Beide werden
hier vorausgesetzt, nicht wiederholt.

## Korrektur gegenüber der früheren Recherche

`RECHERCHE_BEISPIELBESTAENDE_2026-08-13.md` führte „deutschsprachig" als
Kriterium **über die Nutzer**. Der Betreiber hat dem widersprochen — niemand
hat festgelegt, dass die ersten brainlehr-Nutzer deutschsprachig sind. Für
diesen Plan gilt die Korrektur: Sprache ist **keine Zielgruppenannahme**,
sondern eine gemessene **technische Einschränkung des Trigramm-Tokenizers**
im Abrufkanal — bei fremder Zeichensystematik (z. B. japanische
Zweizeichenwörter) liefert er nachweislich null Treffer, unabhängig davon,
wer die Frage stellt. Die vier Domänen unten sind deutsches Bundes-/Landesrecht
bzw. SGB-Recht und damit ohnehin deutschsprachig verfasst — die Einschränkung
wird hier benannt, weil sie den Abrufkanal betrifft, nicht weil sie den
Nutzer eingrenzt.

## Gemessener Ist-Stand vor der Recherche (`brainlehr.db`, `knowledge_nodes`)

| Suchbegriff | Treffer | Befund |
|---|---|---|
| `Miete` | 0 | keine Mietrechts-Knoten |
| `WoEigG` | 0 | (bereits in PLAN_RECHTSDOMAENE festgestellt) |
| `Steuer` | 33 | ausschließlich **Architektur-/Projektwissen zu openlehr** (RAG/LoRA, FTS5-Index, Vue-3-ADRs, Café-International-Konsil) — **kein** materielles Steuerrecht |
| `Pflege` | 18 | ausschließlich **ADR-Zusammenfassungen zur App-Architektur** von Pflege-Lotse (Drift/SQLite, Study-Mode, Kreuzreferenz-Graph, Medikamenten-Scope) — **kein** SGB-XI-Regelwissen |
| `SGB` | 0 | kein Sozialrecht-Regelwissen |
| `EStG` | 15, aber inhaltlich `%EStG%`-Treffer sind Zufallstreffer (z. B. ein Fahrtenbuch-Row-Versioning-ADR) — **kein** Einkommensteuerrecht |
| `Photovoltaik` | 0 | |
| `Einspeis` | 0 | |
| `Erneuerbare` / `EEG` | 1 | der GModG-Streichungsknoten (Wegfall der 65-%-EE-Pflicht) — Randtreffer, kein EEG-Stoff |

**Befund:** In allen vier Domänen existiert im brainlehr-Speicher heute
**Meta-Wissen über die eigenen Apps** (wie openlehr oder Pflege-Lotse gebaut
sind), aber **kein materielles Fachwissen** (was das Gesetz sagt, was der
Nutzer fragen würde). Das ist die Lücke, die dieser Plan für alle vier
Domänen gleich beschreibt.

---

## Domäne 1 · Mietrecht

### 1. Echte Fragen (Prüfkorpus)

1. „Darf mein Vermieter die Miete erhöhen, obwohl er nichts saniert hat?"
2. „Ich habe die Kündigung bekommen — wie viel Zeit habe ich wirklich?"
3. „Was darf von meiner Kaution einbehalten werden, wenn ich auszuziehe?"
4. „Muss ich Schönheitsreparaturen zahlen, obwohl im Vertrag nichts Genaues steht?"
5. „Der Vermieter will die Wohnung selbst nutzen — kann er mich einfach rauswerfen?"

### 2. Quellen

| Quelle | Bezugsweg | Lizenz |
|---|---|---|
| BGB §§ 535–580a (Mietrecht) | `gesetze-im-internet.de/bgb/` | Amtliches Werk, § 5 Abs. 1 UrhG — frei. **Bereits in PLAN_RECHTSDOMAENE Block 2 gelistet**, hier nur wiederholt, weil Mietrecht jetzt eigene Domäne ist. |
| Mietspiegel-Verordnung, Kappungsgrenzenverordnung BW | `landesrecht-bw.de` | Amtliches Werk — vermutlich frei, **ungeprüft** in dieser Sitzung. |
| Betriebskostenverordnung (BetrKV) | `gesetze-im-internet.de/betrkv/` | Amtliches Werk — frei. |
| Sekundärliteratur (Mieterverein-Ratgeber, Haufe/dejure-Kurztexte) | jeweilige Website | **Kostenpflichtig oder redaktionell geschützt** — Redaktionstext Dritter, nicht automatisch frei. Nur als Fundhinweis, nicht als Speicherinhalt — dieselbe Regel wie bei den WEG-Gerichtsstand-Zusammenfassungen in PLAN_RECHTSDOMAENE Block 1. |

### 3. Wie schnell veraltet es?

Das materielle Mietrecht selbst ändert sich **selten und angekündigt**
(Mietrechtsreformen sind seltene Bundesgesetzgebungsverfahren). Was
**regelmäßig und leise** wechselt, sind die **Zahlenwerte**, die an
Gerichtsbezirke und Kommunen hängen: Kappungsgrenze (ortsabhängig per
Verordnung, i. d. R. mehrjährig gültig, aber mit Enddatum), örtlicher
Mietspiegel (typischerweise alle zwei bis vier Jahre neu festgestellt) und
die ortsübliche Vergleichsmiete selbst. **Woran man einen abgelaufenen
Eintrag merkt:** nur, wenn der Knoten das Bezugsjahr des Mietspiegels bzw.
die Verordnungslaufzeit als eigenes Feld trägt — sonst **nicht**, ein
Paragraf ohne Datumsfeld sieht identisch aus, ob er zwei oder zehn Jahre alt
ist. Das ist dieselbe Geltungsachsen-Lücke wie in PLAN_RECHTSDOMAENE Block 3
(83 von 2178 Knoten mit `gilt_ab`), hier nur an einem anderen Zahlenwert
gezeigt.

### 4. Was darf nicht hinein

Kein individueller Mietvertrag, keine konkrete Adresse, kein konkreter
Streitfall eines Nutzers — nur der allgemeine Gesetzestext und die
orts**typ**-bezogene Verordnungslage (z. B. „Baden-Württemberg hat eine
Kappungsgrenzenverordnung", nicht „Herr X aus Auerbach zahlt Y Euro Miete").
Ein konkreter Mietstreit ist personenbezogene Falldokumentation und gehört,
wenn überhaupt, in einen individuellen Klientenspeicher, nicht in den
geteilten Bestand.

### 5. Verworfene Quelle

**Mietspiegel-Datenbanken einzelner Städte im Volltext (z. B. München,
Berlin) als Beispielbestand.** Verworfen als erster Schritt: Ein Mietspiegel
ist eine kommunale Verwaltungsvorschrift mit ausdrücklicher Ortsbindung und
eigenem Ablaufdatum — als „Beispielwert" eingelesen, suggeriert er
bundesweite Geltung, obwohl er das Gegenteil ist. Ohne den in Block 3 von
PLAN_RECHTSDOMAENE bereits verlangten Ortsfilter wäre das derselbe Fehler wie
das dort verworfene KlimaBonus/Karlsbad-Beispiel — nur in einer anderen
Domäne.

---

## Domäne 2 · Erneuerbare Energien

### Abgrenzung zu PLAN_RECHTSDOMAENE — zuerst, um nichts zu doppeln

`PLAN_RECHTSDOMAENE_2026-08-13.md` deckt bereits: GModG/GEG (Gebäudeenergie,
Nachrüstpflichten, Wärmepumpe), EEG als Quellenzeile in Block 2 (nur
Bezugsweg/Lizenz notiert, **nicht inhaltlich erschlossen**), und
Bund-/Land-/Kreis-/Gemeinde-Förderprogramme für energetische Sanierung
(BAFA, KfW, L-Bank). **Die Grenze:** PLAN_RECHTSDOMAENE behandelt Energie am
**Gebäude** (Sanierungspflicht, Heizungstausch, Förderantrag für ein
konkretes Objekt in Karlsbad). Diese Domäne behandelt Energie als
**Erzeugungs- und Vermarktungsrecht** — EEG-Einspeisevergütung,
Marktprämie, Eigenverbrauch, Anlagenregister — also die Fragen eines
Anlagenbetreibers, nicht die eines Sanierungspflichtigen. Beide Domänen
berühren dieselben Paragrafen (GModG referenziert EEG-Begriffe), aber aus
verschiedener Fragerichtung. Kein doppelter Import derselben Norm, nur zwei
verschiedene Frage-Perspektiven auf teils überlappenden Stoff.

### 1. Echte Fragen (Prüfkorpus)

1. „Ich will eine Solaranlage aufs Dach — was bekomme ich pro Kilowattstunde, die ich einspeise?"
2. „Muss ich meine Solaranlage irgendwo anmelden, bevor sie läuft?"
3. „Lohnt sich ein Batteriespeicher steuerlich und rechtlich, oder nur die Anlage allein?"
4. „Was ändert sich, wenn ich mehr Strom verbrauche, als ich einspeise?"
5. „Bekomme ich als Mieter eine Solaranlage auf dem Balkon genehmigt, oder braucht das den Vermieter?"

### 2. Quellen

| Quelle | Bezugsweg | Lizenz |
|---|---|---|
| EEG (Erneuerbare-Energien-Gesetz, aktuelle Fassung) | `gesetze-im-internet.de/eeg_2014/` | Amtliches Werk, § 5 Abs. 1 UrhG — frei. Bereits als Zeile in PLAN_RECHTSDOMAENE Block 2, **inhaltlich noch nicht erschlossen** — das holt dieser Plan nach. |
| Marktstammdatenregister-Verordnung (MaStRV) | `gesetze-im-internet.de/mastrv/` | Amtliches Werk — frei. |
| §§ 20a EnWG (Balkonkraftwerk-Vereinfachungen) | `gesetze-im-internet.de/enwg_2005/` | Amtliches Werk — frei. |
| Bundesnetzagentur-Merkblätter zu Einspeisevergütung/Marktprämie | `bundesnetzagentur.de` | Behörden-Redaktionstext — **ungeprüft**, ob amtliches Werk nach § 5 UrhG oder geschützter Redaktionstext; im Zweifel wie bei BAFA/KfW in PLAN_RECHTSDOMAENE als „ungeprüft" behandeln. |
| Fachartikel/Ratgeber zu Balkonkraftwerken (Verbraucherzentrale) | jeweilige Website | Redaktionstext der Verbraucherzentrale — urheberrechtlich geschützt, nur als Fundhinweis. |

### 3. Wie schnell veraltet es?

**Am schnellsten in der ganzen Vier-Domänen-Liste.** Die
EEG-Einspeisevergütungssätze sinken nach gesetzlich festgelegtem
„atmenden Deckel" **monatlich** (Degression), zusätzlich ändert der
Gesetzgeber die Fördersystematik selbst in unregelmäßigen Novellen (zuletzt
u. a. Wegfall der Pflicht zur Volleinspeise-Meldung, Vereinfachungen für
Balkonkraftwerke). **Woran man es merkt:** nur, wenn ein Vergütungssatz-Knoten
das Inbetriebnahmedatum trägt, für das er gilt — die Vergütungshöhe ist in
Deutschland an den Zeitpunkt der Anlageninbetriebnahme gekoppelt (20 Jahre
fester Satz ab Inbetriebnahme), nicht an das Antragsdatum. Ein Knoten ohne
dieses Feld beantwortet „was bekomme ich" **falsch für jede Anlage, die
nicht exakt heute in Betrieb geht** — und das merkt niemand, weil die Zahl
plausibel aussieht.

### 4. Was darf nicht hinein

Keine anlagenspezifische Wirtschaftlichkeitsberechnung eines konkreten
Nutzers (Dachfläche, Ausrichtung, Verbrauchsprofil) — das ist eine
individuelle Berechnung, kein allgemeines Regelwissen. Nur die Rechtslage
und die Berechnungsformel gehören in den geteilten Speicher, nicht das
Ergebnis für eine bestimmte Adresse.

### 5. Verworfene Quelle

**Herstellerangaben und Produktvergleichsportale zu PV-Modulen/Wechselrichtern
(z. B. „welches Modul ist am effizientesten").** Verworfen: Das ist
Produktwissen, kein Rechtswissen, ändert sich mit jeder Modellgeneration
schneller als jede Geltungsachse es sinnvoll nachführen könnte, und gehört
— wenn überhaupt — in einen separaten Produktkatalog, nicht in einen
Rechts-/Förderspeicher.

---

## Domäne 3 · Steuerrecht

### Was im Verbund schon vorhanden ist — zuerst geprüft, nicht vermutet

**openlehr ist die Steuer-App des Verbunds**, unter
`/Volumes/daten/Begod2026/openlehr` (nur gelesen). Gefunden:

- `archive/tax_laws/` enthält Metadaten und **Kurzauszüge** (nicht
  Volltext) zu EStG, UStG, AO — je Datei **631 Byte, eine Zeile**
  (`estg.txt`, `ustg.txt`, `ao.txt`, gemessen mit `wc -l`). Der
  `source_snapshots_seed.json` zeigt den Inhalt: eine
  Inhaltsübersicht mit Beispiel-Paragrafen (§ 1, § 32a, § 35a EStG
  u. a.), **kein** durchsuchbarer Gesetzestext. Das ist ein Seed/Platzhalter,
  kein fertiger Bestand — anders als die 13 fertigen buckeberg-Dateien im
  WEG-Fall.
- `steuer/` (Datenbank-Init, Schema, `research_plan.json` — **leer, `{}`**)
  und `daemon/steuer/homeoffice_pauschale.py` mit zugehörigen Tests: das ist
  **Anwendungslogik** (Berechnung der Homeoffice-Pauschale, ELSTER-Übertragung
  Anlage S, Belegverwaltung, ASN-Nummerierung) — funktionierender Code, der
  Steuerrecht **anwendet**, aber kein durchsuchbares Regelwissen-Bestand, den
  brainlehr übernehmen könnte.
- Der brainlehr-Bestand selbst (siehe Ist-Stand-Tabelle oben) trägt zu
  „Steuer" ausschließlich Architekturwissen über openlehr selbst (RAG/LoRA,
  Frontend-ADRs) plus einen Papernetz-Fund „Steuerrecht für Fotografen"
  (Freiberufler-Abgrenzung, Umsatzsteuersatz auf Bildrechte) — ein sehr
  schmaler Einzelfall, kein systematisches Regelwissen.

**Befund, parallel zum WEG-Fall, aber mit anderem Ergebnis:** Anders als bei
WEG-Recht (13 fertige Dateien lagen bereit) liegt bei Steuerrecht **kein**
fertiger Textbestand vor, sondern nur ein Metadaten-Seed und
Anwendungscode. Ein Übertrag „wie bei WEG" ist hier **nicht** möglich — der
Stoff selbst muss noch geholt werden, nicht nur überführt.

### 1. Echte Fragen (Prüfkorpus)

1. „Ich arbeite von zuhause — was kann ich dafür überhaupt absetzen?"
2. „Muss ich als Kleinunternehmer Umsatzsteuer ausweisen?"
3. „Ich habe eine Steuererklärung zu spät abgegeben — was passiert jetzt?"
4. „Welche Belege muss ich wie lange aufheben?"
5. „Was ändert sich an meinem Steuersatz, wenn ich nebenberuflich selbstständig bin?"

### 2. Quellen

| Quelle | Bezugsweg | Lizenz |
|---|---|---|
| EStG (Einkommensteuergesetz) | `gesetze-im-internet.de/estg/` | Amtliches Werk — frei. Bereits als Metadaten-Verweis in openlehr vorhanden, **Volltext fehlt dort wie hier**. |
| UStG (Umsatzsteuergesetz) | `gesetze-im-internet.de/ustg_1980/` | Amtliches Werk — frei. |
| AO (Abgabenordnung) | `gesetze-im-internet.de/ao_1977/` | Amtliches Werk — frei. |
| Jährliche Pauschalen/Freibeträge (Homeoffice-Pauschale, Sparer-Pauschbetrag, Kilometerpauschale, Grundfreibetrag) | BMF-Schreiben, `bundesfinanzministerium.de` | BMF-Schreiben sind Verwaltungsanweisungen — Einordnung als amtliches Werk **ungeprüft** in dieser Sitzung; der reine Zahlenwert (z. B. „1.230 Euro Werbungskosten-Pauschbetrag") ist als Fakt ohnehin nicht schutzfähig, der Erläuterungstext des BMF schon. |
| ELSTER-Anleitungen (bereits als `elster_anleitung_euer_2024.html` in openlehr archiviert) | `elster.de` | Redaktionstext der Finanzverwaltung — **ungeprüft**, ob amtliches Werk. |
| Sekundärliteratur (Steuerberater-Blogs, Haufe-Kurztexte) | jeweilige Website | Kostenpflichtig/redaktionell geschützt — nur als Fundhinweis. |

### 3. Wie schnell veraltet es?

**Die tragende Frage dieser Domäne, und sie ist hier am schärfsten.** Das
Gesetz selbst (EStG-Grundstruktur) ändert sich selten. Die **Zahlenwerte**
darin — Grundfreibetrag, Sparer-Pauschbetrag, Homeoffice-Pauschale,
Kilometerpauschale, Sozialversicherungs-Beitragssätze — ändern sich **jährlich
zum 1. Januar**, meist durch ein Jahressteuergesetz oder eine BMF-Bekanntgabe,
und zwar **still**: Es gibt keine Streichliste wie beim GModG, die auffällt,
sondern nur eine neue Zahl an derselben Stelle. **Woran man einen
abgelaufenen Eintrag merkt:** nur, wenn der Knoten das **Veranlagungsjahr**
als Pflichtfeld trägt (nicht das Einlesedatum) — sonst gar nicht, ein
Pauschalwert ohne Jahresangabe sieht in jedem Jahr identisch plausibel aus.
Das ist der schärfste Einzelfall der in PLAN_RECHTSDOMAENE Block 3
beschriebenen Förderprogramm-Problematik, nur mit jährlichem statt
mehrjährigem Zyklus.

### 4. Was darf nicht hinein

Keine individuelle Steuererklärung, kein konkreter Beleg, keine konkrete
Steuernummer oder Steuer-ID eines Nutzers — Steuerdaten sind so
personenbezogen wie Gesundheitsdaten, auch wenn sie nicht unter Art. 9
DSGVO fallen. Nur die allgemeine Rechtslage und die (datierten) Pauschalwerte
gehören in den geteilten Speicher.

### 5. Verworfene Quelle

**openlehr `steuer.db` / `db/steuer.db*` als Bestandsquelle.** Verworfen:
Das sind Anwendungsdatenbanken mit potenziell echten oder Test-Buchungsdaten
einzelner Nutzer (Belege, Rechnungen, Kontakte laut Testdateinamen
`test_contact_management.py`, `test_belege_asn.py`) — personenbezogene
Nutzdaten einer fremden App, kein allgemeines Regelwissen. Ein Übertrag
verletzte dieselbe Trennung, die bei der Pflegelotsen-Domäne unten für
Gesundheitsdaten verlangt wird, nur bei Finanzdaten statt Gesundheitsdaten.

---

## Domäne 4 · Pflegelotsen-Domäne

### Existenz geprüft, nicht vermutet

Die App existiert im Verbund: `/Volumes/daten/Begod2026/pflegelotse`
(nur gelesen), Flutter-App, 514 Commits, 14 ADR-Dateien. Feature-Verzeichnis
`apps/pflegelotse/lib/features/nba_rechner/domain/cross_references.dart`
(NBA = Neues Begutachtungsassessment, die Grundlage der
Pflegegrad-Einstufung nach SGB XI). Domänenwissen liegt heute:

- **Im Code**, nicht als durchsuchbarer Wissensbestand: `cross_references.dart`
  verknüpft NBA-Kriterien miteinander (laut ADR-019 „NBA-Kriterien verweisen
  aufeinander … nur Domain-Code, kein globales Schema").
- **In ADRs**, als Architektur- und Scope-Entscheidungen, nicht als
  Fachwissen selbst: ADR-018 (Medikamenten-Scope-Grenze, s. u.), ADR-019
  (Kreuzreferenz-System, referenziert „SGB-§§" und „BRi" — die
  Begutachtungs-Richtlinien — als Knotentypen, aber ohne deren Inhalt).
- **Im brainlehr-Bestand bereits vorhanden**: 18 „Pflege"-Treffer, aber
  ausnahmslos ADR-**Zusammenfassungen zur App-Architektur** (Drift/SQLite,
  Study-Mode, Farbkonzept), **kein** einziger SGB-XI-Inhalt.

**Befund:** Es gibt eine reife App mit eigener Scope-Disziplin, aber ihr
fachliches Regelwissen (was ist ein Pflegegrad, wie läuft eine
NBA-Begutachtung ab) ist im Code verankert, nicht im geteilten
Wissensspeicher — dieselbe Lücke wie bei den anderen drei Domänen, nur mit
einer zusätzlichen Schärfe: **hier ist die Grenze zwischen Regelwissen und
Gesundheitsdaten bereits einmal formal gezogen worden**, in ADR-018.

### ADR-018 als Präzedenzfall für „was darf hinein"

ADR-018 (Status: Akzeptiert, Konsil-Ergebnis, 7 Experten einstimmig) zieht
für die Medikamentenfunktion genau die Linie, die dieser Plan für den ganzen
Wissensspeicher braucht: Die App speichert **nur Dokumentation**
(„Was hat der Arzt verschrieben?"), nie eine **Bewertung** („Soll der Patient
das nehmen, wann, wie viel?") — Letzteres würde die App zum
zulassungspflichtigen Medizinprodukt nach MDR machen. Medikamentendaten
bleiben **lokal auf dem Gerät**, kein Server, kein Cloud-Sync — Berufung auf
die Haushaltsausnahme Art. 2 Abs. 2c DSGVO.

**Für den geteilten brainlehr-Speicher folgt daraus dieselbe Trennung, nur
eine Ebene höher:**

| Gehört in den geteilten Speicher | Gehört NICHT hinein |
|---|---|
| Der Text des SGB XI (Pflegebedürftigkeitsbegriff, §§ 14/15) | Der Pflegegrad einer bestimmten Person |
| Der allgemeine Ablauf einer NBA-Begutachtung (sechs Module, Punktesystem) | Das Begutachtungsergebnis eines bestimmten Falls |
| Die Struktur der Begutachtungs-Richtlinien (BRi) als Regelwerk | Eine konkrete Diagnose, ein konkretes Medikament, eine konkrete Betreuungssituation |
| Die ADR-Entscheidung selbst als Architekturwissen (bereits vorhanden) | Freitext-Notizen aus einem echten Pflegetagebuch |

Pflegegrade, Diagnosen und Betreuungssituationen sind **Gesundheitsdaten
nach Art. 9 DSGVO** — sie benötigen eine der engen Ausnahmen des Art. 9
Abs. 2, die ein geteilter, mehrbenutzerfähiger Wissensspeicher nicht ohne
Weiteres erfüllt (die App selbst löst das durch lokale Speicherung ohne
Server — genau der Weg, der einem geteilten Speicher nicht offensteht).

### 1. Echte Fragen (Prüfkorpus)

1. „Wie läuft eine Begutachtung zur Feststellung des Pflegegrads eigentlich ab?"
2. „Was ist der Unterschied zwischen Pflegegrad 2 und Pflegegrad 3, ganz allgemein?"
3. „Auf welche Leistungen habe ich grundsätzlich Anspruch, wenn ein Pflegegrad festgestellt wurde?"
4. „Wie lange dauert es normalerweise, bis ein Widerspruch gegen einen Bescheid entschieden ist?"
5. „Was wird bei der Begutachtung überhaupt bewertet — nur Körperliches, oder auch geistige Fähigkeiten?"

Alle fünf sind bewusst **allgemein** formuliert (kein „meine Mutter hat…"),
weil das der Prüfstein für die Trennung aus ADR-018 ist: Eine Frage, die nur
mit einer konkreten Person beantwortbar wäre, gehört nicht in diesen
Prüfkorpus.

### 2. Quellen

| Quelle | Bezugsweg | Lizenz |
|---|---|---|
| SGB XI (Elftes Buch Sozialgesetzbuch, Soziale Pflegeversicherung) | `gesetze-im-internet.de/sgb_11/` | Amtliches Werk, § 5 Abs. 1 UrhG — frei. |
| Begutachtungs-Richtlinien (BRi) des GKV-Spitzenverbands | `gkv-spitzenverband.de` | **Ungeprüft** in dieser Sitzung — der GKV-Spitzenverband ist eine Körperschaft öffentlichen Rechts, die BRi ist eine untergesetzliche Richtlinie mit Normcharakter; ob sie unter § 5 UrhG fällt oder als Verbandsredaktionstext geschützt ist, wurde nicht nachgesehen. |
| Pflegelotse-eigene ADRs (ADR-018, ADR-019) | bereits im brainlehr-Bestand als Architekturwissen | Eigenes Werk des Verbunds — unproblematisch, aber Architekturwissen, kein SGB-XI-Fachinhalt. |
| Sekundärliteratur (Pflegekassen-Ratgeber, Verbraucherzentrale, Sozialverbände VdK/SoVD) | jeweilige Website | Redaktionstext der jeweiligen Organisation — geschützt, nur als Fundhinweis. |

### 3. Wie schnell veraltet es?

Der Pflegebedürftigkeitsbegriff selbst (SGB XI §§ 14/15, seit der Reform
2017) ist seit Jahren stabil. Was sich **regelmäßig** ändert, sind die
**Leistungsbeträge** (Pflegegeld, Pflegesachleistung je Pflegegrad) — diese
werden per Gesetz meist zum 1. Januar angepasst, ähnlich wie die
Steuerpauschalen, aber nicht zwingend jährlich (die letzte große Anpassung
lag mehrere Jahre zurück, die nächste ist politisch angekündigt, nicht
automatisch). **Woran man es merkt:** nur, wenn ein Leistungsbetrags-Knoten
das Datum der zugrunde liegenden Gesetzesfassung trägt — sonst nicht, exakt
dieselbe stille Alterung wie bei Steuerpauschalen und
EEG-Vergütungssätzen. Die **Begutachtungs-Richtlinien** selbst werden vom
GKV-Spitzenverband in unregelmäßigen Abständen überarbeitet, ohne festen
Zyklus — ein BRi-Knoten braucht darum eine Versionsangabe der Richtlinie
selbst, nicht nur ein Einlesedatum.

### 4. Was darf nicht hinein

Siehe Tabelle oben (ADR-018-Trennung). Zusätzlich, spezifisch für diesen
Speicher: **kein** Transfer aus einer laufenden oder abgeschlossenen
Pflegelotse-Installation, auch nicht anonymisiert versuchsweise — die App
selbst hält Gesundheitsdaten bewusst lokal und ohne Server (ADR-012,
ADR-018), und ein nachträglicher Export in einen geteilten Speicher würde
genau die Schutzentscheidung unterlaufen, die die App-Architektur trifft.
Nur der **Gesetzes- und Regeltext** (SGB XI, BRi-Struktur) und das bereits
vorhandene **Architekturwissen** (ADRs) sind zulässig.

### 5. Verworfene Quelle

**Pflegelotse-eigene Testdaten/Fixtures (`integration_test/`,
Screenshot-Tests) als Beispielbestand.** Verworfen: Auch wenn es sich um
synthetische Testpersonen handelt, simulieren diese Fixtures typischerweise
konkrete Pflegegrad- und Diagnose-Situationen zu Testzwecken — die Form
selbst (ein NBA-Modul-Ergebnis für eine „Person") ist strukturell identisch
mit einer echten Gesundheitsdatenerhebung. Ein Import würde die
Regelwissen/Fall-Trennung aus ADR-018 im Speicher selbst wieder aufweichen,
selbst wenn die konkreten Werte erfunden sind — nicht nachvollziehbar
prüfbar, ob eine Fixture je zufällig reale Werte trifft oder als Vorlage
missverstanden wird.

---

## Was bewusst nicht getan wird, samt Preis

- **Kein Netzabruf, kein Volltextimport in diesem Plan.** Preis: Alle vier
  Domänen bleiben vorerst auf das beschränkt, was im Verbund bereits liegt
  (bei Steuerrecht: fast nichts; bei Pflegelotsen: nur Architekturwissen).
  Grund: reine Recherche, kein Bauauftrag laut Auftrag.
- **Keine Prüfung der BRi- und BMF-Lizenzfrage in dieser Sitzung.** Preis:
  zwei „ungeprüft"-Vermerke bleiben offen (Domäne 3 und 4), bis jemand die
  Primärquelle liest. Grund: Netzabruf über die reine Fundstellenprüfung
  hinaus ist kein Recherche-, sondern ein Prüfauftrag.
- **Keine Geltungsachsen-Implementierung.** Preis: Die vier
  „woran merkt man Ablauf"-Antworten bleiben Diagnosen, keine Mechanismen.
  Grund: Das ist bereits Gegenstand von Aufgabe 88 / PLAN_RECHTSDOMAENE
  Schritt A und wird dort gelöst, nicht hier verdoppelt.

## Woran sich Erfolg misst

Vier Prüfkorpora mit je fünf natürlichen Fragen liegen vor (20 insgesamt) —
das ist der Maßstab, an dem sich ein künftiger Import später **rot vor
grün** messen lässt: Vor dem Import liefert der Speicher auf diese Fragen
nichts oder nur Architektur-Rauschen (siehe Ist-Stand-Tabelle), nach einem
künftigen, gesondert freizugebenden Import müsste er den einschlägigen
Gesetzestext oder Regelinhalt liefern.

---

## Aufträge, fertig zum Übergeben

**Tabu für alle Schritte:** `/Volumes/daten/Begod2026/openlehr/`,
`/Volumes/daten/Begod2026/pflegelotse/`, `/Volumes/daten/Begod2026/buckeberg/`
werden nur **gelesen** — fremde Repos. Kein Netzabruf über das reine Lesen
öffentlicher Normtexte hinaus. Dieser Plan selbst wird nicht durch einen
Agenten umgesetzt, sondern liegt zur Freigabe vor — die folgenden Schritte
sind vorbereitete, aber noch nicht beauftragte Anschlussarbeiten.

### Schritt A · Geltungsfeld je Domäne ergänzen, sobald Schritt A aus PLAN_RECHTSDOMAENE steht

| | |
|---|---|
| **Darf ändern** | `kern/` (Erweiterung des in PLAN_RECHTSDOMAENE Schritt A gebauten Übernahmeschritts), `tests/` (neue Datei) |
| **Tabu zusätzlich** | Kein Volltextimport von BRi oder BMF-Schreiben, solange deren Lizenzstatus „ungeprüft" ist (Domäne 3 und 4, Abschnitt Quellen). |
| **Fakten** | Vier Domänen brauchen je einen eigenen Ablauf-Indikator: Mietspiegel-Bezugsjahr, EEG-Inbetriebnahmedatum, Steuer-Veranlagungsjahr, SGB-XI-Leistungsbetrags-Gesetzesfassung — vier verschiedene Felder, keins davon ist mit den bereits für WEG/GModG vorgesehenen Feldern identisch genug, um sie ungeprüft wiederzuverwenden. |
| **Abnahme** | Für jede der vier Domänen liefert eine Abfrage mit Stichtag nur, was zu diesem Stichtag galt. Rot-Probe: ein EEG-Vergütungssatz-Knoten ohne Inbetriebnahmedatum wird als „Geltung unbekannt" markiert, nicht als geltend ausgeliefert. Negativfall: ein SGB-XI-Paragraf ohne Zahlenwert (z. B. § 14 Pflegebedürftigkeitsbegriff) braucht kein Ablauffeld und wird nicht fälschlich als unvollständig gemeldet. Grenzwert: ein Leistungsbetrag, dessen Gesetzesfassung exakt am Stichtag in Kraft trat. |
| **Einsatz** | Ohne dieses Feld wiederholt sich in vier neuen Domänen derselbe stille Alterungsfehler, der in PLAN_RECHTSDOMAENE bereits einmal real war (`L-2fa1e2`). |

### Schritt B · Lizenzstatus BRi und BMF-Schreiben klären

| | |
|---|---|
| **Darf ändern** | `pflege/` (neue Rechercheergebnis-Datei), `tests/` (keine) |
| **Fakten** | Zwei offene „ungeprüft"-Vermerke aus diesem Plan: BRi des GKV-Spitzenverbands (Domäne 4), BMF-Schreiben zu Jahrespauschalen (Domäne 3). Beide sind untergesetzliche Verwaltungsvorschriften, keine Parlamentsgesetze — die Einordnung nach § 5 UrhG ist bei diesem Typ nicht automatisch wie bei einem Bundesgesetz. |
| **Abnahme** | Für beide Quellen liegt entweder eine Fundstelle vor, die die Lizenz belegt, oder der Vermerk „ungeprüft" bleibt ausdrücklich stehen — keine dritte Möglichkeit („vermutlich frei" ohne Beleg zählt als ungeprüft, nicht als geklärt). |
| **Einsatz** | Ein Volltextimport ohne diese Klärung wäre derselbe Fehler wie ein VDE-Normtext im freien Speicher (PLAN_RECHTSDOMAENE Block 2) — nur unbemerkt, weil BRi und BMF-Schreiben staatsnäher wirken als ein Verbandsstandard, ohne es zu sein.

### Schritt C · EStG/UStG/AO-Volltext holen, wo openlehr nur einen Seed hat

| | |
|---|---|
| **Darf ändern** | `pflege/` (neue Datei), `tests/` (neue Datei) |
| **Tabu zusätzlich** | `openlehr/archive/tax_laws/` nicht überschreiben oder ergänzen — fremdes Repo, nur lesen. Kein Import von `openlehr/steuer.db` oder `openlehr/db/steuer.db*` (verworfene Quelle, personenbezogene Anwendungsdaten). |
| **Fakten** | `openlehr/archive/tax_laws/estg.txt`, `ustg.txt`, `ao.txt` sind je eine Zeile / 631 Byte — Metadaten-Seed, kein Volltext (gemessen mit `wc -l`). Anders als bei WEG-Recht liegt hier kein fertiger Bestand zur Überführung bereit. |
| **Abnahme** | Der Prüfkorpus aus Domäne 3 (fünf Fragen) wird gegen den geholten Bestand gefahren, rot vorher (heute: 0 einschlägige Treffer laut Ist-Stand-Tabelle), grün danach für mindestens die Paragrafen, die die fünf Fragen unmittelbar berühren (§ 4 Nr. 5b EStG bzw. Nachfolgeregelung Homeoffice, § 19 UStG Kleinunternehmer, § 149 AO Fristen). |
| **Einsatz** | Steuerrecht ist die einzige der vier Domänen, in der noch nicht einmal ein fertiger Fremdbestand irgendwo im Verbund liegt — ohne diesen Schritt bleibt sie die schwächste der vier. |

**Reihenfolge, bindend:** Schritt A setzt voraus, dass die Geltungsachse aus
`PLAN_RECHTSDOMAENE_2026-08-13.md` Schritt A bereits trägt — sonst entwertet
sich die Arbeit, wie dort bereits begründet. Schritt B ist von A und C
unabhängig und darf jederzeit parallel laufen. Schritt C setzt weder A noch
B voraus (der Volltextimport selbst ist unabhängig von der Geltungsachse
möglich, sollte aber vor einem produktiven Einsatz auf A warten, damit er
nicht ungeltungsmarkiert einläuft).

**Sieht der Code oder der Bestand anders aus als hier beschrieben, halte
dich an das Vorgefundene und melde die Abweichung.**
