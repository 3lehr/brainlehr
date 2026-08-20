# Startprompt: den Gesamtplan bauen

Erstellt 2026-08-21T00:29:28+0200. Alle Zahlen unten sind nachgezählt, nicht erinnert.

---

Bau den Gesamtplan aus `docs/PLAN_BETRIEBSPROFILE_2026-08-20.md` (710 Zeilen,
acht Stränge A–G). **Ohne Rückfragen**, bis morgen früh. Du entscheidest
Reihenfolge und Zuschnitt innerhalb der unten genannten Sperren.

## Fakten

* Repo `/Volumes/daten/Begod2026/brainlehr`, Zweig `brainlehr/b4-ausweis`,
  Stand `5d3c6f17`.
* Bestand: 5 232 Knoten, 1 173 Lehren, 288 Testdateien.
* Katalog `docs/REQUIREMENTS_BRAINLEHR.md`: 66 BDW-Zeilen, **10 auf NOT RUN**
  (P09–P14, E22–E25). Das sind deine Abnahmekriterien — jede trägt AC1/AC2.
* Übergabe mit dem Einstieg: `docs/UEBERGABE_2026-08-21.md`.
* `A1` (Widerspruchserkennung) ist seit gestern fertig, `melder/normwiderspruch.py`.

## Bindende Reihenfolge

**B1 zuerst** — die Achsen ins Schema: `mandant` (Vorgabe `lokal`), `kreis`,
`sprache`, und Geltung als eigene Tabelle. Danach erst B2, B3 und C.

Der Grund ist **nicht** die Datenmenge: 5 232 Alteinträgen lässt sich
rückwirkend keine Zuordnung geben, die sie nie hatten. Wer B3 vorzieht, baut
eine Rechteprüfung, die nichts hat, worauf sie prüft.

**Parallel ab sofort:** A2 · A3 · D · E1 · F · P14-Tür (README und
CONTRIBUTING auf Englisch).

## Grenzen

* **Nicht auf `main`.** Committen nach jedem abgeschlossenen Schritt, kein Push.
* **Nicht bauen:** BDW-E24 (zweiter Faktor — sechs Wege im Plan, keiner
  entschieden), E01/E04/E05 (IdP, SSO, SCIM — an einen echten Piloten
  gebunden), E19 (Datenregionen — es gäbe nichts zu begrenzen).
* **Der öffentliche Export wird nicht gepusht.** 675 Dateien liegen bereit;
  das GitHub-Konto ist wegen einer Abrechnungsfrage gesperrt.
* **Vier Stopp-Punkte bleiben**, dort wird gewartet statt entschieden:
  Kennwörter · Außenwirkung gegenüber Dritten · Unumkehrbares · Geld.
  Alles andere entscheidest du selbst.

## Arbeitsweise

* **Hauptchat plant, Subagenten bauen und testen** (Rang-1-Weisung 2026-08-20).
  Opus → Sonnet → Haiku. Kontextfenster wiederverwenden, solange dieselben
  Dateien betroffen sind; neues Thema oder über ~300k Token → frisch beauftragen.
* **Ponytail** und **Caveman ultra** bleiben in Kraft.
* Plan und Katalog werden **mitgeschrieben**, nicht nachträglich — `melder/
  planmitschrieb.py` misst das. Jede Betreiberentscheidung geht **zuerst** in
  den Katalog (Rang-1-Pflicht).

## Abnahme

Je Strang: **rot vor grün** an einem festen Bezugspunkt, Gegenprobe in beide
Richtungen, Negativfall. Für B1 und B3 zusätzlich:

* Beide Ausgangszustände fahren — **frisch angelegt UND gewachsen**, nicht nur
  der leere.
* Je Achse ein **Negativtest**: Der fremde Mandant sieht nichts. Ein
  Positivtest allein belegt keine Trennung.
* Bei jedem neuen Melder eine **Positivkontrolle** — einer, der nie
  ausgeschlagen hat, ist von einem kaputten nicht zu unterscheiden.

## Zwei Sätze, die in jeden Agentenauftrag gehören

> Sieht der Code anders aus als hier beschrieben, halte dich an den Code und
> melde die Abweichung.

> Ein gebautes Skript ist keine Messung — führe es aus und lege die
> Ergebnisdatei vor. Starte nichts im Hintergrund; dein Prozess stirbt mit
> deinem Zug.

## Fallen von gestern, gemessen und nicht theoretisch

1. `git checkout --` auf eine **generierte** Dateiliste löschte zweimal
   fertige, uncommittete Arbeit. Vorher committen, was bleiben soll.
2. Kennungen doppelt vergeben (BDW-P06/E20) — die höchste vergebene Nummer
   **messen**, nicht raten.
3. Der laufende MCP-Prozess trägt **alten Code**. Serveränderungen wirken erst
   in einer neuen Sitzung; für sofortige Wirkung ein frischer Python-Prozess.
4. **Zwei von drei Meldern waren beim ersten Lauf gegen den echten Bestand
   falsch** — einer meldete 13 von 13, einer 21 Rauschtreffer. Jeden Melder
   einmal gegen den Bestand fahren und die Treffer **lesen**, bevor du ihm
   glaubst.

## Einsatz

Der Plan trägt acht Stränge aus einem Tag Gespräch, jeder mit gemessenem
Ist-Stand und benanntem Preis. Was heute nicht als Achse ins Schema kommt,
ist morgen nur noch mit rückwirkender Zuschreibung nachzuholen — und die ist
nicht ehrlich herstellbar.
