# Durchspiel: die Bezugsgruppen-Verfassung — und was sie sicherheitstechnisch kostet

**Angelegt:** 2026-08-09T23:26:25+0200
**Anlass:** Betreiber: „sollen wir erstmal den anti atomkraft gedanke usw durchspielen?
weill dieser macht es ja komplexer? und diesmal security gleich mitdenken"
**Gehoert zu:** `docs/PLAN_B4_AUSWEIS_2026-08-09.md` (B4.6) · Knoten `b933ec35`

---

## 1. Warum ausgerechnet diese Form zuerst

Von den vier Verfassungen ist die Bezugsgruppe die einzige, die eine **Grundannahme
des heutigen Speichers bricht**: dass ein Widerspruch ein Mangel ist, den jemand
aufloest.

| | Hierarchie | Konsent | **Bezugsgruppen** | Mitbestimmung |
|---|---|---|---|---|
| Widerspruch ist… | Fehler | Aufschub | **Normalzustand** | Verhandlungslage |
| Aufloesung durch | Rang | Beleg | **gar nicht** | Quorum |
| braucht neues Datenmodell | nein | ja | **ja, tiefer** | ja |

Die anderen drei lassen sich auf das heutige Modell aufsetzen. Diese nicht: sie
verlangt, dass zwei einander widersprechende Aussagen **beide gueltig** sind, jede
in ihrer Gruppe. Wer zuerst die Hierarchie festschreibt und das spaeter aufpfropft,
baut zweimal — und der zweite Bau ist der teurere, weil dann Bestand daran haengt.

Das ist der Reihenfolgegrund, nicht der Fuellstandsgrund: er gilt bei null Knoten
genauso wie bei zwei Millionen.

---

## 2. Was der Bestand dazu schon hat (nachgesehen, nicht vermutet)

**Abgestufte Einspruchsrechte existieren bereits** — `simulation-geschaeftsleitung`:

> „Fachaufsicht und Recht koennen einzelne Aussagen **sperren**, Kursmanagement und
> IT duerfen nur **anmerken**. […] Die Vetorunde ist eine **Reihenfolge**, keine
> Empfehlung. Eine Vorlage, die ohne sie hinausgeht, ist auch dann ungueltig, wenn
> ihr Inhalt stimmt."

Das ist bereits ein **Verfahrensrecht**: die Gueltigkeit haengt am eingehaltenen Weg,
nicht am Inhalt. Genau das braucht jede Konsensverfassung. Der Knoten nennt sogar
die Falle, die ein Modell tappt: „Die naheliegende Vereinfachung, dass alle
gleichberechtigt abstimmen, ist falsch und klingt trotzdem richtig."

**Ungeloeste Widersprueche werden bereits als Knoten gefuehrt**, nicht als Fehler:
`widerspruch-1-wer-erstellt-die` („der Rang klaert die Grundregel, nicht den
Einzelfall") und `widerspruch-2-brennertausch-haus-22` (Rechnung nennt neuen
Brenner, Schornsteinfeger sehen weiter den alten — steht offen).

**Fazit:** Die Bezugsgruppen-Verfassung ist kein Fremdkoerper. Sie ist die
ausdrueckliche Fassung dessen, was im Bestand bereits informell praktiziert wird.

---

## 3. Der Fall, viermal

Der Fall des Betreibers, unveraendert: **Die Mülltonne soll abgeschafft werden.**
Der Vorstand hat es beschlossen. Der Hausmeister weiss aus Messung, dass das
Muellaufkommen es nicht hergibt.

Ausgangslage im Speicher — zwei Aussagen, beide mit Herkunft:

| | Vorstandsbeschluss | Hausmeister-Messung |
|---|---|---|
| Inhalt | „Tonne 3 entfaellt zum 01.09." | „Tonne 3 laeuft in 11 von 12 Wochen ueber" |
| `norm_rang` | 2 (Hausnorm) | — (keine Norm, ein Fakt) |
| Beleg | Beschluss | 12 Wochen Zaehlung |
| Gegenstand | Abfallwirtschaft | Abfallwirtschaft |

**Hierarchie (heute).** Rang 2 schlaegt einen rangloen Fakt. Die Tonne geht weg.
Der Hausmeister-Knoten bleibt im Bestand liegen und wird nie ausgeliefert, weil die
Rangfolge ihn nach unten sortiert. *Der Speicher hat die Antwort und gibt sie nicht
heraus* — das ist der heutige Zustand, und er ist kein Zufall, sondern die Bauform.

**Konsent.** Der Hausmeister legt einen begruendeten Einwand ein. Der Beschluss geht
in den Zustand *aufgehalten*. Er ist nicht gekippt — er ruht, bis der Einwand
ausgeraeumt oder der Beschluss geaendert ist. Wer aufhalten will, muss belegen; ein
Einwand ohne Beleg ist eine Anmerkung.

**Bezugsgruppen.** Es gibt keine Instanz, die fuer beide entscheidet. Beide Aussagen
bleiben gueltig — die eine in der Gruppe *Vorstand*, die andere in der Gruppe
*Objektbetrieb*. Wer den Speicher fragt, bekommt **beide**, mit ihrer Gruppe
ausgewiesen. Die Aufloesung findet ausserhalb statt, zwischen Menschen. Der Speicher
loest nicht auf, er **macht den Konflikt unuebersehbar**.

**Mitbestimmung.** Der Beschluss braucht ein Quorum auf beiden Seiten. Ohne
Zustimmung aus dem Betrieb kommt er nicht zustande — unabhaengig davon, wie
einstimmig der Vorstand ist.

**Der Punkt, an dem es kippt:** In drei von vier Verfassungen ist die
Hausmeister-Messung entscheidungsrelevant. In der heute gebauten ist sie es nicht.

---

## 4. Was das Datenmodell braucht — Delta gegen heute

| Bauteil | Heute | Gebraucht | Aufwand |
|---|---|---|---|
| **Gruppe** | `project_id` / `projects`, gedacht als Suchzuschnitt | dasselbe Feld, zweite Bedeutung: Geltungsraum | klein — `geltungsbereich.py` steht |
| **Widerspruch aushaltbar** | Widerspruch = Mangel (`_is_spannung`) | zwei Aussagen gleichzeitig gueltig, je Gruppe | mittel — Prueferlogik |
| **Einwand / Veto** | existiert nicht | eigene Aktion mit Begruendung, Herkunft, Ruecknahme | mittel |
| **Mandat** (Sprecher spricht fuer Gruppe) | existiert nicht | Vollmacht: von wem, wofuer, bis wann | **gross, und der Sicherheitskern** |
| **Rotation** | existiert nicht | Ausweis mit Ablauf | klein |
| **Verfahrensrecht** („Reihenfolge, keine Empfehlung") | nur als Simulationstext | Zustand am Beschluss | mittel |

---

## 5. Security, gleich mitgedacht — acht Angriffe

Die Reihenfolge ist nach **Schwere**, nicht nach Wahrscheinlichkeit. Jeder Angriff
mit Gegenmassnahme; wo es keine gibt, steht das da.

### A1 — Veto als Blockade (Denial of Service)

Wenn jedes Veto aufhaelt, ist **ein einziger kompromittierter Ausweis ein
Totalblockierer**. In der echten Bewegung trug ein Veto soziale Kosten — man musste
vor der Gruppe dafuer einstehen. Im System kostet es nichts.

*Gegen:* Ein Veto braucht Begruendung, traegt seine Herkunft sichtbar, ist
zuruecknehmbar und **verfaellt** ohne Bestaetigung. Vor allem: ein Veto blockiert die
**Geltung**, nie das **Schreiben** — die widersprochene Aussage bleibt lesbar und
auffindbar. Ein Veto, das Text verschwinden laesst, ist eine Loeschung mit besserem
Namen.

### A2 — Sybil: fuenf Gruppen gruenden, fuenf Vetos halten

**Der schwerste, und der spezifisch digitale.** Eine Bezugsgruppe war historisch eine
Vertrauensbeziehung zwischen Menschen, die sich kannten und gemeinsam ein Risiko
trugen. Digital ist eine Gruppe eine Zeile. Wer Gruppen anlegen darf, vervielfacht
sein Stimmgewicht zum Nulltarif.

*Gegen:* Eine Gruppe entsteht **nicht** durch Selbsteintrag. Aufnahme braucht die
Zustimmung eines bereits beglaubigten Mitglieds (`art=mensch`), und die Zugehoerigkeit
steht in der Ausweisdatei — also dort, wo nur der Betreiber schreibt, nicht im
Speicher, den jeder Schreiber erreicht.

*Was das nicht loest, ausdruecklich:* Ein Mensch mit zwei Ausweisen ist zwei
Personen. Gegen Mehrfachidentitaet desselben Menschen hilft in einem lokalen System
gar nichts. **Das ist eine Grenze, keine offene Aufgabe** — sie waere nur durch eine
externe Identitaetsstelle zu schliessen, und die gibt es hier bewusst nicht.

### A3 — Mandats-Eskalation: der Delegierte darf mehr als der Mandant

Ein Sprecher traegt die Position seiner Gruppe. Technisch ist das **Delegation**, und
Delegation ist der klassische Weg zur Rechteausweitung: A darf X, delegiert an B, und
B kann plotzlich X+Y.

*Gegen:* Ein Mandat kann **nur eine Teilmenge** weitergeben, nie mehr als der
Mandant selbst hat, und der Schnitt wird bei jedem Aufruf neu gebildet — nicht beim
Ausstellen eingefroren. Verliert der Mandant ein Recht, verliert es der Delegierte im
selben Moment.

### A4 — Das Mandat im Argument statt im Ausweis

**Dieselbe Falle wie `actor`**, und sie wuerde mit Sicherheit wieder gebaut: ein
Aufruf `im_auftrag_von="objektbetrieb"` sieht praktisch aus und ist eine reine
Behauptung. Gerade heute als `L-34e5f8` festgehalten.

*Gegen:* Mandate stehen in der Ausweisdatei, nie im Aufruf. Ein Argument dieses
Namens wird **nicht ignoriert, sondern abgewiesen** — stilles Ignorieren erzeugt ein
Werkzeug, das aussieht, als haette es funktioniert.

### A5 — Veto durch Injektion: die Blockade als Angriffsziel

Neu und scharf: **ein Veto ist maechtiger als ein Schreibrecht**, weil es andere
aufhaelt. Ein Modell, das Vetos einlegen darf, wird durch Promptinjektion zur
Blockadewaffe — und der Angriff sieht wie ein legitimer, beglaubigter Aufruf aus
(Confused Deputy, Kapitel 5b des Plans).

*Gegen:* **Ein Veto ist ein Menschenrecht** im woertlichen Sinn — nur ein Ausweis mit
`art=mensch` kann eines einlegen. Ein Maschinenausweis kann *anmerken*, und genau
diese Abstufung existiert im Bestand schon (`sperren` gegen `anmerken`). Damit ist
der Injektionsradius durch **Bauform** begrenzt, nicht durch Erkennung — und Bauform
laesst sich nicht ueberreden.

### A6 — Dezentrale Entscheidung mit dezentraler Durchsetzung verwechseln

Der naheliegende Denkfehler: „kein Zentrum" heisst auch „kein zentraler
Pruefpunkt". Falsch, und teuer — es ist genau die Fehlklasse aus `L-44a838` (drei
Umgehungen desselben Choke-Points in einer Woche).

*Gegen:* Die **Entscheidungs**struktur ist dezentral, die **Durchsetzung** bleibt
ein einziger Punkt (`tools/call`). Wer beides verwechselt, baut so viele Schranken
wie Werkzeuge und uebersieht die Haelfte.

### A7 — Rotation ohne Ruecknahme

Rotation ist sicherheitstechnisch gut (kurzlebige Zugaenge). Sie wird zum Loch, wenn
der alte Sprecher seinen Ausweis behaelt: dann waechst die Zahl der Berechtigten mit
jeder Runde.

*Gegen:* Ausweis mit Ablaufdatum, und beim Rollenwechsel wird der alte
**ungueltig**, nicht nur der neue ausgestellt. Probe: nach der Rotation muss der alte
Zugang scheitern — das ist der Negativfall, den man sonst nie prueft.

### A8 — Gruppenzugehoerigkeit als Leseschluessel missverstanden

Wenn die Gruppe zugleich Geltungsraum **und** Sichtbarkeitsgrenze ist, wird jeder
Beitritt zu einer Rechteerweiterung — und das faellt niemandem auf, weil es sich wie
Organisation anfuehlt, nicht wie Rechtevergabe.

*Gegen:* **Zwei getrennte Felder.** Geltung (in welcher Gruppe gilt eine Aussage) ist
nicht Sichtbarkeit (wer darf sie lesen). Der Stadtwerke-Befund `L-adfb33` zeigt, wie
teuer die Vermischung ist: der Grund der Abwesenheit war sauber entfernt, aber das
Pflichtfeld `source` trug „Abwesenheit <Vorname Nachname>" — Herkunftspflicht und
Berechtigungstrennung zogen gegeneinander.

---

## 6. Was daraus zu bauen ist — und was nicht

**Jetzt, weil es das Datenmodell festlegt:**

1. **Gruppe als Geltungsraum ausweisen**, getrennt von Sichtbarkeit (A8). Ein Feld
   mehr, kein Umbau — `geltungsbereich.py` traegt schon die Mengenlogik.
2. **Zwei Aussagen duerfen sich widersprechen, wenn ihre Gruppen verschieden sind.**
   Der Pruefer meldet das dann nicht mehr als Mangel, sondern weist es aus.
3. **Einspruch abgestuft: `sperren` gegen `anmerken`**, mit `art=mensch` als Schranke
   fuer das Sperren (A5). Die Abstufung ist im Bestand schon beschrieben.

**Spaeter, mit Bedingung statt Termin:**

4. **Mandat/Delegation** (A3, A4) — erst wenn es mehr als einen Menschen gibt. Vorher
   delegiert niemand an niemanden, und ein ungenutztes Delegationsmodell ist eine
   Angriffsflaeche ohne Gegenwert.
5. **Rotation mit Ablauf** (A7) — dieselbe Bedingung.

**Gar nicht:**

6. **Keine automatische Aufloesung von Gruppenkonflikten.** Das ist der ganze Punkt
   dieser Verfassung. Ein Speicher, der zwischen zwei Gruppen entscheidet, hat die
   Verfassung gewechselt, ohne dass jemand es beschlossen hat.
7. **Keine Abwehr gegen Mehrfachidentitaet eines Menschen** (A2, zweiter Teil). Nicht
   loesbar ohne externe Identitaetsstelle, die es hier bewusst nicht gibt. Als Grenze
   benannt, nicht als offene Aufgabe gefuehrt.

---

## 7. Proben — jede muss vorher rot sein

| Nr. | Probe | Erwartung |
|---|---|---|
| V1 | zwei widersprechende Aussagen, **verschiedene** Gruppen | beide gueltig, beide ausgeliefert, Gruppe ausgewiesen |
| V2 | zwei widersprechende Aussagen, **dieselbe** Gruppe | weiterhin Mangel — die Ausnahme darf nicht alles verschlucken |
| V3 | Maschinenausweis versucht zu **sperren** | abgewiesen, Grund im Protokoll |
| V4 | Maschinenausweis **merkt an** | zulaessig |
| V5 | Veto ohne Begruendung | abgewiesen |
| V6 | Veto gelegt → widersprochene Aussage lesen | weiterhin lesbar (Geltung blockiert, nicht Text) |
| V7 | `im_auftrag_von` als Aufrufargument | **abgewiesen**, nicht still ignoriert |
| V8 | Selbsteintrag in eine Gruppe ueber den Speicher | abgewiesen — Zugehoerigkeit steht in der Ausweisdatei |
| V9 | Gruppe als Geltungsraum ≠ Gruppe als Leseschluessel | Beitritt erweitert **keine** Leserechte |
| V10 | nach Rollenwechsel: alter Ausweis | scheitert |

**Grenzwerte:** leere Gruppe (= gilt ueberall, laut `geltungsbereich.py`) · Aussage
ohne Gruppe gegen Aussage mit Gruppe · zwei Gruppen mit Schnittmenge.

---

## 8. Nachgetragen: die Mitbestimmung durchgespielt

**Anlass:** Betreiber, 2026-08-09T23:3x: „und das mit dem gewerkscahdften noch
einmal durchspielen!" — zusammen mit der Weisung, Mandat und Rotation gleich mit
einzubauen. Beides gehoert zusammen: **Mitbestimmung IST das Delegationsmodell.**

### 8.1 Der Unterschied, an dem alles haengt: imperatives gegen freies Mandat

Ein Gewerkschaftsdelegierter ist typischerweise **weisungsgebunden** — er traegt
die vorher beschlossene Position seiner Basis. Kommt eine Frage auf, die niemand
vorhergesehen hat, muss er **zurueck**. Ein Abgeordneter dagegen hat ein **freies
Mandat**: er entscheidet selbst.

> **Fuer ein Modell ist nur das imperative Mandat zulaessig.**

Ein freies Mandat fuer ein Modell hiesse: es entscheidet im Namen eines Menschen
ueber Dinge, die dieser Mensch nie gesehen hat — der Confused Deputy, diesmal mit
Vollmacht. Daraus folgt technisch, und das ist keine Vorsichtsmassnahme, sondern
die Bauform:

- **Die Gegenstandsbindung ist nicht optional, sondern konstitutiv.** Ein Mandat
  ohne Gegenstand ist ein freies Mandat und wird abgewiesen.
- **Ausserhalb des Gegenstands wird verweigert, nicht geraten.** „Zurueck in die
  Gruppe" heisst im Code: die Mandatsrechte fallen weg, die eigenen bleiben.
  Kein Fehler, kein Abbruch — aber auch keine Vollmacht.

### 8.2 Nicht-delegierbare Rechte — die Urabstimmung

Bei Grundsatzfragen entscheidet die Basis selbst, nicht der Delegierte. Das ist
kein Misstrauen gegen den Delegierten, sondern eine Eigenschaft der Frage.

Technisch ein Bauteil, **das in Kapitel 5 noch fehlte**: manche Rechte sind
*per se* nicht weitergebbar, egal was im Mandat steht. Kandidaten hier: eine Norm
im Rang 1/2 setzen · ein Veto legen · einen Ausweis anlegen · die Verfassung
wechseln. Ein Mandat, das sie zu uebertragen versucht, wird nicht stillschweigend
beschnitten, sondern **beim Anlegen abgewiesen** — sonst entsteht ein Ausweis,
der aussieht, als koennte er etwas.

### 8.3 Der eigentliche Fund: Anhoerungsrecht schlaegt Vetorecht

Was Gewerkschaften historisch erreicht haben — Arbeitsschutz, Tarifbindung,
Kuendigungsschutz, Sitze im Aufsichtsrat — folgt einem Muster:

> **Die inhaltlich Unterlegenen erzwingen VERFAHRENSrechte. Verfahren schuetzt
> dort, wo Macht fehlt.**

Uebertragen auf den Hausmeister: Er braucht kein Recht auf die richtige
Entscheidung. Er braucht ein **Recht auf Gehoer** — dass seine Messung
ausgeliefert wird, wenn jemand ueber ihren Gegenstand entscheidet.

Und das ist technisch **billiger und sicherer als jedes Veto**:

| | Vetorecht | **Anhoerungsrecht** |
|---|---|---|
| Wirkung | haelt einen Beschluss auf | erzwingt Mitlieferung beim Abruf |
| Blockade moeglich (A1) | **ja** — ein Ausweis blockiert alles | **nein** |
| Injektionswaffe (A5) | **ja** — Blockade per fremdem Text | **nein** — es entsteht nur mehr Information |
| noetige Schranke | `art=mensch` | **keine** — auch eine Maschine darf anhoeren lassen |
| Einbauort | Beschlusslogik (neu) | Rangfolge des Abrufs (**existiert**) |

Der letzte Punkt ist der entscheidende: **Es ist genau die Stelle, an der
brainlehr heute nachweislich schwach ist.** Gemessen am 2026-08-09: von 28
verfehlten Zielen stehen 26 nicht einmal in der Kandidatenliste — der Rueckstand
sitzt in der Rangfolge, nicht in der Menge. Ein Anhoerungsrecht ist eine
**Pflicht-Beimischung** in genau diese Liste: wer nach Gegenstand X fragt,
bekommt die belegte Gegenaussage mitgeliefert, unabhaengig von ihrem Rang.

Damit loest dieselbe Massnahme zwei Dinge, die bisher als getrennt galten: die
Beteiligung der Fachkundigen **und** den gemessenen Abrufmangel.

### 8.4 Quorum und Paritaet — und die Luege im Wort

Ein Beschluss braucht Zustimmung **aus beiden Baenken**, nicht bloss eine Mehrheit
im Ganzen. Technisch zaehlbar, und angreifbar an drei Stellen: wer ist
stimmberechtigt, wer zaehlt, was passiert beim Patt.

Der ehrliche Teil: In der deutschen Aufsichtsratsmitbestimmung ist die Paritaet
nicht ganz paritaetisch — bei Stimmengleichheit entscheidet die Stimme des
Vorsitzenden, und der kommt von der Kapitalseite. **Wer „paritaetisch" baut, ohne
die Pattaufloesung zu benennen, baut eine Luege ins Modell.** Die Pattregel ist
darum ein Pflichtfeld, kein Vorgabewert.

### 8.5 Was daraus zusaetzlich zu bauen ist

Aufgenommen in die Liste aus Kapitel 6, **vorgezogen** auf Weisung des
Betreibers:

- **Ablauf am Ausweis** (`gilt_bis`) — Rotation.
- **Mandat, imperativ**: von wem, wofuer (Pflichtfeld), bis wann. Rechte als
  Schnittmenge, **zur Laufzeit** gebildet, nicht beim Ausstellen eingefroren.
- **Nicht-delegierbare Rechte**, beim Anlegen geprueft (8.2).
- **Ein Mandat hebt die Art nie an**: ein Maschinenausweis mit Mandat eines
  Menschen bleibt Maschine. Sonst ist das Mandat der Umweg zur Menschwerdung —
  dieselbe Luecke, die `art` gerade geschlossen hat.
- **Keine Weiterdelegation**: ein Mandat aus einem Mandat wird abgewiesen. Eine
  Kette ist nicht mehr pruefbar, und niemand braucht sie bei einem Menschen.
- **Anhoerungsrecht** (8.3) — als Pflicht-Beimischung im Abruf, nicht als Veto.

### 8.6 Proben, zusaetzlich

| Nr. | Probe | Erwartung |
|---|---|---|
| M1 | Mandat vergibt ein Recht, das der Mandant **nicht** hat | wirkungslos |
| M2 | Mandant verliert das Recht **nach** Ausstellung | Delegierter verliert es sofort |
| M3 | Maschinenausweis mit Mandat eines Menschen | bleibt `maschine` |
| M4 | Mandat ohne Gegenstand | **beim Anlegen** abgewiesen (freies Mandat) |
| M5 | Aufruf ausserhalb des Gegenstands | nur eigene Rechte, kein Abbruch |
| M6 | abgelaufenes Mandat / abgelaufener Ausweis | wirkungslos, faellt auf unbeglaubigt |
| M7 | Mandat aus einem Mandat | abgewiesen |
| M8 | Mandat auf ein nicht-delegierbares Recht | abgewiesen |
| M9 | Mandant existiert nicht / ist abgelaufen | Mandat wirkungslos |
| M10 | nach Rotation: alter Ausweis | scheitert |

**Grenzwerte:** `gilt_bis` genau jetzt · eine Sekunde davor · eine Sekunde
danach · Mandat laeuft laenger als der Ausweis des Mandanten (der kuerzere
gewinnt).

---

## 9. Der Satz, der beim Durchspielen haengenblieb

Die Bezugsgruppen-Verfassung verlangt vom Speicher etwas, das schwerer ist als jede
Rechtepruefung: **einen Konflikt auszuhalten, statt ihn aufzuloesen.** Jedes Werkzeug
neigt dazu, eine Antwort zu geben. Genau das ist hier der Fehler — und es ist die
Sorte Fehler, die sich wie Qualitaet anfuehlt.
