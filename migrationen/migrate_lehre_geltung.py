#!/usr/bin/env python3
"""migrate_lehre_geltung.py -- Aufgabe 79487bf9 (ADR-030).

Additive Migration (Vorbild migrate_gedaechtnisart.py) auf lessons_learned:

1. Vier Spalten: gilt_ab, gilt_bis, bezug (JSON-Array, KEIN Vorgabewert),
   gilt_bis_version. Leer heisst unbefristet/ungeprueft, NICHT unbekannt.
   bezug bleibt NULL bis zur ersten Pruefung -- '[]' heisst 'geprueft,
   kein Produkt gefunden' und ist etwas anderes als 'noch nicht geprueft'
   (sonst waere eine bereits mit Vorgabewert angelegte Spalte von einer
   echten Negativpruefung nicht mehr unterscheidbar, Falle 'zwei
   Ausgangszustaende').
2. Zwei BEFORE-Trigger (bi/bu): gilt_bis darf nicht vor gilt_ab liegen.
3. Rueckwirkende Fuellung von bezug ueber eine feste Namensliste (Auftrag),
   gesucht in description+root_cause+resolution+prevention. gilt_bis_version
   wird von dieser Migration NIE gesetzt -- nur beim Erfassen einer neuen
   Lehre setzbar (Auftrag).

AUSDRUECKLICH NICHT TEIL DIESER MIGRATION: kein gilt_ab_version (keine
Begruendung gefunden, wofuer eine Lehre erst AB einer Version gelten sollte)
und keine Versions-Rueckfuellung aus dem Text -- gemessen: nur 12 von 252
Treffern mit Produktnennung tragen ueberhaupt eine Version im Text, und die
sind ueberwiegend falsch (ein gefundener Wert "127.0.0" stammt aus einer
IP-Adresse). Raten aus dem Text ist keine Migration, sondern eine neue
Fehlerquelle.

Usage:
    python3 migrationen/migrate_lehre_geltung.py [--apply]
    python3 migrationen/migrate_lehre_geltung.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import json
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

SPALTEN = ("gilt_ab", "gilt_bis", "bezug", "gilt_bis_version")

TRIGGER_NAMEN = (
    "lessons_learned_gilt_bis_vor_gilt_ab_bi",
    "lessons_learned_gilt_bis_vor_gilt_ab_bu",
)

TRIGGER_SQL = """
CREATE TRIGGER IF NOT EXISTS lessons_learned_gilt_bis_vor_gilt_ab_bi
BEFORE INSERT ON lessons_learned
FOR EACH ROW WHEN NEW.gilt_ab IS NOT NULL AND NEW.gilt_bis IS NOT NULL
    AND julianday(NEW.gilt_bis) < julianday(NEW.gilt_ab)
BEGIN
    SELECT RAISE(ABORT, 'lessons_learned.gilt_bis liegt vor gilt_ab');
END;

CREATE TRIGGER IF NOT EXISTS lessons_learned_gilt_bis_vor_gilt_ab_bu
BEFORE UPDATE ON lessons_learned
FOR EACH ROW WHEN NEW.gilt_ab IS NOT NULL AND NEW.gilt_bis IS NOT NULL
    AND julianday(NEW.gilt_bis) < julianday(NEW.gilt_ab)
BEGIN
    SELECT RAISE(ABORT, 'lessons_learned.gilt_bis liegt vor gilt_ab');
END;
"""

# Feste Namensliste aus dem Auftrag -- Produktverteilung war damit bereits
# gemessen (flutter 64, python 56, carplay 43, ios 33, dart 26, android 25,
# swift 19, macos 18). \b-Grenzen trennen "Swift" von "SwiftUI" von selbst
# (kein Wortende nach "Swift" in "SwiftUI").
NAMENSLISTE = (
    "iOS", "iPadOS", "macOS", "Xcode", "SwiftUI", "Swift", "CarPlay",
    "Flutter", "Dart", "Android", "Gradle", "SQLite", "Ollama", "Python",
    "Claude Code", "FastAPI", "Riverpod",
)
_MUSTER = {name: re.compile(r"\b" + re.escape(name) + r"\b") for name in NAMENSLISTE}


def _bezug_aus_text(*teile: str | None) -> list[str]:
    text = " ".join(t for t in teile if t)
    treffer = [name for name in NAMENSLISTE if _MUSTER[name].search(text)]
    return treffer


def _has_column(conn: sqlite3.Connection, table: str, spalte: str) -> bool:
    return spalte in {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def missing_columns(conn: sqlite3.Connection) -> list[str]:
    return [s for s in SPALTEN if not _has_column(conn, "lessons_learned", s)]


def missing_triggers(conn: sqlite3.Connection) -> list[str]:
    existing = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    return [t for t in TRIGGER_NAMEN if t not in existing]


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
        spalten_fehlen = missing_columns(conn)
        trigger_fehlen = [] if spalten_fehlen else missing_triggers(conn)
        vorher_zeilen = conn.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
        # Unbefuellte Zeilen VOR jeder Aenderung -- unabhaengig davon, ob die
        # Spalte gerade erst entsteht (dann sind es alle NULL) oder schon
        # frueher angelegt wurde (Falle "zwei Ausgangszustaende", CLAUDE.md):
        # eine frisch aus schema.sql erzeugte Datenbank traegt die Spalte
        # ohne Vorgabewert (NULL) von Anfang an, OHNE dass diese Migration je
        # lief -- das Backfuellen haengt deshalb ausschliesslich an "bezug
        # ist NULL", niemals an "Spalte fehlt". '[]' ist ein eigener,
        # unterscheidbarer Zustand ("geprueft, nichts gefunden") und zaehlt
        # NICHT als unbefuellt.
        unbefuellt_vorher = vorher_zeilen if "bezug" in spalten_fehlen else conn.execute(
            "SELECT COUNT(*) FROM lessons_learned WHERE bezug IS NULL"
        ).fetchone()[0]
    finally:
        conn.close()

    etwas_fehlt = bool(spalten_fehlen or trigger_fehlen)
    etwas_zu_tun = etwas_fehlt or unbefuellt_vorher > 0
    result = {
        "vorher_zeilen": vorher_zeilen,
        "spalten_fehlen": spalten_fehlen,
        "trigger_fehlen": trigger_fehlen,
        "backup": None,
        "etwas_fehlt": etwas_fehlt,
        "bezug_gefuellt": 0,
        "bezug_je_produkt": {},
        "gilt_bis_version_nicht_leer": None,
    }
    if not etwas_zu_tun or not apply:
        return result

    backup_path = _backup(db_path)
    result["backup"] = str(backup_path)

    conn = sqlite3.connect(str(db_path))
    try:
        for spalte in spalten_fehlen:
            conn.execute(f"ALTER TABLE lessons_learned ADD COLUMN {spalte} TEXT")
        conn.executescript(TRIGGER_SQL)

        # Rueckwirkende bezug-Fuellung -- nur bei Zeilen, deren bezug noch
        # NULL ist (idempotent: zweiter Lauf ueberschreibt keine Zeile, die
        # schon '[]' oder einen Treffer traegt, weder von dieser Migration
        # noch vom Erfassen einer neuen Lehre).
        zaehler: dict[str, int] = {name: 0 for name in NAMENSLISTE}
        gefuellt = 0
        for lid, beschreibung, ursache, loesung, vorbeugung in conn.execute(
            "SELECT id, description, root_cause, resolution, prevention "
            "FROM lessons_learned WHERE bezug IS NULL"
        ):
            treffer = _bezug_aus_text(beschreibung, ursache, loesung, vorbeugung)
            # Immer schreiben, auch '[]' bei keinem Treffer -- sonst bleibt
            # die Zeile NULL ("ungeprueft") und wird bei jedem weiteren Lauf
            # erneut durchsucht, was die Migration nicht idempotent machen
            # wuerde.
            conn.execute(
                "UPDATE lessons_learned SET bezug = ? WHERE id = ?",
                (json.dumps(treffer, ensure_ascii=False), lid),
            )
            if not treffer:
                continue
            gefuellt += 1
            for name in treffer:
                zaehler[name] += 1

        conn.commit()
        result["bezug_gefuellt"] = gefuellt
        result["bezug_je_produkt"] = {k: v for k, v in zaehler.items() if v}
        result["nachher_zeilen"] = conn.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
        result["gilt_bis_version_nicht_leer"] = conn.execute(
            "SELECT COUNT(*) FROM lessons_learned WHERE gilt_bis_version IS NOT NULL"
        ).fetchone()[0]
    finally:
        conn.close()
    return result


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
    print(f"=== migrate_lehre_geltung ({mode}) ===")
    print(f"lessons_learned: vorher {res['vorher_zeilen']} Zeilen, fehlende Spalten: "
          f"{res['spalten_fehlen'] or '(keine)'}, fehlende Trigger: "
          f"{res['trigger_fehlen'] or '(keine)'}")
    if res["backup"]:
        print(f"Sicherung: {res['backup']}")
        print(f"bezug gefuellt: {res['bezug_gefuellt']} Zeilen, je Produkt: {res['bezug_je_produkt']}")
        print(f"gilt_bis_version nicht leer nach Migration: {res['gilt_bis_version_nicht_leer']}")
    return 0


def _selftest() -> int:
    import re as _re
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "brainlehr.db"

        # Rot-vor-gruen gegen einen FESTEN Commit (nie HEAD, L-82415c): der
        # Stand vor dieser Aufgabe. `git show` statt Ruecknahme -- kein
        # Zustand des Arbeitsbaums wird beruehrt.
        import subprocess
        FESTER_COMMIT = "dee26e17"
        alt_schema = subprocess.run(
            ["git", "show", f"{FESTER_COMMIT}:schema.sql"],
            cwd=WURZEL, capture_output=True, text=True, check=True,
        ).stdout

        # Minimaler alter Tabellenstand fuer den Rot-Lauf (die vollen
        # CREATE-Bloecke aus altem Schema brauchen Tabellen, die dieser Test
        # nicht anlegt -- hier reicht die reale Spaltenmenge von
        # lessons_learned zum Fixpunkt, ausgeschnitten wie in
        # migrate_gedaechtnisart.py::_selftest).
        block_start = alt_schema.index("CREATE TABLE IF NOT EXISTS lessons_learned")
        block_end = alt_schema.index(");", block_start) + 2
        alter_block = alt_schema[block_start:block_end]
        for neu in SPALTEN:
            assert neu not in alter_block, f"{neu} bereits im Fixpunkt-Schema -- Test waere nicht rot gewesen"

        conn = sqlite3.connect(str(db_path))
        conn.executescript(alter_block)
        conn.execute(
            "INSERT INTO lessons_learned (id, type, description, anlass, bemerkt_woran) "
            "VALUES ('L-ios1', 'insight', 'Auf iOS bricht die Simulator-Kopplung nach SIGSTOP.', 'skript', 'test')"
        )
        conn.execute(
            "INSERT INTO lessons_learned (id, type, description, anlass, bemerkt_woran) "
            "VALUES ('L-kein', 'insight', 'Ein Commit umfasst eine Sache, sonst ist das Verzeichnis wertlos.', 'skript', 'test')"
        )
        conn.execute(
            "INSERT INTO lessons_learned (id, type, description, anlass, bemerkt_woran) "
            "VALUES ('L-swift', 'insight', 'SwiftUI-Buttons unter 24px verletzen 2.5.8, reines Swift-Enum reicht als Fix nicht.', 'skript', 'test')"
        )
        conn.commit()
        conn.close()

        conn = sqlite3.connect(str(db_path))
        assert missing_columns(conn) == list(SPALTEN)
        conn.close()

        # (a) erster Lauf: Spalten + Trigger, bezug rueckwirkend gefuellt.
        res1 = migrate(db_path, apply=True)
        assert res1["backup"] and Path(res1["backup"]).exists()
        assert res1["vorher_zeilen"] == 3

        conn = sqlite3.connect(str(db_path))
        bezug = dict(conn.execute("SELECT id, bezug FROM lessons_learned").fetchall())
        # Positivkontrolle: Produktnennung -> bezug gefuellt.
        assert json.loads(bezug["L-ios1"]) == ["iOS"], bezug["L-ios1"]
        # SwiftUI und Swift unterscheiden sich (Wortgrenze trennt sie).
        assert set(json.loads(bezug["L-swift"])) == {"SwiftUI", "Swift"}, bezug["L-swift"]
        # Gegenprobe: KEINE Produktnennung -> bezug bleibt leer, kein Raten.
        assert json.loads(bezug["L-kein"]) == [], bezug["L-kein"]

        assert res1["bezug_gefuellt"] == 2
        assert res1["bezug_je_produkt"]["iOS"] == 1
        assert res1["bezug_je_produkt"]["SwiftUI"] == 1
        assert res1["bezug_je_produkt"]["Swift"] == 1

        # Negativfall, wichtigster Punkt: gilt_bis_version bleibt bei ALLEN
        # Zeilen leer.
        leer = conn.execute(
            "SELECT COUNT(*) FROM lessons_learned WHERE gilt_bis_version IS NOT NULL"
        ).fetchone()[0]
        assert leer == 0, f"gilt_bis_version haette bei der Migration leer bleiben muessen, {leer} Zeile(n) gesetzt"
        assert res1["gilt_bis_version_nicht_leer"] == 0

        # Trigger-Gegenprobe beide Richtungen: gilt_bis vor gilt_ab abgelehnt,
        # gilt_bis nach gilt_ab (bzw. beide leer) angenommen.
        try:
            conn.execute(
                "UPDATE lessons_learned SET gilt_ab = '2026-08-19', gilt_bis = '2026-08-01' WHERE id = 'L-ios1'"
            )
            abgelehnt = False
        except sqlite3.IntegrityError:
            abgelehnt = True
        assert abgelehnt, "gilt_bis vor gilt_ab haette abgelehnt werden muessen"

        conn.execute(
            "UPDATE lessons_learned SET gilt_ab = '2026-08-01', gilt_bis = '2026-08-19' WHERE id = 'L-ios1'"
        )
        conn.commit()
        conn.close()

        # (b) zweiter Lauf: nichts zu tun, keine neue Sicherung, keine
        # Verdopplung von bezug (idempotent).
        res2 = migrate(db_path, apply=True)
        assert res2["backup"] is None
        assert res2["etwas_fehlt"] is False
        conn = sqlite3.connect(str(db_path))
        bezug2 = dict(conn.execute("SELECT id, bezug FROM lessons_learned").fetchall())
        assert bezug2 == bezug, "zweiter Lauf hat bezug veraendert -- Migration nicht idempotent"
        conn.close()

    # (c) Falle "zwei Ausgangszustaende" (CLAUDE.md): eine Datenbank, deren
    # Spalten schon existieren (z.B. frisch aus schema.sql erzeugt), aber
    # deren bezug NIE durch diese Migration lief -- Backfuellen darf NICHT
    # an "Spalte fehlt" haengen, sonst bleibt so eine Zeile fuer immer leer.
    with tempfile.TemporaryDirectory() as tmp2:
        db_path2 = Path(tmp2) / "brainlehr.db"
        conn = sqlite3.connect(str(db_path2))
        conn.executescript(alter_block.replace(");", ", gilt_ab TEXT, gilt_bis TEXT, "
                                                "bezug TEXT, gilt_bis_version TEXT);"))
        conn.executescript(TRIGGER_SQL)
        conn.execute(
            "INSERT INTO lessons_learned (id, type, description, anlass, bemerkt_woran) "
            "VALUES ('L-frisch', 'insight', 'Ein Gradle-Build schlug fehl.', 'skript', 'test')"
        )
        conn.commit()
        conn.close()

        conn = sqlite3.connect(str(db_path2))
        assert missing_columns(conn) == [], "Testaufbau falsch: Spalten sollten schon da sein"
        conn.close()

        res3 = migrate(db_path2, apply=True)
        # Spalten UND Trigger waren schon vollstaendig da (Testaufbau) --
        # NUR bezug war nie befuellt, wie bei einer frisch aus schema.sql
        # erzeugten Datenbank.
        assert res3["spalten_fehlen"] == []
        assert res3["trigger_fehlen"] == []
        assert res3["etwas_fehlt"] is False
        assert res3["backup"] is not None, (
            "Migration hat bei vorhandenen, aber unbefuellten Spalten nichts getan -- "
            "genau die Falle 'zwei Ausgangszustaende'"
        )
        assert res3["bezug_gefuellt"] == 1

        conn = sqlite3.connect(str(db_path2))
        bezug3 = conn.execute("SELECT bezug FROM lessons_learned WHERE id = 'L-frisch'").fetchone()[0]
        assert json.loads(bezug3) == ["Gradle"], bezug3
        conn.close()

    print("SELFTEST OK: gilt_ab/gilt_bis/bezug/gilt_bis_version additiv, bezug "
          "rueckwirkend nur aus Text gefuellt (Positiv- und Gegenprobe), "
          "gilt_bis_version bleibt bei der Migration durchgehend leer, "
          "Trigger gilt_bis<gilt_ab beide Richtungen geprueft, idempotent, "
          "Backfuellung haengt an bezug IS NULL statt an fehlender Spalte "
          "(Falle 'zwei Ausgangszustaende' geprueft).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
