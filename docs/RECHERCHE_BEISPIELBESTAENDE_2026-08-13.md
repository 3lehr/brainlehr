# Recherche: Beispielbestände für neue brainlehr-Nutzer

Stand: 2026-08-13T18:13:07+0200. Reine Recherche, kein Bauauftrag — nichts
importiert, nichts heruntergeladen, keine andere Datei angefasst.

Betreiberfrage, wörtlich: „welche datensätze gibt es noch welche wir als
beispiel wissen mitgeben können? welche datensätze wären allgemeinverständlich
damit jeder neue brainlehr user testen kann? welches wissen könnten wir selbst
extrahieren?"

## Gemessener Ist-Stand (vor der Recherche geprüft, nicht aus Erinnerung)

- `quellen/fremdquellen.json`: 11 Quellen erfasst, davon **grün** nur
  `nasa-llis` (1637 Einträge, importiert) und `bsi-grundschutz` (Profil
  liegt bei, Weitergabe aber gelb wegen Share-Alike).
- `auszug-offen/bestand.jsonl`: 1746 Zeilen `knowledge_nodes`, davon
  **1639 mit „nasa" im Datensatz** — der offene Auszug besteht damit fast
  vollständig aus dem NASA-LLIS-Import. Eigene brainlehr-Knoten sind darin
  eine kleine Minderheit.
- `docs/LIZENZPRUEFUNG_FREMDBESTAENDE_2026-08-11.md` (Opus, 37
  Werkzeugaufrufe, 2026-08-11) hat acht der elf Kandidaten bereits gegen
  Primärquellen geprüft. Diese Recherche wiederholt das nicht, sondern baut
  darauf auf und ergänzt, was dort fehlt: die Allgemeinverständlichkeits- und
  Sprachfrage, und neue Kandidaten.
- `kern/fremdimport.py` erzwingt Projektion + Gegenprobe + Gattung
  `nachschlagewerk` für jeden Fremdimport — das ist die Bauform, in die ein
  neuer Kandidat müsste, kein neues Werkzeug nötig.

---

## Teil 1 — Fremdbestände als Beispielwissen

Maßstab: (a) allgemeinverständlich beurteilbar, (b) deutsch oder
zweisprachig, (c) Lizenz mit Fundstelle, (d) natürliche Frage-Seite. Fehlt
eine Fundstelle, steht ausdrücklich **„Lizenz ungeprüft"**.

### 1.1 Bereits geprüfte Kandidaten — neu bewertet nach (a)/(b)

| Bestand | Umfang | Sprache | Lizenz (Fundstelle) | Bezugsweg | Testfrage eines Neulings |
|---|---|---|---|---|---|
| **NASA LLIS** | 1637 Einträge (gemessen, `auszug-offen/bestand.jsonl`) | Englisch, einzeilig, Fachjargon Raumfahrt-Projektmanagement | „US-Bundeswerk, gemeinfrei (17 U.S.C. §105)" laut Import-Skript-Kommentar — **ungeprüft**, Primärquelle war laut Skriptkopf `NASADatanauts/llis_topicModel` (MIT) | bereits importiert, `pflege/nasa_llis_import.py` | „Was sagt die NASA zu Kommunikationsproblemen in Projekten?" — beantwortbar, aber ein deutschsprachiger Neuling muss zuerst über die Sprachbarriere und den Aerospace-Jargon hinweg, bevor er die Antwort selbst beurteilen kann. **Verfehlt (a) und (b) trotz grüner Lizenz.** |
| **ASRS** (Aviation Safety Reporting System) | „bis 10.000 Datensätze" laut Exportgrenze (Quelle: `LIZENZPRUEFUNG…md`) — Umfang nicht selbst nachgezählt, daher Schätzung aus Fremdbeleg | Englisch, Fließtext-Meldungen von Piloten | Auswertung/Weitergabe 🟢 laut `LIZENZPRUEFUNG_FREMDBESTAENDE_2026-08-11.md`, Personenbezug 🟢 (de-identifiziert lt. Betreiberaussage der Quelle) | asrs.arc.nasa.gov, Exportfunktion | „Was ist bei einem Beinahe-Zusammenstoß am Boden schiefgelaufen?" — inhaltlich zugänglich, aber wieder Englisch und Luftfahrt-Fachbegriffe (Callsign, Taxiway, ATC). **Verfehlt (b), (a) nur mit Vorwissen.** |
| **NIST** | Teilbestand laut Register „weiterhin unbenannt" — kein Umfang feststellbar ohne diesen Schritt zuerst zu tun | Englisch, technisch | Weitergabe 🟢 mit Auflage (Byline, Änderungshinweis) laut o.g. Prüfung | nist.gov, Teilbestand offen | Ohne benannten Teilbestand keine seriöse Testfrage formulierbar. **Nicht einsatzbereit, unabhängig von (a)/(b).** |
| **BSI Stand-der-Technik-Bibliothek** | 947 Controls (`bsi-dev-profile.json`, laut `docs/FREMDBESTAENDE.md`) | Deutsch | CC BY-SA 4.0, Fundstelle github.com/BSI-Bund/Stand-der-Technik-Bibliothek, geprüft 2026-08-10 laut Register | github, bereits im Profil abgelegt | „Was verlangt der Stand der Technik zu Passwort-Hashing?" — Sprache passt, aber ein Neuling ohne IT-Security-Hintergrund kann eine Control-Antwort **nicht selbst beurteilen** (verfehlt a trotz b und c). Für ein Fachpublikum wäre es geeignet, nicht für „jeder neue Nutzer". |

### 1.2 Neue Kandidaten, hier erstmals geprüft (Modellwissen, ausdrücklich als
solches gekennzeichnet — keine Primärquelle in dieser Sitzung abgerufen,
da ein Netzabruf laut Auftrag nicht Teil dieser Recherche ist)

| Bestand | Umfang (Schätzung) | Sprache | Lizenz | Bezugsweg | Testfrage |
|---|---|---|---|---|---|
| **GermanQuAD / mteb/germanquad-retrieval** | ~13.722 QA-Paare im Originaldatensatz (deepset); die im Repo bereits genutzte Retrieval-Variante hat laut `pruefstand/germanquad.py` **2204 Query-Dokument-Zuordnungen (qrels), gemessen und im Code belegt** | **Deutsch**, auf deutscher Wikipedia aufgebaut | CC BY-SA 4.0 — **Lizenz ungeprüft in dieser Sitzung**, deepset nennt diese Lizenz auf der Modellkarte laut Modellwissen, nicht selbst nachgesehen | huggingface.co, bereits ein Bezugsweg im Repo dokumentiert (`pruefstand/germanquad.py`, mit bekannten Einschränkungen des HF-Endpunkts) | „Wann wurde X gegründet?" / „Was passierte im Jahr Y bei Z?" — klassische Wikipedia-Faktenfragen, von jedem deutschsprachigen Leser ohne Vorwissen beurteilbar. **Erfüllt (a), (b), (d); (c) fehlt noch die eigene Prüfung.** Bereits als Prüfstand-Vergleichsmaterial genutzt, aber **nicht** als Beispielbestand im offenen Auszug — das ist ein Unterschied im Zweck, siehe Teil 3. |
| **Gesetze im Internet (BMJ)**, z. B. SGB XI (Pflegeversicherung), BGB-Auszüge | einzelne Paragraphen, Umfang je nach Auswahl (BGB allein > 2000 §§) | Deutsch, Amtssprache — kein Fachjargon im Sinne einer Community, sondern Gesetzeswortlaut | Amtliche Werke sind nach **§ 5 Abs. 1 UrhG gemeinfrei** — **Lizenz ungeprüft in dieser Sitzung**, die Norm selbst ist bekanntes, unstrittiges deutsches Recht, aber die genaue Reichweite (gilt sie auch für die Aufbereitung/Gliederung auf gesetze-im-internet.de?) wurde nicht nachgesehen | www.gesetze-im-internet.de, XML/HTML pro Gesetz | „Was regelt § 14 SGB XI?" — für jeden Deutschsprachigen sofort selbst nachschlagbar und damit selbst überprüfbar. **Erfüllt (a) und (b) besonders gut**, weil die Antwort auch ohne brainlehr an einer bekannten Stelle nachprüfbar ist — das ist der eigentliche Witz eines Schaufensterbestands. Passt inhaltlich zur bereits genannten Pflegelotsen-Domäne (NBA-Kriterien, SGB-§§ laut `ADR-019-universum-kreuzreferenz-system.md`). |
| **OpenThesaurus** (deutsches Synonymwörterbuch) | laut Modellwissen mehrere hunderttausend Wortbeziehungen — **Umfang ungeprüft** | Deutsch | GPL/LGPL-artig, Projekt nennt eigene Lizenzbedingungen für Datenexport — **Lizenz ungeprüft in dieser Sitzung** | openthesaurus.de, Downloadbereich | „Was ist ein Synonym für ‚schnell'?" — trivial für jeden deutschsprachigen Nutzer selbst zu beurteilen, denkbar niedrige Eintrittshürde. **Erfüllt (a), (b), (d) gut**, aber die Fragen sind fachlich zu flach für einen Retrieval-Test (Einwort-Lookup, kein Kontext) — siehe Verwerfung als Prüfkorpus in Teil 3. |

### 1.3 Ausdrücklich verworfene Kandidaten

| Bestand | Grund der Verwerfung | Beleg |
|---|---|---|
| **CROSS** (Confidential Reporting on Structural Safety) | `robots.txt` sperrt `CCBot`, `GPTBot`, `ChatGPT-User`, `Google-Extended` per `Disallow: /` — ein maschinenlesbarer TDM-Opt-out nach Art. 4 Abs. 3 DSM-RL. Ein Zitatrecht ändert daran nichts. | `docs/LIZENZPRUEFUNG_FREMDBESTAENDE_2026-08-11.md`, selbst per curl gegen cross-safety.org/robots.txt geprüft (HTTP 200, dort dokumentiert) |
| **ESA Lessons Learned** | Kein öffentlich abrufbarer Bestand unter esa.int feststellbar — die Registerzeile zeigt auf nichts Abrufbares. | dieselbe Quelle |
| **NRC Licensee Event Reports** | Jeder Zugriff wird am Akamai-Rand mit HTTP 403 abgewiesen, auch `robots.txt` selbst — weder Erlaubnis noch Vorbehalt feststellbar, ein Massenabruf wäre Umgehung einer aktiven Sperre. | dieselbe Quelle |
| **IAEA IRS** | Zugang auf Mitgliedstaaten/berechtigte Stellen beschränkt, voraussichtlich rot. | `quellen/fremdquellen.json`, Feld `pruefauftrag` |
| **Ganze Wikipedia/Wiktionary-Dumps** (erwogen, nicht in obiger Tabelle) | Verworfen als **erster** Kandidat, nicht grundsätzlich: Umfang macht Auswahl und Aufbereitung selbst zu einem Projekt (welche Artikel, welche Tiefe), und CC BY-SA bringt Share-Alike-Pflicht für den abgeleiteten Bestand — dieselbe Auflage, die beim BSI-Profil schon zur Gelb-Ampel geführt hat. GermanQuAD deckt den Wikipedia-Fall bereits kuratiert und mit fertigen Frage-Antwort-Paaren ab, ohne die Auswahlarbeit neu zu leisten. | eigener Schluss aus dem BSI-Präzedenzfall (`docs/FREMDBESTAENDE.md`, Zeile zu Share-Alike) |

---

## Teil 2 — Was der Verbund selbst extrahieren könnte

Repos geprüft (nur gelesen): brainlehr, buckeberg, openlehr, fahrtenbuch,
hub, wohlair, pflegelotse, openhood, begem, begem2026.

**KORREKTUR vom Orchestrator, 2026-08-13T19:10, selbst nachgeprüft.** Der
Bericht schrieb ursprünglich, alle bis auf begem/begem2026 seien Worktrees
desselben Monorepos. Das stimmt nur zur Hälfte. Geprüft wurde, ob `.git` eine
Datei (Worktree) oder ein Ordner (eigenes Repo) ist:

| | |
|---|---|
| Worktree desselben Repos | `buckeberg`, `fahrtenbuch` |
| **eigenes Repo mit eigener Historie** | `openlehr`, `wohlair`, `hub` |

Das ändert Teil 2 an der entscheidenden Stelle: Nur bei `buckeberg` und
`fahrtenbuch` überlappen ADRs und Commit-Historie. `openlehr`, `wohlair` und
`hub` tragen **unabhängiges** Material und sind damit wertvoller als der
Bericht sie einstuft — die Überlappungswarnung gilt für zwei Repos, nicht für
acht. Passend zum Knoten `/shared/arch/repo-aufteilung-2026-08-11-19-app-repos`:
am 2026-08-11 wurden 20 Apps aus dem hub-Monorepo herausgelöst, und genau
diese Herauslösung macht den Unterschied.

**Nachtrag 2026-08-13T19:35, Betreiberentscheidung, wörtlich:** *„für
buckeberg und fahrtenbuch wollten wir auch noch ein eigenes repo geben, machen
wir aber noch nicht weil darin gearbeitet wird."* Die Überlappung ist also
bekannt und beschlossen aufzulösen — nur nicht jetzt. Für diese Recherche
heißt das: buckeberg und fahrtenbuch bleiben vorerst **eine** Quelle, nicht
zwei, und diese Zahl ändert sich später ohne unser Zutun. Knoten `4dd88122`.

Und der Grund, warum ausgerechnet hier nicht gedrängt wird: buckeberg ist laut
Betreiberaussage vom 2026-08-11 „schon aktiv eingesetzt", alle übrigen Apps
sind „noch im demo modus". Die Beta-Direktive — Ausfallzeit kostet nichts —
gilt für buckeberg nicht mehr. Es ist das einzige Repo des Verbunds, bei dem
eine Trennung während laufender Arbeit echten Schaden anrichten kann.

Gemessene Commit-Zahlen (`git log --oneline | wc -l`):

| Repo | Commits | ADR-Dateien (`find … ADR-*.md`) |
|---|---|---|
| openlehr | 1550 | 21 |
| fahrtenbuch | 1878 | 15 |
| buckeberg | 967 | 18 |
| hub | 340 | 32 |
| wohlair | 381 | 10 |
| pflegelotse | 514 | 14 |
| openhood | 512 | 14 |
| begem | 2 | — |
| begem2026 | 2 | — |

### 2.1 Kandidaten mit gutem Ertrag

- **ADRs über alle Repos (rund 120 Dateien, mit Überlappung durch
  gemeinsames Monorepo)** — Extraktionsquelle: die ADR-Dateien selbst
  (`docs/adr/ADR-*.md`), die bereits im Format Kontext→Entscheidung→
  Konsequenz vorliegen. Ertrag: strukturiertes Architekturwissen, das nur
  noch destilliert, nicht mehr aus Prosa herausgezogen werden muss —
  billigste Extraktion im ganzen Verbund, weil die Struktur schon da ist.
  Beispiel gefunden: `ADR-019-universum-kreuzreferenz-system.md` (openlehr)
  benennt die Domänen Pflege-Lotse (NBA-Kriterien, SGB-§§), DRG/Klinik-Lotse,
  OpenHood (OBD2-PIDs), Afrika (MIR-Papers) explizit als Wissensträger.
- **Runbooks und Wiederherstellungs-Dokumente**, z. B.
  `brainlehr/docs/RUNBOOK_WIEDERHERSTELLUNG.md` — Extraktionsquelle: Text
  liegt vor. Ertrag: Betriebswissen (was tun bei Ausfall X), das sich direkt
  in Lehren wandeln lässt, weil es bereits als Handlungsanweisung geschrieben
  ist.
- **Abschluss-/Nachtberichte** (`fahrtenbuch/COMPLETION_REPORT.md`,
  `buckeberg/NACHTBERICHT.md`) — Extraktionsquelle: Freitext-Postmortems.
  Ertrag: mittel bis gut, aber mit Nacharbeit — die Berichte sind für
  Menschen geschrieben, nicht als Lehre strukturiert, brauchen also die
  gleiche Destillation wie ein Fehlerbericht aus einem Chat.
- **Testnamen als Regelkatalog**, Beleg im eigenen Repo:
  `wohlair/test/privacy/health_fields_stay_local_test.dart` — ein Test, der
  bestimmte Feldnamen im Quelltext SUCHT statt eine Funktion zu prüfen.
  Extraktionsquelle: `grep` über Testdateinamen und -inhalte nach diesem
  Muster (Name beschreibt eine Garantie, nicht eine Funktion). Ertrag:
  mittel — funktioniert nur dort, wo dieses Bauformmuster schon angewandt
  wurde, dafür ist der einzelne Fund hochwertig (genau dieser Test steht
  bereits als Vorbildfall im Kopf von `kern/fremdimport.py`).
- **Git-Commit-Historie mit Fehlerbezug** (`git log --grep`,
  Commit-Message-Konvention „fix/why" laut CLAUDE.md-Regel „Committen ohne
  Aufforderung") — Extraktionsquelle: `git log -- <datei>` je Repo. Ertrag:
  hoch bei fahrtenbuch (1878 Commits, langjährig, laut `AI_HANDOFF.md`/
  `COMPLETION_REPORT.md` bereits mit Postmortem-Kultur) und openlehr (1550
  Commits), weil dort das „warum", nicht nur das „was" in den Nachrichten
  stehen soll — das ist aber eine Annahme aus der systemweiten Regel, nicht
  an einzelnen Commits dieser Repos nachgezählt.

### 2.2 Kandidaten mit geringem Ertrag (ausdrücklich benannt)

- **hub** — 340 Commits, 32 ADRs, aber **hub ist selbst der Ort, an dem
  `knowledge.db` und `shared-knowledge/` liegen** (laut CLAUDE.md-Pfaden).
  Eine Extraktion aus hub würde großteils Wissen zurück in den Speicher
  schreiben, aus dem es kam — dieselbe Dopplung, die die bestehende
  Systemregel „Wissen festhalten" ausdrücklich ausschließt: „Repo-Ableitbares
  (Code-Struktur, Git-Historie, CLAUDE.md) … bleibt draußen." Was aus hub
  lohnt, ist bereits im knowledge.db-Workflow erfasst oder wird es beim
  nächsten `/learn`-Lauf; ein gesonderter Extraktionsauftrag für hub selbst
  liefe größtenteils leer.
- **begem / begem2026** — 2 Commits je Repo, praktisch frisch angelegte
  Gerüste ohne gewachsene Historie. Ertrag: **gering**, weil es schlicht
  noch keine Vergangenheit gibt, aus der sich etwas extrahieren ließe — das
  ist keine Bewertung der beiden Projekte, sondern eine Aussage über ihren
  Zeitpunkt.
- **Die `.zip`-Archive im Wurzelverzeichnis** (`mosaikplan*.zip`,
  `fahrtenbuch*.zip`, `wpdrop*.zip`) — kein Git, keine Commit-Historie, kein
  ADR-Ordner erreichbar ohne Entpacken. Ertrag: **gering bis nicht
  feststellbar** ohne einen eigenen Schritt (Entpacken), der außerhalb
  dieser Recherche liegt.

---

## Teil 3 — Schaufenster vs. Prüfkorpus

Die beiden Zwecke ziehen in unterschiedliche Richtungen: Ein Schaufenster
muss ein Fremder in Minuten beurteilen können — das verlangt Allgemeinwissen,
kurze Antworten, keinen Fachjargon. Ein Prüfkorpus muss **Ground Truth**
haben, an der sich Trefferquote automatisch messen lässt — das verlangt
strukturierte Frage-Antwort-Paare, nicht bloß plausible Fragen. Ein Bestand
kann das eine erfüllen und beim anderen versagen.

| Bestand | Schaufenster (Neuling probiert aus) | Prüfkorpus (Abrufgüte messen) |
|---|---|---|
| NASA LLIS | ✗ — Englisch, Aerospace-Jargon, ein Neuling kann eine Antwort nicht selbst beurteilen | ✓ — bereits automatisiert importiert, 1637 strukturierte Lesson-Datensätze, laut `docs/LIZENZPRUEFUNG…` aber nur für interne Auswertung, nicht als offizielles Referenzkorpus mit Ground-Truth-Fragen aufbereitet |
| ASRS | ✗ — Englisch, Luftfahrt-Fachbegriffe | (✓) — Auswertung/Weitergabe laut Prüfung 2026-08-11 grün, aber noch nicht importiert; Ground Truth müsste erst gebaut werden |
| BSI Stand-der-Technik | ✗ — Antwort nur mit IT-Security-Vorwissen beurteilbar, trotz deutscher Sprache und geklärter Lizenz | (✓) für ein Fachpublikum, nicht für „jeder neue Nutzer" |
| **GermanQuAD** | **✓** — Wikipedia-Fakten, deutsch, jeder kann die Antwort selbst nachschlagen | **✓** — genau dafür gebaut (Retrieval-Benchmark mit Ground-Truth-Zuordnung), im Repo bereits als Prüfstand-Material genutzt (`pruefstand/germanquad.py`), aber getrennt vom offenen Beispielbestand zu halten |
| **Gesetze im Internet** (SGB XI, BGB) | **✓** — bekannter Stoff, an bekannter Stelle unabhängig nachprüfbar | ✗ — Gesetzestext hat keine eingebauten Frage-Antwort-Paare; ein Prüfkorpus müsste erst selbst formuliert werden, das ist ein eigener Aufwand |
| **OpenThesaurus** | **✓** — niedrigste Eintrittshürde überhaupt, sofort selbst prüfbar | ✗ — Einwort-Lookups ohne Kontext sind als Retrieval-Test zu flach, um Abrufgüte differenziert zu messen |
| Eigene ADRs/Lehren aus dem Verbund | (✓) nur als „Was kann brainlehr über sich selbst sagen"-Demo, nicht als neutrales externes Beispiel — mischt internen Betrieb mit Vorführung | (✓) bedingt: strukturiert, aber die „richtige" Antwort ist oft die eigene Systemmeinung, nicht extern nachprüfbar — schwächt die Funktion als unabhängiger Maßstab |

**Der eine Satz, der die Verwechslung vermeidet:** Ein Bestand, den heute
schon niemand außerhalb des Systems beurteilen kann (NASA LLIS, BSI-Profil,
ASRS), bleibt ein legitimes Prüfkorpus, taugt aber nicht als das, was der
Betreiber „Schaufenster" nennt — und umgekehrt macht ein sofort verständlicher
Bestand (Gesetzestext, Thesaurus) noch keinen guten Maßstab für Abrufgüte,
weil ihm die eingebaute Ground Truth fehlt. GermanQuAD ist der einzige
geprüfte Kandidat, der beides zugleich leistet, weil Wikipedia-Fakten
allgemeinverständlich UND mit fertigen Frage-Antwort-Paaren versehen sind.

---

## Offene Punkte, nicht Teil dieser Recherche

- Lizenzprüfung von GermanQuAD, Gesetze im Internet und OpenThesaurus an der
  Primärquelle — hier nur Modellwissen, ausdrücklich als ungeprüft markiert.
- Jeder tatsächliche Import bräuchte das Wort des Betreibers für den
  Netzabruf (Aufgabe 7, wie im Auftrag benannt) und würde durch
  `kern/fremdimport.py` (Projektion + Gegenprobe + Gattung
  `nachschlagewerk`) laufen.
- Die Größenangabe zu ASRS und NIST beruht auf dem Fremdbeleg vom
  2026-08-11, nicht auf eigener Zählung dieser Sitzung.

---

## Nachtrag des Orchestrators — was diese Recherche NICHT abgesucht hat

Der Rastervermerk gehört dazu, sonst heißt „nicht gefunden" nur „nicht
gesucht". Am 2026-08-09 hat genau diese Lücke zwei Nachbarn mit zusammen über
100 000 Sternen unsichtbar gemacht, weil ausschließlich nach *Eigenschaften*
gesucht wurde und Codeverzeichnisse nicht einmal als bewusst ausgelassen im
Vermerk standen (`L-402a51`, dreimal aufgetreten).

**Abgesucht:** die eigenen Repos, die bereits als Aufgabe benannten Bestände
(MAUDE, ASRS, NIST, BSI), Websuche nach Datensätzen.

**NICHT abgesucht, und das sind echte Lücken:**
- **Hugging Face Datasets** als eigener Suchraum. GermanQuAD kam über die
  bereits im Repo liegende `pruefstand/germanquad.py` ins Bild, nicht über
  eine Suche — es ist also ein Zufallsfund, kein Rechercheergebnis. Was dort
  sonst an deutschsprachigen Frage-Antwort-Beständen liegt, ist offen.
- **GovData / Open-Data-Portale des Bundes und der Länder.** Amtliche Werke
  sind nach §5 UrhG gemeinfrei; das ist der rechtlich sauberste Raum
  überhaupt und wurde nicht systematisch abgesucht.
- **Die Laien-Suchbegriffe.** Gesucht wurde nach unseren Fachwörtern. Wer als
  Neuling einen Beispielbestand sucht, tippt „Beispieldatensatz Wissensbasis"
  oder „sample knowledge base" — dieses zweite Raster fehlt.

## Was bereits belegt ist und die Auswahl mitentscheidet

`pruefstand/germanquad.py` liegt seit 2026-08-10 im Repo und bringt
`count_oversized(corpus, limit_tokens=2048)` mit — die Funktion zählt
Einträge, die über die Kontextgrenze der Einbettung hinausgehen. Damit ist
GermanQuAD nicht nur Schaufenster und Prüfkorpus, sondern liefert zugleich
das Messmittel für die offene Aufgabe 69 (`num_ctx=2048` kappt bei rund 8000
Zeichen). Das ist ein Grund mehr für diesen Bestand, und er stand in keiner
der drei Anforderungslisten.
