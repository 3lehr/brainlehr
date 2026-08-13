# Konsil-Ergebnis — Grundarchitektur

**Stand** 2026-08-13T23:41:40+0200
**Aufbau** 10 Opus-Rollen, parallel, ohne Kenntnis voneinander. Material:
`docs/KONSIL_MATERIAL_2026-08-13.md` — ohne ADRs, ohne Pläne, ohne Bestandszahlen, ohne
Quellenliste (Begründung dort, Abschnitt 5). Jede Rolle durfte eigene Recherche fahren.
**Was hier steht, ist nicht beschlossen.** Es ist der Rohertrag plus meine Nachprüfung.

---

## 0. Was ich selbst nachgemessen habe

Alles Folgende von mir mit Werkzeugaufruf geprüft, nicht aus den Berichten übernommen:

| Behauptung einer Rolle | Nachgeprüft |
|---|---|
| 30 Tabellen, 51 Trigger, 0 Views | **stimmt** |
| 2183 Knoten, 868 Lehren, 6469 Relationen | **stimmt** |
| 1928 Schreib- gegen 566 Lesevorgänge (3,4 : 1) | **stimmt** (add 799 + update 1129) |
| `zurueckziehen` 8-mal benutzt | **stimmt** |
| 97 831 Zeilen Python in 360 Dateien | **stimmt** |
| 640 Commits, 565 in sieben Tagen | **stimmt** |
| **61 definierte Rollen, 18 benutzte, Schnittmenge genau eine (`performance`)** | **stimmt** |
| `knowledge_zurueckziehen` leert `content` und `summary` | **stimmt** — steht wörtlich im eigenen Docstring |
| Art. 50 EU-KI-VO gilt seit 2026-08-02 | **stimmt**, unabhängig bestätigt; Bußgeld bis 15 Mio. € oder 3 % Umsatz; Übergang für vorhandene generative Systeme bis 2026-12-02 |
| EAA seit 2025-06-28 durchsetzbar | **stimmt**; Übergang für Bestandsprodukte bis 2030-06-28 |
| MCP seit Dez. 2025 bei der Linux Foundation | **stimmt** — und das ist eine **unabhängige Deckung**: dieselbe Tatsache hatte ich am selben Abend vor dem Konsil selbst gefunden, ohne dass die Rolle davon wissen konnte |
| Typst erzeugt PDF/UA-1 nativ | **nicht bestätigt** — meine Suche fand dazu nichts. Offen. |

---

## 1. Vier Konvergenzen

Die Rollen kannten einander nicht. Wo mehrere unabhängig dasselbe finden, ist das kein
Konsens, sondern der einzige Beleg, den ein Konsil erzeugen kann.

### 1.1 Die Gattungsfrage — acht von zehn verwerfen „Überforderung"

Ich hatte den Widerspruch offen ins Material geschrieben: Was haben Stadtwerke und eine
Akademie mit einer Wohnungseigentümerin gemeinsam?

- **evangelist:** *„Nicht die Menschen sind unwissend — das Wissen ist am falschen Ort."*
- **jesus-guide:** Distanz zwischen vorhandenem Wissen und der Stelle, an der entschieden wird.
- **solution-architect:** *„Eine Gattung, sechs Entfernungen."* Die Rolle ist **Bote, nicht Experte** — und Boten kann man prüfen.
- **zeitreisender:** **Einmal-Spieler gegen Dauer-Spieler.** Sie spielt einmal, ihr Gegenüber jeden Tag.
- **psychologist:** **der gebrochene Rückkanal** — wer die Antwort benutzt, trägt im Moment der Benutzung nicht die Kosten dafür, dass sie falsch ist.
- **evangelist, zusätzlich:** *„Hilfe für Überforderte"* ist als Positionierung unbrauchbar — **niemand kauft etwas, das ihn zum Überforderten erklärt.**

**Dissens, und er ist gehaltvoll:** `spaghetti-monster` und `newton-standards` sagen: zwei
Gattungen, nicht eine. Der Jurist liefert die Trennachse, und sie ist die einzige der
vorgeschlagenen, die **messbar** ist statt psychologisch:

> **Ist die Antwort einem Vorbehaltsberuf zugewiesen (RDG, StBerG), und kann der Empfänger sie prüfen?**
> Steuer/Recht/Behörde: vorbehalten, nicht prüfbar, Schaden existenziell.
> Stadtwerke/Akademie: nichts vorbehalten, der Empfänger **ist** der Fachmann, der Mangel ist Auffindbarkeit im eigenen Bestand.

Beides zugleich ist haltbar: **eine Gattung im Zweck, zwei im Rechtsregime.**

### 1.2 Die Basis nicht zuerst — fünf von zehn, mit Zahlen

- **solution-architect:** *„Eine Grundlage wird nicht entworfen, sie wird herausgezogen. Eine Grundlage mit einem Verbraucher ist keine Grundlage, sondern eine Anwendung mit ungewöhnlich großem Selbstbild."*
- **zeitreisender:** **„Etwas ist erst eine Basis, wenn eine Domäne darauf gebaut wurde, ohne dass die Basis dafür angefasst wurde."**
- **jesus-guide:** genau daran starben Cyc (40 Jahre, ~2000 Personenjahre), Freebase, Nupedia (21 Artikel im ersten Jahr gegen Wikipedias 18 000).
- **evangelist:** nicht „nicht bauen", sondern **„nicht zuerst bauen"**.
- **spaghetti-monster:** eine Anwendung zu Ende bauen, die Basis aus dem herausschneiden, was zweimal gebraucht wurde.

**Und der `archaeologe` widerlegt dabei seine eigene Ausgangsthese**, was die Zählung wertvoll
macht: Von acht toten Vorhaben starben nur **2 von 8** an Pflegekosten und **1 von 8** an
Unübertragbarkeit. **5 von 8** starben an etwas anderem, mit gemeinsamer Form:

> Sie verlangten **Tribut vor der Gegenleistung.** Man musste die eigene Arbeit unterbrechen,
> um das System zu bedienen, und der Nutzen kam später, woanders, oder bei jemand anderem an.

Alle drei Überlebenden (schema.org, Wikidata, Rules as Code) kehren das um: der Nutzen
erreicht den Beitragenden **in derselben Sitzung**. Daraus die schärfste Prüffrage des
ganzen Konsils, anwendbar auf jede einzelne Entscheidung:

> **Zahlt das dem zurück, der es getan hat, in der Sitzung, in der er es tat?**

Das trifft Widerspruch (b): „oben schnell, unten streng" hält nur, wenn die strenge Schicht
sofort zurückzahlt. Zahlt sie später oder nur an andere, wird sie nicht gepflegt.

### 1.3 Vertrauen ist nicht herstellbar — Prüfbarkeit schon. Sechs von zehn

- **`archaeologe`, der unbequemste Beleg:** MYCIN diagnostizierte auf Facharztniveau (65 % gegen 42–62 % der befragten Ärzte) und wurde **nie klinisch eingesetzt.** INTERNIST-I starb an der „Greek Oracle"-Kritik: der Arzt wurde zum Dateneingeber.
- **psychologist:** Erklärungen erhöhen zuverlässig das **Vertrauen**, nicht die **Prüffähigkeit** — auch erfundene Begründungen; bei nachweislich unzuverlässigen Systemen hoben sie das Vertrauen sogar an. Ein Gegenbefund war nicht auffindbar.
- **zeitreisender:** ein Vertrauenswert geriet fast in die Oberfläche. Gerettet durch eine peinlich einfache Frage: *„0,82 kann sie genauso wenig prüfen wie die Auskunft selbst."*
- **data-act-jurist, die juristische Fassung desselben Satzes:** **„Haftungsrelevant ist nicht, ob die Auskunft falsch war. Haftungsrelevant ist, ob das System wusste, dass es unsicher war, und trotzdem sicher klang."** Grobe Fahrlässigkeit entsteht nicht aus dem Irrtum, sondern aus dem **Weglassen des Zweifels**.
- **Die gemeinsame Folgerung:** Nicht das Vertrauen verdienen, sondern die Antwort **für einen Dritten prüfbar machen.** *„Prüfbarkeit ist übertragbar, Vertrauen nicht."* Die Eigentümerin kann § 26 WEG nicht beurteilen — sie kann die Fundstelle in fünf Minuten einem Anwalt vorlegen statt in fünf Stunden.

### 1.4 Neubau heilt den stillen Fehlschlag nicht — vier von zehn, gleicher Ersatz

`newton-standards` trennt drei Krankheiten, die unter einem Namen laufen:

| | Ebene | Stand |
|---|---|---|
| Es kommt nichts zurück, wo etwas kommen müsste | Protokoll | **gelöst** — MCP `isError`, schemavalidierte Ausgabe (seit `2025-06-18`), HTTP RFC 9457 |
| Es kommt „ok" zurück, und nichts ist passiert | Semantik | **hier und nur hier** rechtfertigt sich Eigenbau — Medizin ist eine Bauregel: *nie eine nackte Bestätigung, immer den resultierenden Zustand* |
| Es kommt Plausibles zurück, und es stimmt nicht | Erkenntnis | **kein Standard existiert** |

- **spaghetti-monster:** *„Wenn Neubau das Problem nicht löst, war das Problem nie das Argument für den Neubau. Es war der **Anlass**, und Anlass und Grund sind verschiedene Dinge."*
- **solution-architect:** Plausibilität ist nur **gegen eine Erwartung** falsifizierbar — der Aufrufer muss **vor** dem Aufruf sagen können, wie das Ergebnis aussehen muss. Eigenschaft des Protokolls, nicht der Werkzeuge.
- **zeitreisender:** in der Praxis ist es **die Leerzeile** — nicht die Auskunft, sondern der Hinweis, dass in keinem der vier Angebote steht, wer die Bankvollmacht hält.

---

## 2. Der Treffer gegen das Konsil selbst

`spaghetti-monster` hat sich absichtlich nicht an Abschnitt 5 gehalten und selbst gemessen:

> *„Abschnitt 5 ist als methodische Tugend geschrieben und ist in Wahrheit die stärkste
> Selbstimmunisierung im ganzen Dokument. Er verbietet dem Konsil genau die drei Dinge, aus
> denen ein Nein bestehen könnte."*

Das ist berechtigt. Die Absicht war, das Erben eines fremden Rahmens zu verhindern (ADR-004:
*„alle fünf haben den Termin geerbt, weil mein Auftrag ihn nannte"*). Dabei wurde das Einzige
mitentfernt, **was gegen den Auftrag zurückschlagen kann.** Ein Termin ist eine fremde
Vorgabe; eine gemessene Zahl ist ihr Gegenteil.

**Die Unterscheidung, die gefehlt hat, hat er selbst geliefert: Füllstände sind kein
Argument (Hausregel), Verhältnisse schon.** 97 831 Zeilen Apparat auf 2 183 Knoten · mehr
Trigger als Tabellen · 3,4-mal so viel Schreiben wie Lesen. Diese drei bleiben, was sie
sind, ob dort 2 000 Knoten liegen oder zwei Millionen.

---

## 3. Einzelbefunde, die nicht in eine Konvergenz fallen

### 3.1 Ein akuter Defekt, verifiziert

`knowledge_zurueckziehen` setzt `content = ''` und `summary = ''`. Der Docstring sagt es
selbst. Damit gilt:

> **Das Korrigieren eines falschen Eintrags vernichtet den Beweis des falschen Eintrags.**

Genau die Zeile, die man braucht, wenn er Schaden angerichtet hat — und genau die, die der
Jurist für die Haftungsfrage verlangt. Behebbar mit einem Einzeiler, heute.

### 3.2 Woran man Totes erkennt — drei Signale, die nicht lügen

`archaeologe`, gemessen und von mir nachgeprüft:

- **Definitionen gegen Aufrufe.** **61 definierte Rollen, 18 tatsächlich benutzte, Schnittmenge genau eine.** Was läuft, heißt `general-purpose` (421), `implementer` (336), `architekt` (17) — Namen, die jemand hingeschrieben hat, nicht aus dem Katalog gewählt.
- **Kopien gegen Referenzen.** 96 Kopien von `AGENTS.md` in 7 Fassungen; 614 `VERFASSUNG.md` im Baum. *„Was referenziert wird, existiert einmal. Was kopiert wird, wird von Hand getragen, und Handtragen hört auf."*
- **Einheitlichkeit.** Am 2026-08-05 wurde in 16 Projekten genau eine Datei angefasst — `settings.json`, mit der vollen Wächterkette. Elf davon hatten seit 13–34 Tagen keine echte Arbeit. **„Einheitlichkeit ist ein Todeszeichen, kein Gesundheitszeichen. Lebendiges driftet."**

Und die Regel daraus: *„Halbtot ist, was kostet."* Weggeworfenes kostet nichts; etwas, das
noch wie eine Antwort aussieht, kostet jeden künftigen Leser eine falsche Abzweigung.

### 3.3 Der `Bestatter` widerlegt seine eigene Ausgangsannahme

*„Es stimmt nicht, dass nichts einen Tod hat"* — `zurueckgezogen` existiert mit
Pflichtbegründung. Aber: **es gibt genau eine Todesart, und sie vererbt nichts.** Relationen
bleiben beim Widerruf unberührt; was auf einem widerrufenen Satz aufbaut, merkt nichts und
tritt weiter mit voller Autorität auf.

Drei Tode, die nicht dasselbe sind: **Irrtum** (war nie richtig, stirbt rückwärts bis zur
Geburt) · **Widerruf** (war richtig, hat ein Datum) · **Anlassverlust** (immer noch richtig,
fragt niemand mehr). Verschiedene Erbfolgen — deshalb keine Kosmetik. Heute ist
`zurueckgezogen_grund` Freitext, die Unterscheidung steht dort, wo kein Programm sie findet.

Prüfstein für Scheintod: **tot ist, was nur noch von Dingen abhängt, die es selbst erzeugt
hat.** Wegnehmen und schauen, ob irgendwo etwas anschlägt.

### 3.4 Fünf Dinge, die es nur vorher gibt

`solution-architect`, Reihenfolge bindend, jedes entwertet ein späteres:

1. **Fassungen — vor der ersten Antwort an einen echten Menschen.** Nicht „bevor viel drinsteht". Ab der ersten Antwort existiert die Frage *„welche Regel galt, als das gesagt wurde?"*, und sie entsteht nur im Moment des Sagens.
2. **Der Verfallsanlass — im Moment des Schreibens.** Kein Datum, eine Bedingung: *„gilt nicht mehr, wenn X, nachzusehen bei Y."* Ein Speicher stirbt nicht an falschen Einträgen — die werden korrigiert. Er stirbt an Einträgen, die **einmal richtig waren**.
3. **Die Folgenklasse auf der Frageseite.** Schaden ist eine Eigenschaft der Verwendung, nicht des Satzes. *„Frist vier Wochen"* kostet in einer Notiz nichts und in einer Fristberechnung die Wohnung. `annahmen.kosten_wenn_falsch` ist die richtige Idee in der falschen Tabelle.
4. **`project_id` ohne Vorgabewert.** Verallgemeinert und für mich die brauchbarste Regel des Beitrags: **jeder Vorgabewert, der eine Entscheidung vertritt, ist eine Entscheidung, die später niemand rekonstruieren kann.** Trifft auch `anlass DEFAULT 'unbekannt'`.
5. **Identität getrennt von Adresse.** Relationen und Einbettungen zeigen auf `path` — Umräumen bricht jede Referenz. Teuer, aber als einziges der fünf mechanisch reparierbar.

Und die Umkehrung, die er als Kern vorschlägt: **das Protokoll ist die Wahrheit, der Baum
ist eine wegwerfbare Projektion** — nur-anhängend, mit `UPDATE`/`DELETE`-Verbot per Trigger.
*„Ein kleiner unsterblicher Kern erteilt allem anderen die Erlaubnis zu sterben."*

### 3.5 Recht — was jetzt gilt und was angreifbar ist

- **Art. 50 EU-KI-VO gilt seit 2026-08-02** (elf Tage). Offenlegung gegenüber dem Nutzer, maschinenlesbare Kennzeichnung erzeugter Inhalte. Bußgeld bis 15 Mio. € oder 3 % Umsatz. **Und: Quelloffenheit kauft die Freistellung nicht** — Art. 2 Abs. 12 endet ausdrücklich bei Art. 50.
- **Die KI-VO-Exposition entsteht erst durch die Plattformabsicht.** Baut ein Stadtwerk darauf eine Anwendung, die Anspruchsberechtigungen prüft, ist **jene** Anhang III Nr. 5; nach Art. 25 wird der Nachbauer selbst Anbieter, und der ursprüngliche Anbieter muss ihm die technischen Angaben liefern. **Eine Basis für Organisationen muss abgebbar dokumentierbar sein** — Herkunft, Datengrundlage, Grenzen, Stand.
- **Die RDG-Linie verläuft durch die Ausgabeform, nicht durch die AGB.** BGH smartlaw (I ZR 113/20) hielt, weil der Generator die Umstände keiner eigenen rechtlichen Bewertung unterzog. § 309 Nr. 7 lit. b BGB macht den Haftungsausschluss gegenüber Verbrauchern für grobe Fahrlässigkeit unwirksam — der Satz „keine Rechtsberatung" leistet **nicht**, wovon er zu handeln vorgibt. Zu LLM und RDG existiert **keine Entscheidung**.
- **„Eine Regel, die aus genau einem Fall stammt, ist auch ohne Namen der Fall"** (Singling out, WP216). Zwei billige, maschinell prüfbare Tests: Bleibt die Regel sinnvoll, wenn man den Fall löscht? Steht mehr als ein Vorgang dahinter?
- **Nebenprodukte erben Herkunft** — Volltextindex, Einbettungen, Testfixtures, Beispielausgaben, Fehlerprotokolle **und Commit-Nachrichten.** Das kollidiert frontal mit der Hausregel *„die Nachricht nennt warum"*: In einem System, das aus Fallmaterial lernt, **ist das Warum oft der Fall.**
- **Das öffentliche Verzeichnis wird als öffentliches geboren.** `git filter-repo` erreicht keine Forks, Klone, Spiegel. Sobald ein Fork existiert, ist Entfernung eine Absichtserklärung.
- **Die gefährlichste Fläche sind Fristen.** *„Das System nennt Fristen und ihre Grundlage, es rechnet sie nicht still aus."* Ein genanntes Datum mit Paragraf ist prüfbar; ein errechnetes ohne Rechenweg ist eine Zusage.
- **Schwellen sind richtungsabhängig.** *„Sie haben kein Fristproblem"* ist falsch katastrophal; *„Sie haben möglicherweise eins"* ist falsch eine verlorene Stunde. Eine symmetrische Schwelle sieht für jeden Juristen nach Anfängerfehler aus.

### 3.6 Standards — wo Folgen falsch wäre

`newton-standards`, damit die Rolle nicht bloß Prüfliste ist: **PROV-O** (W3C, 2013,
außerhalb der Forschungsdaten-Nische tot) — die drei Fragen klauen (wer, woraus, durch
welche Handlung), die Ontologie nicht importieren. **A2A** löst Agenten *verschiedener
Eigentümer*; hier gibt es einen. Form behalten, Abhängigkeit später. **ISO/IEC 42001** für
einen Einzelbetrieb in Beta eine Papierfabrik.

**Und die Antwort auf „gibt es einen anerkannten Maßstab" aus dem Material: nein — und einen
zu zitieren wäre selbst der Anfängerzug.** TruthfulQA gesättigt und ohne Fragenkenntnis zu
79,6 % lösbar; GAIA-Antworten öffentlich; SWE-bench kontaminiert; WebArena/OSWorld rufen
`eval()` auf agentengesteuerten Strings. **Der professionelle Stand 2026 ist ein eigenes,
eingefrorenes, nicht veröffentlichtes Prüfset mit dokumentiertem Bauverfahren.**

Dazu zwei billige Gewinne: **Sterbemodell existiert seit 2009** — SKOS `owl:deprecated` plus
`dcterms:isReplacedBy`, Crossref/Retraction Watch: der Widerruf ist ein **eigener Datensatz**,
kein Häkchen am Original, und **der Bezeichner überlebt**, damit auffindbar bleibt, was auf
ihm stand. Und **SQL:2011 System-Versioned Tables** als echte ISO-Norm für bitemporale
Speicherung: *„was haben wir an dem Tag geglaubt, an dem wir es ihr gesagt haben."*

### 3.7 Zwei Angriffe auf Sätze des Betreibers

- **Zum schönen Dokument** (`psychologist`): Schönheit ist ein Vertrauenssignal. Bei einer Rechnung harmlos, weil die Aussage vom Menschen stammt. Bei einer Einschätzung *„eine in Typografie erzählte Lüge — perfekt gesetzte Ratlosigkeit sieht aus wie perfekt gesetztes Wissen."* Vorschlag: zwei Register — Pracht für das, was der Mensch verantwortet, Nüchternheit für alles, was die Maschine behauptet. Dazu unabhängig: **EAA seit 2025-06-28** — ein Schreiben an eine Behörde muss barrierefrei sein, sonst wird die Oberfläche auf AA geprüft und das **Erzeugnis** fällt aus dem Rahmen.
- **Zum Wegwerfen** (`psychologist`, `Bestatter`, `newton-standards` unabhängig): Für Code richtig. Für einen Menschen, der sich darauf gestützt hat, nie — er verliert kein Merkmal, sondern den einzigen Griff an seinem Problem. Und: **wegwerfbare Anwendungen ja, wegwerfbare Schnittstelle nie.** Dass die Wegwerf-Regel und die Standard-Regel dieselbe Linie ziehen, ist das beste Zeichen dafür, dass die Linie stimmt.

### 3.8 Zwei Lagen sind unabhängig als nicht tragfähig gemeldet

- **Kita:** `jesus-guide` — die Kommunen veröffentlichen die Vergabekriterien gar nicht (OVG NRW musste zur Transparenz verurteilen). `zeitreisender` — das Ergebnis hängt an der Platzzahl, nicht am Vorbringen: *„Das System konnte den Eltern erklären, warum sie verloren hatten. Das war Grausamkeit mit Fußnoten."* Daraus die Grenze: **das Werkzeug wirkt nur, wo das Ergebnis vom Vorbringen abhängt.**
- **Steuer in der gewünschten Form:** StBerG § 6 Nr. 4 knüpft an **Personen** mit Ausbildung plus drei Jahren Praxis; ein System kann sich nicht hineinqualifizieren. § 5 StBerG verbietet **geschäftsmäßige** Hilfeleistung, Entgeltlichkeit ist nicht nötig — eine dem § 6 Abs. 2 RDG entsprechende Ehrenamtstür fehlt dort. **Die Steuerdomäne ist rechtlich die härtere von beiden, obwohl sie sich harmloser anfühlt.**

---

## 4. Was die Rollen selbst als unbelegt gekennzeichnet haben

Sie haben es getan, ohne dass ich es verlangt hätte — hier zusammengezogen, damit es nicht
als Befund weiterwandert: § 6 Abs. 2 RDG und die Auslegung von „geschäftsmäßig" (Modellwissen,
im Lauf nicht geprüft) · die Übertragung der EDPB-Opinion 28/2024 auf Einbettungen
(Analogieschluss) · die Anhang-III-Einordnung eines bürgerseitigen Auskunftswerkzeugs
(Subsumtion, keine Fundstelle) · ob der „Digital Omnibus" zum Stichtag verbindlich ist
(zwei Quellen widersprechen sich) · C2PA-Versionsstand · Typst/PDF-UA · sämtliche Zeitangaben
und Mengen der Zukunftserzählung (*„elf Tage, sechs Wochen, einundzwanzig Seiten — alles
Ausschmückung"*) · dass die Gattung eine ist und nicht zwei (*„der eleganteste Gedanke und
deshalb der verdächtigste"*).

---

## 5. Betriebsbefund

Die zehn Opus-Rollen haben das Kontingent für gleichzeitige Agenten ausgeschöpft — zwei
Rollen konnten **keine** Sonnet-Zuarbeit bekommen und haben das gemeldet, statt ihr
Modellwissen als Beleg auszugeben. Wer ein Konsil dieser Größe fährt, plant die Zuarbeit
vorher oder bekommt sie nicht.
