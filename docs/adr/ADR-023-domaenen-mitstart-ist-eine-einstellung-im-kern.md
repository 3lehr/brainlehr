# ADR-023: Ob eine Domäne mitstartet, entscheidet der Mensch in einer Einstellung — nicht die Domäne

**Stand** 2026-08-16T07:44:00+0200
**Status** Angenommen
**Betrifft** `atelier` (Kern), `brainlehr`, jedes Domänen-Repo (ADR-013)
**Entscheider** Betreiber, 2026-08-16

## Die Anforderung, wörtlich

> *„dann brauchen wir aber eine einstellung die den user erllaubt zu sagen
> openlehr mitzustarten. sonst denkt der enduser immer warum läuft open lehr
> nicht!"*

## Warum das kein Widerspruch zu ADR-013 ist, sondern dessen fehlende Hälfte

ADR-013 sagt: der Dienst einer Domäne läuft im **eigenen Prozess**, nie im
atelier, **installiert mit Zustimmung**. Der Satz regelt, *wo* der Dienst läuft
und *dass* jemand zustimmt — er sagt nicht, **wo diese Zustimmung wohnt** und
**wer sie später wieder sieht**. Genau dort entsteht der Fehler, den der
Betreiber beschreibt: Eine Zustimmung, die einmal beim Installieren gegeben wird
und danach nirgends steht, ist für den Menschen nicht von einem Defekt zu
unterscheiden. Er sieht nur, dass nichts läuft.

**Die Zustimmung wird deshalb ein Schalter, kein Moment.**

## Die Entscheidung

**1. Der Schalter steht im Kern, nicht in der Domäne.** Nach ADR-014 gehört ins
atelier, was *keine Domäne über sich selbst entscheiden darf.* Ob eine Domäne
beim Anmelden des Menschen von selbst einen Prozess startet, ist der
Lehrbuchfall davon — eine Domäne, die ihren eigenen Autostart erteilt, ist keine
Schranke. Der Schalter liegt bei den Einstellungen neben Modellzugängen und
brainlehr-Grundeinstellungen.

**2. Die Startbeschreibung liefert die Domäne, im Manifest.** Der Kern kann keine
Domäne starten, die er nicht kennt. Gemessen am 2026-08-16 trägt
`pakete/steuer.domaene.json` genau fünf Felder — `domaene`, `bezeichnung`,
`herkunft`, `stand`, `quellen`, `regeln` — also **nur den Teil *Wissen* aus
ADR-013.** Die Teile *Dienst* und *Oberfläche* haben im Manifest heute keine
Vertretung. Der Dienst-Teil bekommt sie hier: was zu starten ist, worauf es
hört, woran man erkennt, dass es lebt.

**3. Absolute Pfade sind verboten, Platzhalter sind Pflicht.** Der Grund liegt
gemessen vor. Die beiden Startbeschreibungen im Haus unterscheiden sich genau an
dieser Stelle:

| | |
|---|---|
| `de.brainlehr.dienst` | `__REPO_PFAD__` als Platzhalter, Python-Kandidaten werden auf Tauglichkeit **geprüft** statt geraten |
| `de.openlehr.daemon` (Legacy) | `/Volumes/daten/Begod2026/openlehr` und `.venv` fest verdrahtet |

Die erste Fassung überlebt einen Import auf einen fremden Rechner, die zweite
nicht. Da ADR-013 ausdrücklich will, dass Fremde ein Domänen-Repo importieren
können, ist das kein Stilfrage, sondern die Bedingung dafür, dass die Domäne bei
irgendwem außer dem Betreiber startet.

**4. Der Mensch sieht drei Zustände, nicht zwei.** „läuft" und „läuft nicht"
reichen nicht — sie sind der Grund für die Frage, die diese ADR ausgelöst hat.
Es braucht: **aus** (Schalter steht aus — kein Defekt, eine Entscheidung) ·
**startet** · **läuft** · **kommt nicht hoch** (mit dem, was der Mensch tun
kann). Die ersten beiden sind heute nicht unterscheidbar, und genau diese
Verwechslung beschreibt der Betreiber.

**5. Voreinstellung: aus.** Eine frisch importierte Domäne startet nichts von
selbst. ADR-018 hat dieselbe Form für Regeln — eingelesen heißt nicht in Kraft;
hier heißt installiert nicht gestartet. Der Unterschied zum heutigen Zustand ist
trotzdem groß, denn das *Aus* ist dann **sichtbar und umlegbar**, statt
unsichtbar und rätselhaft.

## Was ausdrücklich nicht entschieden wird

- **Nicht, mit welcher Technik gestartet wird.** LaunchAgent, `launchctl submit`
  oder ein Kindprozess unter Aufsicht des atelier — das ist eine Bauentscheidung
  und gehört in den Umsetzungsplan. Diese ADR legt fest, *wer* entscheidet und
  *wo* es steht.
- **Nicht, ob der Entwicklungsassistent** (die zweite in openlehr gefundene
  Domäne, 56 Endpunkte) überhaupt neu gebaut wird. Das ist eine Umfangsfrage und
  offen.

## Preis

`DienstAufsicht.swift` kennt heute **genau einen** Dienst — den eigenen. Aus
einer Aufsicht über einen Dienst wird eine über *n*, und *n* ist zur Bauzeit
unbekannt. Das ist echte Arbeit und wird hier benannt, nicht versteckt.

## Woran sich der Erfolg messen lässt

Ein Mensch, der die Domäne importiert und den Schalter nicht umlegt, bekommt an
keiner Stelle den Eindruck eines Defekts — er sieht „aus" und weiß, was zu tun
ist. Und: dieselbe Domäne startet auf einem Rechner, auf dem das Repo an einem
anderen Ort liegt.
