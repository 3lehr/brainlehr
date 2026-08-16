# Videoauswertung — 2026-08-16T08:15:00+0200

Video: `https://www.youtube.com/watch?v=B_y-2GUs928`
Titel: „Die AI Bubble findet gerade Graphentheorie für sich"
Kanal: The Morpheus Tutorials · Länge 44:34

**Werbehinweis:** Das Video enthält einen ausgewiesenen Sponsorenblock für einen
Cloud-Speicher-Anbieter, mit Rabattcode. Fremdwerbung, inhaltlich vom Thema getrennt.
Der Sprecher verkauft außerdem eigene Werkzeuge („von mir es auch kaufen könnt") — die
Zahlenangaben zu Benchmarks stammen aus fremden Veröffentlichungen und sind hier
**nicht** nachgerechnet.

## Beschaffung — und warum sie diesmal anders lief

YouTube liefert für dieses Video **weder automatische noch manuelle Untertitel**. Der
Weg der Auswertung vom 2026-08-13 (`yt-dlp --write-auto-sub`) läuft hier ins Leere.
Das Audio lag im Download-Ordner des Betreibers; transkribiert mit `whisper-cli`
(whisper.cpp, Modell `ggml-base`, lokal, kein fremder Dienst): **44 Minuten in 28
Sekunden**, 6806 Wörter, 249 Sätze. Transkript liegt unter
`docs/transkripte/B_y-2GUs928_harness-engineering.txt`.

Erkennungsfehler der Spracherkennung sind sichtbar und bleiben unkorrigiert
(„Grafentheorie", „GbD 5.6 Sol" für ein Konkurrenzmodell, „Chemie Code"). Wörtliche
Zitate unten tragen das mit.

## Die Kernaussage

> „Zunächst einmal ist ein Harness eigentlich, wenn man so möchte, eine Art Graf. Also
> ein Graf wie in der Grafentheorie, der uns sagt, in welche Richtung soll eigentlich
> was gehen."

> „Ein Graf besteht aus Knoten und Kanten und die Knoten heißen eine Aktion. […] Ihr
> habt Knoten, wie bei regulären Grafen, die euch die einzelnen Jobs definieren. Und
> die Kanten sind die Flos."

**Und der Punkt, auf den es hier ankommt — nicht jeder Knoten ist ein Modell:**

> „Das Besondere ist, dass nicht alles hier an ein KI Agent sein muss. […] Und der
> hier, ich habe das Quality Gates genannt. Und das heißt, da laufen einmal alle Tests
> durch, damit ich nicht die ganzen Agents, also die Review Agents verballern, wirklich
> viele Tokens."

## Der Loop, den der Betreiber meinte

> „Wenn die Tests viel schlagen [fehlschlagen], wenn ein Linter viel schlägt oder so
> was, dann geht es direkt wieder hier zurück. Das heißt, quasi noch mal eine Loop
> dazwischen."

**Das ist ein anderer Loop als der, den die Agentenkarte heute früh bekommen hat.**
Dort wurde der Werkzeugzyklus gezeichnet (Modell → Werkzeug → Modell) und der
Haltepunkt, der per `decision: block` zurückführt. Beides ist der Zyklus **des
Werkzeugs**. Der Loop des Videos liegt eine Ebene darüber: im **Arbeitsablauf** —
Implementer → Quality Gate → bei Rot zurück zum Implementer, erst bei Grün weiter zu
den Reviewern.

## Zweiter Befund: parallel statt nacheinander, mit Zahl

> „Wenn ich die Tests, also die Review Agents, nacheinander laufen lassen, dann war das
> ein Unterschied von ungefähr Faktor 4 […] mein Implementer Agent hat jedes Mal bloßes
> Feedback von einem Reviewer bekommen und wenn der eine Reviewer dann zufrieden war,
> habe ich den nächsten angemacht […] So dass quasi mehrere Feedback schleifen sich
> gespart werden und man quasi nur einmal starten muss."

Faktor 4 ist **seine** Messung an **seinem** Aufbau, hier nicht nachgeprüft. Die
Bauform dahinter ist trotzdem übertragbar: mehrere Prüfer gleichzeitig, ein
gesammeltes Feedback, statt einer Kette von Runden.

## Abgleich mit dem eigenen Bestand

**Was es hier gibt:**
- Ein Quality Gate existiert: `hub/scripts/quality_gate_hook.py`, verdrahtet am
  Ereignis `Stop`. Es blockt Sitzungen, die sicherheitsrelevante Dateien angefasst
  haben, ohne dass ein passender Spezial-Agent lief.
- **Geprüft und widerlegt:** Sein Docstring nennt `/tmp/claude-agent-register.jsonl`,
  also den Ort von vor dem Umzug am 2026-08-08. Der **Code** löst den Pfad aber über
  `agent_register_ort.pfad()` auf und liest damit den richtigen Ort
  (`hub/laufzeit/agent-register.jsonl`, 1691 Zeilen, aktuell). Nur die Beschreibung ist
  veraltet — kein wirkungsloser Wächter. Dasselbe gilt für
  `agent_reuse_guard_hook.py`.

**Was es hier NICHT gibt, und das ist der eigentliche Ertrag:**
Einen **deklarierten Ablaufgraphen**. Unsere Abläufe sind implizit — verteilt über
Hausregeln, Haken und Gewohnheit. Es gibt keine Datei, die sagt „erst Implementer, dann
Gate, bei Rot zurück, bei Grün drei Prüfer parallel". Deshalb konnte die Agentenkarte
diesen Loop auch nicht zeigen: **er ist nirgends aufgeschrieben.**

Das ist keine Frage der Darstellung. Wer den Ablauf zeichnen will, muss ihn zuerst
haben.

## Was daraus folgt — offen, nicht beschlossen

1. **Ablauf deklarieren, bevor man ihn zeichnet.** Ohne Beschluss des Betreibers wird
   hier kein Harness gebaut.
2. **Wenn deklariert, dann als Datei** — dieselbe Bauform wie die Landkarten: erzeugt,
   geprüft, im `pre-push` gegen Abweichung gesichert.
3. **Die Zahl „Faktor 4" wird nicht übernommen**, sondern gemessen, falls parallele
   Prüfer je gebaut werden.
