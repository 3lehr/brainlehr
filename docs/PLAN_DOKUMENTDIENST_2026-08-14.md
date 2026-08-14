# Linie F: der Dokumentdienst — Abzweigung aus dem Gesamtplan

**Stand** 2026-08-14T12:0x+0200 · **Zweig** `brainlehr/b4-ausweis`
**Gesamtplan** `docs/PLAN_GESAMT_2026-08-13.md`, Linie F — dort steht die
Reihenfolge, hier die Ausführung. Kennungen F1–F5 gelten repo-weit.
**Rahmen** ADR-010 (Dokumentfenster: nativ, mehrbenutzerfähig Zeichen für Zeichen,
erst LAN) · ADR-006 (Python ist Grundsprache) · ADR-007 (brainlehr trägt, openlehr wirkt)

Geschrieben im Abwesenheitsmodus. Alles unter „gemessen" ist an diesem Tag mit
Werkzeugen erhoben; die Entscheidungen unten sind meine, unter benannter Annahme,
und der Betreiber kann jede davon umstoßen.

---

## 1 · Gemessener Ist-Stand

| | |
|---|---|
| **CRDT Python** | `pycrdt` 0.14.2 — gleichzeitige Änderungen konvergent, Bausteinbaum trägt `absatz` und `feld` |
| **CRDT Swift** | `yswift` 0.2.1 — baut und läuft, `YDocument.undoManager` vorhanden, **Kennung unter 2^32** (ADR-010) |
| **Baustein-Vertrag** | `kern/baustein.py` steht: Typen, Kennung, Anker, Anmerkung mit Zustand |
| **Dienst** | Bei Planbeginn: **es gab keinen** (kein `http.server`, `fastapi`, `uvicorn` unter `kern/`, `haken/`, `melder/` — per grep). Seit `f00fff3` steht `kern/dokumentdienst.py` |
| **Nächste Naht** | `app/Sources/Atelier/Steuerschnittstelle.swift` bindet auf 4599 (Debug), Port 0 als Ausweichweg, tatsächlicher Port in einer Datei |
| **Transport verfügbar** | `websockets` 17.0.1 (cp314-Wheel) und `pycrdt-websocket` 0.16.4 laden beide |

## 2 · Entscheidungen, mit Ablehnungsgrund

**Transport: WebSocket, über `websockets`.** Die Python-Standardbibliothek hat
keinen WebSocket-Server — gemessen, nicht vermutet. Verworfen: HTTP-Polling
(Zeichen für Zeichen bei 200 ms Takt ist entweder träge oder ein Lastproblem)
und ein roher TCP-Rahmen von Hand (spart eine Abhängigkeit und kostet den
Rahmenparser, den `websockets` korrekt hat).

**`pycrdt-websocket` NICHT von Anfang an.** Es bringt Raumverwaltung und ein
fertiges Yjs-Protokoll mit — und genau deshalb erst dann, wenn der eigene
Rahmen sich als zu dünn erweist. Der Grund ist nicht Sparsamkeit: die
Kennungsauflage aus ADR-010 muss auf **jedem** Teilnehmer durchgesetzt werden,
und eine Bibliothek, die Dokumente selbst anlegt, vergibt die Kennung selbst.
Erst messen, ob sie sich vorschreiben lässt.

**Bindung: loopback als Vorgabe, LAN mit Ausweispflicht.** Ursprünglich als
meine Entscheidung notiert („Vorgabe loopback, LAN nur über einen Schalter") —
**der Betreiber hat sie am 2026-08-14 gekippt**: LAN sofort, damit der Mini im
selben Netz als Testfall dient. Umgesetzt als **Regel statt Schalter**: alles
außer `127.0.0.1` verlangt einen beglaubigten Ausweis (`kern/ausweis.loese_auf`).
Ein Schalter „LAN ohne Ausweis" wäre der, den man einmal für einen Test umlegt
und nie zurück. Preis, der bleibt und in Linie G steht: keine
Transportverschlüsselung, das Geheimnis wandert im Klartext.

**Ein Dokument je Raum, Raum je Kennung.** Kein Mandantenmodell, keine
Rechteverwaltung. Beides gehört zu „Konten später".

## 3 · Reihenfolge, und wo sie bindet

**F1 · Kennungsvergabe zentral** (`kern/dokumentkennung.py` o. ä.): jeder
   Teilnehmer bekommt seine Kennung vom Dienst, nicht vom Zufall. **Bindend
   vor allem anderen** — sonst verdoppelt sich Text still, und der Fehler ist
   nachträglich nicht von einer echten Doppeleingabe zu unterscheiden.
**F2 · Dienst mit einem Raum**: verbinden, Anfangsstand holen, Updates
   weiterreichen, Stand halten. Noch ohne Ablage.
**F3 · Ablage**: der Stand überlebt einen Neustart des Dienstes.
**F4 · Anmerkungen** über denselben Kanal (sie sind Teil des Dokuments, kein
   zweiter Weg — sonst driften Dokument und Anmerkung auseinander).
**F5 · Fenster im atelier**: Klient, `yswift`, Kennung vom Dienst.

F1 vor F2 ist bindend. F3 kann nach F4, wenn ein Neustart nichts kostet.

## 4 · Was bewusst NICHT gebaut wird

- **Keine Rechteverwaltung, keine Konten.** Preis: der Dienst taugt nicht über
  das eigene Netz hinaus, und das steht dann auch so in seiner Beschreibung.
- **Kein Web-Fenster.** Betreiberentscheid (ADR-010).
- **Kein Ersatz für `Verschmelzung.swift`.** Sie bleibt, bis der Dienst steht;
  ihre `Absatz.Herkunft` ist die Naht der Herkunftskette.
- **Keine Formularlogik.** `feld` ist ein Bausteintyp, mehr nicht — Rechnungen
  rechnen später.

## 5 · Aufträge, fertig zum Übergeben

**F1–F4 sind gebaut** (`kern/teilnehmer.py`, `kern/dokumentdienst.py`,
`kern/dokument.py`). Offen ist allein **F5**. Der erledigte F4 bleibt unten
stehen, weil seine Abnahme beschreibt, woran F5 sich messen lassen muss.

**Für die Aufträge gleichermaßen:** Arbeitsort
`/Volumes/daten/Begod2026/brainlehr`, Zweig `brainlehr/b4-ausweis` — ein
Startverzeichnis unter `.claude/worktrees/` ist ein alter Stand. Zuerst
`CLAUDE.md` hier und in `~/.claude/` lesen, dann diesen Plan und ADR-010.
„Sieht der Code anders aus als hier beschrieben, halte dich an den Code und
melde die Abweichung." Kein `git add -A`, kein Push, kein `git stash`.
Committen mit expliziter Pfadliste. Volle Python-Suite **im Vordergrund** mit
`timeout=600000` (rund 350 s). Neues Modul mit `--selftest` gehört in
`MODULE` in `tests/test_alle_selftests.py`, sonst wird die Ratsche rot.

### F4 · Anmerkungen über denselben Kanal

| | |
|---|---|
| **Darf ändern** | `kern/dokumentdienst.py`, `kern/baustein.py`, deren Selbsttests |
| **Tabu zusätzlich** | `kern/teilnehmer.py` (die Kennungsauflage wird nicht angefasst), `schema.sql` — es wird **keine Spalte und keine Tabelle** angelegt, die Ablage bleibt eine Datei |
| **Fakten** | Der Raum hält heute genau ein CRDT-Dokument und reicht Updates weiter (drei Nachrichtenarten: `willkommen`, `update`, `fehler`). `kern/baustein.py` kennt `Anmerkung` mit Zustand, Klasse, Anker und `wechsle()`, das den **erreichten** Zustand zurückgibt. Anmerkungen gehören **in dasselbe Dokument** wie die Bausteine — ein zweiter Kanal ließe Dokument und Anmerkung auseinanderdriften, und genau das ist der Grund, warum die KI hier kein Sonderfall ist. |
| **Abnahme** | Rot vor grün: zwei Teilnehmer, einer setzt eine Anmerkung mit Anker, der andere sieht sie samt Zustand — vorher gibt es keinen Weg dafür. Negativfall, und er ist der wichtigere: wird der bezeichnete Baustein gelöscht, ist die Anmerkung **sichtbar verwaist** und wandert nicht über den Suchtext an eine ähnliche Stelle. Grenzwerte: Anmerkung auf den ersten Baustein, auf den letzten, auf einen, der nie existierte. Jeder Zustandswechsel gibt den erreichten Zustand zurück, nie `True`. |

### F5 · Das Fenster im atelier

| | |
|---|---|
| **Darf ändern** | `app/Sources/Atelier/` (neue Ansicht), `app/Package.swift` für die `yswift`-Abhängigkeit |
| **Tabu zusätzlich** | `app/Sources/BrainlehrCore/Verschmelzung.swift` — sie bleibt unangetastet, bis der Dienst trägt; `kern/` vollständig |
| **Fakten** | `yswift` 0.2.1 baut auf diesem Rechner, `Package.resolved` liegt in `spikes/crdt_pyswift/`. `YDocument.undoManager` existiert — Undo/Redo ist **nicht** zu bauen. Die Kennung kommt aus der `willkommen`-Nachricht des Dienstes und wird **nie** selbst gewürfelt; `pycrdt`-Vorgabewerte liegen über der 32-Bit-Schranke und verdoppeln Text still (`L-44dc9f`). Der Empfang braucht eine Frist — ein Klient, der ewig wartet, sieht aus wie ein langsamer (`L-3d88e9`). |
| **Abnahme** | Rot vor grün: zwei Fenster am selben Dienst, gleichzeitig in denselben Satz getippt, beide zeigen dasselbe — vorher gibt es kein Fenster. Negativfall: ein Fenster, das eine Kennung ≥ 2^32 anbietet, wird vom Dienst **abgewiesen** statt bedient. Grenzwert: Kennung 1, 2^32−1, 2^32. |

## 6 · Woran sich Erfolg misst

- Zwei Klienten, gleichzeitig in denselben Satz getippt → beide zeigen
  dasselbe. **Rot vorher:** es gibt keinen Dienst.
- Ein Teilnehmer bekommt nie eine Kennung ≥ 2^32 — Negativfall: der Dienst
  weist eine selbst gewählte Kennung darüber **ab**, statt sie zu nehmen.
- Der Dienst wird neu gestartet, das Dokument ist noch da (nach Schritt 3).
- Eine Anmerkung überlebt eine Umsortierung der Bausteine; ein gelöschter
  Baustein hinterlässt eine sichtbar verwaiste Anmerkung, keine still
  umgehängte (`kern/baustein.py` prüft das bereits im Kleinen).
