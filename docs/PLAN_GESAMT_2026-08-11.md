# Gesamtplan brainlehr, Fassung 2026-08-11 (Abend)

Ersetzt die Leitannahme von `PLAN_DESTILLE_2026-08-09.md`. Der Plan selbst
bleibt gültig, wo er Einzelschritte beschreibt — seine **Reihenfolge** ändert
sich, weil die Annahme, auf der sie stand, heute vermessen wurde.

## Was sich geändert hat

Der Destille-Plan stand auf einem Satz: *der Abruf ist die Fehlstelle, also den
Abruf verbessern.* Heute ist die Reichweite dieses Satzes beziffert.

| Ausfallstelle | gemessen | hilft ein besserer Abruf? |
|---|---|---|
| Zeitpunkt — Nachricht erreicht den Haltepunkt nie | 18,3 % (15 von 82) | nein |
| Rangfolge — Ziel nicht unter Deckel 10/7 | 15 von 35 | teilweise |
| Gewohnheit — es wird gar nicht gefragt | heute dreimal belegt | nein |

Dazu drei Einzelbefunde, die die mittlere Spalte zusätzlich entwerten:

- Die **Stichwortsuche trägt nichts bei.** Über sechs Verschmelzungsgewichte
  rettet sie keinen Fall, den die Vektorsuche verfehlt — und im Betriebszustand
  kostet die Verschmelzung zwei Fälle (13 statt 15).
- Der Speicher ist in der **Sprache der Antwort** abgelegt, der Prompt trägt die
  **Sprache der Frage**. Am 2026-08-11 gemessen an einer echten Betreiberfrage:
  von acht Stichworten kam genau eines in der entscheidenden Lehre vor — das
  Füllwort „trotzdem".
- Die dafür gebaute Gegenmaßnahme (**S12**, mehrstufiger Abruf) steht seit dem
  2026-08-09 auf **AUS**: beide billigen Stufen verbesserten nichts. Die teure —
  die Anfrage in die Sprache der Antwort übersetzen — wurde nie gebaut.

**Folge:** Der Abruf bleibt eine Baustelle, aber er ist nicht mehr *die*
Baustelle. Zwei von drei Ausfällen sind gegen Ranking immun.

## Die drei Linien, in die sich die Arbeit ab jetzt teilt

### Linie A · Mehr Wege hinein, die nicht raten

Ein Pfad ist ein exakter Schlüssel: Wissen ist da oder nicht, keine
Trefferquote, kein Deckel.

| gebaut | Stand |
|---|---|
| Pfadschlüssel `codekanten.py` | 1744 Kanten, 874 Dateien tragen Wissen |
| Prüfspruch-Kette `pruefspruch.py` | 7 Sprüche, Kette geschlossen |
| Frageform im Recall-Block | steht |

**Offen:** S12 zweiter Anlauf (Anfrage in die Sprache der Antwort übersetzen)
und Metroviz als Anzeige auf den Kanten.

### Linie B · Sortieren statt sammeln

Nicht jede Lehre gehört in eine Suche. Die Börsen-Recherche liefert das
Kriterium (unter Zeitdruck liest niemand nach — SEC 15c3-5, belegt),
`sortierregel.py` liefert die Zahl: **40 von 741 Lehren gehören in den
Codepfad**, 701 ins Nachschlagewerk, davon 141 ausdrücklich, weil sie Haltung
beschreiben statt einer prüfbaren Bedingung.

Erste vollständige Kette an einem Beispiel: `L-a69129` → Vorschlag → Sortierung
→ Bedingung im Code (Modellsperre) → gefangen hätte sie drei Vorfälle.

**Offen:** die restlichen 39 der 40 durchgehen — aber nicht am Stück, sondern
wenn sie auftreten.

### Linie C · Messen dürfen

Drei Messungen an einem Tag zurückgenommen: Kontamination durch den
Abruf-Haken, ein Fehler im eigenen Messaufbau, ein Tuning-Maximum aus 24
Versuchen. Die Regeln dagegen stehen jetzt als Prüfung (`messregeln.py`,
beanstandet die drei eigenen Dateien von heute).

**Der Engpass ist der Korpus.** `echtkorpus.py` sammelt kontaminationsfrei —
Aufgabentext aus echten Nachrichten, Ziel über den Pfadschlüssel — aber der
Ertrag ist **4 Fälle aus 300 Nachrichten**. Ohne ihn ist jede weitere Abrufzahl
eine, die wir später zurücknehmen.

## Enigma — was steht, was blockiert

Landkarte: `docs/ENIGMA_LANDKARTE_2026-08-11.md`. Aller Enigma-Code liegt auf
`brainlehr/b4-ausweis`, **nicht** in diesem Arbeitsbaum.

**Steht:** Zweckprojektion für eine Rolle an `knowledge_read` (echt verdrahtet,
2/2 grün) · neutrale Ablehnung gesperrter Knoten ohne Metadatenleck ·
Ausweis-Grundmechanismus · zwei synthetische Machbarkeitsstudien, ehrlich als
„kein P2-Anspruch" markiert.

**Offen, nach Blockierwirkung:**

1. **`freigabe` fehlt in `knowledge_search`/`knowledge_browse`** — ein
   gesperrter Knoten bleibt dort auffindbar. *Dieser Punkt ist heute zweimal
   unabhängig gefunden worden: von mir am Vormittag (Knoten `cda47024`) und von
   der Bestandsaufnahme am Abend. Das macht ihn zum ersten.*
2. Zweckprojektion deckt nur ein Rolle/Zweck-Paar ab.
3. Die Ausweis-Sperre ist ein **Merkmal, keine Sperre** (`L-33d3bd`) —
   Selbstbedienung möglich.
4. Machbarkeitsstudien sind nicht mit dem realen Speicher verbunden.
5. Pseudonymisierungs-Proxy und Kontext-Schnappschüsse: nur Konzeptknoten.
6. P2-Unternehmensgrenze ausdrücklich pausiert.

**Widerspruch, benannt statt aufgelöst:** Zwei kritische Lehren (`L-f67cd1`,
`L-645969`) behaupten weiterhin „rot"/xfail; im Code gibt es keinen
Enigma-`xfail` mehr und die Tests laufen grün. Der Speicher wurde nicht
nachgetragen. Ich schreibe das nicht auf Zuruf um — die Tests liegen auf einem
fremden Zweig, die Prüfung gehört dorthin.

## Die Durchgangslinie, die erst jetzt sichtbar wird

Drei Vorhaben, die getrennt entstanden sind, haben dieselbe Bauform:

- **Enigmas Zweckprojektion** baut aus einem Datensatz einen neuen, der nur
  trägt, was der Zweck rechtfertigt.
- **Der Fremdimport** (`fremdimport.py`, heute gebaut) baut aus einem
  MAUDE-Datensatz einen neuen, der die Art.-9-Felder gar nicht erst enthält.
- **Die Sortierregel** entscheidet, was überhaupt in den durchsuchbaren
  Bestand gehört.

Alle drei sind **Projektion statt Filterung**: nicht entfernen, was nicht darf,
sondern nur bauen, was darf. Jede Blacklist hat ein Loch; eine Whitelist hat
diese Eigenschaft nicht. Das ist kein Zufall dreier Entwürfe, sondern eine
Architekturregel, die dieses Haus schon anwendet, ohne sie benannt zu haben.

## Reihenfolge, und wo sie bindend ist

1. **Korpus vor Abrufarbeit** (Linie C vor Linie A). Bindend: ohne ihn ist
   jede Verbesserung unbelegbar, und wir haben heute dreimal erlebt, was das
   kostet.
2. **Freigabe in `search`/`browse`** (Enigma 1). Unabhängig von allem anderen,
   zweimal unabhängig gefunden, und es ist eine Lücke, keine Verbesserung.
3. **S12 zweiter Anlauf** — erst wenn 1 steht, sonst misst er sich selbst.
4. **Fremdbestände**: ASRS und NIST vollständig, MAUDE über die Whitelist. FAA
   danach. CROSS, ESA, NRC, IAEA nicht.
5. Enigma 2–6 nach Blockierwirkung, aber auf ihrem Zweig.

## Was bewusst nicht getan wird

Kein Ausbau des Rankings, bevor der Korpus steht. Keine Übernahme der
NASA/ESA-Zwangsmechanik (Konsil 2026-08-11: die Voraussetzung ist strittig, die
Prosa-Quittierung wird binnen Tagen zum Ritual). Kein Import von CROSS, ESA,
NRC, IAEA. Keine Rückrechnung alter Messungen — sie sind zurückgenommen, nicht
repariert.

## Woran sich Erfolg messen lässt

- Korpus ≥ 20 Fälle, kontaminationsfrei erhoben — dann ist Linie A wieder
  messbar.
- Ein gesperrter Knoten erscheint in **keinem** der drei Lesewege.
- Zahl der Lehren, die als Bedingung im Code stehen, statt nur im Speicher.
- Und die ehrlichste Kennzahl: wie oft eine Prüfinstanz den Auftraggeber
  überstimmt. Heute 3× (Konsil), 2× (Recherchen). Sinkt sie auf null, ist das
  Verfahren Dekoration.
