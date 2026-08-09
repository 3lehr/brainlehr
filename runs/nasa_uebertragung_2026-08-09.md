# NASA-LLIS Uebertragungs-Stichprobe — 2026-08-09T07:15:00+0200

Auftrag: 40 Knoten aus `/nasa-llis` (1638 total, 81% des Bestands), gestreut ueber
Unterbereiche, auf domaenenfreie Uebertragbarkeit pruefen. Reine Messung/Stichprobe,
KEINE Schreibung in den Bestand, keine Kanten angelegt.

## Streuung

Nicht die ersten 40. Aus den Tag-Kategorien der 1637 Knoten (Kategorien-Zaehlung per
sqlite ueber `tags`-Spalte) wurden 40 verschiedene Kategorien gewaehlt — von den
haeufigsten (Engineering design and project processes, Spacecraft, Program Management)
bis zu selteneren (Communication Systems, Human factors impact on mission design,
Role of civil service technical staff versus contractor staff). Je Kategorie ein
zufaellig gezogener, noch nicht verwendeter Knoten (`random.seed(42)`/`random.seed(43)`,
Python, deterministisch reproduzierbar). Damit deckt die Stichprobe Software, Hardware,
Recht/Datenschutz, Logistik, Personalfuehrung, Reviews, Sicherheit, Beschaffung und
Requirements-Prozesse ab, nicht nur ein Cluster.

## Format je Fall

`Pfad — Titel` / **Behauptung** (domaenenfrei) / **Urteil** (uebertragbar/gebunden + Grund)
/ **Entsprechung** (Pfad/Kennung im uebrigen Bestand, oder "keine gefunden").

---

### 1. `/nasa-llis/2218` — Flight Software Engineering Lessons
**Behauptung:** Software, die parallel zum restlichen System und unter Zeitdruck entsteht, ist die Stelle, an der sich Risiko konzentriert.
**Urteil:** uebertragbar — reines Aussagemuster ueber Softwareentwicklung, kein Raumfahrtbezug.
**Entsprechung:** keine gefunden (Suche nach Risiko aus paralleler Entwicklung ergab nur Einzelfaelle, keinen allgemeinen Knoten).

### 2. `/nasa-llis/8302` — Reducing the Error Rate in Command Files Uplinked to the Spacecraft
**Behauptung:** Fehlerraten bei kritischen Befehls-/Konfigurationsuebertragungen steigen in Phasen hoher Betriebs-Taktung und bei Erstereignissen; das Risiko muss aktiv gegen andere Projektrisiken abgewogen werden.
**Urteil:** uebertragbar — Deploy-/Release-Risiko waehrend Phasen erhoehter Aenderungsfrequenz ist ein Softwarethema.
**Entsprechung:** keine gefunden.

### 3. `/nasa-llis/5996` — Vehicle Assembly Building (VAB) Fall from the 41st Floor **[GEGENPROBE]**
**Behauptung:** Wer in grosser Hoehe arbeitet, muss persoenliche Schutzausruestung tragen, um Sturzfolgen zu verhindern.
**Urteil:** GEBUNDEN — physische Absturzsicherung hat kein Softwareaequivalent; das ist Arbeitsschutz an Hardware, kein Ingenieurprinzip, das sich abstrahieren liesse.
**Entsprechung:** entfaellt.

### 4. `/nasa-llis/2217` — Maintain a Master Schedule of Supplier Audits
**Behauptung:** Wenn mehrere Pruefer unabhaengig voneinander dasselbe Ziel pruefen, ohne sich abzustimmen, belastet das den Geprueften unnoetig und verschwendet Pruefkapazitaet — ein gemeinsamer Pruefplan behebt das.
**Urteil:** uebertragbar — Koordinationsproblem bei mehrfachen Audits/Reviews desselben Ziels ist allgemein.
**Entsprechung:** keine gefunden.

### 5. `/nasa-llis/4936` — Logistics Sparing Methodology
**Behauptung:** Ohne eine konsistente, analysebasierte Methode fuer Ersatz-/Pufferkapazitaet werden Ressourcen durch ad-hoc Ueber- oder Unterbevorratung verschwendet.
**Urteil:** uebertragbar — Kapazitaets-/Pufferplanung (z.B. Server-Kapazitaet, Vorhalte-Strategie) ist ein generisches Thema.
**Entsprechung:** keine gefunden.

### 6. `/nasa-llis/5479` — Proper Manufacturing, Handling, Use, Storage and Care Of Metal Bellows Flex Hoses **[GEGENPROBE]**
**Behauptung:** Metallbaelge-Schlaeuche sind anfaellig fuer Biegewechsel-Ermuedung, die durch Inspektion praktisch nicht erkennbar ist.
**Urteil:** GEBUNDEN — Materialermuedung an Metallteilen ist Werkstoffkunde. Die Versuchung, daraus "latente Schaeden sind unsichtbar bis zum Ausfall" als Softwareweisheit (Technische Schulden) zu ziehen, waere eine erzwungene Verbindung: Der Kern der Lehre ist die physikalische Nichtdetektierbarkeit per Sichtpruefung, nicht ein allgemeines Prinzip.
**Entsprechung:** entfaellt.

### 7. `/nasa-llis/4216` — Space Vehicle Database for Data Generated During Development
**Behauptung:** Ein durchgaengiger, abfragbarer Datenspeicher fuer Test-/Leistungsdaten (statt verstreuter Dateien) verhindert Entscheidungsblockaden und liefert bessere Modelle.
**Urteil:** uebertragbar — klassisches "verstreute Daten vs. zentraler Speicher"-Muster.
**Entsprechung:** GEFUNDEN — `/methodik/adr-bestand-hub-docs-adr/adr-013-knowledge-graph-als` (ADR-013, Knowledge Graph als Wissensbasis). Bestaetigung: dieses Projekt hat exakt diesen Schluss bereits selbst gezogen und gebaut (das befragte knowledge.db IST die Antwort auf diese Lehre).

### 8. `/nasa-llis/6076` — MPS Databook
**Behauptung:** Ohne eine einzige, unter Versionskontrolle stehende autoritative Quelle fuer Analyseparameter arbeiten Leute mit veralteten Dateien und produzieren Fehler; eine zentrale, laufend aktualisierte Quelle identifiziert zugleich alle Nutzer.
**Urteil:** uebertragbar — "keine Single Source of Truth" ist universell in der Softwarearbeit.
**Entsprechung:** GEFUNDEN — dieselbe ADR-013 (Bestaetigung, keine neue Erkenntnis).

### 9. `/nasa-llis/5476` — The Value of Post Flight Reports and System Reviews
**Behauptung:** Systematische Nachbetrachtung, die Ergebnisse mit Entwurfsentscheidungen korreliert, deckt wiederkehrende Probleme auf, die sonst unbemerkt blieben.
**Urteil:** uebertragbar — das ist die Postmortem-/Retro-Idee.
**Entsprechung:** keine gefunden (kein eigener Postmortem-Prozess-Knoten im Bestand, nur die "Es funktioniert braucht Beleg"-Direktive, die etwas anderes prueft).

### 10. `/nasa-llis/3377` — Software Requirements Management
**Behauptung:** Unvollstaendige, unklare oder spaet geaenderte Anforderungen kosten umso mehr, je spaeter im Lebenszyklus sie entdeckt werden; manuelle Nachverfolgung ist ineffizient, Werkzeuge plus enge Abstimmung mit dem Auftraggeber sind noetig.
**Urteil:** uebertragbar — direkt, ohne jede Uebersetzung.
**Entsprechung:** keine gefunden (kein Requirements-Traceability-Knoten im Bestand).

### 11. `/nasa-llis/6758` — Review of Open Work at Integration and Test Readiness Reviews
**Behauptung:** Unerledigte Arbeit an einer Komponente kann andere Komponenten gefaehrden, sobald sie integriert wird; offene Punkte muessen vor dem naechsten Integrationsschritt geprueft werden.
**Urteil:** uebertragbar — Merge/Integration mit bekannten offenen Fehlern ist dasselbe Muster.
**Entsprechung:** keine gefunden.

### 12. `/nasa-llis/8401` — Schedule Early Generation and Validation of Simulated Science Datasets
**Behauptung:** Wird nicht frueh und gemeinsam geplant, welche Testdaten alle kritischen Faelle abdecken muessen, entstehen spaete Luecken in der Testabdeckung.
**Urteil:** uebertragbar — Testdaten-/Fixture-Planung ist Softwarealltag.
**Entsprechung:** schwache Entsprechung — `/methodik/direktiven/walkthrough-doktrin-alle-coding-aufgaben-ohne-aufruf` verlangt zwar E2E-Testabdeckung, adressiert aber nicht explizit die fruehe gemeinsame Planung von Testdatensaetzen. Als Bestaetigung gewertet, nicht als Treffer 1:1.

### 13. `/nasa-llis/2356` — Chiller Coil Coating Failure
**Behauptung:** Eine unangekuendigte Prozessaenderung bei einem Zulieferer bricht stillschweigend Annahmen, auf die sich die eigene Fertigung verlaesst — sichtbar wird das erst im Betrieb.
**Urteil:** uebertragbar (mit Abstrichen) — Analogie zu stillem Verhaltenswechsel bei Abhaengigkeiten/Vendor-Updates ist tragfaehig, auch wenn die Lehre selbst rein materialtechnisch erzaehlt ist.
**Entsprechung:** keine gefunden (Suche nach "Abhaengigkeit aktualisiert, Verhalten stillschweigend geaendert" traf nur Themen-fremde Treffer).

### 14. `/nasa-llis/5204` — Enterprise Architecture / Access to Program Data
**Behauptung:** Fehlen gemeinsame Werkzeuge/Technologien, um Information ueber eine verteilte Organisation zu verbreiten, leiden Entscheidungsfindung und Koordination.
**Urteil:** uebertragbar — Datensilos/fehlendes internes Tooling.
**Entsprechung:** GEFUNDEN — ADR-013 (dieselbe, Bestaetigung).

### 15. `/nasa-llis/1765` — Managing Rover-Orbiter Relay Link Prediction Variability
**Behauptung:** Wo die tatsaechliche Verfuegbarkeit einer Ressource von der Vorhersage abweicht, sollte um einen konservativen Wert (z.B. ein Sigma unter Vorhersage) geplant werden statt um den Mittelwert.
**Urteil:** uebertragbar — Kapazitaetsplanung unter Streuung (z.B. Bandbreiten-/Rate-Limit-Schaetzungen) ist ein generisches Muster.
**Entsprechung:** keine gefunden.

### 16. `/nasa-llis/6536` — Communicate Requirements Associated with Analysis Tied to Required Verification Data
**Behauptung:** Delegiert eine Organisation eine Analyse an eine nachgeordnete Gruppe, ohne die geltenden Randbedingungen (z.B. welche Datenquellen zulaessig sind) vollstaendig mitzugeben, kann die Analyse technisch korrekt und sachlich falsch fertiggestellt werden — entdeckt erst in einem spaeten Review.
**Urteil:** uebertragbar — direkter Treffer auf Auftrags-/Delegationsprobleme.
**Entsprechung:** GEFUNDEN — `/methodik/direktiven/nachsehen-bevor-gefragt-oder-delegiert-wird-systemweit` und die CLAUDE.md-Direktive "Auftraege an Agenten sind Schnappschuesse" (vier Handgriffe fuer Auftragsklarheit) treffen dieselbe Fehlerklasse. Bestaetigung, keine neue Erkenntnis — dieses System hat den Fehler bereits selbst gemacht und dokumentiert (z.B. L-c64f3b, Hook-Kontext faelschlich als eigene Arbeit gelesen).

### 17. `/nasa-llis/4456` — Ice Detection Camera (IDC) Close Call
**Behauptung:** Ausruestung, die nicht denselben Qualifizierungsprozess durchlaeuft wie Produktivsysteme, weil sie "nur ein Prototyp" ist, versagt im Feld genau an der Stelle, an der abgekuerzt wurde.
**Urteil:** uebertragbar — Analogie zu Ad-hoc-Skripten/Tools neben Produktivsystemen.
**Entsprechung:** keine gefunden.

### 18. `/nasa-llis/1760` — Process Control to Prevent Incorrect Assembly (Video Lesson)
**Behauptung:** Sehen zwei Bauteile gleich aus, funktionieren aber unterschiedlich, sollte die Konstruktion falsche Montage unmoeglich machen (Poka-Yoke), statt sich auf Aufmerksamkeit oder Inspektion zu verlassen.
**Urteil:** uebertragbar — Mistake-Proofing ist ein Kernprinzip, das sich 1:1 auf Typsysteme/Guards uebertraegt.
**Entsprechung:** GEFUNDEN — `/shared/arch/neuer-status-enum-wert-statt-zusatz` (neuer Zustand als Enum-Wert statt Zusatz-Flag, erzwingt ueber exhaustive switches Compilerfehler an jeder vergessenen Stelle — dasselbe Prinzip: Fehler durch Konstruktion verhindern statt durch Vorsicht). Bestaetigung.

### 19. `/nasa-llis/6976` — Government Property Disposition Efficiencies **[GEGENPROBE]**
**Behauptung:** Batch-Verarbeitung, elektronische Uebergaben und Ausnahmegenehmigungen reduzieren doppelte Dateneingabe und Wartezeit zwischen zwei Organisationssystemen.
**Urteil:** GEBUNDEN — die konkreten Mechanismen (DCMA-Wartefristen, PCARSS-Formulare, Regierungsvertragsrecht) sind so spezifisch an US-Beschaffungsburokratie gebunden, dass keine trennscharfe, nicht-triviale Uebertragung uebrigbleibt. Was uebrig bliebe ("Stapelverarbeitung spart Zeit") ist zu allgemein, um als eigenstaendige Erkenntnis zu zaehlen.
**Entsprechung:** entfaellt.

### 20. `/nasa-llis/4496` — Umbilical Plates Project Lessons Learned
**Behauptung:** — keine extrahierbar. Der Lesson-Text lautet woertlich "See attachment"; Inhalt liegt nicht im Datensatz vor, nur eine Kategorienliste.
**Urteil:** NICHT BEURTEILBAR — Datenluecke im Import, kein Urteil moeglich.
**Entsprechung:** entfaellt. (Hinweis fuer die Ausbeuterechnung: dieser Fall zaehlt nicht zu den 39 beurteilten.)

### 21. `/nasa-llis/3220` — Dynatube Seal Savers **[GEGENPROBE]**
**Behauptung:** Ein Teflon-Ring als Verschleissschutz fuer eine Dichtflaeche verhindert Folgeschaeden bei wiederholtem Trennen/Verbinden.
**Urteil:** GEBUNDEN — konkretes mechanisches Bauteil fuer eine konkrete Dichtungsart. Kein abstrahierbares Prinzip jenseits von Hardware.
**Entsprechung:** entfaellt.

### 22. `/nasa-llis/2676` — Logistics Lessons Learned in NASA Space Flight
**Behauptung:** Werden Betriebsdaten auf getrennte Systeme entlang von Organisationsgrenzen verteilt, entstehen Redundanz, Fehler und schlechte Echtzeit-Sicht auf den Systemzustand.
**Urteil:** uebertragbar — dasselbe Datensilo-Muster wie bei Software-Teams.
**Entsprechung:** GEFUNDEN — ADR-013 (Bestaetigung).

### 23. `/nasa-llis/3457` — COTS Change Processing
**Behauptung:** Aenderungsmanagement-Prozesse, die fuer seltene Eigenentwicklungs-Aenderungen gebaut wurden, versagen bei schnelllebigen Drittkomponenten mit haeufigen Patches; beide brauchen unterschiedliche Prozesse.
**Urteil:** uebertragbar — direkter Treffer auf Abhaengigkeits-/Patch-Management vs. Eigencode-Governance.
**Entsprechung:** keine gefunden.

### 24. `/nasa-llis/3763` — Certifying Calibration on Test Components
**Behauptung:** Dass ein System als Ganzes validiert wurde, heisst nicht, dass jede Einzelkomponente noch innerhalb ihrer Kalibrierung/Spezifikation ist — das muss getrennt nachverfolgt werden.
**Urteil:** uebertragbar — Systemtest bestanden heisst nicht, jede Konfigurations-/Abhaengigkeitskomponente ist noch aktuell.
**Entsprechung:** GEFUNDEN — Lesson `L-c1cdb9` (fahrtenbuch/openhood): ein Compliance-Test pruefte "gepflegte Haelfte" (Bluetooth-Beschreibung vorhanden), waehrend die tatsaechlich benoetigte Podfile-Freigabe fehlte — "geprueft wurde ausgerechnet die gepflegte Haelfte". Dieselbe Struktur: Gesamtvalidierung deckt Einzelteil-Drift nicht auf. Bestaetigung, sehr gute Passung.

### 25. `/nasa-llis/1976` — Creation of a National Aeronautics Operational Monitoring System Research Data Center
**Behauptung:** Ein Vertraulichkeitsversprechen ist nur so stark wie der rechtliche/technische Mechanismus dahinter; sind die spezifischen Bedingungen (wer erhebt die Daten, welcher Wortlaut wird verlesen) nicht erfuellt, greift der Schutz stillschweigend nicht — trotz gutem Glauben beim Versprechen.
**Urteil:** uebertragbar — starke Analogie zu Datenschutz-/Anonymisierungs-Zusagen in Software, deren Wortlaut die tatsaechliche Rechtslage nicht trifft.
**Entsprechung:** keine gefunden (Suche nach Vertraulichkeit/Anonymisierung/rechtliche Bedingung ergab keinen Treffer im Bestand). Bemerkenswerte unbesetzte Stelle angesichts der BSI/Datenschutz-Direktiven dieses Systems.

### 26. `/nasa-llis/2044` — MRO Articulation Keep-Out Zone Anomaly
**Behauptung:** Eine Anforderung, die nur auf hoher Abstraktionsebene formuliert ist (Bauteil X darf Zone Y nicht beruehren), ohne einen konkreten Mechanismus, der das in allen geometrischen Faellen erzwingt, besteht die Verifikation und versagt trotzdem in einem nicht bedachten Grenzfall.
**Urteil:** uebertragbar — Kernstueck jeder ernsthaften Grenzwert-/Edge-Case-Disziplin.
**Entsprechung:** GEFUNDEN — CLAUDE.md-eigene Direktive "'Es funktioniert' braucht einen Beleg" (`c7edde55`), Punkt 1: "Grenzwert geprueft, nicht nur ein bequemer Wert? Jede Schwelle braucht Test bei Schwelle-1, Schwelle, Schwelle+1." Bestaetigung — exakt dieselbe Lehre, bereits als eigene Arbeitsregel verankert.

### 27. `/nasa-llis/4016` — Coating System for Launch Support Facilities **[GEGENPROBE]**
**Behauptung:** Eine anfangs teurere, haltbarere Beschichtung reduziert die Haeufigkeit (und damit Kosten) wiederkehrender Wartung.
**Urteil:** GEBUNDEN (wegen Trivialitaet) — "eine robustere Loesung senkt spaetere Wartungskosten" ist zwar technisch auch auf Software (Technische-Schulden-Abbau) uebertragbar, aber so allgemein, dass daraus keine pruefbare, nicht-triviale Aussage wird. Wo eine Uebertragung nur eine Binsenweisheit reproduziert, zaehlt sie hier nicht als Treffer.
**Entsprechung:** entfaellt.

### 28. `/nasa-llis/3157` — Environmental Control System (ECS) Purge Support Requirements
**Behauptung:** Anforderungen, die nur den geplanten Normalfall abdecken und nicht, was bei ungeplanten Ausfaellen/Abweichungen passiert, hinterlassen eine Luecke, die erst im Ausnahmefall auffaellt.
**Urteil:** uebertragbar — Fehlerbehandlung nur fuer den Happy Path spezifiziert ist ein Standardfehler.
**Entsprechung:** GEFUNDEN (mittlere Passung) — Lesson `L-8d7350` (wohlair): `overallAmpelConfigured` beruecksichtigte im Basis-Modus (ohne IR-Daten) nur eine Teilampel; Nutzer im Basis-Modus bekamen "gruen", ohne dass die eigentliche Pruefung stattfand — derselbe Fehler: der Nicht-Normalfall (kein IR) war beim Requirements-Entwurf nicht mitgedacht. Bestaetigung.

### 29. `/nasa-llis/2157` — Network/Radio Frequency (RF) Compatibility Testing
**Behauptung:** Auch ein Verfahren, das schon oft erfolgreich gelaufen ist, muss weiter exakt befolgt werden; Nachlaessigkeit durch Routine fuehrt zu Konfigurationsfehlern und Testversagen.
**Urteil:** uebertragbar — Runbook-/Deploy-Prozedur-Nachlaessigkeit nach vielen erfolgreichen Wiederholungen ist ein bekanntes Betriebsmuster.
**Entsprechung:** keine gefunden (die naechstliegenden Treffer betrafen andere Fehlerklassen — veraltete UI-Werte, nicht Prozedur-Nachlaessigkeit).

### 30. `/nasa-llis/1843` — Science Data Downlink Process Must Address Constraints Stemming from Fixed DSN Assets
**Behauptung:** Anforderungen, die zwei Disziplinen (Wissenschaft und Technik) gemeinsam an eine geteilte, feste, ueberbuchte Ressource stellen, basieren oft auf zu optimistischen Annahmen; der Entwurf muss die reale Grenze der Ressource einplanen, nicht die wuenschenswerte.
**Urteil:** uebertragbar — SLA/Anforderungen gegen eine gemeinsam genutzte, ratenlimitierte Ressource (z.B. externe API, gemeinsame DB) folgen demselben Muster.
**Entsprechung:** keine gefunden.

### 31. `/nasa-llis/1996` — MSL Heatshield Handling Incident
**Behauptung:** Die erste Bewegung/Anwendung eines wichtigen Guts sollte vorab als Probelauf validiert werden, mit einer verantwortlichen Fachperson anwesend, statt es beim ersten Mal live zu tun.
**Urteil:** uebertragbar — Analogie zu Trockenlauf/Staging vor erster Produktivmigration.
**Entsprechung:** GEFUNDEN (strukturell, anderes Gebiet) — `/brainlehr/probelauf-2026-08-06-was-ein-fremder`: erster Lauf von brainlehr in fremder Umgebung deckte auf, dass zwei von sechs Eigenschaften "nicht mitreisen" — derselbe Kerngedanke (erster Realeinsatz unter unbekannten Bedingungen deckt Annahmen auf, die im gewohnten Umfeld unsichtbar blieben). Bestaetigung, keine neue Erkenntnis, aber gute Strukturanalogie.

### 32. `/nasa-llis/1858` — Maintain a Materials Properties Database that Covers Environmental Extremes
**Behauptung:** Herstellerdokumentation deckt oft nicht den tatsaechlichen Betriebsbereich ab; ueber Jahre angesammeltes institutionelles Wissen muss aktiv zugaenglich gemacht werden, sonst bleibt es implizit und geht verloren.
**Urteil:** uebertragbar — Kernaussage dieses Wissenssystems selbst.
**Entsprechung:** GEFUNDEN — ADR-013 / das gesamte `knowledge.db`-Projekt ist die gebaute Antwort auf genau diese Lehre. Staerkste Bestaetigung der Stichprobe, aber keine neue Erkenntnis.

### 33. `/nasa-llis/4059` — Flexhose Quick Disconnect (QD) Design Improvement for Easier Use **[GEGENPROBE]**
**Behauptung:** Ein Drehgelenk zwischen Schlauch und Kupplung reduziert Fehlversuche beim Verbinden.
**Urteil:** GEBUNDEN — die Uebertragung ("ein Freiheitsgrad an der Schnittstelle reduziert Reibung") waere erzwungen: Kern der Lehre ist mechanische Ergonomie (Drehmoment, Gewicht, Torsion), kein allgemeines Entkopplungsprinzip, das sich ohne Verlust auf Softwareschnittstellen uebertragen liesse.
**Entsprechung:** entfaellt.

### 34. `/nasa-llis/6796` — TRaiNED Deployment Failure Was Traced to Design Flaws and Process Escapes
**Behauptung:** Guenstige, risikoreiche Projekte, die zur Ausbildung juengerer Ingenieure dienen, brauchen zusaetzliche Sorgfalt bei Materialverfolgung, eindeutiger Bauteilkennzeichnung und Wissenserhalt bei Personalwechsel — gerade weil dort am ehesten gespart wird.
**Urteil:** uebertragbar — Bus-Factor/Onboarding-Risiko bei knapp besetzten Teams ist ein Softwarethema.
**Entsprechung:** keine gefunden (naechstliegender Treffer, `L-e107ee` Projektgrenze nicht durchgesetzt, behandelt ein anderes Problem).

### 35. `/nasa-llis/6216` — MSL Mobility Assembly Lift Mishap
**Behauptung:** Ein quantitatives Signal (ungewoehnlicher Sensorwert), das auf ein Problem hindeutete, war nicht vorab dokumentiert/kommuniziert und wurde waehrend der Operation nicht ueberwacht; das spezialisierte Wissen, es zu erkennen, war verfallen, nachdem die Ausbildung dazu eingestellt wurde.
**Urteil:** uebertragbar — Monitoring-Signal ohne dokumentierten Erwartungswert plus verfallendes Spezialwissen ist ein Alerting-/Wissenserhalt-Muster.
**Entsprechung:** keine gefunden (naechstliegend war `L-3faad7` Konfidenzverfall, behandelt aber Vertrauens-, nicht Wissensverfall bei Personalwechsel).

### 36. `/nasa-llis/3716` — Testbed Limitations May Impact End-to-End Flight System Testing
**Behauptung:** Eine Testumgebung, die fuer die urspruengliche Entwicklung ausreichte, wird stillschweigend unzureichend, sobald eine spaete Aenderung ein Szenario beruehrt, das die Testumgebung nie abbilden konnte — die Aenderung geht ungetestet durch, weil niemand die Testabdeckung gegen die Aenderung neu geprueft hat.
**Urteil:** uebertragbar — Kernaussage der "Test-as-you-fly"-Regel, direkt uebersetzbar.
**Entsprechung:** GEFUNDEN, staerkster Treffer der ganzen Stichprobe — `/methodik/direktiven/walkthrough-doktrin-alle-coding-aufgaben-ohne-aufruf` (E2E-Journey als echter Test statt Behauptung) UND Lesson `L-46dfd3` (Rot-Probe fuer Fahrtenbuch-Fix: "connect()-basierter Reconnect kann den historischen Bug strukturell nicht rot zeigen" — der Test konnte das Szenario, in dem der Fehler lebte, gar nicht abbilden). Bestaetigung, praktisch wortgleiche Lehre, nur im Raumfahrtvokabular.

### 37. `/nasa-llis/3340` — Fair Wear and Tear Specifications, Standard Repair Procedures and Cosmetic Condition Reports
**Behauptung:** Ohne vorab festgelegte Regeln, was als akzeptabler Mangel gilt und welche Reparaturschritte zulaessig sind, wird jeder Fall einzeln beurteilt, was die Bearbeitung verlangsamt.
**Urteil:** uebertragbar — Analogie zu fehlenden Schweregrad-Schwellen bei Code-Review/Datenqualitaets-Triage.
**Entsprechung:** keine gefunden.

### 38. `/nasa-llis/2716` — Thermal Control System (TCS) Blanket Interference with Xo378 Bulkhead Vent Ports
**Behauptung:** Ist die Schnittstelle zwischen zwei Bauteilen nur unklar dokumentiert, kann eine fuer sich genommen korrekte lokale Aenderung ein benachbartes System stillschweigend beeintraechtigen; jeder Beitragende muss verstehen, wie sein Teil das Gesamtsystem beeinflusst.
**Urteil:** uebertragbar — klassisches API-/Vertragsgrenzen-Problem.
**Entsprechung:** GEFUNDEN — Lesson `L-f7912d`: zwei Auswerter derselben Spalte (`normkraft.py::in_kraft` und `knowledge_mcp_server.py::_geltung_status`) implementierten das Grenzverhalten von `gilt_bis` unabhaengig voneinander — einer exklusiv, einer inklusiv; beide erreichbar, am Stichtag widersprachen sie sich stillschweigend. Gleiche Struktur: unklare/implizite Schnittstellenbedeutung, zwei fuer sich korrekte Implementierungen kollidieren unbemerkt. Bestaetigung, gute Passung.

### 39. `/nasa-llis/6416` — SpaceWire Cable Fabrication and Installation
**Behauptung:** Ein fehlender Schritt in einer schriftlichen Anleitung, der nur durch stillschweigendes Wissen kompensiert wurde, bleibt unsichtbar, bis ihn jemand ohne dieses Wissen ausfuehrt; Zeichnungen/Spezifikationen brauchen genug Detail, dass kein "das weiss doch jeder"-Schritt uebrig bleibt.
**Urteil:** uebertragbar — direkter Treffer auf Dokumentations-/Onboarding-Luecken.
**Entsprechung:** GEFUNDEN (systemisch, kein Einzelknoten) — die Existenz und Begruendung der CLAUDE.md-Direktive "Wissen festhalten & abrufen" (Reflex-Erfassung nicht-offensichtlicher Befunde) ist die gebaute Antwort auf genau dieses Problem; konkrete Einzelfaelle wie `L-db33de` (Daemon haelt alten Codestand ohne Neustart-Hinweis) zeigen dieselbe Fehlerklasse. Bestaetigung.

### 40. `/nasa-llis/1831` — Human Engineering should be considered a Systems Engineering and Integration function
**Behauptung:** Ein Querschnittsthema (Bedienbarkeit fuer die Menschen, die das System betreiben/warten), das keinen expliziten eigenen Abschnitt/Verantwortlichen im Entwurfsreview hat, wird leise uebergangen, obwohl alle es grundsaetzlich fuer wichtig halten — es muss zum expliziten Pflichtteil jedes Systementwurfs gemacht werden, nicht zur stillschweigenden Annahme.
**Urteil:** uebertragbar — praktisch wortgleich mit dem Umgang dieses Systems mit Barrierefreiheit.
**Entsprechung:** GEFUNDEN, zweitstaerkster Treffer der Stichprobe — `/methodik/direktiven/wcag-2-2-aa-verbindlich-bei-jeder-oberflaeche-systemweit`: WCAG 2.2 AA als verbindlicher, nicht optionaler Bestandteil jeder Oberflaeche, mit derselben Grundeinsicht ("der Regelfall ist gar kein Konflikt... erst wenn eine Massnahme nachweislich Platz/Tempo/Uebersicht kostet, greift die Direktive"). Bestaetigung.

---

## Ausbeute (die eigentliche Frage)

Von 40 gezogenen Knoten:

- **1 Knoten unbrauchbar** (Nr. 20, `4496`, Lesson-Text nur "See attachment") — aus der Ausbeuterechnung entfernt. Verbleiben **39 beurteilte Knoten**.
- **Uebertragbare Behauptung: 33 von 39** (85%). Als GEBUNDEN eingestuft: 6 (Nr. 3, 6, 19, 21, 27, 33 — alle als Gegenprobe markiert und einzeln begruendet).
- **Von den 33 uebertragbaren: 13 finden eine Entsprechung** im uebrigen Bestand (382 Nicht-NASA-Knoten + 689 Lehren) — **39% Trefferquote unter den uebertragbaren**.
- **Von diesen 13 Treffern: 0 sind NEU.** Alle 13 bestaetigen eine Erkenntnis, die dieses System bereits selbst — meist durch eigenen Schaden — gefunden und als Direktive, ADR oder Lesson festgehalten hat (ADR-013 Knowledge Graph, Walkthrough-Doktrin, Grenzwert-Regel, WCAG-Direktive, Wissen-festhalten-Direktive, Enum-Exhaustiveness-Regel, mehrere konkrete Lessons wie L-c1cdb9, L-f7912d, L-8d7350, L-46dfd3, L-c64f3b).
- **20 der 33 uebertragbaren Behauptungen finden KEINE Entsprechung** — unbesetzte Stellen, keine erzwungenen Verbindungen versucht (u.a. Nr. 1, 2, 4, 5, 9, 10, 11, 13, 15, 17, 23, 25, 29, 30, 34, 35, 37).

## Fuenf Gegenproben (nicht uebertragbar, mit Grund)

1. `/nasa-llis/5996` — physische Absturzsicherung, kein Softwareaequivalent.
2. `/nasa-llis/5479` — Materialermuedung an Metall, per Inspektion unsichtbar; Uebertragung auf "technische Schulden" waere erzwungen.
3. `/nasa-llis/6976` — an US-Beschaffungsburokratie (DCMA/PCARSS) gebundene Prozessdetails; Rest zu trivial fuer eine eigenstaendige Aussage.
4. `/nasa-llis/3220` — konkretes mechanisches Bauteil (Dichtungsring), kein abstrahierbares Prinzip.
5. `/nasa-llis/4059` — mechanische Ergonomie eines Drehgelenks; "Entkopplung reduziert Reibung" waere eine erzwungene Verallgemeinerung.

## Empfehlung

**Lohnt sich nur fuer bestimmte Unterbereiche, nicht als Vollzug ueber alle 1638 Knoten.**

Begruendung: Die Uebertragbarkeitsrate selbst ist hoch (85%) — die These des Betreibers,
dass die NASA-Lehren strukturell und nicht vokabelgebunden sind, ist bestaetigt. Aber
die NUTZBARKEIT fuer diesen Bestand ist begrenzt, weil dieses System dieselben
Prinzipien bereits ueberwiegend selbst durch eigene Fehlerfaelle gefunden hat — die
Deckungsflaeche ist die, in der ein sehr disziplinierter Software-Wissensspeicher
ohnehin schon sitzt (Single Source of Truth, Grenzwertpruefung, Mistake-Proofing,
Testabdeckung gegen den echten Fehlerpfad, Querschnittsthemen als Pflichtteil).

Was sich lohnen wuerde: die Unterbereiche mit der hoechsten TREFFERQUOTE in dieser
Stichprobe gezielt weiterzuziehen, nicht blind der Reihe nach:
- **Systems Engineering / Requirements-Verifikation** (Nr. 6, 26, 36 — 3 von 3 Treffer)
- **Software Engineering / Configuration Management** (Nr. 7, 8, 22 — Datenbank-/Single-Source-Cluster, durchgehend Treffer, aber durchgehend Bestaetigung ohne Neuwert)
- **Human Factors als Systems-Engineering-Funktion** (Nr. 40 — starker Treffer, wahrscheinlich mehrere weitere in derselben Kategorie)

Was sich NICHT lohnt: rein hardwarenahe Kategorien (Facilities, Ground Equipment,
Materialbehandlung/Dynatube/Flexhose-Cluster) — dort war die Gegenprobe-Quote hoch
und der Rest, wo doch etwas uebertragbar war, fand keine Entsprechung (Kapazitaets-/
Sparing-Themen, Nr. 5, blieb unbesetzt).

Ein zweiter Fund, der eigens gemeldet werden sollte: **Nr. 25 (NAOMS, Vertraulichkeits-
zusage ohne erfuellte Rechtsbedingung)** ist die einzige uebertragbare Behauptung mit
klarem Bezug zu Datenschutz/Compliance-Zusagen, und sie findet KEINE Entsprechung im
Bestand — trotz BSI-Compliance-Direktive. Das ist die interessanteste unbesetzte Stelle
der Stichprobe, weil sie nicht durch fehlende Suchbegriffe erklaerbar ist, sondern durch
eine echte Luecke: es existiert bislang keine Lehre darueber, dass ein Versprechen
("wir anonymisieren das") nur so stark ist wie sein tatsaechlicher rechtlich-technischer
Unterbau.

## Zwei ueberzeugendste Uebertragungen (Wortlaut)

**Nr. 36** (`/nasa-llis/3716`, Testbed Limitations): *"Eine Testumgebung, die fuer die
urspruengliche Entwicklung ausreichte, wird stillschweigend unzureichend, sobald eine
spaete Aenderung ein Szenario beruehrt, das die Testumgebung nie abbilden konnte — die
Aenderung geht ungetestet durch, weil niemand die Testabdeckung gegen die Aenderung neu
geprueft hat."* — praktisch wortgleich mit der eigenen Walkthrough-Doktrin und der
Rot-Probe-Lesson L-46dfd3.

**Nr. 40** (`/nasa-llis/1831`, Human Engineering): *"Ein Querschnittsthema, das keinen
expliziten eigenen Abschnitt/Verantwortlichen im Entwurfsreview hat, wird leise
uebergangen, obwohl alle es grundsaetzlich fuer wichtig halten — es muss zum expliziten
Pflichtteil jedes Systementwurfs gemacht werden, nicht zur stillschweigenden Annahme."*
— trifft die eigene WCAG-2.2-AA-Direktive fast wortgleich, nur 22 Jahre und ein
Vokabular entfernt (2004, Space Shuttle Design Review → 2026, Oberflaechen-Direktive).
