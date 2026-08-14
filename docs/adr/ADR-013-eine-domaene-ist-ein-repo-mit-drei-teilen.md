# ADR-013: Eine Domäne ist ein Repo mit drei Teilen — und ihre Oberfläche ist Beschreibung, nicht Code

**Stand** 2026-08-14T21:36:26+0200
**Status** Angenommen
**Betrifft** `brainlehr`, `atelier`, `openlehr`, jede künftige Domäne
**Entscheider** Betreiber, 2026-08-14

## Die Anforderung, wörtlich

> *„nein mir geht es darum das der ganze opelehr teil eine eigene neue repo
> werden soll, andere leute die brainlehr und atelier haben sollen sich dann die
> repo importieren können, danach soll es dann so aussehen als währe openlehr
> ein teil von brainlehr atelier"*

Damit ist die Verteilungseinheit entschieden, und sie ist größer als das, was
ADR-012 vorsah: **nicht eine Paketdatei, sondern ein Repo.** ADR-012 bleibt
gültig — es beschreibt die Vertrauensstufen *innerhalb* dieses Repos.

## Gemessene Ausgangslage

openlehr liegt als **eine von 13 Apps** im Monorepo `3lehr-monorepo`
(`apps/openlehr`, 390 MB, dazu `docs/openlehr`, 12 MB). Ein eigenes Repo heißt
also **Herauslösung mit Historie**, nicht Neuanlage. Die Schnittgrenze wird
gemessen, bevor geschnitten wird (`docs/openlehr/schnittgrenze_2026-08-14.md`).

## Die Entscheidung: drei Teile, drei Vertrauensstufen

Ein Domänen-Repo enthält genau drei Sorten, und keine davon vermischt sich mit
einer anderen:

| Teil | was | wo es läuft | Vertrauensstufe |
|---|---|---|---|
| **Wissen** | Regeln, Quellen, Fundstellen (`*.domaene.json`) | nirgends — es wird gelesen | keine nötig, es kann nichts tun |
| **Dienst** | der Fachcode: rechnen, verbinden | **eigener Prozess**, nie im atelier | installiert, mit Zustimmung |
| **Oberfläche** | Ansichten, Menüpunkte, Formularfelder | im atelier — **als Beschreibung gezeichnet** | keine nötig, es ist kein Code |

## Der Kern: „als wäre es ein Teil davon" geht nur ohne fremden Oberflächen-Code

Das atelier ist eine native Anwendung. Für fremde Ansichten gibt es zwei Wege,
und der naheliegende ist der schlechtere:

**Verworfen — fremder Oberflächen-Code** (geladenes Bündel, dynamische
Bibliothek): Jede Domäne könnte die Anwendung zum Absturz bringen, jede
Installation verlangte eine neu gebaute und signierte App, und **das Ergebnis
sähe trotzdem fremd aus** — fremder Code bringt seine eigene Handschrift mit.
Er erreicht das Ziel des Betreibers also nicht einmal.

**Gewählt — die Oberfläche ist Beschreibung.** Die Domäne sagt, *was* zu sehen
sein soll (Felder, Abschnitte, Menüpunkte, Reihenfolge, Beschriftungen); das
atelier zeichnet es mit **seinen eigenen** Bausteinen. Damit sieht jede Domäne
zwangsläufig aus wie ein Teil der Anwendung — nicht weil sie sich anpasst,
sondern weil sie gar nicht selbst zeichnet.

**Das ist keine neue Erfindung, sondern bereits gebaut:** `kern/baustein.py`
führt den Typ `feld` gleichberechtigt neben `absatz`, ausdrücklich damit *„eine
Rechnung und ein Schriftsatz dieselbe Struktur benutzen"*. Ein Domänen-Bildschirm
ist derselbe Baum aus Bausteinen. Und es ist dieselbe Trennung wie beim
Wissenspaket (ADR-011: ein Paket ist Daten) — hier auf den Bildschirm angewandt.

## Der Preis, und er ist echt

- **Eine Domäne kann nur so aussehen, wie das atelier zeichnen kann.** Braucht
  sie ein Bedienelement, das es nicht gibt, muss das atelier es lernen — das ist
  Arbeit an der Trägerschicht, nicht an der Domäne. Gegenwert: keine Domäne kann
  die Anwendung beschädigen, und alle sehen aus wie eine.
- **Zwei Prozesse pro Domäne.** Ist der Dienst nicht da, fehlen die Fähigkeiten;
  das Wissen bleibt trotzdem nutzbar. Der Bildschirm muss diesen Zustand
  benennen können, ohne über Prozesse zu reden.
- **Der Schnitt ist einmalig teuer.** Historie trennen, Auswärtsbindungen lösen,
  absolute Pfade entfernen. Danach ist es billiger als vorher.

## Was daraus sofort folgt, weil es später nicht mehr geht

1. **Kein absoluter Pfad überlebt den Schnitt.** Er funktioniert auf genau einem
   Rechner und bricht bei jedem Empfänger. Wird vor dem Schnitt gemessen.
2. **Keine Datenbank, kein Zwischenstand, keine Zugangsdatei wandert mit.** Was
   einmal in der Historie eines verteilten Repos liegt, ist nicht mehr
   einzufangen — auch nicht durch späteres Löschen.
3. **Die Oberflächenbeschreibung gehört von Anfang an ins Manifest**, auch wenn
   sie zunächst leer bleibt. Ein Format nachträglich um ein Pflichtfeld zu
   erweitern macht jedes verteilte Repo ungültig.

## Verworfen

- **openlehr bleibt im Monorepo, Verteilung über Kopien.** Verworfen: Der
  Betreiber hat das Repo als Verteilungseinheit entschieden, und eine Kopie ohne
  Historie verliert genau das, was ein Repo ausmacht.
- **Neues Repo ohne Historie anlegen** (Dateien kopieren). Verworfen: `git log`
  ist das einzige Verzeichnis, das erklärt, warum eine Zeile so aussieht. Ein
  Neuanfang wirft es weg, und für 43 237 Zeilen fremd wirkenden Code ist es das
  Wertvollste, was mitkommen kann.
- **Alles ins atelier hineinbauen.** Verworfen: Dann gibt es keine Domänen,
  sondern eine Anwendung, die alles kann — und der nächste Fachbereich verlangt
  wieder einen Neubau der App.
