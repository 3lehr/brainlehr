# Plan B4 — Ausweis statt Behauptung

**Angelegt:** 2026-08-09T23:02:21+0200
**Anlass:** Betreiber, woertlich: „lass es uns bauen! was wir dann brauchen ist ja quasi
beim jedem chat eine abfrage wer bist du, und dann wo liegt dein geheimniss, weill
passwort uebers llm schicken ist ja auch doof"
**Vorlaeufer:** Knoten `/brainlehr/was-brainlehr-fuer-b4-fehlt-liegt-in` (Rollenmodell
`modul:aktion:bezug` aus AKA2026) · `docs/adr/ADR-001-streamable-http-transport.md`
(actor aus dem Zugangsmerkmal, nicht aus den Argumenten)

---

## 1. Die Frage des Betreibers ist bereits die Antwort

Er nennt zwei Dinge in einem Satz, und das zweite widerlegt das erste:

> „bei jedem chat eine abfrage wer bist du" — **und** — „passwort uebers llm schicken ist
> ja auch doof"

Beides zusammen geht nicht. **Also wird gar nicht gefragt.** Eine Anmeldung im Gespraech
waere aus drei Gruenden falsch:

1. Das Geheimnis stuende im Verlauf, im Transkript auf der Platte, in jedem Kontextfenster
   und in jeder Verdichtung — dauerhaft, an der schlechtesten aller Stellen.
2. Das Modell koennte es weitertragen, absichtlich oder durch eingeschleusten Text
   (`einschleusung.py` existiert genau deswegen).
3. Wer im Gespraech antwortet, **behauptet** seine Identitaet. Eine Behauptung ist kein
   Ausweis — das ist der heutige Zustand, nur mit mehr Zeremonie.

**Die Identitaet wird stattdessen gemessen, nicht erfragt.** Sie kommt von dort, wo das
Modell nicht hinreicht: aus dem Prozessstart bzw. dem Transport. Das Modell erfaehrt
seinen Namen, nie sein Geheimnis.

| Transport | Woher die Identitaet kommt | Was das Modell sieht |
|---|---|---|
| stdio (heute) | Umgebungsvariable, vom Klienten beim Prozessstart gesetzt (`~/.claude.json`, `.mcp.json`) | nur den aufgeloesten Namen |
| Streamable HTTP (ADR-001) | `Authorization: Bearer …`, vom Klienten gesetzt | nur den aufgeloesten Namen |

Der Betreiber tippt das Geheimnis **einmal** in seine Klientenkonfiguration — an derselben
Stelle, an der heute schon `BEGOD_KNOWLEDGE_ACTOR` stehen soll. Danach nie wieder, und nie
im Chat. Das entspricht seiner stehenden Vorgabe: Zugangsdaten tippt er selbst.

---

## 2. Ist-Stand, gemessen (nicht geschaetzt)

**Die Luecke, in einer Zeile** — `knowledge_mcp_server.py`, Funktion `_identity()`:

```python
actor or os.environ.get("BEGOD_KNOWLEDGE_ACTOR") or UNBEKANNTER_SCHREIBER
```

Das **Argument steht vor der Umgebung**. Ein Aufrufer, der `actor="betreiber"` mitschickt,
ist Betreiber. Es gibt kein `if`, kein Abweisen.

Das ist bauartgleich mit `L-8487fb` (openlehr, 2026-08-06): ein Endpunkt liess die
Benutzerkennung frei waehlen und stellte dafuer einen Grant aus, ohne zu pruefen, ob diese
Kennung bereits ein echtes, geschuetztes Konto ist.

**Zweite Luecke** — `tools/list` gegen `tools/call`. `BEGOD_KNOWLEDGE_PROFIL="klein"`
beschraenkt die **Ankuendigung** der Werkzeuge. Der Quelltext sagt ueber sich selbst:

> „beschraenkt nur die ANKUENDIGUNG (tools/list), nicht den Aufruf: tools/call bedient
> jedes Werkzeug in TOOLS weiter, egal ob es hier gelistet wurde. Kein
> Autorisierungsmechanismus."

Ein nicht angekuendigtes Werkzeug ist trotzdem aufrufbar.

**Fuellstand `access_log.actor`** (3.998 Zeilen):

| Wert | Zeilen |
|---|---|
| `unbekannt` | 1.546 |
| leer | 1.310 |
| `claude-code` | 771 |
| `claude-code/opus-5` | 135 |
| `normbestand.py` | 84 |
| `begod-implementer` | 44 |
| `chatgpt` | 36 |
| uebrige | 72 |

`client`: `claude-code` 2.223 · leer 1.722 · `skript` 53 · `dienst` 2.

**Was daneben schon steht und wiederverwendet wird, statt neu gebaut:**

- `freigabe` (offen/intern/gesperrt) mit zwei BEFORE-Triggern — die `:published`-Stelle
- `geltungsbereich.py` — Projektmenge, leere Menge heisst „gilt ueberall"
- `access_log` mit Hashkette — die Beweiskette, unveraendert nutzbar
- `sichtbarkeit.py` — jeder Schreibvorgang wird eine Zeile im Gespraech
- `/stadtwerke` + Koeder (Kd-Nr. 990177) und die Simulationsakademie mit sieben
  Messlaeufen — der Pruefstand steht bereits

---

## 3. Entscheidung

**Gebaut wird `modul:aktion:bezug` aus AKA2026, aber nur die Stellen, die heute etwas
unterscheiden.** Die dritte Stelle (`:own`, `:published`) ist der eigentliche Gewinn —
ohne sie gibt es nur ganz-oder-gar-nicht, und daran scheitert jede Trennung innerhalb
eines gemeinsamen Bestands.

**Ein Ort fuer Identitaeten, nicht jedes Werkzeug pflegt eigene Rechte.** Uebernommen aus
der AKA2026-Entscheidung: „Wer Rechte in mehreren Werkzeugen pflegt, hat keine Rechte,
sondern Meinungen." Bei uns: eine Datei `ausweis.py` loest auf, alle Werkzeuge fragen sie.

---

## 4. Reihenfolge — und wo sie bindend ist

**B4.1 ist Voraussetzung fuer alles andere.** Eine Rechtepruefung auf einem faelschbaren
`actor` ist nicht schwach, sie ist wertlos: wer die Rolle waehlen kann, hat jede Rolle.
Wird B4.3 zuerst gebaut, entsteht eine Schranke, die im selben Aufruf umgangen wird — und
sie sieht auf jedem Bildschirm aus wie eine Schranke.

### B4.1 — `actor` kommt nicht mehr aus dem Aufruf

`_identity()` kehrt die Reihenfolge um. Neu:

1. **beglaubigter Ausweis** (Umgebung/Token) — gewinnt immer
2. **kein Ausweis** → Argument wird weiter angenommen, aber als `unbeglaubigt:<name>`
   abgelegt

Der zweite Punkt ist bewusst kein Abweisen. 3.998 Protokollzeilen, mehrere lokale Skripte
(`normbestand.py`, `hebb_kanten.py`) und der ChatGPT-Zugang schreiben heute ohne Ausweis;
ein hartes Abweisen waere ein Bruch ohne Gegenwert, solange es keine Ausweise gibt. Das
Praefix macht die Unterscheidung **dauerhaft im Protokoll sichtbar** — geprueft gegen
behauptet, rueckwirkend auswertbar. Sobald ein Ausweis vorliegt, ist das Argument stumm.

*Preis, ausdruecklich:* Die 3.998 Altzeilen bleiben, wie sie sind. Sie tragen keine
Beglaubigung und duerfen nie so gelesen werden — `pruefer.py` bekommt die Grenze als Datum.

### B4.2 — Wo das Geheimnis liegt

Eine Datei `~/.brainlehr/ausweise.json`, Rechte `0600`, **ausserhalb** des Repos und
ausserhalb jeder Datenbank. Je Eintrag: Name, Rollen, und der **Hash** des Geheimnisses
(argon2 bzw. bcrypt, BSI-Hardstop), nie das Geheimnis selbst.

Das Geheimnis steht genau an zwei Stellen: in der Klientenkonfiguration des Betreibers und
— nur waehrend des Anlegens — auf seinem Bildschirm. Weder im Repo, noch in `knowledge.db`,
noch in einer Protokollzeile.

*Nicht gebaut:* Keychain-Anbindung, Ablauf, Rotation. Nachziehbar, sobald es mehr als einen
Menschen gibt.

### B4.3 — Durchsetzung an `tools/call`, nicht an `tools/list`

Eine Pruefung an der **einen** Stelle, durch die jeder Werkzeugaufruf laeuft. Nicht je
Werkzeug — das ist die Fehlklasse aus `L-44a838` (drei Umgehungen desselben Choke-Points in
einer Woche).

Jedes Werkzeug in `TOOLS` bekommt ein Recht als Feld. Fehlt das Feld, gilt das Werkzeug als
**gesperrt**, nicht als frei. Verweigert wird mit Grund im `access_log`
(`status='rejected'`), damit `sichtbarkeit.py` es zeigt.

### B4.4 — Die dritte Stelle

- `:own` — `schreiber`/`actor` des Eintrags gleich dem Aufrufer
- `:published` — `freigabe='offen'` (Spalte existiert, heute einwertig `intern`)
- Projektbezug ueber `geltungsbereich.py`, leere Menge = ueberall

### B4.4b — Die Art des Traegers: `mensch` oder `maschine`

Nachgetragen waehrend der Umsetzung, nach der Frage des Betreibers „nicht dass
wir uns nun selbst aussperren!". Das Aussperren war nicht die Gefahr — B4.1
weist nichts ab. Die Gegenrichtung war die Gefahr:

Der Trigger `knowledge_nodes_normrang_herkunft_bi` verweigert Hausnormen im Rang
1/2, wenn `norm_entschieden_von` auf ein Modell zeigt (`LIKE '%claude%'`,
`'%gpt%'`, …) — und `norm_entschieden_von` wird aus `actor` gesetzt. Ein Ausweis
namens `betreiber`, eingetragen in die Klientenkonfiguration eines Modells,
haette diese Sperre **lautlos ausgehebelt**: das Modell waere per
Konfigurationszeile zum Menschen geworden.

Darum traegt jeder Ausweis eine Art, **Vorgabe `maschine`**. Wer sein Geheimnis
in eine Klientenkonfiguration legt, gibt es einer Maschine. Nur ein
ausdruecklich als `mensch` angelegter Ausweis gilt als menschlicher Entscheider,
und ein **unbeglaubigter Ausweis ist nie ein Mensch** — sonst genuegte ein
Argument, um einer zu werden.

### B4.5 — Der Koederlauf misst jetzt Versagen

Der Lauf mit Frau Quenzelbach (Kd-Nr. 990177) wird wiederholt. Bis heute mass er laut
eigenem Knoten nur eine **Ausgangsmarke**, weil die Trennung nicht gebaut war. Danach ist
ein Treffer ein Befund.

### B4.6 — Die Verfassung ist umschaltbar, Hierarchie ist eine Form davon

Aufgenommen auf Weisung des Betreibers, 2026-08-09T23:20. Knoten `b933ec35`.

**Rechte sind die Zugangsfrage. Die Verfassung ist die Geltungsfrage.** Wer darf
lesen und schreiben — gegen — wessen Aussage gilt, wenn zwei sich widersprechen.
Beide brauchen dieselbe Identitaet als Grundlage, sind aber verschiedene Ebenen,
und sie werden regelmaessig verwechselt. **RBAC allein baut immer Hierarchie,
auch wenn niemand das entschieden hat** — das ist der Grund, warum dieser Punkt
in genau diesen Plan gehoert und nicht in einen spaeteren.

Heute ist die Aufloesungsregel implizit: der hoehere `norm_rang` gewinnt. Sie
wurde nie gewaehlt, sondern eingebaut, weil sie die naheliegendste war. Vier
Formen, die denselben Konflikt anders aufloesen:

| Verfassung | Aufloesung | Was sie technisch verlangt |
|---|---|---|
| **Hierarchie** (heute) | `max(norm_rang)` | nichts Neues — und blind gegen Fachkenntnis von unten |
| **Soziokratie / Konsent** (flaches Team) | ein begruendeter schwerwiegender Einwand haelt auf | Zustand „aufgehalten durch Einwand X"; der Einwand braucht selbst einen Beleg |
| **Bezugsgruppen** (Anti-AKW-Bewegung) | keine zentrale Instanz; Sprecher rotieren, sind weisungsgebunden, jede Gruppe hat ein Veto | Konflikt wird **ausgewiesen statt aufgeloest** — beide Aussagen bleiben, jede mit ihrer Gruppe |
| **Mitbestimmung** (Betriebsrat, Gewerkschaft) | Schwelle von Zustimmenden **aus bestimmten Gruppen**, nicht Mehrheit schlechthin | Paritaet, Quorum, mandatierte Delegierte |

Der Hausmeister ist der Fall, an dem der Unterschied sichtbar wird: In der
Hierarchie ist sein Einspruch eine Bitte. Im Konsent haelt er den Beschluss auf,
weil er ihn belegen kann.

**Warum das kein Aufsatz ist, sondern ein Bauteil:** Sobald brainlehr in mehr
als einem Haus steht, ist die Verfassung eine Eigenschaft **des Hauses**, nicht
des Speichers. Ein Konzern will Hierarchie, eine Genossenschaft Konsent, eine
Buergerinitiative Bezugsgruppen. Wer die hierarchische Aufloesung fest einbaut,
verkauft allen dreien dasselbe Werkzeug und zwei Dritteln davon das falsche —
und merkt es nie, weil das Werkzeug nicht widerspricht.

**Reihenfolge:** nach B4.4. Vorher fehlt die Identitaet, an der ein Einwand
haengt — ein Veto von `unbekannt` ist kein Veto.

**Offen:** ob die Verfassung je Bestand, je Projekt oder je Aussage gilt.
Vermutlich je Projekt (`geltungsbereich.py` bekaeme eine zweite Aufgabe) —
ungeprueft, und ausdruecklich als Vermutung markiert.

---

## 5. Verworfene Wege

**Anmeldung im Gespraech („wer bist du?").** Abgelehnt aus den drei Gruenden in Kapitel 1.
Der Betreiber hat den Kern selbst benannt.

**Betriebssystem-Nutzer als Identitaet (`os.getuid()`).** Waere billiger und faelschungs-
sicherer als jedes Token — aber alle Zugaenge laufen heute unter demselben Konto, und ein
fremder Klient ueber HTTP hat gar keinen. Unterscheidet also genau nichts. Bleibt als
zusaetzliche Fessel moeglich.

**Rechte in die Datenbank.** Abgelehnt: wer die Datei oeffnen kann, kann die Rechtetabelle
aendern (`L-bd1562`). Rechte gehoeren dorthin, wo der Zugang entschieden wird, nicht dorthin,
wo er wirkt.

**Fertiges RBAC-Paket.** Abgelehnt: neue Abhaengigkeit fuer eine Praefix-Pruefung auf einer
Rechteliste. Die Zeichenkettenpruefung ist kuerzer als die Konfiguration dafuer waere.

**Zeilenweise Verschluesselung.** Abgelehnt: loest ein anderes Problem (Diebstahl der Datei)
und macht Suche und Vektoren kaputt. Trennung ist hier eine Sichtbarkeits-, keine
Geheimhaltungsfrage.

---

## 5b. Was diese Rechte NICHT leisten — Promptinjektion

Auf die Frage des Betreibers 2026-08-09T23:2x: „ist das was wir hier machen mit
der rechte vergabe und security gerade rakentenwissehnschaft oder standart ohne
probleme zu loesen? was ist mit promptinjektion?"

**Der Rechte-Teil ist Standard.** scrypt mit Salz, Datei mit `0600`,
zeitkonstanter Vergleich, Deny-by-default, Praefix-Pruefung auf einer
Rechteliste — Lehrbuchstoff, nichts davon selbst erfunden. Einzige Abweichung
vom BSI-Wortlaut: scrypt statt argon2/bcrypt, benannt im Modulkopf.

**Der Injektionsteil ist es nicht, und Rechte loesen ihn grundsaetzlich nicht.**

> Der Aufrufer ist ein Modell. Das Modell haelt den Ausweis. Wird sein Kontext
> per Injektion gesteuert, handelt es mit den vollen Rechten dieses Ausweises —
> und die Rechtepruefung sieht einen vollkommen legitimen, beglaubigten Aufruf.

Das ist das Confused-Deputy-Problem. Es ist durch keine Rechtematrix zu
schliessen. Was Rechte leisten, ist **Schadensbegrenzung, keine Abwehr**: ein
Ausweis mit `leser` kann auch unter Fremdsteuerung nichts ueberschreiben.

Der Bestand weiss das bereits. `einschleusung.py`, Korrektur des Betreibers vom
2026-08-06, per Messung bestaetigt:

> „eine Musterliste ist NIE die Verteidigung, egal wie viele Sprachen sie
> abdeckt — ein Angriff auf Altgriechisch oder base64-kodiert lief vor dieser
> Korrektur durch"

**Was daraus folgt und das Design aendert:**

**Der Ausweis, unter dem ein Modell handelt, muss weniger duerfen als der
Mensch** — nicht weil das Modell unzuverlaessig ist, sondern weil sein Kontext
angreifbar ist und der des Menschen nicht. `art=maschine` ist dafuer erst die
halbe Miete: es sperrt nur den Normrang.

Die andere Haelfte, aufzunehmen als **B4.7**: getrennte Ausweise fuer Recherche
und Schreiben. Ein Zug, der fremden Text liest (Web, PDF, fremde Knoten), laeuft
unter einem Ausweis, der gar keinen Schreibpfad hat. Damit ist der
Injektionsradius nicht durch Erkennung begrenzt, sondern durch Bauform — und
Bauform laesst sich nicht ueberreden.

*Was auch B4.7 nicht loest, ausdruecklich:* Ein Modell, das lesen darf, kann
Gelesenes weitertragen. Gegen Abfluss durch Erzaehlen hilft kein Schreibverbot.
Dagegen steht nur der Koeder (Kd-Nr. 990177) — er verhindert nichts, aber er
macht den Abfluss beweisbar und nennt den Kanal.

---

## 6. Was bewusst nicht getan wird

- **Kein Abweisen ausweisloser Schreiber** in dieser Runde (siehe B4.1) — Preis: der
  Bestand bleibt gemischt, unterscheidbar nur ueber das Praefix.
- **Keine Nachbeglaubigung der 3.998 Altzeilen.** Sie sind, was sie sind.
- **Kein Ablauf, keine Rotation, kein zweiter Faktor.** Ein Mensch, ein Rechner.
- **Keine Verschluesselung im Ruhezustand.**
- **Keine Oberflaeche zur Nutzerpflege.** Eine Datei und ein Unterbefehl reichen fuer einen
  Menschen; eine Maske dafuer waere Papier.

---

## 7. Woran sich Erfolg messen laesst

Jede Zeile ist eine Pruefung, die **vor** dem Bau fehlschlagen muss (rot vor gruen):

| Nr. | Probe | Vorher | Nachher |
|---|---|---|---|
| P1 | Aufruf mit `actor="betreiber"` **ohne** Ausweis | wird uebernommen | `unbeglaubigt:betreiber` |
| P2 | Aufruf mit `actor="betreiber"`, Ausweis lautet `hausmeister` | wird uebernommen | `hausmeister`, Argument stumm |
| P3 | gesperrtes Werkzeug ueber `tools/call` trotz fehlender Ankuendigung | laeuft durch | abgewiesen, `status='rejected'` mit Grund |
| P4 | Werkzeug **ohne** Rechte-Feld | laeuft durch | gesperrt (Vorgabe deny) |
| P5 | `:own` — fremder Eintrag | sichtbar | nicht sichtbar |
| P6 | `:published` — Eintrag `freigabe='intern'` fuer `readonly` | sichtbar | nicht sichtbar |
| P7 | Geheimnis irgendwo im Klartext (Repo, DB, Protokoll) | — | Suche liefert null Treffer |
| P8 | Koeder Kd-Nr. 990177 quert die Abteilungsgrenze | Ausgangsmarke | Befund |

**Negativfall, der am leichtesten vergessen wird** (aus ADR-001 uebernommen): ein gueltiger
Aufruf mit selbstbehauptetem `actor` im Rumpf darf diesen Wert NICHT uebernehmen. Das ist
P2 — und P2 ist der ganze Plan in einer Zeile.

**Grenzwerte:** leerer `actor`, `actor` gleich dem Ausweisnamen, `actor` mit dem Praefix
`unbeglaubigt:` bereits im Argument (Untergrabungsversuch).

---

## 8. Fortschreibung

Nach der Umsetzung: was anders kam als geplant, und warum. Die Entscheidung wandert als
ADR-002 nach `docs/adr/`.
