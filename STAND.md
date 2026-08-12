# STAND brainlehr — 2026-08-12T23:10:00+0200

## Warum die Regeln nicht greifen — gemessen, nicht vermutet

Drei Ursachen, getrennt (`ffc52b7`, `runs/regelgriff_2026-08-12.json`):

1. **Regel ohne Mechanismus** — 11 von 19 Abschnitten der globalen Hausregeln, darunter „Plan vor Umsetzung". Nachgestellt: Agenten-Auftrag über drei Dateien ohne Plan, beide Wächter `exit 0`.
2. **Mechanismus ohne Verdrahtung** — `ui_guard.py` 0 Treffer in `settings.json`; `push_guard.py` in brainlehr und 6 von 8 Repos nicht installiert.
3. **Keine projekteigene Ablage** — brainlehr hat weder `CLAUDE.md` noch `.claude/settings.json`.

**Wiederholungsfund:** `/shared/arch/fleet-audit-2026-07-verdrahtungsdefizit` hat dasselbe vor drei Tagen über 20 Arbeitsbäume gemessen. Erhoben, abgelegt, nicht verdrahtet — ein Befund ohne Folge ist dieselbe Fehlerklasse eine Etage höher.

**Der Beleg dafür, dass Verdrahtung wirkt, entstand aus Versehen** (`L-498f64`): Das Messskript brach selbst zwei Regeln, beide verdrahteten Wachen fingen es binnen Minuten. Was nur im Text steht, fiel erst auf, als der Betreiber fragte.

## Zwei Zahlen, kein Widerspruch — und der Korpus war schuld (`546e1b8`, `L-7318ce`)

„Stichwortkanal rettet keinen Fall und kostet zwei" gegen „ihn zu dämpfen kostet vierzehn": Beide richtig, beide beantworten eine andere Frage. Drei Unterschiede gleichzeitig — Korpus (35 synthetische gegen 89 echte Fälle), Pfad (`rrf_fuse` direkt gegen Produktionspfad), Vergleichsgröße (Kanal **entfernt** gegen **andere** Fusionsfunktion).

Der Defekt saß im Korpus: Die 35 Fälle wurden **aus den Zieltexten erzeugt** und können strukturell nicht zeigen, wozu ein Stichwortkanal da ist. Der Bias stand im Commit von damals und wurde beim späteren Vergleich nicht mitgelesen.

Neu gemessen: **7 von 44** Ziel-Instanzen echter Fälle, in denen der beste Treffer nur über den Stichwortkanal erreichbar war — gegen **0 von 35** synthetisch. Einschränkung: erste 30 der 89 Fälle, kein Zufallszug (ein Abruf kostet 3–4,5 s, Kosinus über 3508 Vektoren ohne Index). Vollmessung als Aufgabe 59.

## Betreiberanweisung 2026-08-12T20:00

„es darf nie wieder passeiren das wir sowas ohne plan bauen!" — abgelegt als `/methodik/direktiven/ohne-plan-wird-nicht-gebaut` (`0bd52cd8`). **Rang offen:** als Hausnorm Rang 1 vorgesehen, die Schranke verlangt einen menschlichen Entscheider. Der Rang wartet auf ihn.

Massgeblich ist die Aufgabenliste der Sitzung. `melder/offene_arbeit.py` zeigt beim Sitzungsstart den offenen Teil von `docs/SPRINTS.md`.

## Die Fehlerklasse dieses Tages, in acht Erscheinungsformen

Gemeinsam ist allen: nichts wurde gemeldet.

1. **Werkzeug tut still nichts** — `normbezug.py` meldete jedes Normzitat als unbelegt, weil sein Pfad ins Leere zeigte.
2. **Kanal stellt still nicht zu** — der Eilmeldungs-Haken war neun Stunden tot, `exit 0`.
3. **Aufzeichnung behauptet still Falsches** — die eingefrorene S12-Teilung. Widerrufen: der Fehler lag in *meiner* Gegenrechnung.
4. **Prüfer bestätigt das Gegenteil** — „§ 71 GEG" galt als *belegt*, obwohl der Treffer die Streichung dokumentiert. Behoben: Status `ausser_kraft`.
5. **Melder spricht über ein Siebtel** — `planbindung.py` sah 23 von 139 Abschnitten. Behoben, und beim Beheben entstand derselbe Fehler eine Ebene höher (`L-65d33e`, 2×).
6. **Eskalation ohne Empfänger** — 65 Einträge über vier Tage in eine Datei, die niemand liest (`L-14acea`).
7. **Regel schreibt, Prüfung fehlt** — auf den ersten Modellwissen-Vorfall folgte ein Dokument statt eines Testfalls. Vier Stunden später derselbe Fehler (`L-122b1c`).
8. **Bremse läuft nie** — die Kalibrierbremse wird mit `project_id=None` aufgerufen; die Schwellenprüfung erreicht kein Projekt. Im Code dokumentiert, im Selbsttest als Widerspruch sichtbar geworden.

## Erledigt seit 14:00

| | Commit |
|---|---|
| Regeln als wählbare Pakete, Rang kommt nie mit | `7013c04` |
| Lehren zwischen Instanzen, Prüfung an der Tür | `f6e0e63` |
| Eilmeldungen verfallen, Eskalation erreicht den Sitzungsstart | hub `336d32dfd`, `007630c` |
| Zweckprojektion: unbeschriebene Rolle bekommt nichts | `ec3a443` |
| Zweckprojektion wirkt in Suche und Blättern | `64bd010` |
| Diagnose: RRF gewichtet Rang, nicht Güte des Kanals | `06bb156` |
| `planbindung` sieht 79 statt 23 und nennt, was es nicht sieht | `f0f2c88` |

## Erledigt seit 17:30

| | Commit |
|---|---|
| `brainlehr.app` löst die Ausweisstelle ab, Wissensraum im Menü | `4dc33ef` |
| Abrufweg pulsiert, der vorige verglimmt — das Bild trägt sein Alter | `8389dc8` |
| Der Weg liegt im Bedeutungsraum, Helligkeit aus dem Kosinus statt aus dem Rang | `f21b766` |
| Fragen sterben nicht an einem Filter — sie nennen keine Adresse | `faf9f64` |
| Dienst legt seine Datenbank nicht mehr selbst an, Startpfade geprüft | `00e94e1` |
| `brainlehr.app` als echtes Bündel mit vollständiger Menüleiste | `c30a30b` |
| Schichtwache: Kern ohne Oberfläche, Schale ohne Datenbank | `403309f` |

Suite: 970 grün, 2 übersprungen, 11 xfail, 0 rot (vorher 945). Vektoren vollständig neu gerechnet (2963, 0 Fehler) — 0 Änderungen, aber jetzt gemessen statt geschlossen (`L-bc1499`).

**Der Korpus misst eine Bauform, nicht eine Frage** (`fa296b67`). Von 1903 eindeutigen Fragen nennen 0,9 % eine Adresse, von 776 Aufträgen 18,6 %. Kein Sammelkanal heilt das — gemessen, nicht vermutet. Jede veröffentlichte Abrufzahl braucht diesen Zusatz, sonst behauptet sie mehr als gemessen wurde (an Aufgabe 29 gehängt).

**Handprobe offen:** `prefers-reduced-motion` ist für Baum, Bedeutung und Spuren nur gelesen, nicht am laufenden Bild gesehen — die Browser-Werkzeuge können die Systemeinstellung nicht umschalten. Dieselbe wiederverwendete Bedingung wie in Ansicht 4, die reine Funktion ist darauf geprüft. Ein Schluss, keine Sichtprobe.

## Wartet auf den Betreiber

Aufgabe 20 und 23 gehören zusammen (Ausweisordner sichern, Geheimnis rotieren, Eintrag aus `~/.claude.json`).
Aufgabe 7: MAUDE-Import lädt über das Netz — Download braucht das ausdrückliche Wort.
Aufgabe 31: alle 808 Lehren stehen auf `intern`; der Austausch läuft leer, bis jemand freigibt.
Aufgabe 29: Der öffentliche Schnitt ist **vorbereitbar** — beide Ausgangszustände sind gefahren (`e2ff82d`), beide tragen. Frisch nach README benutzbar, Aktualisierung vom alten Schema additiv und verlustfrei, kein ausgeliefertes Werkzeug setzt eine nur hier entstehende Tabelle voraus. Damit ist der Zustand von `L-96db3e` belegt behoben. Offen vor einer Veröffentlichung: `--bestand`/`--vektoren`, ein MCP-Rundlauf über einen **neu gestarteten** Klienten, `doctor.py` als eigenständiges Kommando. **Push bleibt ein Stopp-Punkt.**

## Nicht vergessen

Ein Melder nennt **drei** Zahlen: vorhanden, geprüft, beanstandet (`L-65d33e`).
Ein Prüflauf, der nichts ändert, verwandelt eine Annahme in eine Messung (`L-bc1499`).
Wenn die Antwort auf einen Vorfall ein Dokument ist und kein Testfall, ist die Wiederholung eingeplant (`L-122b1c`).
Kein `git stash` für Rot-Proben (`L-56a352`). Läufe über zehn Minuten nicht in Subagenten (`L-1056bb`).
