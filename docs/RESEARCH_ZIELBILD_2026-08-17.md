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
| RQ-001 | Welche Betreiberentscheidungen, ADRs, Pläne, Codepfade, Tests und verifizierten Brainlehr-Knoten bilden die interne Produktgenealogie? | Quellenmatrix mit Status und direktem Repo-Beleg | OFFEN |
| RQ-002 | Was ist intern bereits bindend entschieden, was nur vorgeschlagen, überholt, widersprüchlich oder offen? | Jede Kernaussage trägt genau eine Einstufung | OFFEN |
| RQ-003 | Welcher Stand der Technik 2025/2026 gilt für episodisches, semantisches und prozedurales agentisches Langzeitgedächtnis? | Primärquellen mit URL/Abrufdatum | OFFEN |
| RQ-004 | Welche Mechanismen sind Stand der Technik für Provenance, Confidence, Decay und zeitliche Geltung? | Primärquellen; Abgleich mit Ist-Code/Test | OFFEN |
| RQ-005 | Wie werden Retrieval, Antwortnützlichkeit, Konflikte und Policy-Governance belastbar evaluiert? | Messbare Evals und Testgates statt Featureliste | OFFEN |
| RQ-006 | Welche Anforderungen folgen aus Tamper Evidence, Multi-Agent-/Shared Memory und Portabilität/Föderation? | Primärquellen; Risiken und Nicht-Ziele | OFFEN |
| RQ-007 | Welche Unternehmensbaseline folgt für Identitätsauthority, SSO/SCIM und Lebenszyklus von Konten? | BSI-Control-IDs plus offizielle Standards | OFFEN |
| RQ-008 | Welche Baseline folgt für RBAC/ABAC/objektbezogene Rechte und Mandantentrennung? | BSI-Control-IDs; testbare Autorisierungsgrenzen | OFFEN |
| RQ-009 | Welche Baseline folgt für Verschlüsselung, Schlüsselverwaltung und Datenresidenz? | BSI-Control-IDs; Betriebsoptionen ohne Compliancebehauptung | OFFEN |
| RQ-010 | Welche Baseline folgt für Audit/SIEM, Aufbewahrung, Löschung und Legal Hold? | BSI-Control-IDs; prüfbare Ereignis- und Lebenszyklusgates | OFFEN |
| RQ-011 | Welche Baseline folgt für Backup/Restore/BCM, DLP/Privacy, Genehmigungswege und Observability/SLO? | BSI-Control-IDs; Restore- und Betriebs-Gates | OFFEN |
| RQ-012 | Wo endet Brainlehr gegenüber Atelier, Openlehr/Fachdomänen, DMS, Suchmaschine, Vektordatenbank, Agent-Orchestrator und IAM? | Boundary-Matrix; offene Optionen nicht vorentschieden | OFFEN |
| RQ-013 | Welche Fähigkeiten sind heute vorhanden, teilweise vorhanden, fehlen oder bewusst Nicht-Ziel? | Gap-Matrix mit Evidenz und Testgate je Zeile | OFFEN |
| RQ-014 | Welche mindestens drei konkurrierenden Zielbilder sind realistisch? | Chancen, Risiken, relative Kosten und falsifizierbare Annahmen je Zielbild | OFFEN |
| RQ-015 | Welches Zielbild ist aufgrund der Evidenz empfohlen, und wodurch wäre die Empfehlung widerlegt? | Empfehlung plus explizite Falsifikationsbedingungen | OFFEN |
| RQ-016 | Welche Fragen muss der Betreiber wirklich entscheiden, und welche sind bereits belegt entschieden? | Entscheidungsmenge ohne erneut geöffnete Scheinoffenheit | OFFEN |
| RQ-017 | Ist jede Frage und Empfehlung des Wizards aus Research oder bindender Primärquelle ableitbar? | Stabile Wizard-Frage-ID, Quellen und keine Vorauswahl | OFFEN |
| RQ-018 | Besteht der aktualisierte Wizard technisch und als menschlich lesbarer Dialog bei 736 px und 360 px? | JS-/ID-Prüfung, Tastaturtest, visuelle Prüfung, Zusammenfassungs-Prompt | OFFEN |

## Ergebnisstruktur

Die abgeschlossene Research ergänzt unterhalb dieses Katalogs: interne
Genealogie, externe Evidenz, Unternehmensbaseline, Produktgrenze, Gap-Matrix,
drei Zielbilder, Empfehlung, falsifizierbare Annahmen und die echte
Betreiber-Entscheidungsmenge. Danach wird nur diese Entscheidungsmenge in den
Wizard übernommen.
