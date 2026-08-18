# Was „fertig bauen" wirklich verlangt — 44 Lücken, 9 Entscheidungen, 5 Punkte ohne Rückfrage

Stand: 2026-08-18T19:30:00+0200 · Grundlage: `runs/bau_gates_block_{e1,f1,r1,rest}.json`,
Knoten `f0619359` · Katalog: `docs/REQUIREMENTS_BRAINLEHR.md` (14/56 belegt)

Vier Agenten haben alle offenen Produktgates einzeln gegen den Code gehalten.
Ergebnis: **44 geprüft, 0 belegbar.** Kein einziges Gate ist offen, weil ein
Test fehlt — es fehlt der geprüfte Gegenstand.

Damit ist „fertig bauen" keine Testliste. Es ist eine Reihe von
Produktentscheidungen. Diese Vorlage bündelt sie.

## Teil 1 — Fünf Punkte, die KEINE Entscheidung brauchen

Sie betreffen den Kern (Zielbild A, `BDW-P05`), sind aus eigener Kraft baubar
und gehören unabhängig von jeder Enterprise-Frage zu brainlehr.

| Gate | Was fehlt | Aufwand |
|---|---|---|
| `BDW-P04` | Abstention- und Aktionsgates. Vorhanden sind Treffer- und Falschmeldequote (`kern/kanalguete_messung.py`) — **2 von 4**. | mittel |
| `BDW-P05` | Ein Test auf die 95-%-Schwelle: Aussage, Quelle, Status, Gültigkeit in einem Abruf. | mittel |
| `BDW-F05` | Benchmark gegen eine **No-Memory-Baseline**. `tests/test_abrufwirkung.py` ist grün, misst aber Rückläufe — nicht dasselbe. | mittel |
| `BDW-R01` | Boundary-Prüfung: Governance zu brainlehr, Fachlogik zu openlehr. | klein |
| `BDW-R05` | Ein lokaler MCP-Lauf mit austauschbarem Modellpfad. | klein |

**Das ist die eigentliche Arbeitsliste.** Sie macht aus 14/56 realistisch
19/56 — und sie stärkt genau die Hälfte, die brainlehr von einem Speicher
unterscheidet: dass er seine eigene Güte misst.

## Teil 2 — Neun Entscheidungen, die beim Betreiber liegen

Jede Zeile ist eine Ja/Nein-Frage. Ein Nein ist eine vollwertige Antwort und
räumt den Katalog auf: die betroffenen Gates werden dann auf `DEFERRED`
gesetzt, nicht offen gelassen.

| # | Frage | Betroffene Gates | Preis eines Ja |
|---|---|---|---|
| 1 | Gibt es **Mandanten**? | `E03`, `E06`, `E19` | Die Achse fehlt im Datenmodell — das ist ein Schema-Umbau, kein Feature. |
| 2 | Gibt es eine **Unternehmensanmeldung** (IdP, SSO, SCIM)? | `E01`, `E04`, `E05`, `F10`, `U07` | `kern/ausweis.py` ist lokale scrypt-Identität; ein IdP-Anschluss ist ein eigenes Vorhaben. |
| 3 | Gibt es **zwei Fassungen** (lokal und Enterprise) mit einem Kern? | `C02`, `C03`, `P01`, `P03`, `E08`, `E17`, `E21` | Profilmechanik, Betriebsprofile, SLI/SLO je Profil. |
| 4 | Gibt es **Aufbewahrungsfristen und Löschautomatik**? | `E12`, `E13`, `E14`, `E15`, `E16` | Fristen je Datenklasse, Legal Hold, isolierter Restore-Test mit RPO/RTO. |
| 5 | Gibt es **kundenseitig kontrollierte Schlüssel**? | `E07`, `E09` | Verschlüsselung ruhend für Daten, Index UND Backup; Rotation, Widerruf, Restore. |
| 6 | Gibt es eine **Ausgangskontrolle** (DLP, SIEM, Exportprüfung)? | `E11`, `E20`, `U02`, `U03`, `U05`, `U08` | Default-Deny an allen Ausgängen, Auditstrom nach außen. |
| 7 | Werden **Gedächtnisarten getrennt** (episodisch, semantisch, prozedural)? | `F01`, `F02`, `F03` | Drei Speicherarten mit eigenem Schreib-, Korrektur- und Löschpfad. |
| 8 | Gibt es **Connectoren** zu fremden Dokumentquellen? | `F08`, `U04` | Referenz + Prüfsumme + Provenienz statt Dokumentkopie; Allowlist. |
| 9 | Gibt es **Föderation** über mehrere Instanzen? | `F11` | Deterministische Konvergenz, Offline-Replikation, Widerruf. |

## Teil 3 — Was diese Vorlage NICHT sagt

Sie sagt nicht, dass die neun Fragen mit Nein zu beantworten wären. Sie sagt,
dass sie **offen** sind und der Katalog sie als entschieden führt (`DECIDED`)
— das ist der eigentliche Widerspruch. Die Entscheidungsmatrix vom 2026-08-17
hat 53 Fragen beantwortet, aber der Preis stand nicht dabei.

Sie sagt auch nichts über Dringlichkeit. Nach der Hausregel ist der Bestand
kein Argument: Was zählt, ist die **Reihenfolge** — was blockiert den nächsten
Schritt, was entwertet spätere Arbeit, was ist später nur teurer zu haben.
Nach diesem Maßstab steht Frage 1 vorn: Eine Mandantenachse nachträglich in
ein gewachsenes Schema zu ziehen kostet mehr als jede andere Zeile hier, und
sie ist Voraussetzung für 2, 3 und 6.

## Anhang — zwei abgewehrte Beinahefehler

Beide wären ohne die ausdrückliche Auflage im Agentenauftrag („Ein Test, der
etwas ANDERES prüft als das AC, ist keine Deckung") als Beleg durchgegangen:

- `BDW-F05`: `tests/test_abrufwirkung.py` ist grün und misst Rückläufe und
  Signalwirkung — das AC verlangt eine No-Memory-Baseline samt Toolwahl.
- `BDW-P04`: `kern/kanalguete_messung.py` deckt Treffer- und Falschmeldequote.
  Zwei von vier geforderten Gatearten ist keine Deckung.

Ein grüner Test am falschen Gegenstand ist teurer als ein fehlender: er liest
sich wie ein Beleg.
