# STAND brainlehr — 2026-08-09T11:55:00+0200

## Der eine Befund, auf den heute drei unabhaengige Messungen zeigen

**Der Rueckstand im Abruf sitzt in der RANGFOLGE, nicht in der Menge und nicht in der Kappung.** 7 von 35 Zielen werden getroffen. Von den 28 verfehlten stehen **26 ueberhaupt nicht in der Kandidatenliste** — sie werden nicht abgeschnitten, sie werden nicht gefunden.

Drei Wege dorthin, alle heute, alle unabhaengig:
1. **S12** (`haken/mehrstufiger_abruf.py`): ein groesserer Kandidatenpool SENKTE die Trefferzahl (7/35 → 6/35). Schalter gebaut, gemessen, **Vorgabe AUS**.
2. **Sortierung**: der S12-Agent nannte den Sortierschluessel in `query()` als Ursache (Stichworttreffer gehen nicht ein). Diagnose stimmt fuer den Code, **Wirkung nicht** — testweise entfernt, gemessen, unveraendert 7/35. Zurueckgenommen.
3. **Deckelreihe** (`deckelreihe.py`, `runs/deckelreihe_2026-08-09.json`):

   | Deckel | LESSON | NODE | gesamt | Zeichen/Prompt |
   |---|---|---|---|---|
   | **3/2** | 4/15 | 3/20 | **7/35** | 4769 |
   | 5/3 | 4/15 | 3/20 | 7/35 | 7287 |
   | 7/5 | 4/15 | 3/20 | 7/35 | 11436 |
   | 10/7 | 4/15 | 3/20 | 7/35 | 16476 |
   | 15/10 | 5/15 | 4/20 | 9/35 | 23788 |

   Drei Stufen vervierfachen die Zeichenmenge und bringen **null** zusaetzliche Treffer. Deckel bleiben bei 3/2.

**Grenze aller drei:** sie messen ABRUF, nicht Antwortqualitaet. Ob ein Modell mit 23788 Zeichen schlechter antwortet als mit 4769, ist NICHT gemessen.

**Naechster Schritt:** herausfinden, warum die 26 nie ins Rennen kommen. Nicht mehr liefern, nicht anders kappen. Der Pruefkorpus paraphrasiert absichtlich — nur 6 von 28 Fehlschlaegen teilen ueberhaupt einen Wortstamm. Die einzige Stufe, die das adressieren koennte, ist Umformulierung durch ein Modell (S12 Stufe 3) — **nicht gebaut**, Kosten je Prompt sind eine Betreiberentscheidung.

## Wettbewerbslage — Behauptung geprueft, zur Haelfte gefallen

Knoten `/brainlehr/wettbewerbslage-2026-08-09-zwei-echte`, Lehre `L-db00ac`.

Deep Research urteilte **NICHT WIDERLEGT** fuer fertige Produkte. Beide tragenden Quellen habe ich selbst abgerufen, beide existieren:
- **TOKI**, [arXiv:2606.06240](https://arxiv.org/abs/2606.06240), 04.06.2026, 43 Seiten — bitemporale Operatoralgebra, drei Write-Time-Anomalien N1/N2/N3.
- **Governed Memory**, [arXiv:2603.17787](https://arxiv.org/abs/2603.17787), Maerz 2026, mit [Quelltext](https://github.com/personizeai/governed-memory).

**Meine Falsifikationsbedingung ist eingetreten.** Ich hatte geschrieben: „Punkt 6 (Selbstmessung im Betrieb) halte ich fuer den unwahrscheinlichsten. Faellt Punkt 6 irgendwo, war meine Behauptung falsch." Layer 4 von Governed Memory erkennt „ineffective or stale schema attributes" — funktionsgleich mit `normachsen.py`. Am Volltext gezielt nachgeprueft haelt die andere Haelfte: Layer 4 fuehrt **keinen** Erlasser, **keine** menschliche Zustimmung, **keinen** Belegrang, **keine** Fehlerkosten.

**Was uebrig bleibt und gemessen in Benutzung ist:** deontische Vorrangregel im Abrufpfad (`rangfolge.py:91`, `norm_score`) und Governance-Selbstmessung (`pruefer.py`).
**Was Behauptung ist, nicht Praxis:** `norm_art` 0 von 72 gefuellt · `kosten_wenn_falsch` in genau 1 Zeile (das fuellt sich im Betrieb, kein Fehler).
**Nachbau aus fertigen Teilen laut Bericht:** 8–12 Wochen. Kein Graben, aber auch keine Ausrede.

## Was aus TOKI folgt (gelesen, nicht ueberflogen)

- **N3 audit erasure** — betrifft uns nicht, `knowledge_versions` haelt 2025 Fassungen.
- **N2 belief-drift skew** — theoretisch beruehrt (mehrere MCP-Prozesse auf derselben WAL-DB, im Servercode selbst dokumentiert). **Bei uns ungemessen.**
- **N1 judge-replay inconsistency** — unsere Aufloesung ist deterministisch (`knowledge_lint._resolve_norm_conflict`, lex superior → specialis → posterior). **Aber gemessen: das Ergebnis wird NIRGENDS gespeichert**, keine Tabelle dafuer, kein Gegenstueck zu TOKIs `resolution_strategy_id`. Aufloesung passiert auf dem Lesepfad, jedes Mal neu — und `gilt_ab`/`norm_rang`/`scope` sind aenderbar. Damit gewinnt spaeter womoeglich eine andere Norm, ohne dass irgendwo steht, dass es je anders war. **Reichweite klein** (der Abrufpfad benutzt `rangfolge.norm_score`, nicht diese Funktion) — Befund, kein Bauauftrag.

## Herkunft: gemessen, teilbehoben, bewusst unvollstaendig

`actor` bei **359 von 382** Knoten des Arbeitsbestands (94 %) und `model` bei **315 von 382** (82 %) auf `unbekannt`. Gefunden beim Nachsehen, ob der neue Sichtbarkeitsmelder feuert — in genau dem Knoten, in dem ich zwei Minuten zuvor `actor`/`model` als Alleinstellung gegen die Konkurrenz aufgeschrieben hatte.

- **Ausgefuehrt:** `hub/.mcp.json` traegt jetzt `"env": {"BEGOD_KNOWLEDGE_ACTOR": "claude-code"}`. Wirkt **erst nach Serverneustart**.
- **Bewusst NICHT gesetzt:** `BEGOD_KNOWLEDGE_MODEL`. Ein fester Wert waere bei jedem Sonnet-Subagenten falsch, und eine falsche Herkunft ist schlechter als eine eingestandene Luecke. `pruefer.py` wird `model` weiter melden — **das ist der gewollte Zustand**, behoben wird er dadurch, dass der Aufrufer `model` mitgibt.
- **Das war schon bekannt:** `L-cb619e`, gemessen am **2026-08-05**, diagnostiziert als Konfigurationsfrage. Der Recall hat es erst heute hochgespuelt, nachdem ich es neu gefunden hatte. Einzelfall genau des Rueckstands oben.

## Herkunftsschranke hat im Betrieb gegriffen — erstmals echt

Beim Anlegen des Konfigurationsknotens wollte ich Rang 2 setzen. Abgewiesen: „norm_rang 1/2 verlangt fuer Hausnormen einen menschlichen Entscheider." Zu Recht — der Betreiber hatte „loese die Probleme" gesagt, nicht „dies ist Hausrecht". `anlass='betreiber'` war gesetzt und hat die Tuer **nicht** geoeffnet, weil `norm_entschieden_von` die Maschine traegt. Erster Fall ausserhalb der Tests.
**Was das nicht beweist:** Abdeckung. Die Schranke greift nur bei Rang 1/2. Rang 3–6 kann sich eine Maschine weiterhin selbst geben — und die sechs offenen Knoten unten sind genau Rang 4/6.

## Neu gebaut heute

`sichtbarkeit.py` (S2, meldet Speicherschreibvorgaenge im Chat; Matcher sind die elf schreibenden `mcp__knowledge__`-Werkzeuge, **nicht** `Edit|Write`; `--init` an SessionStart, sonst verschluckt jede Sitzung ihren ersten Schreibvorgang) · `rasterblick.py` (S1c, jede Rastersuche traegt Sitzung/Akteur/Modell/Bestand/Kontextfenster; feuerte beim naechsten Start von selbst: 13 Ergebnisdateien ohne Vermerk) · `haken/mehrstufiger_abruf.py` (S12, AUS) · `deckelreihe.py` · `pruefer.platzhalterfuellung` (neue Fehlklasse: Spalte formal gefuellt, sagt nichts — faellt durch `stumme_spalte`, weil die nur bei 100 % NULL meldet).

**Rot vor gruen beim Platzhalter-Pruefstein war meine eigene erste Fassung:** sie zaehlte ueber ALLE Knoten und haette geschwiegen (361 von 2022 = 17,9 %), weil der NASA-Import mit 1638 Zeilen einen echten Schreiber traegt. Erst mit `gattung='arbeitsbestand'` als Nenner: 94 %. Beide Zahlen stehen als Gegenprobe im Selbsttest.

## Papernetz — Entscheidung offen, Umfang groesser als gemeldet

Der Agent fand **2** Netze (56 Paper). Es sind **9 verschiedene, 297 Paper, 1624 Zitationskanten** mit Begruendungstext:

| Paper | Kanten | Ort |
|---:|---:|---|
| 63 | 517 | BEGOD Universum (P24 global) — **21× kopiert** |
| 61 | 512 | zwei aeltere Fassungen desselben (drobo-nas, fahrtenbuch) |
| 31 | 31 | `openlehr/docs/papers/` — Steuerrecht Fotograf |
| 29 | 6 | `hub/docs/papers/brainlehr/` — Nanopublications/Provenance |
| 25 | 3 | `setfunk/docs/papers/` — WebRTC |
| 12 | 28 | `afrika/docs/papers/lyrics-stt/` |
| 8 | 10 | `openlehr.worktrees/agents-curved-wolf/…/akademia-fortbildung-evidence/` |
| 7 | 5 | `fahrtenbuch/apps/openhood/docs/papers/` |

**Die Kanten sind wertvoller als die Paper** — 1624 BELEGTE Zitationsbeziehungen gegen unsere 5853 gerechneten Kanten.
**Vorschlag des Agenten:** Gattung `nachschlagewerk` (wie NASA-LLIS, aus dem Auto-Recall ausgeschlossen, ueber `nachschlagewerk_suche.py` erreichbar).
**Die Luecke, die er ehrlich benannt hat:** die Netzdateien tragen **nur Bibliografie, keine Abstracts**. Kernaussage/Methodik/Bewertung waeren leer oder erfunden.
**Der Agent nannte auch einen Pfad falsch** (`apps/openlehr/…` statt `openlehr/…`) — waere so ins `source`-Feld gewandert.
**Offen:** alle 9 oder nur die zwei? Den 21× kopierten einmal aufnehmen, nicht 21×. `source_tier` (primary/secondary, nur bei openlehr) deckt sich fast mit unserem Belegrang — eigener Schritt.

## Wartet auf Betreiber

- **sechs** Knoten Rang 4/6 ohne Entscheidung (alle buckeberg/Verwalterwahl) — das ist **keine Ja/Nein-Frage**, es braucht die Sachentscheidung
- abgelaufene Norm `/ops/buckeberg-anbieterabend-2026-08-05` (`gilt_bis 2026-08-06`) — die zweite abgelaufene ist Testmaterial und bleibt
- `_VERWAIST_shared-knowledge-2026-08-08` · fremde `.mcp.json` in `hub/.claude/worktrees/stoic-dubinsky-dd9d76` zeigt auf den entfernten Pfad
- acht MCP-Server brauchen Anmeldung (asana, atlassian, datadog, github, linear, notion, pagerduty, slack) — nur interaktiv, ueber `claude mcp` oder die claude.ai-Verbindungen
- `docs/CHATGPT_EINKLINKEN_2026-08-09.md` — Weg A (Prompt) fertig; Weg B (echte Verbindung) beschrieben, **nicht gebaut**: braucht HTTP-Bruecke + Tunnel, und dann liest ein Dritter Steuerunterlagen und Verwalterwahl mit
- `docs/PRUEFAUFTRAG_DEEP_RESEARCH_2026-08-09.md` — ausgefuehrt, Ergebnis oben

## Prozesse und Neustart

**Der MCP-Server laeuft NICHT eigenstaendig** — jede Sitzung startet ihren eigenen Kindprozess, er stirbt mit ihr. Gemessen 2026-08-09T11:50: vier Instanzen von `knowledge_mcp_server.py` (PID 5173 unter `hermes-agent`, **1 Tag alt**; 61742 diese Sitzung; 81834 und 97206 je ~15 h 50 unter anderen claude-code-Sitzungen). **Nur 61742 hielt Schreibhandles** — dessen Neustart gibt die Sperre frei, kein `kill` noetig. Das WAL stand bei 20 MB.
`PID 11397` ist **kein** MCP-Server, sondern der Wissensgraph auf Port 8766 aus `.claude/launch.json` (nur lesend).

## Faellig nach Fallzahl, nicht nach Datum

`recall_log.jsonl.nulllinie` und `bereinigung_log.jsonl.nulllinie` sind gesetzt (erster Lauf misst die Nulllinie selbst, an seinem Ort). `pruefer.faellige_auswertung` meldet bei +200 bzw. +500 Faellen.

## Gegenproben

Alle zwoelf vermerkt, **drei widersprechen sich selbst** — `ab_vergleich_abruf` (Bestand wuchs 1971→1974 waehrend des A/B-Laufs), `pruefkorpus_v3_erweitert` und `_lauf_B` (beide abgebrochen). **Nicht als Beleg verwenden.**

## Aelteres, weiter gueltig

Repo `github.com/3lehr/brainlehr`, **PRIVATE**, Entscheidung `d6f0dd0f`: nie oeffentlich schalten, `knowledge.db` liegt in 31 Commits der Historie. Eine Veroeffentlichung entsteht als NEUES Repo mit frischer Historie.
Uebergangsverweis `hub/shared-knowledge` entfernt (neun Nutzer, gefunden durch Abklemmen statt Suchen, `L-5af2e2`; dabei die stille `BEGOD_ROOT`-Regression gefunden).
BSI: Sync hatte das Regelwerk zerstoert, wiederhergestellt, Einbruchssperre in `hub c7db4f4b8`, 951 Controls, alle drei ABSOLUT-Hard-Stops unveraendert.
Offene Annahme `A-d93330`: vier Spalten fuehren eine Identitaet als freien Text. Traegt, solange nur Agenten darin stehen; teurer ab dem ersten menschlichen Namen.
Testlauf im Arbeitsbaum: 646 gruen, 11 rot — dieselben elf (fehlende `knowledge.db` im Arbeitsbaum, Umlautfaltung, instructions).
