# Quantitativer Handel: Software, Rechenweg, Vorhersageprüfung — 2026-08-11

Eigene Stimme, eigene Quellen, eigener Eintrag in der Prüfspruch-Kette (#6).
Herkunft je Aussage gekennzeichnet.

## Warum das hierher gehört

Ein Abruf ist strukturell dasselbe wie eine Vorhersage: aus vielen Kandidaten
die wenigen wählen, die gleich gebraucht werden. Der Handel prüft solche
Vorhersagen seit Jahrzehnten — und hat dabei gelernt, sich selbst zu misstrauen.
Er hat für zwei Fehler, die dieser Betrieb heute gemacht hat, Namen und
Gegenmittel.

## Die zwei Fehler von heute, mit ihren Fachnamen

### 1 · Bestwert aus 24 Versuchen als Ergebnis ausgegeben

Heute wurden vier Suchbauformen und sechs Verschmelzungsgewichte an denselben
35 Fällen durchprobiert und der beste Wert berichtet. Im Handel heißt das
**Backtest-Overfitting**; die Korrektur ist die **Deflated Sharpe Ratio**
(Bailey/López de Prado 2014, SSRN 2460551) — sie rechnet aus, wie gut der beste
von N Versuchen allein durch Zufall aussehen musste (*belegt*).

Sie braucht weder Geld noch große Fallzahl. Die billigste brauchbare Form:
**die Anzahl der Versuche mitschreiben und den Gewinner an einem Satz
bestätigen, der beim Tunen nicht dabei war.**

**Sofort angewandt** (`runs/haltemenge_2026-08-11.json`), Teilung nach Hash der
Zielkennung, damit sie weder zufällig noch von mir gewählt ist:

| | Tuning (22 Fälle) | Haltemenge (13 Fälle) |
|---|---|---|
| beste Bauform `kurzfeld` | 5 | **2** |
| FTS5 (Ausgangsstand) | — | **4** |

Der Vorsprung, den `kurzfeld` beim Tunen hatte, ist auf der Haltemenge **weg** —
dort liegt der alte Stand vorn. Die Zahl „7 von 35" aus dem Bauform-Vergleich
war ein Tuning-Maximum, keine Messung. Das ist genau der Fehler, den die DSR
beschreibt, und er wäre ohne diese Recherche in die nächste Entscheidung
gewandert.

### 2 · Prüfkorpus aus den Einträgen erzeugt, die er finden soll

Fachname: **data snooping bias / In-Sample-Kontamination**. Gegenmittel:
**Point-in-Time-Trennung** und **Purging/Embargo** (López de Prado 2017,
purged/combinatorial purged CV) — beides reine Reihenfolgefragen, direkt
übertragbar, ohne Fallzahl (*belegt*).

## Alterung einer Lehre

**Walk-Forward** (später an neuen Fällen nachmessen) überträgt sich und braucht
keine große Fallzahl (*belegt*). Echte Halbwertszeit-Kurven brauchen tägliche
Beobachtungen über Jahre — bei 763 Lehren nicht nachbaubar, höchstens als
Faustregel (*Modellwissen, ungeprüft*: genannte Alpha-Zerfallsraten US 5,6 %
p.a., Europa 9,9 % p.a., mittlere Beweiskraft).

## Ausdrücklich verworfen

**kdb+/q und Tick-Datenbank-Infrastruktur.** Voraussetzung ist Durchsatz von
Millionen Ereignissen je Sekunde. brainlehr hat 2102 Einträge, keine
Latenzanforderung, keinen Datenstrom (*belegt* zur Technik, Verwerfung an der
Voraussetzung).

## Was daraus für brainlehr folgt

1. **Jede Messung nennt künftig die Zahl der Versuche.** Ein Bestwert ohne
   diese Zahl ist keine Messung.
2. **Haltemenge ist Pflicht**, sobald mehr als eine Bauform verglichen wird.
3. **Der neue Prüfkorpus wird zeitlich getrennt**, nicht thematisch: Fälle aus
   Einträgen, die es zum Messzeitpunkt schon gab, gegen Einträge danach.
