# Startprompt — openlehr_einzelunternehmer umsetzen

*Für ein frisches Kontextfenster. Alles ab „ANFANG DES PROMPTS" kopieren.*
*Erzeugt 2026-08-16T09:30:56+0200.*

---

## ANFANG DES PROMPTS

Lies zuerst `~/.claude/CLAUDE.md`, dann `/Volumes/daten/Begod2026/brainlehr/CLAUDE.md`.
Danach diese vier Wissensknoten — sie tragen die Entscheidungen, auf denen alles
Folgende steht:

    806132da   der Name und seine Regel
    6c8c9a84   ADR-007: zwei Schichten — brainlehr trägt, openlehr wirkt
    bf4c87c9   openlehr enthält ZWEI Domänen und einen zweiten Kern (gemessen)
    73f8a1c0   legacy gilt als ungeprüft (Rang-1-Weisung vom 2026-08-16,
               ergangen an fahrtenbuch_legacy — die Übertragung auf
               openlehr_legacy ist eine Ableitung, keine wörtliche Weisung)

Abrufen mit `knowledge_read <id>`. Sie kosten zusammen wenige Minuten und ersparen
die drei Fehler, die diese Aufgabe bisher gekostet hat.

### Was gebaut wird

**`openlehr_einzelunternehmer`** — die erste benannte Domäneninstanz auf brainlehr:
Steuerchaos für Selbständige. Der Name ist eine Betreiberentscheidung vom 2026-08-16
(wörtlich: *„lass es uns openlehr_einzelunternehmer nennen ohne chaos!"*) und ersetzt
`openchaos_einzelunternehmer`. Die Regel dahinter: `openlehr_<Lage>` — die Schicht
trägt den Namen, die Lage hängt an. Die Schwägerin bekäme `openlehr_schulkorrektor`.

### Die Lage, gemessen — nicht aus älteren Prompts übernehmen

**Der Ort hat sich geändert, und ältere Startprompts nennen ihn falsch.**
`/Volumes/daten/Begod2026/openlehr` **existiert nicht mehr.** Das Verzeichnis heißt
seit Commit `d5c24182` **`openlehr_legacy`** — die Commit-Nachricht sagt, warum:
*„openlehr wird openlehr_legacy — Blaupause statt Werkbank"*. Zweig
`merge/daten-features`, `origin` zeigt auf ein lokales Desktop-Verzeichnis.

Daneben liegt `openlehr_stale_2026-07-22/` — ein noch älterer Stand. Nicht anfassen.

**Was in `openlehr_legacy` steckt** (Erhebung 2026-08-15 an Commit `21b00d8f`,
Knoten `bf4c87c9`, per `create_app()` gezählt statt gegrept):

| | |
|---|---|
| Endpunkte gesamt | **329** |
| davon Steuer (`/v1/steuer`) | 189, aber nur **102** sind wirklich Steuerfachlichkeit |
| **Entwicklungsassistent** (`/v1/ide`, plan_coach, orchestrator, goals, roadmap, konsile) | **56** — eine ZWEITE Domäne nach ADR-013 |
| Kern (Ausweis, Rahmen, Navigation, Dienstaufsicht, Modellzugänge) | 78 |
| Bestandteil | 93 |
| `daemon/steuer/` | 130 Module, 43 787 Zeilen |

**Die Falle daran, und sie ist teuer:** Wer „Steuer gegen Rest" trennt, schiebt den
Entwicklungsassistenten versehentlich ins atelier. Er ist eine eigene Domäne, kein
Kern.

### Die bindende Auflage: kopieren ist verboten

**`openlehr_legacy` ist Blaupause, nicht Vorlage zum Abschreiben** (H12) — das sagt
schon die Commit-Nachricht der Umbenennung. Dazu kommt die Rang-1-Weisung vom
2026-08-16 (`73f8a1c0`). **Sie erging wörtlich an `fahrtenbuch_legacy`; dass sie hier
ebenso gilt, ist eine Ableitung** — der Betreiber hat sie für openlehr nicht eigens
ausgesprochen. Die Begründung trägt aber gleichermaßen:

> Jede Regel, Schwelle, Formel oder Verhaltensweise aus dem Bestand trägt beim
> Übernehmen `status: unbelegt`. Sie wird `belegt`, sobald im Neubau ein eigener
> Test existiert, der gegen eine bewusst falsche Fassung ROT war.

**Übernommen werden nur DATEN** — Beispielbelege, Grenzwerte, aufgezeichnete Dialoge.
**Nie Testlogik**, sonst wandert der blinde Fleck mit. ADRs und Feldbefunde sind
Begründung, nicht Beweis.

Grund, in einem Satz: 4 575 grüne Tests im Bestand belegen nur, dass der Code tut, was
jemand aufgeschrieben hat — nicht, dass es richtig ist.

### Was schon entschieden ist und nicht neu verhandelt wird

- **Mandant = Unternehmen** (`456dea78`). Die DB-Datei ist die Mandantengrenze —
  mehrere Firmen heißen mehrere SQLite-Dateien, niemals Row-Level-Tenancy.
- **Lizenzierte Lokal-Installation, kein SaaS** (`96c1198c`). Gesperrt durch OL-E1
  (kein Cloud-Outbound) und OL-E3 (kein öffentlich erreichbarer Code) — eine harte
  Klausel, keine offene Lücke.
- **Der Kern existiert doppelt**: Ausweis, Rahmen, Navigation, Dienstaufsicht und
  Modellzugänge sind in openlehr gebaut UND im atelier. Die 78 Kern-Endpunkte sind
  die genaueste Anforderungsliste, die das atelier je bekommen wird — sie werden
  **gelesen**, nicht kopiert.

### Fallen beim Arbeiten, alle gemessen (Knoten `ae1356b1`)

- `.venv/bin/python` aufrufen, **nie** `python3` — sonst 85 Sammelfehler, die wie
  echte Fehler aussehen.
- Der Steuer-Testbaum liegt in der Repo-Wurzel unter `tests/steuer`, **nicht** unter
  `apps/openlehr/`.
- Zwei gleichzeitige `pytest`-Läufe im selben Repo enden mit Abbruchcode 144.
- Zahlen aus Ausgaben nie durch `tail` abschneiden.
- `apps/openlehr/macos/` ist eine tote Snapshot-Referenz; der lebende macOS-Klient
  ist `apps/openlehr/macshell/` (Knoten `6e22ac48`).

### Betriebslage

openlehr enthält **ausschließlich Testdaten**, ein Nutzbetrieb existiert nicht
(`f6d00767`). „Das System wäre zwischenzeitlich unbenutzbar" ist **kein** Argument.
Löschen, umbauen, neu aufsetzen ist frei.

### Der Satz, der in jeden Agentenauftrag gehört

> „Sieht der Code anders aus als hier beschrieben, halte dich an den Code und melde
> die Abweichung."

Er hat am 2026-08-15 fünfmal verhindert, dass ein Agent bereits Gebautes noch einmal
baut (`L-229bb2`).

### Reihenfolge

1. **Existenzprobe.** Gibt es `openlehr_einzelunternehmer` schon irgendwo?
   `git log --all --grep`, dazu
   `python3 /Volumes/daten/Begod2026/hub/scripts/symbolindex.py einzelunternehmer`.
   Gesucht wird nach der **Sache**, nicht nach dem Namen.
2. **Plan schreiben**, ins Repo, mit gemessenem Ist-Stand, verworfenen Wegen,
   bindender Reihenfolge, was NICHT getan wird, und Erfolgsmaß. Ohne Plan wird nicht
   gebaut — das ist eine Betreiberanweisung vom 2026-08-12.
3. Erst dann bauen.

### Was dieser Faden NICHT tut

Alles zu brainlehr selbst — Kanalgüte, Landkarten, Wissensablage — läuft in einem
anderen Fenster. Nicht doppelt anfassen.

## ENDE DES PROMPTS
