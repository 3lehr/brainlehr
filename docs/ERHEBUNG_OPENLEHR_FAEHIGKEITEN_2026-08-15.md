# Was openlehr kann — Erhebung in vier Stufen, und die Trennlinie nach ADR-014

**Stand** 2026-08-15T21:16:50+0200
**Auftrag** `brainlehr/docs/STARTPROMPT_OPENLEHR_ATELIER_2026-08-15.md`
**Gegenstand** `/Volumes/daten/Begod2026/openlehr`, `apps/openlehr/`, Zweig
`merge/daten-features`, Commit `21b00d8f`
**Gebaut wurde nichts.** Diese Datei ist der einzige Liefergegenstand.

---

## 0. Womit gemessen wurde

| Stufe | Messmittel | keine Schätzung, sondern |
|---|---|---|
| 1 Fachlogik | `find`/`wc` über `daemon/` | Dateien und Zeilen |
| 2 Erreichbar | **die laufende Anwendung befragt** — `create_app()` importiert, `app.routes` aufgezählt | 329 Endpunkte |
| 3 Bedienbar | alle `"/v1/…"`-Zeichenketten aus `daemon/static/**` und aus den nativen Oberflächen, gegen die Routenliste gehalten | 113 + 69 Treffer |
| 4 Nachweislich richtig | voller `pytest`-Lauf, 16:09 min | Zahl mit Nenner, unten |

Stufe 2 wurde bewusst **nicht** per Grep über Modulnamen erhoben — genau die
Verwechslung, die laut `L-b38d85` hier zweimal Geld gekostet hat. Die Routenliste
stammt aus der Anwendung selbst, nicht aus dem Quelltext.

## 1. Die Zahl mit Nenner — zuerst, wie verlangt

```
25 failed, 3386 passed, 6 skipped, 1 xfailed  in 969.46s (0:16:09)
```

`.venv/bin/python -m pytest -q`, voller Baum, 2026-08-15T21:0x. **3418 gesammelt,
25 rot.** Damit gilt für jede Fähigkeit unten: grün ist kein Beleg, und rot ist
nicht automatisch ein Fachfehler. Die 25 zerfallen in sechs Ursachen, und nur
vier davon sind Fehler in der Sache:

| Ursache | Anzahl | Beispielbeleg |
|---|---|---|
| **Umlaut-Umstellung, Erwartung zog nicht nach** | 5 | `assert 'Finanzamt-Frist prüfen' == 'Finanzamt-Frist pruefen'` · `assert 'zu gross' in 'datei zu groß für den lokalen upload.'` · `'RE-2026--00001'` gegen erzeugtes `'RE-2026-00001'` |
| **Prüfstand ohne Anmeldung** | 4 | `steuer_dataset_validation_runner.py:347: User create failed (403): Diese Aktion braucht eine gueltige Anmeldung ueber /v1/context/select_user` |
| **Feld im Rechenweg umbenannt** | 5 | `KeyError: 'nach_sonderausgaben_vereinfacht'` (2×) · `KeyError: 'validation_status'` (3×) |
| **Quellenaudit blockiert** | 3 | `blockers: [{'id': 'estg', 'reason': 'source_review_due'}, {'id': 'ustg', …}]` |
| **erzeugtes Artefakt veraltet** | 2 | `API_SPEC.json ist veraltet` · `STAND.md ist 14 Commits alt (Schwelle 10)` |
| **Messwerkzeug unvollständig** | 1 | siehe §5, Befund 2 |
| **echter Fachbefund** | 5 | ELSTER-Arbeitsblatt `assert 2 == 1` · Zahlungseingang schließt Rechnung nicht · Mahnung landet nicht in der Outbox · ungültiges Angebot erscheint nicht in der Aktionsschlange |

Die dritte Zeile ist die unangenehmste: Zwei verschiedene Testdateien greifen auf
ein Feld zu, das der Rechenweg nicht mehr liefert. Das ist kein Textvergleich,
das ist die Naht zwischen Rechnung und Abfrage.

## 2. Stufe 1 — Fachlogik, gemessen

| | |
|---|---|
| `daemon/steuer/` | **130 Module, 43 787 Zeilen** |
| `daemon/` ohne `steuer/` | **51 Module, 28 230 Zeilen** (davon `app.py` allein 15 886) |
| Weboberfläche | 20 Bildschirme, 38 JS-Dateien, 13 859 Zeilen |
| macOS-Schale `macshell/` | **19 Swift-Dateien, 14 611 Zeilen** |
| Tests | 292 Dateien unter `apps/openlehr/tests/`, dazu 20 jsdom-Suiten |

Zum Vergleich, weil er die wichtigste Zahl dieses Berichts ist:
**`atelier` hat heute 17 Swift-Dateien mit 3 514 Zeilen.** Die openlehr-Schale ist
das Vierfache — und sie trägt Hauptfenster, Navigation, Dienstaufsicht,
Debug-Fenster, IDE-Reiter und Steuerfenster.

## 3. Stufe 2 und 3 — erreichbar und bedienbar

**329 Endpunkte** laufen in der Anwendung. Davon:

| | Endpunkte | von einem Bildschirm aus erreicht |
|---|---|---|
| `/v1/steuer/**` | 189 | **108** (Weboberfläche) |
| alles übrige | 140 | **69** (macshell, VS-Code-Erweiterung, CLI, Kanäle) |
| **gesamt** | **329** | **177 (54 %)** |

**Die 20 Bildschirme und woran sie hängen** — jeder Bildschirm ruft echte
Endpunkte, keiner ist eine Attrappe:

| Bildschirm | ruft |
|---|---|
| `anmelden`, `gemeinsam` | demo · ui-prefs · web |
| `ordner`, `belege`, `belegansicht` | belege · capture · import · workflow · classify · documents · ocr |
| `klaerungen` | clarifications · documents |
| `rechnungen`, `anzahlungen` | invoice · offers · backoffice · settings · anzahlungen |
| `jahr`, `kennzahlen` | elster · export · workflow · homeoffice · kennzahlen |
| `anlagegueter`, `vorsorge` | aveuer · private · profile |
| `stammdaten`, `firmendaten` | backoffice · profile · settings |
| `postfach`, `mailansicht`, `suche` | autopilot · mail · similar |
| `assistent` | assistant · chat |
| `zahlungen` | import · workflow |

**Die 81 Steuer-Endpunkte ohne Bildschirm** ballen sich an drei Stellen:
`mail` (12), `intake` (7), `kalender` (5). Dazu je 4 bei `llm-settings`,
`golden-set`, `exports`, `assistant`. Das ist kein Streuverlust, sondern sind
drei ganze Fähigkeiten, die über den Endpunkt existieren und über keinen
Bildschirm.

## 4. Stufe 4 — was nachweislich richtig ist

**Es gibt eine echte E2E-Reise, und sie ist besser als erwartet.**
`scripts/reise/drehbuch.json`: **36 Schritte, alle als `implementiert` markiert**,
von A1 „frisches System" bis I2. Der Weg führt vom leeren Wurzelverzeichnis über
Anmeldung, Firmendaten, Ordner, Chaos-Korpus, Einlesen, Sortieren, Belege,
Tarifzonengrenze (−1 / auf / +1, also Grenzwertprobe), Anlagegut, Vorsorge,
Anzahlung, Homeoffice, „was fehlt mir noch", ELSTER-Arbeitsblatt und Paket,
Jahresabschluss samt Wieder-Öffnen, Rechnung per Chat, Verbindlichstellen
(auch zweimal — Unumkehrbarkeit), Brief, Kontoauszug, Zahlungszuordnung bis zum
jsdom-Endzustand. Vier Schritte brauchen ein echtes Modell.

Dazu **11 E2E-/Walkthrough-Testdateien**, darunter `test_walkthrough_e2e.py` mit
37 Schritten (1 606 Zeilen) und `test_walkthrough_weiss_nicht_e2e.py` mit
15 Schritten zum Herkunftsnachweis einer Antwort.

**Und trotzdem lautet der Stand der Reise „nicht nachgemessen".** Im Repo liegt
**kein festgehaltenes Ergebnis eines Reise-Laufs** — gesucht wurde nach der
Sache, nicht nach dem Namen; gefunden wurden nur der Läufer, das Drehbuch und
vier Testdateien für dessen Prüfer. Ein Drehbuch, dessen letzter grüner Lauf
niemand kennt, ist ein Versprechen, kein Beleg.

## 5. Drei Befunde am Messwerkzeug und an der Übergabe

**Befund 1 — `router.py` ist nicht, was die Übergabe sagt.** Beide Übergabepapiere
nennen `router.py` die „feldgeprüfte Liste der Anforderung". `daemon/router.py`
hat **194 Zeilen und entscheidet, welches Sprachmodell eine Anfrage bekommt** —
mit der Anforderungsliste hat es nichts zu tun. Gemeint ist
`daemon/steuer/router.py` (5 841 Zeilen, 168 Endpunkte) zusammen mit `app.py`
(15 886 Zeilen, 136 Endpunkte). Die Aussage stimmt, der Dateiname nicht.

**Befund 2 — der Endpunkt-Wächter schlägt falsch an, und das deckt eine Lücke
auf.** `test_steuer_endpoint_registry.py::test_keine_neuen_aufrufe_ins_leere` ist
rot und meldet fünf Aufrufe ins Leere, alle vom Klärungen-Bildschirm.
**Sie existieren:** `GET /v1/steuer/clarifications`,
`POST …/{cid}/antworten`, `GET …/{cid}/beleg-kandidaten`, `POST …/{cid}/resolve`
sind in der laufenden Anwendung vorhanden. Ursache ist eine **fest verdrahtete
Dateiliste** in `tools/steuer_endpoint_registry.py`: acht Routerdateien,
`clarifications_router.py` fehlt — es wurde später aus `router.py` herausgelöst.

Die zweite Hälfte wiegt schwerer als der Fehlalarm: Dieselbe unvollständige
Liste trägt die Gegenzahl `BASELINE_OHNE_AUFRUFER = 117`. **Eine Baseline, die
über einen zu schmalen Bestand erhoben wurde, misst zu wenig — und meldet das
nicht.** Genau die Fehlerklasse aus `L-0e0ab6`, hier in beide Richtungen
gleichzeitig.

**Befund 3 — zwei erzeugte Artefakte laufen dem Code hinterher.**
`docs/openlehr/API_SPEC.json` ist veraltet (`python apps/openlehr/scripts/export_openapi.py`),
`apps/openlehr/STAND.md` ist 14 Commits alt bei einer Schwelle von 10. Beides ist
kein Fachfehler, aber beides ist eine Quelle, aus der ein nächstes Fenster
falsche Zahlen zieht.

## 6. Die Trennlinie nach ADR-014

Zugeordnet wurde **jeder der 329 Endpunkte**, nicht eine Auswahl. Das Ergebnis ist
eine Einschätzung und als solche angreifbar; die Zahlen darunter sind es nicht.

| Sorte | Endpunkte | was darunter fällt |
|---|---|---|
| **Kern** — immer da | **78** | Ausweis und Anmeldung (`/v1/users`, `/v1/context`, `/v1/permissions`, Kennwörter) · Modellzugänge (`/v1/models`, `/v1/ollama`, `/v1/setup/providers`, `llm-settings`) · Dienstaufsicht (`/v1/runs`, `/v1/audit`, `/v1/waechter`, `/v1/autonomy`, `/v1/debug`, `/v1/status-truth`) · Datenschutz-Vorschau (`/v1/privacy/proxy/preview`) |
| **Bestandteil** — gemeinsam gebaut, auf Anforderung geladen | **93** | Dokumenteingang und Erkennung (`intake`, `import`, `ocr`, `documents`, `capture`, `/v1/files`) · **Klärungen** (`clarifications`) · Wissen und Gedächtnis (`/v1/knowledge`, `/v1/memory`, `similar`) · Mail und Kalender · Chat-Sitzungen · Kontakte (`backoffice`) · Sicherung, Ausfuhr, Oberflächen-Vorlieben |
| **Domäne Steuer** | **102** | Rechnung, Angebot, Mahnwesen, EÜR/ELSTER, Anlagevermögen, Vorsorge, Anzahlungen, Homeoffice, Kennzahlen, Fristen, Finanzamt, Jahresabschluss |
| **Domäne Entwicklungsassistent** | **56** | `/v1/ide/**`, `/v1/plan_coach`, `/v1/plan_autonomy`, `/v1/orchestrator/**`, `/v1/goals`, `/v1/roadmap`, `/v1/konsile`, `/v1/modules`, `/v1/tools/**`, `/v1/ask` |

### Die vier Sätze, die aus dieser Tabelle folgen

**1. openlehr enthält zwei Domänen, nicht eine.** Die 140 Endpunkte außerhalb von
`/v1/steuer` sind nicht durchweg atelier-Stoff. **56 davon sind ein
Entwicklungsassistent** — Dateibaum lesen und schreiben, Aufgaben ausführen,
Pläne begleiten, Arbeiter beauftragen, Schalen messen. Das ist eine eigene
Domäne nach ADR-013 und gehört weder in den Kern noch in die Steuer.
Wer die Trennung „Steuer gegen Rest" zieht, schiebt sie versehentlich ins atelier.

**2. Der Kern existiert bereits zweimal.** Ausweis, Rahmen, Navigation,
Dienstaufsicht und Modellzugänge sind in openlehr gebaut (78 Endpunkte,
`macshell/` mit 14 611 Zeilen) **und** im atelier (3 514 Zeilen). Nach H12 wird
openlehr gelesen, nicht kopiert — die 78 Endpunkte sind damit die genaueste
Anforderungsliste, die das atelier bekommen kann, weil sie unter Druck entstanden
ist. `StiftshuetteRoot.swift`, `ServiceSupervisor.swift` und `DebugWindow.swift`
beantworten Fragen, die das atelier noch vor sich hat.

**3. Der stärkste Bestandteil-Kandidat ist der, den niemand auf der Liste hatte:
die Klärung.** `clarifications` ist der gebaute Fall von „ich weiß es nicht" —
mit Frage, Priorität, Belegkandidaten, Herkunft der Antwort (Nutzer oder Import)
und der Regel, dass eine zweite Antwort auf eine beantwortete Klärung ein 400
ist. Er hat 15 E2E-Schritte und einen eigenen Bildschirm. Das ist **derselbe
Mechanismus, den der Torwächter für jede Domäne braucht**: eine Summe kommt nur
durch, wenn sie ihre Summanden mitliefert. Nach der H12-Regel „was beim zweiten
Kind kopiert wird, wandert nach unten" gehört er nach unten — und er ist heute
fertiger als alles, was dafür sonst existiert.

**4. Die Tabellenkalkulation trifft auf eine bestehende Rechnung, nicht auf
leeres Feld.** ADR-016 will EÜR und UStVA als Tabelle. In openlehr sind sie als
Endpunkte gebaut und über den Bildschirm `jahr` bedienbar (`elster`, `export`,
`workflow`), einschließlich ELSTER-Arbeitsblatt und Paketerzeugung. Der
Reise-Schritt F1 heißt „Arbeitsblatt zeigen". **Die 37 Funktionen der Positivliste
werden also nicht gegen ein leeres Blatt gemessen, sondern gegen eine laufende
Rechnung** — und deren ELSTER-Arbeitsblatt ist heute einer der fünf echten
Fachbefunde (`assert 2 == 1`). Wer die Tabelle baut, hat damit eine Gegenprobe
geschenkt bekommen: Beide Wege müssen dieselbe Zahl liefern.

### Nachtrag 2026-08-16T07:12:00+0200 — vier angebliche Streitfälle, keiner davon offen

Die erste Fassung dieses Abschnitts legte vier Zuordnungen dem Betreiber vor.
**Sein Einwand traf:** *„aber was gibt es zu entscheiden? wir wollten einen harten
Schnitt machen und das legacy nur als Blaupause benutzen!"* Der harte Schnitt ist
beschlossen (H12), und keiner der vier Fälle fragt danach — sie fragen, auf
welcher Seite der ADR-014-Linie eine Fähigkeit **beim Neubau** steht. Diese Frage
beantworten die vorhandenen Regeln, wenn man sie anwendet statt sie
weiterzureichen.

| angeblich strittig | die Regel, die es entscheidet | Ergebnis |
|---|---|---|
| **Kontakte** (`backoffice`, 6) | H12: *was beim zweiten Kind kopiert wird, wandert nach unten.* Der Korrekturator hat Schülerinnen und Eltern als Gegenüber | **Bestandteil** — das Adressbuch. Die steuerlichen Felder (Steuernummer, Rechnungsempfänger) sind Domäne und sitzen darauf, nicht darin |
| **Mail und Kalender** (22) | ADR-014 Nachtrag: *gemeinsam gebaut, nicht immer gebraucht* — wörtlich der Dokumentfenster-Fall | **Bestandteil**, auf Anforderung geladen. Eine Domäne ohne Posteingang lädt es nie |
| **Wissen und Gedächtnis** (`/v1/knowledge`, `/v1/memory`, 6) | ADR-007: brainlehr ist die Schicht, die trägt | **Wird nicht neu gebaut.** Beim harten Schnitt entsteht kein zweiter Speicher — brainlehr *ist* der Speicher. Es war nie eine Zuordnungsfrage, sondern eine, die sich mit dem Schnitt erledigt |
| **`golden-set`** (4) | brainlehr ist die Instanz, die prüft und Belege verlangt | **brainlehr**, nicht Domäne. Ein Prüfkorpus misst die Güte einer Zuordnung — das ist Aufsicht, nicht Steuerrecht |

**Und noch eine Zuordnung fällt damit weg, die gar nicht auf der Liste stand:**
Nach ADR-013 ist die Oberfläche einer Domäne **Beschreibung, nicht Code**. Die 20
HTML-Bildschirme und 13 859 Zeilen JavaScript wandern also nirgendwohin — sie
werden gelesen und als Beschreibung neu gezeichnet. Das ist keine Entscheidung,
das ist die Folge einer bereits getroffenen.

### Was tatsächlich offen ist — eine Frage, nicht vier

**Wird der Entwicklungsassistent (56 Endpunkte) als Domäne neu gebaut, oder fällt
er mit dem Schnitt weg?**

Das ist keine Zuordnungsfrage — ADR-014 sagt bereits, wohin er gehört, falls es
ihn gibt: eine eigene Domäne neben `openlehr_einzelunternehmer`, nicht Kern.
Offen ist der **Umfang**, und Umfang ist keine Regelfrage. Dahinter stehen
`/v1/ide/**` (Dateibaum lesen, schreiben, Vorschau), `/v1/plan_coach`,
`/v1/plan_autonomy`, `/v1/orchestrator/**` samt Tuner und Arbeiter-Messung,
`/v1/goals`, `/v1/roadmap`, `/v1/konsile`, `/v1/tools/**` (`shell_exec`,
`file_read`, `confirm_token`) und `/v1/ask`.

Der Grund, warum diese eine Frage nicht von selbst zerfällt: Sie entscheidet
nicht, wo etwas hinkommt, sondern **ob überhaupt jemand dafür arbeitet.** Fällt
er weg, ist der Rest der Erhebung um 56 Endpunkte kleiner und die Blaupause um
ein Kapitel kürzer.

## 7. Was diese Erhebung ausdrücklich nicht sagt

- **Kein Aufwand geschätzt.** Auftragsgemäß; die Art der Lücke trägt, eine
  Schätzung täte es nicht.
- **Die Reise wurde nicht gefahren.** Vier Schritte brauchen ein echtes Modell,
  der Lauf gehört in eine eigene Sitzung mit festgehaltenem Ergebnis. Bis dahin
  steht bei jeder Fähigkeit oben „bedienbar", nicht „richtig".
- **Die jsdom-Suiten wurden nicht einzeln gefahren.** Nur zwei der zwanzig hängen
  an pytest (`anmelden`, `stammdaten`); die übrigen 18 laufen über
  `node run_all.js` und waren in der Zahl mit Nenner nicht enthalten.
- **`daemon/steuer/` wurde nicht auf tote Module geprüft** — eine frühere Messung
  fand dort 0, das wurde nicht nachgerechnet.

## 8. Der eine Satz, der in den nächsten Auftrag gehört

> Sieht der Code anders aus als hier beschrieben, halte dich an den Code und melde
> die Abweichung.

Er hat auch in dieser Sitzung getragen: Ohne ihn wäre `router.py` als
Anforderungsliste weitergereicht worden, und der Klärungen-Bildschirm stünde hier
als tot.
