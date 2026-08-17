# Kanonischer Lastenkatalog: Prompt-Invarianz

| ID | Anforderung | Gate |
|---|---|---|
| MUST-STAB-001 | Deterministischer Kern wertet neutrale, umgekehrte und gegensätzliche Ergebnisse aus. | TEST-STAB-001 |
| MUST-STAB-002 | Siegerwechsel oder wesentliche Rangdrift ist instabil, nie normale Empfehlung. | TEST-STAB-002 |
| MUST-CANARY-001 | Kleiner Context-Rot-Kanarienkorpus besitzt Sollantworten. | TEST-CANARY-001 |
| MUST-MEM-001 | Präferenz/früherer Gewinner ist keine Entscheidungsevidenz. | TEST-STAB-001 |
| MUST-ROLE-001 | Expertenrolle ersetzt nie Quelle, Rechnung oder Test. | TEST-STAB-001 |
| MUST-AGENT-001 | Claude, ChatGPT und Hermes referenzieren dieselben Regeln. | TEST-AGENT-001 |
| MUST-NOT-001 | Kein universeller Mehrfach-Prompt-Wrapper. | Codeprüfung |
| MUST-NOT-002 | Kein zweiter Memory-Dienst. | Codeprüfung |
| MUST-NOT-003 | Kein Laufzeitgate ohne gemessenen Prüfkorpus-Befund. | Codeprüfung |
| TEST-STAB-001 | Stabile/neutrale/reihenfolge-umgekehrte und präferenzfreie Fälle bestehen. | pytest |
| TEST-STAB-002 | Siegerwechsel schlägt fehl. | pytest |
| TEST-CANARY-001 | Kanarien-Sollantwort bleibt identisch. | pytest |
| TEST-AGENT-001 | Drei Agentenvorlagen tragen identische Regel. | pytest |

Konflikte werden hier ergänzt, nicht still aufgelöst.
