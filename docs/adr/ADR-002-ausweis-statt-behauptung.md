# ADR-002: Identitaet wird gemessen, nicht erfragt — und Rechte wirken am Aufruf

**Status:** Akzeptiert
**Datum:** 2026-08-10T05:54:13+0200
**Entscheider:** Betreiber ("lass es uns bauen!", 2026-08-09; Vorgaben zur
Ablage, zur Art des Traegers und zur Vorziehung von Mandat/Rotation im Verlauf)
**Betroffen:** `ausweis.py` (neu), `werkzeugrechte.py` (neu),
`knowledge_mcp_server.py` (`_identity`, `tools/call`), `schema.sql`
**Plan:** `docs/PLAN_B4_AUSWEIS_2026-08-09.md`

---

## Ausgangslage, gemessen

`_identity()` loeste `actor` so auf:

```python
actor or os.environ.get("BEGOD_KNOWLEDGE_ACTOR") or UNBEKANNTER_SCHREIBER
```

Das Argument stand vor der Umgebung: wer `actor="betreiber"` mitschickte, WAR
Betreiber. Kein `if`, kein Abweisen. Bauartgleich mit `L-8487fb`.

Und `BEGOD_KNOWLEDGE_PROFIL` beschraenkte nur die Ankuendigung. Der Quelltext
sagte es ueber sich selbst: „tools/call bedient jedes Werkzeug in TOOLS weiter,
egal ob es hier gelistet wurde. **Kein Autorisierungsmechanismus.**"

Fuellstand `access_log.actor` (3.998 Zeilen): `unbekannt` 1.546, leer 1.310,
`claude-code` 771, Rest 371.

---

## Entscheidung

**1. Es wird nicht gefragt, wer jemand ist.** Eine Anmeldung im Gespraech waere
falsch: das Geheimnis stuende im Verlauf, im Transkript, in jedem Kontextfenster
und in jeder Verdichtung — und wer im Gespraech antwortet, *behauptet* seine
Identitaet, also genau der alte Zustand mit mehr Zeremonie. Die Identitaet kommt
aus dem Prozessstart, wo das Modell nicht hinreicht. **Es erfaehrt seinen Namen,
nie sein Geheimnis.**

**2. Ohne Ausweis wird nichts abgewiesen, sondern markiert.** `unbeglaubigt:`
als Praefix. 3.998 Protokollzeilen, lokale Skripte und der ChatGPT-Zugang
schreiben ohne Ausweis; ein hartes Abweisen waere ein Bruch ohne Gegenwert. Die
Unterscheidung geprueft/behauptet bleibt dauerhaft im Protokoll auswertbar.

**3. Jeder Ausweis traegt eine Art, Vorgabe `maschine`.** Wer sein Geheimnis in
eine Klientenkonfiguration legt, gibt es einer Maschine. Nur `art=mensch` gilt
als menschlicher Entscheider; ein unbeglaubigter Ausweis ist nie ein Mensch.

**4. Mandate sind imperativ.** Gegenstand ist Pflichtfeld, der Rechteschnitt
wird zur Laufzeit gebildet, ein Mandat hebt die Art nie an, keine
Weiterdelegation, nicht-delegierbare Rechte werden beim Anlegen abgewiesen.

**5. Die Durchsetzung sitzt an `tools/call`**, an genau einem Punkt, mit
Deny-Vorgabe fuer unzugeordnete Werkzeuge.

**6. Der Bezug (`:own`/`:published`) wirkt auf das Ergebnis**, ebenfalls an
einem Punkt. Was kein Freigabemerkmal tragen kann, ist nicht freigegeben.

---

## Die Bedingung, ohne die diese Entscheidung falsch waere

> **`weich` ist kein Schutz.**

Die Vorgabe laesst unbeglaubigte Aufrufer weiterhin alles tun. Der Gewinn ist,
dass ein Ausweis *wirkt* und dass der Schalter existiert. Der Schutz entsteht
erst mit `BRAINLEHR_DURCHSETZUNG=streng` — und dieser Schritt gehoert dem
Betreiber, weil er den Betrieb betrifft. Wer diese ADR liest und daraus
„brainlehr hat Zugriffsschutz" macht, hat sie falsch gelesen.

---

## Verworfene Wege

**Anmeldung im Gespraech.** Siehe Entscheidung 1.

**Betriebssystem-Nutzer als Identitaet.** Faelschungssicherer, aber alle Zugaenge
laufen unter demselben Konto — unterscheidet nichts.

**Rechte in der Datenbank.** Wer die Datei oeffnen kann, aendert die
Rechtetabelle (`L-bd1562`). Rechte gehoeren dorthin, wo der Zugang entschieden
wird.

**argon2/bcrypt.** Nicht installiert. `hashlib.scrypt` ist Standardbibliothek,
memory-hard und in BSI TR-02102-1 zugelassen — Abweichung vom BSI-Wortlaut
benannt statt stillschweigend. *(Der Verweis auf TR-02102-1 stammt aus
Modellwissen und ist nicht an der Primaerquelle geprueft; `normbezug.py` meldet
ihn genau deshalb.)*

**Mandat spaeter.** Vom Betreiber verworfen, zu Recht: nachtraeglich eingezogen
haette jede Rechtepruefung im Bestand die Annahme „ein Aufrufer, eine Identitaet"
mitgetragen.

---

## Folgen

**Gewonnen:** Ein Aufrufer kann seine Identitaet nicht mehr behaupten · ein
Modell kann sich nicht per Konfigurationszeile zum Menschen machen · ein Leser
kann nicht schreiben · ein Gast sieht nur Freigegebenes · jede Abweisung steht
mit Grund im Protokoll.

**Bezahlt:** Eine Datei mehr, die verwaltet werden will · scrypt kostet je
Pruefung rund 16 MiB (gecacht je Geheimnis und Dateistand) · 3.998 Altzeilen
tragen keine Beglaubigung und duerfen nie so gelesen werden · sechs
Bestandstests erwarteten den nackten Namen und wurden nachgezogen.

**Abbruchbedingung, an der diese Entscheidung als falsch erkennbar waere:** Wenn
Ausweise in der Praxis nicht angelegt werden und `unbeglaubigt:` der Regelfall
bleibt, ist der Apparat Zeremonie. Zaehlbar in `access_log`: Anteil der Zeilen
mit Praefix, gemessen in vier Wochen.

---

## Nachweis

Rot vor gruen, je Schritt gemessen:

| Schritt | vorher rot | nachher |
|---|---|---|
| B4.1 Identitaet | 4 von 7 | 7/7 |
| B4.3 Durchsetzung | 4 von 7 | 7/7 |
| B4.4 Bezug | 2 von 5 | 5/5 |
| B4.5 Koederlauf | Leck gefunden | 0/10 gegen 10/10 |
| Freigabe an Lehren | 1 von 7 | 7/7 |

Dazu eine **Mutationsprobe** ueber `ausweis.py` mit sechs gezielten Fehlern:
fuenf sofort rot, einer blieb gruen (die Kettenschranke gegen Weiterdelegation
war ungeprueft, weil die Probe ein *geliehenes* Recht weitergab — erst am
eigenen Recht des Delegierten wird sie beobachtbar). Danach 6 von 6.

Volle Suite: 757 gruen bei unveraendert 8 roten und 6 Fehlern (Vorzustand).

**Was der Bau an sich selbst gefunden hat** — und was den Wert der Proben
belegt: der Cache uebersah `chmod` (mtime aendert sich dabei nicht) ·
`unbeglaubigt:unbekannt` haette eine bestehende Konstante verschoben · der
Koederlauf fand, dass Lehren durch den `published`-Filter fielen · der
Herkunftstrigger erzwang die Regel, dass ein ohne Ausweis geschriebener Knoten
niemandem gehoert.
