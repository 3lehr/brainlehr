# ADR-004: Die Anzeige wächst mit der Fläche — eine Mechanik für alle Lagen

**Stand** 2026-08-13T16:22:00+0200
**Status** Angenommen
**Betrifft** brainlehr `app/`, buckeberg `homepage/`
**Ersetzt** den ersten Entwurf dieser ADR („Kein Multiview für den Termin") — vollständig, siehe „Warum der erste Entwurf falsch war"

## Warum der erste Entwurf falsch war

Der erste Entwurf schloss aus fünf Konsil-Messungen: *kein Multiview*. Der
Betreiber hat ihn mit einem Satz erledigt:

> *„zu punkt eins und generell! die app muss alle scenarien tragen nicht nur das
> morgige!"*

Er hat recht, und der Fehler ist benennbar: **Ich hatte die Bauform der App an
genau einem Termin gemessen** — ein eingebauter Bildschirm, 346 mm breit, 2 m
Abstand — und aus dem Ergebnis eine Aussage über die App gemacht. Für diesen
einen Fall stimmte die Rechnung. Als Aussage über ein Werkzeug, das danach
weiterlebt, war sie falsch.

Das ist dieselbe Verwechslung, die in den Hausregeln unter „Aufwandsfrage statt
Ergebnisfrage" steht, nur eine Ebene höher: Ich habe eine **Lagefrage** („trägt
dieser Schirm das?") als **Bauformfrage** („ist diese Bauform richtig?")
beantwortet.

Die Korrektur ist nicht, das Ergebnis umzudrehen. Sie ist, **die Zahl aus dem
Dokument zu nehmen und in eine Funktion zu stecken**, die man mit der nächsten
Lage erneut aufruft: `app/werkzeuge/lesbarkeit.py`.

## Die Lagen, die zu tragen sind

Vom Betreiber genannt, nicht ausgedacht: Einzelplatz allein · zwei
Bildschirmansichten im Büro der Stadtwerke oder der Zahnakademie · Termin mit
großem 4K-Fernseher als Zweitmonitor bei 1,5 m.

Gerechnet mit `lesbarkeit.py` gegen den gemessenen Bestand (Fließtext Median
10,9 pt, x-Höhe 0,547 je Punkt, an 29 Quellen-PDFs vermessen):

| Lage | Zoll | Abstand | volle A4-Seiten |
|---|---|---|---|
| Einzelplatz, Laptop | 14 | 0,6 m | **0** |
| Büro, ein 27-Zoll | 27 | 0,7 m | **0** |
| Büro, 32-Zoll 4K | 32 | 0,8 m | 2 |
| Termin, 55-Zoll TV | 55 | 1,5 m | **0** |
| Termin, 65-Zoll TV | 65 | 1,5 m | **2** |
| Termin, 75-Zoll TV | 75 | 1,5 m | 3 |
| Vortrag, 85-Zoll | 85 | 2,5 m | **0** |

**Zwei Dinge daran entscheiden die Bauform, und beide sind kontraintuitiv:**

1. **Die Sprünge sind nicht sanft.** 55 Zoll trägt null Seiten, 65 Zoll trägt
   zwei. Der Engpass ist die **Höhe**, nicht die Breite: eine A4-Seite braucht
   bei 1,5 m rund 739 mm, ein 55er ist 685 mm hoch, ein 65er 809 mm. Eine fest
   verdrahtete Feldzahl wäre in fast jeder Lage falsch — und zwar nicht ein
   bisschen, sondern um alles.
2. **Der Einzelplatz trägt nie eine volle Seite.** Weder 14 Zoll bei Armlänge
   noch ein einzelner 27-Zöller im Büro. Das ist die häufigste Lage von allen,
   und in ihr ist „eine Seite zeigen" grundsätzlich das falsche Ziel.

## Entscheidung

**Die Anzeigeeinheit ist nicht fest. Sie folgt aus der verfügbaren Fläche und
dem eingestellten Abstand, und die App rechnet sie aus.**

| verfügbare Fläche | was gezeigt wird |
|---|---|
| trägt < 1 Seite | **Ausschnitt**: die Fundstelle groß, mit je einem Satz Kontext davor und dahinter, dazu ein bewusst unlesbares Seitenbild mit Positionsbalken |
| trägt 1 Seite | **die volle Seite**, an der Stelle aufgeschlagen und markiert |
| trägt ≥ 2 Seiten | **nebeneinander** — das Multiview, und hier trägt es |

Damit ist das Vorbild des Betreibers nicht verworfen, sondern **eingeordnet**:
Der Vorschaumonitor ist die Form, die ab zwei tragfähigen Feldern greift. Auf
dem Laptop wäre er leer, auf dem 65-Zöller ist er richtig.

**Drei Auflagen, die aus den Messungen folgen:**

- **Keine Feldzahl in der Konfiguration.** `raster.json` beschreibt, *was* in
  ein Feld darf, nie *wie viele* Felder es gibt. Die Zahl kommt aus der
  Rechnung. Der Nutzer darf sie übersteuern — dann ist es sein dichter Modus,
  und der trägt die AA-Aussage getrennt.
- **Der Abstand ist eine Einstellung, kein Messwert.** Kein Gerät weiß, wie
  weit jemand wegsitzt. Voreinstellung 0,7 m für den eingebauten Schirm, 1,5 m
  für einen zweiten großen — beides sichtbar und änderbar.
- **Ausschnitt heißt Auswahlmacht, und die wird gekennzeichnet.** Ein Satz ohne
  seinen „es sei denn"-Nachsatz ist überzeugender als jede Vorschau und kann
  falsch sein. Nie weniger als der volle Satz plus Nachbarsätze; die Karte
  trägt sichtbar, dass sie ein Ausschnitt ist; ein Handgriff öffnet die volle
  Seite.

## Alternativen, samt Ablehnungsgrund

| Weg | Abgelehnt weil |
|---|---|
| **Feste Rasterzahl** (3×3 wie ATEM) | Trägt in genau einer der sieben gerechneten Lagen. Der Sprung 55 → 65 Zoll zeigt, dass die richtige Zahl nicht ratbar ist. |
| **Nur Ausschnitt** (Belegkarte überall) | Verschenkt auf dem 65-Zöller die Fläche, die den Vergleich zweier Dokumente erst möglich macht — und der ist bei WEG-Fragen der halbe Streit. |
| **Nur volle Seite** | Auf dem Einzelplatz, der häufigsten Lage, unlesbar. |
| **Zwei getrennte Oberflächen** (Laptop-App und TV-App) | Doppelte Pflege für eine Unterscheidung, die eine Funktion trifft. Und der Zweitmonitor kommt und geht während derselben Sitzung. |

## Was das kostet

- **Drei Darstellungsformen statt einer**, jede mit eigener Prüfung. Der Preis
  ist echt; er ist der Preis dafür, dass die App nicht nur morgen funktioniert.
- **Die Rechnung stützt sich auf eine Schwelle aus Modellwissen** (0,2°
  Sehwinkel für flüssiges Lesen). Sie ist deshalb ein Parameter, und
  `--tabelle` gibt drei Stufen aus, damit sichtbar bleibt, wie stark das
  Ergebnis daran hängt. Bei der mittleren Stufe trägt der 27-Zöller drei
  Felder statt null — die Schwelle ist der unsicherste Teil der ganzen ADR.
- **Der Zweitbildschirm ist auf diesem Rechner nicht prüfbar.** Der
  Plattformprüfer konnte einen virtuellen Schirm erzeugen (`displayID=7`,
  Online-Liste stieg von 1 auf 2), aber ohne Modus veröffentlicht der
  Fenstermanager ihn nicht; die Berechtigung `com.apple.developer.virtual-display`
  braucht ein echtes Provisioning-Profil, ad-hoc signiert endete der Prozess
  mit SIGKILL. **Der Code-Pfad ist prüfbar** (`NSWindow(…screen:)`,
  `window.screen ==`), die Darstellung darauf nicht. Das ist eine Grenze meines
  Aufbaus, keine der Plattform, und sie wird als Handprobe am echten Fernseher
  ausgewiesen.

## Was unabhängig davon gilt

**Für den Termin morgen ist die App nicht der Weg** — nicht weil sie falsch
wäre, sondern weil zwei billigere Dinge davor liegen und ohne sie jede Anzeige
leer bleibt:

- **Schritt A ist erledigt** (buckeberg 9a7848da6): Der pdf.js-Betrachter war
  tot, `vendor/pdfjs-viewer/build/` fehlte wegen `.gitignore` Zeile 21.
  Belegt am laufenden `dist/`: vorher HTTP 404 und graue Fläche, jetzt Seite 2
  aufgeschlagen, 1 Treffer, 1 markierte Stelle. Dazu `ANZAHL_QUELLEN` von fest
  verdrahteten 45 auf die abgeleiteten 48 — [46], [47], [48] waren nicht
  erreichbar, obwohl das Dossier [47] und [48] zitiert.
- **Schritt B steht aus**: 19 der 20 HTML-Quellen tragen ihre Stelle bereits im
  Klartext im Feld `kurz` („§ 16 Abs. 2 Satz 2 WEG …"), nur im falschen Feld.
  Das hebt die markierbaren Quellen von 14 auf bis zu 33 von 48 — und es ist
  Datenpflege, keine Software.

`kern/fundstelle.py` und die beiden Datenendpunkte bleiben unverändert gültig:
sie beantworten „wo steht das" oder sagen, dass sie es nicht wissen.

## Nachtrag: die Referenz gelesen, nachdem gemessen war

Die parallele Sitzung mahnte an, die Apple-Referenz zu lesen statt sich auf
Modellwissen zu verlassen — mit einem eigenen Beleg: Sie hatte zehn
Claude-Code-Haken-Ereignisse für vollständig gehalten, die Referenz nennt 29.

Nachgelesen. **Sie bestätigt jede gemessene Aussage punktgenau**, auch die
unbequeme: `QLPreviewView` kennt nur `previewItem`, `displayState` und
`refreshPreviewItem` — kein Aufschlagen, kein Suchen, kein Hervorheben, und
ausdrücklich kein Fehler-Delegate. Die Referenz empfiehlt selbst, das Format
vorher zu prüfen. Eine gemessene Aussage ist damit nicht schwächer als die
Referenz, sondern stärker: sie gilt für die Fassung, die auf dem Rechner liegt.

**Und trotzdem hat die Mahnung getragen, an genau ihrer Stelle.** Die Referenz
nennt `PDFMarkupType.redact` — danach hätte keine Messung gesucht, weil es in
keinem Auftrag stand. Das ist die Lücke, die eine Messung strukturell nicht
schließt: Sie prüft die Fälle, die der Messende schon kennt.

**Die Falle darin, ungeprüft und deshalb hier als Warnung:** Eine
Redaktions-Anmerkung ist bei PDF zunächst nur eine *Anmerkung* — ein schwarzes
Rechteck über weiterhin vorhandenem Text. Für ein Repo mit WEG-Rechtsfällen und
Namen Dritter ist das keine Randnotiz. Wird je eine Schwärzung gebaut, gilt sie
erst als erfüllt, wenn `pdftotext` den Namen **nicht mehr** findet — vorher
findet er ihn, nachher nicht. Alles andere ist Anstrich, der wie Schutz
aussieht. Festgehalten als Knoten `201381b4`.

## Nachtrag zur Arbeitsweise

Der erste Entwurf dieser ADR war **methodisch sauber und im Ergebnis falsch**.
Fünf unabhängige Rollen, jede Zahl nachgerechnet, jede Alternative mit
Ablehnungsgrund — und trotzdem eine Aussage über die App, die nur für einen
Nachmittag galt.

Was gefehlt hat, war keine weitere Prüfung, sondern **die Frage, wie viele
Lagen die Sache überhaupt hat**. Sie stand in keiner der fünf Rollen, weil ich
sie in keinen Auftrag geschrieben hatte: Alle fünf haben den Termin geerbt,
weil mein Auftrag ihn nannte. Ein Konsil prüft die Frage, die man ihm stellt —
es findet nicht die Frage, die man hätte stellen sollen.
