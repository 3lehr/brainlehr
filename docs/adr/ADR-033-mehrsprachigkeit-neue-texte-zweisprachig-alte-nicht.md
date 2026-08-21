# ADR-033 — Mehrsprachigkeit: neue Texte zweisprachig, alte bleiben liegen

Angelegt 2026-08-21T13:45:00+0200.
Status: **entschieden** (Assistent, unter der Betreiberfreigabe zur
selbstständigen Reihenfolge; Widerspruch jederzeit möglich).

## Anlass

`BDW-P19`, Betreiberwort 2026-08-21: *„wenn wir einen englischsprachigen user
haben, sollten diese dinge auch auf englisch angezeigt werden"*. Offen war
die **Bauform** — Katalogdatei, Gettext, oder englische Quelle mit deutscher
Schicht.

## Gemessener Ist-Stand

`runs/sprachstand_oberflaeche_2026-08-21.json`, Erhebung über `haken/`,
`melder/`, `knowledge_mcp_server.py`, `schema.sql`, `berichte/`:

| | |
|---|---|
| nutzersichtbare Textstellen | **707**, davon **690** erreichen wirklich jemanden |
| Zeichenmenge | **60 543** |
| größter Einzelposten | **113 MCP-Werkzeugbeschreibungen, 21 402 Zeichen** |
| davon bereits englisch | **48 zu 11** — die Schnittstelle ist schon englisch |
| Übersetzungsschicht im Repo | **keine**, Nullbefund über zwei Suchwege |
| Textstellen ohne Auslöser | 17 (1 645 Zeichen) — erreichen niemanden |

## Entscheidung

**Es wird jetzt keine Übersetzungsschicht gebaut.** Stattdessen zwei Regeln:

1. **Jeder NEU geschriebene nutzersichtbare Text entsteht zweisprachig.**
   Das betrifft zuerst die Erklärungen des Hermes-Plugins (`description`,
   `info`, `placeholder`, Optionsbeschreibungen). Sie existieren noch nicht —
   zweisprachig kostet dort fast nichts.
2. **Der Altbestand bleibt deutsch, bis ein englischsprachiger Nutzer
   existiert.**

## Warum — der Maßstab dieses Tages, angewandt

Jede Entscheidung dieses Tages folgte einer Frage: **Was lässt sich später
nicht mehr nachholen?** Bei `mandant`, `kreis`, Gegenstand und Fälligkeit
lautete die Antwort „die Zuordnung zum Altbestand" — deshalb wurden sie
zuerst gebaut.

**Bei Übersetzungen lautet die Antwort: nichts.** Ein deutscher Satz von
heute lässt sich in einem Jahr genauso übersetzen wie jetzt. Er altert nicht,
er verliert keine Zuordnung, und niemandem fehlt rückwirkend etwas. Die
60 543 Zeichen kosten später exakt dasselbe wie heute.

**Damit fällt der einzige Grund weg, es vorzuziehen.** Was bliebe, wäre ein
Aufwandsargument — und Aufwand ist als Kriterium ausdrücklich gestrichen
(`L-dafc34`, Regelrang). Die ehrliche Begründung ist deshalb nicht „zu
teuer", sondern: **es gibt heute keinen englischsprachigen Nutzer**, und ein
Mechanismus ohne Benutzer ist Vorbau.

## Was trotzdem jetzt entschieden ist, weil es sonst teuer wird

**Die fünf Fälle, die sich nicht folgenlos übersetzen lassen**, sind benannt
und bleiben benannt — wer später übersetzt, muss sie kennen:

* **33 `RAISE`-Texte in `schema.sql`.** Eine geänderte Datei erreicht eine
  gewachsene Datenbank nicht von selbst (`L-55075a`).
* **Vier Wächter, die auf ihr EIGENES deutsches Vokabular prüfen** —
  `melder/nulllinie.py` auf „Nulllinie/Positivkontrolle/Gegenprobe",
  `melder/korrekturlehre.py` auf wörtliche Tadel des Betreibers,
  `melder/vermutungswaechter.py` auf eine eigene Sprachheuristik,
  `melder/rueckfrageschleife.py` auf Formulierungsmuster. Übersetzt man die
  geprüften Texte, werden diese Wächter **blind** (`L-8fce9c`).

**Daraus folgt die Bauform für den Tag, an dem übersetzt wird**, und sie ist
festgelegt, damit sie nicht neu erfunden wird: **Die Quelle bleibt deutsch,
übersetzt wird bei der AUSGABE.** Ein Nachschlagewerk, dessen Schlüssel der
deutsche Satz selbst ist — keine erfundenen Schlüssel, kein Umschreiben von
707 Stellen, und die Wächter sehen weiter den deutschen Quelltext, den sie
prüfen. Fehlt eine Übersetzung, kommt das Original zurück.

## Verworfen

* **Gettext** — bringt eine Abhängigkeit für ein Problem, das heute niemand
  hat.
* **Englisch als Quelle, Deutsch als Schicht** — würde die vier Wächter sofort
  blind machen und das Haus zwingen, seinen eigenen Quelltext auf Englisch zu
  lesen, ohne dass ein Nutzer davon profitiert.
* **Alles jetzt übersetzen** — 60 543 Zeichen für null Leser.

## Abnahme

1. Ein neu geschriebener Plugin-Text liegt in beiden Sprachen vor. Negativ:
   ein einsprachig neu geschriebener Text ist ein Regelbruch, kein Rückstand.
2. Am Tag der Umstellung: Die vier Wächter bleiben nach der Übersetzung
   scharf — nachgewiesen an je einem Fall, der sie auslösen MUSS.
3. Der Altbestand bleibt unangetastet, solange kein englischsprachiger Nutzer
   existiert. Erscheint einer, ist das der Auslöser, nicht ein Datum.
