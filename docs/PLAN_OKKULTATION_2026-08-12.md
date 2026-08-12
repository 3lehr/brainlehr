# Okkultation — misst der Speicher überhaupt etwas, oder redet er nur mit

Stand 2026-08-12T23:59:00+0200. Anlass: Betreiberfrage — ob das Problem gar
nicht der Kern von brainlehr ist, sondern dass die Einspielungen keine Wirkung
zeigen und Claude den Speicher schlicht nicht einsetzt.

Diese Frage lässt sich **entscheiden statt diskutieren**. Der Plan beschreibt,
wie.

## Der gemessene Ist-Stand

| | Befund |
|---|---|
| Alter des Systems | 5 bis 10 Tage. Jede Aussage über „Verfall" oder „Bestandsnutzung" ist entsprechend zu lesen |
| Bestand | 2155 Knoten, davon **1638 NASA-Import** (`nachschlagewerk`, absichtlich Heuhaufen) und 820 Lehren |
| Einspielungshäufigkeit | Gemessen 2026-08-08 (`L-8b377b`): 868 Einspielungen, **ein** Eintrag 380 mal, die drei häufigsten zusammen **78 %**; für 1732 von 2008 Knoten gar kein Signal |
| Anteil am Kontext | rund **0,8 %** Wissens-Einspielung gegen **71 %** Werkzeugausgaben |
| Was der Abrufkorpus messen kann | nur Nachrichten, die eine **Adresse** nennen — Fragen tun das in 0,9 % der Fälle (`fa296b67`) |
| Vergleichsbefund aus neun Ingenieurssystemen | Wirksamkeit kommt aus **administrativem Zwang**, nicht aus besserer Suche |

**Warum der naheliegende Weg ausscheidet:** Ein Nützlichkeitszähler über
Einspielungen misst die Auslieferung, nicht den Nutzen. Ein Eintrag, der 380
mal eingespielt wurde, hat nicht 380 mal geholfen — er passt zu häufigen
Themen. Als Rangfaktor wäre er eine Rückkopplung: Häufiges stiege weiter,
Seltenes sänke dauerhaft.

## Die Alternativen

**A — Zähler über Einspielungen.** Abgelehnt, siehe oben. Gegenprobe für jede
künftige Nützlichkeitszahl: *Anteil der drei häufigsten an der Gesamtzahl.*
Über 50 % heißt, die Kennzahl beschreibt die Suche, nicht den Nutzen.

**B — Selbstauskunft des Modells** („war das hilfreich?"). Abgelehnt. Dasselbe
Modell, das die Antwort schreibt, bewertet den Beitrag zu seiner eigenen
Antwort — und heute wurde mehrfach gemessen, dass ehrliche Berichte trotzdem
falsch sein können.

**C — Okkultation, also Eingriff (gewählt).** Dieselbe Aufgabe zweimal
bearbeiten: einmal mit Einspielung, einmal ohne. Der Unterschied im **Ergebnis**
ist der Nutzen. Der Name kommt aus der Astronomie: Man erkennt einen Körper
daran, dass etwas verschwindet, wenn er davorzieht.

## Der Aufbau

**Die Fallmenge.** Der Echtkorpus (89 Fälle) misst nur Nachrichten mit Adresse.
Für diese Frage ist das **die falsche Menge** — gerade die Fragen fehlen. Also
zwei getrennte Mengen, getrennt ausgewiesen:
- **M1, Zielaufgaben:** die 89 Fälle mit bekanntem Ziel. Erfolg ist objektiv
  messbar (Ziel getroffen oder nicht).
- **M2, Fragen ohne Ziel:** echte Fragen aus dem Verlauf. Erfolg ist **nicht**
  objektiv messbar. Für sie wird kein Erfolgsurteil gefällt, sondern nur
  festgehalten, ob sich die Antwort **inhaltlich unterscheidet** — und wenn ja,
  worin. Ein Unterschied ist noch kein Nutzen; das gehört so benannt.

**Die zwei Läufe.** Derselbe Prompt, dasselbe Modell, einmal mit und einmal
ohne den `<knowledge-recall>`-Block. Alles andere gleich.

**Die Bewertung.** Für M1 mechanisch (Ziel im Ergebnis). Für M2 durch einen
Prüfer, der **beide Antworten sieht, aber nicht weiß, welche welche ist** —
sonst bewertet er die Erwartung statt den Text.

## Die drei Ergebnisse, die möglich sind — und was jedes bedeutet

| Ergebnis | Bedeutung |
|---|---|
| Ohne Einspielung **gleich gut** | Der Speicher trägt nichts bei. Die Vermutung des Betreibers ist bestätigt; die Arbeit gehört dann in die Verwendung, nicht in die Suche |
| Ohne Einspielung **schlechter** | Der Speicher wirkt. Die Differenz ist die erste belastbare Nutzenzahl, die das System je hatte |
| Ohne Einspielung **besser** | Die Einspielung schadet — sie verdrängt Kontext oder lenkt ab. Das wäre der wichtigste Befund von allen und ist ausdrücklich als möglich mitzuführen |

**Ein Ergebnis wird nicht vorweggenommen.** Der Aufbau muss alle drei zulassen,
sonst misst er die Erwartung.

## Was bewusst nicht getan wird, samt Preis

- **Keine Nützlichkeitszahl je Eintrag.** Der Versuch beantwortet, ob das
  *Verfahren* wirkt, nicht welcher Knoten wie wertvoll ist. Preis: keine
  Rangliste. Gewinn: keine Rückkopplung in den Abruf.
- **Kein Eingriff in den laufenden Betrieb.** Der Versuch läuft neben dem
  Betrieb, nicht in ihm — niemandes Sitzung wird beschnitten.
- **Keine Ausweitung auf andere Dämonen im ersten Lauf.** Codex und die
  übrigen Klienten bleiben außen vor, obwohl sie denselben Speicher benutzen.
  Preis: Das Ergebnis gilt zunächst für einen Klienten. Es wird als solches
  ausgewiesen und nicht verallgemeinert.

## Woran sich Erfolg messen lässt

- Beide Läufe je Fall wirklich gefahren, kein hochgerechneter Vergleich.
- Jede Zahl mit Nenner, getrennt nach M1 und M2.
- Die Gegenprobe zur Schiefe ist mitgeführt: Anteil der drei häufigsten
  Einspielungen an der Gesamtzahl.
- **Negativkontrolle:** ein Lauf, in dem statt der echten Einspielung ein
  gleich langer, thematisch fremder Block eingespielt wird. Ist das Ergebnis
  damit genauso gut wie mit der echten, misst der Versuch die **Länge** des
  Blocks und nicht seinen Inhalt.
- Was **nicht** gemessen werden konnte, steht im Ergebnis, nicht im Anhang.
