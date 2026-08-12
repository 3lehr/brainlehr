# Simulator und Signalstärke — den Abruf vorführen, ohne ihn zu erfinden

Stand 2026-08-12T23:30:00+0200. Anlass: Betreiberwunsch, wörtlich — *„ausserdem
hätte ich gerne einen simulator button der verschiedene abfragen simuliert und
etwas mit dem ich die ‚starke' der singnale einstellen kann, also wie
stark/hell/schnell/intensive sie gezeichnet werden. wähle passende paramter"*

## Der gemessene Ist-Stand

| | Befund |
|---|---|
| Wo gezeichnet wird | `entscheidungen.html`, fünf Ansichten; Puls und Verglimmen seit `8389dc8`, Weg im Bedeutungsraum seit `f21b766` |
| Wie ein Weg entsteht | Eingabe in der Abrufweg-Leiste, `POST /api/abrufweg` |
| Puls heute | gedämpfte Sinuswelle, Periode 3200 ms (0,31 Hz), Amplitude 0,13 um Grundwert 0,83 |
| Verglimmen heute | `ABRUFWEG_GLIMM_MS = 4000` |
| Helligkeit im Raum | aus der rohen Kosinus-Ähnlichkeit, relativ zum Kandidatenfeld normiert |
| Bewegungsschalter | `prefers-reduced-motion` schaltet jede Bewegung ab, über einen `matchMedia`-Horcher |
| Echte Fälle vorhanden | `runs/echtkorpus_2026-08-12T1000.json`, 89 Fälle aus echten Nachrichten |
| Kosten je Abruf | 3 bis 4,5 s (Kosinus über 3508 Vektoren, reines Python, kein Index) |

## Die Alternativen

**A — Erfundene Beispielanfragen.** Abgelehnt. Ein Vorführmodus mit
ausgedachten Fragen zeigt, wie es aussehen soll, nicht wie es ist — und im
Video wäre nicht unterscheidbar, was echt gemessen und was hübsch gemacht ist.
Genau diese Verwechslung ist in diesem Projekt schon einmal teuer geworden.

**B — Anfragen aus dem Echtkorpus (gewählt).** Die 89 Fälle sind echte
Nachrichten. Der Simulator zieht daraus, ruft denselben `/api/abrufweg`, den
die Eingabeleiste ruft, und zeigt damit **denselben Weg**, den der Speicher im
Betrieb ginge. Ein Vorführmodus, der nichts vortäuscht.

**C — Vorberechnete Wege abspielen.** Abgelehnt als Regelfall: schnell, aber
eine Aufzeichnung. Bleibt als Rückweg, falls die 3–4,5 s je Abruf die Vorführung
unbrauchbar machen — dann aber **sichtbar beschriftet** als Aufzeichnung.

## Was der Simulator tut

Ein Schalter „Vorführen". Solange er an ist, wird alle N Sekunden eine Anfrage
aus dem Echtkorpus abgesetzt. Jeder neue Weg löst genau das aus, was seit
`8389dc8` gebaut ist: der neue pulsiert, der vorige verglimmt. Damit zeigt der
Simulator nicht nur einen Weg, sondern **den Wechsel** — das, was man sonst
nur sieht, wenn man dabeisitzt.

Beschriftet wird jeder Durchlauf mit der Anfrage im Klartext. Der Betrachter
muss sehen können, worauf der Weg antwortet.

## Die Regler, und warum diese fünf

Nicht „stark/hell/schnell/intensiv" als vier Wörter für dasselbe, sondern die
Größen, die im Code wirklich getrennt sind:

| Regler | Wirkt auf | Bereich | Voreinstellung |
|---|---|---|---|
| **Helligkeit** | Grundwert der Deckkraft | 0,4 – 1,0 | 0,83 |
| **Pulsstärke** | Amplitude um den Grundwert | 0 – 0,35 | 0,13 |
| **Pulsdauer** | Periode der Welle | **1000 – 6000 ms** | 3200 |
| **Nachleuchten** | Verglimmdauer des vorigen Wegs | 1 – 15 s | 4 s |
| **Taktung** | Abstand zweier Anfragen im Vorführmodus | 8 – 60 s | 15 s |

**Die Untergrenze der Pulsdauer ist keine Geschmacksfrage.** 1000 ms sind 1 Hz;
WCAG 2.3.1 verbietet mehr als drei Blitze je Sekunde. Der Regler wird deshalb
bei 1000 ms hart begrenzt — nicht als Empfehlung, sondern als Anschlag. Das ist
die eine Stelle, an der die bestehende Direktive „Barrierefreiheit ist
Voreinstellung, keine Zwangsjacke" **nicht** greift: Sie erlaubt dem Nutzer,
für sich enger oder dichter einzustellen; sie erlaubt nicht, eine Grenze zu
überschreiten, die gegen einen körperlichen Schaden steht.

**Die Untergrenze der Taktung folgt aus der Messung:** Ein Abruf kostet 3 bis
4,5 s. Unter 8 s überholen sich die Anfragen, und man sähe nicht mehr, welcher
Weg zu welcher Frage gehört.

## Was bewusst nicht getan wird, samt Preis

- **Kein Regler für die Größe der Punkte.** Sie trägt bereits Bedeutung (die
  Stärke des Treffers); ein Regler darauf würde eine Messung zur Dekoration
  machen. Preis: weniger Einstellmöglichkeit.
- **Keine Speicherung der Reglerstände im Speicher.** Sie bleiben im Browser.
  Preis: nach einem Rechnerwechsel neu einstellen. Gewinn: kein Schreibpfad,
  keine neue Spalte, keine Frage nach dem Ausweis.
- **Kein Zufall ohne Wiederholbarkeit.** Die Reihenfolge der Anfragen ist die
  des Korpus; wer dieselbe Vorführung zweimal braucht, bekommt sie zweimal
  gleich.

## Woran sich Erfolg messen lässt

- Der Vorführmodus setzt echte Abrufe ab: Die gezeigten Wege sind mit einer
  Handeingabe derselben Anfrage **identisch**. Belegt, nicht behauptet.
- `prefers-reduced-motion` schaltet weiterhin jede Bewegung ab — auch im
  Vorführmodus, auch bei aufgedrehten Reglern.
- Die Pulsdauer lässt sich nicht unter 1000 ms stellen. **Rot-Probe:** Versuch,
  einen kleineren Wert zu setzen, wird abgewiesen.
- Jeder Reglerstand ist als Text ablesbar, nicht nur als Schieberposition.
- Die Schleife hält weiterhin an, wenn die Ansicht wechselt oder das Fenster
  verdeckt ist — der Vorführmodus darf daran nichts ändern.
