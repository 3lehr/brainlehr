# Startprompt: openlehr als erste Instanz auf brainlehr

Erzeugt 2026-08-14 am Ende der Grundarchitektur-Sitzung, für ein **frisches
Kontextfenster**. Alles unter „gemessen" ist an diesem Tag mit Werkzeugen
erhoben. Was hier fehlt, fehlt absichtlich — dieser Prompt gibt **keine
Empfehlung** zur Reihenfolge ab, die entscheidet der Betreiber.

---

## Der Auftrag

> **Betreiber, 2026-08-14:** *„berufschule ganz nach hinten schieben, wir wollen
> zuerst openlehr integrieren und dies mit den chaos fotografen steuer usw
> domäne"*

Die Berufsschul-Domäne (Knoten `962fbf48`) ist **zurückgestellt**, nicht
verworfen. Zuerst: openlehr wird die erste echte Instanz auf der brainlehr-
Schicht, am Fall „Fotograf mit Belegchaos".

## Was in der Grundarchitektur-Sitzung entschieden und gebaut wurde

**ADR-006 bis ADR-010** liegen in `brainlehr/docs/adr/`. Die vier Sätze, die
für diese Arbeit zählen:

| | |
|---|---|
| **ADR-007** | Zwei Schichten. **brainlehr** trägt (was gilt, und ob es belegt ist), **openlehr** wirkt (was ein Mensch in seiner Lage damit tun kann). Die Prüffrage für jede Idee: *muss sie etwas verweigern können?* → dann brainlehr |
| **ADR-006** | Python ist Grundsprache, das DB-Schema ist die Quelle der Form |
| **ADR-009** | Dokumentausgabe: LuaLaTeX mit `verapdf -f ua1` als Schranke — Rechnungen und Schreiben kommen barrierefrei UND druckfähig aus demselben Lauf |
| **ADR-010** | Das Dokumentfenster: Mensch und Modell am selben Dokument, Zeichen für Zeichen, Anmerkung = **Auftrag mit Anker**, nicht Kommentar |

**Gebaut und belegt (brainlehr, Zweig `brainlehr/b4-ausweis`, gepusht):**

- `kern/baustein.py` — Dokument als Baum aus Bausteinen mit stabilen Kennungen.
  Bausteintyp **`feld`** steht gleichberechtigt neben `absatz`: **eine Rechnung
  und ein Schriftsatz benutzen dieselbe Struktur.**
- `kern/dokument.py` — Anmerkungen liegen im **selben** Dokument wie die
  Bausteine. Zustand `offen → umgesetzt → abgenommen | abgelehnt`, Urheber
  `mensch`/`modell`.
- `kern/dokumentdienst.py` — WebSocket-Dienst, ein Raum, Stand überlebt
  Neustart, Ausweispflicht außerhalb von `127.0.0.1`, acht Kennzahlen.
- `kern/teilnehmer.py` — Kennungsauflage (< 2³², sonst verdoppelt sich Text still).
- `melder/dienstwache.py` — meldet die vier Fälle ohne Normalfall.
- **atelier** (`app/`) — native Mac-App, Ansicht **Dokument** verbunden mit dem
  Dienst; Steuerschnittstelle auf 4599 mit `/zustand`, `/ansicht`, `/blick`,
  `/dokument`.
- Suiten: Python **1489 grün**, Swift **193 grün**, 13 xfail mit Grund.

## Gemessener Ist-Stand openlehr (2026-08-14)

- Zweig `merge/daten-features`, **12 Commits ungepusht**, 1 Datei geändert.
- **529 Python-Dateien** unter `apps/openlehr`, Steuermodul unter
  `apps/openlehr/daemon/steuer/` (FastAPI-Daemon, Port 4242).
- Papernetz zum Fotografen-Steuerrecht: `docs/papers/citation-network.json`,
  **31 Knoten**. Kernbefund daraus: **es gibt keinen 9-%-Satz** — nur 19 % und
  7 %, und der 7-%-Satz für Bildrechte greift nur, wenn die Nutzungsrechte
  gesondert verhandelt und bepreist sind (FG Münster).
- Letzter eigener Stand: `docs/openlehr/STAND_2026-07-25T09-55-00+0200_…`.
  **Älter als drei Wochen — vor Gebrauch gegen `git log` prüfen.**

## Die Lehre, die diese Arbeit prägen sollte

`L-473ba2`, aus einem Prüftag an openlehr (2026-08-08/09): Acht Fehler, **sechs
davon an derselben Stelle** — der Naht zwischen Oberfläche und Fachlogik. Das
Rechnungschreiben, der Kern der App, war aus der Oberfläche heraus **tot**: der
Server verlangte `issue_date` und `service_period`, der Bildschirm hatte dafür
nie Felder. Währenddessen: 386 jsdom-Tests und über 300 pytest-Tests grün — die
einen prüfen die Oberfläche gegen einen erfundenen Server, die anderen die
Fachlogik gegen erfundene Eingaben. **Der erste E2E-Walkthrough fand in EINEM
Lauf mehr echte Fehler als beide Testbäume zusammen.**

Daraus vier Regeln für jede neue Domäne, alle mechanisch statt diszipliniert:

1. Die **E2E-Journey ist die Abnahmedefinition** und wird **vor** den
   Bildschirmen geschrieben — rot, bis die Domäne wirklich läuft.
2. Drei Nahtprüfungen: **Baustein-Bindung**, **Feldvertrag** (jedes
   serverseitige Pflichtfeld existiert auf dem besitzenden Bildschirm),
   **Textvertrag**.
3. **Ein Versprechen ist ein Test**: steht auf einem Bildschirm „wird gebraucht
   für X", muss ein Test belegen, dass X passiert.
4. Der Prüfstand wird aus der Auslieferung **abgeleitet**, nie parallel
   gepflegt.

## Die Fragen an den Betreiber

Sie stehen bewusst **ohne Antwortvorschlag**. Nummeriert, damit er einzeln
antworten kann.

### Der Fall selbst

1. **Wer ist der Fotograf?** Ein echter Mensch mit echten Belegen, ein
   Bekannter, oder eine gedachte Person? Davon hängt ab, ob wir mit Testdaten
   oder mit echten Daten Dritter arbeiten — und das ist die Grenze der
   Beta-Direktive.
2. **Was genau ist „das Chaos"?** Schuhkarton mit Papierbelegen, ein volles
   Mailpostfach, Fotos auf dem Telefon, oder alles zusammen?
3. **Was soll am Ende herauskommen?** Eine EÜR, eine UStVA, ein Ordner
   sortierter Belege, oder eine Antwort auf „darf ich das absetzen"?
4. **Bis wann?** Gibt es eine Frist (Steuertermin), oder ist das eine
   Erprobung ohne Datum?
5. **Wie viele Belege ungefähr, über welchen Zeitraum?** Zehn oder tausend
   entscheidet die Bauform.

### Was openlehr heute schon kann und soll

6. **Was von openlehr/steuer läuft aus deiner Sicht bereits zuverlässig?**
   529 Dateien sagen nichts darüber, was du benutzt.
7. **Was hast du zuletzt selbst damit gemacht** — und was hat dabei genervt?
8. **Die 12 ungepushten Commits auf `merge/daten-features`:** soll ich die
   zuerst prüfen und pushen, oder liegen die absichtlich?
9. **Gibt es Mandanten?** Ein Fotograf oder mehrere Nutzer mit getrennten
   Daten?
10. **Soll die Steuer-Oberfläche bleiben, wie sie ist**, oder ist sie Teil
    dessen, was neu gebaut wird?

### Die Naht zu brainlehr

11. **Was soll brainlehr in diesem Fall verweigern können?** Nach ADR-007 ist
    das die Trennlinie. Kandidaten: eine Rechtsauskunft ohne Beleg, ein
    Steuersatz ohne Fundstelle, ein Beleg ohne Herkunft.
12. **Soll das Rechtswissen (Papernetz, 31 Knoten) in brainlehr wandern** oder
    in openlehr bleiben?
13. **Wer entscheidet über eine Buchung** — du, das Modell, oder das Modell mit
    deiner Bestätigung? Dieselbe Frage wie beim Dokumentfenster; dort ist die
    Antwort „einstellbar, Vorgabe Vorschlag".
14. **Soll das Dokumentfenster hier zum Einsatz kommen**, also Rechnungen und
    Schreiben im atelier statt im Browser?
15. **Gilt die Ausweispflicht auch hier?** Steuerdaten sind heikler als ein
    Schriftsatz.

### Grenzen und Risiko

16. **Was darf das System NIE tun?** Abgeben an ELSTER? Zahlen? Fristen
    quittieren?
17. **Was passiert bei einer falschen Zahl** — merkst du es, oder fällt es erst
    beim Steuerberater auf?
18. **Gibt es einen Steuerberater im Spiel**, und was macht er?
19. **Sollen Belege das Haus verlassen** (Modellanfrage an einen Anbieter),
    oder bleibt alles lokal?
20. **Was ist dir lieber: ein System, das oft nachfragt, oder eines, das
    selten falsch liegt?** Beides zugleich gibt es nicht.

### Arbeitsweise

21. **Soll ich zuerst messen, was openlehr heute kann** (ein Walkthrough über
    den echten Ablauf), oder direkt bauen?
22. **Was ist der kleinste Fall, an dem du den Nutzen sofort sehen würdest?**
23. **Darf ich openlehr umbauen**, oder ist es produktiv genug, dass nur
    ergänzt wird?

## Wie in dieser Sitzung gearbeitet werden soll

- **Arbeitsort** `/Volumes/daten/Begod2026/openlehr`, für die brainlehr-Seite
  `/Volumes/daten/Begod2026/brainlehr` (Zweig `brainlehr/b4-ausweis`). Ein
  Startverzeichnis unter `.claude/worktrees/` ist ein alter Stand.
- Zuerst `CLAUDE.md` in beiden Repos lesen, dann diesen Prompt, dann
  `brainlehr/docs/PLAN_GESAMT_2026-08-13.md` (Linien F und G sind fertig).
- **Ein neuer Plan wird eine LINIE im Gesamtplan**, keine eigene Zählung ab 1
  (`L-30be01`).
- „Sieht der Code anders aus als hier beschrieben, halte dich an den Code und
  melde die Abweichung."
- Kein `git add -A`, kein `git stash`. Committen mit expliziter Pfadliste.
- Volle Suite **im Vordergrund** mit `timeout=600000`.

## Was in dieser Sitzung NICHT passieren soll

- **Keine Berufsschul-Domäne.** Zurückgestellt, Knoten `962fbf48`.
- **Kein Umbau am Dokumentdienst**, solange keine Domäne ihn braucht.
- **Keine Schwellen für die mengenhaften Kennzahlen** ohne Nullmessung mit dem
  zweiten Gerät (G3 steht offen, Grund in
  `brainlehr/runs/nullmessung_dokumentdienst_2026-08-14.json`).
