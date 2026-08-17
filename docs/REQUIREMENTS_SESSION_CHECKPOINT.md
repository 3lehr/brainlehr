# Lastenkatalog: temporärer Sitzungscheckpoint

Stand: 2026-08-17T19:59:51+02:00

Quelle: Betreiberentscheidung `19724255`

| ID | Typ | Anforderung | Gate | Status |
|---|---|---|---|---|
| MUST-SESSION-001 | MUSS | Pro `session_id` existiert höchstens ein temporärer, agentneutraler Checkpoint. Schreiben und Auswerten benötigen keinen Modellaufruf. | `TEST-SESSION-001` | PASS |
| MUST-SESSION-002 | MUSS | Persistiert werden nur technische IDs und Zustände: Sitzung, Projekt, Kontextanteil, Themenkennung, Requirements-, Child- und Evidenz-IDs, nächste Aktions-ID, Status und Ablaufzeit. | `TEST-PRIV-001` | PASS |
| MUST-SESSION-003 | MUSS | Setzen, Lesen und Schließen sind idempotent; abgelaufene Zeilen werden beim Zugriff entfernt. Der Checkpoint wird weder per FTS noch per Embedding oder Recall indiziert. | `TEST-SESSION-001` | PASS |
| MUST-ROLL-001 | MUSS | Offene erforderliche Child-IDs verhindern einen Chatwechsel und verlangen zuerst Integration. | `TEST-ROLL-001` | PASS |
| MUST-ROLL-002 | MUSS | Ab 75 Prozent wird Sichern empfohlen, ab 88 Prozent das vollständige Sicherungsgate; beides ist kein Chatwechsel. | `TEST-ROLL-001` | PASS |
| MUST-ROLL-003 | MUSS | Ein neues Chatfenster wird nur bei geänderter Themenkennung und vollständigem Übergabepaket empfohlen. | `TEST-ROLL-001` | PASS |
| MUST-AGENT-001 | MUSS | Claude, ChatGPT/Codex und Hermes referenzieren dieselbe deterministische Checkpoint- und Wechselregel; der vorhandene Claude-Kontextwächter fordert bei 75/88 Prozent die Aktualisierung an. | `TEST-AGENT-001` | PASS |
| MUST-PRIV-001 | MUSS | Rohprompts, Antworten, Transkripte, Freitext, PII, Secrets, Nutzerpräferenzen und frühere Gewinner sind strukturell nicht speicherbar. | `TEST-PRIV-001` | PASS |
| MUST-NOT-001 | DARF NICHT | Der Checkpoint wird nicht bei jedem Prompt in den Modellkontext injiziert. | Quelltextprüfung | PASS |
| MUST-NOT-002 | DARF NICHT | Es entsteht kein zweiter dauerhafter Memory- oder Eventlog-Dienst. | Schema-/Quelltextprüfung | PASS |
| MUST-NOT-003 | DARF NICHT | Der Checkpoint startet keine Schatten- oder Modellaufrufe und schätzt keine Tokenzahl. | Quelltextprüfung | PASS |
| TEST-SESSION-001 | TEST | Setzen, Lesen, Überschreiben, Ablauf und Schließen gegen eine temporäre SQLite-Datenbank. | Pytest | PASS |
| TEST-ROLL-001 | TEST | Offene Children, 75/88 Prozent sowie vollständiger und unvollständiger Themenwechsel. | Pytest | PASS |
| TEST-PRIV-001 | TEST | Zusätzliche Felder, Freitext, E-Mail-Form und Secret-Präfix werden abgewiesen. | Pytest | PASS |
| TEST-AGENT-001 | TEST | Alle drei öffentlichen Agentenvorlagen tragen wortgleich dieselbe Regel. | Pytest | PASS |

Konflikte: keine. Ein produktiver Host darf eine Empfehlung ausführen, Brainlehr selbst öffnet niemals einen Thread.
