# Plan: die nächste Stufe — was der Nachtlauf erforscht hat und was daraus folgt

Angelegt 2026-08-21T08:20:00+0200. Nachfolger von
`docs/PLAN_GESAMTBAU_2026-08-21.md` (acht Stränge A–G, abgeschlossen).

Dieser Plan ordnet nach EINEM Maßstab, und es ist derselbe wie bei B1:
**Was lässt sich später nicht mehr nachholen?** Nicht Größe, nicht Nutzen,
nicht Aufwand — Aufwand ist als Kriterium ausdrücklich gestrichen
(`L-dafc34`, 4×, Regelrang).

## §1 Was der Nachtlauf ergeben hat

**Gebaut und belegt** (25 Commits, `1d0e7470`..`85df5c87`): vier Achsen im
Schema · Mandanten- und Kreistrennung samt Zahlen · Profilwechsel mit Rückweg
· Forderungen als Vorgang · Aussetzer-Sicherung · Zugriffsmuster ·
Verfallsrate · englische Tür · Einrichtungsassistent.

**Zweimal NICHT gebaut, weil die Messung es sagte** — und das sind Ergebnisse,
keine Lücken:

| | gemessen | Folge |
|---|---|---|
| A2 Leerlauf-Rückzug | 40,5 % gesparte Suchen gegen 38,6 % verpasste Treffer; in der sicheren Fassung 0,0 % verpasst, aber nur 0,4 % gespart | verworfen |
| A1 Widerspruchserkennung | 7 Treffer, **0 echte Widersprüche**, Positiv- und Negativkontrolle greifen | nicht verdrahtet |

**Fünf Zahlen aus Plan und Übergabe waren falsch**, alle gemessen widerlegt:
die Spracherkennung („36 Stoppwörter, 758/770") existierte als Code nicht ·
der Leer-Anteil war 34,1 % statt 37,8 % · von 13 Forderungen war **eine**
offen · A1 galt als „belegt", ohne je abgenommen worden zu sein · und das
GitHub-Konto ist **nicht** gesperrt, der öffentliche Export ist seit
2026-08-20T17:27 draußen.

## §2 Der Engpass, gemessen und unverändert

`BDW-P05` (Zielbild A): **3/35 = 8,6 %** gegen Schwelle 95 %. Aussage 17,1 %,
Quelle 11,4 %, Status 11,4 %, Geltung 8,6 %.

**Das ist kein Trefferquotenproblem.** Die drei anderen Felder werden gar
nicht ausgeliefert. Der Speicher, dessen Zweck das Belegen ist, liefert seine
Antworten ohne Herkunft. Solange das so ist, ist jede Verbesserung am Abruf
eine Verbesserung an der falschen Stelle.

## §3 Zwei Achsen, die sich nicht nachholen lassen — bindend zuerst

Derselbe Grund wie bei B1, und er ist keine Frage des Füllstands.

**§3.1 Der GEGENSTAND — wer oder was ist gemeint.** (`BDW-P16`)
Gemessen: `gegenstaende` trägt **2 Zeilen**, `gegenstand_namen` **7** — und
beide Gegenstände sind Software (`anwendung`, `einstellung`). Keine Person,
kein Objekt, kein Vertragspartner. Die Tabelle existiert seit ADR-028 („Ein
Name ist nie ein Schlüssel"), angewandt ist sie auf sich selbst.

Jedes Werkzeug, das je dazukommt, hängt daran: ein Kalender braucht
Teilnehmer, eine Rechnung einen Empfänger, ein WEG-Vorgang einen Eigentümer,
ein Beleg einen Aussteller. Wer heute ein Dokument ablegt, ohne die Person zu
binden, hat morgen **einen Text mit einem Namen darin** — und ein Name ist
nie ein Schlüssel.

**§3.2 Die FÄLLIGKEIT — was wann von wem zu tun ist.** (`BDW-P17`)
Gemessen: `gilt_ab` in der Zukunft steht bei **0 von 5 240**, `gilt_bis` bei
**2**. Der Speicher hat keine Zukunft.

Strang F hat die halbe Sache gebaut, ohne dass es auffiel: Der Vorgang trägt
`offen|erledigt|abgelehnt|ueberholt`, sortiert nach Alter, beim Sitzungsstart
vorgelegt — eine Aufgabenliste **ohne Datum**. Kalender, Aufbewahrungsfrist,
Wiedervorlage, Zahlungsziel und Wartungstermin sind **eine** Achse, nicht
fünf Anwendungen.

**Was daraus NICHT folgt:** Mail, Chat, Telefonie, Buchhaltung,
Dateisynchronisation. Sie hängen alle an denselben zwei Achsen und bringen
keine eigene mit — sie kosten später genauso viel wie heute und gehören
deshalb nicht vorgezogen.

## §4 Was unabhängig davon gebaut werden kann

**§4.1 Die Namensfrage als Namensfrage erkennen** (`BDW-P18`) — der Fund des Konsils, den
keine Linse beauftragt hatte, gemessen am 2026-08-21:

| Frage | Ziele gefunden |
|---|---|
| `Döldissen` | **3 von 3**, Ränge 1, 2, 3 |
| `zeige mir alles was mit Frau Döldissen zu tun hat` | **1 von 3** |

Die Fähigkeit ist da, sie wird nur nicht angesteuert. Die Füllwörter der
Frage verdünnen den Namen; im schlechten Lauf steht auf Rang 2
`/stadtwerke/koeder-frau-elvira-quenzelbach-kd-nr` — getroffen auf „Frau",
geliefert eine andere Person. Der Verlust sitzt in der FRAGEFORM, nicht im
Index und nicht am Deckel: die beiden fehlenden Ziele stehen gar nicht mehr
in der Kandidatenliste.

**§4.2 Getrennte Kandidatenbudgets.** Heute fusioniert
`haken/suchpfad_abruf.py:169-171` Knoten und Lehren in EINE Liste von 17
Plätzen, bevor die getrennte Kappung (`MAX_NODES=10`, `MAX_LESSONS=7`)
greift. Das ist der gemessene, gattungsUNabhängige Hebel — und der Grund,
warum beim Katalogimport eine Lehre herausfiel.

**§4.3 Dokumentenablage** (`ADR-032`, `BDW-P15`), Ort als Einstellung je
Domäne.

**§4.4 Bauvermeidung** (Knoten `cb2193a8`): vor dem Bauen erst im eigenen
Haus, dann in der Welt nachsehen. Die innere Hälfte ist seit dem 2026-08-21
als Forderung erfasst.

## §5 Der Konsil zum zweiten Vektorraum — Stand und Widerspruch

| Linse | Empfehlung | tragendes Argument |
|---|---|---|
| Abrufgüte | **C** (nichts tun) | Verlust nicht gattungsabhängig (B und C liefern dieselbe Zahl) und **sättigend**: 951→13/35, 2 853→12/35, 9 510→12/35 |
| Betrieb | **A** (eigener Raum) | Wachstum (3 503 Abschnitte = 47 % des Vektorbestands), Löschen ist bei Dokumenten der Normalfall, und die `sensibel`-Kopplung |
| Irrtumskosten | offen | Linse wurde umgestellt (Aufwand als Kriterium gestrichen), rechnet neu |

**Die `sensibel`-Kopplung ist der härteste Einzelbefund und gehört
entschieden, egal wie der Konsil ausgeht:** `schema.sql:342/360` hängt die
FTS-Trigger an `sensibel = 0` — ein sensibler Knoten steht NICHT im
Volltextindex. `kern/build_embeddings.py` kennt das Feld gar nicht (0
Vorkommen), vergibt also einen Vektor. Wer WEG- und Steuerdokumente als
sensibel markiert — und „Daten Dritter" legt das nahe —, **zerstört damit
genau den Kanal, der Namen findet** (FTS: Ränge 1/9/70; Vektor: 4/218/1804).

**Ein Befund korrigiert eine eigene Lehre:** „Weg B — Gattungsfilter in der
Anfrage" ist bereits der Ist-Zustand (`haken/suchpfad_abruf.py:125`). Er war
nie eine Option.

## §4a Die Sprache der Oberfläche (`BDW-P19`)

Betreiberwort 2026-08-21: *„wenn wir einen englischsprachigen user haben,
sollten diese dinge auch auf englisch angezeigt werden"*.

**Abzugrenzen von `BDW-P10`, und die Verwechslung lag nahe:** Dort ist
`sprache` die Sprache des EINTRAGS — gemessen 3 573 de, 1 609 en. Hier ist es
die Sprache der ANZEIGE. Zwei verschiedene Größen; die Achse aus B1 hilft
dafür nicht.

Heute führt die englische Tür aus `BDW-P14` in ein deutsches Haus: jede
Hakenmeldung, jeder Meldertext, jeder Triggerfehler ist deutsch. Ein
englischsprachiger Nutzer liest „Gegenprobe faellig" und „Melder ohne
Ausloeser".

**Erhebung läuft** (`runs/sprachstand_oberflaeche_2026-08-21.json`): Zahl und
Zeichenmenge je Ort, getrennt nach dem, was ein Nutzer WIRKLICH sieht — ein
Melder ohne Auslöser erreicht niemanden. Ausdrücklich ohne Empfehlung zur
Bauform: Katalogdatei, Gettext oder englische Texte mit Übersetzungsschicht
bindet alles Spätere, und eine Empfehlung vor der Entscheidung würde die
Zahlen einfärben.

**Die drei Fälle, die sich nicht folgenlos übersetzen lassen**, gehören vorher
benannt: Triggertexte in `schema.sql` (eine geänderte Datei erreicht eine
gewachsene Datenbank nicht von selbst, `L-55075a`) · Texte, auf die ein
Wächter per regulärem Ausdruck prüft (übersetzt greift er nicht mehr,
`L-8fce9c` — heute passiert, siehe §5a) · Texte, die in abgelegten
Wissenseinträgen wörtlich zitiert sind.

## §4b Die Einstellungen im Hermes-Panel — der Schnitt

Betreiberfrage 2026-08-21: welche Schalter (Einzelplatz gegen Unternehmen
usw.) gehören in das Memory-Provider-Plugin?

**Der Maßstab ist, wer davorsitzt.** Hermes' Panel steht vor einem Menschen,
der brainlehr nicht kennt und unsere Messungen nicht kennt. Dorthin gehört,
was ohne unseren Kontext richtig entscheidbar ist. Was eine Begründung aus
unserem Bestand braucht, bleibt in lehrAtelier, wo die Begründung
danebensteht.

**Gemessene Bauform (Hermes, `plugins/memory/config_schema.py`):** Feldarten
`text` · `select` · `secret` · `bool` · `number` · `json`. `inline=True`
markiert das kompakte Panel, der Rest erscheint im vollen Dialog. Zum
Vergleich: `honcho` deklariert 28 Felder (6 inline), `hindsight` 5.

### Ins Hermes-Panel — inline

| Feld | Art | Herkunft | warum dorthin |
|---|---|---|---|
| Datenbankpfad | `text` | `haken/ort.py` | ohne ihn läuft nichts; Plugins liegen pro Profil |
| Ausweis / handelnde Kennung | `text` | `kern/ausweis.py` | ohne sie wird **jeder Schreibvorgang abgewiesen** (Trigger, kein Hinweis) |
| Betriebsprofil | `select` einzelplatz/unternehmen | `knowledge_config.betriebsprofil`, `kern/betriebsprofil.py` | der Schalter, nach dem der Betreiber gefragt hat |
| Mandantenname | `text` | dito | Pflicht beim Wechsel auf `unternehmen`, sonst verborgen |
| Einbettungsdienst — Adresse | `text` | `kern/einrichtung.py` | ohne ihn entstehen Einträge **ohne Vektor**, ohne Fehlermeldung |
| Sprache der Oberfläche | `select` de/en | `BDW-P19` | der Grund, aus dem P19 entstand |

### Ins Hermes-Panel — voller Dialog, nicht inline

| Feld | Art | Anmerkung |
|---|---|---|
| Sprache des eigenen Materials | `select` | `BDW-P10`, nicht dasselbe wie die Oberflächensprache |
| Kataloge beim Erststart | `json` / Mehrfachauswahl | gehört eigentlich auf `POST /api/memory/providers/{name}/setup`, nicht in `config` |
| Einbettungsmodell | **`select` mit GENAU EINER Option** | siehe unten |

### Das eine Feld, das gefährlich ist

`embed_model` (heute `bge-m3@ctx2048`) sieht aus wie eine gewöhnliche
Einstellung. Eine Änderung **entwertet den gesamten Vektorbestand, ohne dass
irgendwo ein Fehler auftaucht** — 7 409 Vektoren. Belegt im Swift-Kommentar
`atelier/app/Sources/BrainlehrCore/Modellzugaenge.swift:8-13`.

**Und Hermes' Schema hat dafür keine Antwort:** Es kennt keine Feldart
„anzeigen, aber nicht ändern". Der generische Renderer macht aus jeder
Deklaration ein Eingabefeld. Der Ausweg ohne Änderung an Hermes:
`KIND_SELECT` mit **genau einer** Option — dem laufenden Modell. Sichtbar,
auf nichts anderes stellbar.

### Ausdrücklich NICHT ins Hermes-Panel

Nicht weil sie unwichtig wären, sondern weil sie ohne unseren Bestand nicht
entscheidbar sind:

* **Gemessene Schwellen** — `MIN_HITS = 3` (Pareto-Front über 60 Versuche),
  `0,65` (zwei Millionen Paare), `0,25` Normkonflikt, `2,0`/`10 %`
  Zugriffsmuster, `84` Kaskadenanteil. Anzeigen ja, bedienbar nein.
* **`BRAINLEHR_DURCHSETZUNG`** (weich/streng) — ein Sicherheitsschalter, den
  ein Fremder nicht beurteilen kann, und seine Verankerung ist ungeklärt.
  Anzeigen ja, bedienbar nein: Wer ihn nicht sieht, kann ihn auch nicht
  versehentlich lockern.

**KORREKTUR desselben Tages, Betreibereinwand, und er trifft den
Ausschlussgrund, nicht die Liste:** *„aber in hermes soll brainlehr auch ohne
lehrAtelier funktionieren, das macht die einstiegshürde kleiner!"*

Richtig. Ich hatte Verfallsraten, Nachtschicht, Siegbedingungs-Gewichte und
Lehren-Beförderung mit „gehört nach lehrAtelier" ausgeschlossen — das setzt
voraus, dass es lehrAtelier gibt. Für einen Hermes-Nutzer gibt es das nicht,
und damit stünde die Einstiegshürde genau dort, wo wir sie wegnehmen wollen.
**brainlehr muss unter Hermes vollständig bedienbar sein, ohne eine zweite
Oberfläche.**

**Der richtige Schnitt ist ein anderer und schärfer: EINSTELLUNG gegen
HANDLUNG.**

| | gehört wohin | warum |
|---|---|---|
| **Einstellung** — ein Wert, der bleibt und das Verhalten prägt | ins `config_schema` | genau dafür ist das Panel gebaut |
| **Handlung** — ein einmaliger Vorgang an einem Gegenstand | in ein **MCP-Werkzeug** | Werkzeuge kommen über `get_tool_schemas()` und brauchen **gar keine Oberfläche** |

Damit lösen sich die vier Punkte auf, ohne dass einer verlorengeht:

* **Nachtschicht** (an/aus, Antrieb, Budget in Aufrufen) → **Einstellung, ins
  Panel.** Das ist eine Entscheidung über die Rechenzeit auf SEINEM Rechner —
  niemand anders kann sie treffen. Vorher hatte ich sie ausgeschlossen; das
  war der klarste Fehler des ersten Schnitts.
* **Verfallsrate je Ast** (`BDW-P13`) → **Einstellung, voller Dialog.** Sie
  braucht Kenntnis des eigenen Materials, und die hat der Nutzer. Kein
  Vorgabewert, leer bis gesetzt — das bleibt.
* **Siegbedingungs-Gewichte** → **Einstellung, voller Dialog**, aber mit der
  Warnung im `info`-Text, dass sie eine Messung verstellen. Nicht sperren:
  Wer misst, darf gewichten.
* **Lehren-Beförderung, Eilmeldungen quittieren, Freigabe je Eintrag,
  Ausweis-Widerruf** → **Handlungen, keine Einstellungen.** Sie gehören in
  Werkzeuge, nicht ins Panel — und sind damit unter Hermes ohnehin erreichbar,
  ohne jede Oberfläche.
* **Ablageort je Domäne** (`ablage.<domaene>`, `BDW-P15`) → **beim Import
  gefragt, nicht im Panel.** Erste Fassung dieses Plans schlug ein
  `json`-Feld vor; das war schwach und wurde auf Betreiberrückfrage
  korrigiert. Ein JSON-Feld in einem Einstellungspanel heißt „ich weiß nicht,
  wo das hingehört" — der Nutzer soll eine Datenstruktur tippen.
  Das echte Problem: `config_schema` deklariert eine FESTE Feldliste, und wie
  viele Domänen es gibt, weiß man beim Deklarieren nicht. Die Auflösung folgt
  aus dem Schnitt oben, den ich zunächst selbst nicht angewandt hatte: Eine
  Domäne wird IMPORTIERT — das ist eine Handlung, und der Ablageort ist Teil
  dieser Handlung. Im Panel steht höchstens eine **Vorgabe für neue Domänen**:
  ein einzelnes `select`, kein JSON.

**Zur Verfallsrate, weil die Frage naheliegt: ausgeschlossen wurde das RATEN,
nicht das SETZEN.** `kern/verfallsrate.py:15-24` hält es fest — „NICHT geraten,
sondern EXPLIZIT VON EINEM MENSCHEN. Kein Vorgabewert. […] Richtig war nur die
Ablehnung des Ratens; eine leer-vorgabewertige Ablage ist keine geratene
Zahl." Nach dem Lauf: 0 gesetzt, Ablage leer — das ist das Ergebnis.
Und die Abgrenzung zur Hausregel „Schwellen sind gemessen, nicht gesetzt":
Die gilt für SYSTEMschwellen (`0,65`, `MIN_HITS=3`). Die Verfallsrate ist ein
FACHURTEIL über ein Gebiet — „Steuerrecht ändert sich jährlich, Zahlentheorie
nicht". Das kann keine Messung liefern. Die gemessene Hälfte (Widerrufsquote
aus der eigenen Historie) bleibt gemessen und wird getrennt ausgewiesen, samt
Widerspruch, wenn beide auseinanderlaufen.

**Was von der ursprünglichen Ausschlussliste übrigbleibt**, und nur das: die
**gemessenen Schwellen**. Sie sind keine Einstellung, sondern das Ergebnis
einer Messung — anzeigen ja, bedienbar nein.



### Die Erklärungen — zweisprachig von Anfang an

Betreiberwort 2026-08-21: *„deswegen brauchen wir auch gute mehrsprachige
erklärungen dazu!"*

**Die Felder dafür existieren und sind ungenutzt:** `description` je Feld,
`info` als Tooltip, `placeholder`, `docs_url`, dazu
`ProviderFieldOption.description` je Auswahlwert. Sechs von acht Anbietern
deklarieren gar kein Schema, füllen also auch nichts davon.

**Was eine Erklärung taugen muss:** Sie sagt nicht, WAS das Feld ist — das
sagt der Feldname. Sie sagt, **was passiert, wenn man es falsch setzt.** Der
Unterschied entscheidet, ob sie Schaden verhindert oder nur Platz braucht:

| Feld | nutzlos | brauchbar |
|---|---|---|
| `embed_model` | „Einbettungsmodell" | „Eine Änderung entwertet 7 409 vorhandene Vektoren, ohne dass ein Fehler erscheint." |
| Ausweis | „Handelnde Kennung" | „Ohne sie weist die Datenbank jeden Schreibvorgang ab — das ist ein Trigger, kein Hinweis." |
| Einbettungsdienst | „Adresse des Dienstes" | „Ist er nicht erreichbar, entstehen Einträge ohne Vektor und sind über die Bedeutungssuche unauffindbar. Am 2026-08-20 dreizehnmal passiert." |
| Betriebsprofil | „Einzelplatz oder Unternehmen" | „`einzelplatz` ist der Auslieferungszustand. Der Wechsel ist später möglich und hat einen Rückweg — beides gefahren und gezählt." |

**Und hier dreht sich das Sprachproblem aus `BDW-P19` um.** Die 707
vorhandenen Textstellen (60 543 Zeichen) sind deutsch gewachsen; sie
nachträglich zweisprachig zu machen kostet den vollen Preis. Diese
Erklärungen dagegen **existieren noch nicht** — sie werden für das Plugin neu
geschrieben. Zweisprachig von Anfang an kostet dabei fast nichts.

**Daraus folgt eine Reihenfolge, die sonst niemand sähe:** Die
Plugin-Erklärungen werden **englisch UND deutsch geschrieben, bevor** über ein
Übersetzungsverfahren für den Altbestand entschieden ist. Sie sind damit der
Prüfstein für die Bauform: Was für fünfzehn neue Texte trägt, trägt auch für
siebenhundert alte — und was schon bei fünfzehn umständlich ist, war die
falsche Wahl.

### Was brainlehr von den anderen sieben unterscheidet

`hindsight` und `honcho` verlangen beide `api_key` als `KIND_SECRET` ohne
Vorgabewert. **brainlehr braucht kein einziges Geheimnis** — local-first heißt,
es gibt keinen Schlüssel zu hinterlegen. Von acht Anbietern wäre es neben
`holographic` der zweite lokale und der einzige ohne Schlüssel.

### Was Hermes technisch verlangt, gemessen

Vier `@abstractmethod` in `agent/memory_provider.py`: `name`,
`is_available`, `initialize`, `get_tool_schemas`. Dazu `plugin.yaml` mit vier
Feldern. `config_schema.py` ist **optional** — sechs der acht Anbieter haben
keins.

**Die beiden Pflichtfelder, die STILL scheitern** (Ausweis und
Einbettungsdienst), gehören in `is_available()`. Gibt die `False` zurück,
fügt der `MemoryManager` den Anbieter gar nicht erst hinzu, statt ihn kaputt
laufen zu lassen.

## §5a Kein neunter Plan — und warum das gemessen wurde

Der Betreiber verlangte am 2026-08-21 „einen neuen Plan und den Lastenkatalog
ergänzen". Der Katalog ist ergänzt (P16–P19). **Ein neues Plandokument wurde
bewusst NICHT angelegt**, und der Grund ist gemessen statt befürchtet:

`grep` über `docs/PLAN_*.md` und `SPRINTS.md`: **`S12` steht in sechs
Dateien**, `S17` in drei, acht weitere in je zwei. Genau die Fehlklasse aus
`L-30be01` — dieselbe Abschnittskennung mehrfach vergeben, aufgefallen
seinerzeit erst an der Frage „wieviele S haben wir insgesamt?", die sich
nicht beantworten ließ. Ein neunter Plan hätte sie fortgesetzt.

**Die Regel daraus, angewandt:** Neue Anforderungen gehen in den KATALOG (eine
normative Quelle, stabile `BDW-`Kennungen, Kennung vor der Vergabe gemessen).
Neue Arbeit wird ein ABSCHNITT in diesem Plan. Ein eigenes Dokument bekommt
nur, was einen eigenen Kennungsraum wirklich braucht.

## §6 Reihenfolge

```
  §3.1 Gegenstand ─┐
                   ├─ bindend zuerst, nicht nachholbar
  §3.2 Faelligkeit ┘
        |
        +--> §4.3 Dokumentenablage (braucht den Gegenstand)
        +--> Kalender, Fristen, Wiedervorlage (brauchen die Faelligkeit)

  UNABHAENGIG, ab sofort:
    §4.1 Namensfrage (P18)   §4.2 Kandidatenbudgets   §4.4 Bauvermeidung
    §4a  Oberflaechensprache (P19)  -- Erhebung laeuft, Bauform offen
    §2   BDW-R05 / Zielbild A  <-- groesster gemessener Rueckstand (3/35)
```

**Katalogbezug:** §3.1 = `BDW-P16` · §3.2 = `BDW-P17` · §4.1 = `BDW-P18` ·
§4a = `BDW-P19` · §4.3 = `BDW-P15`. Der Katalog ist die normative Quelle,
dieser Plan die Umsetzung — bei Widerspruch gilt der Katalog.

## §7 Was bewusst nicht getan wird

* **Kein zweiter Vektorraum, solange der Konsil 1:1 steht.** Die dritte Linse
  entscheidet, oder der Betreiber. Ein Bau auf 1:1 wäre eine Wahl, die sich
  als Messung ausgibt.
* **Kein Werkzeug für Mail, Chat, Buchhaltung.** Siehe §3.
* **Kein `lehrtools`-Etikett auf brainlehr selbst** — brainlehr ist der
  Speicher, kein Werkzeug. Es gehört auf `lehrAtelier` und die
  `openlehr_X`-Domänen.

## §9 Festgeschriebene Reihenfolge (Betreiber, 2026-08-21)

Der Plan ist ab hier fest. Was nicht darin steht, wird nicht gebaut, ohne
dass er fortgeschrieben wird.

**Welle 1 — läuft ab sofort, zwei Stränge nebeneinander:**

| | Gegenstand | besitzt |
|---|---|---|
| **P16** | Gegenstands-Achse, Erstanwendung Plankennungen | `schema.sql`, `kern/gegenstand*.py` |
| **P18** | Namensfrage als Namensfrage erkennen | `haken/suchpfad_abruf.py`, `haken/knowledge_recall_hook.py` |

Die Trennung ist keine Ordnungsfrage: Beide Stränge fassen sonst dieselben
Dateien an, und zwei Agenten an einer Datei erzeugen einen Zwischenstand, den
keiner von beiden geprüft hat (gemessen in der Nacht zum 2026-08-21).

**Welle 2 — nach Welle 1:**
`P17` Fälligkeit (braucht `schema.sql` frei) · §4.2 getrennte
Kandidatenbudgets (braucht `suchpfad_abruf.py` frei) · `P15`
Dokumentenablage (braucht die Gegenstands-Achse aus P16).

**Welle 3:** §2 `BDW-R05` / Zielbild A — der größte gemessene Rückstand
(3/35 = 8,6 % gegen Schwelle 95 %) · §4.4 Bauvermeidung · `P19`-Bauform,
sobald die Hermes-Erklärungen sie erprobt haben.

**Vertagt, nicht offen:** `E24` zweiter Faktor. Betreiberentscheidung
2026-08-21, wörtlich: *„als future markieren, brauchen wir noch nicht"*. Der
Katalog trägt `FUTURE` samt der gemessenen Vorfrage (Median 9 Sitzungen je
Tag), damit die nächste Sitzung sie nicht erneut erhebt.

**Entschieden und damit vom Tisch:** kein zweiter Vektorraum (Konsil 2:1,
`ADR-032`), und `sensibel` ist für Dokumente Dritter das falsche Werkzeug —
geschützt wird über `mandant`/`kreis`/`freigabe`.

## §8 Verlauf

* 2026-08-21T08:20 — angelegt, nach Abschluss des Gesamtbaus und mit zwei von
  drei Konsillinsen.
* 2026-08-21T08:50 — Katalog um P16–P19 ergaenzt (Kennungen gemessen, hoechste war P15). Kein neues Plandokument, siehe §5a.
* 2026-08-21T09:20 — Hermes-Panel geschnitten (Paragraf 4b): 6 Felder inline, 3 im vollen Dialog, 4 Gruppen ausdruecklich draussen.
* 2026-08-21T10:30 — Reihenfolge festgeschrieben (Paragraf 9). E24 vertagt. Welle 1 gestartet.
