# ADR-012: Verteilung — Wissen reist, Werkzeug wird installiert

**Stand** 2026-08-14T21:36:26+0200
**Status** Angenommen
**Betrifft** `brainlehr`, `atelier`, jede Domäne, jeder künftige Nutzer
**Entscheider** Betreiber, 2026-08-14

## Die Frage, wörtlich

> *„ja aber was ist mit dem ganzen code? wenn das system einmal läut sollten wir
> es für andere brainlehr user weiter verteilen können!"*

**Sie hebt eine Verwerfung aus ADR-011 auf, und das gehört hierhin statt in eine
Fußnote.** Dort stand, eine Lieferform für brainlehr sei gegenstandslos — „es
wird nichts importiert, es wird gerufen". Das gilt, **solange der Dienst auf
demselben Rechner liegt**. Bei einem zweiten Nutzer liegt er dort nicht. Eine
angemeldete Fähigkeit, die niemand installiert hat, ist keine Fähigkeit.

## Die Entscheidung

Eine Domäne wird als **zwei Dinge mit zwei verschiedenen Vertrauensstufen**
weitergegeben — und die Trennung ist die Sicherheitsgrenze, nicht eine
Ordnungsfrage:

| | was es ist | wie es reist | was es kostet |
|---|---|---|---|
| **Wissenspaket** | Daten: Regeln, Quellen, Fundstellen | frei — Datei, Netz, Weitergabe unter Nutzern | nichts. Es kann nichts ausführen, also muss ihm niemand vertrauen |
| **Werkzeug** | ein Programm (der Fachdienst) | **installiert**, mit eigener ausdrücklicher Zustimmung und geprüfter Herkunft | Vertrauen. Deshalb nie nebenbei |

**Der Satz, der die Grenze trägt:** Ein Dokument öffnen ist nicht dasselbe wie
ein Programm installieren. Der Menüpunkt „Domäne importieren" darf **niemals**
das Zweite nebenbei erledigen — sonst ist er genau das Einfallstor, gegen das
ADR-011 „ein Paket ist Daten" festgeschrieben hat.

Findet der Import ein Wissenspaket, das ein Werkzeug **verlangt**, das hier
nicht installiert ist, dann übernimmt er das Wissen und **sagt**, was fehlt. Er
lädt nichts nach. Die Installation ist ein eigener Weg mit eigener Zustimmung.

## Was daraus für die Reihenfolge folgt

Verteilung ist **nicht jetzt zu bauen** — das System läuft noch nicht, und der
Betreiber sagt selbst *„wenn das system einmal läuft"*. Aber drei Dinge sind
**heute** billig und später teuer, und nur deshalb stehen sie hier:

1. **Keine maschinengebundenen Angaben in Paket und Dienst.** Ein absoluter
   Pfad, ein fester Port, ein Verweis auf ein Verzeichnis dieses Rechners macht
   jedes weitergegebene Paket beim Empfänger falsch. *Geprüft: das erste Paket
   (`pakete/steuer.domaene.json`) enthält null absolute Pfade; `herkunft` ist
   repo-relativ. Der Stand ist also heute sauber und soll es bleiben.*
2. **Das Manifest bekommt den Platz für die Werkzeugherkunft von Anfang an** —
   Name, Bezugsquelle, Prüfsumme. Auch wenn das Feld heute leer bleibt. Ein
   Format nachträglich um ein Pflichtfeld zu erweitern heißt, jedes bereits
   verteilte Paket ungültig zu machen.
3. **Die Dienstgrenze ist `127.0.0.1` plus Nachweis**, bevor irgendetwas
   verteilt wird. Wer einen offenen Port mitverteilt, verteilt ihn an alle.
   *Ausdrücklich nicht gemessen: wie Port 4242 heute gebunden und angemeldet
   ist. Vor dem ersten Auslieferungsversuch nachsehen.*

Der Grund für alle drei ist **die Reihenfolge, nicht die Menge**: Sie müssen
stehen, bevor das erste Paket den Rechner verlässt — danach sind sie nicht mehr
einzuholen, weil fremde Kopien existieren.

## Was das für openlehr heißt

Damit openlehr/steuer je bei einem anderen Nutzer läuft, braucht es eine
**Auslieferungsform**, die es heute nicht hat: ein installierbares Bündel.
Welche (Python-Paket, Container, App-Bündel) ist hier **nicht** entschieden —
die Frage wird beantwortet, wenn ein zweiter Nutzer tatsächlich ansteht, und
dann gegen dessen Rechner, nicht gegen eine Vermutung.

Was hier entschieden ist: **Diese Form ist nicht der Importknopf, und sie ist
nicht das Wissenspaket.** Wer beides vermischt, hat entweder ein Wissenspaket,
dem man vertrauen muss, oder eine Installation, die niemand bemerkt hat.

## Verworfen

- **Alles in ein Paket** (Wissen + Code in einer Datei). Verworfen: dann trägt
  jedes Wissenspaket das Vertrauensniveau eines Programms, und die billige,
  freie Weitergabe von Wissen — der eigentliche Wert — wäre verloren.
- **Nachladen aus einer Bezugsquelle beim Import.** Verworfen: Bequemlichkeit,
  die aus dem Importknopf einen Installationsknopf macht, den niemand als
  solchen liest.
- **Verteilung jetzt bauen.** Verworfen: Es gibt keinen zweiten Nutzer, und
  eine Auslieferungsform ohne Empfänger wird gegen eine Vermutung gebaut. Die
  drei Vorkehrungen oben genügen, um die Tür offen zu halten.

## Preis

Ein zweiter Nutzer bekommt das Wissen sofort und die Fähigkeiten erst nach einer
Installation, die er selbst auslöst. Das ist mehr Reibung als „ein Klick, alles
da" — und diese Reibung ist der bezahlte Gegenwert dafür, dass ein
Wissenspaket ungefährlich bleibt.
