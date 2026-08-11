# Wie der Handel Wissen wirksam macht — Recherche 2026-08-11

Eigene Stimme, eigener Zugang (Websuche), eigener Eintrag in der Prüfspruch-Kette
(#5). Herkunft je Aussage gekennzeichnet, wie beauftragt.

## Die Antwort auf die Frage, die hier den ganzen Tag offen war

**Unter Zeitdruck wirkt kein Nachschlagewerk.** Die SEC hat in der Durchsetzung
zu Rule 15c3-5 ausdrücklich festgestellt, dass menschliche Überwachung in
Echtzeit NICHT genügt — die Prüfung muss automatisiert vor der Order laufen
(*belegt*). Wissen wirkt dort nur, wenn es **vorher, außerhalb der
Drucksituation, in ausführbare Kontrollen übersetzt** wurde: Schwellenwert,
Gate, Notabschaltung. Am Entscheidungspunkt liest niemand mehr etwas.

Übertragen auf hier: Die gemessene Trefferquote von 15 von 35 ist strukturell
dasselbe Problem wie „ein Mensch müsste unter Zeitdruck nachschlagen". Daraus
folgt eine **Sortierregel, die brainlehr heute nicht hat**:

> Eine Lehre mit hohem Schaden gehört nicht in den durchsuchbaren Speicher,
> sondern als Prüfung in den Codepfad, der die Handlung ausführt.

Der Speicher behält den Rest — Zusammenhang, Begründung, Historie. Heute
landet beides im selben Topf, und genau deshalb sah die Abruffrage aus wie
das ganze Problem.

## Mechanismen mit Voraussetzungsprüfung

| Mechanismus | Voraussetzung | trägt ohne Geld/Aufsicht? | Herkunft |
|---|---|---|---|
| Vorhandels-Risikoprüfung (SEC 15c3-5) | automatisches Gate vor der Aktion | **ja, vollständig** | belegt |
| Kill-Switch (MiFID II RTS 6 Art. 12) | ein Punkt, der alles Laufende zurückzieht | **ja** | belegt |
| Post-Mortem / Fehlerdatenbank | abgegrenzter Vorfall, Disziplin | **ja, vollständig** | belegt (Knight Capital) |
| Modellvalidierung (Fed SR 11-7) | Prüfer ohne Berichtslinie zum Entwickler | geschwächt, Grundmuster trägt | belegt |
| Positions-/Verlustgrenzen | bezifferte Grenze in Geld | Kalibrierung fällt weg, Muster überträgt sich | Modellwissen, ungeprüft |
| Vier-Augen-Prinzip | zweite, unabhängig urteilende Instanz | ohne sie leer | Modellwissen, ungeprüft |
| Notfallübungen | wiederkehrender geplanter Testlauf | ja | Modellwissen, ungeprüft |
| **Circuit Breaker** | viele unabhängige Teilnehmer, fremde Panik | **nein — verworfen** | belegt |
| **Meldepflicht an Aufsicht** | externe Instanz mit Sanktionsmacht | **nein — verworfen** | belegt |

## Knight Capital, und warum der Fall ohne Geld überträgt

Als Kernursache wurden **fehlende Eskalationsprozedur und fehlende
automatisierte Fehlererkennung** benannt — nicht fehlendes Kapital (*belegt*).
Der Verlust war die Folge, nicht die Ursache. Damit hängt der Mechanismus nicht
an der Geld-Rückmeldung.

## Was an der Geld-Rückmeldung hängt — und was nicht

Am Geld hängt die **Kalibrierung** einer Grenze, nicht ihre Bauform. Das Muster
„harte automatische Obergrenze plus Blockade" überträgt sich auf jede
quantifizierbare Größe; im hiesigen Betrieb naheliegend: Token-Budget, Anzahl
geänderter Dateien, Laufzeit. (*Modellwissen, ungeprüft* für die Übertragung.)

## Was das mit dem heutigen Tag zu tun hat

Drei unabhängige Wege sind zum selben Ergebnis gekommen:

1. Der **Widersacher** im Konsil: am schwersten zu umgehen ist kein Satz,
   sondern ein falsifizierbarer, gegen den echten Stand geprüfter Beleg.
2. Die **Modellsperre** von heute Vormittag: eine Regel im Klartext wurde
   dreimal verletzt; dieselbe Regel als Bedingung im Code hält.
3. Diese **Recherche**: die SEC sagt es als Aufsichtsregel — menschliche
   Prüfung in Echtzeit genügt nicht.

Und der Weg dorthin ist hier bereits halb gebaut: `vorschlag.py` (Planschritt
S18) erhebt aus dem Bestand, welche Lehren einen Prüfstein verdienen. Sein
erster Vorschlag am 2026-08-11 war `L-a69129` — und genau daraus wurde am
selben Tag eine Bedingung im Code. Aus dem Zufall soll der Regelfall werden.
