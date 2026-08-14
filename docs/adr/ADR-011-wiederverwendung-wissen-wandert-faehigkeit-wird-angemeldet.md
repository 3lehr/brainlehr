# ADR-011: Wiederverwendung — Wissen wandert als Paket, Fähigkeit wird angemeldet, Gerüst bleibt liegen

**Stand** 2026-08-14T21:36:26+0200
**Status** Angenommen
**Betrifft** `brainlehr`, `atelier`, `openlehr`, jede künftige Instanz
**Entscheider** Betreiber, 2026-08-14 — Anlass war seine Frage

## Die Frage, wörtlich

> *„ja aber alles was schon fertig vorliegt und getestet ist können wir ja
> wiederverwenden? wir müssen es nur richtig verpacken. eigentich ist das eine
> große architektur frage?"*

Ja. Und sie war bis hierher nur zur Hälfte beantwortet: Der Menüpunkt „Domäne
importieren" (Linie H, H8) verpackt **Wissen**. Er verpackt keine einzige der
gebauten **Fähigkeiten** — Texterkennung, Bankabgleich, E-Rechnung, PDF-Satz,
Dublettensuche. Genau die sind aber der Grund, warum es sich lohnt.

## Gemessene Lage (2026-08-14, nicht geschätzt)

- `apps/openlehr/daemon/steuer/`: **128** `.py`, **43 237** Zeilen. **0 tote
  Module** — 121 verdrahtet, 7 nur von Tests erreicht.
- **121 Testdateien**, deren Pfad `steuer` enthält.
- Die vier größten Dateien sind Gerüst: `router.py` 5841, `api.py` 5662,
  `db.py` 2526, dazu `ingest.py` 2404.

**Eine Einschränkung gehört zum „und getestet" dazu**, einmal gesagt und nicht
wiederholt: Gemessen wurde, dass die Tests **existieren**, nicht dass sie den
Fehler fangen würden. `L-473ba2` ist der Gegenbeleg aus demselben Repo — 386
jsdom- und über 300 pytest-Tests standen grün neben einem Rechnungschreiben,
das aus der Oberfläche heraus tot war. „Getestet" heißt hier: es gibt einen
Test. Ob er trägt, entscheidet sich beim ersten echten Durchlauf.

## Die Entscheidung: drei Verpackungen, und die Sorte entscheidet, nicht der Ort

| Sorte | Beispiele | Verpackung |
|---|---|---|
| **Wissen** | Zuordnungsregeln mit Fundstelle, Formularkatalog, Belegkategorien, Rechtssätze | **Datenpaket** (`*.domaene.json`), wird beim Import gegen den Belegvertrag geprüft. Niemals Code. |
| **Fähigkeit** | Texterkennung, Bankabgleich, E-Rechnung, PDF-Satz, Dublettensuche, Plausibilität | **Angemeldet, nicht umgezogen.** Das Manifest nennt Namen, Aufrufweg und Zusage. Der Code bleibt, wo er ist. |
| **Gerüst** | Routen, Serialisierung, Ablage, alte Oberfläche | **Bleibt liegen.** Wird nicht wiederverwendet und nicht umgezogen. |

**Der Kern in einem Satz:** Wissen wird *übernommen*, eine Fähigkeit wird
*gerufen*. Nur Wissen kann geprüft werden, indem man es liest — eine Fähigkeit
kann man nur an dem prüfen, was sie zusagt.

Das ist keine neue Idee, sondern ADR-007 zu Ende gelesen. Dort steht die
Vorgabe des Betreibers wörtlich: *„vorgefertigtes valides ki wissen + werkzeug
um das wissen einzusetzen. in welcher form auch immer das werkzeug dann ist"* —
**Wissen und Werkzeug sind dort bereits zwei Dinge.** Diese ADR sagt nur, dass
sie deshalb auch zwei Verpackungen brauchen.

## Die Zusage, ohne die eine Fähigkeit nicht angemeldet wird

Eine angemeldete Fähigkeit läuft in fremdem Code, den der Belegvertrag nicht
durchdringt. Deshalb genau eine Auflage, und sie ist prüfbar:

**Eine Fähigkeit muss ihr Nichtwissen ausdrücken können.** Wer „das ist eine
Rechnung" sagen kann, muss auch „ich weiß es nicht" sagen können. Wer eine Zahl
liefert, liefert ihre Herkunft mit. Kann eine Fähigkeit das nicht, wird sie
nicht angemeldet — sie wird vorher darum ergänzt.

Der Maßstab dafür ist gemessen und liegt im Code: `euer_zuordnung.py` macht aus
einem Widerspruch `None` statt `False`, `classifier.py` kennt den Ausgang
`unklar`. Die Zusage verlangt also nichts Neues, sie macht das Vorhandene zur
Bedingung.

## Verworfene Wege

**Alles umziehen.** 43 237 Zeilen nach unten holen. Verworfen: Bei 0 toten
Modulen zieht man die Altlast mit um, nicht statt ihrer — und Tests, die an
ihrer Umgebung hängen, verlieren beim Umzug genau die Aussage, derentwegen man
sie behalten wollte.

**Alles nur per Schnittstelle rufen, ohne Manifest.** Verworfen: Dann weiß
brainlehr nicht, was eine Fähigkeit zusagt, und die Belegpflicht endet an der
Prozessgrenze. Ein Dienst, der ungefragt eine Zahl ohne Herkunft liefert, ist
schlimmer als gar keiner, weil die Zahl belegt aussieht.

**Code als Domänenpaket nachladen.** Verworfen und ausdrücklich verboten: Ein
Paket, das ausführbaren Code trägt, macht den Importknopf zum Einfallstor. Ein
Paket ist Daten.

**Eine Paketform für brainlehr bauen** (`pyproject.toml`), damit openlehr die
Module importieren kann. Verworfen, weil durch diese Entscheidung
gegenstandslos: Es wird nichts importiert. Die Frage kehrt erst wieder, wenn
brainlehr selbst ausgeliefert wird.

## Der Preis, benannt

- **Zwei laufende Prozesse.** openlehr bleibt ein eigener Dienst; das atelier
  ruft ihn. Ist er nicht da, fehlt die Fähigkeit — und das muss der Bildschirm
  sagen, ohne den Nutzer nach einem Prozess zu fragen.
- **Die Zusage ist eine Behauptung, bis sie geprüft ist.** Eine angemeldete
  Fähigkeit trägt ihren eigenen Prüffall, sonst ist die Anmeldung Papier.
- **Zwei Orte für Fachwissen.** Solange Regeln in openlehr stehen *und* als
  Paket importiert sind, gibt es zwei Wahrheiten. Aufgelöst wird das nur in
  eine Richtung: Das Paket wird aus dem Code **erzeugt**, nie von Hand gepflegt.

## Folgen

- Linie H, H8: Das Manifest bekommt einen zweiten Abschnitt `faehigkeiten` —
  Name, Aufrufweg, Zusage. **H9** wird die erste angemeldete Fähigkeit; welche,
  entscheidet der erste echte Durchlauf, nicht diese ADR.
- Die Belegpflicht (H1–H3) bleibt davon unberührt: Sie gilt für Wissen, und
  Wissen wandert.
- `ADR-007` wird nicht geändert. Diese Entscheidung liest ihn nur aus.
