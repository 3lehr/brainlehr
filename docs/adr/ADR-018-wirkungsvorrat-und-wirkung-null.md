# ADR-018: Die Trennlinie heißt Wirkungsvorrat und Wirkung Null — nicht „Daten gegen Code"

**Stand** 2026-08-14T21:36:26+0200
**Status** Angenommen
**Betrifft** ADR-011 bis ADR-017, `kern/domaene.py`, `kern/belegvertrag.py`, das atelier
**Entscheider** Betreiber, 2026-08-14 (Konsil aus drei unabhängigen Linsen)
**Ersetzt** die **Begründung** von ADR-012, nicht dessen Ergebnis

## Anlass

Der Betreiber: *„nun sind wir doch wieder bei schwerwiegenden
Architekturentscheidungen? kleines 3er Opus-Konsil?"* — und davor der Einwand,
der es auslöste: *„das atelier ist noch nicht wirklich ein Betriebssystem, und
sobald Makro-Code in die Datenbank kommt …"*

Drei Linsen, unabhängig, keine kannte die Antwort des Auftraggebers: **Angreifer**
(kannte die Entscheidungen nicht) · **Durchsetzbarkeit** (Sperre oder Merkmal) ·
**Trennlinie** (trägt „Wissen tut nichts" noch, wenn Wissen rechnen darf).
Sie sind zu verschiedenen Ergebnissen gekommen — die Frage war nicht suggestiv.
Wo sie sich treffen, treffen sie sich aus verschiedenen Richtungen.

## Der Befund: die Trennung trägt als Kostengrenze, nicht als Sicherheitsgrenze

ADR-012 begründet die freie Weitergabe mit: *„es kann nichts ausführen, also
muss ihm niemand vertrauen."* **Dieser Satz ist vom eigenen Code widerlegt** —
und zwar von dem Code, der Regeln bereits verteilt.

`kern/regelpaket.py` verteilt Regeln als reine Daten. Wäre „Daten können nichts
tun" die tragende Begründung, wäre sein dritter Teil überflüssig. Stattdessen ist
er der sorgfältigst begründete Teil der Datei: Ein Import schreibt
`norm_rang = NULL` und `norm_entscheidung='keine_norm'`, weil
`rangfolge.norm_score(None) == 0.0` und die Trigger in `schema.sql` Rang 1/2 ohne
menschlichen Entscheider abweisen. Der Selbsttest fährt beide Richtungen. Die
Datei sagt die richtige Linie selbst, wörtlich:

> *„sie kommt nie hoeher herein als ‚keine Wirkung', und alles darueber ist ein
> Willensakt eines Menschen HIER"*

**Das ist keine Daten-gegen-Code-Grenze. Das ist eine Wirkungsgrenze.** Das
System hat die richtige Linie längst gezogen — an einer Stelle, unter anderem
Namen, und ADR-012 hat daneben eine falsche behauptet.

## Die zwei Achsen, beide prüfbar

**Achse A — Wirkungsvorrat: Wem gehört die Menge der möglichen Wirkungen?**
Geprüft wird **am Leser**, nicht am Artefakt. Ein Leser darf frei Empfangenes
verarbeiten, wenn seine Wirkungsmenge endlich aufzählbar ist **und er sie
veröffentlicht**. `json.loads` erfüllt das. Eine Positivliste in der
Tabellenkalkulation erfüllt es — und ADR-016 forderte sie bereits, ohne zu
benennen, dass die Liste dem **Empfänger** gehört. `eval`, `dlopen`, `import`
erfüllen es nicht: dort bestimmt der Absender.

Damit bleibt „Formeln ja, Makros nein" richtig — aber die Begründung ist eine
andere und trägt: nicht *rechnet gegen ruft*, sondern **wem der Wirkungsvorrat
gehört**.

**Achse B — Wirkung Null: Kommt der Inhalt wirkungslos an?** Frei reisen darf
nur, was ohne Wirkung eintrifft und erst durch einen **Willensakt eines Menschen
der Zielinstanz** wirksam wird. Prüfbar als Spalte: `norm_rang IS NULL` beim
Schreiben, Wirksamwerden nur über die bestehende Schranke. **Existiert, ist
getestet, ist in Betrieb — und fehlt in `kern/domaene.py`.**

**Beide sind nötig.** A allein lässt eine mechanisch harmlose, aber belegt
aussehende Falschregel durch. B allein macht ein Makro nicht ungefährlich.

## Was gemessen wurde, und es korrigiert mich an drei Stellen

**1. „Wir sind das Betriebssystem" ist falsch, und zwar messbar.**
`codesign -dv` auf das gebaute atelier: `flags=0x2(adhoc)`,
`TeamIdentifier=not set`, kein Entitlement-Block — **die App-Sandbox ist nicht
aktiv**. Das atelier ist eine unsignierte Anwendung in fremder Umgebung, also
genau die Lage, gegen die ADR-017 argumentiert hat. Der **Beschluss** (Bedingung
an die Identität statt an die Datei) bleibt richtig; die **Begründung** war es
nie.

**2. Fast alles ist Merkmal, nicht Sperre.** Kern, Ausweis, Mandat und Widerruf
liegen in Dateien, die derselbe Benutzer schreiben darf, den sie einschränken
sollen. `kern/ausweis.py::selbstbedienung_moeglich` sagt das **selbst** — und
steht als Diagnose da, nicht als Schranke. Die einzige heute wirksame Grenze ist
kernel-erzwungen: die Bindung auf `127.0.0.1`.

**3. Der Belegvertrag beweist sich selbst.** Die Quellen kommen aus **derselben
Paketdatei** wie die Regeln. Gemessen: ein Paket mit erfundener Quelle und
wörtlich passender Fundstelle wird angenommen. Der Belegvertrag ist eine
**Selbstkonsistenzprüfung**, keine Vertrauensprüfung — und ADR-011 hat ihm eine
Last aufgeladen, die er nicht trägt.
*(Der zweite Fund derselben Linse — die leere Fundstelle galt als Beleg — ist
behoben und mit Rot-Probe abgesichert.)*

## Der Preis, und die unbequemste Folge

- **Die Prüflast wandert vom Paket zum Leser.** Jeder Leser muss seinen
  Wirkungsvorrat aufzählen und veröffentlichen.
- **Und damit ist der Web-Weg aus ADR-013 die nachgiebigste Stelle des ganzen
  Entwurfs** — nachgiebiger als die Tabellenkalkulation. Ein Browser ist ein
  Leser mit **nicht aufzählbarem** Wirkungsvorrat. Unter der alten Linie war das
  unsichtbar, weil HTML dort als „Beschreibung, kein Code" geführt wurde. Diese
  Einordnung fällt.
- **Der billige Satz stirbt.** „Wissen braucht kein Vertrauen" war ein
  Verkaufsargument; an seine Stelle tritt eine Zusage, die der Empfänger halten
  muss.

## Bindende Reihenfolge

> **Achse B steht für Domänenpakete, BEVOR `kern/domaene.py` das erste Mal
> etwas speichert.**

Der Grund ist die Reihenfolge, nicht die Menge: Danach existiert Bestand ohne
Rangdisziplin, und das gilt bei null Zeilen wie bei einer Million. Heute
speichert `domaene.py` nichts — das Fenster ist offen und schließt sich mit dem
ersten Schreibvorgang.

## Was daraus folgt

- **ADR-012** behält sein Ergebnis, bekommt diese Begründung.
- **ADR-011, ADR-013, ADR-016** erben sie; ADR-013 verliert die Einordnung
  „HTML ist Beschreibung".
- **ADR-017** ist deren **erste Anwendung**, kein Sonderfall.
- **ADR-016** behält „keine Makros", jetzt mit tragfähigem Grund.
