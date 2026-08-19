#!/usr/bin/env python3
"""migrate_lehre_prozedur.py -- Aufgabe 79487bf9, BDW-F03-AC1 (letzte offene
Katalogzeile von 56). Reine DATENmigration: gedaechtnisart, gilt_ab/gilt_bis,
gilt_bis_version existieren auf lessons_learned bereits seit Commit
06391b58 (ADR-030 + Aufgabe 104) -- hier wird keine Spalte geschaffen, nur
zugeordnet und ein Widerrufsweg fuer Prozeduren bereitgestellt.

TEIL 1 -- ZUORDNUNG: 'pattern'-Lehren MIT erkennbarer Schrittfolge bekommen
gedaechtnisart='prozedural'. 'Schrittfolge' heisst hier: mindestens ZWEI
verschiedene nummerierte Marker ('1.', '2)', '(3)' ...) in description,
root_cause, resolution oder prevention. Geprueft und verworfen: Signalwoerter
("zuerst", "dann", "danach") als Zusatzkriterium -- Stichprobe gegen den
gewachsenen Bestand ergab 500 von 1116 Treffern statt der im Plan
(docs/PLAN_GESAMT_2026-08-13.md) genannten 248, weil Fliesstext mit "dann"
fast ueberall vorkommt, ohne eine Prozedur zu sein. Reine Nummerierung liegt
mit 226 Treffern gesamt / 80 bei type='pattern' nahe an der Planzahl (248 /
85) und ist NICHT identisch -- diese Abweichung ist ein Befund, kein Fehler:
die Planzahl war eine grobe Vorabmessung ohne festgehaltene Regel.

Zugeordnet wird NUR type='pattern', nie 'antipattern' (Plan-Entscheidung
99b8e3a9: eine Lehre UEBER einen Fehler bleibt eine Lehre ueber einen Fehler,
auch wenn ihre Vorbeugung Schritte enthaelt -- die Prozedur steckt IN ihr,
sie IST keine). Idempotent: nur Zeilen mit gedaechtnisart != 'prozedural'
werden geprueft, ein zweiter Lauf faengt nichts mehr ein.

TEIL 2 -- WIDERRUF: widerrufe_prozedur() setzt gilt_bis/gilt_bis_version
einer PROZEDURALEN Lehre. Der Eintrag bleibt dabei VOLLSTAENDIG LESBAR --
anders als knowledge_zurueckziehen() in knowledge_mcp_server.py, das
content/summary eines Knotens LEERT und den Wortlaut ins Archiv auslagert.
Der Unterschied ist der Grund fuer BDW-F03-AC1: ein FAKT wird widerrufen,
weil er nicht stimmte (rueckwirkend, der Wortlaut wird zum Beweisstueck);
eine PROZEDUR wird widerrufen, weil sie ab einem Zeitpunkt oder einer
Version nicht mehr funktioniert (nicht rueckwirkend, der Wortlaut bleibt die
Anleitung, nur nicht mehr unbegrenzt gueltig). Der bestehende Fakten-Weg
(knowledge_nodes.zurueckgezogen*, knowledge_widerruf_archiv,
knowledge_mcp_server.py::knowledge_zurueckziehen) wird von dieser Datei
nicht beruehrt.

Usage:
    python3 migrationen/migrate_lehre_prozedur.py [--apply]
    python3 migrationen/migrate_lehre_prozedur.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import zeitmarke

HERE = Path(__file__).parent
WURZEL = _w
DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (WURZEL / "brainlehr.db"))

# Mindestens zwei verschiedene nummerierte Marker -- "1." / "2)" / "(3)".
# \b-lose absichtlich (Klammern zaehlen nicht als Wortgrenze).
_NUM = re.compile(r"(?:^|[\s(])([1-9]\d?)[.)]\s", re.MULTILINE)


def ist_schrittfolge(*teile: str | None) -> bool:
    text = " ".join(t for t in teile if t)
    if not text:
        return False
    marker = {int(m.group(1)) for m in _NUM.finditer(text)}
    return len(marker) >= 2


def _backup(db_path: Path) -> Path:
    conn = sqlite3.connect(str(db_path))
    try:
        busy, log_frames, checkpointed = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if busy:
            raise RuntimeError(
                f"WAL-Checkpoint blockiert (busy={busy}, log={log_frames} Frames, "
                f"{checkpointed} checkpointed) -- ein anderer Prozess schreibt gerade. "
                "Sicherung abgebrochen statt unvollstaendig angelegt."
            )
    finally:
        conn.close()
    stamp = datetime.now(zeitmarke.BERLIN).strftime("%Y%m%dT%H%M%S")
    dest = db_path.parent / f"{db_path.name}.bak-{stamp}"
    shutil.copy2(db_path, dest)
    return dest


def migrate(db_path: Path, apply: bool) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        pattern_zeilen = conn.execute(
            "SELECT id, description, root_cause, resolution, prevention "
            "FROM lessons_learned WHERE type = 'pattern' AND gedaechtnisart != 'prozedural'"
        ).fetchall()
        pattern_gesamt = conn.execute("SELECT COUNT(*) FROM lessons_learned WHERE type = 'pattern'").fetchone()[0]
        bereits_prozedural = conn.execute(
            "SELECT COUNT(*) FROM lessons_learned WHERE gedaechtnisart = 'prozedural'"
        ).fetchone()[0]
    finally:
        conn.close()

    kandidaten = [row[0] for row in pattern_zeilen if ist_schrittfolge(*row[1:])]

    result = {
        "pattern_gesamt": pattern_gesamt,
        "bereits_prozedural_vorher": bereits_prozedural,
        "kandidaten": len(kandidaten),
        "backup": None,
        "neu_prozedural": 0,
    }
    if not kandidaten or not apply:
        return result

    backup_path = _backup(db_path)
    result["backup"] = str(backup_path)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.executemany(
            "UPDATE lessons_learned SET gedaechtnisart = 'prozedural' WHERE id = ?",
            [(i,) for i in kandidaten],
        )
        conn.commit()
        result["neu_prozedural"] = len(kandidaten)
        result["prozedural_nachher"] = conn.execute(
            "SELECT COUNT(*) FROM lessons_learned WHERE gedaechtnisart = 'prozedural'"
        ).fetchone()[0]
        result["episodisch_bleibt"] = conn.execute(
            "SELECT COUNT(*) FROM lessons_learned WHERE gedaechtnisart != 'prozedural'"
        ).fetchone()[0]
    finally:
        conn.close()
    return result


def widerrufe_prozedur(
    conn: sqlite3.Connection,
    lehre_id: str,
    gilt_bis: str,
    gilt_bis_version: str | None = None,
) -> None:
    """Setzt eine Grenze auf eine PROZEDURALE Lehre, ohne sie zu leeren.

    Negativfall: eine Lehre, die nicht als prozedural gilt, ist kein
    gueltiges Ziel -- Widerruf gehoert an die Prozedur, nicht an die
    Beobachtung dahinter (siehe Moduldocstring)."""
    row = conn.execute(
        "SELECT gedaechtnisart FROM lessons_learned WHERE id = ?", (lehre_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"Lehre {lehre_id!r} nicht gefunden -- nichts widerrufen")
    if row[0] != "prozedural":
        raise ValueError(
            f"Lehre {lehre_id!r} ist gedaechtnisart={row[0]!r}, nicht 'prozedural' -- "
            "widerrufe_prozedur() ist kein Ersatz fuer knowledge_zurueckziehen()"
        )
    conn.execute(
        "UPDATE lessons_learned SET gilt_bis = ?, gilt_bis_version = ? WHERE id = ?",
        (gilt_bis, gilt_bis_version, lehre_id),
    )
    conn.commit()


def main() -> int:
    apply = "--apply" in sys.argv
    if "--selftest" in sys.argv:
        return _selftest()

    print(f"Datenbank: {DB_PATH}")
    if not DB_PATH.exists():
        print(f"FEHLER: {DB_PATH} nicht gefunden.")
        return 1

    res = migrate(DB_PATH, apply=apply)
    mode = "APPLY" if apply else "DRY-RUN (kein --apply)"
    print(f"=== migrate_lehre_prozedur ({mode}) ===")
    print(f"pattern gesamt: {res['pattern_gesamt']}, bereits prozedural vorher: "
          f"{res['bereits_prozedural_vorher']}, Kandidaten (Schrittfolge): {res['kandidaten']}")
    if res["backup"]:
        print(f"Sicherung: {res['backup']}")
        print(f"neu auf prozedural gesetzt: {res['neu_prozedural']}")
        print(f"prozedural nachher gesamt: {res['prozedural_nachher']}, "
              f"bleibt episodisch/semantisch: {res['episodisch_bleibt']}")
    return 0


FESTER_COMMIT = "06391b58"  # traegt gedaechtnisart/gilt_ab/gilt_bis/bezug/gilt_bis_version bereits


def _tabellenblock(tabelle: str) -> str:
    import subprocess
    alt_schema = subprocess.run(
        ["git", "show", f"{FESTER_COMMIT}:schema.sql"],
        cwd=WURZEL, capture_output=True, text=True, check=True,
    ).stdout
    start = alt_schema.index(f"CREATE TABLE IF NOT EXISTS {tabelle}")
    ende = alt_schema.index("\n);", start) + 3
    return alt_schema[start:ende]


def _alter_tabellenblock() -> str:
    return _tabellenblock("lessons_learned")


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "brainlehr.db"
        block = _alter_tabellenblock()
        for spalte in ("gedaechtnisart", "gilt_ab", "gilt_bis", "gilt_bis_version"):
            assert spalte in block, (
                f"{spalte} fehlt im Fixpunkt-Commit {FESTER_COMMIT} -- falscher Fixpunkt gewaehlt"
            )
        conn = sqlite3.connect(str(db_path))
        conn.executescript(block)
        # Nur fuer die Gegenprobe Fakt-vs-Prozedur ganz unten: die
        # knowledge_nodes-Tabelle desselben Fixpunkts, damit der
        # Fakten-Widerruf (zurueckgezogen/content-Leerung) neben dem
        # Prozedur-Widerruf steht -- diese Datei aendert an knowledge_nodes
        # nichts, sie liest hier nur ihr CREATE-TABLE fuer den Vergleich.
        conn.executescript(_tabellenblock("knowledge_nodes"))

        # (1) pattern MIT Schrittfolge -- soll prozedural werden. ROT vor dem
        # Lauf: gedaechtnisart traegt noch die Vorgabe 'episodisch'.
        conn.execute(
            "INSERT INTO lessons_learned (id, type, description, resolution, anlass, bemerkt_woran) "
            "VALUES ('L-schritt', 'pattern', 'Verfahren X', "
            "'1. Erst A pruefen. 2. Dann B ausfuehren. 3. Ergebnis loggen.', 'skript', 'test')"
        )
        # (2) pattern OHNE Schrittfolge -- bleibt episodisch (Negativfall).
        conn.execute(
            "INSERT INTO lessons_learned (id, type, description, resolution, anlass, bemerkt_woran) "
            "VALUES ('L-ohne', 'pattern', 'Verfahren Y', 'Einfach X tun.', 'skript', 'test')"
        )
        # (3) antipattern MIT Schrittfolge in prevention -- bleibt episodisch
        # (Punkt 3 der Abnahme, der wichtigere Fall: Schritte allein reichen
        # nicht, es muss 'pattern' sein).
        conn.execute(
            "INSERT INTO lessons_learned (id, type, description, prevention, anlass, bemerkt_woran) "
            "VALUES ('L-anti', 'antipattern', 'Fehler Z', "
            "'1. Nie A ohne B. 2. Nie C uebergehen.', 'skript', 'test')"
        )
        conn.commit()

        vor = dict(conn.execute("SELECT id, gedaechtnisart FROM lessons_learned").fetchall())
        assert vor == {"L-schritt": "episodisch", "L-ohne": "episodisch", "L-anti": "episodisch"}, vor
        conn.close()

        res1 = migrate(db_path, apply=True)
        assert res1["kandidaten"] == 1, res1
        assert res1["neu_prozedural"] == 1, res1
        assert res1["backup"] and Path(res1["backup"]).exists()

        conn = sqlite3.connect(str(db_path))
        nach = dict(conn.execute("SELECT id, gedaechtnisart FROM lessons_learned").fetchall())
        assert nach["L-schritt"] == "prozedural", nach          # GRUEN: Positivfall
        assert nach["L-ohne"] == "episodisch", nach              # Gegenprobe: keine Schritte
        assert nach["L-anti"] == "episodisch", nach               # Gegenprobe: nicht 'pattern'

        # (4) Idempotenz: zweiter Lauf faengt nichts mehr.
        res2 = migrate(db_path, apply=True)
        assert res2["kandidaten"] == 0 and res2["neu_prozedural"] == 0 and res2["backup"] is None, res2

        # (5) Widerruf einer Prozedur -- bleibt lesbar, nur eine Grenze dazu.
        original_resolution = conn.execute(
            "SELECT resolution FROM lessons_learned WHERE id = 'L-schritt'"
        ).fetchone()[0]
        widerrufe_prozedur(conn, "L-schritt", "2026-08-19", gilt_bis_version="9.9.9")
        zeile = conn.execute(
            "SELECT resolution, gilt_bis, gilt_bis_version FROM lessons_learned WHERE id = 'L-schritt'"
        ).fetchone()
        assert zeile[0] == original_resolution, "Widerruf einer Prozedur hat den Wortlaut veraendert -- falsch"
        assert zeile[1] == "2026-08-19" and zeile[2] == "9.9.9"

        # Negativfall: eine nicht-prozedurale Lehre ist kein gueltiges Ziel.
        try:
            widerrufe_prozedur(conn, "L-ohne", "2026-08-19")
            fehlgeschlagen = False
        except ValueError:
            fehlgeschlagen = True
        assert fehlgeschlagen, "widerrufe_prozedur haette eine episodische Lehre ablehnen muessen"

        # Gegenprobe zum FAKT-Weg, EIN Testfall (Abnahme Punkt 4): ein Fakt
        # wird nach demselben Muster wie
        # knowledge_mcp_server.py::knowledge_zurueckziehen widerrufen
        # (content/summary geleert) -- OHNE dass diese Datei den Fakten-Weg
        # anfasst, nur zum Vergleich in derselben Pruefung nachgebaut.
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, title, summary, content) "
            "VALUES ('n1', '/test/fakt', 'Ein Fakt', 'stimmte nicht', 'urspruenglicher Wortlaut')"
        )
        conn.execute(
            "UPDATE knowledge_nodes SET zurueckgezogen = 1, zurueckgezogen_grund = 'war falsch', "
            "content = '', summary = '' WHERE id = 'n1'"
        )
        fakt = conn.execute(
            "SELECT title, summary, content, zurueckgezogen FROM knowledge_nodes WHERE id = 'n1'"
        ).fetchone()
        prozedur = conn.execute(
            "SELECT resolution, gilt_bis FROM lessons_learned WHERE id = 'L-schritt'"
        ).fetchone()
        assert fakt[3] == 1 and fakt[1] == "" and fakt[2] == "", (
            "Fakten-Widerruf haette Inhalt leeren muessen"
        )
        assert prozedur[0] == original_resolution and prozedur[1] == "2026-08-19", (
            "Prozedur-Widerruf haette den Wortlaut NICHT leeren duerfen"
        )
        conn.close()

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
