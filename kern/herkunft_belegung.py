#!/usr/bin/env python3
"""herkunft_belegung.py -- Belegungstabelle der Herkunftsfelder, gegen den
ECHTEN Bestand gemessen (Aufgabe J4, docs/PLAN_GESAMT_2026-08-13.md).

ANLASS: J4 verlangt "Herkunft als Pflichtfeld". Vor jeder Pflicht steht die
Messung, welche Felder ueberhaupt wie voll sind -- eine Handmessung veraltet
beim naechsten Schreiben, dieses Werkzeug nicht.

BEFUND, der die Pflicht in dieser Form ABLEHNT (kein Feld wird hier
erzwungen): bedient_von ist bei der grossen Mehrheit der Zeilen ABSICHTLICH
leer -- schema.sql (Spaltenkommentar an knowledge_nodes.bedient_von) haelt
das ausdruecklich fest: "LEER ist der Normalfall und kein Mangel". Der Wert
kommt AUSSCHLIESSLICH aus dem beglaubigten Ausweis (nie aus einem Argument,
Betreiberweisung 2026-08-11) -- genau die Bauform, die L-34e5f8 fordert
(Herkunft aus dem Ausweis, nicht aus einer Behauptung im Aufruf). Eine
NOT-NULL-Pflicht auf bedient_von wuerde jeden unbeglaubigten Schreiber und
jeden Menschen an der Wurzel der Kette (niemand steht ueber ihm) ablehnen --
bestehende, legitime Schreibwege waeren gebrochen. Das ist die Falle, vor der
CLAUDE.md warnt: "Eine Pflicht, die bestehende Aufrufer bricht, ist falsch
geschnitten."

GEMESSEN, live, am 2026-08-15: Knoten 2211 (/woanders, erzeugt
2026-08-15T09:17:03Z durch den internen Astknoten-Erzeuger
_ensure_ast_chain() in knowledge_mcp_server.py) traegt AUCH actor/session/
model/client als NULL -- ein Schreibpfad, der IDENTITY() umgeht, obwohl er im
selben Prozess laeuft wie jeder andere Schreibvorgang. Dieser Pfad liegt in
knowledge_mcp_server.py, das waehrend dieser Sitzung tabu ist (parallele
Bearbeitung). Eine Pflicht ueber actor/session/model/client wuerde also
GENAU DIESEN, heute lebendigen und legitimen Schreiber brechen -- Beleg fuer
dieselbe Falle wie bei bedient_von, an anderer Stelle.

WAS DIESES WERKZEUG STATTDESSEN IST: die Messung, die jede kuenftige
Entscheidung ueber eine Pflicht braucht, wiederholbar statt einmalig. Es
erzwingt nichts.

'Leer' fasst NULL, Leerstring, reine Leerzeichen UND den Text 'unbekannt'
zusammen -- dieselbe Definition, die speicher.normiere_akteur() fuer die
Normierung (Aufgabe 79) schon durchsetzt. Wiederverwendet statt zweimal
definiert.

Aufruf:
    python3 kern/herkunft_belegung.py --bericht
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

from pathlib import Path

import speicher  # noqa: E402

# Tabelle -> Herkunftsfelder, die dort tatsaechlich existieren (schema.sql).
FELDER: dict[str, tuple[str, ...]] = {
    "knowledge_nodes": ("abgeleitet_von", "bedient_von", "actor", "session", "model", "client"),
    "lessons_learned": ("bedient_von", "actor", "session", "model", "client"),
    "access_log": ("bedient_von", "actor", "session", "model", "client"),
}


def _ist_leer(wert: object) -> bool:
    """NULL/Leerstring/Leerzeichen/'unbekannt' -- dieselbe Zusammenfassung
    wie speicher.normiere_akteur(), hier wiederverwendet statt neu gebaut."""
    return speicher.normiere_akteur(wert if wert is None else str(wert)) is None


def belegung(db: Path | str | None = None) -> dict[str, dict[str, tuple[int, int]]]:
    """Je Tabelle und Feld: (Anzahl leer, Anzahl gesamt) -- gegen den
    tatsaechlichen Bestand, keine Schaetzung. Eine leere Tabelle liefert
    (0, 0), keinen Fehler."""
    ergebnis: dict[str, dict[str, tuple[int, int]]] = {}
    with speicher.lesen(db) as conn:
        for tabelle, felder in FELDER.items():
            ergebnis[tabelle] = {}
            for feld in felder:
                zeilen = conn.execute(f"SELECT {feld} FROM {tabelle}").fetchall()
                gesamt = len(zeilen)
                leer = sum(1 for z in zeilen if _ist_leer(z[0]))
                ergebnis[tabelle][feld] = (leer, gesamt)
    return ergebnis


def bericht(ergebnis: dict[str, dict[str, tuple[int, int]]]) -> str:
    zeilen = ["Belegungstabelle Herkunftsfelder -- leer / gesamt"]
    for tabelle, felder in ergebnis.items():
        zeilen.append(f"\n{tabelle}:")
        for feld, (leer, gesamt) in felder.items():
            anteil = f"{leer / gesamt:.0%}" if gesamt else "n/a"
            zeilen.append(f"  {feld:20s} {leer:6d} / {gesamt:<6d} ({anteil} leer)")
    return "\n".join(zeilen)


def _selftest() -> None:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    db = tmp / "probe.db"
    schema = (_w / "schema.sql").read_text(encoding="utf-8")
    # Keine eigene sqlite3.connect() hier (tests/test_naht_ratsche.py haelt
    # die Zahl der Dateien mit eigener Verbindung fest) -- Aufbau ueber die
    # schreibende Tuer, die speicher.py ohnehin schon oeffnet.
    with speicher.schreiben(db) as conn:
        conn.executescript(schema)

    ergebnis = belegung(db)
    assert ergebnis["lessons_learned"]["bedient_von"] == (0, 0), "leere Tabelle -> Nenner 0"
    for tabelle in FELDER:
        assert tabelle in ergebnis
    text = bericht(ergebnis)
    assert "knowledge_nodes" in text and "n/a" in text
    print("selftest ok", file=_sys.stderr)


def main() -> int:
    if "--selftest" in _sys.argv:
        _selftest()
        return 0
    if "--bericht" in _sys.argv:
        print(bericht(belegung()))
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
