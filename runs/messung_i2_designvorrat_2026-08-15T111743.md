# Messung I2 — Designvorrat als Daten, kanonische Quelle

Stand 2026-08-15T11:17:43+0200. Nur Messung, nichts umgebaut, nichts gelöscht.
Root aller Zählungen: `/Volumes/daten/Begod2026` (Verbund-Root, `find .`).

## 1. Wieviele Kopien, je Datei, nach Sorte

### `konsil-design-guide.md`

Kommando: `find . -type f -name "konsil-design-guide.md"` → **53** Treffer.
`find . -type l -name "konsil-design-guide.md"` → **0** Symlinks.

| Sorte | Zahl | Kommando |
|---|---|---|
| echte Repo-Kopien (Top-Level) | 20 | `grep -vE '\.claude/worktrees/\|^\./(archive\|.*_stale_)'` |
| Arbeitsbaum-Kopien (`.claude/worktrees/`) | 31 | `grep -c '\.claude/worktrees/'` |
| Archiv/Stale-Verzeichnisse | 2 | `archive/openlehr_desktop_2026-07-28`, `openlehr_stale_2026-07-22` |
| Sicherungen (`.bak`,`~`,`.orig`) | 0 | `find . -iname 'konsil-design-guide.md*' -not -name 'konsil-design-guide.md'` → leer |

20+31+2 = 53. Stimmt.

Abweichung zur Vorgabe im Auftrag (51): heute anders gezählt, **53**. Nicht
nachvollzogen woher 51 kam — vermutlich vor Anlage eines der Arbeitsbäume
gezählt. `brainlehr` selbst hat **keine** Kopie (0 Treffer unter `./brainlehr`).

### `aka-design-guide.json`

Kommando: `find . -type f -name "aka-design-guide.json"` → **36** Treffer.
`find . -type l -name "aka-design-guide.json"` → **0** Symlinks.

| Sorte | Zahl |
|---|---|
| echte Repo-Kopien (Top-Level) | 10 |
| Arbeitsbaum-Kopien (`.claude/worktrees/` oder `.worktrees/`) | 24 |
| Archiv/Stale-Verzeichnisse | 2 |
| Sicherungen | 0 (aber 27× `aka-design-guide.json.processed.json` — Postfach-Verarbeitungsmarker, andere Sorte, nicht mitgezählt) |

10+24+2 = 36. Stimmt. Die 36 aus dem Auftrag (als "nicht bestätigt" markiert)
ist damit **bestätigt** — mit Sortentrennung, die vorher fehlte.

## 2. Inhaltlich gleich oder verschieden — Prüfsummen

### `konsil-design-guide.md`

`while read f; do md5 -q "$f"; done | sort | uniq -c`:

```
53 ff24804bca8a382dfcfc203187e87f82
```

**Alle 53 identisch.** Reines Verteilungsproblem, keine Divergenz. 18 von 19
Top-Level-Repos tragen den Commit vom selben Zeitstempel (`2026-02-20
11:14:35 +0100`) — ein einziger Fan-out-Vorgang in ein Repo pro Stunde,
`begem` hat die Datei nur ungetrackt liegen, `hub`/`wpdrop` haben sie später
neu committet (Inhalt trotzdem gleich).

### `aka-design-guide.json`

```
33 7e4d292e1e0909b48272cbad75612465   (v1.0.0, "LZKBW"-Farbschema)
 3 e9f619d530d6d6dc544a5c66561efed6   (v3.2.0, "AKA Grün"-Farbschema)
```

**Divergenzproblem, kein Verteilungsproblem.** Die 3 abweichenden Dateien
liegen unter `begod/knowledge/apps/akademia/aka-design-guide.json` in:
`design-lab/`, `openlehr.worktrees/agents-curved-wolf/`,
`openlehr.worktrees/agents-curved-wolf/builds/universe/AKA2026-Universe-v2026.03.09/`.
`diff` bestätigt: komplett andere Farbwerte, andere Version, andere
Metadaten (v3.2.0 trägt zusätzlich `pdf_masszahlen` — Border-Radius-System,
Typo-Skala aus PyMuPDF-Audit; v1.0.0 kennt das nicht).

Die 33 identischen Kopien liegen alle unter `X-postfach/.../aka-design-guide.json`
— Postfach-Archiv, nie aktualisiert, tragen die **veraltete** v1.0.0.

## 3. Welche Datei ist kanonisch

### `konsil-design-guide.md`
Frage stellt sich nicht in der scharfen Form — alle 53 sind byte-identisch,
also ist jede Kopie inhaltlich die kanonische. Offen bleibt nur, **welche
Kopie die einzige bleiben soll**, nicht welche recht hat.

### `aka-design-guide.json` — die Kriterien gehen NICHT auseinander, sie zeigen alle auf dieselbe Datei

- **Vom Token-Erzeuger gelesen:** Der Erzeuger erwartet
  `<REPO_ROOT>/begod/knowledge/apps/akademia/aka-design-guide.json`
  (`design-lab/begod/scripts/generate_design_tokens.py:21-23`, identische
  Konstante auch in der älteren `begem`-Fassung). In `begem` selbst
  **existiert diese Datei gar nicht** — nur eine Postfach-Archivkopie mit
  v1.0.0 liegt dort, nicht am erwarteten Pfad. Nur in `design-lab` liegt die
  Datei tatsächlich am vom Skript erwarteten Ort.
- **Git-verfolgt gegenüber lokal:** `git -C design-lab ls-files
  begod/knowledge/apps/akademia/aka-design-guide.json` → getrackt, `git
  status --short` → sauber, `git log -1` → `836c44b`, 2026-03-06. **`begem`
  ist gar kein Git-Repo** (`git -C begem rev-parse --is-inside-work-tree` →
  `fatal: not a git repository`) — dort ist ohnehin nichts versioniert.
- **Jüngste Fassung:** v3.2.0 (design-lab-Gruppe) > v1.0.0
  (Postfach-Archiv-Gruppe) — im Dateiinhalt selbst ausgewiesen
  (`meta.version`, `meta.aktualisiert: "2026-03-06"`).
- **Zuständiges Repo:** `design-lab` ist zugleich das Repo mit der
  **aktuellen, git-getrackten** Fassung des Erzeugerskripts selbst
  (621 Zeilen, `git log -1` → 2026-03-05) — die Fassung in `begem`
  (228 Zeilen) ist die ältere, kennt weder den vierten Erzeuger noch die
  App-Deploy-Logik.

**Befund: `design-lab/begod/knowledge/apps/akademia/aka-design-guide.json`
ist die kanonische Datei — Pfad-Übereinstimmung mit dem Erzeuger, Git-Status,
Alter und Vollständigkeit zeigen übereinstimmend dorthin.** Das im Auftrag
genannte `begem/begod/scripts/generate_design_tokens.py` ist die veraltete,
ungetrackte Nebenfassung — nicht die maßgebliche.

## 4. Billigste Bauform gegen künftige Vervielfachung

Geprüfte Kandidaten:

- **Eine Quelle + erzeugte Kopien:** passt für die 33 Postfach-Kopien nicht —
  das sind fremde Repos (`openlehr`, `hub`, `buckeberg`, `begem`, …), dort darf
  laut Verbundregel nicht committet werden. Passt nur innerhalb `design-lab`
  selbst (Quelle → `generated/`, bereits so gebaut).
- **Symlinks:** scheitert an Repo-Grenzen aus demselben Grund — ein Symlink
  über Repo-Grenzen hinweg ist kein Git-Objekt, das ein fremdes Repo tragen
  kann, ohne dass jemand dort committet.
- **Eine Prüfung, die Abweichung meldet, ohne zu vereinheitlichen:** einzige
  Bauform, die ohne Schreibzugriff auf fremde Repos auskommt. Ein Melder, der
  `md5` über alle Fundstellen bildet und bei mehr als einer Prüfsummen-Gruppe
  meldet (wie hier von Hand gemacht), deckt genau den Fall ab, der heute
  unbemerkt blieb: v1.0.0 vs. v3.2.0 seit mindestens 2026-03-06, niemandem
  aufgefallen.

**Vorschlag, ungebaut:** dritte Bauform — ein Melder in `brainlehr/melder/`,
der beide Dateinamen im Verbund sucht (Ausschluss `.claude/worktrees/`,
`archive/`, `*_stale_*`), Prüfsummen gruppiert und bei >1 Gruppe meldet, mit
der design-lab-Fassung als Referenzwert. Kein Umbau an den 20+10 Fundstellen
selbst — die liegen in fremden Repos.

## 5. Fehlender LaTeX-Erzeuger — Zeilenschätzung

`grep -rli "generate_latex" --include="*.py" .` (Vendor-Treffer in
`simulatoren/.../pygments/` ausgenommen, projektfremd) → **0** echte Treffer
im ganzen Verbund.

Gemessene Vergleichswerte, kanonische Fassung (`design-lab`, 621 Zeilen
gesamt):

| Funktion | Zeilen |
|---|---|
| `generate_flutter` | 116 |
| `generate_css` | 103 |
| `generate_scss` | 63 |
| `generate_raumstation_json` (vierter Erzeuger, existiert bereits — JSON, nicht LaTeX) | 58 |

Zum Vergleich die veraltete `begem`-Fassung (228 Zeilen gesamt, ohne
`pdf_masszahlen`-Block):

| Funktion | Zeilen |
|---|---|
| `generate_flutter` | 72 |
| `generate_css` | 45 |
| `generate_scss` | 21 |

Ein LaTeX-Erzeuger (`\definecolor`, Längen für Radius/Abstand,
`\setmainfont`) ist strukturell dem SCSS-/CSS-Erzeuger am nächsten
(Variablen-Dump, kein Klassenkörper wie bei Flutter). Grundlage für eine
Schätzung, keine Messung: zwischen `generate_scss` (63, kanonisch) und
`generate_css` (103, kanonisch) — grob 60–110 Zeilen, wenn er dieselben
`pdf_masszahlen`-Blöcke (Radius, Typo-Skala) mitträgt wie die aktuelle
CSS/SCSS-Fassung.

## GRENZE

- Nur gelesen, außerhalb von `brainlehr` nichts geändert, nichts committet.
- Keine Prüfsummen-Vollabdeckung über alle 27 `.processed.json`-Marker
  gebildet — andere Dateiendung, nicht Gegenstand des Auftrags.
- `openlehr.worktrees/` (ohne Punkt, kein `.claude/worktrees/`) ist ein
  eigenständiger Fund — vermutlich ein weiterer Arbeitsbaum-Mechanismus
  neben `.claude/worktrees/`, hier nur als Fundort gezählt (Kategorie
  Arbeitsbaum-Kopien), nicht strukturell untersucht.
- Kein Melder gebaut, kein Skript geändert — Punkt 4 ist ein geprüfter
  Vorschlag, keine Umsetzung.
