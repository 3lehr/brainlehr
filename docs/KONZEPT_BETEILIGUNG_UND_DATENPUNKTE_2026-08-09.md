# brainlehr als zentraler Speicher: Beteiligung, und was aus Datenpunkten entsteht

**Angelegt:** 2026-08-09T23:45:00+0200
**Anlass:** Betreiber, woertlich: „du denkst zu kurz! brainlehr soll der zentralle
wissenspeicher auch im unternehme. werden! er koennte zb dazu dienen umfragen und
abstimungen durchzufuehren, mit echten menchen ohne maschienen. denk einmal darueber
nach was aka2026 alles kann, und grundgedanke war da auch alles zentrall an eine platzn
speichern, weill isch dadurch synagien durch datenpunkte ergeben die wir heute noch
garnicht denken koennen!"

---

## 1. Der Einwand trifft, und wo genau

Ich hatte Mandat und Rotation als **Zugangstechnik** gedacht: wer darf was. Der
Betreiber meint etwas anderes — **Beteiligungsinfrastruktur**: eine Abstimmung ist
kein Rechteproblem, sondern ein eigener Gegenstand im Speicher. Rechte sind ihre
Voraussetzung, nicht ihr Zweck.

Der Unterschied ist nicht akademisch. Er entscheidet, ob `art=mensch` eine Schranke
gegen Missbrauch ist (meine Lesart) oder das **konstitutive Merkmal einer
Abstimmung** (seine): „mit echten menschen ohne maschinen".

---

## 2. Was AKA2026 tatsaechlich hat (nachgesehen, 16 Apps unter `/Volumes/daten/AKA2026/apps`)

| App | Was sie tut | Welchen Datenpunkt sie erzeugt |
|---|---|---|
| `aka-scanner` | QR-Check-in auf dem iPad, `POST /api/checkin` | **wer war wann wo anwesend** |
| `aka-pretix` | Ticketing / Kurseinschreibung | **wer hat sich wofuer eingeschrieben** |
| `aka-raumstation` | Astro-Control-Plane, SSE zum Demo-Server (Port 8765), KPI-Grid Kurse/Buchungen/Check-ins/Live-Events | **der Ereignisstrom selbst** |
| `aka-hub` | Desktop-Launchpad fuer Mitarbeiter | wer bedient was |
| `akawiki` | eigene DB (`aka_cms.db`), laut Beschluss die **alleinige Authority fuer Identitaeten** | wer ist wer |
| `akapp` | Flutter-App (Kursbetreuung) | Betreuung je Kurs |
| `aka-poliklinik`, `aka-present`, `aka-stage` | Fach-, Praesentations- und Buehnenschicht | Inhalte, Ablaeufe |

**Die Bauform ist ein zentraler Ereignisstrom mit vielen Oberflaechen darauf** — nicht
eine App mit Modulen. Genau das ist der „alles an einem Platz"-Gedanke, und er ist
dort gebaut, nicht behauptet.

**brainlehr hat diesen Strom bereits**: `access_log`, 3.998 Zeilen, mit Hashkette,
Feldern `actor/action/node_path/query/session/client/status`. Der Knoten
`brainlehrs-zugriffsprotokoll-ist` hielt schon fest, dass das die Feldform ist, die
eine Sigma-Regel zur Missbrauchserkennung braucht. **Was fehlt, ist nicht der Strom,
sondern die zweite Sorte Ereignis darin.**

---

## 3. Die Synergie, konkret statt als Versprechen

Der Satz „Synergien, die wir heute noch nicht denken koennen" ist als Begruendung
wertlos, solange kein einziges Beispiel steht. Vier, die aus den oben **gemessenen**
Datenpunkten folgen:

**Stimmberechtigung aus Teilnahme statt aus einer gepflegten Liste.** Wer beim Kurs
eingecheckt war (`aka-scanner`), ist bei der Abstimmung ueber diesen Kurs
stimmberechtigt. Keine zweite Liste, die veraltet — der Datenpunkt existiert schon
und wurde fuer etwas anderes erhoben.

**Anhoerungsrecht aus Fachberuehrung.** Wer zu einem Gegenstand je etwas beigetragen
oder gemessen hat, wird beim Abruf ueber diesen Gegenstand **mitgeliefert**. Das ist
der Hausmeister-Fall, technisch geloest — und es ist dieselbe Massnahme, die den
gemessenen Abrufmangel angeht (26 von 28 verfehlten Zielen stehen nicht einmal in der
Kandidatenliste).

**Nachweis der informierten Entscheidung.** `access_log` weiss, ob ein Abstimmender
die Gegenposition **tatsaechlich abgerufen** hat, bevor er stimmte. Kein
Umfragewerkzeug der Welt weiss das, weil dort die Stimme ohne Wissenskontext liegt.
Das ist der Punkt, an dem „alles an einem Platz" einen Unterschied macht, den
Getrenntheit nicht herstellen kann.

**Warnung vor dem Beschluss.** Widerspricht eine Vorlage einer belegten Messung im
Bestand, ist das vor der Abstimmung sagbar — samt der Angabe, wer es weiss und nicht
gefragt wurde.

---

## 4. Die Kehrseite, und sie ist dieselbe Eigenschaft

**Synergie und Zweckentfremdung sind technisch nicht unterscheidbar.** Ein Datenpunkt,
der fuer Zweck A erhoben wurde und Frage B beantwortet, ist genau dann ein Gewinn,
wenn B erlaubt ist — und genau dann ein Uebergriff, wenn nicht. Der Unterschied ist
keine Frage der Technik, sondern der Erlaubnis.

Dieselben Check-in-Daten, die Stimmberechtigung begruenden, ergeben ein
**Bewegungsprofil**: wer war wann wo, wie lange, mit wem. Der Stadtwerke-Befund
`L-adfb33` zeigt, wie leise das passiert: der Grund der Abwesenheit war sauber
entfernt — und das Pflichtfeld `source` trug „Abwesenheit Fritz Mueller (gueltig bis
2026-08-15)". Herkunftspflicht und Berechtigungstrennung zogen gegeneinander, und die
Herkunftspflicht gewann, weil sie ein Trigger ist.

**Was daraus folgt, bevor die erste Umfrage laeuft:**

1. **Zweck am Datenpunkt, nicht im Kopf.** Wofuer wurde erhoben — als Feld, nicht als
   Absicht. Ohne das ist jede spaetere Nutzung ununterscheidbar von der
   urspruenglichen.
2. **`kanonymitaet.py` steht bereits** und misst, wie viele Personen eine Auspraegung
   teilen. Es sagt ausdruecklich nicht „anonym" — das waere eine Rechtsaussage, die
   kein Programm trifft. Vor jeder Auswertung ueber Personen anzuwenden.
3. **Aggregat statt Einzelfall als Vorgabe.** „Drei von fuenf Anwesenden haben
   widersprochen" braucht keinen Namen.

---

## 5. Das Wahlgeheimnis gegen die Herkunftspflicht — der harte Konflikt

brainlehr erzwingt `source NOT NULL` **per Trigger**, unumgehbar. Das ist die
Herkunftspflicht, und sie ist eine der besten Eigenschaften des Speichers.

**Eine geheime Abstimmung verlangt das Gegenteil:** die Stimme darf nicht auf den
Waehler zurueckfuehren. Beides zugleich geht nicht am selben Datensatz.

Die Aufloesung ist klassisch und muss **vor** der ersten Abstimmung stehen, nicht
danach:

| Was | Wo | Sichtbar |
|---|---|---|
| **dass** X abgestimmt hat | Beteiligungsliste, mit Herkunft | ja — sonst ist keine Wahlbeteiligung pruefbar |
| **was** X gestimmt hat | Stimmurne, ohne Personenbezug | nein |
| dass die Urne unveraendert ist | Hashkette (existiert) | ja |

Das ist die Trennung von *Berechtigung* und *Stimme* — zwei Datensaetze, nie einer.
Wer sie nachtraeglich einzieht, hat die erste Abstimmung bereits deanonymisiert, und
das ist nicht heilbar. **Reihenfolgegrund, kein Fuellstandsgrund:** er gilt bei null
Stimmen genauso.

**Offen und ausdruecklich unentschieden:** ob eine offene Abstimmung (mit Namen) der
Regelfall sein soll und die geheime die Ausnahme. Fuer ein Unternehmen mit
Betriebsrat ist die geheime Wahl teils gesetzlich vorgeschrieben — das ist zu pruefen
und nicht zu raten.

---

## 6. Was das fuer die vier Verfassungen heisst

Die Abstimmung ist die Stelle, an der `b933ec35` (Verfassung umschaltbar) vom Konzept
zum Bauteil wird. **Dieselbe Stimmenmenge, vier Auswertungen:**

| Verfassung | Auswertung derselben Stimmen |
|---|---|
| Hierarchie | die Stimme mit dem hoechsten Rang entscheidet |
| Konsent | ein begruendeter Einwand haelt auf, Zustimmung ist nicht noetig |
| Bezugsgruppen | je Gruppe ein Ergebnis, kein Gesamtergebnis |
| Mitbestimmung | Schwelle **je Bank**, Pattregel als Pflichtfeld |

Das ist der Beleg dafuer, dass die Verfassung ein Bauteil ist und kein Aufsatz: die
Erhebung ist identisch, die Auswertung nicht. Wer nur eine baut, hat die Wahl schon
getroffen.

---

## 7. Reihenfolge — was zuerst und warum

1. **Trennung Berechtigung / Stimme** (Kapitel 5). Vor der ersten Abstimmung, weil
   nachtraeglich nicht heilbar.
2. **Zweck am Datenpunkt** (Kapitel 4.1). Vor der ersten Zweitnutzung, aus demselben
   Grund.
3. **Anhoerungsrecht im Abruf** (Kapitel 3). Zieht doppelt: Beteiligung **und** der
   gemessene Rangfolgemangel.
4. **Abstimmung als Vorgang**, mit `art=mensch` als Teilnahmebedingung — das ist die
   Stelle, an der die heute gebaute Ausweis-Achse ihren eigentlichen Zweck bekommt.
5. **Auswertung je Verfassung** (Kapitel 6).

**Nicht jetzt:** eigene Oberflaeche fuer Umfragen. Die Erhebung kann ueber vorhandene
Wege laufen; eine Maske ist die billigste und am leichtesten nachzuholende Schicht.

---

## 7b. Zweck als Pflichtfeld — „nur mit begruendetem Interesse"

**Anlass:** Betreiber: „wir hatten bei aka2026 den reverse proxy gedacht um zb dsvgo
einzuhalten und dinge datenschutzkomform zu machen, nur mit begruendeten interesse
durf man daten lesen".

### Was in AKA2026 wirklich steht (nachgesehen, nicht uebernommen)

`L-ad0dda` warnt genau davor, Muster aus AKA2026 pauschal zu kopieren — 86 Agent-
Dateien uebernommen, 11 genutzt. Also geprueft:

- **OD13 ist Infrastruktur, nicht Zweckpruefung.** Woertlich: „Dev und Prod verwenden
  DIESELBE Infrastruktur-Stack: Docker Compose, **Traefik als Reverse Proxy**,
  PostgreSQL, HTTPS. Kein 'das funktioniert nur lokal'-Kompromiss." Das ist
  Umgebungsparitaet und TLS.
- **Die DSGVO-Bindung steht in der VERFASSUNG** (Art. 5, 6, 17 fuer Teilnehmerdaten)
  und als eigener `legal`-Agent fuer Verstoesse.
- **Das eigentliche Muster steckt bei den Purpose-Strings:** „Purpose strings fuer
  alle Datenzugriffe (Kamera fuer QR-Scan benoetigt explizite Begruendung)", plus
  „Explizite User-Einwilligung + Purpose-String im Onboarding/Info.plist PFLICHT".

Das ist Apples Zwang, **vor** dem Zugriff den Zweck zu deklarieren. Der Gedanke des
Betreibers uebertraegt ihn von Geraetesensoren auf Datensaetze — und das ist die
staerkere Fassung, nicht die schwaechere.

### Warum ein Reverse Proxy der richtige Ort, aber die falsche Schicht ist

Ein Proxy sieht **Anfragen**, keine Datensaetze. Er kann `/api/personal/*` sperren; er
kann nicht „dieses Feld fuer diesen Zweck". Bei uns liegt die Stelle, an der beides
bekannt ist — Aufrufer, Werkzeug und betroffener Datensatz — an **`tools/call`**, dem
Choke-Point aus B4.3.

Mit ADR-001 (Streamable HTTP) wird ein Proxy trotzdem real: fuer TLS, `Origin`-Pruefung
und Ratenbegrenzung. **Zwei Aufgaben, zwei Orte** — sie zu vermischen erzeugt eine
Schranke, die aussieht wie Datenschutz und Verkehrsregelung ist.

### Die Regel, ohne die es eine Rechteerweiterung per Behauptung waere

> **Der Zweck verengt. Er erweitert nie.**
> Wirksame Sicht = Rolle **geschnitten mit** Zweck, nie vereinigt.

Der Zweck ist eine **Behauptung** und kann es nicht anders sein: anders als `actor`,
der einen Ausweis hat, lebt der Zweck im Kopf des Aufrufers. Es gibt nichts, wogegen
man ihn pruefen koennte. Wer daraus mehr Rechte ableitet, hat dieselbe Luecke gebaut
wie `actor` im Argument — nur schwerer zu sehen.

Was trotzdem geht, und das ist viel:

1. **Geschlossene Liste statt Freitext.** Ein Freitextzweck ist nicht auswertbar und
   damit auch nicht pruefbar.
2. **Der Zweck bestimmt die PROJEKTION, nicht nur die Erlaubnis.** Das ist der
   eigentliche Gewinn und echte Datenminimierung (Art. 5 Abs. 1 lit. c) statt eines
   Vermerks. Am gemessenen Fall `L-adfb33`:

   | Zweck | sieht |
   |---|---|
   | Dienstplanung | „abwesend bis 2026-08-15" |
   | Personalverwaltung | zusaetzlich den Grund |

   Heute gibt es nur ganz-oder-gar-nicht — und deshalb stand der Name im
   Pflichtfeld `source`, wo ihn niemand vermutete. **Die Zweckprojektion loest genau
   diesen Befund**, den Sichtbarkeitsregeln allein nicht loesen konnten.
3. **Protokoll macht die Behauptung nachpruefbar.** `access_log` traegt den Zweck mit;
   Muster wie „derselbe Zweck fuer 1.000 Datensaetze in 3 Sekunden" sind zaehlbar. Der
   Knoten `brainlehrs-zugriffsprotokoll-ist` haelt fest, dass die Feldform dafuer
   bereits Sigma-tauglich ist.
4. **Zweckwechsel ist ein Ereignis.** Wer denselben Datensatz unter zwei Zwecken
   abruft, tut etwas Auffaelliges — nicht verboten, aber sichtbar.

### Die Grenze, ehrlich benannt

„Berechtigtes Interesse" nach Art. 6 Abs. 1 lit. f DSGVO verlangt eine **Abwaegung**
gegen die Interessen der betroffenen Person. **Keine Software trifft diese Abwaegung.**
Was Software kann: Zweckbindung (Art. 5 Abs. 1 lit. b) und Datenminimierung
(lit. c) technisch durchsetzen und die Abwaegung dokumentierbar machen.

Das ist dieselbe Haltung, die `kanonymitaet.py` schon im Kopf traegt: es nennt die
Zahl k und verwendet nie das Wort „anonym", weil das eine Rechtsaussage waere. Ein
Werkzeug, das „DSGVO-konform" von sich behauptet, hat diese Grenze ueberschritten.

### Proben

| Nr. | Probe | Erwartung |
|---|---|---|
| Z1 | Zugriff ohne Zweck | abgewiesen, wo der Datensatz Personenbezug traegt |
| Z2 | unbekannter Zweck (Freitext) | abgewiesen, nicht als „sonstiges" gefuehrt |
| Z3 | Zweck gewaehrt ein Feld, das die Rolle nicht hat | **Feld bleibt weg** (Schnitt, nicht Vereinigung) |
| Z4 | Rolle erlaubt alles, Zweck ist eng | nur die Zweckprojektion |
| Z5 | derselbe Datensatz, zwei Zwecke | zwei Protokollzeilen, unterschiedliche Felder |
| Z6 | Zweck steht im Protokoll | bei **jedem** Lesezugriff, nicht nur bei Schreibvorgaengen |

---

## 8. Was ich falsch gerahmt hatte

`art=mensch` habe ich als **Schranke gegen Missbrauch** gebaut — damit ein Modell
nicht per Konfigurationszeile zum Menschen wird. Das bleibt richtig.

Aber es ist zugleich das **konstitutive Merkmal einer Abstimmung**: „mit echten
menschen ohne maschinen" ist keine Sicherheitsauflage, das ist die Definition. Ein
Feld, das ich als Zaun gedacht hatte, ist in Wahrheit ein Fundament.

Das ist der Grund, warum der Betreiber „zu kurz gedacht" gesagt hat — und er hat in
einem Punkt recht, der ueber diese eine Entscheidung hinausgeht: **Ich habe die
Schutzfrage gestellt und die Zweckfrage nicht.**
