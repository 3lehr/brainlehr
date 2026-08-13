# STAND brainlehr — 2026-08-13T14:30:00+0200

## Die älteste Sperre fiel — sie war ein Fehler in meiner eigenen Notiz

„Nicht zuordenbare Differenz: 45 gegen 33 von **205**". An der Quelle gemessen:
Die 33 ist **33 von 35**, aus `runs/messlauf_abrufguete_v2.json` über
`pruefkorpus_v2.jsonl`. Die 45 ist 45 von 205 Ziel-Instanzen über 89 echte
Fälle. **Zwei Korpora, zwei Nenner, zwei Einheiten** — ich hatte beim Verkürzen
den Nenner der einen Zahl auf die andere übertragen.

Die Werte widersprechen sich nicht nur nicht, sie **bestätigen** einen bekannten
Befund: Der 35er-Korpus ist aus den Zieltexten erzeugt und misst den leichten
Fall (34,1 % wörtliche Überschneidung gegen 10,7 %).

**Auflage statt Sperre:** Jede Abrufzahl nennt **Nenner und Korpus**. `45`
allein ist keine Aussage (`L-ee64d5`).

## Die Suite hing am Heimatverzeichnis — aufgedeckt durch eine Nebenwirkung

Die Geheimnis-Rotation erzeugte eine Datei, die es vorher nicht gab. Plötzlich
hatten **14 Tests** eine Identität, wo sie „unbekannt" erwarteten. Der eigentliche
Befund ist nicht die Rotation: **Die Suite war auf keinem anderen Rechner
reproduzierbar**, und niemand hätte es je gemerkt. Ein Selbsttest lief sogar nur
zufällig grün. Jetzt isoliert eine Vorrichtung jeden Test, ein eigener Test
belegt die Isolierung.

## Vier Ausprägungen einer Fehlerklasse an einem Tag

`grep`-Treffer für Prüfung gehalten (`L-bee002`) · Wahrheitswert statt Wortlaut
gelesen · Kodierung angenommen statt gelesen (base64 gegen hex, hätte alle
Sitzungen ausgesperrt) · Ursache angenommen statt gemessen (Aufgabe 92: „reist
nicht mit" — tatsächlich existierte die Datei schlicht nicht).

**Gefangen hat sie jedes Mal jemand anderes** oder eine Gegenprobe in **beide**
Richtungen. Daraus Aufgabe 97, Peer Review als Bauform — und der Einbauort ist
`PreToolUse` auf das Agent-Werkzeug, weil `SubagentStart` nicht blockieren kann
und dem Modell nicht sichtbar ist.

## Was gebaut wurde

| | |
|---|---|
| Dublettenerkennung beim Anlegen | `a0cd9d2` — zwei Signale zusammen; eine niedrigere Einbettungsschwelle hätte bei 0,60 **112** Treffer je Knoten erzeugt |
| Herkunftskette | `462f527` — 1 Angabe wird zu **229 Kanten auf 126 Knoten**; die Differenz belegt, warum eine Spalte falsch gewesen wäre |
| Kanalwahl an Anfragelänge | `a31f6f7` — die Zerlegung erkannte CJK **gar nicht**, eine japanische Anfrage war leer, `count=0` vor jedem Kanal |
| `WorktreeCreate`-Haken | `aaf18b5` |
| eigene `CLAUDE.md` | `67d8c56` — das einzige Repo ohne eine |
| Freigabe | 145 Knoten geöffnet, `/ops` `/openlehr` `/apps` `/shared` **0** |

## Offene Schemafrage (Aufgabe 100)

`knowledge_relations` referenziert per Fremdschlüssel `knowledge_nodes.path` —
eine **Lehre hat keinen Pfad**. Inzwischen umgehen **zwei** Werkzeuge deshalb den
gekapselten Schreibpfad, und die Naht-Ratsche musste zweimal gelockert werden.
Das ist kein Sorgfaltsproblem, sondern eine Annahme im Schema, die nicht mehr
stimmt: dass alle Kantenenden Knoten sind. 229 Kanten sagen das Gegenteil.

## Stand 13:15 — die Befunde des Mittags

## Die fehlende Hinsicht — sechs Stellen, eine Form (`012500e5`)

Auf Betreiberfrage *„wo taucht das noch auf?"*: **Eine Aussage trägt einen
Wahrheitswert nur zusammen mit der Hinsicht, in der sie gilt.** Katze und Delfin
sind beide Säugetiere, nur einer mag Wasser.

5814 Kanten ohne die Angabe **worin** ähnlich · Schwelle `0,65` für Rechtsfrage
und Funktionsnamen gleich · kein Rechtsraum · Zeit nicht im Vektor (2026 und
2020 ununterscheidbar nah) · `trigram` im Deutschen tauglich, im Japanischen
blind · zwei Ausgangszustände frisch gegen gewachsen.

**Prüffrage vor dem Bau:** *Gibt es einen Fall, in dem dieselbe Aussage hier wahr
und dort falsch ist?* Wenn ja, gehört die Hinsicht ins **Datenmodell**, nicht in
den Fließtext — dort wird sie beim Vergleichen nicht mitgelesen.

Der unangenehme Teil: Sichtbar wurde die gemeinsame Form erst, als der
**Betreiber** fragte. Alle sechs Befunde lagen im Speicher.

## Zwei Sorten von „brainlehr sagt" — und die erste Hälfte ist gebaut

Ab sofort gilt: Stammt eine Aussage aus dem eingespielten Block, wird sie
zugeschrieben. Anlass war ein Befund samt Zahlen, den ich als eigene Aussage
weitergegeben habe; er war sechs Tage alt und aus einem Codestand, den es nicht
mehr gibt.

Dazu die Unterscheidung **eigene Regel** gegen **fremdes Zitat**. Gemessen war
`norm_art` bei **0** von 2166, `gilt_bis` bei **2**, örtliche Geltung **kein
Feld**, und 1919 Knoten stehen auf `offen`.

**Gebaut** (`ccc9afd`): `norm_art` ist Pflicht, sobald die Quelle einen fremden
Satz nennt — Gesetz, DIN, ISO, BSI, Urteil. Eigenes Wissen läuft ohne durch.
Wertemenge war bereits entschieden (`sein`/`sollen`/`dürfen`, Knoten `dd367fd1`)
und wurde **übernommen, nicht neu erfunden**.

Damit ist die Vorbedingung für den Rechtsraum erfüllt: Es ist jetzt
entscheidbar, für welche Zeilen Ablauf und Ort überhaupt verlangt werden — die
Handvoll fremder Zitate statt aller 2166. Der Rechtsraum kommt als
**hierarchischer Pfad** (`/EU/DE/NI`), weil brainlehr dieses Idiom ohnehin
benutzt und „gilt das hier?" damit ein Präfixvergleich ist
(`docs/PLAN_RECHTSRAUM_2026-08-13.md`).

**Nebenbefund aus dem Bau:** Die Markerliste des älteren
`normrang_herkunft`-Triggers enthielt `%EN %` und traf damit gewöhnliches
Deutsch („Impressen (", „Knoten unter"). Vorher unauffällig, weil dieser Trigger
nur bei `norm_rang IN (1,2)` lief.

## Stand 08:55 — die Befunde des Vormittags

## Die Regel gegen wirkungslose Mechanismen gab es schon — vor Monaten

`spaghetti-monster` aus der Stiftshütte prüft nicht nur Code, sondern den
**Prozess**, und trägt wörtlich die Regel *„Agent ohne Trigger in 5+ Sessions →
Sunset-Kandidat"*. Kein Veto, nur Hinweisrecht, ausgelöst „proaktiv bei
Gruppendenken und ‚das ist offensichtlich'-Momenten".

Das ist genau der Melder, der in dieser Nacht **zwölfmal von Hand** gespielt
wurde. Der Verlust ist kein Denkfehler, sondern eine Eigenschaft des
Plattformwechsels: Bei einem Umzug wandern die **Artefakte**, die man sieht.
Eine Rolle, deren einziger Wert ihr **Auslöser** war, hat keinen Gegenstand, den
man mitnehmen könnte. Prüffrage für den nächsten Wechsel: nicht „welche Dateien
nehmen wir mit", sondern **„was hat sich von selbst gemeldet, und wer tut das
jetzt?"** (Knoten `e5b68f3a`, Aufgabe 85, `docs/AGENTENBESTAND_2026-08-13.md`.)

Erhebung nachgeprüft, drei Angaben des Agenten waren falsch: 81 Rollendateien
statt 58, das Feld `agent_count` existiert nicht, und `aufsaetze/agenten.py`
vermisst nichts. Der alte Bestand nennt dabei **drei Zahlen für sich selbst** —
81 Dateien, 75 Indexeinträge, 77 Routingzeilen. Ein gepflegter Index statt eines
erzeugten; genau die Bauform, die hier abgeschafft wurde.

## Der Speicher schlägt 55 Dinge vor, und niemand sieht sie

`berichte/vorschlag.py` liefert **25 Prüfstein- und 30 Fähigkeit-Kandidaten**,
je mit fertigem Auftragsentwurf aus der Lehre. Verdrahtung: **0** in beiden
Regelablagen. Zwölfte Erscheinungsform.

Es kennt **keine Agenten** — wann einer zu starten wäre, steht nirgends, obwohl
der Bestand die Daten trägt. Ein Laden oder Entladen von Fähigkeiten wurde
gesucht und **nicht gefunden**. Die eigene Sperre benennt das Werkzeug ehrlich:
*„die Bedingung für automatisch starten ist die maschinelle Abnahme, und die
fehlt noch."* Die Sperre ist richtig; sie steht nur an der falschen Stelle,
solange der Bericht überhaupt niemanden erreicht. (Aufgabe 84.)

## Der Stop-Haltepunkt liefert — die Existenzprüfung hängt trotzdem im Leeren

Aus 5642 Transcript-Datensätzen `system/stop_hook_summary` im ganzen Verbund:
Der Stop-Kanal löst aus, in brainlehr allein **949-mal**, je acht Haken, zuletzt
heute 05:27:55. **`haken/existenzpruefung.py` kommt in 0 von 949 vor.**

Die acht laufenden Haken stehen alle mit absolutem Pfad in
`~/.claude/settings.json`. Der Stop-Eintrag in der projekteigenen
`brainlehr/.claude/settings.json` — gestern Nacht angelegt, um die globale Datei
nicht anzufassen — hat nie gewirkt. Jedes Stop-Ereignis lief mit einem
Arbeitsbaum unter `.claude/worktrees/` als Verzeichnis, nie im Hauptbaum.

**Warum die Nachbardateien nichts beweisen:** `hookInfos` wird ausschließlich
für `stop_hook_summary` protokolliert (5642 von 5650 Datensätzen). Die
projekteigenen Einträge von fahrtenbuch (`UserPromptSubmit`) und buckeberg
(`PostToolUse`) sind in diesem Datensatztyp gar nicht sichtbar — über sie ist
damit **nichts** gesagt, weder in die eine noch in die andere Richtung.

Zehnte Erscheinungsform derselben Bauform: gebaut, gemeldet, in null Fällen
wirksam. Diesmal war die Ursache die **Vorsicht** — der Plan wählte die
projekteigene Ablage ausdrücklich, um fremde Sitzungen nicht zu treffen, und
genau diese Wahl ist der Grund, warum nichts ankam.

## Vorsorge für einen Zustand, den es noch nicht gibt: der Ausschreibekatalog

`impl` steht **0-mal** im Bestand, die lange Form **133-mal** (`339eaee`).
Trotzdem tritt der Schaden heute nicht ein: über **7649** protokollierte Suchen
kommt `impl` **zweimal** vor, `res`/`msg`/`err`/`val`/`param` je **null**.
Grund — Caveman ist nicht verdrahtet, alle 7649 Suchen stammen aus
unkomprimierten Antworten.

Daraus die Bauform (`16453e8`): Gelernt wird aus dem **Bestand** (Zähler kurz
gegen lang), nicht aus dem Protokoll — dort steht kein einziges Beispiel. Der
Protokollkanal kommt als zweiter dazu, sein heutiger Nullwert ist die
Nullmessung. Übersetzt wird nur die **Anfrage**, mit beiden Formen per ODER,
nie der gespeicherte Text (`L-d8c5fb`: „TG" wurde still zu „Tiefgarage"
aufgelöst und wanderte in sieben abgeleitete Fundstellen, zwei davon
öffentlich).

## Herkunft: das Feld ist da, die Werte sind es nicht

`access_log.model` ist zu 86 % „gefüllt" — davon sagen **6395 von 10117**
wörtlich `unbekannt`, weitere 1426 sind leer. Echt brauchbar: **22 %**. Bei den
Knoten 12 %.

Zwei Fehler verhindern jede Auswertung, bevor sie beginnt: **drei
Schreibweisen für ein Modell** (`claude-opus-5`, `Anthropic/claude-opus-5`,
`Anthropic/Opus 5`) und **zwei Arten von Nichtwissen** (`unbekannt` als Text
neben NULL). Wer gruppiert, bekommt drei Gruppen und merkt es nicht.

Deshalb **kein** neues Feld für den Antwortmodus (Aufgabe 79): Der Prüfer meldet
bereits zehn Spalten mit 98–100 % Leerstand. Und die Reihenfolge ist bindend —
solange Caveman nicht wirkt, zeichnet ein Modusfeld eine Konstante auf.

## Ein Vektor kennt nur seinen Modellnamen, nicht seine Parameter (Aufgabe 80)

**KORRIGIERT 13:20.** Der frühere Absatz hier behauptete, der Lesepfad prüfe das
Modell nicht. **Das war falsch, und der Fehler war meiner:** Ich hatte einen
Agentenbefund mit einem `grep`-Treffer für geprüft gehalten, statt die Fundstelle
zu lesen. Nachgelesen filtern **alle drei** Leser auf `model` —
`_embedding_ranking` mit ausführlicher Begründung und zusätzlichem Dedup,
`kanten_aus_bedeutung` ebenso, und die Zeile in `suchpfad_abruf.py` gehört zum
**Selbsttest** und filtert auch. Die beschriebene Lücke gab es nicht (`L-bee002`).

**Was übrig bleibt und weiterhin gilt:** Die Identität eines Vektors ist allein
der **Modellname**. Parameter, die den Vektor verändern, ohne den Namen zu
ändern, sind darin nicht enthalten — `num_ctx` ist genau so einer.

**Das macht Aufgabe 80 zur Vorbedingung von Aufgabe 69, nicht umgekehrt.** Wird
`num_ctx` angehoben und der Bestand neu gerechnet, entstehen Vektoren desselben
Modells mit derselben Dimension, aber anderer Abschneidegrenze. Die
Längenprüfung greift dann nicht, weil die Länge stimmt — alte und neue Vektoren
werden während des Laufs als vergleichbar behandelt, still.

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

## Die Okkultation ist gefahren — und liefert ein Instrument, keine Antwort (`fec7684`)

M1 zwölf Fälle: **mit** Einspielung 1, **ohne** 0, **Negativkontrolle** 0. **Ein Fall Unterschied bei n=12 ist kein Ergebnis.**

Was trägt: Von den zwölf lieferte der Abruf das Ziel in **sechs**. Diese Quote hängt nur am Abruf — mindestens die Hälfte des Problems liegt **vor** jeder Nutzungsfrage.
Was nicht trägt: Von diesen sechs erschien eines in der Antwort. Beruht auf einer **Ersatzaufgabe**, weil die echten Prompts mehrseitig sind — Hinweis, kein Beleg.
Was gehalten hat: Die Negativkontrolle (längengleicher Block aus 1641 fremden NASA-Knoten) erzeugte 0 von 12 — der Versuch misst nicht die Blocklänge. Der Selbstbezug vom 07.08. ist ausgeschlossen.

Zum Abschließen fehlen: größere Fallmenge · echte statt Ersatzaufgabe · Negativkontrolle für M2 · Nachweis, dass die antwortenden Agenten keine Werkzeuge benutzten.

## Neunte Erscheinungsform geschlossen: die Kalibrierbremse ist ausgebaut (`008a223`)

Die Entscheidungsregel ergab **B**, nicht A. Etikettierte Abruffälle je Projekt: `shared` 12, `brainlehr` 8, `begod` 7, `fahrtenbuch` 4 — ADR-035 eichte den gemeinsamen Wert mit 24 Aufgaben und nannte das die Grenze zur Überanpassung. Ein Bruchteil davon je Projekt ist Raten mit Nachkommastellen.

**Nebenfund:** Der xfail, der die Widersprüchlichkeit maskierte, verdeckte einen **zweiten**, unabhängigen Fehler. Ein xfail, der zwei Dinge verdeckt, ist die Bauform, in der ein Fehler jahrelang überlebt.

## Jede Einbettung wird bei 8000 Zeichen gekappt — durch einen Vorgabewert (`0b1ab4c`)

Gemessen: Ab **2048 Token** ist der Vektor exakt gleich, unabhängig vom Suffix. Das ist Ollamas `num_ctx`, **nicht** bge-m3s 8192-Token-Grenze; im Repo überschreibt nichts diesen Wert. Belegverfahren: gleicher Anfang, **verschiedenes Ende**, identischer Vektor — Ähnlichkeit wäre Konvergenz, Gleichheit ist Abschneiden.

Bestand: **9 von 2163 Knoten** über der Grenze, längster 33908 Zeichen. **0 von 832 Lehren.** Entscheidung offen (Aufgabe 69): `num_ctx` anheben und alles neu rechnen · die neun teilen · die Grenze dokumentieren.

**Zweiter Anfragevektor NICHT gebaut** (Aufgabe 39): Er findet überwiegend anderes (7,56 von 15 Treffern nur über ihn), aber belegt ist nur *anders*, nicht *richtig* — und **46,7 %** der Einspielungen tauchen in der Folgeantwort wieder auf. Bedingung zum Weiterbauen: blinde Relevanzbewertung plus Antwort auf die Rückkopplung.

**Aufgabe 40, Prämisse widerlegt:** In der Ausgabe wird **nichts** gekürzt — Titel, Zusammenfassung, Beschreibung und Vorbeugung erscheinen vollständig. Begrenzt ist die **Anzahl** (10 Knoten, 7 Lehren) und die Feldwahl. Offen ist nur noch, ob der Betreiber die Blöcke in seinem Fenster überhaupt sieht.

## Nachtschicht 2026-08-13: gemessen, entschieden, verdrahtet

| | Commit |
|---|---|
| Widerspruch im Stichwortkanal aufgelöst — drei Unterschiede, kein Widerspruch | `546e1b8` |
| Beide Ausgangszustände der Fremdinstallation gefahren, beide tragen | `e2ff82d` |
| Okkultation: Instrument geliefert, Antwort noch nicht | `fec7684` |
| Kalibrierbremse ausgebaut — Messung ergab B, nicht A | `008a223` |
| Bauform des Nachbarn gelesen — mein eigener Auftrag war falsch | `97a5946` |
| Drei Zahlen vor dem Antwortvektor, eine betrifft den Bestand | `0b1ab4c` |
| Der Monitor zeigt die **Frage**, nicht nur die Antwort | `711a3e6` |
| Existenzprüfung verdrahtet — projekteigen, Verdrahtung selbst geprüft | `24c2484` |
| Zweite Oberfläche stillgelegt, samt Wache gegen ihre Wiederkehr | `28b5c05` |

Suite: **1035 grün, 2 übersprungen, 10 xfail, 0 rot.**

**Zwei Muster, die sich in dieser Nacht wiederholt haben und beide in meiner eigenen Arbeitsweise sitzen:**

*Aufgabenbeschreibungen altern wie Aufträge.* Dreimal war die Prämisse überholt — der Abrufmonitor lieferte Rang je Kanal längst, in der Ausgabe wird nichts gekürzt, und Aufgabe 41 war größtenteils gebaut. **Die Aufgabenliste ist selbst ein Schnappschuss.** Vor dem Beauftragen gegen den Code messen, nicht die Beschreibung glauben.

*Sieben Agenten endeten im Wartezustand*, weil mein Auftrag „Suite abwarten" verlangte und sie den Lauf in den Hintergrund legten — obwohl er mit `timeout=600000` bequem in den Vordergrund passt. Ursache im Auftrag, nicht in der Arbeit. Seit dem sechsten Fall steht die Auflage ausdrücklich drin.

## PostToolUse ist kein Ausgabekanal — 432 Zustellungen, null im Faden

Im eigenen Faden nachgestellt (06:30): Zehn Meldungen auf fällig gesetzt, ein Werkzeugaufruf, der Zähler steht bei **432 Zustellungen** — und im Faden erschien nichts. Dasselbe für eine zweite Hakengruppe mit sechs Skripten. In `~/.claude/settings.json` hängen **7 Einträge mit 8 Skripten** an diesem Haltepunkt.

**Nachweislich liefernde Kanäle:** `UserPromptSubmit` (die Wissens-Einspielungen erscheinen), `SessionStart`. `PreToolUse` mindestens über den Ablehnungsweg — die Kaskaden-Wache konnte damit sechs Tage lang Arbeit blockieren.

**Offen und heute Nacht selbst verursacht (Aufgabe 74):** Die Existenzprüfung wurde an `Stop` verdrahtet, ohne zu prüfen, ob *dieser* Kanal liefert. Geprüft wurde der Eintrag, nicht die Wirkung. Das Muster von `haken/antwort_abruf.py` löst es bereits: **am toten Haltepunkt sammeln, am lebenden ausgeben.**

**Fehler beim Nachprüfen, festgehalten:** Ich habe zuerst die Zustandsdatei einer *fremden* Sitzung verändert, bevor ich meine eigene suchte. Byte-gleich zurückgestellt — aber es war dieselbe Regel, die ich seit Stunden in jeden Agentenauftrag schreibe.

## Das Datenmodell ist eine Liste von W-Fragen — und drei bleiben unbeantwortet

Gemessen an 2163 Knoten: `source` **100 %**, `freigabe` **100 %**, `anlass` 85 % — alle drei **Pflichtangaben**. Alles Freiwillige liegt darunter: `norm_entschieden_von` 11 %, `gilt_ab` 3,8 %, **`gilt_bis` 0,1 %**, **`abgeleitet_von` 0,05 %**, **Belegart 0 %**.

**Das ist der Beleg für die Bauregel:** Pflichtfelder werden gefüllt, freiwillige nicht. Wer eine W-Frage beantwortet haben will, stellt sie beim **Schreiben** — nicht in einer Erinnerung.

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

**Handprobe offen, verschoben auf Betreiberwunsch (2026-08-13):** Ein Anlege- oder Einlade-Durchlauf **mit Geheimnis** in der nativen App (`8c1d528`) ist nicht gefahren — das Kennwortfeld verweigert synthetische Eingaben, macOS-Verhalten, kein Defekt. Belegt sind: „Ausweise anzeigen" gegen den echten Dienst mit drei echten Einträgen, die Fehlerweiterleitung im Swift-Code, der Negativfall über die Python-Suite. Für Schritt 3 gilt daher **„gebaut und in Teilen belegt, am Gerät nicht durchgefahren"** — nicht „funktioniert". Verschieben kostet nichts, weil die AppleScript-Fassung die drei Abläufe weiterhin trägt; genau deshalb steht sie noch auf dem Schreibtisch.

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
