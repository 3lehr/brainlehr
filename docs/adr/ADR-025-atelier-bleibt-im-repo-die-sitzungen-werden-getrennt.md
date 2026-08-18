# ADR-025: Das atelier bleibt im Repo — getrennt werden die Sitzungen, nicht die Repos

**Stand** 2026-08-18T05:35:00+0200
**Status** Angenommen
**Betrifft** `atelier` (`app/`), jede Sitzung, die an der Naht Python↔Swift arbeitet
**Entscheider** Betreiber, 2026-08-18

> **Nicht zu verwechseln:** Ältere Dokumente verweisen auf „ADR-025/026", die es nie
> gab (`docs/REQUIREMENTS_BRAINLEHR.md`, `BDW-C01`). Dieser Text ist **nicht** deren
> Nachfolger; die Lücke bleibt eine Lücke, sie wird hier nicht gefüllt.

## Die Frage

> *„gehört diese nun hier in den brainlehr arbeitsbereich oder sollten wir einen
> eigenen worktree dafür anlegen?"*

und nach der Vorlage der Messung:

> *„genauso machen wir es, setzte deine vorschläge um!"*

## Entscheidung

1. **Ein Repo.** Das atelier bleibt die Swift-App unter `app/` in brainlehr.
2. **Getrennte Arbeitsbäume und Sitzungen.** Wer am atelier arbeitet, tut das im
   Arbeitsbaum `/Volumes/daten/Begod2026/atelier` auf dem Zweig `brainlehr/atelier`.
3. **Kein dauerhafter Bau-Arbeitsbaum.** Gebaut wird dort, wo gearbeitet wird.

## Warum kein zweites Repo

Genau am 2026-08-18 gemessen: Ein Sonnet-Subagent erweiterte den Rückgabewert von
`speichere()` um `aktualisiert` (`INT-UPD-001`). Die Swift-Seite las weiterhin nur
`gespeichert` und hätte einem Menschen bei einem Aktualisierungs-Import gemeldet
„enthielt nichts Neues" — während gerade eine korrigierte Fachregel einlief
(`L-51e6d8`). In **einem** Repo fällt so etwas in **einen** Testlauf. In zwei Repos
liefe es über eine Repo-Grenze, und wie zuverlässig solche Läufe übersprungen werden,
zeigt `INT-GATE-001`: dort skippte der Cross-Repo-Test, sobald der Gegenpfad fehlte.

Zahlen zur Größe: 74 getrackte Dateien unter `app/`, 376 KB Quelltext; von den letzten
100 Commits berühren **4** beide Seiten. Ein eigenes Repo würde für 376 KB eine
Versionsgrenze einziehen, die viermal je hundert Commits überquert werden müsste.

## Warum trotzdem getrennte Sitzungen

Drei Gründe, alle am selben Tag belegt: Zwei Sitzungen teilen nicht denselben
Denkfehler — heute war ich Auftraggeber und Prüfer derselben Naht, und dass der Fehler
auffiel, war Glück. Zweitens zwingt die Trennung den Vertrag ins Dokument statt in den
Kopf; genau daraus wurde `contract_version` ein Pflichtfeld. Drittens ist eine Sitzung,
die Python, Swift und die Naht zugleich hält, die teuerste Bauform.

## Verworfen: der dauerhafte Bau-Arbeitsbaum

Zuerst vorgeschlagen, dann durch die eigene Messung widerlegt und zurückgezogen:
Der Modulcache von Swift trägt **absolute Pfade** — nach dem Umzug von `/private/tmp`
brach der Bau sofort (`PCH was compiled with module cache path '/private/tmp/…'`),
295 MB mussten neu entstehen. Zweitens hing der Baum an einem alten Commit
(215 Tests statt 241) und hätte still veralteten Code geprüft — dieselbe Klasse wie
`L-600726` (Quelle gegen Betrieb). Der Baum wurde wieder entfernt.

## Preis

Der Befund von heute fiel nur, weil beide Seiten in einem Commit lagen. Getrennte
Sitzungen verschieben ihn auf den nächsten gemeinsamen Testlauf. Die Gegenmaßnahme ist
kein zweites Repo, sondern der Satz aus `L-51e6d8`: Wer einen Rückgabewert oder ein
Schema ändert, nennt die Konsumenten — auch in Dateien, die er nicht anfassen darf.

---

## NACHTRAG 2026-08-18T17:37:02+0200 — die Werkbank heißt jetzt lehrAtelier

Diese ADR ist am 2026-08-18 geschrieben worden, als die Werkbank `atelier` hieß.
Am selben Tag wurde sie in **`lehrAtelier`** umbenannt (ADR-027, Commit `7db10b10`,
286 Swift-Tests grün). Betreiberbegründung: die Vorsilbe passt, weil die Werkbank
den Domänen beibringt, die Werkzeuge zu benutzen, die sie bereitstellt.

**Der Text oben wird nicht umgeschrieben.** Er war zu seinem Zeitpunkt richtig, und
eine Entscheidung nachträglich auf den heutigen Namen zu bringen, macht aus einem
Beleg eine Behauptung. Das ist dieselbe Regel, die seit heute als `BDW-P08` im
Katalog steht: das Abgelöste bleibt lesbar, es wird gekennzeichnet.

**Was umbenannt wurde:** Swift-Ziel, Quellverzeichnis `app/Sources/LehrAtelier`,
Bündel `lehrAtelier.app`, Bundle-Kennung `de.brainlehr.lehratelier`, Signaturprofil,
Anzeigename.

**Was ausdrücklich NICHT umbenannt wurde** — und deshalb gilt jede Ortsangabe oben
unverändert weiter:

| bleibt | Wert |
|---|---|
| Arbeitsbaumpfad | `/Volumes/daten/Begod2026/atelier` |
| Zweig | `brainlehr/atelier` |
| Steuerung | `BRAINLEHR_STEUERUNG`, Port 4599 |
| Historie | Commits, ADRs, Messläufe, Wissensknoten |

Der Arbeitsbaumpfad blieb, weil ein LaunchAgent darauf zeigt — eine getrennte
Entscheidung, die beim Betreiber liegt.

**Die Umbenennung hat sich selbst eine Falle gestellt**, und sie gehört hierher,
weil sie die nächste Umbenennung betrifft: Der alte Prozess `atelier` lief weiter
und hielt Port 4599; der Aufräumbefehl `pkill -f "Ausgabe/lehrAtelier"` traf ihn
nicht, weil sein Pfad noch den alten Namen trug. Der neue Prozess scheiterte still
am Binden, und jeder Steuerbefehl ging danach an eine Anwendung, die niemand ansah.
Daraus entstand ein Defektbericht über einen Fehler, den es nie gab (`L-542a28`,
zweites Vorkommen). **Nach jeder Umbenennung eines laufenden Programms einmal nach
dem ALTEN Namen suchen — der Aufräumbefehl kennt nur den neuen.**
