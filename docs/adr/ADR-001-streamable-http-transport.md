# ADR-001: Der Wissensspeicher bekommt Streamable HTTP als zweiten Transport

**Status:** Akzeptiert
**Datum:** 2026-08-09T18:05:00+0200
**Entscheider:** Betreiber (ausdrueckliche Wahl "Streamable HTTP sofort", nachdem die
Alternative Unix-Socket samt Preisvergleich vorlag)
**Betroffen:** `knowledge_mcp_server.py`, neuer HTTP-Aufsatz, Klientenkonfiguration

## Ausgangslage, gemessen

Fuer den Transport gab es **keine Entscheidung** — Knoten `436cb221`, geprueft am
2026-08-08: stdio ist die Voreinstellung von MCP und wurde uebernommen, weil sie trug. Der
einzige aeltere Knoten `3b4c7f68` ist ein Rechercheergebnis ohne Entscheider.

Was stdio heute kostet, alles belegt:

- **Mehrere Prozesse, eine Datei.** Gemessen im `access_log`: in acht Stunden am
  2026-08-08/09 schrieben zwei bis drei verschiedene Sitzungen gleichzeitig, Spitzenstunde
  634 Zeilen. Der Server haelt WAL und `BUSY_TIMEOUT_MS = 2000`; der Quelltext benennt
  selbst, dass das bei Gedraenge nicht reicht (`L-f3edbf`).
- **Kein zweites Geraet**, per Konstruktion.
- **Ein fremder Kunde muesste unser Verzeichnis besitzen**, weil er den Prozess startet.
- **Keine Durchsetzung**: wer den Prozess startet, kann die Datei ohnehin oeffnen
  (`L-bd1562`). stdio hat die Zugriffskontrolle erspart, nicht ersetzt.
- **Codeaenderungen greifen erst nach Neustart** (Veraltet-Melder), weil jede Sitzung ihren
  eigenen Serverprozess haelt.

Die Spezifikation (Stand 2026-07-28) kennt genau zwei Standard-Bindungen: **stdio** und
**Streamable HTTP**. Eigene Transporte sind erlaubt und sollen ueber Bytestroeme das
stdio-Framing wiederverwenden.

## Entscheidung

Der Server bekommt **Streamable HTTP** als zweiten Transport. stdio bleibt bestehen und
unveraendert — der Umstieg ist additiv, kein Ersatz.

Verbindlich aus der Spezifikation, ohne Ermessen:

| Anforderung | Verhalten |
|---|---|
| ein Endpunkt, nur POST | GET/DELETE → `405` |
| `Origin` pruefen (MUSS) | ungueltig → `403`, gegen DNS-Rebinding |
| lokal binden (SOLL) | Vorgabe `127.0.0.1`, nie `0.0.0.0` ohne ausdrueckliche Konfiguration |
| Authentifizierung (SOLL) | hier **Pflicht**, siehe unten |
| `MCP-Protocol-Version`, `Mcp-Method`, `Mcp-Name` | muessen zum Rumpf passen, sonst `400` + `-32020` |
| Notification | `202` ohne Rumpf |
| Anfrage | `application/json` **oder** `text/event-stream` |
| unbekannte Methode | `404` + `-32601` |
| Abbruch | Klient schliesst den SSE-Strom |
| entfallen in dieser Revision | Sitzungen (`Mcp-Session-Id`), GET-Strom, `Last-Event-ID` |

## Die Bedingung, ohne die diese Entscheidung falsch waere

> **Ein offener Port ohne Rechte ist schlimmer als eine offene Datei.**

Mit stdio ist die Prozessgrenze die Zugangsgrenze; `actor`, `session` und `model` stammen aus
dem Prozesskontext. Ueber HTTP kaemen sie als Behauptung des Aufrufers — und heute existiert
**keine** Rechtepruefung. Gemessen: 62 von 72 Normentscheidungen hat ein KI-Akteur sich selbst
zugeschrieben; `actor` sagt bei 365 von 388 Zeilen nichts aus.

**Darum gilt ab dem ersten Tag des HTTP-Betriebs:**

1. **`actor` kommt aus dem Zugangsmerkmal, nicht aus den Argumenten.** Ein Aufrufer kann seine
   Identitaet nicht mehr behaupten. Das ist der eigentliche Gewinn dieser Umstellung und
   heilt eine Fehlklasse, die stdio nie heilen konnte.
2. **Kein Zugangsmerkmal, keine Antwort** — `401`, bevor irgendetwas gelesen oder geschrieben
   wird.
3. **Schreibende Werkzeuge nur mit Schreibbefugnis.** Bis ein Rollenmodell existiert (S6),
   gibt es genau zwei Stufen: lesen und schreiben.

## Verworfene Alternativen

**Unix-Domain-Socket mit stdio-Framing.** Waere der kleinste Schritt gewesen (die Spezifikation
sieht ihn ausdruecklich vor) und haette die Nebenlaeufigkeit ebenso geloest, ohne Port und ohne
Rechtepflicht — Zugang ueber Dateirechte. **Abgelehnt vom Betreiber**, weil er das zweite
Geraet und den fremden Kunden jetzt braucht, nicht spaeter; ein Socket haette beides nicht
gekonnt und einen zweiten Umbau erzwungen.

**Bei stdio bleiben.** Abgelehnt: haette die vier gemessenen Kosten oben festgeschrieben.

**Fertiges MCP-SDK einziehen.** Abgelehnt: unser JSON-RPC ist handgeschrieben und
transportfrei (`handle()` liefert ein Antwort-Dict, die Schleife liegt darum herum). Ein SDK
brauchte eine neue Abhaengigkeit und einen Umbau der Werkzeugregistrierung, um dieselbe
Schleife zu ersetzen. Der HTTP-Aufsatz kommt mit der Standardbibliothek aus.

## Folgen

**Gewonnen:** ein Serverprozess statt acht — damit ein Schreiber statt zwei bis drei, und das
Sperrproblem loest sich ohne Transaktionsapparat · Codeaenderungen greifen ohne
Sitzungsneustart · zweites Geraet und fremder Kunde moeglich · Identitaet wird geprueft statt
behauptet.

**Bezahlt:** eine Angriffsflaeche, die es vorher nicht gab, samt Pflicht zu Zugangsmerkmalen
und deren Aufbewahrung · Lebenszyklus des Servers wird zur eigenen Aufgabe (stdio bekam ihn
geschenkt: EOF beendete den Prozess) · TLS ist beim Sprung ueber den Rechner hinaus
nachzuruesten, `127.0.0.1` traegt nur lokal.

**Abbruchbedingung, an der diese Entscheidung als falsch erkennbar waere:** Wenn nach der
Umstellung Schreibvorgaenge haeufiger verloren gehen als vorher, oder wenn der HTTP-Weg in
Messungen langsamer ist als stdio, ohne dass ein zweiter Klient ihn nutzt. Beides ist zaehlbar
und wird gezaehlt.

## Nachweis, der zur Umsetzung gehoert

Rot vor gruen, je Anforderung ein Fall, jeder muss vor dem Bau fehlschlagen: `403` bei fremdem
`Origin` · `401` ohne Zugangsmerkmal · `400` mit `-32020` bei Header-Rumpf-Abweichung · `405`
auf GET · `404` mit `-32601` bei unbekannter Methode · `202` auf eine Notification · und der
Negativfall, der am leichtesten vergessen wird: **ein gueltiger Aufruf mit selbstbehauptetem
`actor` im Rumpf darf diesen Wert NICHT uebernehmen.**
