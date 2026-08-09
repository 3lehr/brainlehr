FAKTEN

Eingabedatei: SCRATCH/lose/LOSNAME
Ausgabedatei: SCRATCH/neu/LOSNAME

Die Eingabedatei enthaelt bis zu 10 Wissensknoten als JSON-Liste mit den Feldern id, path, title, summary, co (der Volltext, heisst im Bestand content), tags, project_id.

AUFTRAG

Jeden Knoten NEU FORMULIEREN. Der Sachgehalt bleibt vollstaendig und unveraendert: nichts hinzuerfinden, nichts weglassen, keine Zahl, kein Datum, kein Eigenname geaendert. Geaendert wird ausschliesslich, WIE dasselbe gesagt wird.

1. title: benennt die Sache, nicht ihre Herkunft. "Konsil 2026-07-22" sagt nichts; "Wer entscheidet ueber die Vergabe" sagt es. Datum, Kennung und Anlass duerfen vorkommen, aber nie allein stehen.
2. summary: ein bis drei Saetze mit der KERNAUSSAGE, verstaendlich ohne Vorwissen. Keine Verwaltungsformeln ("dieser Knoten haelt fest"), kein Verweis auf Dateien oder Sitzungen als Ersatz fuer Inhalt.
3. co: behaelt alle Einzelheiten. Ganze Saetze statt Stichpunktfragmente. Benenne die Begriffe MEHRFACH und unterschiedlich -- wo nur "der Vorgang" steht, gehoert an einer Stelle auch der Sachbegriff hin, damit der Text auch dann trifft, wenn jemand mit anderen Worten fragt als der Verfasser sie gewaehlt hat.
4. Ist co leer, schreibe ihn aus title und summary heraus so weit, wie der vorhandene Sachgehalt reicht -- und keinen Satz weiter. Erfinde nichts, um Laenge zu erzeugen. Ein Knoten, ueber den wenig bekannt ist, bleibt kurz.
5. Deutsch, Umlaute erlaubt. Keine Emojis, keine Ueberschrift tiefer als zwei Ebenen.

DIE HARTE REGEL, an der dieser Auftrag abgenommen wird

Jede Zahl, jedes Datum, jede Uhrzeit, jede Kennung, jeder Dateiname, jeder Pfad und jede Zeilennummer aus dem Originaltext MUSS im neuen Text wieder vorkommen -- woertlich, in derselben Schreibweise. Sie sind die Traeger der Aussage: ohne sie bleibt ein Satz, der plausibel klingt und nichts mehr belegt.

Das gilt auch dann, wenn dir eine Aufzaehlung von Zeilennummern oder Dateinamen unwichtig erscheint. Sie ist es nicht -- sie ist der Grund, warum jemand diesen Knoten spaeter findet und ihm glaubt.

Umgekehrt gilt genauso: erfinde KEINE Zahl und KEINEN Dateinamen, der im Original nicht steht. Auch nicht als Verkuerzung -- wenn dort '/features/vehicles/domain/vehicle_identity_resolution.dart' steht, schreibe genau das und nicht 'vehicle_identity_resolution.dart'.

Ein Text darf laenger werden. Er darf NICHT kuerzer werden, indem Belege wegfallen.

Eine maschinelle Pruefung vergleicht diese Traeger vorher/nachher. Sie findet jeden Verlust.

TAGS

Das Feld tags wird mit gefuellt, und zwar AUSSCHLIESSLICH aus diesem Katalog:

KATALOG

Regeln dazu: drei bis sechs Tags je Knoten. Nur Begriffe aus dem Katalog, woertlich uebernommen. Passt nichts, nimm weniger -- notfalls gar keins. Ein Tag, das im Katalog fehlt, DARFST DU NICHT SETZEN; du sammelst es stattdessen und meldest es am Ende als Vorschlag. Vorhandene Tags des Knotens, die im Katalog stehen, bleiben erhalten.

GRENZEN

- Du aenderst KEINE Datei im Repo und KEINE Datenbank. Nur deine eine Ausgabedatei.
- Felder id, path, project_id bleiben unveraendert und werden unveraendert uebernommen.
- Suche NICHT im Repo nach Zusatzinformation. Arbeite ausschliesslich mit dem, was in deiner Eingabedatei steht.

ABNAHME

Ausgabe als JSON-Liste in die Ausgabedatei: gleiche Anzahl, gleiche Reihenfolge, gleiche id-Werte, Felder id, path, title, summary, co, tags, project_id. Pruefe vor dem Melden per Python, dass die Datei gueltiges JSON ist, die Anzahl stimmt und die id-Menge identisch mit der Eingabe ist.

Melde NUR: Anzahl, die Liste deiner Tag-Vorschlaege (Begriffe, die du gerne gesetzt haettest, die aber nicht im Katalog stehen), und je Knoten eine Zeile mit id und Zeichenzahl von summary und co vorher/nachher. Keine Inhaltszusammenfassung.

Sieht die Datei anders aus als hier beschrieben, halte dich an die Datei und melde die Abweichung.

EINSATZ

Diese Texte sind kuenftig der Bestand, aus dem jede Sitzung ihr Wissen zurueckbekommt. Wer Sachgehalt hinzuerfindet oder weglaesst, faelscht ihn -- und niemand sieht es, weil der neue Text plausibel klingt.
