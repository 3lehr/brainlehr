#!/usr/bin/env python3
"""Forderung ans eigene Haus: erkennen (Vorlage), markieren, auflisten.

ANLASS: Auftrag F, docs/PLAN_BETRIEBSPROFILE_2026-08-20.md Abschnitt F.
Ein Knoten mit Rang 1 vom 2026-08-16 verlangt woertlich "einen Waechter,
keinen Vorsatz" -- vier Tage spaeter war keiner gebaut, weil nichts danach
gefragt hat. knowledge_nodes.forderung_stand traegt seit B1 die Spalte
(schema.sql), dieses Skript ist die einzige Schreibstelle dafuer.

DREI BEFEHLE:

    python3 melder/forderung_vorgang.py --kandidaten     # Vorlage, KEIN Schreibvorgang
    python3 melder/forderung_vorgang.py --markieren PATH offen
    python3 melder/forderung_vorgang.py --markieren PATH abgelehnt --grund "..."
    python3 melder/forderung_vorgang.py --offene          # Liste, aelteste zuerst
    python3 melder/forderung_vorgang.py --selftest

WAS HIER AUSDRUECKLICH NICHT PASSIERT: --kandidaten SCHREIBT NICHTS. Eine
Textsuche ist eine Vorlage fuer einen Menschen, nie die Markierung selbst --
sonst waere forderung_stand wieder geraten statt erkannt (Auftrag F1). Nur
--markieren schreibt, und zwar genau EINEN Knoten, genau EINMAL aufgerufen.

WARUM EIN EIGENES SKRIPT UND NICHT knowledge_add/knowledge_update: beide
Funktionen (knowledge_mcp_server.py) kennen forderung_stand nicht -- diese
Datei ist im Auftrag ausdruecklich nicht anzufassen. Die Haerte liegt darum
komplett in den vier DB-Triggern (schema.sql, Dateiende); dieses Skript ist
nur ein duenner Aufrufer davon und validiert nichts doppelt.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "kern"))
import speicher  # noqa: E402

ZUSTAENDE = ("offen", "erledigt", "abgelehnt", "ueberholt")

# Vorlage, kein Ersatz fuer menschliches Lesen (Auftrag: "zwei von drei
# Meldern waren am 2026-08-20 beim ersten Lauf gegen den echten Bestand
# falsch" -- jeder Treffer hier ist ein VERDACHT, keine Feststellung).
_DEMAND_MUSTER = (
    "muss gebaut", "braucht einen", "braucht eine", "fehlt noch ein",
    "fehlt noch eine", "umsetzen", "noch nicht gebaut", "steht noch aus",
    "einen wächter", "verlangt wörtlich", "verlangt einen",
    "keinen vorsatz",
)


def kandidaten(db: Path | None = None, haus: str = "brainlehr") -> list[dict]:
    """Textbasierte VORLAGE fuer die menschliche Sichtung -- kein Schreiben,
    keine Markierung. Sucht nur in Titel+Summary, nicht im vollen Content
    (Content kann Zitate fremder Forderungen enthalten, die dann faelschlich
    als eigene erschienen)."""
    try:
        with speicher.lesen(db) as con:
            rows = con.execute(
                "SELECT path, title, summary, created_at, forderung_stand "
                "FROM knowledge_nodes WHERE zurueckgezogen = 0"
            ).fetchall()
    except sqlite3.OperationalError:
        return []
    treffer = []
    for r in rows:
        d = dict(r)
        text = f"{d['title'] or ''} {d['summary'] or ''}".lower()
        ist_haus = haus in (d["path"] or "").lower() or haus in (d["title"] or "").lower()
        if ist_haus and any(m in text for m in _DEMAND_MUSTER):
            treffer.append(d)
    return sorted(treffer, key=lambda d: d["created_at"] or "")


def markiere(path: str, stand: str, grund: str | None = None, db: Path | None = None) -> None:
    """Setzt forderung_stand (und ggf. forderung_grund) fuer GENAU einen
    Knoten. Wertebereich und Grundpflicht werden von den DB-Triggern erzwungen
    -- hier keine Doppelpruefung, damit es keine zweite Wahrheit gibt."""
    with speicher.schreiben(db) as con:
        cur = con.execute(
            "UPDATE knowledge_nodes SET forderung_stand = ?, forderung_grund = ? WHERE path = ?",
            (stand, grund, path),
        )
        if cur.rowcount == 0:
            raise ValueError(f"kein Knoten unter path={path!r}")


def offene(db: Path | None = None) -> list[dict]:
    """Offene Vorgaenge, aeltester zuerst -- Quelle fuer den Sitzungsstart-
    Kanal (melder/eilmeldung_faellig.py)."""
    try:
        with speicher.lesen(db) as con:
            rows = con.execute(
                "SELECT path, title, created_at FROM knowledge_nodes "
                "WHERE zurueckgezogen = 0 AND forderung_stand = 'offen' "
                "ORDER BY created_at ASC"
            ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [dict(r) for r in rows]


def _selftest() -> None:
    import tempfile

    wurzel = Path(__file__).resolve().parent.parent
    schema = (wurzel / "schema.sql").read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmp_dir:
        db = Path(tmp_dir) / "test.db"
        conn = sqlite3.connect(str(db))
        conn.executescript(schema)
        for zeile in (
            ("a", "/brainlehr/alt", "Altvorgang", "2026-08-08T09:00:00Z"),
            ("b", "/brainlehr/neu", "Neuvorgang", "2026-08-20T09:00:00Z"),
            ("c", "/andere/sache", "Kein Vorgang", "2026-08-01T09:00:00Z"),
        ):
            conn.execute(
                "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, "
                "level, source, created_at, norm_entscheidung, norm_entschieden_von, "
                "norm_entschieden_grund) VALUES (?,?,?,?,?,?,0,?,?,'keine_norm','test',"
                "'Testvorrichtung, keine echte Norm-Pruefung')",
                (zeile[0], zeile[1], "shared", zeile[2], "x", "x", "test", zeile[3]),
            )
        conn.commit()
        conn.close()

        # Neuer Knoten ohne Angabe bekommt KEINEN stillen Vorgabewert.
        with speicher.lesen(db) as con:
            stand = con.execute("SELECT forderung_stand FROM knowledge_nodes WHERE path='/andere/sache'").fetchone()[0]
        assert stand is None, ("stiller Vorgabewert entstanden", stand)

        markiere("/brainlehr/alt", "offen", db=db)
        markiere("/brainlehr/neu", "offen", db=db)

        off = offene(db)
        assert [o["path"] for o in off] == ["/brainlehr/alt", "/brainlehr/neu"], off

        # ROT-Probe: Ablehnung ohne Grund scheitert.
        try:
            markiere("/brainlehr/alt", "abgelehnt", db=db)
            assert False, "Ablehnung ohne Grund haette scheitern muessen"
        except sqlite3.IntegrityError:
            pass

        # Gegenprobe: mit Grund gelingt es, und der Knoten verschwindet aus
        # der offenen Liste (Abschluss wirkt).
        markiere("/brainlehr/alt", "abgelehnt", grund="Testvorrichtung, kein echter Vorgang", db=db)
        off = offene(db)
        assert [o["path"] for o in off] == ["/brainlehr/neu"], off

        # Negativfall: unbekannter Zustandswert scheitert.
        try:
            markiere("/brainlehr/neu", "irgendwas", db=db)
            assert False, "unbekannter Zustand haette scheitern muessen"
        except sqlite3.IntegrityError:
            pass

        # Kein Ruecksfall auf NULL, sobald einmal markiert.
        try:
            with speicher.schreiben(db) as con:
                con.execute("UPDATE knowledge_nodes SET forderung_stand = NULL WHERE path = '/brainlehr/neu'")
            assert False, "Ruecksetzen auf NULL haette scheitern muessen"
        except sqlite3.IntegrityError:
            pass

        # Nach Erledigung verschwindet der Knoten aus der offenen Liste.
        markiere("/brainlehr/neu", "erledigt", db=db)
        assert offene(db) == [], offene(db)

    print("forderung_vorgang: Selbsttest gruen")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--kandidaten", action="store_true")
    p.add_argument("--markieren", nargs=2, metavar=("PATH", "STAND"))
    p.add_argument("--grund", default=None)
    p.add_argument("--offene", action="store_true")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--db", type=Path, default=None)
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return
    if a.markieren:
        path, stand = a.markieren
        markiere(path, stand, grund=a.grund, db=a.db)
        print(f"markiert: {path} -> {stand}")
        return
    if a.offene:
        for o in offene(a.db):
            print(f"{o['created_at']}  {o['path']}  {o['title']}")
        return
    for k in kandidaten(a.db):
        print(f"{k['created_at']}  stand={k['forderung_stand']}  {k['path']}  {k['title']}")


if __name__ == "__main__":
    main()
