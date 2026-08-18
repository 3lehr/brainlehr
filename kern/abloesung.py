#!/usr/bin/env python3
"""Eine Abloesung ist selbst ein Wissensgegenstand -- und das Abgeloeste bleibt.

BETREIBERENTSCHEIDUNG 2026-08-18, woertlich: "wir sollten die Abloesung
dokumentieren und das abgeloeste nicht komplett wegschmeissen, weil wenn
etwas zum Beispiel Firma abgeloest wird. Kann daraus auch wieder Neues
wissen oder leeren entstehen?!"

Der Satz korrigiert einen Vorschlag, den ich eine Antwort vorher gemacht
hatte: das Abgeloeste aus dem Suchindex fallen zu lassen. Das waere falsch
gewesen, und zwar aus einem Grund, der ueber Aufbewahrung hinausgeht.

DER UEBERGANG TRAEGT WISSEN, DAS IN KEINEM DER BEIDEN ZUSTAENDE STEHT.
Wird eine Verwaltung abgeloest, steht der Mangel weder im alten noch im
neuen Vertrag -- er steht im GRUND des Wechsels. Wird `atelier` zu
`lehrAtelier`, ist die Erkenntnis nicht der neue Name, sondern dass ein
Gattungswort als Eigenname nicht sagt, wozu es gehoert. Wird
`BEGOD_KNOWLEDGE_DB` durch `BRAINLEHR_DB` abgeloest, entsteht aus der
halben Abloesung eine Falle, die 48 Knoten in die Produktivdatenbank
schrieb -- auch das ist Wissen, das erst im Uebergang entsteht.

Das Abgeloeste ist ausserdem der einzige Massstab, an dem sich der Wert des
Neuen messen laesst. Wer es wegwirft, kann hinterher nicht mehr sagen, ob
der Wechsel etwas gebracht hat.

WAS DIESES MODUL DESHALB NICHT TUT: loeschen, leeren, ausblenden. Das
Abgeloeste bleibt vollstaendig lesbar und auffindbar; es wird nur
GEKENNZEICHNET, damit es nicht als geltend ausgegeben wird. Der Unterschied
ist die ganze Sache: unauffindbar waere Vergessen, ungekennzeichnet waere
eine Falschaussage.

ES GIBT EINEN GEGENBELEG IM EIGENEN HAUS. `knowledge_zurueckziehen` setzt
heute `content = '', summary = ''` (knowledge_mcp_server.py). Wer einen
falschen Eintrag korrigiert, vernichtet damit den Beweis des falschen
Eintrags -- am 2026-08-13 als Defekt gemeldet und bis heute offen. Dieses
Modul ist die Gegenbauform, nicht die Behebung jenes Defekts.

KEIN VERFALL NACH ZEIT. Ausdruecklich verworfen am selben Tag: Ein Eintrag
wird nicht falsch, weil er alt ist. Eine Lehre von vier Stunden hat heute
einen Fehler gefangen, den eine von gestern nicht gefangen haette. Abgeloest
wird durch einen NACHFOLGER mit Grund, nie durch eine Uhr.

Aufruf:
    python3 abloesung.py --selftest
"""
from __future__ import annotations

import hashlib
import sqlite3
import sys

# Der Kantentyp. knowledge_relations laesst den Typ frei -- keine
# Schemaaenderung noetig, keine neue Tabelle.
TYP = "loest_ab"
MARKE = "abgeloest"


def _kanten_id(neu: str, alt: str) -> str:
    return hashlib.sha1(f"{TYP}|{neu}|{alt}".encode()).hexdigest()[:12]


def loese_ab(conn: sqlite3.Connection, *, alt: str, neu: str, grund: str, ts: str,
             urheber: str = "unbekannt") -> str:
    """`neu` loest `alt` ab. Der GRUND ist Pflicht -- eine Abloesung ohne
    Grund ist genau die Aussage, die spaeter niemand rekonstruieren kann,
    und sie ist der eigentliche Ertrag des Vorgangs.

    `alt` behaelt Titel, Zusammenfassung und Volltext. Es bekommt nur die
    Marke, damit ein Abruf es nicht als geltend ausgibt."""
    if not grund or not grund.strip():
        raise ValueError(
            "grund ist Pflicht: der Uebergang traegt das Wissen, nicht der Zustand davor "
            "oder danach. Ohne ihn ist die Abloesung eine Statusaenderung und kein Eintrag.")
    if alt == neu:
        raise ValueError("ein Knoten kann sich nicht selbst abloesen")
    for pfad in (alt, neu):
        if not conn.execute("SELECT 1 FROM knowledge_nodes WHERE path=?", (pfad,)).fetchone():
            raise ValueError(f"unbekannter Knoten {pfad!r}")

    kid = _kanten_id(neu, alt)
    conn.execute(
        "INSERT OR REPLACE INTO knowledge_relations"
        " (id, source_path, target_path, relation_type, evidence, source, creator, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        (kid, neu, alt, TYP, grund, "kern/abloesung.py", urheber, ts, ts))

    # Marke setzen, Inhalt anfassen wir NICHT. Tags sind eine Liste in einem
    # Textfeld; doppeltes Markieren wird vermieden, ohne die uebrigen zu
    # verlieren.
    zeile = conn.execute("SELECT tags FROM knowledge_nodes WHERE path=?", (alt,)).fetchone()
    tags = [t for t in (zeile[0] or "").split(",") if t.strip()]
    if MARKE not in tags:
        tags.append(MARKE)
        conn.execute("UPDATE knowledge_nodes SET tags=? WHERE path=?", (",".join(tags), alt))
    return kid


def vorgaenger(conn: sqlite3.Connection, pfad: str) -> list[dict]:
    """Was dieser Knoten abgeloest hat, mit Grund -- die Kette rueckwaerts."""
    kette = []
    aktuell = pfad
    gesehen = {pfad}
    while True:
        zeile = conn.execute(
            "SELECT target_path, evidence, created_at FROM knowledge_relations"
            " WHERE source_path=? AND relation_type=?", (aktuell, TYP)).fetchone()
        if not zeile or zeile[0] in gesehen:
            return kette
        kette.append({"pfad": zeile[0], "grund": zeile[1], "seit": zeile[2]})
        gesehen.add(zeile[0])
        aktuell = zeile[0]


def nachfolger(conn: sqlite3.Connection, pfad: str) -> dict | None:
    """Was diesen Knoten abgeloest hat. Beantwortet die Frage, die ein Leser
    des ALTEN Eintrags stellt -- und die er sonst nicht stellen kann, weil er
    nicht weiss, dass es einen neueren gibt."""
    zeile = conn.execute(
        "SELECT source_path, evidence, created_at FROM knowledge_relations"
        " WHERE target_path=? AND relation_type=?", (pfad, TYP)).fetchone()
    return {"pfad": zeile[0], "grund": zeile[1], "seit": zeile[2]} if zeile else None


def gilt_noch(conn: sqlite3.Connection, pfad: str) -> bool:
    return nachfolger(conn, pfad) is None


def gruende(conn: sqlite3.Connection) -> list[dict]:
    """Alle Abloesungsgruende des Bestands. DAS ist der Ertrag, um den es dem
    Betreiber ging: nicht die Zustaende, sondern die Uebergaenge -- eine Liste
    dessen, was sich als unzureichend erwiesen hat und warum."""
    return [dict(zip(("neu", "alt", "grund", "seit"), r)) for r in conn.execute(
        "SELECT source_path, target_path, evidence, created_at FROM knowledge_relations"
        " WHERE relation_type=? ORDER BY created_at", (TYP,))]


def _kulisse() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE knowledge_nodes (path TEXT PRIMARY KEY, title TEXT, summary TEXT,
                                      content TEXT, tags TEXT);
        CREATE TABLE knowledge_relations (
            id TEXT PRIMARY KEY, source_path TEXT NOT NULL, target_path TEXT NOT NULL,
            relation_type TEXT NOT NULL, evidence TEXT, source TEXT, creator TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            UNIQUE(source_path, target_path, relation_type));
    """)
    for p, t in [("/v/verwaltung-alt", "Verwaltung A"), ("/v/verwaltung-neu", "Verwaltung B"),
                 ("/v/verwaltung-neuer", "Verwaltung C")]:
        conn.execute("INSERT INTO knowledge_nodes VALUES (?,?,?,?,?)",
                     (p, t, f"Zusammenfassung {t}", f"Volltext {t}", "vertrag,weg"))
    return conn


def _selftest() -> int:
    conn = _kulisse()
    loese_ab(conn, alt="/v/verwaltung-alt", neu="/v/verwaltung-neu",
             grund="Jahresabrechnung dreimal verspaetet, keine Belegeinsicht vor Ort",
             ts="2026-08-01T10:00:00+0200", urheber="betreiber")

    # DER KERN: das Abgeloeste ist vollstaendig erhalten. Kein leerer Inhalt,
    # keine geloeschte Zusammenfassung -- das ist der Unterschied zu
    # knowledge_zurueckziehen, das genau das tut.
    alt = conn.execute("SELECT title, summary, content, tags FROM knowledge_nodes"
                       " WHERE path='/v/verwaltung-alt'").fetchone()
    assert alt[0] == "Verwaltung A" and alt[1] and alt[2], f"Inhalt angetastet: {alt}"
    assert "vertrag" in alt[3] and "weg" in alt[3], f"bestehende Marken verloren: {alt[3]}"
    assert MARKE in alt[3], f"nicht gekennzeichnet: {alt[3]}"

    # Der Leser des ALTEN Eintrags erfaehrt, dass es einen neueren gibt -- samt Grund.
    n = nachfolger(conn, "/v/verwaltung-alt")
    assert n and n["pfad"] == "/v/verwaltung-neu", n
    assert "Belegeinsicht" in n["grund"], n
    assert gilt_noch(conn, "/v/verwaltung-alt") is False
    assert gilt_noch(conn, "/v/verwaltung-neu") is True

    # Kette ueber zwei Stufen: der Grund JEDES Uebergangs bleibt einzeln erhalten,
    # nicht nur der letzte.
    loese_ab(conn, alt="/v/verwaltung-neu", neu="/v/verwaltung-neuer",
             grund="Preis um 40 Prozent erhoeht, Leistung unveraendert",
             ts="2026-08-15T10:00:00+0200")
    kette = vorgaenger(conn, "/v/verwaltung-neuer")
    assert [k["pfad"] for k in kette] == ["/v/verwaltung-neu", "/v/verwaltung-alt"], kette
    assert "Preis" in kette[0]["grund"] and "Belegeinsicht" in kette[1]["grund"], kette

    # Die Uebergangsliste -- der eigentliche Ertrag: was hat sich als
    # unzureichend erwiesen, und warum.
    g = gruende(conn)
    assert len(g) == 2, g
    assert all(e["grund"] for e in g), g

    # Ein Grund ist Pflicht. Ohne ihn waere die Abloesung eine Statusaenderung.
    for schlecht in ("", "   "):
        try:
            loese_ab(conn, alt="/v/verwaltung-alt", neu="/v/verwaltung-neuer",
                     grund=schlecht, ts="2026-08-18T10:00:00+0200")
        except ValueError:
            pass
        else:
            raise AssertionError("Abloesung ohne Grund haette abgewiesen werden muessen")

    # Negativfaelle: Selbstabloesung und unbekannter Knoten.
    for alt_, neu_ in (("/v/verwaltung-alt", "/v/verwaltung-alt"), ("/v/gibtsnicht", "/v/verwaltung-neu")):
        try:
            loese_ab(conn, alt=alt_, neu=neu_, grund="x", ts="2026-08-18T10:00:00+0200")
        except ValueError:
            pass
        else:
            raise AssertionError(f"haette abgewiesen werden muessen: {alt_} -> {neu_}")

    print("abloesung: Selbsttest gruen (Inhalt erhalten, Marke gesetzt, Kette ueber "
          "zwei Stufen mit je eigenem Grund, Grund erzwungen, zwei Negativfaelle)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
