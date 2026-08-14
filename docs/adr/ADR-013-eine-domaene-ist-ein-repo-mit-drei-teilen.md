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

## Nachtrag am selben Tag: es sind drei Klassen von Oberfläche, nicht eine

Auf die Frage *„dann doch http nehmen und das atelier nur als
startoberfläche?"* — und nachdem der Betreiber zu Recht darauf bestand, dass
Swift Plugins laden **kann** (siehe unten):

**Der Satz oben, „die Oberfläche ist Beschreibung", war zu grob.** Gemessen
fährt das atelier den Hybrid längst: `WissensraumWebView.swift` (113 Z.) bettet
eine Webseite über WebKit ein, während die Ansichtswahl nativ in der
Seitenleiste liegt. Im Dateikopf steht der Grund wörtlich: *„Ansichtswahl nativ
in der Seitenleiste statt als Knopfleiste im Web"*.

Damit ist die Frage nicht „nativ oder Web", sondern **welche Teile nativ bleiben
müssen**. Drei Klassen, scharf getrennt:

| Klasse | wer zeichnet | warum |
|---|---|---|
| **Rahmen und Navigation** | nativ, das atelier | Damit jede Domäne am selben Ort dieselben Wege hat. Muster existiert |
| **Fachbildschirme** (Listen, Formulare, Tabellen, Auswertungen) | **die Domäne, als Web über HTTP** | Nativ bringt hier wenig, und openlehrs Bildschirme existieren bereits |
| **Dokumente** (Rechnung, Brief ans Finanzamt) | **Dokumentfenster, nativ, nie Web** | ADR-010: Mensch und Modell am selben Dokument, Zeichen für Zeichen. Das gibt es im Browser nicht |

**Die Trennlinie in einem Satz:** *Wo ein Dokument entsteht, das ein Mensch
außerhalb liest, zeichnet das atelier. Wo Daten verwaltet werden, zeichnet die
Domäne.*

**Warum nicht „nur Startoberfläche":** Dann wäre ADR-010 gegenstandslos — das
Dokumentfenster ist der Grund, warum ein Brief ans Finanzamt hier besser
entsteht als im Browser, und es ist gebaut (F1–F5). Und der Betreiberwunsch
*„soll aussehen als wäre openlehr ein Teil davon"* wird genau von diesen zwei
nativen Klassen getragen: Rahmen und Dokumente sehen überall gleich aus. Dass
die Listen je Domäne verschieden aussehen, fällt am wenigsten auf — dort wird
gearbeitet, nicht repräsentiert.

**Was das für openlehr rettet:** Die bestehende Steuer-Oberfläche muss nicht neu
gebaut werden, um im atelier zu erscheinen. Der Beschluss zum UI-Neubau bleibt
gültig, beantwortet aber ab jetzt eine andere Frage — nicht *ob* Web, sondern
wie die Fachbildschirme aussehen.

**Zur Korrektur an der Plugin-Frage:** Swift **kann** Code nachladen (`dlopen`,
`Bundle.load()`, XPC, ExtensionKit). Der frühere Satz, es ginge nur mit einem
Neubau der App, war falsch. Die Gründe gegen geladenen Oberflächen-Code bleiben
— Signaturbindung (Library Validation), Absturz im selben Prozess, und dass
fremd gezeichnete Oberflächen fremd aussehen. **Nicht gemessen:** XPC und
ExtensionKit lösen das Absturzproblem und wären die ernsthafte Alternative zum
HTTP-Weg; sie binden die Domäne aber an macOS, und openlehr ist ein
Python-Dienst.

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
