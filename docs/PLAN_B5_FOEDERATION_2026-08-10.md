# Plan B5 — Instanzkennung und Vertrauensliste

**Angelegt:** 2026-08-10T07:00:00+0200
**Anlass:** Betreiber: „könnte eine fremde brainlehr instanz dann auch einen fremden
einbürgern (samt seinem wissen) aus einem anderen staat […] visa vergeben, dann zb mit
arbeitsverbot. oder etwas wie ein asylverfahren?" — danach: „planen dann umsetzen!"
**Entwurf:** Knoten `7c8df4e7` · **Voraussetzung:** ADR-002 (B4)

---

## 1. Ist-Stand, gemessen

| | Stand |
|---|---|
| `PRAGMA application_id` | **1112689746** = ASCII „BRLR" |
| dieselbe Kennung im Quelltext | **kein einziger Treffer** (grep über `*.py`, `*.sql`) |
| `knowledge_config` | genau zwei Zeilen: `embed_model`, `herkunftsmodus` |
| `PRAGMA user_version` | 1 |

**Korrektur an Knoten `7c8df4e7`:** Dort steht, `application_id` sei „der Anfang" der
Instanzkennung. Das ist falsch, und der Unterschied ist der ganze Punkt:

> `application_id` ist eine **Gattungs**kennung — sie sagt „diese Datei ist eine
> brainlehr-Datenbank". Jeder Klon trägt dieselbe. Eine **Instanz**kennung sagt
> „diese Datei ist DIESE brainlehr-Instanz", und genau die fehlt.

Ohne sie ist der Satz „ein Ausweis aus Instanz B" nicht formulierbar — es gibt kein B.

---

## 2. Was gebaut wird

**B5.1 — Instanzkennung.** Eine Zufallskennung plus ein sprechender Name, beides in
`knowledge_config`, beim ersten Lauf erzeugt und danach unveränderlich.

**B5.2 — Vertrauensliste.** Welche fremde Instanz wird anerkannt, und **mit welcher
Rolle höchstens**. Ausdrücklich, nicht abgeleitet.

Mehr nicht. Übernahme von Wissen (B5.3) und Asylverfahren (B5.4) bleiben ungebaut —
sie brauchen B5.1/B5.2 als Grundlage, und ohne eine zweite Instanz im Betrieb wäre
beides ungenutzte Angriffsfläche (dieselbe Begründung, mit der Mandat und Rotation
vertagt werden sollten — dort war sie falsch, weil das Datenmodell davon abhing; hier
ist sie richtig, weil es das nicht tut).

---

## 3. Die drei Regeln, die den Bau bestimmen

**Vertrauen ist nicht transitiv.** Traut A der Instanz B und B der Instanz C, dann
traut A **nicht** C. Sonst ist die schwächste Instanz der Zugang zu allen — und
niemand merkt es, weil jede einzelne Beziehung vernünftig aussieht. Technisch: die
Vertrauensliste kennt nur **direkte** Einträge, es gibt keine Auflösung über Dritte.

**Erreichbarkeit ist kein Vertrauen.** „Ich kann B erreichen" heißt nicht „ich traue
B". Ein Eintrag entsteht nur durch ausdrückliche Aufnahme, nie durch einen Kontakt.

**Die Vertrauensliste ist eine Obergrenze, kein Rechteverleih.** Der Eintrag sagt
*höchstens* — was ein einzelner fremder Ausweis dann wirklich darf, ist der Schnitt
aus seinen eigenen Rollen und dieser Grenze. Dieselbe Bauform wie beim Mandat, aus
demselben Grund: eine Obergrenze kann nur wegnehmen.

---

## 4. Wo die Dinge liegen — und warum nicht anders

**Instanzkennung in `knowledge_config`**, nicht in einer Datei: Sie beschreibt *diese
Datenbank*. Läge sie daneben, wären Kopie und Kennung trennbar, und ein Backup hieße
plötzlich anders als sein Original.

**Vertrauensliste neben der Ausweisdatei**, nicht in der Datenbank: Wer die Datenbank
öffnen kann, änderte sonst die Vertrauensliste (`L-bd1562`). Vertrauen ist eine
Zugangsentscheidung und gehört dorthin, wo der Zugang entschieden wird — dieselbe
Begründung wie bei den Ausweisen in ADR-002.

**Der Klon-Fall, ehrlich:** Eine Kennung wandert beim Kopieren mit. Für ein **Backup**
ist das richtig (es *ist* dieselbe Instanz), für eine **Abspaltung** falsch (eine
zweite Abteilung ist eine andere Instanz). Automatisch unterscheiden lässt sich das
nicht — die Datei sieht in beiden Fällen gleich aus. Darum ein ausdrücklicher Befehl
`--neue-instanz`, der die Kennung neu würfelt, und eine Warnung, dass er die alte
Herkunft kappt.

---

## 5. Verworfene Wege

**`application_id` umwidmen.** Naheliegend, weil sie schon da ist — und falsch: sie
ist per SQLite-Konvention eine Dateityp-Kennung. Wer sie je Instanz ändert, macht die
Gattungserkennung kaputt, die sie leistet.

**Instanzkennung aus dem Rechnernamen ableiten.** Kostenlos und instabil: Rechner
werden umbenannt, Instanzen wandern, zwei Instanzen auf einem Rechner kollidieren.

**Vertrauen über Zertifikate / eine Wurzelinstanz.** Der saubere Weg für viele
Teilnehmer — und hier Überbau: es gibt eine Instanz. Eine Liste mit Namen kostet
zwanzig Zeilen, eine Zertifikatskette kostet einen Betrieb. Nachziehbar, sobald ein
dritter Teilnehmer erscheint.

**Vertrauen automatisch bei erstem Kontakt.** Genau der Fehler aus Regel 2.

---

## 6. Was bewusst nicht getan wird

- **Keine Übernahme von Wissen** (B5.3) und **kein Asylverfahren** (B5.4).
- **Kein Netzwerkverkehr.** B5 macht Föderation *aussagbar*, nicht *benutzbar* —
  dafür fehlt weiterhin ADR-001 (HTTP).
- **Keine Sperrliste** (welcher Instanz wird ausdrücklich *nicht* getraut). Solange
  die Liste eine Positivliste ist, ist Nichteintrag bereits die Ablehnung.

---

## 7. Proben — jede muss vorher rot sein

| Nr. | Probe | Erwartung |
|---|---|---|
| F1 | zweimal lesen | dieselbe Kennung |
| F2 | Kennung existiert nicht | wird erzeugt und bleibt |
| F3 | Kennung von außen überschreiben | abgewiesen, unveränderlich |
| F4 | `--neue-instanz` | neue Kennung, alte im Protokoll vermerkt |
| F5 | fremde Instanz **nicht** in der Liste | kein Vertrauen (Vorgabe deny) |
| F6 | fremde Instanz mit Obergrenze `leser`, Ausweis trägt `schreiber` | wirksam nur `leser` |
| F7 | fremde Instanz mit Obergrenze `schreiber`, Ausweis trägt `leser` | wirksam nur `leser` — die Grenze verleiht nichts |
| F8 | A traut B, B traut C, C fragt A | **kein Vertrauen** (nicht transitiv) |
| F9 | eigene Kennung in der Vertrauensliste | abgewiesen — man bürgt nicht für sich selbst |
| F10 | Vertrauensdatei mit zu weiten Rechten | ignoriert, wie bei den Ausweisen |

**Grenzwerte:** leere Liste · Eintrag ohne Rolle · unbekannte Rolle · Instanzkennung
leer oder mit Sonderzeichen.

---

## 8. Fortschreibung

Nach der Umsetzung: was anders kam. Bei Bedarf ADR-003.
