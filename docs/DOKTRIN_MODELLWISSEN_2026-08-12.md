# Was aus Modellwissen entstehen darf und was aus dem Speicher kommen muss

Stand 2026-08-12T11:00:00+0200. Anlass: In der Buckeberg-Sitzung wurden drei
Rechtsaussagen aus dem Modellgedächtnis als geltend ausgegeben, alle drei zum
Zeitpunkt der Aussage falsch. Das Gesetz stammt vom 23.07.2026, der
Trainingsstand endet im Mai 2026 — kein Modellwissen konnte es kennen.

**Das Versagen war nicht das Nichtwissen.** Es war, das Nichtwissen nicht wie
Nichtwissen behandelt zu haben.

## Die falsche Trennlinie, und die richtige

Naheliegend, aber unbrauchbar: „Modellwissen gegen Speicherwissen". Der
Speicher weiß das meiste auch nicht, und Modellwissen ist für Struktur,
Argumentation und Code völlig in Ordnung.

Die tragfähige Linie verläuft woanders: **Was kostet es, wenn dieser Satz
falsch ist, und merkt es jemand?**

| | darf aus dem Modell | muss belegt werden |
|---|---|---|
| Struktur, Gliederung, Argumentation | ja | — |
| Code, Idiome, Verfahren | ja | — |
| Erklärungen, die der Leser selbst prüfen kann | ja | — |
| **Paragraphen, Artikel, Gesetzesnamen** | nein | Primärquelle |
| **Fristen, Stichtage, Jahreszahlen** | nein | Primärquelle |
| **Beträge, Preise, Quoten** | nein | Primärquelle |
| **Version-abhängiges Verhalten** („ab Version X") | nein | Doku oder Test |
| **Aussagen über Dritte** (Zusagen, Verträge, Firmen) | nein | Beleg im Bestand |
| **Alles in einem Dokument, das nach außen geht** | nein | doppelt |

Das Erkennungszeichen ist einfach: **Eine präzise Fundstelle aus dem Gedächtnis
ist verdächtiger als eine vage Angabe, nicht glaubwürdiger.** Wer „§ 71 Abs. 1
Satz 2" sagt, hat entweder nachgeschlagen oder erfunden — dazwischen gibt es
nichts.

## Was passiert, wenn der Speicher nichts hat — und warum das billig ist

Die teure Antwort wäre eine Recherche-Runde bei jeder Lücke. Die richtige
Antwort ist billiger und besser:

**Die Aussage entfällt.** Sie wird nicht geraten, nicht abgeschwächt, nicht mit
Vorbehalt garniert — sie wird nicht getroffen. Der Satz lautet dann: „Dazu
liegt nichts vor." Das kostet null Token.

Beschafft wird erst, wenn die Aussage für eine Entscheidung gebraucht wird, und
dann gezielt: eine Quelle, ein Abruf. Nicht eine Runde.

Drei Formulierungen, die zulässig bleiben und die alle ehrlich sind:

- „Dazu liegt im Speicher nichts vor."
- „Aus dem Modellwissen, ungeprüft — vor Verwendung nachschlagen."
- „Der Wortlaut ist nicht belegt; belegt ist nur, dass es die Norm gibt."

Die zweite Formulierung gehört **in denselben Satz**, in dem die Angabe fällt,
nicht in eine Fußnote am Ende. Am 2026-08-10 stand der Vorbehalt korrekt im
Wissensknoten und fehlte zwei Nachrichten später im Gespräch (`L-62b600`).

## Wie geprüft wird, ob der Speicher aktuell ist — ohne alles neu zu holen

Nicht jede Aussage altert gleich schnell. Der Speicher trägt die Felder dafür
bereits: `gilt_ab`, `gilt_bis`, `zurueckgezogen`, `updated_at`, dazu einen
gerechneten Konfidenzverfall.

Die billige Prüfung ist eine **Altersschwelle je Aussagenart**, kein erneuter
Abruf:

| Art | verfällt | Prüfung |
|---|---|---|
| Gesetz, Verordnung | nie von selbst — aber jede Zitierung ist prüfpflichtig | Verkündungsblatt, nicht Datenbank |
| Preise, Förderbedingungen | Wochen | Datum im Beleg gegen heute |
| Schnittstellen, Versionen | Monate | Beleg gegen installierte Fassung |
| Verfahren, eigene Beschlüsse | lang | Ablösung durch spätere Entscheidung |

`kern/normbezug.py` führt dafür bereits `PRUEFALTER_TAGE` und kennt den Status
„veraltet" neben „belegt" und „unbelegt". Der Aufwand ist eine SQL-Abfrage am
Ende einer Antwort, nicht eine Recherche.

**Eine Datenbank kann im Rückstand sein, ein Verkündungsblatt nicht.** Genau
dieser Unterschied hat den Fund vom 2026-08-12 ermöglicht: Die
Gesetzesdatenbank zeigte in der Inhaltsübersicht „(weggefallen)" und lieferte
auf der Einzelseite noch den alten Fließtext.

## Der Fehler, der heute gefunden wurde und der die ganze Kette entwertet hätte

Der Melder meldet für „§ 71 GEG" den Status **belegt** — und der Beleg ist
ausgerechnet der Knoten, der die Streichung dokumentiert. Er enthält die
Zeichenfolge „§ 71".

**Ein Suchtreffer belegt Erwähnung, nicht Geltung.** Das gilt über den
Rechtsfall hinaus: für Schnittstellen, Konfigurationswerte und eigene
Beschlüsse genauso. Jede Prüfung, die aus dem Vorhandensein eines Textes auf
die Gültigkeit einer Aussage schließt, hat diesen Fehler.

Behebung läuft; bis dahin trägt der Status „belegt" dieses Melders **keine**
Aussage über die Geltung.

## Für ein Dokument, das nach außen geht

Vier Handgriffe, keiner davon teuer:

1. Jede Zahl, jede Frist und jedes Zitat im Dokument einzeln durchgehen und
   fragen: aus welcher Quelle, von welchem Datum?
2. Bei Rechtsnormen: Verkündungsblatt, nicht Gesetzesdatenbank, nicht der
   Melder.
3. Was sich nicht belegen lässt, **streichen** — nicht abschwächen. Ein
   abgeschwächter falscher Satz bleibt ein falscher Satz und wirkt dazu
   vorsichtig geprüft.
4. Das fertige Dokument ansehen, nicht den Lauf, der es erzeugt hat. Ein PDF,
   das niemand geöffnet hat, ist ungeprüft, egal wie grün der Lauf war.

## Was das Verfahren leistet und was es nicht leistet

Ehrlich bilanziert, nach dem Verlauf vom 2026-08-12:

Das Verfahren fängt, was ein Modell sagen würde, wenn niemand nachhakt — durch
die Auflage, einen Fehlschlag zu melden statt ihn zu überspielen, durch eine
Kritiker-Runde, und dadurch, dass diese den eigenen Auftrag auf Rahmensetzung
prüfen musste.

Es ersetzt nicht, dass jemand nachhakt. Drei Fehlaussagen desselben Tages hat
nicht das System gefunden, sondern der Betreiber — jedes Mal durch eine
Nachfrage.

Und der Speicher selbst hat zur Rechtslage **nichts** beigetragen: Er enthielt
nichts dazu und spielte nichts ein. Gefunden hat es ein Agent mit Websuche. Was
brainlehr beigetragen hat, ist der Ort, an dem der Fund jetzt liegt — damit die
nächste Sitzung ihn nicht noch einmal machen muss.
