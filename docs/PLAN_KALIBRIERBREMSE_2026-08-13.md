# Kalibrierbremse: verdrahten oder ausbauen

Stand 2026-08-13T02:00:00+0200. Aufgabe 35. Kurzer Plan, weil eine Entscheidung
mit echten Alternativen ansteht und delegiert wird.

## Der gemessene Ist-Stand

| | Befund |
|---|---|
| Aufruf | `query()` ruft `_effective_noise_mult(None, project_counts)` mit **hartcodiertem** `project_id=None` |
| Wirkung | Die Schwellenprüfung erreicht damit **kein einziges Projekt** — die Bremse greift nie |
| Selbstauskunft | Der Docstring sagt es selbst: „HERKUNFT NOCH NICHT VERDRAHTET" |
| Übersteuerungstabelle | `PROJECT_NOISE_OVERRIDES` ist **leer** und trägt den Vermerk „GERATEN, NICHT GEMESSEN" |
| Belegt seit | Commit `1711f01`, im Selbsttest als Widerspruch sichtbar |

## Die Alternativen

**A — Herkunft verdrahten.** Das Arbeitsverzeichnis auf eine Projektkennung
abbilden, damit die Schwellenprüfung ein Projekt sieht. **Bedingung, ohne die
das nicht gemacht wird:** Die Übersteuerungswerte müssen vorher **gemessen**
sein. Sonst wirkt ab dem ersten Tag eine geratene Zahl auf den Abruf — und
niemand merkt es, weil eine wirkende Bremse genauso aussieht wie eine richtige.

**B — Ausbauen.** Bremse und Tabelle entfernen. Eine fertige, getestete, nie
aufgerufene Struktur ist Ballast, der beim nächsten Lesen für wirksam gehalten
wird. Genau diese Fehlerklasse ist heute neunmal gemessen worden.

**C — Stehenlassen wie sie ist.** Abgelehnt, ausdrücklich. Sie sieht dann
weiter aus wie ein Schutz, den es nicht gibt.

## Die Entscheidungsregel statt einer Vorentscheidung

Es wird **nicht vorab** gewählt. Zuerst wird eine Frage beantwortet, und sie
entscheidet:

> **Lässt sich der Schwellenwert je Projekt aus dem vorhandenen Bestand
> messen — oder müsste er geraten werden?**

Messbar → **A**, und die gemessenen Werte kommen mit in denselben Schritt.
Nicht messbar → **B**, weil eine Bremse ohne Skala dieselbe leere Behauptung
wäre wie ein Rang ohne Einheit, gegen den heute eine Sperre gebaut wurde.

## Was bewusst nicht getan wird, samt Preis

- **Kein Schätzwert als Zwischenlösung.** Preis: Bei B ist die Arbeit von
  damals weg. Gewinn: keine Zahl im Abruf, die niemand herleiten kann.
- **Kein Umbau des Abrufpfads über diese Frage hinaus.** Der Pfad wurde gerade
  gemessen; jede weitere Änderung dort macht die Nullmessung unvergleichbar.

## Woran sich Erfolg misst

- Die Frage oben ist mit **Zahlen** beantwortet, nicht mit einer Einschätzung.
- Bei A: rot vor grün — ein Fall, in dem die Bremse greifen **muss**, war
  vorher rot. Und ein Negativfall, in dem sie **nicht** greifen darf.
- Bei B: Die Suite bleibt grün, und kein Aufrufer bleibt zurück — gezählt, nicht
  vermutet.
- In beiden Fällen: Der Selbsttest widerspricht sich danach nicht mehr selbst.
