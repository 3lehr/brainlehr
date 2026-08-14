# Plan: der Dokumentdienst — Schritt 4 aus ADR-010

**Stand** 2026-08-14T12:0x+0200 · **Zweig** `brainlehr/b4-ausweis`
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
| **Dienst** | **Es gibt keinen.** Kein `http.server`, kein `fastapi`, kein `uvicorn` irgendwo unter `kern/`, `haken/`, `melder/` — gemessen per grep |
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

**Bindung: `127.0.0.1` zuerst, LAN als ausdrücklicher Schalter.** Der Betreiber
hat „erst LAN, Konten später" gewählt. Ein Dienst ohne Ausweis, der auf allen
Schnittstellen lauscht, ist im selben Netz von jedem Gerät beschreibbar — das
ist kein Testumgebungsproblem, sondern eine Bauform, die man später nicht mehr
zurücknimmt. Deshalb: Vorgabe loopback, LAN nur über `BRAINLEHR_DIENST_HOST`,
und der Ausweis (`kern/ausweis.py`) ist die vorgesehene Naht, sobald der Dienst
das Haus verlässt. **Das ist meine Entscheidung, nicht seine** — er kann sie
auf LAN-per-Vorgabe umstellen.

**Ein Dokument je Raum, Raum je Kennung.** Kein Mandantenmodell, keine
Rechteverwaltung. Beides gehört zu „Konten später".

## 3 · Reihenfolge, und wo sie bindet

1. **Kennungsvergabe zentral** (`kern/dokumentkennung.py` o. ä.): jeder
   Teilnehmer bekommt seine Kennung vom Dienst, nicht vom Zufall. **Bindend
   vor allem anderen** — sonst verdoppelt sich Text still, und der Fehler ist
   nachträglich nicht von einer echten Doppeleingabe zu unterscheiden.
2. **Dienst mit einem Raum**: verbinden, Anfangsstand holen, Updates
   weiterreichen, Stand halten. Noch ohne Ablage.
3. **Ablage**: der Stand überlebt einen Neustart des Dienstes.
4. **Anmerkungen** über denselben Kanal (sie sind Teil des Dokuments, kein
   zweiter Weg — sonst driften Dokument und Anmerkung auseinander).
5. **Fenster im atelier**: Klient, `yswift`, Kennung vom Dienst.

Schritt 1 vor 2 ist bindend. 3 kann nach 4, wenn ein Neustart nichts kostet.

## 4 · Was bewusst NICHT gebaut wird

- **Keine Rechteverwaltung, keine Konten.** Preis: der Dienst taugt nicht über
  das eigene Netz hinaus, und das steht dann auch so in seiner Beschreibung.
- **Kein Web-Fenster.** Betreiberentscheid (ADR-010).
- **Kein Ersatz für `Verschmelzung.swift`.** Sie bleibt, bis der Dienst steht;
  ihre `Absatz.Herkunft` ist die Naht der Herkunftskette.
- **Keine Formularlogik.** `feld` ist ein Bausteintyp, mehr nicht — Rechnungen
  rechnen später.

## 5 · Woran sich Erfolg misst

- Zwei Klienten, gleichzeitig in denselben Satz getippt → beide zeigen
  dasselbe. **Rot vorher:** es gibt keinen Dienst.
- Ein Teilnehmer bekommt nie eine Kennung ≥ 2^32 — Negativfall: der Dienst
  weist eine selbst gewählte Kennung darüber **ab**, statt sie zu nehmen.
- Der Dienst wird neu gestartet, das Dokument ist noch da (nach Schritt 3).
- Eine Anmerkung überlebt eine Umsortierung der Bausteine; ein gelöschter
  Baustein hinterlässt eine sichtbar verwaiste Anmerkung, keine still
  umgehängte (`kern/baustein.py` prüft das bereits im Kleinen).
