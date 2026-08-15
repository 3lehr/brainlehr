# Startprompt für die nächste Sitzung — 2026-08-15

Erzeugt 2026-08-15T00:20:00+0200 am Ende einer sehr langen Sitzung, für ein
frisches Kontextfenster. Alles unter „gemessen" ist mit Werkzeugen erhoben.
**Jede Zahl und jeder Werkzeugname hier wurde vor dem Aufschreiben geprüft**
(`L-cd1ef0` — genau dieser Prompt-Typ hat gestern zwei falsche Angaben
transportiert).

## Zuerst lesen

1. `docs/PLAN_GESAMT_2026-08-13.md` — Linien F, G, H, I und **die Sperren**.
2. `docs/adr/ADR-018-wirkungsvorrat-und-wirkung-null.md` — die Trennlinie, auf
   der alles andere steht.
3. `docs/SICHERHEITSFUNDE_2026-08-14.md` — fünf offene Funde mit Fundstelle.

**Der Satz, der in jeden Agentenauftrag gehört:** *„Sieht der Code anders aus
als hier beschrieben, halte dich an den Code und melde die Abweichung."*

## Lage in einem Absatz

brainlehr ist der Speicher mit Belegpflicht, das atelier die Werkbank,
`openlehr_X` sind die Domänen. Gestern entstanden: der Belegvertrag, der
Domänen-Import samt Menüpunkt, der Satzweg vom Baustein-Baum zum gesetzten
Blatt, die Satzwache, und die Umstellung des Dienstes auf eigenständig. Ein
Konsil aus drei unabhängigen Linsen hat die Begründung von ADR-012 gekippt und
fünf Sicherheitsfunde geliefert. **Zweige `brainlehr/b4-ausweis` und
`merge/daten-features` sind gepusht**; danach kam noch ein Plan-Commit.

## Was parallel laufen kann — vier Stränge, gemessen disjunkt

Geprüft: keine zwei Stränge fassen dieselbe Datei an.

| | Auftrag | Dateien | Modell |
|---|---|---|---|
| **A** | **H2** — die 12 Regeln in `classifier.py` an den Belegvertrag. Rot vor grün: eine Regelmenge ohne Fundstelle lädt dort heute klaglos | `openlehr/…/steuer/classifier.py` + Test | sonnet |
| **B** | **H3** — die Naht schließen: `ingest.py` liest `(\d{1,2})%`, geprüft wird erst in `api.py::_ocr_rate`. Gegenprobe: „9 % MwSt" muss Klärungsfall werden | `openlehr/…/steuer/ingest.py`, `api.py` + Test | sonnet |
| **C** | **O1** — der schwerste Sicherheitsfund: `entscheidungen.html:1546` setzt `p.a`, `p.p`, `p.d` roh per `innerHTML`. Maskieren **und** einen Test, der bei roher Ausgabe fällt | `entscheidungen.html`, `kern/raum_daten.py` (lesend) | sonnet |
| **D** | **Zwei Messungen, kein Bau** — (1) gibt es für Ausweise einen Widerruf? (2) lädt das CRDT-Rahmenwerk in einer Sandbox? Beide entscheiden über I4 bzw. G6 | nur lesend + eigenes Spike-Verzeichnis | sonnet |

**Nicht parallel dazu:** alles, was `kern/domaene.py` anfasst — siehe Sperre.

## Die Sperren, die zuerst zu lesen sind

- **Wirkung Null steht, BEVOR `kern/domaene.py` das erste Mal speichert.**
  Gemessen: `domaene.py` enthält heute **0** Treffer für `INSERT`, `UPDATE`,
  `commit()` — es persistiert nichts. Das Fenster ist offen und schließt sich
  mit dem ersten Schreibvorgang. Vorbild steht in `kern/regelpaket.py`
  (Import schreibt `norm_rang = NULL`).
- **Kein Bau an den beiden Dokumentausgaben**, solange die Ablösung nicht
  belegt ist — der Weg ist gemessen, die Ablösung nicht.
- **`H2` vor `H10`** (Export), **`H6`** (Fristenrechnung) vor `H5`s Sortierung.

## Was auf den Betreiber wartet

- **Ein Befehl mit seinem Passwort** (`G5`): eigener Systembenutzer, Bestand und
  Ausweisdatei auf `0600`. Vorlegen, nicht ausführen.
- Der **Name** für die Steuerdomäne; `openlehr` bleibt der alte Ort.
- Ob das neue Domänen-Repo **bei GitHub** liegt.
- **Urheberschaft** dessen, was im atelier gemeinsam mit dem Modell entsteht —
  vor der ersten Weitergabe an einen Menschen zu klären.

## Was gestern schiefging und sich wiederholen kann

- **Zwei Seiten parallel gebaut, eine musste den Vertrag raten** — die Swift-
  Seite nahm eine andere Antwortform an als die Python-Seite lieferte, und ihre
  Tests waren trotzdem grün, weil sie die eigene Übersetzung prüften. Wo zwei
  Agenten an einer Naht arbeiten: den Vertrag **vorher** festschreiben, als Test.
- **Ein Selbsttest, der nur Positiv- und Falschfall kennt, sieht den leeren Fall
  nicht.** `belegt("")` war `True`, weil `"" in text` immer wahr ist. Grenzwerte
  gehören dazu, nicht nur zwei Pole.
- **Eine Metapher taugt nicht als Begründung.** „Wir sind das Betriebssystem"
  war messbar falsch (`codesign`: adhoc, kein Entitlement).

## Arbeitsweise

- Arbeitsort `/Volumes/daten/Begod2026/brainlehr`, Zweig `brainlehr/b4-ausweis`.
  Für openlehr `/Volumes/daten/Begod2026/openlehr`.
- Testlauf brainlehr: `python3 -m pytest` (kein `.venv` vorhanden, gemessen).
  Swift: `app/bauen.sh` (zuletzt **202** Fälle grün).
  openlehr: `.venv/bin/python -m pytest`, **nie** System-Python.
- Kein `git add -A`, kein `git stash`. Committen mit expliziter Pfadliste.
- **Ein neuer Plan wird eine LINIE im Gesamtplan**, keine eigene Zählung ab 1.
