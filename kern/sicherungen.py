#!/usr/bin/env python3
"""Aufbewahrungsregel fuer die automatischen Datenbanksicherungen.

DER BEFUND, 2026-08-14: 312 Sicherungsdateien, zusammen 22 GB, entstanden in
drei Tagen -- und die Platte stand bei 100 Prozent Belegung mit 9,6 GB Rest.
Ursache ist keine Nachlaessigkeit an einer Stelle, sondern eine Luecke im
Bauplan: 14 Stellen legen eine Vollkopie an (allein zehn in
knowledge_mcp_server.py, dazu kern/build_embeddings.py, kern/normbestand.py,
kern/migrate_relations.py), und KEINE einzige raeumt auf. Jede fuer sich ist
richtig -- eine Sicherung vor einem Schemaeingriff ist gute Praxis. Zusammen
sind sie ein Leck.

WARUM HIER UND NICHT AN DEN 14 STELLEN: Eine Regel, die an jeder Schreibstelle
haengt, muss vierzehnmal richtig eingebaut werden und beim naechsten
Schreibpfad ein fuenfzehntes Mal. Eine Regel, die ueber das VERZEICHNIS laeuft,
wirkt auf alle -- auch auf die, die es noch nicht gibt. Sie ist deshalb
absichtlich nicht an das Anlegen gekoppelt, sondern an den Start.

WAS SIE NICHT TUT: Sie entscheidet nicht, ob eine Sicherung wertvoll ist. Sie
kennt nur Alter und Anzahl. Eine Sicherung, die jemand aufheben will, gehoert
umbenannt -- alles ohne das Muster `<db>.bak-*` wird nie angefasst. Das ist
die Rueckfallebene fuer den Menschen, und sie ist absichtlich so grob.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken")]

from pathlib import Path

# Wieviele der juengsten automatischen Sicherungen bleiben liegen.
# Zehn, weil eine Sicherung genau einen Zweck hat: den Schritt zurueck, der
# gerade schiefging. Wer zwanzig Schritte zurueck will, will in Wahrheit ein
# Archiv, und ein Archiv gehoert nicht neben die Betriebsdatenbank.
BEHALTE = 10

# Nur DIESE Form wird aufgeraeumt. Von Hand vergebene Namen
# (`brainlehr.db.vor_utc_2026-08-14`, `.bak-...-normherkunft`) tragen einen
# Zweck im Namen und werden NIE angefasst -- Umbenennen ist damit der Weg,
# eine Sicherung dauerhaft zu behalten.
MUSTER = ".bak-"


def _automatisch(p: Path, db_name: str) -> bool:
    """Traegt die Datei den maschinell erzeugten Zeitstempelnamen?

    `<db>.bak-20260814T113559` ja, `<db>.bak-20260814T113746-normherkunft`
    NEIN -- der Zusatz hinter dem Zeitstempel ist die Handschrift eines
    Menschen, der wusste, wofuer er sichert.
    """
    if not p.name.startswith(db_name + MUSTER):
        return False
    rest = p.name[len(db_name) + len(MUSTER):]
    return len(rest) == 15 and rest[8] == "T" and rest.replace("T", "").isdigit()


def kandidaten(db_pfad: Path) -> list[Path]:
    """Automatische Sicherungen, juengste zuerst."""
    ordner = db_pfad.parent
    if not ordner.is_dir():
        return []
    treffer = [p for p in ordner.iterdir() if _automatisch(p, db_pfad.name)]
    return sorted(treffer, key=lambda p: p.name, reverse=True)


def aufraeumen(db_pfad: Path, behalte: int = BEHALTE) -> tuple[int, int]:
    """Loescht alle bis auf die `behalte` juengsten. Gibt (geloescht, bytes).

    Nie blockierend: eine Datei, die sich nicht loeschen laesst (fremder
    Halter, Rechte), wird uebersprungen statt zu werfen. Diese Funktion darf
    einen Serverstart unter keinen Umstaenden verhindern -- sie raeumt auf,
    sie ist nicht der Zweck.
    """
    alt = kandidaten(db_pfad)[behalte:]
    n = groesse = 0
    for p in alt:
        try:
            groesse += p.stat().st_size
            p.unlink()
            n += 1
        except OSError:
            continue
    return n, groesse


def aufraeumen_still(db_pfad) -> tuple[int, int]:
    """Wie aufraeumen(), aber verschluckt JEDEN Fehler und gibt (0, 0) zurueck.

    Fuer Aufrufer, deren eigentlicher Zweck ein anderer ist -- der MCP-Server
    ruft das beim Start. Ein Aufraeumfehler darf einen Serverstart unter
    keinen Umstaenden verhindern; er haette dieselbe Wirkung wie das Leck,
    gegen das er gebaut ist, nur schneller.
    """
    try:
        return aufraeumen(Path(db_pfad))
    except Exception:
        return (0, 0)


def _selftest() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        db = d / "brainlehr.db"
        db.write_bytes(b"x")
        for i in range(15):
            (d / f"brainlehr.db.bak-2026081{i//10}T00000{i%10}").write_bytes(b"y" * 100)
        # Von Hand benannte bleiben, egal wie alt.
        (d / "brainlehr.db.bak-20260801T000000-vor-umbau").write_bytes(b"z")
        (d / "brainlehr.db.vor_utc_2026-08-14").write_bytes(b"z")
        (d / "brainlehr.db-wal").write_bytes(b"z")

        assert len(kandidaten(db)) == 15, len(kandidaten(db))
        n, _ = aufraeumen(db, behalte=10)
        assert n == 5, n
        assert len(kandidaten(db)) == 10

        # NEGATIVFALL, der wichtigere: nichts ausser der Zeitstempelform
        # wurde angefasst. Ein Mensch, der eine Sicherung behalten will,
        # benennt sie um -- diese Zusicherung ist sein Verlass darauf.
        for name in ("brainlehr.db", "brainlehr.db.bak-20260801T000000-vor-umbau",
                     "brainlehr.db.vor_utc_2026-08-14", "brainlehr.db-wal"):
            assert (d / name).exists(), f"{name} haette nicht angefasst werden duerfen"

        # Grenzwert: genau `behalte` vorhanden -> nichts zu tun.
        n2, _ = aufraeumen(db, behalte=10)
        assert n2 == 0, n2
        # Und behalte=0 raeumt alles Automatische weg, sonst nichts.
        n3, _ = aufraeumen(db, behalte=0)
        assert n3 == 10 and (d / "brainlehr.db").exists()
        # aufraeumen_still schluckt auch einen kaputten Pfad.
        assert aufraeumen_still("/gibt/es/nicht/db") == (0, 0)
    print("selftest ok (6 Faelle): juengste bleiben, Handnamen bleiben, "
          "Grenzwert, behalte=0 und stiller Fehlerfall geprueft")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        import ort
        n, b = aufraeumen(Path(ort.DB))
        print(f"{n} automatische Sicherungen entfernt, {b/1e9:.1f} GB frei")
