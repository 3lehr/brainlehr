# Plan: die nächste Stufe — was der Nachtlauf erforscht hat und was daraus folgt

Angelegt 2026-08-21T08:20:00+0200. Nachfolger von
`docs/PLAN_GESAMTBAU_2026-08-21.md` (acht Stränge A–G, abgeschlossen).

Dieser Plan ordnet nach EINEM Maßstab, und es ist derselbe wie bei B1:
**Was lässt sich später nicht mehr nachholen?** Nicht Größe, nicht Nutzen,
nicht Aufwand — Aufwand ist als Kriterium ausdrücklich gestrichen
(`L-dafc34`, 4×, Regelrang).

## §1 Was der Nachtlauf ergeben hat

**Gebaut und belegt** (25 Commits, `1d0e7470`..`85df5c87`): vier Achsen im
Schema · Mandanten- und Kreistrennung samt Zahlen · Profilwechsel mit Rückweg
· Forderungen als Vorgang · Aussetzer-Sicherung · Zugriffsmuster ·
Verfallsrate · englische Tür · Einrichtungsassistent.

**Zweimal NICHT gebaut, weil die Messung es sagte** — und das sind Ergebnisse,
keine Lücken:

| | gemessen | Folge |
|---|---|---|
| A2 Leerlauf-Rückzug | 40,5 % gesparte Suchen gegen 38,6 % verpasste Treffer; in der sicheren Fassung 0,0 % verpasst, aber nur 0,4 % gespart | verworfen |
| A1 Widerspruchserkennung | 7 Treffer, **0 echte Widersprüche**, Positiv- und Negativkontrolle greifen | nicht verdrahtet |

**Fünf Zahlen aus Plan und Übergabe waren falsch**, alle gemessen widerlegt:
die Spracherkennung („36 Stoppwörter, 758/770") existierte als Code nicht ·
der Leer-Anteil war 34,1 % statt 37,8 % · von 13 Forderungen war **eine**
offen · A1 galt als „belegt", ohne je abgenommen worden zu sein · und das
GitHub-Konto ist **nicht** gesperrt, der öffentliche Export ist seit
2026-08-20T17:27 draußen.

## §2 Der Engpass, gemessen und unverändert

`BDW-P05` (Zielbild A): **3/35 = 8,6 %** gegen Schwelle 95 %. Aussage 17,1 %,
Quelle 11,4 %, Status 11,4 %, Geltung 8,6 %.

**Das ist kein Trefferquotenproblem.** Die drei anderen Felder werden gar
nicht ausgeliefert. Der Speicher, dessen Zweck das Belegen ist, liefert seine
Antworten ohne Herkunft. Solange das so ist, ist jede Verbesserung am Abruf
eine Verbesserung an der falschen Stelle.

## §3 Zwei Achsen, die sich nicht nachholen lassen — bindend zuerst

Derselbe Grund wie bei B1, und er ist keine Frage des Füllstands.

**§3.1 Der GEGENSTAND — wer oder was ist gemeint.**
Gemessen: `gegenstaende` trägt **2 Zeilen**, `gegenstand_namen` **7** — und
beide Gegenstände sind Software (`anwendung`, `einstellung`). Keine Person,
kein Objekt, kein Vertragspartner. Die Tabelle existiert seit ADR-028 („Ein
Name ist nie ein Schlüssel"), angewandt ist sie auf sich selbst.

Jedes Werkzeug, das je dazukommt, hängt daran: ein Kalender braucht
Teilnehmer, eine Rechnung einen Empfänger, ein WEG-Vorgang einen Eigentümer,
ein Beleg einen Aussteller. Wer heute ein Dokument ablegt, ohne die Person zu
binden, hat morgen **einen Text mit einem Namen darin** — und ein Name ist
nie ein Schlüssel.

**§3.2 Die FÄLLIGKEIT — was wann von wem zu tun ist.**
Gemessen: `gilt_ab` in der Zukunft steht bei **0 von 5 240**, `gilt_bis` bei
**2**. Der Speicher hat keine Zukunft.

Strang F hat die halbe Sache gebaut, ohne dass es auffiel: Der Vorgang trägt
`offen|erledigt|abgelehnt|ueberholt`, sortiert nach Alter, beim Sitzungsstart
vorgelegt — eine Aufgabenliste **ohne Datum**. Kalender, Aufbewahrungsfrist,
Wiedervorlage, Zahlungsziel und Wartungstermin sind **eine** Achse, nicht
fünf Anwendungen.

**Was daraus NICHT folgt:** Mail, Chat, Telefonie, Buchhaltung,
Dateisynchronisation. Sie hängen alle an denselben zwei Achsen und bringen
keine eigene mit — sie kosten später genauso viel wie heute und gehören
deshalb nicht vorgezogen.

## §4 Was unabhängig davon gebaut werden kann

**§4.1 Die Namensfrage als Namensfrage erkennen** — der Fund des Konsils, den
keine Linse beauftragt hatte, gemessen am 2026-08-21:

| Frage | Ziele gefunden |
|---|---|
| `Döldissen` | **3 von 3**, Ränge 1, 2, 3 |
| `zeige mir alles was mit Frau Döldissen zu tun hat` | **1 von 3** |

Die Fähigkeit ist da, sie wird nur nicht angesteuert. Die Füllwörter der
Frage verdünnen den Namen; im schlechten Lauf steht auf Rang 2
`/stadtwerke/koeder-frau-elvira-quenzelbach-kd-nr` — getroffen auf „Frau",
geliefert eine andere Person. Der Verlust sitzt in der FRAGEFORM, nicht im
Index und nicht am Deckel: die beiden fehlenden Ziele stehen gar nicht mehr
in der Kandidatenliste.

**§4.2 Getrennte Kandidatenbudgets.** Heute fusioniert
`haken/suchpfad_abruf.py:169-171` Knoten und Lehren in EINE Liste von 17
Plätzen, bevor die getrennte Kappung (`MAX_NODES=10`, `MAX_LESSONS=7`)
greift. Das ist der gemessene, gattungsUNabhängige Hebel — und der Grund,
warum beim Katalogimport eine Lehre herausfiel.

**§4.3 Dokumentenablage** (`ADR-032`, `BDW-P15`), Ort als Einstellung je
Domäne.

**§4.4 Bauvermeidung** (Knoten `cb2193a8`): vor dem Bauen erst im eigenen
Haus, dann in der Welt nachsehen. Die innere Hälfte ist seit dem 2026-08-21
als Forderung erfasst.

## §5 Der Konsil zum zweiten Vektorraum — Stand und Widerspruch

| Linse | Empfehlung | tragendes Argument |
|---|---|---|
| Abrufgüte | **C** (nichts tun) | Verlust nicht gattungsabhängig (B und C liefern dieselbe Zahl) und **sättigend**: 951→13/35, 2 853→12/35, 9 510→12/35 |
| Betrieb | **A** (eigener Raum) | Wachstum (3 503 Abschnitte = 47 % des Vektorbestands), Löschen ist bei Dokumenten der Normalfall, und die `sensibel`-Kopplung |
| Irrtumskosten | offen | Linse wurde umgestellt (Aufwand als Kriterium gestrichen), rechnet neu |

**Die `sensibel`-Kopplung ist der härteste Einzelbefund und gehört
entschieden, egal wie der Konsil ausgeht:** `schema.sql:342/360` hängt die
FTS-Trigger an `sensibel = 0` — ein sensibler Knoten steht NICHT im
Volltextindex. `kern/build_embeddings.py` kennt das Feld gar nicht (0
Vorkommen), vergibt also einen Vektor. Wer WEG- und Steuerdokumente als
sensibel markiert — und „Daten Dritter" legt das nahe —, **zerstört damit
genau den Kanal, der Namen findet** (FTS: Ränge 1/9/70; Vektor: 4/218/1804).

**Ein Befund korrigiert eine eigene Lehre:** „Weg B — Gattungsfilter in der
Anfrage" ist bereits der Ist-Zustand (`haken/suchpfad_abruf.py:125`). Er war
nie eine Option.

## §6 Reihenfolge

```
  §3.1 Gegenstand ─┐
                   ├─ bindend zuerst, nicht nachholbar
  §3.2 Faelligkeit ┘
        |
        +--> §4.3 Dokumentenablage (braucht den Gegenstand)
        +--> Kalender, Fristen, Wiedervorlage (brauchen die Faelligkeit)

  UNABHAENGIG, ab sofort:
    §4.1 Namensfrage    §4.2 Kandidatenbudgets    §4.4 Bauvermeidung
    §2   BDW-R05 / Zielbild A  <-- groesster gemessener Rueckstand
```

## §7 Was bewusst nicht getan wird

* **Kein zweiter Vektorraum, solange der Konsil 1:1 steht.** Die dritte Linse
  entscheidet, oder der Betreiber. Ein Bau auf 1:1 wäre eine Wahl, die sich
  als Messung ausgibt.
* **Kein Werkzeug für Mail, Chat, Buchhaltung.** Siehe §3.
* **Kein `lehrtools`-Etikett auf brainlehr selbst** — brainlehr ist der
  Speicher, kein Werkzeug. Es gehört auf `lehrAtelier` und die
  `openlehr_X`-Domänen.

## §8 Verlauf

* 2026-08-21T08:20 — angelegt, nach Abschluss des Gesamtbaus und mit zwei von
  drei Konsillinsen.
