# Research-Katalog: Was soll Brainlehr sein?

Angelegt 2026-08-17. Dieser Katalog ist die eine kanonische Arbeitsgrundlage
für die Zielbild-Research und den daraus abgeleiteten Betreiber-Wizard. Seine
`RQ-*`-IDs sind Researchfragen, keine zweite Lastenheft-Skala. Verbindliche
Produktanforderungen entstehen erst durch Überführung in den künftigen
Root-Lastenkatalog; bis dahin entscheidet dieses Dokument nichts heimlich.

## Quellen- und Statusregeln

- Interne Rangfolge: wörtliche Betreiberentscheidung und geltende ADR vor Plan,
  Plan vor Ist-Code/Test, Brainlehr-Recall nur als Suchhinweis. Jeder Recall-Fund
  wird gegen Repo- oder Betreiber-Primärbeleg geprüft.
- Externe technische Aussagen: Primärquellen aus Paper, Standard oder offizieller
  Produktdokumentation; direkte URL und Abrufdatum. Keine Suchsnippet-Evidenz.
- Sicherheit: zuerst lokale BSI-Anwenderkataloge mit Datei und Control-ID;
  ergänzend offizielle EU-/NIST-/OWASP-/CISA-Quellen. Controls sind Baseline oder
  Guidance, keine Compliancebehauptung.
- Einstufung je Aussage: `bindend`, `vorgeschlagen`, `überholt`,
  `widersprüchlich` oder `offen`. Ein Konflikt bleibt sichtbar.

## Kanonische Researchfragen

| ID | Frage / Liefergegenstand | Gate | Status |
|---|---|---|---|
| RQ-001 | Welche Betreiberentscheidungen, ADRs, Pläne, Codepfade, Tests und verifizierten Brainlehr-Knoten bilden die interne Produktgenealogie? | Quellenmatrix mit Status und direktem Repo-Beleg | PASS |
| RQ-002 | Was ist intern bereits bindend entschieden, was nur vorgeschlagen, überholt, widersprüchlich oder offen? | Jede Kernaussage trägt genau eine Einstufung | PASS |
| RQ-003 | Welcher Stand der Technik 2025/2026 gilt für episodisches, semantisches und prozedurales agentisches Langzeitgedächtnis? | Primärquellen mit URL/Abrufdatum | PASS |
| RQ-004 | Welche Mechanismen sind Stand der Technik für Provenance, Confidence, Decay und zeitliche Geltung? | Primärquellen; Abgleich mit Ist-Code/Test | PASS |
| RQ-005 | Wie werden Retrieval, Antwortnützlichkeit, Konflikte und Policy-Governance belastbar evaluiert? | Messbare Evals und Testgates statt Featureliste | PASS |
| RQ-006 | Welche Anforderungen folgen aus Tamper Evidence, Multi-Agent-/Shared Memory und Portabilität/Föderation? | Primärquellen; Risiken und Nicht-Ziele | PASS |
| RQ-007 | Welche Unternehmensbaseline folgt für Identitätsauthority, SSO/SCIM und Lebenszyklus von Konten? | BSI-Control-IDs plus offizielle Standards | PASS |
| RQ-008 | Welche Baseline folgt für RBAC/ABAC/objektbezogene Rechte und Mandantentrennung? | BSI-Control-IDs; testbare Autorisierungsgrenzen | PASS |
| RQ-009 | Welche Baseline folgt für Verschlüsselung, Schlüsselverwaltung und Datenresidenz? | BSI-Control-IDs; Betriebsoptionen ohne Compliancebehauptung | PASS |
| RQ-010 | Welche Baseline folgt für Audit/SIEM, Aufbewahrung, Löschung und Legal Hold? | BSI-Control-IDs; prüfbare Ereignis- und Lebenszyklusgates | PASS |
| RQ-011 | Welche Baseline folgt für Backup/Restore/BCM, DLP/Privacy, Genehmigungswege und Observability/SLO? | BSI-Control-IDs; Restore- und Betriebs-Gates | PASS |
| RQ-012 | Wo endet Brainlehr gegenüber Atelier, Openlehr/Fachdomänen, DMS, Suchmaschine, Vektordatenbank, Agent-Orchestrator und IAM? | Boundary-Matrix; offene Optionen nicht vorentschieden | PASS |
| RQ-013 | Welche Fähigkeiten sind heute vorhanden, teilweise vorhanden, fehlen oder bewusst Nicht-Ziel? | Gap-Matrix mit Evidenz und Testgate je Zeile | PASS |
| RQ-014 | Welche mindestens drei konkurrierenden Zielbilder sind realistisch? | Chancen, Risiken, relative Kosten und falsifizierbare Annahmen je Zielbild | PASS |
| RQ-015 | Welches Zielbild ist aufgrund der Evidenz empfohlen, und wodurch wäre die Empfehlung widerlegt? | Empfehlung plus explizite Falsifikationsbedingungen | PASS |
| RQ-016 | Welche Fragen muss der Betreiber wirklich entscheiden, und welche sind bereits belegt entschieden? | Entscheidungsmenge ohne erneut geöffnete Scheinoffenheit | PASS |
| RQ-017 | Ist jede Frage und Empfehlung des Wizards aus Research oder bindender Primärquelle ableitbar? | Stabile Wizard-Frage-ID, Quellen und keine Vorauswahl | PASS |
| RQ-018 | Besteht der aktualisierte Wizard technisch und als menschlich lesbarer Dialog bei 736 px und 360 px? | JS-/ID-Prüfung, Tastaturtest, visuelle Prüfung, Zusammenfassungs-Prompt | PASS |

## Ergebnisstruktur

Die abgeschlossene Research ergänzt unterhalb dieses Katalogs: interne
Genealogie, externe Evidenz, Unternehmensbaseline, Produktgrenze, Gap-Matrix,
drei Zielbilder, Empfehlung, falsifizierbare Annahmen und die echte
Betreiber-Entscheidungsmenge. Danach wird nur diese Entscheidungsmenge in den
Wizard übernommen.

## RQ-003 bis RQ-006 — Stand der Technik für agentisches Langzeitgedächtnis

Stand der Webprüfung: 2026-08-17. Die Papers sind Primärquellen ihrer jeweiligen
Beiträge; mehrere sind Preprints. Daraus folgt Forschungs- und Prüfevidenz, keine
allgemeine Markt- oder Compliancebehauptung.

| Thema | Primärbeleg | Folgerung für ein prüfbares Brainlehr-Zielbild |
|---|---|---|
| Gedächtnisarten | [Huang et al., 2026](https://arxiv.org/abs/2602.06052) ordnen Agent Memory nach Substrat, Mechanismus (sensorisch, Arbeits-, episodisch, semantisch, prozedural) und Subjekt; [Pink et al., 2025](https://arxiv.org/abs/2502.06975) behandeln episodisches Gedächtnis als situations- und zeitgebundenes Lernen. | Episoden, abstrahierte Claims und Prozeduren brauchen getrennte Schreib-, Abruf-, Korrektur- und Löschtests; ein einziges Freitext-Knotenformat beweist diese Fähigkeiten nicht. |
| Provenienz | [W3C PROV Primer](https://www.w3.org/TR/prov-primer/) modelliert Entity, Activity, Agent und Ableitung. | Jeder verwendete Claim muss zu Quelle/Erzeuger, Ableitung und Zeitpunkt zurückführbar sein. Konfidenz ist eine Bewertung, kein Wahrheitsbit. |
| Veränderung und Vergessen | [Memora/FAMA](https://arxiv.org/abs/2604.20006) misst und bestraft die Nutzung obsoleter oder invalidierter Erinnerung. | `gültig`, `abgelaufen`, `ersetzt`, `widersprüchlich`, `ungeprüft` und `widerrufen` sind explizite Zustände; Decay darf Inhalte nicht still löschen. |
| Retrieval-Evaluation | [MemoryAgentBench](https://arxiv.org/abs/2507.05257) trennt Retrieval, Lernen in der Interaktion, langfristiges Verständnis und selektives Vergessen; [Mem2ActBench](https://arxiv.org/abs/2601.19935) prüft die tatsächliche Nutzung von Erinnerung in Tool-Aktionen. | Gates brauchen zeitabhängige, widersprüchliche und abstain-fähige Fälle sowie korrekte Toolwahl/-parameter; Recall@k allein reicht nicht. |
| Konflikte | [StateFuse](https://arxiv.org/abs/2607.05844) untersucht deterministische, konfliktbewahrende Replikation; [Multi-Agent Memory](https://arxiv.org/abs/2603.10062) beschreibt Konsistenz und Zugriffskontrolle als offene Architekturprobleme. | Replikat-Merge, normative Geltungsentscheidung und Berechtigung sind drei getrennte Mechanismen. `latest write wins` ist kein ausreichendes Sollbild. |
| Manipulationserkennung | Der [IETF-VOLT-Entwurf](https://www.ietf.org/archive/id/draft-cowles-volt-00.html) beschreibt Ereignis-Ledger, Hashverkettung, Evidence Bundles und optionale Attestierung. | Korrekturen werden als neue Ereignisse sichtbar; ein Gate unterscheidet „nachträglich unverändert“ von „inhaltlich wahr“. Sensible Rohdaten gehören nicht in öffentliche Nachweise. |
| Portabilität und Teilen | Die [MCP-Spezifikation 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18/index) trennt serverkontrollierte Resources, modellgesteuerte Tools und nutzergesteuerte Prompts. [Collaborative Memory](https://arxiv.org/abs/2505.18279) untersucht dynamische Rechte für Nutzer, Agenten und geteilte Ressourcen. | Der Kern bleibt modell-/clientneutral. Private, geteilte und organisationsweite Sichten brauchen explizite Grenzen; MCP ist Schnittstelle, nicht Berechtigungsmodell. |

Minimaler Evaluationssatz daraus: (1) Fakt mit Quellenbeleg wiederfinden,
(2) Claim ersetzen/ablaufen/widerrufen, (3) zwei gleichrangige Widersprüche als
Konflikt oder Abstention zeigen, (4) Antwort auf konkrete Claim-/Quellen-IDs
zurückführen, (5) Logmanipulation erkennen, (6) parallele Agentenschreibungen
konfliktbewahrend zusammenführen, (7) Export/Import ohne Verlust von IDs,
Zeitintervallen, Provenienz und Rechten, (8) Erinnerung korrekt in einer
Tool-Aktion verwenden.

## RQ-007 bis RQ-011 — Unternehmens- und Sicherheitsbaseline

Lokale Baseline: BSI-Bibliothek Commit
`12abb438fcdb4f4b63fb3e751e89d7c526e647b5`, Datei
`/Volumes/daten/bibliotheken/Stand-der-Technik-Bibliothek/Anwenderkataloge/Grundschutz++/Grundschutz++-catalog.json`.
Die folgenden Punkte sind **Guidance für Architektur- und Abnahmekriterien**.
Sie bescheinigen weder BSI-Grundschutz noch DSGVO-Konformität.

| Bereich | BSI-Control-IDs / ergänzende Primärquelle | Baseline und mögliches Testgate | Produktentscheidung? |
|---|---|---|---|
| Identitätsauthority, SSO, SCIM | `BER.2.1` eindeutige Person-/Systemidentität, `BER.3.6` zentrales Kontenmanagement, `BER.3.12` zentraler IdP, `BER.2.5` Deaktivierung bei Weggang; [NIST SP 800-63-4](https://csrc.nist.gov/pubs/sp/800/63/4/final), [SP 800-63C-4](https://csrc.nist.gov/pubs/sp/800/63/C/4/final), [SCIM RFC 7644](https://www.rfc-editor.org/info/rfc7644/) | Organisation ist Authority; lokale Notfall-/Offline-Identität ist eng begrenzte Ausnahme. Provisioning-, Deprovisioning- und Federation-Test mit nachvollziehbarer Subjektbindung. SCIM definiert keinen Mandantenschutz — dieser wird separat getestet. | SSO/SCIM-Zeitpunkt und Offline-Ausnahme sind offen; selbstbehauptete Produktionsidentität ist kein tragfähiges Unternehmensziel. |
| Rollen, Attribute, Objekt-/Zweckgrenze | `BER.4.1` geringste Berechtigung, `BER.4.2` Autorisierung, `BER.4.4` Rechteprüfung, `KONF.6.5`/`KONF.6.13` dynamische Zugriffskontrolle, `KONF.6.6` getrennte Datenhaltung | RBAC kann Grundrollen liefern; objekt-, mandanten- und zweckbezogene Einschränkungen verengen sie. Negativmatrix für Rolle × Zweck × Objekt × Mandant, Default Deny. | Reines RBAC reicht für den belegten Zweckprojektionsanspruch nicht; konkrete Policy-Sprache bleibt offen. |
| Mandantentrennung | `KONF.6.6` getrennte Datenhaltung, `ARCH.2.3` Mikrosegmentierung; RFC 7644 Abschnitt 6 warnt, dass SCIM Multi-Tenancy nicht selbst definiert | Jede ID, Suche, Relation, Export-, Backup- und Adminoperation trägt/prüft Tenant-Kontext; Cross-Tenant-Negativtests auf jeder Datennaht. | Logische versus physische Trennung nach Schutzbedarf offen. |
| Verschlüsselung und Schlüssel | `ASST.4.2` Vertraulichkeit/Integrität beim Transport, `KONF.10.2` Kryptografie in Anwendungen, `KONF.11.8` at rest, `BER.6.1` etablierte Schlüsselerzeugung, `BER.6.9` Zweckbindung, `BER.6.10` abgelaufene Schlüssel; [OWASP ASVS 5.0](https://owasp.org/www-project-application-security-verification-standard/) | TLS an Remote-Grenzen; Schutz ruhender sensibler Daten; Schlüsselrotation/-widerruf und Wiederherstellung werden getestet. Schlüssel nicht im Gedächtnis oder Auditinhalt speichern. | BYOK/HYOK, HSM und Feld- versus Datenträgerverschlüsselung sind Schutzbedarfsentscheidungen. |
| Audit und SIEM | `DET.3.1` sicherheitsrelevante Ereignisse, `DET.3.5` revisionssichere Änderungen, `DET.3.6` Unbestreitbarkeit, `DET.4.1` Überwachung der Protokollierung, `DET.2.2` SOC; [NIST SP 800-53 Rev. 5](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final) | Strukturierte, minimierte Ereignisse für Lesen/Schreiben/Entscheiden/Export/Admin; Manipulations- und SIEM-Exporttest. Audit beweist Integrität, nicht Wahrheit. | Ereigniskatalog, SIEM-Format und Unbestreitbarkeitsniveau offen. |
| Aufbewahrung, Löschung, Legal Hold | `ASST.7.2` Fristen, `ASST.7.3` geregeltes Löschen, `SENS.5.5` Löschfristen, `BES.6.5` aufzubewahrende Aufzeichnungen; [DSGVO Art. 5, 17, 20, 32, 44](https://eur-lex.europa.eu/eli/reg/2016/679/oj/) | Policy pro Datenklasse; Löschung umfasst Kopien/Indizes und hat ein evidentes Ergebnis. Hold ist eine begründete, autorisierte Sperre gegen Löschung, kein heimliches „für immer“. Export-/Lösch-/Hold-Konflikttests. | Fristen und Rechtsgrundlage kann das Produkt nicht pauschal festlegen; Betreiber/Organisation entscheiden. |
| Backup, Restore, BCM, offline | `NOT.4.7` versionierte Sicherung, `NOT.4.8` verschlüsselte Sicherung, `NOT.4.10` getrennte Aufbewahrung, `NOT.4.13` Datensouveränität, `NOT.4.14` Offline-Kopie, `NOT.4.15` Wiederherstellungsverfahren, `NOT.4.16` Sicherungstest, `NOT.4.17` Anwendungstest | Nicht „Backup vorhanden“, sondern frischer Restore in isolierter Umgebung mit RPO/RTO, Integrität, Rechten und Suchfähigkeit. | On-prem, Cloud und Offline sind Bereitstellungsprofile; unterstützte Kombinationen und SLO bleiben offen. |
| Datenresidenz und Bereitstellung | `ASST.3.10` autorisierte Datenlokationen, `BES.1.5`/`BES.1.6` autorisiertes/dokumentiertes Bereitstellungsmodell, `BES.2.2`/`BES.2.3` Rechtsraum und Datenlokation | Daten-, Index-, Backup-, Telemetrie- und Modellprovider-Flüsse werden je Profil kartiert und technisch gesperrt. | Regionen, Provider und erlaubte Auslandsübermittlung sind Betreiberentscheidungen. |
| DLP und Privacy | `ASST.3.7` Pseudonymisierung, `ASST.3.8` Anonymisierung, `DET.4.5` unerwünschte Datenabflüsse, `DEV.3.3` keine sensiblen Fehlerausgaben; DSGVO Art. 5/32 | Keine Secrets/PII in Recall-, Web-, Fehler- oder Telemetriepfaden; Export- und Connector-DLP-Negativtests. | Klassifikationsschema und Freigabeschwellen offen. |
| Genehmigung | `UMS.5.1`/`UMS.5.2` autorisierte/dokumentierte Ausnahmen, `TEST.4.1` Autorisierung kritischer Änderungen, `ASST.4.3` Veröffentlichungsfreigabe, `BER.4.2` Rechtefreigabe | Risikobasierte Freigaben für Regelrang, Veröffentlichung/Export, Connector, Modell-/Providerwechsel, Ausnahme und Löschsperre; Vier-Augen nur dort, wo Schutzbedarf es verlangt. | Welche Vorgänge genehmigungspflichtig sind, bleibt offen. |
| Observability und SLO | `DET.4.12`–`DET.4.17` Netz-/Host-/Anwendungs-/Kapazitätsüberwachung, `BES.5.2` messbare Dienstgüte | SLI für Verfügbarkeit, Recall-Nutzen, Fehlklassifikation, Latenz, Restore und Policy-Denials; Alarme ohne Inhaltsleck. | Zielwerte und Betriebsmodell sind offen. |

BSI verlangt hier nicht „eine Enterprise-Funktion pro Control“. Die kleinste
sinnvolle Produktantwort ist ein geschlossenes Policy-/Audit-/Testmodell, das
lokal zunächst einfach sein darf und später SSO, SCIM, SIEM oder HSM ankoppelt.

## RQ-001/RQ-002 — interne Genealogie und Bindungsstatus

| Aussage | Status | Primärbeleg / Einordnung |
|---|---|---|
| Brainlehr ist die tragende Wissens- und Aufsichtsschicht; Openlehr macht Menschen mit geprüftem Wissen und Werkzeug handlungsfähig. | **bindend** | `docs/adr/ADR-007-zwei-schichten-brainlehr-und-openlehr.md:1-27`, angenommen durch den Betreiber. Geräte-Apps sind zunächst keine Openlehr-Instanzen; ihre Lehren dürfen dennoch in Brainlehr wirken (`:57-76`). |
| Atelier ist die gemeinsame Werkbank; `open*` ist der Instanz-Namensraum. | **bindend** | `docs/adr/ADR-008-die-werkbank-heisst-atelier.md:1-27`, angenommen. |
| Im Atelier liegen gemeinsamer Rahmen und unabtretbare Sicherheits-/Modell-/Grundeinstellungen; Fachlogik liegt in der Domäne; Dokumentfenster und Wissensraum sind optional ladbare gemeinsame Bestandteile. | **bindend** | `docs/adr/ADR-014-was-ins-atelier-gehoert.md:1-68`, angenommen und durch Betreiber-Nachtrag verengt. |
| V1 des Ateliers ist nativ; eine Weboberfläche ist ein späterer Zeichner derselben plattformblinden Beschreibung. | **bindend** | `docs/adr/ADR-024-v1-ist-nativ-die-beschreibung-bleibt-plattformblind.md:47-80`, angenommen. Zeitpunkt der Weboberfläche bleibt dort ausdrücklich offen. |
| Der Vertrauensregler steuert Rückfragepflicht, niemals Belegpflicht; `handeln` ist Default, `raeumen` eine höhere Betreiberstufe. | **bindend, teilweise umgesetzt** | `docs/PLAN_VERTRAUENSREGLER_2026-08-16.md:1-17,30-90,121-154`; Datei/Lesefunktion und Protokollierung stehen, breite Wächterverdrahtung ist bewusst offen. |
| Zweck Z1–Z6 und Nicht-Ziele seien in ADR-026 entschieden. | **nicht als bindend verifizierbar** | Die aufgerufene Brainlehr-Notiz `c3eb7927` nennt ADR-026 selbst noch „vorgeschlagen“. Weder ADR-025 noch ADR-026 existiert in diesem Repo; `docs/STARTPROMPT_GRUNDARCHITEKTUR_2026-08-13.md:149-154` verweist nur auf die fehlende Datei und hält die Kernfrage weiter offen. Der Recall ist nützliche Genealogie, aber kein Ersatz für den Primärbeleg. |
| Ein einziger kanonischer Lastenkatalog mit stabilen IDs ist für komplexe Artefakte Pflicht. | **bindend für den Arbeitsprozess** | Brainlehr-Knoten `cd571222` stimmt mit der aktuell geltenden globalen `AGENTS.md`-Regel überein; dieser Research-Katalog setzt sie mit genau einer `RQ-*`-Skala um. Er ist noch kein Produktlastenheft. |
| README-Zweck: herstellerneutraler lokaler MCP/SQLite-Speicher, der ungefragt warnt, Lücken vorschlägt, unbelegte Einträge verhindert, Fremdtext als Daten markiert und seine Retrievalwirkung misst. | **implementierte öffentliche Produktbeschreibung, keine stabile API-Garantie** | `README.md:1-31` nennt ausdrücklich Version `0.1.0`, keine stabile Schnittstelle und kein Aufwärtskompatibilitätsversprechen. `README.md:38-49` begrenzt das Problem auf Herkunft, Geltung, Widerspruch und Wirkung. |
| Der aktuelle Stand sei eine eindeutige Aufgabenquelle. | **überholt/widersprüchlich** | `STAND.md:1-13` bezeichnet dieselbe Kanalgüte-Verdrahtung gleichzeitig als erledigt und später als offen. Die Datei ist eine Momentaufnahme, kein kanonischer Gesamt-Lastenkatalog. |

**Genealogischer Befund:** Der Kern ist hinreichend klar, um Grenzen und
Testziele zu formulieren. Nicht hinreichend belegt ist, dass die fehlende
ADR-026 je angenommen wurde. Deshalb werden ihre sinnvollen Z1–Z6-Inhalte als
Hypothesen/Research-Gates behandelt, nicht als heimlich bindende Norm.

## RQ-012 — Produktgrenze

| Gegenstand | Gehört zu Brainlehr? | Begründung / offene Grenze |
|---|---|---|
| Governierter Wissensbestand | **ja, Kern** | Claims/Knoten und Lehren, Herkunft, Normrang/Geltung, Freigabe/Widerruf, Retrieval, Audit und Selbstmessung. |
| Atelier | **nein, eigene Trägerschicht** | Gemeinsame Darstellung, Sicherheit und Einstellungen; bedient Brainlehr und Domänen, ist aber nicht der Speicher. |
| Openlehr/Fachdomänen | **nein, obere Fachschicht** | Fachlogik, Fachwissen und situationsbezogene Werkzeuge. Brainlehr kann ihre Herkunft/Geltung prüfen, besitzt ihre Fachoberfläche nicht. |
| Dokumentenablage/DMS | **kein Kern** | Ein Dokumentfenster kann Atelier-Bestandteil sein. Brainlehr speichert Verweis, Prüfsumme, Provenienz und abgeleitete Claims, nicht beliebige Dokumentkopien. |
| Suchmaschine | **nur der eigene Abruf** | FTS5 und optionale lokale Bedeutungsvektoren sind Retrievalkanäle des Wissensbestands; beliebige Datei-/Websuche bleibt außerhalb. |
| Vektordatenbank | **kein eigenes Produkt** | Heute lokale Embeddingtabellen und Cosinus-Fusion; die Vektortechnik ist austauschbarer Index, nicht Source of Truth. |
| Agent-Orchestrator | **nein, nur Integrationsvertrag** | MCP-Tools/Hooks liefern Speicheroperationen und Warnungen. `docs/adr/ADR-022-der-orchestrierungsweg-wird-gezeichnet.md:76-94` beschreibt Wege, keinen allgemeinen Task-Orchestrator. |
| IAM/IdP | **nein, aber harte Abhängigkeit** | Brainlehr erzwingt seine objekt-/zweck-/werkzeugbezogenen Policies gegen verifizierte Subjekte. SSO/SCIM/Verzeichnisdienst bleiben externe Authority/Connectoren; lokaler Ausweis ist ein Entwicklungs-/Offlinepfad. |

Die größte echte Produktentscheidung ist daher nicht „Speicher oder Plattform“:
bindend ist Brainlehr die Governance-Basis mehrerer Domänen. Offen ist, wie viel
**Unternehmens-Control-Plane** (Tenant-Policy, Connectoren, Export, Betriebs-SLO)
es selbst anbietet und wie viel es an IAM, SIEM, DMS und Orchestrator delegiert.

## RQ-013 — Gap-Matrix mit Testgates

| Fähigkeit | Heute | Evidenz | Nächstes belastbares Gate |
|---|---|---|---|
| MCP/SQLite, FTS5, optionale Embeddings | **vorhanden** | `README.md:22-31,70-82`; `knowledge_mcp_server.py:2416-2495` | Frischer MCP-E2E in FTS-only und hybrid; identische IDs/Geltung, dokumentierte Qualitätsdifferenz. |
| Herkunft und Ableitung | **vorhanden, nicht vollständig standardisiert** | DB-Trigger erzwingen `source`; `abgeleitet_von` und Quellhash existieren. Kein W3C-PROV-Exportvertrag. | Antwort→Claim→Quelle→Ableitung vollständig reproduzierbar; Export/Import erhält Kette. |
| Normrang, zeitliche Geltung, Widerspruch | **teilweise** | Normfelder und Geltungsfilter existieren; `START_HIER.md:25-40` verlangt konfliktbewahrende Darstellung. Allgemeine Fakten/Lehren haben kein einheitliches Claim-Statusmodell. | Ersetzen/ablaufen/widerrufen und gleichrangiger Konflikt; alte Version darf nicht als aktuelle Wahrheit erscheinen. |
| Episodisch/semantisch/prozedural | **teilweise/implizit** | Knoten und Lessons trennen zwei Gattungen, aber keine vollständige Memory-Funktionsmatrix. | Je Typ eigene Capture-, Abstraktions-, Recall-, Korrektur-, Lösch- und Freigabefälle. |
| Retrievalqualität und Abstention | **teilweise, aktuell rot** | Relevanz-/Kanaltests existieren; aktueller fokussierter Lauf: 91 PASS, `tests/test_vektorlage.py:62-71` rot wegen je einem Knoten und einer Lehre ohne Vektor. `MUST-LAGE-001` verhindert inzwischen falsche Negativbehauptung. | Null fehlende erwartete Vektoren; zeitliche/konfliktive/aktionsbezogene Memory-Evals; keine unkalibrierte Bestandsbehauptung. |
| Manipulationserkennung/Audit | **teilweise** | Hashkette/Merkle-/Ankerpfade und Auditlog existieren; ein externer Attestierungsbetrieb und SIEM-Vertrag fehlen. | Mutation wird erkannt; Korrektur bleibt neues Ereignis; Export in minimiertem, versioniertem SIEM-Schema. |
| Gleichzeitige Agenten | **teilweise** | Prozessübergreifende SQLite-Schreibsperre ist getestet; geteilte Policy-/Konfliktsynchronisation fehlt. | Zwei Agenten schreiben gleichzeitig, deterministischer konfliktbewahrender Merge ohne Rechteüberschreitung. |
| Portabilität/Föderation | **teilweise** | JSONL rein/raus und MCP sind vorhanden; Rechte, Zeitintervalle und Provenienzverlust über Instanzen sind nicht vollständig gegatet. | Roundtrip erhält IDs, Status, Beziehungen, Geltung, Herkunft und Rechte; unzulässige Importe scheitern atomar. |
| Identität und Autorisierung | **teilweise** | Lokaler Ausweis und Werkzeugrechte; `START_HIER.md:43-50` warnt weiterhin: ohne Ausweis keine Unterscheidung, keine Verschlüsselung/Anonymisierung. | Verifiziertes Subjekt; Default-Deny-Matrix für Werkzeug × Objekt × Zweck × Mandant; Deprovisioning. |
| SSO/SCIM und Mandanten | **fehlt** | Kein belegter Enterprise-IdP-/Provisioning-/Tenant-Lebenszyklus. | IdP-/SCIM-Vertrag, Cross-Tenant-Negativsuite und kontrollierte Offline-Ausnahme. |
| Verschlüsselung/Schlüssel | **fehlt bis teilweise** | Lokale Dateirechte/Geheimnispfade sind nicht gleich at-rest-Schlüsselmanagement. | Schlüsselrotation, Sperre/Widerruf, Restore, TLS-Grenze und Providerfluss nach Schutzprofil. |
| Retention/Löschung/Hold | **teilweise** | Rückzug/permanente Entfernung und Backuppfade existieren, aber keine geschlossene Datenklassen-Policy. | Fristlauf über Primärdaten, Index, Cache und Backup; begründeter Hold gewinnt sichtbar, nicht dauerhaft still. |
| Backup/Restore/BCM | **teilweise** | Sicherungsskripte vorhanden; kein vollständiges aktuelles RPO/RTO-/Rechte-/Suchfähigkeitsgate belegt. | Isolierter Restore aus Offline-/versionierter Kopie mit Integrität, Rechten und erfolgreichem Recall. |
| Atelier und Konfiguration | **teilweise** | Native V1 und Grenzen entschieden; `docs/adr/ADR-014...:75-81` nennt Modellzugänge und Brainlehr-Grundeinstellungen noch neu zu bauen. Vertrauensregler steht, breite Wächterwirkung offen. | Organisationspolicy begrenzt Userwahl; Modell-/Connector-/Export-/Notification-Einstellungen mit Negativtests. |

Der einzelne rote Vektorfall ist ein **bestehender Bestandsfehler**, keine neue
Produktanforderung. Die fehlenden Enterprise-Fähigkeiten sind Gaps bzw. offene
Scopeentscheidungen, keine Fehlertickets gegen die lokale 0.1.0-Beschreibung.

## RQ-014/RQ-015 — drei konkurrierende Zielbilder

| Zielbild | Chancen | Risiken | relative Kosten | falsifizierbare Annahmen |
|---|---|---|---|---|
| **A · Geschichteter, governierter Memory-Kern (local first)** — zentraler Claim-/Lesson-Ledger; Episoden bleiben quellennah/privat, semantische Claims und Prozeduren werden kontrolliert abgeleitet; Atelier/Openlehr bleiben getrennt. | Schließt direkt an SQLite/MCP, Provenienz, Normen und Audit an; kleinster Weg zu nachvollziehbarem Nutzen; offline und modellneutral. | Zentrale Instanz und lokale Identität begrenzen echte Organisationsteilung; Projektion zwischen Episode, Claim und Regel kann falsch sein. | **niedrig–mittel** | Mindestens 95 % eines festgelegten Prüfkorpus lassen die verwendete Aussage samt Quelle, Status und Gültigkeit innerhalb eines Abrufs reproduzieren; Memory-to-Action schlägt Baseline ohne Memory; Projektion leakt keine gesperrten Rohereignisse. |
| **B · Enterprise Knowledge Control Plane** — A plus IdP/SSO/SCIM, harte Mandanten-/Objekt-/Zweckpolicy, zentrale Admin-, Audit-/SIEM-, Retention-/Hold-, Connector- und SLO-Funktionen. | Klare Organisationsgrenzen und betriebliche Integration; gemeinsames Gedächtnis für Teams; kontrollierbare Provider-/Datenflüsse. | IAM-, Tenant-, Schlüssel-, Betriebs- und Compliance-Komplexität können den Memory-Kern überdecken; falsche Policy wird organisationsweit wirksam. | **hoch** | Drei voneinander getrennte Pilotmandanten bestehen Cross-Tenant-/Deprovisioning-/Restore-/Export-Negativtests; externe IAM/SIEM/DMS bleiben ersetzbar; Administrationsaufwand pro Nutzer sinkt gegenüber Einzelinstanzen. |
| **C · Föderiertes Multi-Agent-Memory-Fabric** — mehrere offline-fähige Instanzen replizieren Claims, Provenienz, Rechte und sichtbare Konflikte. | Hohe Portabilität, Resilienz und Agenten-/Organisationsgrenzen; kein zentraler Single Point of Failure. | Höchste Merge-, Identitäts-, Policy- und Löschkomplexität; globale Retention/Hold und Widerruf sind ohne zentrale Authority schwer. | **sehr hoch** | Replikate konvergieren deterministisch ohne Konfliktverlust; Widerruf und Rechte werden nicht durch Offline-Replikate umgangen; Export/Import erhält alle IDs, Zeitintervalle, Provenienz und Policies. |

### Empfehlung

**Zielbild A ist die empfohlene erste Produktgrenze.** Es erfüllt den belegten
Brainlehr-Kern und schafft die Memory-Schichtung, die aktuelle Forschung
verlangt, ohne ungeklärte Enterprise-/Föderationskosten in Version 0.x zu ziehen.
Seine Daten- und Policy-Verträge sollen jedoch so getestet werden, dass B später
anknüpfen kann: extern verifizierbare Subjekt-ID, Tenant-/Objekt-/Zweckfelder,
versioniertes Audit-/Exportformat und providerneutrale Schnittstellen.

Zielbild B ist ein **optionales Folgeprofil**, sobald ein echter
Mehrbenutzerpilot Käufer, Authority, Datenklassen, Betriebsort, Genehmigungen
und SLO benennt. Zielbild C bleibt Forschungszweig, bis ein isolierter
Konvergenz-/Widerrufs-/Rechte-Spike seine falsifizierbaren Annahmen erfüllt.
Diese Empfehlung fällt, wenn ein realer Pilot bereits jetzt harte zentrale
Mandanten-, SCIM- und SIEM-Funktionen als Eintrittskriterium verlangt oder wenn
der lokale Ledger die oben genannte Nutz-/Provenienzschwelle verfehlt.

## RQ-016 — was der Betreiber wirklich entscheiden muss

**Durch bindende Primärquellen entschieden; im Wizard höchstens als
„beibehalten oder neu öffnen“:**

1. Zwei Schichten: Brainlehr trägt Governance, Openlehr wirkt fachlich.
2. Atelier ist die gemeinsame Werkbank; gemeinsamer/unabtretbarer Rahmen dort,
   Fachlogik in Domänen, optionale gemeinsame Bestandteile separat.
3. Native V1 mit plattformblinder Beschreibung; Web später, nicht terminiert.
4. Vertrauensregler steuert Rückfragepflicht, nie Belegpflicht oder Stopp-Punkte.
5. MCP-/Modellneutralität und Quellen-/Geltungs-/Konflikt-/Wirkungsmessung sind
   der öffentlich implementierte 0.1.0-Kern; eine stabile API ist nicht versprochen.

**Echte Widersprüche, die sichtbar bleiben müssen:**

1. ADR-025/026 werden referenziert, fehlen aber im Repo; der Recall-Knoten
   `c3eb7927` nennt ADR-026 vorgeschlagen. Name, Z1–Z6 und Nicht-Ziele dürfen
   daher nicht als bereits angenommene Primärentscheidung dargestellt werden.
2. „Wissensspeicher mit Aufsicht“ und „Plattform für Domänen“ sind im
   Grundarchitektur-Prompt als konkurrierende Lesarten festgehalten. ADR-007
   entscheidet die Schichtbasis, aber nicht den Umfang einer Enterprise-
   Control-Plane.
3. Rollen wurden für Einzelbetrieb vertagt; Enterprise-Betrieb setzt mehrere
   verifizierte Subjekte und Rechte strukturell voraus.

**Echte offene Betreiberentscheidungen für den Lastenkatalog:**

1. Primäres Zielbild A, B oder C und damit erster Käufer/Betreiber.
2. Community-/Enterprise-Profil auf einem Kern oder getrennte Produkte — aber
   keine ungeprüft auseinanderlaufenden Codebasen.
3. Für B: externe Identitätsauthority, Zeitpunkt SSO/SCIM und Offline-Ausnahme.
4. Policy-Modell und Isolation: RBAC-Basis plus Objekt/Zweck/Tenant; logische
   versus physische Trennung nach Schutzbedarf.
5. Betriebsprofile und Organisationsgrenzen: on-prem/cloud/offline,
   Datenresidenz, Provider-/Connector-Allowlist, Schlüsselherrschaft.
6. Datenlebenszyklus: Klassen, Retention, Löschung, Hold, Export und Portabilität.
7. Audit/SIEM, Genehmigungsmatrix und SLO/RPO/RTO mit konkreten Zielwerten.
8. Konfigurationsfreiheit unter Organisationsgrenzen: Recall-Sichtbarkeit,
   persönliche/Firmensicht, Freigabe/Export, Notifications, Modellwahl und
   Ausgestaltung des beschlossenen Vertrauensreglers.
9. Priorität unabhängiger Fähigkeiten: Memory-Typen, Konflikt-/Zeitlogik,
   Memory-to-Action-Evals, Wissenspakete, Connectoren, Multi-User und Föderation.

Nicht der Betreiber entscheiden muss, ob negative Bestandsbehauptungen trotz
sichtbarer Treffer zulässig sind oder ob Backups je getestet werden: Das sind
bereits durch `MUST-LAGE-001` beziehungsweise die Sicherheitsbaseline
beantwortete Qualitätsgrenzen. Offen sind Schwellen, Profile und Zeitpunkte.

## RQ-017/RQ-018 — Wizard-Ableitung und Abnahme

Der finale Dialog liegt außerhalb des Repos unter
`/Users/lehrmacbook/.codex/visualizations/2026/08/17/01a010f0-d6a0-73c0-a545-bea4fc2f1316/brainlehr-entscheidungsdialog.html`.
Seine eine Inline-JavaScript-Datenquelle enthält 53 eindeutige Frage-IDs:

| Seite | IDs | Anzahl |
|---|---|---:|
| belegte Entscheidungen / Review | `BDW-R01`–`BDW-R05` | 5 |
| echte Widersprüche | `BDW-C01`–`BDW-C03` | 3 |
| offene Produktentscheidungen | `BDW-P01`–`BDW-P05` | 5 |
| Unternehmensbetrieb / Sicherheit | `BDW-E01`–`BDW-E21` | 21 |
| neue Fähigkeiten / Priorität | `BDW-F01`–`BDW-F11` | 11 |
| Benutzer-/Admin-Konfiguration | `BDW-U01`–`BDW-U08` | 8 |

Jede Frage nennt Kontext, Primärbeleg oder geprüften Repo-Recall, zwei bis vier
exklusive Optionen und zusätzlich `Später entscheiden`. Empfehlungen sind
markiert, aber nicht vorausgewählt. Die fünf Review-Fragen öffnen bindende
Primärentscheidungen nur ausdrücklich neu; die fehlenden ADR-025/026 erscheinen
als Konflikt und nicht als angenommene Norm. Die Enterprise-Seite kennzeichnet
BSI-Punkte als Sicherheitsbaseline/Guidance.

Abnahme am 2026-08-17:

- Fragmentform geprüft: kein `html/body`, kein `fetch`, keine externe API;
  53 eindeutige IDs in sechs Kategorien und sieben Seiten.
- JavaScript mit `node --check` fehlerfrei; keine vorausgewählte Radio-Option.
- Echte Browserinteraktion: Auswahl bleibt über Seitenwechsel erhalten;
  Zusammenfassung nennt alle fehlenden IDs und Zähler je Kategorie.
- Tastatur: Radioauswahl per Leertaste und Seitennavigation per Enter bestanden.
- Follow-up-Vertrag statisch und im Quelltext geprüft:
  `window.openai.sendFollowUpMessage({title,prompt})`, Titel 40 Zeichen,
  Prompt mit allen IDs, Auswahl/`offen`, Freitext und fehlenden IDs.
- Menschliche visuelle Prüfung in Dark Mode bei 736 × 900 und 360 × 900:
  Navigation bricht um, Fragen und Quellen bleiben lesbar; bei 360 px kein
  horizontaler Überlauf (`scrollWidth == clientWidth == 313` im Host-Frame).
