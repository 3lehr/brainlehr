# ADR-015: Der Designvorrat ist Daten — und der Editor kann nur, was der Satz kann

**Stand** 2026-08-14T21:36:26+0200
**Status** Angenommen
**Betrifft** `atelier` (Dokumentfenster), `kern/satz.py`, jede Gattung, jede Domäne
**Entscheider** Betreiber, 2026-08-14

## Die Frage

> *„wäre das dann der Zeitpunkt, einen übergreifenden konfigurierbaren
> Designguide einzuführen und außerdem den WYSIWYG-Editor dementsprechend
> einzuschränken?"*

## Die Antwort: ja, und der Zeitpunkt ist **vor** dem Editor

**Reihenfolge, keine Menge:** Ein Editor, der zuerst alles kann, kann später
nichts mehr wegnehmen. Jedes bis dahin geschriebene Dokument hielte eine Form
fest, die der Guide verbietet — und dann steht die Wahl zwischen „Guide
aufweichen" und „bestehende Dokumente brechen". Bei null Dokumenten kostet die
Festlegung nichts; sie ist danach nicht mehr zu haben.

## Drei Festlegungen

**1. Der Vorrat ist Daten, nicht Prosa.** Schriftgrößen, Farben, Abstände,
zulässige Bausteinrollen liegen in **einer** Datei, aus der **beide** Ableitungen
lesen — der LaTeX-Vorspann und die schnelle Darstellung. Ein Guide in Prosa wird
zweimal ausgelegt, und das ist dieselbe Drift wie in ADR-013, nur eine Etage
höher.

*Gemessen und als Vorbild wie als Warnung brauchbar:*
`buckeberg/design/DESIGN-GUIDE.md` (7838 Byte, Stand 2026-07-25) ist bereits ein
Guide **für alle Medien** — Typografie, Farben, Layout, Ton, Medien-Umsetzung.
Er ist **reine Prosa**; im Verzeichnis liegt keine Token-Datei. Genau der Schritt
fehlt dort und wird hier zuerst gemacht.

**2. Konfigurierbar nach GATTUNG, nicht nach Domäne.** Rechnung, Brief,
Korrekturblatt, Kapitelübersicht — jede Gattung hat ihren Vorrat. Eine Rechnung
sieht überall gleich aus, **gleich welche Domäne sie erzeugt**. Wäre der Vorrat
je Domäne einstellbar, zerfiele genau das einheitliche Aussehen, das ADR-014
gerade sichert, und der Satz *„soll aussehen, als wäre es ein Teil davon"* wäre
wieder offen.

Anschluss an den bestehenden Baustein-Vertrag: Die Rollen heißen **Behälter,
Überschrift, Liste, Tabelle, Abbildung, Feld** — nicht Drucksachen wie
„Abschnitt" oder „Seite". Nur so passt eine andere Gattung später hinein.

**3. Der Editor bietet nur an, was der Satz kann.** Das ist der eigentliche
Gewinn und der Grund, warum die Einschränkung keine ist: **Der Formenvorrat ist
der Vertrag zwischen Darstellung und Blatt.** Kennen beide nur dieselben
Formen, können sie nicht beliebig weit auseinanderlaufen — der Wächter prüft
dann Einzelfälle, nicht einen offenen Raum.

## Was das nebenbei löst

**Barrierefreiheit wird durchsetzbar statt appellativ.** Kontrast,
Mindestgrößen und Struktur kommen aus dem Vorrat, nicht aus der Sorgfalt
dessen, der gerade schreibt. Das entspricht der Hausregel „Farben, Größen und
Abstände liegen ausschließlich in Tokens" — und dem Grund dafür: Ein Wechsel
des Kontrastverfahrens ist dann eine Funktion, keine Suchen-und-Ersetzen-Aktion
durch alle Dokumente.

## Der Preis, benannt

- **Was der Vorrat nicht kennt, geht nicht.** Wer eine Form braucht, die es nicht
  gibt, ändert den Vorrat — das ist Arbeit an der Trägerschicht und langsamer,
  als es „nur schnell" hinzuschreiben. Genau das ist beabsichtigt.
- **Der Vorrat wird zur Engstelle.** Jede neue Gattung geht durch ihn hindurch.
  Solange die Rollen stimmen (Punkt 2), ist das billig; heißen sie nach
  Drucksachen, wird es teuer.
- **Zwei Leser einer Datei bleiben zwei Leser.** Der Vorrat verhindert die grobe
  Drift, nicht die feine. Der Wächter bleibt nötig.

## Verworfen

- **Guide als Prosa** (wie buckeberg heute). Zwei Ableitungen legen ihn zweimal
  aus; die Abweichung fällt erst am fertigen Blatt auf.
- **Editor erst frei, Regeln später.** Siehe oben: später ist die Festlegung
  nicht mehr zu haben.
- **Vorrat je Domäne einstellbar.** Hebt ADR-014 auf.
