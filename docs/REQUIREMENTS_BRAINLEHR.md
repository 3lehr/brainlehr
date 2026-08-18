# Brainlehr — kanonischer Root-Lastenkatalog

Stand: 2026-08-17

Normative Quelle: die vollständige Operator-Matrix der 53 `BDW-*`-
Entscheidungen. Decoder und Evidenz:
`/Users/lehrmacbook/.codex/visualizations/2026/08/17/01a010f0-d6a0-73c0-a545-bea4fc2f1316/brainlehr-entscheidungsdialog.html`
und `docs/RESEARCH_ZIELBILD_2026-08-17.md`.

## Geltung

Dies ist der **eine normative Gesamtplan** für Brainlehr. Pläne, `STAND.md`,
`SPRINTS.md`, `AI_HANDOFF.md`, Research und Teilkataloge sind Evidenz oder
Umsetzung, aber keine konkurrierende normative Quelle. Die vorhandenen
Teilkataloge bleiben untergeordnet; ihre lokalen IDs sind Umsetzungsgates.

Katalogstatus und Produkt-Teststatus sind getrennt: `DECIDED` bedeutet, dass
die Entscheidung feststeht, nicht dass sie gebaut oder abgenommen ist.
`NOT RUN` bedeutet, dass das jeweilige Produktgate noch nicht vollständig
ausgeführt wurde. `OPEN`, `CONFLICT`, `DEFERRED` und `PILOT` bleiben
sichtbar, bis dieselbe BDW-ID aktualisiert wird.

**Agil und ohne Dogma** heißt: Dieser Katalog ist versionierbar und darf durch
neue belegte Betreiberentscheidungen geändert werden. Es heißt niemals, Beleg-,
Sicherheits-, Konflikt- oder Testgates abzuschaffen. Änderungen aktualisieren
dieselben `BDW-*`-IDs; eine parallele Requirement-Skala ist unzulässig.

## Statusübersicht

- Offene IDs: **keine**
- Offene Konflikte: **keine**
- Explizit aufgelöste Ursprungskonflikte:
  - `BDW-C01`: fehlende ADR-025/026 werden nicht fingiert; dieser Root ist der
    gewählte neue Zweckbeschluss aus der Research.
  - `BDW-C02`: Brainlehr ist ein governierter Kern mit optionalem
    Enterprise-Profil, keine ungetrennte Vollplattform.
- Pilot: `BDW-C03`, `BDW-E04`, `BDW-E05`
- Deferred: `BDW-E17` — Auswahl `later` bedeutet im gemeinsamen
  Wizard-Decoder ausdrücklich **Später entscheiden**. Zielbild A bleibt davon
  unberührt local-first; zusätzliche Betriebsprofile werden später festgelegt.
- Bereits bindend und unverändert übernommen: `BDW-R01`–`BDW-R05`
- Produkt-Teststatus: Alle 53 Gates beginnen mit **NOT RUN**. Bestehende
  Implementierung ist Evidenz, aber keine pauschale Abnahme dieses Root-Katalogs.

## Genau ein Interpretationsreview

Der Betreiber war bei einzelnen Formulierungen unsicher, hat aber alle 53
Fragen beantwortet. Daher wird keine konkrete Auswahl pauschal auf `OPEN`
gesetzt. Stattdessen findet nach dem ersten daraus abgeleiteten
Implementierungsplan genau ein gemeinsames Review statt: Optionstext,
normativer Satz und `AC1` werden nebeneinander gelesen. Ein Missverständnis
ändert dieselbe BDW-ID mit Begründung; es erzeugt keine neue ID-Skala.

## Belegte Entscheidungen und Produktgrenze

| ID | Auswahl | Normtyp | Status | Vollständige normative Entscheidung | Scope / Owner | Akzeptanzkriterium | Produktgate | Quelle |
|---|---|---|---|---|---|---|---|---|
| BDW-R01 | `keep` | MUSS | DECIDED | Die Zweischicht bleibt: Brainlehr trägt Wissens-Governance; Openlehr macht Menschen fachlich handlungsfähig. | Core / Architektur | `BDW-R01-AC1`: Eine Boundary-Prüfung ordnet Governance Brainlehr und Fachlogik Openlehr zu. | NOT RUN | Auswahl „Beibehalten“; ADR-007; RQ-001/002 |
| BDW-R02 | `keep` | MUSS | DECIDED | Atelier bleibt die getrennte gemeinsame Werkbank; gemeinsamer Rahmen und unabtretbare Sicherheit liegen dort, Fachlogik in den Domänen. | Atelier-Grenze / Architektur | `BDW-R02-AC1`: Eine Schichtprüfung weist keine Domänenfachlogik dem Atelier-Kern zu. | NOT RUN | Auswahl „Beibehalten“; ADR-008/014; RQ-001/002 |
| BDW-R03 | `keep` | MUSS | DECIDED | V1 bleibt nativ und die Beschreibung plattformblind; eine Weboberfläche ist später möglich, aber nicht terminiert. | Produkt / Architektur | `BDW-R03-AC1`: Ein zweiter Renderer kann dieselbe plattformblinde Beschreibung nutzen, ohne V1-Fachlogik zu duplizieren. | NOT RUN | Auswahl „Beibehalten“; ADR-024; RQ-001/002 |
| BDW-R04 | `keep` | MUSS | DECIDED | Der Vertrauensregler steuert nur die Rückfragepflicht; Belegpflicht und harte Stopp-Punkte bleiben unverändert. | Core / Safety | `BDW-R04-AC1`: Für jede Reglerstufe bleiben Beleggate und harte Stopps identisch wirksam. | NOT RUN | Auswahl „Beibehalten“; PLAN_VERTRAUENSREGLER; RQ-001/002 |
| BDW-R05 | `keep` | MUSS | DECIDED | Der lokale, modell- und MCP-neutrale 0.1-Kern bleibt Produktbasis; Quellen, Geltung, Konflikt und Retrievalwirkung sind Kern, eine stabile API ist noch nicht versprochen. | Core / Produkt | `BDW-R05-AC1`: Derselbe Kern besteht einen lokalen MCP-Lauf mit austauschbarem Modellpfad und ausgewiesener Quelle/Geltung. | NOT RUN | Auswahl „Beibehalten“; README; RQ-001/002 |
| BDW-C01 | `new-decision` | MUSS | DECIDED | Aus der Research wird ein neuer Root-Zweckbeschluss abgeleitet; fehlende ADR-025/026 werden nicht als angenommen fingiert. Dieser Katalog ist dieser Beschluss. | Gesamtprodukt / Product Owner | `BDW-C01-AC1`: Jede normative Produktanforderung ist über eine BDW-ID in diesem Root auffindbar; fehlende ADRs werden nur als Genealogie benannt. | NOT RUN | Auswahl „Neuen Root-Zweckbeschluss aus Research ableiten“; RQ-001/002/016 |
| BDW-C02 | `governed-core` | Profil | DECIDED | Brainlehr ist ein governierter Kern mit optionalem Enterprise-Profil. | Gesamtprodukt / Architektur | `BDW-C02-AC1`: Core-Tests laufen ohne Enterprise-Connectoren; das Enterprise-Profil ergänzt, ersetzt aber nicht den Core. | NOT RUN | Auswahl „Governierter Kern mit optionalem Enterprise-Profil“; RQ-012/015 |
| BDW-C03 | `pilot` | Pilot | PILOT | Das Rollenmodell wird mit dem ersten realen Mehrbenutzer-Piloten aktiviert. | Enterprise / IAM Owner | `BDW-C03-AC1`: Ein Mehrbenutzer-Pilot startet erst nach Rollen-, Subjekt- und Negativrechtetest. | NOT RUN | Auswahl „Mit erstem realen Mehrbenutzer-Piloten“; RQ-016 |
| BDW-P01 | `regulated` | Profil | DECIDED | Primäre Zielgruppe der ersten Mehrbenutzer-Fassung sind regulierte Großunternehmen. | Enterprise / Product Owner | `BDW-P01-AC1`: Pilotanforderungen benennen Authority, Datenklassen, Betriebsort, Genehmigungen und SLO. | NOT RUN | Auswahl „Regulierte Großunternehmen“; RQ-013/015 |
| BDW-P02 | `root-index` | MUSS | DECIDED | Es gibt einen Root-Katalog mit referenzierten untergeordneten Abschnitten; unverbundene konkurrierende Kataloge sind unzulässig. | Governance / Product Owner | `BDW-P02-AC1`: Ein automatischer Test findet genau diesen Root und alle Teilkataloge verweisen auf ihn. | NOT RUN | Auswahl „Ein Root-Katalog mit referenzierten Abschnitten“; cd571222; RQ-016 |
| BDW-P03 | `profiles` | Profil | DECIDED | Lokale und Enterprise-Fassung nutzen einen Kern mit klaren Profilen, keine getrennten Codebasen. | Architektur / Tech Lead | `BDW-P03-AC1`: Profiltests belegen einen gemeinsamen Core und verhindern divergierende Implementierungen derselben Regel. | NOT RUN | Auswahl „Ein Kern mit klaren Profilen“; RQ-012/015 |
| BDW-P04 | `eval-suite` | MUSS | DECIDED | Retrieval wird mit Treffer-, Falschmelde-, Abstention- und Aktionsgates abgenommen. | Retrieval / Quality Owner | `BDW-P04-AC1`: Ein versionierter Prüfkorpus misst alle vier Gatearten und weist Schwellen aus. | NOT RUN | Auswahl „Treffer-, Falschmelde-, Abstention- und Aktionsgates“; RQ-003–006 |
| BDW-P05 | `A` | Profil | DECIDED | Nächste Produktgrenze ist Zielbild A: ein governierter Local-first-Memory-Kern. | Gesamtprodukt / Product Owner | `BDW-P05-AC1`: Der Kern reproduziert in mindestens 95 % des festgelegten Prüfkorpus Aussage, Quelle, Status und Gültigkeit innerhalb eines Abrufs. | NOT RUN | Auswahl „A · governierter Local-first-Memory-Kern“; RQ-014/015 |

## Enterprise- und Sicherheitsprofil

BSI-Punkte sind Sicherheitsbaseline/Guidance, keine Compliancebehauptung.

| ID | Auswahl | Normtyp | Status | Vollständige normative Entscheidung | Scope / Owner | Akzeptanzkriterium | Produktgate | Quelle |
|---|---|---|---|---|---|---|---|---|
| BDW-E01 | `external` | MUSS | DECIDED | Ein externer zentraler IdP ist Identitätsauthority. | Enterprise IAM / Security | `BDW-E01-AC1`: Jede produktive Subjekt-ID ist zum IdP rückführbar und Deprovisioning sperrt den Zugriff. | NOT RUN | „Externer zentraler IdP“; RQ-007; BSI BER.2.1/2.5 |
| BDW-E02 | `base` | MUSS | DECIDED | RBAC ist die Basisschicht der Autorisierung. | Enterprise IAM / Security | `BDW-E02-AC1`: Default-Deny-Rollentests belegen Least Privilege. | NOT RUN | „RBAC als Basisschicht“; RQ-008; BSI BER.4.1/4.2/4.4 |
| BDW-E03 | `intersection` | MUSS | DECIDED | Wirksames Recht ist die Schnittmenge aus Rolle, Objekt und Zweck; Tenant- und Werkzeuggrenzen verengen zusätzlich. | Enterprise Policy / Security | `BDW-E03-AC1`: Eine Negativmatrix für Rolle × Objekt × Zweck × Tenant verweigert jede fehlende Freigabe. | NOT RUN | „Rolle ∩ Objekt ∩ Zweck“; RQ-008 |
| BDW-E04 | `first-pilot` | Pilot | PILOT | SSO über den zentralen IdP ist ab dem ersten Mehrbenutzer-Piloten Pflicht. | Enterprise IAM / Security | `BDW-E04-AC1`: Der Pilot besteht Login, Sessionbindung, Logout und IdP-Sperre E2E. | NOT RUN | „Ab erstem Mehrbenutzer-Pilot“; RQ-007 |
| BDW-E05 | `pilot` | Pilot | PILOT | SCIM 2.0 ist ab dem ersten Enterprise-Piloten Pflicht. | Enterprise IAM / Security | `BDW-E05-AC1`: Create, Update, Disable und Delete werden gegen den Pilot-IdP E2E geprüft. | NOT RUN | „Ab erstem Enterprise-Pilot“; RQ-007; RFC 7644 |
| BDW-E06 | `tested` | MUSS | DECIDED | Mandantentrennung wird technisch erzwungen und negativ getestet. | Enterprise Data / Security | `BDW-E06-AC1`: Cross-Tenant-Lesen, -Suche, -Relation, -Export, -Backup und -Admin scheitern. | NOT RUN | „Technisch erzwungen und negativ getestet“; RQ-008 |
| BDW-E07 | `sensitive` | MUSS | DECIDED | Alle sensiblen Daten und ihre Ableitungen werden ruhend verschlüsselt. | Data / Security | `BDW-E07-AC1`: Daten, Index und Backup eines sensiblen Testfalls sind ohne autorisierten Schlüssel nicht lesbar. | NOT RUN | „Alle sensiblen Daten und Ableitungen“; RQ-009 |
| BDW-E08 | `operator` | Profil | DECIDED | Der Betreiber entscheidet die Transportverschlüsselung je Betriebsprofil; diese Wahl darf Sicherheitsgates nicht abschaffen. Remote-Pfade benötigen authentisierte Vertraulichkeit und Integrität, Abweichungen nur als dokumentierte isolierte/offline Ausnahme. | Betrieb / Security | `BDW-E08-AC1`: Jedes Profil weist verschlüsselte Remote-Pfade oder eine explizite, getestete lokale/offline Ausnahme aus. | NOT RUN | „Betreiber entscheidet“; RQ-009; BSI ASST.4.2 |
| BDW-E09 | `customer` | MUSS | DECIDED | Schlüssel sind kundenseitig kontrollierbar. | Key Management / Security | `BDW-E09-AC1`: Rotation, Widerruf und Restore mit kundenseitig kontrolliertem Schlüssel bestehen. | NOT RUN | „Kundenseitig kontrollierbar“; RQ-009 |
| BDW-E10 | `tamper` | MUSS | DECIDED | Audit ist manipulationsgeschützt und versioniert. | Audit / Security | `BDW-E10-AC1`: Mutation wird erkannt; Korrektur bleibt als neues Ereignis sichtbar. | NOT RUN | „Manipulationsgeschützt und versioniert“; RQ-006/010 |
| BDW-E11 | `stream-export` | MUSS | DECIDED | SIEM erhält Standardexport und Streaming über ein versioniertes ersetzbares Format. | Audit/SIEM / Operations | `BDW-E11-AC1`: Batch und Stream liefern dasselbe minimierte Ereignisschema ohne Inhaltsleck. | NOT RUN | „Standardexport plus Streaming“; RQ-010 |
| BDW-E12 | `class-policy` | MUSS | DECIDED | Aufbewahrung folgt einer zentralen Policy je Datenklasse. | Data Lifecycle / Data Owner | `BDW-E12-AC1`: Jede persistierte Datenklasse besitzt Zweck, Frist und Ablaufverhalten. | NOT RUN | „Zentrale Policy je Datenklasse“; RQ-010 |
| BDW-E13 | `verified` | MUSS | DECIDED | Löschung erfolgt automatisch, protokolliert und prüfbar über Primärdaten, Indizes, Caches und Kopien. | Data Lifecycle / Data Owner | `BDW-E13-AC1`: Ein Fristlauf entfernt alle Testableitungen und erzeugt einen minimierten Nachweis. | NOT RUN | „Automatisch, protokolliert und prüfbar“; RQ-010 |
| BDW-E14 | `policy` | MUSS | DECIDED | Legal Hold ist eine explizite Policy mit Freigabe und Audit. | Data Lifecycle / Legal+Security | `BDW-E14-AC1`: Autorisierter Hold blockiert Löschung sichtbar; Aufhebung setzt den Fristlauf fort. | NOT RUN | „Explizite Policy mit Freigabe und Audit“; RQ-010 |
| BDW-E15 | `managed` | MUSS | DECIDED | Backups sind automatisch, getrennt und offline-fähig. | BCM / Operations | `BDW-E15-AC1`: Eine versionierte verschlüsselte Kopie bleibt nach simuliertem Primärausfall verfügbar. | NOT RUN | „Automatisch, getrennt, offline-fähig“; RQ-011 |
| BDW-E16 | `regular` | MUSS | DECIDED | Restore wird regelmäßig isoliert getestet, einschließlich RPO/RTO, Integrität, Rechte und Suchfähigkeit. | BCM / Operations | `BDW-E16-AC1`: Ein protokollierter Restore erreicht Profil-RPO/RTO und besteht Rechte- und Recalltest. | NOT RUN | „Regelmäßiger isolierter Restore-Test“; RQ-011 |
| BDW-E17 | `later` | Deferred | DEFERRED | Unterstützte zusätzliche Betriebsprofile werden später entschieden; Zielbild A bleibt local-first, ohne Cloud/Hybrid jetzt normativ festzulegen. | Deployment / Product+Operations | `BDW-E17-AC1`: Vor Aktivierung eines weiteren Profils werden Betriebsgrenzen, Datenflüsse, Residenz und SLO in derselben ID entschieden und getestet. | NOT RUN | Globale Wizard-Auswahl „Später entscheiden“; RQ-011/015 |
| BDW-E18 | `risk` | Profil | DECIDED | Genehmigungen folgen einer risikobasierten Matrix; Vier-Augen gilt selektiv für entsprechend kritische Vorgänge. | Governance / Security | `BDW-E18-AC1`: Regelrang, Export, Connector, Providerwechsel, Ausnahme und Hold sind klassifiziert und korrekt gegatet. | NOT RUN | „Risikobasierte Matrix; Vier-Augen selektiv“; RQ-011 |
| BDW-E19 | `tenant-region` | MUSS | DECIDED | Zulässige Datenregionen werden je Mandant technisch begrenzt. | Residency / Data Owner | `BDW-E19-AC1`: Daten, Index, Backup, Telemetrie und Modellfluss verlassen keine erlaubte Region. | NOT RUN | „Zulässige Regionen je Mandant“; RQ-009/011 |
| BDW-E20 | `default-deny` | MUSS | DECIDED | DLP/Privacy an Ausgängen ist klassifiziert, minimiert und default-deny. | DLP / Security | `BDW-E20-AC1`: Recall, Fehler, Telemetrie, Connector und Export leaken keine gesperrten Testinhalte. | NOT RUN | „Klassifiziert, minimiert, default-deny“; RQ-011 |
| BDW-E21 | `profile` | Profil | DECIDED | SLI/SLO werden je Betriebsprofil festgelegt. | Observability / Operations | `BDW-E21-AC1`: Jedes aktive Profil misst Verfügbarkeit, Recall-Nutzen, Fehlklassifikation, Latenz, Restore und Policy-Denials. | NOT RUN | „SLI/SLO je Betriebsprofil“; RQ-011 |

## Fähigkeiten und Priorität

| ID | Auswahl | Normtyp | Status | Vollständige normative Entscheidung | Scope / Owner | Akzeptanzkriterium | Produktgate | Quelle |
|---|---|---|---|---|---|---|---|---|
| BDW-F01 | `must` | MUSS | DECIDED | Episodisches Gedächtnis gehört in die erste Version. | Memory Core / Product | `BDW-F01-AC1`: Episoden bestehen Schreib-, Zeit-, Quellen-, Recall-, Korrektur- und Löschtest. | NOT RUN | „MUSS erste Version“; RQ-003 |
| BDW-F02 | `must` | MUSS | DECIDED | Semantische Claims gehören in die erste Version. | Memory Core / Product | `BDW-F02-AC1`: Jeder verwendete Claim weist Quelle, Ableitung, Status und Korrekturpfad aus. | NOT RUN | „MUSS erste Version“; RQ-003/004 |
| BDW-F03 | `must` | MUSS | DECIDED | Prozedurales Gedächtnis gehört in die erste Version. | Memory Core / Product | `BDW-F03-AC1`: Prozeduren sind von Fakten/Episoden getrennt und besitzen eigenen Freigabe- und Widerrufstest. | NOT RUN | „MUSS erste Version“; RQ-003 |
| BDW-F04 | `must` | MUSS | DECIDED | Zeit-, Konflikt-, Confidence- und Decay-Governance gehört in die erste Version. | Governance Core / Product | `BDW-F04-AC1`: Ersetzen, Ablauf, Widerruf und Gleichrangkonflikt erscheinen ohne stilles Überschreiben. | NOT RUN | „MUSS erste Version“; RQ-004/005 |
| BDW-F05 | `must` | MUSS | DECIDED | Retrieval-to-Action-Evaluation gehört in die erste Version. | Evaluation / Quality | `BDW-F05-AC1`: Ein Benchmark belegt korrekte Toolwahl/-parameter und bessere Wirkung gegenüber einer No-Memory-Baseline. | NOT RUN | „MUSS erste Version“; RQ-005 |
| BDW-F06 | `must` | MUSS | DECIDED | Manipulationsgeschützte Auditkette gehört in die erste Version. | Audit Core / Security | `BDW-F06-AC1`: Nachträgliche Logänderung wird erkannt, legitime Korrektur bleibt append-only. | NOT RUN | „MUSS erste Version“; RQ-006 |
| BDW-F07 | `must` | MUSS | DECIDED | Portable Wissenspakete gehören in die erste Version. | Portability / Product | `BDW-F07-AC1`: Export/Import erhält IDs, Zeit, Provenienz, Rechte und Konflikte atomar. | NOT RUN | „MUSS erste Version“; RQ-006/012 |
| BDW-F08 | `must` | MUSS | DECIDED | Dokument- und Quellenconnectoren gehören in die erste Version, ohne Brainlehr zum DMS zu machen. | Connectors / Product | `BDW-F08-AC1`: Connector speichert Referenz, Prüfsumme, Provenienz und Claims statt unkontrollierter Dokumentkopie. | NOT RUN | „MUSS erste Version“; RQ-012 |
| BDW-F09 | `must` | MUSS | DECIDED | Privacy-Projektion für externe Modelle gehört in die erste Version. | Projection / Security | `BDW-F09-AC1`: Nur zweckgebundene freigegebene Felder verlassen die lokale Grenze; Negativfälle leaken nichts. | NOT RUN | „MUSS erste Version“; RQ-011/012 |
| BDW-F10 | `must` | MUSS | DECIDED | Mehrbenutzer-Administration gehört in die erste Version. | Enterprise Admin / IAM | `BDW-F10-AC1`: Subjekte, Gruppen, Rechte, Deprovisioning und Audit bestehen einen geschlossenen E2E-Pfad. | NOT RUN | „MUSS erste Version“; RQ-007/008/013 |
| BDW-F11 | `should` | SOLL | DECIDED | Föderation und Multi-Agent-Synchronisation folgen später. | Federation / Research | `BDW-F11-AC1`: Vor Produktisierung bestehen deterministische Konvergenz-, Widerrufs-, Rechte- und Offline-Replikationstests. | NOT RUN | „SOLL später“; RQ-006/014/015 |

## Benutzer- und Admin-Konfiguration

| ID | Auswahl | Normtyp | Status | Vollständige normative Entscheidung | Scope / Owner | Akzeptanzkriterium | Produktgate | Quelle |
|---|---|---|---|---|---|---|---|---|
| BDW-U01 | `org-ceiling` | MUSS | DECIDED | Die Organisation setzt die maximale Vertrauensreglerstufe; Nutzer dürfen sie absenken. | Trust / Org Admin | `BDW-U01-AC1`: Nutzer kann keine höhere Stufe als die Org-Grenze setzen; Absenkung wirkt sofort. | NOT RUN | „Org setzt Maximalstufe, Nutzer darf absenken“; RQ-016 |
| BDW-U02 | `receipt` | MUSS | DECIDED | Jede Antwort zeigt einen kompakten Quellen-/Policy-Beleg der Recall-Aktivität. | UX / Product | `BDW-U02-AC1`: Beleg nennt verwendete/abgelehnte Quellen und Policywirkung ohne geschützten Inhalt. | NOT RUN | „Kompakter Quellen-/Policy-Beleg je Antwort“; RQ-005/016 |
| BDW-U03 | `separate` | MUSS | DECIDED | Persönliche und Firmen-Sicht bleiben getrennt; Übergang verlangt explizite Freigabe. | Views / Security | `BDW-U03-AC1`: Privater Testinhalt erscheint ohne Freigabe nie in Firmenabruf oder -export. | NOT RUN | „Getrennte Sichten mit expliziter Freigabe“; RQ-008/016 |
| BDW-U04 | `allowlist` | MUSS | DECIDED | Die Organisation führt eine Connector-Allowlist; Nutzer wählen nur daraus. | Connectors / Org Admin | `BDW-U04-AC1`: Nicht gelisteter Connector kann weder aktiviert noch durch Direktaufruf genutzt werden. | NOT RUN | „Org-Allowlist, Nutzer wählt daraus“; RQ-011/016 |
| BDW-U05 | `policy` | MUSS | DECIDED | Freigabe und Export folgen Policy plus risikobasierter Genehmigung. | Export / Security | `BDW-U05-AC1`: Zweck, Ziel, Klassifikation und gegebenenfalls Genehmigung werden vor Export geprüft und auditiert. | NOT RUN | „Policy plus risikobasierte Genehmigung“; RQ-010/011/016 |
| BDW-U06 | `risk` | Profil | DECIDED | Benachrichtigungen sind risikobasiert und nutzen konfigurierbare Nutzerkanäle innerhalb der Org-Policy. | Notifications / Operations | `BDW-U06-AC1`: Konflikt, Ablauf, Quellenlücke und Policy-Denial werden nach Risiko geroutet, ohne Inhaltsleck. | NOT RUN | „Risikobasiert mit Nutzerkanälen“; RQ-011/016 |
| BDW-U07 | `approved` | MUSS | DECIDED | Die Organisation führt eine Modell-/Provider-Allowlist; Nutzer wählen nur daraus. | Models / Org Admin | `BDW-U07-AC1`: Nicht freigegebener Provider erhält auch per Direktaufruf keine Daten. | NOT RUN | „Org-Allowlist, Nutzer wählt“; RQ-009/016 |
| BDW-U08 | `org-wins` | MUSS | DECIDED | Bei Konflikt gewinnt die Organisationsgrenze sichtbar vor der Nutzerwahl. | Policy / Security | `BDW-U08-AC1`: Ein Konfliktfall wird verweigert, erklärt und auditiert; Nutzerwahl überschreibt die Org-Policy nie. | NOT RUN | „Org-Grenze gewinnt sichtbar“; RQ-008/016 |

## Untergeordnete Teilkataloge

- `docs/REQUIREMENTS_PROMPT_INVARIANZ.md`
- `docs/REQUIREMENTS_SESSION_CHECKPOINT.md`
- `docs/REQUIREMENTS_INTERFACE_KOMPAT.md` (Interface- und Kompatibilitätsvertrag zu `BDW-F07`)

Ihre lokalen IDs bleiben für Umsetzung und Regression erhalten. Bei
Widerspruch gilt dieser Root; der Konflikt wird hier an der betroffenen
`BDW-*`-ID sichtbar gemacht, nicht im Teilkatalog still aufgelöst.
