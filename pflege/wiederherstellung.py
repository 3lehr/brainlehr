#!/usr/bin/env python3
"""Wiederherstellung -- prueft .bak-*-Sicherungen von brainlehr.db auf
Brauchbarkeit und spielt eine geprueft brauchbare Sicherung an einen
NICHT-Live-Zielpfad zurueck (Auftrag 2026-08-06, Anlass: alle vier
_backup()-Fassungen kopierten bis 2026-08-05 nur die Hauptdatei ohne
WAL-Checkpoint -- brainlehr.db.bak-20260805T221931 fehlt norm_rang,
siehe Lehre L-218f1e. Bisher wurde KEINE Sicherung je zurueckgespielt.

Sicherheitsprinzip: JEDE Pruefung laeuft auf einer WEGWERF-KOPIE der
Sicherung in einem Temp-Verzeichnis, nie auf der Sicherungsdatei selbst
(FTS5-'integrity-check' ist intern ein INSERT-Statement und scheitert
auf einer mode=ro-Verbindung mit 'attempt to write a readonly database'
-- gemessen beim Bau dieses Skripts) und niemals auf brainlehr.db. Die
Sicherung wird nur per shutil.copy2 GELESEN, nie geoeffnet.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

# Liegt eine Ebene unter der Wurzel: die Wurzel muss auf den Suchpfad,
# sonst findet `import knowledge_mcp_server` nichts. Muster aus haken/.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))

import argparse
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parent.parent  # Wurzel, eine Ebene ueber diesem Ordner (Umzug 2026-08-10)
DB_PATH = SHARED_KNOWLEDGE / "brainlehr.db"
SCHEMA_SQL = SHARED_KNOWLEDGE / "schema.sql"

# Tabellen, deren Bestandsgroesse den "Nutzen auf einen Blick" ausmacht.
COUNT_TABLES = [
    "knowledge_nodes",
    "lessons_learned",
    "knowledge_relations",
    "knowledge_embeddings",
    "access_log",
]


class PruefFehler(Exception):
    """Sicherung liess sich nicht einmal kopieren/oeffnen -- 'beschaedigt'."""


def _reference_columns() -> dict[str, list[str]]:
    """Tabellen+Spalten aus dem heutigen schema.sql, ueber eine :memory:-DB
    gelesen (nicht per Regex geparst -- CHECK(...)-Klammern im echten
    schema.sql machen Klammerzaehlen unzuverlaessig)."""
    ref = sqlite3.connect(":memory:")
    try:
        ref.executescript(SCHEMA_SQL.read_text())
        tables = [
            r[0] for r in ref.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '%fts%'"
            ).fetchall()
        ]
        return {
            t: [r[1] for r in ref.execute(f"PRAGMA table_info({t})").fetchall()]
            for t in tables
        }
    finally:
        ref.close()


def _scratch_copy(sicherung: Path):
    """Kopiert `sicherung` in ein Temp-Verzeichnis, gibt (conn, cleanup) zurueck.
    conn ist eine normale (schreibfaehige) Verbindung auf die WEGWERF-Kopie --
    die Original-Sicherung bleibt beim reinen shutil.copy2 unangetastet."""
    tmpdir = Path(tempfile.mkdtemp(prefix="wiederherstellung-pruef-"))
    tmp_db = tmpdir / "pruef.db"
    try:
        shutil.copy2(sicherung, tmp_db)
    except OSError as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise PruefFehler(f"Sicherung nicht lesbar: {e}") from e
    try:
        conn = sqlite3.connect(str(tmp_db))
        conn.execute("SELECT 1")  # erzwingt sofortigen Oeffnen-Fehler, nicht erst spaeter
    except sqlite3.DatabaseError as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise PruefFehler(f"keine gueltige SQLite-Datenbank: {e}") from e

    def cleanup():
        conn.close()
        shutil.rmtree(tmpdir, ignore_errors=True)

    return conn, cleanup


def _integrity_check(conn: sqlite3.Connection) -> tuple[bool, list[str]]:
    rows = conn.execute("PRAGMA integrity_check").fetchall()
    ok = len(rows) == 1 and rows[0][0] == "ok"
    return ok, [r[0] for r in rows]


def _fts_integrity_check(conn: sqlite3.Connection) -> tuple[bool, str | None]:
    has_fts = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='knowledge_fts'"
    ).fetchone()
    if not has_fts:
        return True, "knowledge_fts nicht vorhanden -- uebersprungen"
    try:
        conn.execute("INSERT INTO knowledge_fts(knowledge_fts) VALUES('integrity-check')")
        return True, None
    except sqlite3.DatabaseError as e:
        return False, str(e)


def _schema_diff(conn: sqlite3.Connection) -> dict:
    ref = _reference_columns()
    present = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    fehlende_tabellen = []
    fehlende_spalten: dict[str, list[str]] = {}
    for table, cols in ref.items():
        if table not in present:
            fehlende_tabellen.append(table)
            continue
        have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        missing = [c for c in cols if c not in have]
        if missing:
            fehlende_spalten[table] = missing
    return {"fehlende_tabellen": fehlende_tabellen, "fehlende_spalten": fehlende_spalten}


def _counts(conn: sqlite3.Connection) -> dict[str, int | None]:
    present = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    out: dict[str, int | None] = {}
    for t in COUNT_TABLES:
        if t not in present:
            out[t] = None  # Tabelle fehlt -- kein Zaehlfehler, siehe Schema-Diff
            continue
        out[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    return out


def _zeitraum(conn: sqlite3.Connection) -> dict[str, str | None]:
    """Abgedeckter Zeitraum ueber access_log.timestamp (waechst am
    kontinuierlichsten von allen Tabellen)."""
    present = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "access_log" not in present:
        return {"von": None, "bis": None}
    row = conn.execute("SELECT MIN(timestamp), MAX(timestamp) FROM access_log").fetchone()
    return {"von": row[0], "bis": row[1]}


def _auditkette(conn: sqlite3.Connection) -> dict | None:
    """Wiederverwendet knowledge_lint.find_broken_chain(), soweit die
    Auditketten-Spalten in dieser Sicherung existieren (Nachtrag
    2026-08-06 -- aeltere Sicherungen haben sie nicht, kein Befund)."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(access_log)").fetchall()}
    if not {"zeilen_hash", "ketten_hash"} <= cols:
        return None
    sys.path.insert(0, str(SHARED_KNOWLEDGE))
    from knowledge_lint import find_broken_chain  # noqa: E402  (import hier: nur bei Bedarf)
    conn.row_factory = sqlite3.Row
    try:
        return find_broken_chain(conn)
    finally:
        conn.row_factory = None


def pruefe(sicherung: Path) -> dict:
    """Urteil ueber EINE Sicherung. Wirft nie -- 'beschaedigt' ist ein
    Ergebnis, kein Ausnahmefall."""
    try:
        conn, cleanup = _scratch_copy(sicherung)
    except PruefFehler as e:
        return {"datei": str(sicherung), "urteil": "beschaedigt", "begruendung": str(e)}

    try:
        ok_integrity, integrity_rows = _integrity_check(conn)
        if not ok_integrity:
            return {
                "datei": str(sicherung),
                "urteil": "beschaedigt",
                "begruendung": f"PRAGMA integrity_check: {'; '.join(integrity_rows)}",
            }

        ok_fts, fts_fehler = _fts_integrity_check(conn)
        if not ok_fts:
            return {
                "datei": str(sicherung),
                "urteil": "beschaedigt",
                "begruendung": f"FTS integrity-check: {fts_fehler}",
            }

        diff = _schema_diff(conn)
        if diff["fehlende_tabellen"] or diff["fehlende_spalten"]:
            teile = []
            if diff["fehlende_tabellen"]:
                teile.append("Tabellen fehlen: " + ", ".join(diff["fehlende_tabellen"]))
            for table, cols in diff["fehlende_spalten"].items():
                teile.append(f"{table}: Spalten fehlen: " + ", ".join(cols))
            counts = _counts(conn)
            zeitraum = _zeitraum(conn)
            return {
                "datei": str(sicherung),
                "urteil": "veraltetes Schema",
                "begruendung": "; ".join(teile),
                "bestand": counts,
                "zeitraum": zeitraum,
                "auditkette": _auditkette(conn),
            }

        counts = _counts(conn)
        zeitraum = _zeitraum(conn)
        auditkette = _auditkette(conn)
        begruendung = "Schema vollstaendig, Integritaet ok, Bestand: " + ", ".join(
            f"{k}={v}" for k, v in counts.items()
        )
        return {
            "datei": str(sicherung),
            "urteil": "brauchbar",
            "begruendung": begruendung,
            "bestand": counts,
            "zeitraum": zeitraum,
            "auditkette": auditkette,
        }
    finally:
        cleanup()


def _alle_sicherungen() -> list[Path]:
    """Alle .bak-*-Hauptdateien im Verzeichnis, ohne -shm/-wal-Sidecars und
    ohne das schreibpruefstand/-Verzeichnis (laeuft laut Auftrag gerade)."""
    out = []
    for p in sorted(SHARED_KNOWLEDGE.glob("brainlehr.db.bak-*")):
        if p.name.endswith("-shm") or p.name.endswith("-wal"):
            continue
        out.append(p)
    return out


def _resolve_und_pruefe_ziel(ziel: Path) -> None:
    """Bricht ab, wenn `ziel` die Live-Datenbank ist -- Pruefung, kein
    Kommentar. Vergleich ueber realpath, damit '../brainlehr.db' o.ae.
    nicht durchrutscht."""
    if ziel.exists() and ziel.resolve() == DB_PATH.resolve():
        raise SystemExit(
            f"ABGEBROCHEN: --ziel zeigt auf die Live-Datenbank ({DB_PATH}). "
            "stelle_her schreibt niemals ueber die Live-DB."
        )
    if ziel.resolve() == DB_PATH.resolve():
        raise SystemExit(
            f"ABGEBROCHEN: --ziel zeigt auf die Live-Datenbank ({DB_PATH}). "
            "stelle_her schreibt niemals ueber die Live-DB."
        )


def stelle_her(sicherung: Path, ziel: Path) -> dict:
    _resolve_und_pruefe_ziel(ziel)

    bericht = pruefe(sicherung)
    if bericht["urteil"] == "beschaedigt":
        raise SystemExit(
            f"ABGEBROCHEN: Sicherung ist beschaedigt ({bericht['begruendung']}). "
            "Kein Restore versucht."
        )

    ziel.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sicherung, ziel)

    # Verifikation am Ziel: eigene, frische Pruefung -- muss zum Vorher-Bericht passen.
    nachher = pruefe(ziel)
    abweichungen = []
    if "bestand" in bericht and "bestand" in nachher:
        for k in COUNT_TABLES:
            if bericht["bestand"].get(k) != nachher["bestand"].get(k):
                abweichungen.append(
                    f"{k}: vorher={bericht['bestand'].get(k)} nachher={nachher['bestand'].get(k)}"
                )
    if nachher["urteil"] != bericht["urteil"]:
        abweichungen.append(
            f"Urteil weicht ab: vorher={bericht['urteil']} nachher={nachher['urteil']} "
            f"({nachher.get('begruendung')})"
        )

    return {
        "sicherung": str(sicherung),
        "ziel": str(ziel),
        "vorher": bericht,
        "nachher": nachher,
        "abweichungen": abweichungen,
        "stimmt_ueberein": not abweichungen,
    }


# ─── Ausgabe ────────────────────────────────────────────────────────────

def _print_pruefbericht(b: dict) -> None:
    print(f"{b['datei']}: {b['urteil']} -- {b['begruendung']}")
    if "bestand" in b:
        print(f"  Bestand: {b['bestand']}")
    if b.get("zeitraum"):
        print(f"  Zeitraum: {b['zeitraum']['von']} .. {b['zeitraum']['bis']}")
    if b.get("auditkette") is not None:
        ak = b["auditkette"]
        print(
            f"  Auditkette: {'heil' if ak['heil'] else 'GEBROCHEN bei id ' + str(ak['erster_bruch'])} "
            f"({ak['geprueft_zeilen']} geprueft, {ak['ungedeckter_zeitraum_zeilen']} ungedeckt)"
        )


# ─── Selbsttest ─────────────────────────────────────────────────────────

def _selftest() -> None:
    import os

    tmpdir = Path(tempfile.mkdtemp(prefix="wiederherstellung-selftest-"))
    try:
        # 1) Heile Sicherung -> brauchbar.
        heil = tmpdir / "heil.db"
        c = sqlite3.connect(str(heil))
        c.executescript(SCHEMA_SQL.read_text())
        c.execute(
            "INSERT INTO knowledge_nodes(id, path, project_id, title, summary, source, "
            "norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
            "VALUES ('n1','/x','shared','T','S','selftest','keine_norm','skript:test','Testvorrichtung')"
        )
        c.commit()
        c.close()
        r = pruefe(heil)
        assert r["urteil"] == "brauchbar", r
        assert r["bestand"]["knowledge_nodes"] == 1, r

        # 2) Fehlende Spalte -> veraltetes Schema, Spalte benannt.
        alt = tmpdir / "alt.db"
        c = sqlite3.connect(str(alt))
        c.executescript(SCHEMA_SQL.read_text())
        # Trigger, die NEW.norm_rang lesen, verhindern DROP COLUMN (Nachtrag
        # 2026-08-08) -- fuer dieses Selbsttest-Szenario (absichtlich
        # veraltetes Schema) irrelevant, DROP TRIGGER vorher.
        c.executescript("""
            DROP TRIGGER IF EXISTS knowledge_nodes_norm_rang_gilt_ab_bi;
            DROP TRIGGER IF EXISTS knowledge_nodes_norm_rang_gilt_ab_bu;
            DROP TRIGGER IF EXISTS knowledge_nodes_norm_entscheidung_rang_bi;
            DROP TRIGGER IF EXISTS knowledge_nodes_norm_entscheidung_rang_bu;
            DROP TRIGGER IF EXISTS knowledge_nodes_norm_entscheidung_rang_neu_bu;
        """)
        c.execute("ALTER TABLE knowledge_nodes DROP COLUMN norm_rang")
        c.commit()
        c.close()
        r = pruefe(alt)
        assert r["urteil"] == "veraltetes Schema", r
        assert "norm_rang" in r["begruendung"], r["begruendung"]

        # 3) Absichtlich beschaedigte Datei -> beschaedigt, kein Absturz.
        kaputt = tmpdir / "kaputt.db"
        c = sqlite3.connect(str(kaputt))
        c.executescript(SCHEMA_SQL.read_text())
        c.close()
        with open(kaputt, "r+b") as f:
            f.seek(100)
            f.write(b"\xff" * 200)
        r = pruefe(kaputt)
        assert r["urteil"] == "beschaedigt", r

        # 4) Gar keine SQLite-Datei -> ebenfalls beschaedigt, kein Absturz.
        keine_db = tmpdir / "keine_db.db"
        keine_db.write_text("das ist keine sqlite-datenbank")
        r = pruefe(keine_db)
        assert r["urteil"] == "beschaedigt", r

        # Gegenprobe stelle_her: --ziel auf die Live-Datenbank bricht ab, nichts angefasst.
        vorher_hash = None
        if DB_PATH.exists():
            import hashlib
            vorher_hash = hashlib.sha256(DB_PATH.read_bytes()).hexdigest()
        try:
            stelle_her(heil, DB_PATH)
            raise AssertionError("stelle_her auf Live-DB haette abbrechen muessen")
        except SystemExit:
            pass
        if vorher_hash is not None:
            import hashlib
            nachher_hash = hashlib.sha256(DB_PATH.read_bytes()).hexdigest()
            assert vorher_hash == nachher_hash, "Live-DB wurde veraendert!"

        # stelle_her auf ein zulaessiges Ziel funktioniert und stimmt ueberein.
        ziel = tmpdir / "restored" / "kopie.db"
        res = stelle_her(heil, ziel)
        assert res["stimmt_ueberein"], res
        assert ziel.exists()

        print("wiederherstellung --selftest: alle Faelle bestanden")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ─── CLI ────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--selftest", action="store_true")
    sub = parser.add_subparsers(dest="cmd")

    p_pruefe = sub.add_parser("pruefe", help="ist eine Sicherung wiederherstellbar?")
    p_pruefe.add_argument("sicherung", nargs="?", type=Path)
    p_pruefe.add_argument("--alle", action="store_true")

    p_stelle = sub.add_parser("stelle_her", help="Sicherung an --ziel zurueckspielen (nie Live-DB)")
    p_stelle.add_argument("sicherung", type=Path)
    p_stelle.add_argument("--ziel", required=True, type=Path)

    args = parser.parse_args(argv)

    if args.selftest:
        _selftest()
        return 0

    if args.cmd == "pruefe":
        if args.alle:
            berichte = [pruefe(p) for p in _alle_sicherungen()]
            if not berichte:
                print("keine .bak-*-Sicherungen gefunden")
                return 0
            for b in berichte:
                _print_pruefbericht(b)
            return 0
        if not args.sicherung:
            parser.error("pruefe braucht entweder <sicherung> oder --alle")
        _print_pruefbericht(pruefe(args.sicherung))
        return 0

    if args.cmd == "stelle_her":
        res = stelle_her(args.sicherung, args.ziel)
        print(f"wiederhergestellt: {res['sicherung']} -> {res['ziel']}")
        print(f"stimmt ueberein: {res['stimmt_ueberein']}")
        if res["abweichungen"]:
            print("ABWEICHUNGEN:")
            for a in res["abweichungen"]:
                print(f"  {a}")
            return 1
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
