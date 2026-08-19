# Videoauswertung — 2026-08-19T09:55:00+0200

Video: `https://www.youtube.com/watch?v=mkppuHqIxFU`
Titel: „Claude Agent OS is INSANE!"
Kanal: Julian Goldie SEO · veröffentlicht 2026-08-18 · Länge 7:41
Zum Abrufzeitpunkt 1106 Aufrufe / 21 Likes (fremdberichtet, YouTube-Metadaten)

## Beschaffung

`yt-dlp --write-auto-sub` (englische Untertitel vorhanden, im Gegensatz zum
Video vom 2026-08-16). 1499 Wörter, Transkript unter
`docs/transkripte/mkppuHqIxFU_agent-os.txt`.

## Das Wichtigste zuerst: Gattung

**Das ist ein Verkaufsvideo, kein Fachvideo.** Der Sprecher stellt sich selbst
als „digital avatar of Julian Goldie" vor. Das Video endet auf
`aiprofitboardroom.com`; beworben werden zwei kostenpflichtige Angebote („AI
Profit Boardroom", „AI Success Lab"), und die Produktdatei selbst liegt hinter
der Bezahlschranke: „The full Agent OS zip file is inside the AI Profit
Boardroom right now."

Das ist keine Abwertung, sondern die Einordnung, die für den Rest gilt: **es
gibt im ganzen Video keine nachprüfbare Zahl, keine Methode und keinen
Fehlerfall.** Die beiden vorigen Auswertungen (heise am 13.08., Morpheus am
16.08.) trugen mindestens fremdberichtete Messungen. Diese hier trägt
Behauptungen und Kundenstimmen („Rick joined and had his own version … within
30 minutes").

## Was behauptet wird

| Baustein | Aussage im Video |
|---|---|
| „memory galaxy" | Wissensgraph, **1.277 Erinnerungen**, „I've never updated it manually" — jede Agentennutzung wird automatisch protokolliert |
| Rückgriff | „When I ask Hermes what to work on next, it pulls context straight from that memory graph" |
| „Fusion" | mehrere Modelle zusammen, „sits at the top of an internal benchmark" |
| Dokumentation | „everything I test … gets documented automatically using Claude … so I can compare results side by side" |
| Bedienung | ein Dashboard, Sprachsteuerung, Agenten je Aufgabe |

## Was wir daraus lernen — und der erste Punkt ist der einzige, der wehtut

### 1. Dieses System ist heute Vormittag von uns widerlegt worden

Die „memory galaxy" ist **automatische Erfassung ohne gemessenen Abruf**:
alles wird protokolliert, nichts wird bewertet, und der Rückgriff liefert
immer etwas.

Genau diesen Aufbau haben wir heute gemessen
(`runs/wirkung_llm_probe_2026-08-19T084859.json`): Bei Fragen, zu denen der
Speicher etwas hat, wird die Antwort besser (3 von 10, nie schlechter). Bei
Fragen, zu denen er **nichts** hat, liefert der Wortkanal trotzdem Material —
und die Antwort wird **falsch**: „Welcher Knoten eignet sich zum Verzurren
einer Plane?" wird von *Mastwurf* (richtig) zu *„Kaliblerbremse"*, einem
Planknoten aus unserem eigenen Bestand.

Ein Speicher, der nie schweigt, verschlechtert Antworten außerhalb seines
Gebiets. Das Video beschreibt diese Eigenschaft als Verkaufsargument („it
pulls context straight from that memory graph"), und es hat **keine
Möglichkeit, den Schaden zu bemerken** — es misst nichts.

**Für uns heißt das nicht „wir sind besser", sondern:** Aufgabe `114`
(Enthaltungsschwelle) ist nicht Feinschliff, sondern der Unterschied zwischen
diesem System und einem, dem man trauen kann. Sie bleibt bindend vor `112`.

### 2. Die Größenordnung ordnet unsere eigene Lage ein

1.277 Erinnerungen werden als beeindruckend präsentiert. Unser Bestand steht
heute bei **5.182 Knoten, 1.103 Lehren, 10.316 Kanten** (gemessen
2026-08-19). Der Vorsprung liegt also **nicht** in der Menge — er liegt
darin, dass wir über den Bestand Aussagen treffen können, die weh tun. Menge
ist die Zahl, die man zeigt, wenn man keine andere hat.

### 3. Ein Punkt, den das Video besser löst als wir

> „everything I test inside Agent OS gets documented automatically … so I can
> compare results side by side later"

Das ist bei uns die schwächste Stelle, und sie wird seit Wochen von unseren
eigenen Meldern angezeigt: **75 Ergebnisdateien unter `runs/` ohne
Rastervermerk, 74 ohne Gegenprobevermerk** (Aufgabe `111`). Wir *erzeugen*
Messungen fleißiger als sie, und wir legen sie schlechter ab. Der Unterschied
ist, dass ihre Ablage automatisch passiert und unsere von Hand — mit dem
bekannten Ergebnis.

Übernehmenswert ist **nicht** das Werkzeug, sondern die Stelle: die Ablage
gehört an das **Ende des Messlaufs**, nicht in die Nachsorge. Dieselbe Lehre
wie bei jedem Melder ohne Auslöser.

### 4. Was der Markt für das Problem hält

Die Eröffnung ist eine präzise Problembeschreibung: *„Have you ever built
something with AI and then lost it forever? Gone, buried in some random chat
you can't find again."* Das ist genau unser Gegenstand — und die Antwort des
Videos darauf ist **ein Dashboard**. Nicht Herkunft, nicht Geltung, nicht
Freigabe: eine Oberfläche, die alles an einem Ort zeigt.

Das ist eine Positionierungsauskunft, keine technische. Wer dieses Problem
verkauft, verkauft heute Bedienbarkeit. Unsere Antwort (Belegschicht,
Freigabe, Ablösung) beantwortet eine Frage, die im Markt noch nicht gestellt
wird — was zugleich der Wert und das Absatzrisiko ist.

## Was ausdrücklich NICHT übernommen wird

- **Automatische Vollprotokollierung ohne Bewertung.** Siehe Punkt 1. Wir
  haben den Schaden gemessen, sie nicht.
- **„Fusion sitzt an der Spitze eines internen Benchmarks."** Ein Benchmark,
  den der Anbieter selbst führt, über Ausgaben, die er selbst verkauft, ohne
  genannte Aufgaben, Nenner oder Gegenprobe. Nicht nachrechenbar, also keine
  Zahl.
- **Die Kundenstimmen** („within 30 minutes", „close to 200 pages of
  feedback"). Werbematerial.

## Belegstand

Alles oben Zitierte stammt aus dem Transkript und ist dort nachlesbar. Die
Zahlen zu unserem eigenen Bestand sind heute gemessen. Die Aussagen des
Videos sind **nicht** nachgeprüft und auch nicht nachprüfbar — die Software
liegt hinter einer Bezahlschranke.
