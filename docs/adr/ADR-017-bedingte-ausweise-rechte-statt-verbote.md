# ADR-017: Bedingte Ausweise — Rechte statt Verbote, und die Projektion wird gereicht

**Stand** 2026-08-14T21:36:26+0200
**Status** Angenommen, Bauform in Teilen offen
**Betrifft** `kern/ausweis.py`, jede Domäne, die Tabellenkalkulation (ADR-016), verteilte Werkzeuge (ADR-012)
**Entscheider** Betreiber, 2026-08-14

## Der Einwand, der die Sache dreht

> *„wir haben eine Datenbank! … wir können Zertifikate auch an Bedingungen
> knüpfen: X darf nur Y ausführen, sehen, nur Code aus dessen
> Regelwerk-Projektion ausführen. wir sind ja nicht nur Excel, wir sind auch
> ‚Windows'!"*

**Er trifft, und der Grund ist strukturell:** Office-Makrosignaturen scheiterten,
weil Office **kein Betriebssystem** war. Eine Anwendung in fremder Umgebung hat
nur die Signatur — die Rechte gehören ihr nicht, und der Widerruf eines
gestohlenen Zertifikats lief über Sperrlisten, die niemand rechtzeitig las.

Nach ADR-014 sind wir an dieser Stelle das Betriebssystem: **Sicherheit ist
unabtretbar und liegt im Kern.** Damit können wir das, was Office nicht konnte —
die Bedingung an die Identität hängen statt an die Datei.

## Die Entscheidung

**Das pauschale Makroverbot aus ADR-016 entfällt.** An seine Stelle tritt:

> Eine Rechenvorschrift läuft, wenn ihre **Herkunft belegt** ist und sie nur
> das erreicht, was ihr **eingeräumt** wurde. Nicht verboten, sondern eingehegt.

**Das ist keine Neukonstruktion.** Gemessen in `kern/ausweis.py`: Es gibt
`ROLLEN` als festen Satz, ein **`mandat`** mit den Feldern `von`, `rollen` und
**`gegenstand`** — also bereits „wer darf was, woran" — und einen engen Zugang,
bei dem laut Quelltext *„Volltext gesperrt bleibt"*. Die Bedingung an den
Ausweis zu hängen ist eine Erweiterung, kein Neubau.

## Der eigentliche Gewinn: Widerruf

Bei Office war ein gestohlenes Zertifikat praktisch ein Generalschlüssel — die
Rücknahme hing an Sperrlisten, die offline oder zu spät geprüft wurden. **Bei
uns ist der Widerruf eine Zeile in der eigenen Datenbank und sofort wirksam.**
Das ist der Unterschied zwischen einem Vertrauensanker und einer laufenden
Erlaubnis.

*Nicht gemessen und damit offen:* ob der Widerruf für Ausweise heute
implementiert ist. Für Wissen existiert er (`knowledge_zurueckziehen`); für
Ausweise wurde er in dieser Sitzung nicht nachgewiesen. Vor dem ersten
eingeräumten Recht zu prüfen — ein Recht ohne Rücknahme ist eine Schenkung.

## Die Bauform, ohne die das Ganze ein Merkmal bleibt

**Der eigene Fehler dieses Systems, aus dem die Auflage stammt** (`L-33d3bd`):
Ein Feld `art=mensch|maschine` sollte verhindern, dass ein Modell als
menschlicher Entscheider gilt. Es war wirkungslos, weil **derselbe Prozess es
setzen konnte, den es einschränken sollte.** Eine Prüfung, die im selben Raum
läuft wie das Geprüfte, ist ein **Merkmal**, keine Sperre.

Übertragen auf die Rechenvorschrift heißt das — und es ist genau der Satz des
Betreibers, zu Ende gebaut:

> **Die Projektion wird VOR der Ausführung gebildet und gereicht. Die
> Rechenvorschrift zieht nichts selbst.**

Der Unterschied ist der ganze Punkt:

| | |
|---|---|
| „sie **darf** nur X sehen" | Prüfung bei jedem Zugriff, im selben Raum, umgehbar |
| „sie **sieht** nur X" | sie hat zu mehr keinen Zugang, es gibt nichts zu umgehen |

Also: keine Datenbankverbindung in der Auswertung, kein Dateisystem, kein Netz.
Was sie braucht, liegt vorher auf dem Tisch — abgeleitet aus dem, was ihre
Domäne ohnehin sehen darf.

## Was daraus zusammenwächst

Drei bisher getrennte Bedürfnisse werden **ein** Baustein:

1. **ADR-012** verlangt für ein verteiltes Werkzeug eine geprüfte Herkunft.
2. **ADR-016** braucht sie für Rechenvorschriften aus fremder Hand.
3. **ADR-013** braucht sie für das Domänenpaket selbst.

Einmal gebaut, dreimal benutzt. Und alle drei bekommen dieselbe Rücknahme.

## Offen, ausdrücklich nicht entschieden

- Welche **Wirkungen** überhaupt einräumbar sind (die Positivliste selbst).
- Ob die Auswertung in einem eigenen Prozess läuft oder eine Sprachebene
  genügt, die nichts anderes erreichen kann.
- Der Widerruf für Ausweise, siehe oben.
