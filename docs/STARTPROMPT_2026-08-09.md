# Startprompt nach dem Neustart — 2026-08-09T12:00:00+0200

Zum Kopieren in die erste Nachricht der neuen Sitzung. Bewusst OHNE meine
eigene Vermutung, woran der Rueckstand liegt — der Auftrag laesst messen,
nicht bestaetigen (Hausregel). Was drinsteht, sind Messwerte.

---

```
brainlehr, Fortsetzung. Lies zuerst STAND.md, dann arbeite.

FAKTEN (gemessen 2026-08-09, alle im Repo belegt)

- Abrufguete: 7 von 35 Zielen getroffen (Lehren 4/15, Knoten 3/20).
- Von den 28 verfehlten stehen 26 ueberhaupt nicht in der Kandidatenliste.
  Sie werden nicht abgeschnitten, sie werden nicht gefunden. Belegt durch
  runs/deckelreihe_2026-08-09.json: die Deckel 3/2, 5/3, 7/5 und 10/7
  liefern ALLE 7/35, bei 4769 bis 16476 Zeichen je Prompt. Erst 15/10
  bringt 9/35 bei 23788 Zeichen.
- Der Pruefkorpus paraphrasiert absichtlich: nur 6 von 28 Fehlschlaegen
  teilen ueberhaupt einen Wortstamm mit dem Ziel.
- S12 (haken/mehrstufiger_abruf.py) ist gebaut und steht auf AUS: Stufe 1
  aenderte nichts, Stufe 2 senkte auf 6/35.
- Die Sortierung in knowledge_recall_hook.query() wurde als Ursache
  genannt, testweise entfernt und gemessen: unveraendert 7/35. Die
  Aenderung ist zurueckgenommen, die Diagnose gilt fuer den Code, nicht
  fuer die Wirkung.

AUFGABE

Finde heraus, warum diese 26 Faelle nicht in die Kandidatenliste kommen.
Miss es, stelle keine These auf und pruefe sie. Der Weg dorthin ist deine
Entscheidung; naheliegende Messpunkte sind der Stichwortkanal, der
Bedeutungskanal, die RRF-Verschmelzung und die Vorfilter — welcher davon
die Faelle verliert, ist offen und soll gemessen werden, nicht geraten.

GRENZEN

- Deckel bleiben bei MAX_NODES=3 / MAX_LESSONS=2. Fuenffache Liefermenge
  fuer +2 von 35 ist eine Rechnung, kein Fortschritt.
- knowledge_recall_hook.py ist ein Monolith mit ueber 2000 Zeilen. Nur
  Importe, Aufrufe und Schalter darin aendern, keine Logik umbauen.
- Nichts einschalten, was nicht gemessen besser ist. Ein gebauter Schalter
  ist kein Grund, ihn anzuschalten.
- Fremde Arbeitsstaende nicht mitcommitten: haken/existenzpruefung.py und
  tests/test_existenzpruefung.py gehoeren einer anderen Sitzung.

ABNAHME

- Rot vor gruen: eine Pruefung, die VOR der Aenderung fehlschlaegt und
  danach besteht. Laesst sich kein solcher Beleg herstellen, sag das
  ausdruecklich statt "funktioniert".
- Jede Zahl mit ihrem Nenner.
- Gegenprobe in beide Richtungen und ein Negativfall.
- Bei jedem Melder/Pruefstein: Fehlklasse benennen und den Preis eines
  Fehlalarms.

EINSATZ

Solange vier von fuenf Faellen den Speicher nicht erreichen, ist jede
Disziplin darin Zierrat — sie wirkt nur an dem, was ankommt.

OFFEN, ich entscheide das, frag mich beilaeufig und nicht als Blocker:
Papernetz-Umfang (9 Netze mit 297 Papern und 1624 belegten Zitationskanten,
oder nur die zwei mit 56), die sechs Knoten Rang 4/6, und die abgelaufene
Norm /ops/buckeberg-anbieterabend-2026-08-05.
```

---

## Was beim Neustart passieren soll, in dieser Reihenfolge

1. **Sitzung beenden.** Damit stirbt `knowledge_mcp_server.py` (PID 61742),
   der als einziger Schreibhandles auf `brainlehr.db` hielt. Kein `kill`
   noetig.
2. **Neu starten.** Der frische Serverprozess liest dann erstmals
   `BEGOD_KNOWLEDGE_ACTOR=claude-code` aus `hub/.mcp.json` — und die drei
   `annahme_*`-Werkzeuge sind zum ersten Mal aufrufbar.
3. **Erste Probe, bevor irgendetwas gebaut wird:** einen Knoten anlegen und
   nachsehen, ob `actor` jetzt `claude-code` traegt statt `unbekannt`. Das
   ist die Rot-vor-gruen-Probe fuer die Konfigurationsaenderung — vorher
   94 % blind, gemessen.
4. **`pruefer.py --melder` wird weiter `model` melden.** Das ist gewollt und
   kein Restfehler (Begruendung in STAND.md). Wer es durch einen festen
   env-Wert zum Schweigen bringt, hat es uebertoent, nicht behoben.

## Was nicht vergessen werden darf

Der Prozess unter `hermes-agent` (PID 5173) haengt seit ueber einem Tag an
der DB und ueberlebt den Neustart. Nur lesend, aber beobachten.
