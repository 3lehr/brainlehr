#!/usr/bin/env python3
"""migrate_norm_herkunft.py -- Normachse 3 (Unabaenderlichkeit), Auftrag
2026-08-14 (docs/PLAN_NORMACHSEN_2026-08-14.md, Schritt 1).

Betreiberentscheidung 2026-08-14, woertlich "Wert an der Herkunft": kein
Schemawechsel, kein eigenes Ja/Nein-Feld fuer Achse 3. Stattdessen bekommt
knowledge_nodes.norm_entschieden_von bei einer Norm FREMDER Herkunft (Gesetz,
Verordnung, Urteil, Normungsstelle) den Wert kern.normachsen.HERKUNFT_FREMD
('gesetzgeber') nachgetragen -- das Feld haelt ohnehin fest, WER die Norm
verbindlich gemacht hat, und bei einem Gesetz ist das nicht dieses Haus.
Widerrufbarkeit folgt daraus unmittelbar.

Die Kandidaten kommen aus kern.normachsen.fremdnormen() -- WORTGLEICH
dieselbe Erkennung, die auch der Melder benutzt (FREMDE_QUELLE, an der
Quelle, nicht am Inhalt). Keine zweite Fassung des Musters und keine
eingetippte Pfadliste: eine Liste veraltet mit dem naechsten Gesetzeszitat,
die Funktion nicht.

Idempotent: die UPDATE-Klausel trifft nur Zeilen, deren norm_entschieden_von
den Wert noch nicht traegt (WHERE norm_entschieden_von IS NULL OR <>
HERKUNFT_FREMD) -- ein zweiter Lauf findet nichts mehr zu tun.

Usage:
    .venv/bin/python migrationen/migrate_norm_herkunft.py [--apply]
    .venv/bin/python migrationen/migrate_norm_herkunft.py --selftest
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

import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import zeitmarke
from normachsen import HERKUNFT_FREMD, fremdnormen

HERE = Path(__file__).parent
# BEGOD_KNOWLEDGE_DB/BRAINLEHR_DB ueberschreiben den Pfad -- gleiches Muster
# wie migrate_source_constraints.py, sonst laesst sich dieses Skript nie gegen
# eine Testkopie fahren, ohne die Produktiv-DB anzufassen.
DB_PATH = Path(os.environ.get("BRAINLEHR_DB") or os.environ.get("BEGOD_KNOWLEDGE_DB")
               or (HERE.parent / "brainlehr.db"))

# Grund, wie ihn auch die anderen Migrationen mitschreiben (schema.sql
# verlangt norm_entschieden_grund nicht-leer, sobald norm_entscheidung
# <> 'offen' -- betrifft hier keine der drei echten Zeilen, weil ihr Grund
# schon gesetzt ist, aber ein GRUND-UPDATE waere sonst unbelegt).
GRUND_ZUSATZ = (" Herkunftswert nachgetragen (Migration 2026-08-14, "
                "Betreiberentscheidung 'Wert an der Herkunft'): diese Norm "
                "stammt von aussen und ist darum nicht widerrufbar.")


def _backup(db_path: Path) -> Path:
    """Gleiches Muster wie migrate_source_constraints.py -- Checkpoint vor
    dem Kopieren, sonst fehlen committete, aber noch nicht zurueckgeschriebene
    WAL-Aenderungen in der Sicherung (Lehre L-218f1e)."""
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
    dest = db_path.parent / f"{db_path.name}.bak-{stamp}-normherkunft"
    shutil.copy2(db_path, dest)
    return dest


def kandidaten(conn: sqlite3.Connection) -> list[dict]:
    """Fremdnormen, die den Herkunftswert noch NICHT tragen -- genau die
    Menge, die diese Migration anfasst."""
    conn.row_factory = sqlite3.Row
    return [f for f in fremdnormen(conn) if f["entschieden_von"] != HERKUNFT_FREMD]


def migrate(db_path: Path, apply: bool) -> dict:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        before_nodes = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        offen = kandidaten(conn)
    finally:
        conn.close()

    result = {
        "vorher_zeilen": before_nodes,
        "kandidaten": [f["path"] for f in offen],
        "backup": None,
        "nachgetragen": None,
    }
    if not offen or not apply:
        return result

    backup_path = _backup(db_path)
    result["backup"] = str(backup_path)

    conn = sqlite3.connect(str(db_path))
    try:
        pfade = [f["path"] for f in offen]
        platz = ",".join("?" * len(pfade))
        cur = conn.execute(
            f"UPDATE knowledge_nodes SET norm_entschieden_von = ?, "
            f"norm_entschieden_grund = norm_entschieden_grund || ? "
            f"WHERE path IN ({platz}) "
            f"AND (norm_entschieden_von IS NULL OR norm_entschieden_von <> ?)",
            (HERKUNFT_FREMD, GRUND_ZUSATZ, *pfade, HERKUNFT_FREMD),
        )
        result["nachgetragen"] = cur.rowcount
        conn.commit()
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
    print(f"=== migrate_norm_herkunft ({mode}) ===")
    print(f"vorher: {res['vorher_zeilen']} Knoten")
    print(f"Kandidaten (Fremdnorm ohne Herkunftswert): {res['kandidaten'] or '(keine -- bereits migriert)'}")
    if res["backup"]:
        print(f"Sicherung: {res['backup']}")
    if res["nachgetragen"] is not None:
        print(f"norm_entschieden_von='{HERKUNFT_FREMD}' nachgetragen bei: {res['nachgetragen']} Knoten")
    return 0


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "brainlehr.db"
        schema_sql = (HERE.parent / "schema.sql").read_text(encoding="utf-8")

        conn = sqlite3.connect(str(db_path))
        conn.executescript(schema_sql)

        def _knoten(path, rang, source, grund="Testvorrichtung.",
                    entschieden_von="test", entscheidung="norm_unbefristet",
                    norm_art=None):
            nid = path.strip("/").replace("/", "-") or "wurzel"
            conn.execute(
                "INSERT INTO knowledge_nodes (id, path, parent_path, title, summary, "
                "content, source, norm_rang, norm_art, gilt_ab, norm_entscheidung, "
                "norm_entschieden_grund, norm_entschieden_von, norm_entschieden_am, "
                "created_at, updated_at) "
                "VALUES (?,?,'/',?,?,?,?,?,?,'2026-08-14',?,?,?,'2026-08-14',"
                "'2026-08-14T00:00:00+02:00','2026-08-14T00:00:00+02:00')",
                (nid, path, "Titel", "Zusammenfassung.", "Inhalt.", source, rang,
                 norm_art, entscheidung, grund, entschieden_von),
            )

        # Positivfall: echte Fremdnorm, noch ohne Herkunftswert.
        _knoten("/shared/geg-test", 1, "erzeugt aus BGBl I 2026 Nr. 226",
                entschieden_von="claude-code", norm_art="sollen")
        # Negativfall: Hausregel ohne Gesetzesbezug -- darf NICHT angefasst werden.
        _knoten("/ops/hausregel-test", 3, "erzeugt aus einer eigenen Mitschrift",
                entschieden_von="claude-code/opus-5")
        # Bereits erledigt: zweiter Fremdnorm-Knoten, der den Wert schon traegt --
        # Idempotenz-Probe darf ihn kein zweites Mal anfassen (rowcount).
        _knoten("/shared/schon-erledigt", 1, "Urteil BGH V ZR 206/24",
                entschieden_von=HERKUNFT_FREMD, norm_art="sein")
        conn.commit()
        conn.close()

        # --- rot: vor der Migration traegt der Positivfall den Wert nicht ---
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        vor = conn.execute(
            "SELECT norm_entschieden_von FROM knowledge_nodes WHERE path='/shared/geg-test'"
        ).fetchone()[0]
        assert vor != HERKUNFT_FREMD, "Testaufbau kaputt: Positivfall traegt den Wert schon"
        conn.close()

        res1 = migrate(db_path, apply=True)
        assert res1["backup"] and Path(res1["backup"]).exists()
        assert res1["kandidaten"] == ["/shared/geg-test"], res1["kandidaten"]
        assert res1["nachgetragen"] == 1, res1

        # --- gruen: danach traegt genau der Positivfall den Wert ---
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        nach = {r["path"]: r["norm_entschieden_von"] for r in conn.execute(
            "SELECT path, norm_entschieden_von FROM knowledge_nodes")}
        assert nach["/shared/geg-test"] == HERKUNFT_FREMD
        assert nach["/ops/hausregel-test"] == "claude-code/opus-5", (
            "Negativfall: eine Hausregel ohne Gesetzesbezug darf den Wert NICHT bekommen")
        assert nach["/shared/schon-erledigt"] == HERKUNFT_FREMD
        conn.close()

        # Zweiter Lauf: nichts zu tun, keine neue Sicherung, kein rowcount.
        res2 = migrate(db_path, apply=True)
        assert res2["kandidaten"] == [], res2["kandidaten"]
        assert res2["backup"] is None

    print("SELFTEST OK: Fremdnorm bekommt Herkunftswert, Hausregel bleibt "
          "unangetastet, zweiter Lauf idempotent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
