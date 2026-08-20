# Plan: Betriebsprofile, Enterprise-Achsen und drei Abruf-Lücken

Angelegt 2026-08-20T20:46:38+0200. Auftrag des Betreibers vom 2026-08-20, drei Punkte:
(1) die Lücken schließen, die der Wettbewerbsvergleich zeigte, (2) die am
2026-08-18 auf DEFERRED gestellten Enterprise-Achsen jetzt bauen, (3) vor der
Installation die Wahl Einzelplatz/Unternehmen lassen — **mit späterem Wechsel**.

## Die zentrale Einsicht: 3 ist der Schalter für 2, nicht ein Zusatz

Ohne Profilwahl müsste Mandantenfähigkeit immer vorhanden sein und würde den
Einzelplatz belasten. Mit ihr ist `local-first` der Auslieferungszustand und
`corporate` ein Profil, das etwas **zuschaltet**. Genau das steht bereits im
Katalog: `BDW-P05` nennt das Ziel „governierter Local-first-Memory-Kern",
`BDW-E17` hält fest, dass Betriebsprofile „später entschieden" werden.
Punkt 3 ist diese Entscheidung.

**Und daraus folgt die bindende Reihenfolge.** Der geforderte Wechsel
Einzelplatz → Unternehmen ist nur möglich, wenn die Mandanten-Achse von
Anfang an im Schema liegt — unbenutzt, aber da. Sie nachträglich einzuziehen
hieße, 5.239 Bestandseinträgen rückwirkend einen Mandanten zuzuschreiben, den
sie nie hatten. Das ist keine Frage des Füllstands: Es gilt bei null
Einträgen genauso wie bei einer Million, weil sich nicht rekonstruieren
lässt, wem ein Altbestand gehörte.

## Gemessener Ist-Stand (2026-08-20)

| | |
|---|---|
| Bestand | 5.239 Knoten, 1.171 Lehren, 35 Tabellen, 63 Trigger |
| Katalog | 56 BDW-Zeilen, davon 16 Sprints offen |
| Enterprise-Achsen | E01, E03, E04, E05, E06, E11, E17, E19 auf DEFERRED |
| Produktgates | 24 von 24 sind **Baulücken, nicht Testlücken** (Stichprobe 2026-08-18) |

**Korrektur an der Lückenliste**, gemessen statt übernommen: Von den sechs
Punkten aus dem Wettbewerbsvergleich sind nur **drei** echte Lücken
(0 Treffer im Quelltext). Zwei existieren bereits, einer ist gegenstandslos:

| Punkt | Befund |
|---|---|
| Widerspruchserkennung | **fehlt** — 0 Treffer auf `widerspruch\|contradict\|konflikt` |
| Rückzug bei Leerlauf | **fehlt** — 0 Treffer auf `backoff\|leerlauf` |
| Sicherung gegen tote Dienste | **fehlt** — 0 Treffer auf `circuit\|breaker\|aussetzer` |
| Vertrauen, das sich bewegt | **existiert** als `knowledge_trust_score`, fünf Nutzungsgrößen. Beim Bau wurde ausdrücklich Hermes' `store.py` verglichen (2026-08-07). Bewusst anders: berechnet statt selbst gemeldet |
| Kein Datenverlust bei Sitzungswechsel | `session_checkpoint_*` vorhanden — **zu prüfen**, ob es beim Wechsel flusht |
| Absturzfeste Schreibschlange | **gegenstandslos** — brainlehr schreibt synchron in SQLite, es gibt keine Warteschlange, die ein Absturz verlieren könnte |

## Reihenfolge, und wo sie bindend ist

**B1 — Profilbegriff und Mandanten-Achse im Schema** (bindend zuerst)
Eine Spalte `mandant` auf allen Bestandstabellen, Vorgabewert `einzelplatz`.
Ein Profilschalter, der heute nur zwei Werte kennt. Kein Rollenmodell, keine
Rechte — nur die Achse. Danach ist der spätere Wechsel eine Datenänderung
statt eines Umbaus.

**B1b — Sprachachse, im selben Zug** (nicht bindend, aber hier billig)
Eine Spalte `sprache` neben `mandant`. Anlass ist die Betreiberfrage vom
2026-08-20: „wenn wir Apps fürs Handy bauen, haben wir aber Mehrsprachigkeit?"

**Der Abruf braucht sie NICHT** — gemessen am 2026-08-20: eine deutsche Frage
trifft den gleichbedeutenden englischen Text mit Kosinus 0,819, weit über der
Schwelle 0,65. Genau deshalb antworten die 1.637 englischen NASA-Einträge
heute auf deutsche Fragen, ohne dass jemand sie übersetzt hat.

**Die ANZEIGE braucht sie**, und zwar als WCAG-Auflage, nicht als Komfort:
`3.1.1 Language of Page` / `3.1.2 Language of Parts`. Ein Vorleseprogramm
liest englischen Text mit deutscher Aussprache vor, wenn die Sprache nicht
ausgezeichnet ist — das macht den Inhalt unverständlich. Heute liefert
`knowledge_search` einen NASA-Eintrag aus, ohne dass eine App wüsste, dass er
englisch ist; sie könnte ihn also gar nicht regelkonform darstellen.

**Es braucht genau EIN Feld, kein Übersetzungssystem.** Kein `titel_en`, keine
parallelen Fassungen, keine Pflege: Ein Eintrag hat die Sprache, in der er
geschrieben wurde. Übersetzung ist ein Problem der Ausgabe, nicht des
Speichers — die App entscheidet zur Laufzeit.

**Der Unterschied zur Mandanten-Achse, und er ist der Grund, warum B1b nicht
bindend ist:** Einen Mandanten kann man einem Altbestand nicht rückwirkend
zuschreiben. Eine Sprache steht im Text. Gemessen mit einer Heuristik aus
36 Stoppwörtern, ohne neue Abhängigkeit: 758 von 770 richtig, 9 unklar
(/nasa-llis 200/200, /germanquad 198/200, /brainlehr 197/200, /methodik
163/170). Sie ließe sich also jederzeit nachziehen.

Sie fährt trotzdem hier mit, weil sie in diesem Zug fast nichts kostet: Wer
ohnehin eine Spalte hinzufügt und alle Zeilen einmal anfasst, nimmt die
zweite gratis mit. Ein eigener Durchlauf über 5.239 Zeilen später kostet
mehr als die Spalte jetzt.

**Offen und ausdrücklich nicht entschieden:** Französisch liegt bei 0,630 und
fällt damit unter die Schwelle 0,65 — dieselbe Sache, andere Sprache, Treffer
verworfen. Die Schwelle ist an deutschem Material kalibriert und
sprachübergreifend nicht gleich streng. Heute folgenlos (es gibt kein
französisches Material), vor einer Öffnung nach außen zu messen.

**B2 — Der Wechsel selbst**, als Werkzeug mit Rot-Probe: Bestand wandert
geschlossen auf einen benannten Mandanten. Ein Rückweg gehört dazu.

**B3 — Enterprise-Achsen** (E01, E03, E04, E05, E06, E11, E19), erst danach.
Sie setzen die Achse aus B1 voraus; jede vorher gebaute Rechteprüfung hätte
nichts, worauf sie prüfen könnte.

**A1–A3 — die drei Abruf-Lücken.** Hängen an keinem der beiden und können
sofort und parallel laufen:
* **Widerspruchserkennung.** holographic vergleicht Jaccard-Überlappung gegen
  Inhaltsähnlichkeit (`retrieval.py:355-430`, Schwelle 0,3, O(n²) mit Deckel
  bei 500). brainlehr hat echte Einbettungen und kann es feiner — hohe
  Entity-Nähe bei niedriger Bedeutungsnähe. Direkt einschlägig für
  Normkonflikte, die heute nur auffallen, wenn ein Mensch stolpert.
* **Rückzug bei Leerlauf.** Der Recall lieferte 37,8 % leer und fragte
  unbeirrt weiter. honcho verbreitert das Intervall je leerem Treffer, Deckel
  bei 8 (`__init__.py:1015-1021`).
* **Sicherung gegen tote Dienste.** mem0 pausiert nach 5 Fehlern für 120 s
  (`__init__.py:294-335`). Bei uns heute zweimal gebraucht: Ollama war weg,
  und niemand merkte es.

## Verworfene Wege

* **Mandanten-Achse erst beim ersten Piloten** — der vom Betreiber geforderte
  Wechselweg wäre dann ein Umbau mit rückwirkender Zuschreibung. Verworfen
  aus Reihenfolge, nicht aus Menge.
* **Zwei getrennte Auslieferungen** (Einzelplatz-Zweig, Unternehmens-Zweig) —
  zwei Stände, die auseinanderlaufen, und der Wechsel wäre ein Umzug statt
  eines Schalters. `BDW-E17` sieht Profile ausdrücklich als Zuschaltung.
* **Vertrauens-Rückmeldung nach holographic-Vorbild nachbauen** — wir haben
  das Objektivere (Aufgriffsquote misst tatsächliche Nutzung, nicht die
  Selbstauskunft eines Modells). Verworfen als Rückschritt.

## Was bewusst NICHT getan wird

* **Kein IdP-Anschluss ohne echten Piloten.** `BDW-E04` bindet SSO an den
  ersten Mehrbenutzer-Piloten. Ein gegen einen erfundenen IdP gebauter
  Anschluss prüft den Prüfstand, nicht die Sache.
* **Keine Datenregionen (E19)** ohne zweiten Standort — es gäbe nichts zu
  begrenzen. Preis: Die Zeile bleibt offen.
* **Kein neues Bewertungssignal.** `docs/PLAN_ZWEITES_SIGNAL_2026-08-20.md`
  hält fest, warum zuerst die Wirkung des Abrufs gemessen wird.

## Woran sich Erfolg misst

| Schritt | Nachweis |
|---|---|
| B1 | Frischer Bestand und gewachsener Bestand tragen dieselbe Achse. Beide Ausgangszustände fahren, nicht nur der leere |
| B2 | Wechsel und Rückweg je einmal, mit Bestandszählung davor/danach |
| B3 | Je Achse ein **Negativtest**: der fremde Mandant sieht nichts. Ein Positivtest allein belegt keine Trennung |
| A1 | Mindestens ein Widerspruch, den heute niemand kennt — und eine gezählte Fehlalarmquote gegen den ECHTEN Bestand, nicht gegen gestellte Fälle |
| A2 | Leer-Anteil vor/nach, gegen dieselbe Nulllinie (37,8 %) |
| A3 | Nachstellprobe mit abgeschaltetem Dienst, wie bei `melder/modellwege.py` |

## Offene Entscheidung für den Betreiber

Die Profilnamen. Vorschlag: `einzelplatz` und `unternehmen` — deutsch wie
der übrige Bestand, und `corporate` wäre das einzige englische Wort in einem
Schema, dessen Felder `freigabe`, `geltung` und `herkunft` heißen.
