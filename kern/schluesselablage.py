#!/usr/bin/env python3
"""schluesselablage.py -- die Schluessel liegen in einer EIGENEN Datei.

ADR-029 sagt: der Schluessel entscheidet die Loeschung, nicht die Zeile.
Damit das mehr ist als eine Absicht, muss der Schluessel den Prozess
ueberleben -- `kern/kundenschluessel.py` haelt ihn in einem dict und ist
deshalb bis heute an keinen Schreibpfad angeschlossen (gemessen 2026-08-19,
BDW-E07 auf FAIL).

WARUM EINE EIGENE DATEI und nicht eine Tabelle in brainlehr.db: Eine
Sicherung des Bestands ist eine Bytekopie. Laegen die Schluessel darin, waere
jede Sicherung eine vollstaendige Kopie von Schloss UND Schluessel -- und die
Vernichtung eines Schluessels waere aus jeder alten Sicherung wieder
herstellbar. Genau das soll Crypto-Shredding verhindern. Getrennte Datei
heisst: die Sicherungsregel fuer den Bestand fasst die Schluessel nicht an.

Der Ort kommt aus `BRAINLEHR_SCHLUESSEL`, sonst `schluessel.db` neben der
Datenbank. Ein Schluessel wird NIE ausgegeben (kein print, kein Log) --
`hole()` gibt ihn an den Aufrufer im selben Prozess zurueck, mehr nicht.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken")]

ORT_UMGEBUNG = "BRAINLEHR_SCHLUESSEL"


def pfad() -> Path:
    gesetzt = os.environ.get(ORT_UMGEBUNG, "").strip()
    if gesetzt:
        return Path(gesetzt)
    import ort  # noqa: E402  -- nie den DB-Namen selbst zusammenbauen
    return Path(ort.DB).parent / "schluessel.db"


def _conn(p: Path | None = None) -> sqlite3.Connection:
    p = p or pfad()
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(p))
    c.execute(
        "create table if not exists schluessel ("
        " ref TEXT PRIMARY KEY,"
        " geheim BLOB NOT NULL,"
        " angelegt_ts REAL NOT NULL)")
    # Die TATSACHE eines vernichteten Schluessels bleibt -- sonst laesst sich
    # spaeter nicht unterscheiden, ob es nie einen gab oder ob er weg ist.
    # Genau diese Unterscheidung ist der Nachweis, dass nicht heimlich
    # geloescht wurde (ADR-029).
    c.execute(
        "create table if not exists vernichtet ("
        " ref TEXT PRIMARY KEY,"
        " angelegt_ts REAL NOT NULL,"
        " vernichtet_ts REAL NOT NULL)")
    c.commit()
    return c


def anlegen(ref: str, ts: float, p: Path | None = None) -> bytes:
    """Neuer Schluessel fuer ref. Gibt ihn zurueck, gibt ihn NIE aus."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    geheim = AESGCM.generate_key(bit_length=256)
    c = _conn(p)
    c.execute("insert or replace into schluessel (ref, geheim, angelegt_ts) values (?,?,?)",
              (ref, geheim, ts))
    c.commit()
    c.close()
    return geheim


def hole(ref: str, p: Path | None = None) -> bytes | None:
    c = _conn(p)
    r = c.execute("select geheim from schluessel where ref = ?", (ref,)).fetchone()
    c.close()
    return r[0] if r else None


def vernichten(ref: str, ts: float, p: Path | None = None) -> bool:
    """Schluessel weg, Tatsache bleibt. Gibt zurueck, ob es einen gab."""
    c = _conn(p)
    r = c.execute("select angelegt_ts from schluessel where ref = ?", (ref,)).fetchone()
    if r is None:
        c.close()
        return False
    c.execute("insert or replace into vernichtet (ref, angelegt_ts, vernichtet_ts) "
              "values (?,?,?)", (ref, r[0], ts))
    c.execute("delete from schluessel where ref = ?", (ref,))
    c.commit()
    c.close()
    return True


def lage(ref: str, p: Path | None = None) -> str:
    """'vorhanden' | 'vernichtet' | 'unbekannt' -- drei Faelle, nicht zwei."""
    c = _conn(p)
    try:
        if c.execute("select 1 from schluessel where ref = ?", (ref,)).fetchone():
            return "vorhanden"
        if c.execute("select 1 from vernichtet where ref = ?", (ref,)).fetchone():
            return "vernichtet"
        return "unbekannt"
    finally:
        c.close()


def _selftest() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "s.db"
        assert lage("a", p) == "unbekannt"
        k = anlegen("a", 100.0, p)
        assert len(k) == 32 and hole("a", p) == k
        assert lage("a", p) == "vorhanden"

        # NEUSTART: der Punkt der ganzen Datei. Eine neue Verbindung sieht
        # denselben Schluessel -- das kann die dict-Ablage in
        # kern/kundenschluessel.py prinzipiell nicht.
        assert hole("a", p) == k

        assert vernichten("a", 200.0, p) is True
        assert hole("a", p) is None
        # Die TATSACHE bleibt -- 'vernichtet' ist nicht 'unbekannt'.
        assert lage("a", p) == "vernichtet"
        assert vernichten("a", 300.0, p) is False, "zweite Vernichtung meldet nichts Neues"

        # NEGATIVFALL: ein nie angelegter ref bleibt unbekannt, auch nach
        # einer Vernichtung an anderer Stelle.
        assert lage("b", p) == "unbekannt"

        # Und der Ort ist NICHT die Bestandsdatenbank.
        import ort
        assert pfad() != Path(ort.DB), pfad()
        assert pfad().name == "schluessel.db", pfad()
    print("schluesselablage: Selbsttest gruen (6 Faelle: anlegen, ueber "
          "Verbindungen hinweg lesen, vernichten, Tatsache bleibt, zweite "
          "Vernichtung folgenlos, Ort getrennt vom Bestand)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(f"Schluesselablage: {pfad()}")
