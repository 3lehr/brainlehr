# ADR-024: V1 zeichnet das atelier nativ — und die Beschreibung bleibt plattformblind

**Stand** 2026-08-16T12:59:23+0200
**Status** Abgelöst durch ADR-035 am 2026-08-28
**Betrifft** `atelier` (`app/`), `openlehr_einzelunternehmer`, jede künftige Domäne
**Entscheider** Betreiber, 2026-08-16
**Ersetzt** die Nachtrags-Zeile „Fachbildschirme → die Domäne, als Web über HTTP"
in ADR-013. Der Rest von ADR-013 bleibt unverändert in Kraft.

**Abgelöst durch:** ADR-035. Die frühere native-V1-Reihenfolge gilt nicht mehr:
Die zentrale WebUI ist der einzige produktive Renderer; vorhandene native,
OpenLehr- und sonstige UIs sind nach Inventar-/Ersetzungsgate nur Legacy.

## Die Vorgabe, wörtlich

> *„abe openlehr_einzelunzernehmer soll in V1 als swifft apple app gebaut werden,
> erst danach als webapp?!"*

und auf die Rückfrage, ob die Weboberfläche damit ein weiterer Schritt bleibt:

> *„einverstanden, wenn ich richtig verstanden habe das die weboberfläche später
> dann nur ein weiter schritt ist, es nicht schwerer, höchstens leichter macht?!!"*

## Warum das ADR-013 nicht bricht, sondern zu ihm zurückkehrt

ADR-013 enthält **zwei** Aussagen zur Oberfläche, und sie zeigen in
verschiedene Richtungen:

- **Hauptentscheidung:** *„Die Oberfläche ist Beschreibung. Die Domäne sagt, was
  zu sehen sein soll; das atelier zeichnet es mit seinen eigenen Bausteinen."*
- **Nachtrag am selben Tag**, eine Tabellenzeile: Fachbildschirme zeichnet die
  Domäne **als Web über HTTP**, begründet mit *„Nativ bringt hier wenig, und
  openlehrs Bildschirme existieren bereits"*.

Diese Begründung trägt nicht mehr, aus zwei unabhängigen Gründen:

1. **Sie ist ein Bestandsargument.** Der Betreiber hat genau diese Denkform in
   openlehr zweimal zurückgewiesen (`L-747223`), beim zweiten Mal wörtlich:
   *„Was seit Monaten irgendwo steht, kann nicht mehr ausschlaggebend sein."*
   Vorhandener Code belegt Machbarkeit, er begründet keine Beibehaltung
   (`L-a823a5`).
2. **Der einzige gemessene Grund gegen nativ ist widerlegt.** Die Annahme, die
   Mac-Anwendung sei nicht programmatisch prüfbar, wurde am 2026-08-14 gemessen
   und fiel: 285 Knoten im Bedienungshilfen-Baum, 205 mit zugänglichem Namen
   (`0b0913f6`). *„Damit entfällt der belegte Grund, die Oberflächentechnik von
   Swift wegzubewegen."*

Dazu kommt ADR-014 (das atelier trägt Darstellung und Einstellungen) und ADR-016
(*„ein excel im atelier auf betriebsystem ebene"*) — beide setzen nativ voraus.

## Die Entscheidung

**1. V1 ist nativ.** Das atelier zeichnet die Bildschirme von
`openlehr_einzelunternehmer` mit seinen eigenen Bausteinen. Eine Weboberfläche
ist ein **späterer, zusätzlicher Zeichner** derselben Beschreibung — kein
zweiter Bau und keine Voraussetzung.

**2. Die Beschreibung sagt WAS, nie WIE.** Kein Feld benennt ein Bedienelement,
eine Plattform oder ein Aussehen. Erlaubt sind Absicht und Inhalt (Feld, Liste,
Gruppe, Beschriftung, Pflicht, Wertebereich); verboten sind Bauformen
(`NSTableView`, `popover`, `sidebar`, `modal`, Pixel, Farben, Schriftgrößen).

**3. Die Schranke wird jetzt gebaut, nicht später.** Der Manifest-Prüfer weist
ein Paket ab, dessen Oberflächen-Beschreibung Plattform- oder Bauformbegriffe
trägt; ein Test ist ohne diese Regel rot. Begründung ist die **Reihenfolge**,
nicht die Menge: Solange nur ein Zeichner existiert, zieht nichts in die andere
Richtung, und die Beschreibung nimmt zwangsläufig die Form dessen an, der sie
als Erster liest. Danach ist jede Korrektur eine Migration jedes verteilten
Manifests.

## Was ausdrücklich NICHT entschieden wird

- **Keine Tabellenkalkulations-Oberfläche.** Auf Nachfrage klargestellt,
  wörtlich: *„und mit excel war gemeint wie excel, wir müssen noch keine excel
  oberfläche ui bauen!"* ADR-016 bleibt „Bauform offen bis zum Spike". Was von
  ADR-016 **jetzt schon** gilt, ist seine Regel, nicht sein Bildschirm: eine Zahl
  kommt nur durch, wenn sie ihre Herkunft mitliefert.
- **Nicht, wie die Beschreibung inhaltlich aussieht.** Das Feld existiert ab B1,
  seine Form wird bei B4 am ersten echten Bildschirm entschieden — gemessen statt
  vermutet. `kern/baustein.py` (`absatz`, `ueberschrift`, `tabelle`, `grafik`,
  `feld`) ist dabei Kandidat, aber **ungemessen**: er ist der Dokument-Vertrag aus
  ADR-010, nicht als Bildschirmsprache erprobt.
- **Nicht, wann die Weboberfläche kommt.** Sie ist zugesagt als möglicher
  weiterer Schritt, nicht terminiert.

## Preis

Die native Zeichenfläche muss jedes Bedienelement lernen, das eine Domäne
braucht — das ist Arbeit an der Trägerschicht, nicht an der Domäne (schon in
ADR-013 als Preis benannt). Neu hinzu kommt: **openlehrs vorhandene
Webbildschirme sind damit endgültig nur noch Blaupause.** Sie zeigen, was ein
Bildschirm können muss; sie werden nicht ausgeliefert. Das ist bewusst der
teurere Weg zum ersten Bildschirm und der billigere zum zweiten Zeichner.

## Woran sich der Erfolg messen lässt

Ein zweiter Zeichner (Web) kann später gegen dieselbe Beschreibung gebaut
werden, ohne dass ein einziges Feld des Manifests geändert wird. Prüfbar schon
vorher, ohne den zweiten Zeichner: der Manifest-Prüfer lehnt jede Beschreibung
ab, die eine Bauform nennt — und ein Test belegt, dass er es tut.
