# Plan: Sicherheit und Überwachung des Dokumentdienstes

**Stand** 2026-08-14T13:0x+0200 · **Zweig** `brainlehr/b4-ausweis`
**Anlass** Betreiber, 2026-08-14: LAN öffnen für den Mini im selben Netz, und
*„der Security Aspekt ab jetzt noch mal deutlicher mitdenken und ein Monitoring
mit vorbereiten"*.

---

## 1 · Die Reihenfolge ist der eigentliche Inhalt

**Grenze vor Melder.** Ein Monitoring ohne Zugangskontrolle meldet nur, *dass*
eingebrochen wurde. Deshalb standen die Schranken vor den Zahlen — sie sind
gebaut (`14b34f3`), bevor dieser Plan geschrieben wurde:

| Schranke | Bauform |
|---|---|
| Anmeldung | Auf allem außer `127.0.0.1` ist ein **beglaubigter Ausweis** Pflicht (`kern/ausweis.loese_auf`, scrypt, zeitkonstant). Eine **Regel**, kein Schalter |
| Nachrichtengröße | `max_size` von `websockets`, 1 MiB — abgebrochen, bevor es Speicher kostet |
| Rate | 2000 Nachrichten je 10 s und Verbindung, großzügig: Zeichen-für-Zeichen erzeugt viele kleine Updates |
| Protokoll | Nur `anmelden` und `update`. Alles andere wird **benannt**, nicht verschluckt |

## 2 · Was gemessen wird — Zahlen ohne Urteil

`Kennzahlen` in `kern/dokumentdienst.py`. Bewusst **ohne Schwellen**:

| Zahl | Was sie verrät |
|---|---|
| `verbindungen` | Grundrauschen; Nenner für alles andere |
| `herkunft` (je Adresse) | ein zweites Gerät, wo nur eines stehen soll |
| `abgewiesene_zugaenge` | das erste, was ein Scanner auslöst |
| `abgelehnte_updates` | falscher Klient — oder jemand, der etwas anderes schickt |
| `unbekannte_arten` | jemand spricht ein anderes Protokoll |
| `kennungsverstoesse` | ein Klient, der die 2³²-Auflage nicht kennt |
| `gebremste_nachrichten` | Überflutung |
| `updates`, `bytes_empfangen` | Normalmaß, aus dem die Schwellen erst entstehen |

## 3 · Wann eine Warnung ausschlägt

**Zwei Klassen, und nur die erste ist heute entscheidbar.**

**Sofort, ohne Schwelle** — Vorgänge, die im Normalbetrieb *nie* vorkommen:
- ein abgewiesener Zugang (auf loopback gibt es keine Anmeldung, im LAN kennt
  der eigene Klient das Wort)
- eine unbekannte Nachrichtenart
- ein Kennungsverstoß
- eine **zweite** Herkunftsadresse, solange nur ein Gerät angemeldet sein soll

**Erst nach einer Nullmessung** — alles Mengenhafte (`updates`,
`bytes_empfangen`, Verbindungen je Stunde, Dokumentwachstum). Hier wird
**keine Zahl erfunden**: erst mit dem Mini eine Stunde Normalbetrieb messen,
dann die Schwelle darüber legen. Eine geratene Schwelle schlägt entweder nie
an oder ständig — und ständig heißt: weggeklickt. Genau diese Fehlerklasse hat
heute schon zweimal zugeschlagen (`L-528f0c`).

**Der Nenner gehört zu jeder Quote.** Vor jeder Aussage der Form „X % sind
auffällig" wird hingeschrieben, welche Bedingung diesen Wert überhaupt erlaubt
— sonst misst man die eigene Abfrage statt die Lage.

## 4 · Aufträge, fertig zum Übergeben

**Für alle gleichermaßen:** Arbeitsort `/Volumes/daten/Begod2026/brainlehr`,
Zweig `brainlehr/b4-ausweis` — ein Startverzeichnis unter `.claude/worktrees/`
ist ein alter Stand. Zuerst `CLAUDE.md` hier und in `~/.claude/` lesen, dann
diesen Plan. „Sieht der Code anders aus als hier beschrieben, halte dich an den
Code und melde die Abweichung." Kein `git add -A`, kein Push, kein `git stash`.
Committen mit expliziter Pfadliste. Volle Python-Suite **im Vordergrund** mit
`timeout=600000`. Neues Modul mit `--selftest` gehört in `MODULE` in
`tests/test_alle_selftests.py`. **Kein Geheimnis in Protokoll, Meldung oder
Testausgabe — auch nicht gekürzt.**

### Auftrag S1 · Die Kennzahlen verlassen den Prozess

| | |
|---|---|
| **Darf ändern** | `kern/dokumentdienst.py` (nur die Ausgabe), neue Datei unter `melder/`, deren Tests |
| **Tabu zusätzlich** | `kern/ausweis.py`, `kern/teilnehmer.py`, `schema.sql` — **keine neue Tabelle**, die Kennzahlen sind eine Datei |
| **Fakten** | `Kennzahlen.als_dict()` liefert heute acht Zahlen plus `herkunft`. Der Dienst hält sie **nur im Speicher**; ein Neustart setzt sie auf null, und genau das macht sie als Beleg wertlos, sobald der Dienst länger läuft als eine Sitzung. Vorbild für die Ausgabeform: `runs/*.json` mit Zeitstempel aus `kern/zeitmarke.jetzt` (UTC, `Z`-Form — jede andere Form wirft, Aufgabe 111). |
| **Abnahme** | Rot vor grün: der Dienst wird gestartet, ein Klient verbindet, die Zahlen stehen **nach einem Neustart** noch da — vorher waren sie weg. Negativfall: ein Lauf ohne jede Verbindung schreibt eine Zeile mit Nullen, keine leere Datei — Schweigen und „nichts passiert" müssen unterscheidbar bleiben. Grenzwert: erste Zeile überhaupt, Zeile nach genau einem Ereignis, Zeile nach einem Neustart. |

### Auftrag S2 · Der Melder, aber nur die schwellenfreie Klasse

| | |
|---|---|
| **Darf ändern** | die Melder-Datei aus S1, deren Tests |
| **Tabu zusätzlich** | alles Mengenhafte — `updates`, `bytes_empfangen`, Verbindungen je Stunde bekommen in diesem Auftrag **keine** Schwelle |
| **Fakten** | Vorbild für Bauform und Anschluss: die vorhandenen Melder unter `melder/` (jeder mit `--selftest`, Einbindung über `~/.claude/settings.json`). Achtung, gemessen am 2026-08-14: ein Eintrag dort kann **wieder verschwinden** — `WorktreeCreate` war nach 36 Minuten weg (`L-083b95`). Der Melder braucht deshalb eine Probe, die seine eigene Verdrahtung prüft, nicht nur seine Logik (`L-b3eb79`: gebaut ≠ verdrahtet ≠ wirksam). |
| **Abnahme** | Rot vor grün je Fall: abgewiesener Zugang, unbekannte Art, Kennungsverstoß, zweite Herkunftsadresse — jeder schlägt an. Negativfall, und er ist der wichtigere: ein ganz normaler Lauf (eine Adresse, nur `update`) schlägt **nicht** an. Grenzwert bei der Herkunft: eine Adresse, zwei Adressen, dieselbe Adresse zweimal. |

### Auftrag S3 · Nullmessung mit dem Mini, danach erst Schwellen

| | |
|---|---|
| **Darf ändern** | eine Ergebnisdatei unter `runs/`, danach die Schwellen im Melder |
| **Tabu zusätzlich** | Schwellen **vor** der Messung zu setzen. Wer eine Zahl schreibt, bevor sie gemessen ist, hat den Auftrag verfehlt |
| **Fakten** | Der Mini hängt im selben Netz; der Dienst läuft mit `--lan` und verlangt dort einen beglaubigten Ausweis. Normalbetrieb heißt: ein Mensch tippt, ein Modell antwortet. |
| **Abnahme** | Eine Datei unter `runs/` mit Zeitraum, Nenner und den acht Zahlen. Erst danach eine Schwelle je mengenhafter Größe, und jede trägt im Kommentar die Zahl, aus der sie stammt. Negativfall: die Schwelle wird gegen den gemessenen Normalbetrieb geprüft und schlägt dabei **nicht** an. |

## 5 · Was bewusst nicht gebaut wird

- **Kein Fremdwerkzeug** (Prometheus, ELK, IDS). Acht Zahlen und eine Datei
  brauchen keinen Stapel, der selbst überwacht werden will.
- **Keine Verschlüsselung der Verbindung.** Im eigenen Netz mit Ausweis ist
  der nächste sinnvolle Schritt TLS — aber erst, wenn der Dienst das Netz
  verlässt. Preis benannt: wer im selben Netz mitliest, sieht den Inhalt.
  **Das Geheimnis wandert im Klartext über die Verbindung** — für ein
  Heimnetz vertretbar, für alles andere nicht.
- **Keine Sperre nach n Fehlversuchen.** Zuerst messen, wie oft das im
  Normalbetrieb passiert; eine Sperre, die den eigenen Klienten aussperrt,
  wird abgeschaltet und ist dann keine.

## 6 · Der breitere Aspekt, ohne eigenen Bau

Für sicherheitsrelevanten Code gibt es den Auslöser bereits: berührt eine
Änderung Geheimnisse, Anmeldung, Verschlüsselung, Abhängigkeiten, Datenbank
oder Nutzereingaben, wird der `compliance`-Agent gerufen (BSI-Profil, eigener
Kontext). Der Dienst fällt darunter — **dieser Plan ersetzt den Aufruf nicht.**
