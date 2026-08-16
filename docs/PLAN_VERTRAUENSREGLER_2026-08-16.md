# Vertrauensregler — die Rückfragepflicht wird regelbar, die Belegpflicht nicht

**Angelegt** 2026-08-16T18:35:00+0200
**Entscheidung** Knoten `a6991a6b`. Betreiber wörtlich: *„das was an mir hängt, lass davon mehr
brainlehr machen, brainlehr braucht mehr vertrauen! dazu könnten wir einen vertrauensregler
einbauen, den der user steuern kann. meistens waren die blocker bisher keine echten!"*

## §1 Gemessener Ist-Stand

**Die These stimmt für diesen Tag.** Sieben Punkte warteten am 2026-08-16 auf den Betreiber:

| | Wartepunkt | Ausgang |
|---|---|---|
| 1 | Freigabe-Eintrag `mosaikplan` in `push_guard.py` | erteilt, unstrittig |
| 2 | Namensprüfung `origin` entfernen | erteilt („1"), unstrittig |
| 3–6 | **Vier** Rangeinstufungen (`bcabfa28`, `237be0f3`, `3c524455`, ADR-024) | offen, rein formal |
| 7 | Eine Zeile der globalen Hausregel berichtigen | offen, unstrittig |

**Keiner war inhaltlich strittig.** Sechs waren formale Hürden. Die vier Rangeinstufungen sind
derselbe Fall viermal: Drei Datenbank-Trigger (`knowledge_nodes_normrang_herkunft_bi/_bu`,
`..._norm_entschieden_belegart_pflicht_bi`) verlangen für Rang 1/2 einen menschlichen Entscheider
— und `knowledge_add` hat dafür keinen Eingang. Der Wächter blockiert also nicht, weil eine
Entscheidung fehlt, sondern weil ein **Feld** fehlt.

Das ist der wichtigste Befund des Ist-Stands: Der häufigste Blocker war kein Vertrauensproblem,
sondern eine **fehlende Funktion**. Ein Vertrauensregler hätte ihn nicht gelöst.

## §2 Was der Regler steuert

**Die Rückfragepflicht** — wann der Assistent innehält und fragt, statt zu entscheiden und zu
berichten.

**Nicht die Belegpflicht.** Rot vor grün, messen statt vermuten, Befunde benennen statt glätten
bleiben auf jeder Stufe unverändert. Wer schneller handeln darf, prüft sorgfältiger.

**Und auf keiner Stufe die vier Stopp-Punkte:** Kennwörter · Außenwirkung gegenüber Dritten ·
Unumkehrbares ohne Rückweg · Geld. Sie hängen nicht am Vertrauen, sondern an der Reichweite der
Folgen. Ein Regler, der sie mitregelt, ist kein Vertrauensregler, sondern ein Ausschalter.

## §3 Ehrliche Einordnung der Bauform — Merkmal, keine Sperre

Der Assistent läuft als derselbe Benutzer, dem die Reglerdatei gehört; er könnte sie selbst
hochsetzen. Damit ist der Regler ein **Merkmal**, keine Sperre — dieselbe Einordnung wie bei
`art=mensch` (`L-33d3bd`). Er drückt den Willen des Betreibers aus und macht ihn maschinenlesbar.
Er darf in keinem Bericht als Schutz auftauchen.

Tragfähig wird er durch die Gegenrichtung: **Jede Handlung oberhalb der Vorgabestufe wird mit
ihrer Stufe protokolliert.** Der Regler senkt die Zahl der Rückfragen und erhöht die
Nachvollziehbarkeit — nicht umgekehrt.

## §4 Verworfen, mit Grund

1. **Zahlenskala 0–10.** Verworfen: Niemand kann sagen, was 6 von 10 erlaubt und 7 nicht. Eine
   Skala ohne benannte Wirkung wird nach Gefühl gestellt und nach Gefühl ausgelegt.
2. **Regler je Handlungsart** (Push, Commit, Datei, Konfiguration). Verworfen als Startpunkt: vier
   Regler sind vier Stellen, die auseinanderlaufen. Erst eine Stufe, verfeinern wenn gemessen ist,
   dass es an einer bestimmten Art hakt.
3. **Regler im Speicher (Knoten oder Tabelle).** Verworfen: Der Regler muss lesbar sein, *bevor*
   die Datenbank offen ist, und von einem Menschen ohne Werkzeug änderbar. Eine Datei im Klartext.
4. **Automatisches Hochstufen nach Bewährung** („nach 20 fehlerfreien Handlungen eine Stufe
   höher"). Verworfen, und das ist die wichtigste Ablehnung: Ein Regler, den der Assistent selbst
   hochdreht, ist kein Vertrauen des Betreibers, sondern eine Selbstermächtigung mit Statistik
   davor.

## §5 Die Stufen

Benannt, nicht nummeriert — jede Stufe sagt, was sie erlaubt:

| Stufe | Der Assistent … |
|---|---|
| `vorlegen` | entscheidet nichts selbst, legt jeden Schritt vor. Der Zustand vor dem 2026-08-11. |
| `handeln` | entscheidet und berichtet danach; fragt bei Sperren, die andere gesetzt haben. **Vorgabe.** |
| `raeumen` | löst zusätzlich formale Blocker selbst auf, die keine inhaltliche Entscheidung tragen — die Klasse, die heute sechs von sieben Wartepunkten ausmachte. |

`raeumen` ist die Stufe, die der Betreiber meint. Sie ist eng definiert: Ein Blocker ist **formal**,
wenn seine Auflösung keine Frage beantwortet, die nur ein Mensch beantworten kann. Rangeinstufung
einer bereits getroffenen Entscheidung: formal. Ob eine Entscheidung überhaupt gilt: nicht formal.

## §6 Reihenfolge, bindend

1. **Zuerst die fehlende Funktion**, nicht den Regler: `knowledge_add`/`knowledge_update` brauchen
   einen Eingang für `norm_entschieden_von`. Das löst vier der sieben Wartepunkte von heute — ganz
   ohne Vertrauensfrage. Wer den Regler vorzieht, baut Vertrauen an einer Stelle ein, an der
   schlicht ein Feld fehlte.
2. Reglerdatei, Lesefunktion, Vorgabestufe `handeln`.
3. Protokollierung der Stufe bei jeder Handlung oberhalb der Vorgabe.
4. Erst danach: Wächter, die den Regler abfragen.

Schritt 1 vor 2 ist bindend — sonst misst man nie, wie viel der Regler überhaupt beiträgt.

## §7 Woran sich Erfolg messen lässt

**Nicht** an der Zahl der Rückfragen — die ließe sich durch Wegsehen senken. Sondern:

> Von den Punkten, die in einer Sitzung auf den Betreiber warten: Wie viele sind **inhaltlich
> strittig**? Heute: null von sieben. Bleibt diese Zahl bei null, während die Gesamtzahl der
> Wartepunkte sinkt, wirkt der Regler. Steigt sie über null, war eine Stufe zu hoch — und
> **dieser Fall gehört gemeldet, nicht weggeregelt.**

## Fortschreibung: Schritt 1 (2026-08-16T18:56:00+0200)

Erledigt, Commit `787ac08e`: `knowledge_add`/`knowledge_update` bekommen `betreiber_weisung` —
ein wörtliches Zitat, das `norm_entschieden_von='betreiber'` und `norm_entschieden_belegart=
'weisungszitat'` setzt. Beleg als DB-Trigger erzwungen (Anführungszeichen `„...."` + Mindestlänge,
zunächst 15, nach Fund korrigiert auf 10 — Knoten `3c524455` trägt nur ein 13 Zeichen langes
echtes Zitat, „Mit Historie."). Merkmal, keine Sperre — wie bei `art=mensch`.

Vier der fünf Knoten gesetzt: `237be0f3`, `3c524455`, `a6991a6b`, `460725f0` (der fünfte war beim
Nachsehen nicht der „ADR-024-Knoten", sondern die openlehr-V1-Weisung — Abweichung von der
Auftragsbeschreibung, gemeldet statt stillschweigend übernommen). `bcabfa28` **nicht** gesetzt:
sein Text zitiert eine Commit-Nachricht und die bestehende Hausregel, kein Betreiberzitat.

Rot-vor-grün geführt (Schema-Fassung vor dem Commit lehnte `weisungszitat` als Belegart komplett
ab), Gegenprobe geführt (Modellname als Entscheider bleibt bei Rang 1/2 abgewiesen), 14 Testfälle
in `tests/test_weisungszitat_beleg.py`, davon einer als Regressionstest für einen beim Bau selbst
gefundenen L-55075a-Fall (Mindestlängen-Korrektur erreichte eine schon migrierte DB nicht von
selbst, bis `_ensure_belegart_triggers()` den installierten SQL-Text statt nur den Namen prüft).

Schritt 2 (Reglerdatei) noch offen.

## Fortschreibung: Schritt 2 und 3 (2026-08-16T19:05:00+0200)

`kern/vertrauen.py` steht. Reglerdatei `~/.brainlehr/vertrauensstufe`, ein Wort im Klartext —
`echo raeumen > ~/.brainlehr/vertrauensstufe` und fertig, ohne Werkzeug.

**Vorgabe ist `handeln`, nicht die neue Stufe.** Ein Regler, der beim Einbau schon hochgedreht
ist, hat nie eine Ausgangslage — und die braucht §7, um überhaupt messen zu können, was er
beiträgt.

**Zwei Rückfälle, beide belegt:** Ein unbekannter Wert in der Datei fällt auf die Vorgabe zurück
und wirft *nicht*. Ein Tippfehler darf die Arbeit nicht anhalten — aber er darf erst recht nicht
zufällig hochstufen. Dasselbe für die leere Datei.

**Protokolliert wird nur oberhalb der Vorgabe.** Ein Protokoll, das jede gewöhnliche Handlung
aufnimmt, ist nach einem Tag unlesbar und wird dann von niemandem gelesen — dieselbe Todesart wie
beim Wächter, der bei jedem Commit anschlägt.

Die vier Stopp-Punkte stehen als eigene Konstante *neben* der Stufenlogik, nicht darin, mit einer
Zusicherung im Selbsttest. Sie fällt auf, sobald jemand versucht, sie in die Stufen
hineinzuziehen.

**Offen bleibt Schritt 4:** Wächter, die den Regler abfragen. Bewusst noch nicht gebaut — erst
muss sich zeigen, an welchen Stellen `raeumen` tatsächlich gebraucht wird. Wer den Regler jetzt
schon überall abfragt, verteilt eine Einstellung über zwanzig Dateien, bevor gemessen ist, ob sie
an dreien reicht.
