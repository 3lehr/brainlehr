# Wissenskorpus-Kandidaten -- Bericht

Erstellt: 2026-08-15T19:23:38+0200. Rohdaten: `runs/wissenskorpus_kandidaten_2026-08-15.json`.

## Ausgangslage (geprueft, nicht vermutet)

- `kern/pruefkorpus.py` (gelesen): baut 45 Faelle aus dem EIGENEN Bestand, je mit
  bekannter Zielkennung (lesson/fact/norm) oder als Eichfall ohne Ziel
  (Kategorie `negative`, 12 themenfremde Fragen). Der Mechanismus fuer die
  Trennung "Antwort im Bestand bekannt" vs. "bekanntlich nicht" existiert
  also bereits -- er wird nur nicht bis zur Trefferquote weitergerechnet
  (siehe unten).
- `/nasa-llis` (1637 Eintraege, gemessen ueber `quellen/fremdquellen.json`):
  englisch, Luft-/Raumfahrt-Sicherheit, Lizenz US-Bundeswerk (17 U.S.C.
  §105), ausdruecklich als "nicht an der Primaerquelle geprueft" markiert.
  9 von 10 Eintraegen im vorhandenen Quellenregister sind englisch/fachfremd
  -- die Luecke aus dem Auftrag (deutsch, Q&A-Struktur) ist im eigenen
  Register sichtbar, bevor irgendetwas Neues gesucht wurde.

## Kandidaten (5, alle an der Quelle lizenzgeprueft)

| Name | Lizenz | Sprache | Umfang | Kriterium 1 |
|---|---|---|---|---|
| GermanQuAD (deepset) | CC BY 4.0 | de | 11.518+2.204 Fragen mit Antwort+Position | JA, stark |
| GermanDPR (deepset) | CC BY 4.0 | de | 9.275+1.025 Frage-Antwort-Paare + Hard-Negatives | JA, stark |
| Gesetze im Internet (BMJ) | Amtliches Werk, §5 UrhG | de | gesamtes Bundesrecht, XML | teilweise (Kennung = §) |
| Open Legal Data -- Gerichtsentscheidungen | §5 UrhG (Text) + ODbL (Sammlung) | de | 100k-1M Entscheidungen | teilweise (Kennung = Aktenzeichen/ECLI) |
| Wikipedia Deutsch (dewiki) | CC BY-SA 4.0 / GFDL | de | ~2,9 Mio Artikel | schwach als eigenstaendiger Kandidat |

Details, Fundstellen der Lizenzangabe und Einbettungskosten-Grobschaetzung:
siehe JSON, Feld `kandidaten`.

**Empfehlung, wenn eine Prioritaet gewuenscht ist:** GermanDPR zuerst --
einzige Quelle mit Frage + Antwort + Hard-Negatives in einem Aufwasch, exakt
das Material fuer die im Verfahren unten beschriebene Trennung.

## Verworfen

**Robert Koch-Institut (RKI):** eigene Lizenzangabe gepruewft
(rki.de/DE/Service/Impressum), sie verbietet woertlich "Bearbeitung,
Umgestaltung oder Manipulation der Inhalte" ohne vorherige schriftliche
Genehmigung. Kein Fall von "keine Angabe gefunden" (dann waere es raus nach
der GENERELLEN Regel), sondern von "Angabe gefunden und sie verbietet
genau das Vorhaben" -- der haertere und eindeutigere Ablehnungsgrund.

## Sonderfall Lizenzbeleg: Gesetze im Internet / Open Legal Data

Bei diesen beiden liegt KEINE explizite Lizenzangabe auf der Webseite selbst
(gepruewft: impressum.html, hinweise.html -- nur ein Deep-Link-Erlaubnis-
Hinweis). Die Gemeinfreiheit folgt hier aus §5 Abs. 1 UrhG (Gesetze,
Verordnungen, amtliche Entscheidungen/Leitsaetze sind vom Urheberrechtsschutz
ausgenommen) -- das ist ein GESETZLICHER Beleg, kein Website-Vermerk, und
wird deshalb im JSON ausdruecklich als andere Beleg-Art gekennzeichnet statt
stillschweigend gleich behandelt. Bei Open Legal Data zitiert die
Datensatzbeschreibung selbst §5 UrhG woertlich -- dort liegt zusaetzlich ein
Quellenbeleg vor.

## Verfahren: Suche schlecht vs. Bestand leer

Kern: eine Trefferquote ist nur interpretierbar, wenn zu jeder Testfrage VOR
der Messung ein Label "Antwort im Bestand: ja/nein" feststeht.

1. Testkorpus mit Label pro Frage bauen -- Label VORHER festlegen, nie aus
   dem Suchergebnis ableiten (sonst zirkulaer).
2. Positivfaelle: Frage aus nachweislich vorhandenem Eintrag (wie
   pruefkorpus.py fuer lesson/fact/norm bereits tut).
3. Negativfaelle staerker als heute: nicht nur themenfremd (heutige
   `_NEGATIVE_TOPICS`), sondern echte Hard-Negatives -- Frage, deren
   RICHTIGE Antwort nicht im eigenen Bestand liegt, aber ein thematisch
   AEHNLICHER Treffer existiert (GermanDPR liefert das serienmaessig).
4. Suchlauf unveraendert ueber beide Gruppen, Label fliesst nicht in den
   Suchpfad ein.
5. Zwei getrennte Zahlen statt einer: Trefferquote_A = Treffer / Faelle mit
   Label=ja (misst die SUCHE). Fehlalarmquote_B = falsche Treffer / Faelle
   mit Label=nein (misst Falsch-Positiv-Neigung). Die heutige rohe Quote
   (8,78 % / 18 von 205, Label unbekannt) wird nicht mehr berichtet, sobald
   diese zwei Zahlen vorliegen -- sie ist genau die Zahl, die die
   Zweideutigkeit erzeugt.

## Leistet `kern/pruefkorpus.py` das heute schon?

**Teilweise.** Schritt 1-3 sind angelegt (category + target_id je Fall,
negative-Kategorie als Eichung). Schritt 5 -- die stratifizierte
Trefferquotenrechnung selbst -- fehlt in dieser Datei; sie erzeugt nur die
Testfaelle, keine Quote. Ob der Messlauf, der 8,78 % / 18-von-205 erzeugt hat,
diese category-Information genutzt hat, wurde in diesem Auftrag NICHT
geprueft (Suchpfad/kern/ ausser lesend sind laut Grenzen tabu, an anderem
Agenten). Die heutigen negative-Faelle sind zudem schwaecher als das
vorgeschlagene Hard-Negative-Verfahren: sie pruefen nur kompletten
Themenausfall (kubectl, Rosenschnitt), nicht den haerteren Fall "Suche
findet etwas Aehnliches, aber Falsches".

## Nicht getan (Grenzen)

Kein Download, kein Einspielen, keine Aenderung an kern/pruefkorpus.py, an
den Suchpfad-Dateien oder an quellen/fremdquellen.json. Kein Probeabruf
durchgefuehrt -- die Lizenzpruefung allein beantwortete die gestellten
Fragen bereits vollstaendig, ein Probeabruf war fuer diesen Auftrag nicht
noetig.
