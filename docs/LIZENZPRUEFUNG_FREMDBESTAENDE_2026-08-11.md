# Lizenzprüfung der acht offenen Fremdbestände — 2026-08-11

Geprüft von einer eigenen Stimme mit eigenem Rohzugang (Opus, 37 Werkzeugaufrufe),
Urteil in der Prüfspruch-Kette (#7). Anlass: der Einwand des Betreibers, für
Trainingszwecke reiche Zitieren.

**Der Einwand hat sich als teilweise richtig erwiesen — und die Prüfung zeigt
genau, wo er trägt und wo nicht.** Deshalb drei Spalten statt einer Ampel.

Das Register selbst (`docs/FREMDBESTAENDE.md`) liegt auf dem Zweig
`brainlehr/b4-ausweis`, nicht in diesem Arbeitsbaum. Es wurde **nicht** hierher
kopiert — eine zweite Fassung derselben Datei wäre die Doppelarbeit von heute
Vormittag noch einmal. Diese Datei ist der Befund; das Register gehört dort
nachgezogen.

## Ergebnis

| Quelle | Auswertung/TDM | Weitergabe | Personenbezug |
|---|---|---|---|
| ASRS | 🟢 | 🟢 | 🟢 de-identifiziert (Betreiberaussage) |
| NIST | 🟢 | 🟢 mit Auflage | keiner |
| FAA Lessons Learned | 🟢 | 🟡 Quelle schweigt | ungeprüft |
| FDA MAUDE | 🟢 | 🟡 | 🟡 **Art. 9 bestätigt** |
| ESA | 🔴 | 🔴 | ungeprüft |
| NRC LER | 🔴 nicht feststellbar | 🔴 | ungeprüft |
| CROSS | 🔴 | 🔴 | Quelle schweigt |
| IAEA IRS | 🔴 kein Zugang | 🔴 | entfällt |

## Der Befund, der den Vorschlag „für Training reicht zitieren" begrenzt

**CROSS sperrt genau die Nutzung, um die es ginge.** In `robots.txt` steht je
ein `Disallow: /` für `CCBot`, `GPTBot`, `ChatGPT-User` und `Google-Extended`.
Das ist ein maschinenlesbarer Rechtevorbehalt im Sinne von **Art. 4 Abs. 3
DSM-Richtlinie** — er schaltet die TDM-Schranke ab, auf die sich eine
Trainingsnutzung stützen müsste. Ein Zitat ändert daran nichts, weil das Zitat
die Namensnennung regelt und nicht die Erlaubnis.

*Selbst nachgeprüft* am 2026-08-11 per `curl` gegen `cross-safety.org/robots.txt`
(HTTP 200): die vier Einträge stehen dort wörtlich. Das ist der einzige Befund
dieser Prüfung, den ich nicht auf Zuruf übernommen habe — weil die ganze
Entscheidung daran hängt.

## Der zweite folgenreiche Befund: eine freie Lizenz löst keinen Personenbezug

**FDA MAUDE steht unter CC0 1.0**, ausdrücklich auch kommerziell — urheberrechtlich
also frei. Trotzdem bleibt der Art.-9-Vermerk im Register **bestätigt**: openFDA
schwärzt nur personen- und medizinbezogenen Text nach FOIA `(b)(6)`. Alter,
Geschlecht, Gewicht, Ethnie und die Freitext-Berichte zu Tod und schwerer
Verletzung bleiben stehen. Das Risiko ist durch die Redaktion **entschärft, nicht
aufgehoben**.

Die Gegenprobe macht den Unterschied sichtbar: Bei **ASRS** sagt der Betreiber
selbst, alle Berichte seien de-identifiziert und die Identität des Melders
dauerhaft entfernt — deshalb dort grün. Zwei US-Behördenbestände, dieselbe
Lizenzlage, verschiedene Antwort. Die Lizenz war nie die Frage.

## Wo 17 U.S.C. §105 nicht trägt

Vier Lücken, jede bei mindestens einer unserer Quellen einschlägig:

1. Nur Werke von Bundesbediensteten im Dienst — **ASRS wird von einem
   Auftragnehmer betrieben**, Aufbereitungen sind nicht automatisch erfasst.
2. Eingebettete Drittinhalte (Herstellergrafiken, Pressefotos; bei NIST
   ausdrücklich „material marked as copyrighted").
3. §105 ist US-Recht **ohne Entsprechung im deutschen UrhG** — an der *Sammlung*
   kann hier ein sui-generis-Datenbankrecht (§ 87a UrhG) bestehen, auch wenn der
   einzelne Bericht gemeinfrei ist.
4. Vertragliche Bedingungen und technische Sperren binden unabhängig vom
   Urheberrecht — **NRC** ist genau dieser Fall.

## Nebenbefunde, die das Register betreffen

- **ESA**: Auf `esa.int` ist gar kein öffentlicher Lessons-Learned-Bestand
  erreichbar. Die Registerzeile zeigt auf nichts Abrufbares.
- **NRC**: Jeder Zugriff aus dieser Umgebung wird am Akamai-Rand mit HTTP 403
  abgewiesen — **auch `robots.txt`**. Damit ist weder Erlaubnis noch Vorbehalt
  feststellbar, und ein Massenabruf wäre die Umgehung einer aktiven Sperre.
- **NIST**: Der Teilbestand ist im Register weiterhin unbenannt; die Auflage
  (Byline, Änderungshinweis) gilt je Teilbestand.
- **accessdata.fda.gov** (die Weboberfläche, nicht openFDA) hat aktive
  Missbrauchserkennung — bereits eine einzelne Anfrage lief in eine
  „excessive requests"-Seite. Import nur über die offiziellen Massendownloads.

## Was daraus folgt

**Für Auswertung und Training nutzbar: ASRS, NIST, FAA, FDA MAUDE** — vier von
acht. Damit hatte der Betreiber der Sache nach recht, nur nicht in der
Begründung: es trägt die TDM-Schranke, nicht das Zitat.

**Für die Weitergabe im offenen Auszug: ASRS und NIST** (NIST mit Auflage). Bei
FAA und MAUDE schweigt die Quelle beziehungsweise steht der Personenbezug
entgegen — dort greift die schwächere Belegform: kurzes lokales Zitat plus
Adresse plus Prüfsumme eines Archiv-Schnappschusses, ausdrücklich als solche
gekennzeichnet.

**Nicht anfassen: CROSS, ESA, NRC, IAEA.**
