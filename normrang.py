#!/usr/bin/env python3
"""normrang.py -- N3 aus docs/PLAN_NORMSCHICHT_2026-08-05.md.

Vergibt norm_rang (und gilt_ab/gilt_bis) auf knowledge_nodes, deterministisch
aus der Herkunft abgeleitet -- kein Ermessen, keine Textanalyse, kein Modell.
Traeger der Ableitung ist das source-Feld, das normbestand.py (N1) beim
Anlegen jedes Regelartefakts geschrieben hat:

    "erzeugt aus <Quelldatei> (Stand <Zeitpunkt>)"

    Rang 1  Quelldatei == globale CLAUDE.md   (~/.claude/CLAUDE.md)
    Rang 2  Quelldatei == hub-CLAUDE.md       (<hub>/CLAUDE.md)
    Rang 3  Quelldatei liegt unter docs/adr/  (ADR-Bestand)

Alles andere -- Sammelknoten (source z.B. "normbestand.py::ensure_category"
oder "erzeugt aus .../methodik_export.py ..."), Wissensknoten, sonstige
Quellen -- bleibt norm_rang IS NULL. Das ist der Plan-Kern (§2): NULL heisst
"Fakt, keine Norm", nicht "noch nicht bearbeitet".

Die Ableitung haengt nur vom source-String und den beiden Datei-Konstanten
unten ab (gleiche Pfade wie normbestand.py verwendet) -- ein zweiter Lauf
ueber denselben Bestand liefert dieselben Raenge. Wo eine Quelldatei nicht
in eines der drei Muster passt, bekommt der Knoten keinen Rang -- kein
Rateversuch, keine Textaehnlichkeit.

gilt_ab kommt vom Knoten selbst (created_at) -- ein belegbarer Erfassungs-
zeitpunkt, kein neu erfundenes Datum. gilt_bis bleibt NULL: unbefristet in
Kraft (Plan §3).

Rang 4 (eskalierte Lehre, `lessons_learned.status='escalated_to_rule'`) hat
auf der heutigen Schema-Auslegung keinen Traeger: die drei neuen Spalten
liegen ausschliesslich auf knowledge_nodes (schema.sql, N2), nicht auf
lessons_learned. Dieses Skript vergibt darum nur Rang 1..3 und laesst Rang 4
unbesetzt -- siehe Bericht im Auftrag (zwei Lesarten, keine Entscheidung
hier).

MCP-Server deckt norm_rang/gilt_ab/gilt_bis nicht ab: knowledge_update()
kennt nur summary/content/tags (knowledge_mcp_server.py, Stand nach N2) --
die drei Spalten sind additiv und juenger als der Server-Vertrag. Deshalb
direktes SQL statt kms.knowledge_update, mit demselben Begruendungsmuster
wie migrate_normfelder.py (N2) es fuer ALTER TABLE schon nutzt.

Usage:
    .venv/bin/python shared-knowledge/normrang.py [--dry-run|--apply]
    .venv/bin/python shared-knowledge/normrang.py --selftest
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
HUB_ROOT = HERE.parent
DB_PATH = HERE / "knowledge.db"
CET = timezone(timedelta(hours=1))

# Gleiche Pfade wie normbestand.py (N1) beim Anlegen der Artefakte verwendet
# hat -- die Ableitung hier ist bewusst nur ein Nachvollzug jener Quelle,
# keine Neudefinition.
GLOBAL_CLAUDE_MD = Path.home() / ".claude" / "CLAUDE.md"
HUB_CLAUDE_MD = HUB_ROOT / "CLAUDE.md"

SOURCE_PREFIX = "erzeugt aus "
STAND_MARKER = " (Stand "


def _backup(db_path: Path) -> Path:
    """Gleiches Namensschema wie build_embeddings.py::_backup() (und
    migrate_normfelder.py::_backup(), das dieselbe Begruendung traegt) --
    ein Blick ins Verzeichnis findet alle Sicherungsarten gleich wieder.

    Zusatz gegenueber jenen beiden Vorbildern: WAL-Checkpoint vor dem
    Kopieren. Die Live-DB laeuft im WAL-Modus (knowledge.db-wal daneben) --
    ein reiner shutil.copy2 der Hauptdatei kann juengst committete, aber
    noch nicht zurueckgeschriebene Aenderungen verlieren (live beobachtet:
    eine so gezogene Kopie hatte die norm_rang/gilt_ab/gilt_bis-Spalten aus
    N2 nicht, obwohl die Live-DB sie laengst hatte). TRUNCATE checkpointed
    und leert die WAL-Datei, die Kopie ist danach ein vollstaendiger,
    eigenstaendiger Snapshot."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()
    stamp = datetime.now(CET).strftime("%Y%m%dT%H%M%S")
    dest = db_path.parent / f"knowledge.db.bak-{stamp}"
    shutil.copy2(db_path, dest)
    return dest


def quelle_aus_source(source: str | None) -> str | None:
    """Extrahiert die Quelldatei aus 'erzeugt aus <Datei> (Stand ...)'.
    Passt der String nicht exakt auf dieses Muster (Sammelknoten, freier
    Text, NULL) -> None, kein Rateversuch."""
    if not source or not source.startswith(SOURCE_PREFIX):
        return None
    idx = source.find(STAND_MARKER)
    if idx == -1:
        return None
    return source[len(SOURCE_PREFIX):idx]


def rang_aus_quelle(quelle: str | None) -> int | None:
    if quelle is None:
        return None
    if quelle == str(GLOBAL_CLAUDE_MD):
        return 1
    if quelle == str(HUB_CLAUDE_MD):
        return 2
    if quelle.startswith("docs/adr/") and quelle.endswith(".md"):
        return 3
    return None


def rang_fuer_source(source: str | None) -> int | None:
    """Die eine Stelle, die 'Herkunft -> Rang' entscheidet."""
    return rang_aus_quelle(quelle_aus_source(source))


# --- Anwenden --------------------------------------------------------------

def plan(db_path: Path) -> dict:
    """Berechnet je Knoten den Zielzustand, schreibt nichts. Liefert die
    Aenderungsliste plus eine Zaehlung je Rang -- Grundlage fuer sowohl
    --dry-run-Ausgabe als auch --apply."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, source, created_at, norm_rang, gilt_ab, gilt_bis FROM knowledge_nodes"
        ).fetchall()
    finally:
        conn.close()

    changes = []
    counts = {1: 0, 2: 0, 3: 0}
    for r in rows:
        rang = rang_fuer_source(r["source"])
        if rang is None:
            continue
        counts[rang] += 1
        neu = (rang, r["created_at"], None)
        alt = (r["norm_rang"], r["gilt_ab"], r["gilt_bis"])
        if alt != neu:
            changes.append({"id": r["id"], "vorher": alt, "nachher": neu})

    return {
        "gesamt": len(rows),
        "je_rang": counts,
        "ohne_rang": len(rows) - sum(counts.values()),
        "aenderungen": changes,
    }


def anwenden(db_path: Path, apply: bool) -> dict:
    result = plan(db_path)
    result["backup"] = None
    if not apply or not result["aenderungen"]:
        return result

    result["backup"] = str(_backup(db_path))
    # norm_entscheidung (Auftrag 2026-08-08): diese Zuweisung IST die
    # Entscheidung -- gilt_bis bleibt laut Modul-Docstring immer NULL
    # (unbefristet in Kraft), norm_entscheidung deshalb immer
    # norm_unbefristet. norm_entschieden_grund verweist auf die
    # deterministische ADR-034-Ableitung, nicht auf eine Einzelpruefung.
    jetzt = datetime.now(CET).isoformat(timespec="seconds")
    conn = sqlite3.connect(str(db_path))
    try:
        for c in result["aenderungen"]:
            rang, gilt_ab, gilt_bis = c["nachher"]
            conn.execute(
                "UPDATE knowledge_nodes SET norm_rang = ?, gilt_ab = ?, gilt_bis = ?, "
                "norm_entscheidung = 'norm_unbefristet', norm_entschieden_von = ?, "
                "norm_entschieden_am = ?, norm_entschieden_grund = ? WHERE id = ?",
                (rang, gilt_ab, gilt_bis, "skript:normrang.py", jetzt,
                 "deterministisch aus source abgeleitet (ADR-034): Rang folgt aus der Quelldatei "
                 "(globale/hub-CLAUDE.md oder ADR-Bestand), kein Ermessen", c["id"]),
            )
        conn.commit()
    finally:
        conn.close()
    return result


# --- CLI ---------------------------------------------------------------

def _print(result: dict, mode: str) -> None:
    print(f"=== normrang ({mode}) ===")
    print(f"Knoten gesamt: {result['gesamt']}")
    for rang in (1, 2, 3):
        print(f"  Rang {rang}: {result['je_rang'][rang]}")
    print(f"  ohne Rang (Fakt, NULL): {result['ohne_rang']}")
    print(f"Aenderungen: {len(result['aenderungen'])}")
    if result.get("backup"):
        print(f"Sicherung: {result['backup']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Vorgabe -- nur anzeigen, nicht schreiben")
    mode.add_argument("--apply", action="store_true", help="tatsaechlich schreiben")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()

    if not DB_PATH.exists():
        print(f"FEHLER: {DB_PATH} nicht gefunden.")
        return 1

    result = anwenden(DB_PATH, apply=args.apply)
    _print(result, "APPLY" if args.apply else "DRY-RUN (kein --apply)")
    return 0


# --- Selbsttest ----------------------------------------------------------

def _init_temp_db(path: Path) -> None:
    schema_sql = (HERE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(path))
    conn.executescript(schema_sql)
    conn.close()


def _insert_node(conn: sqlite3.Connection, node_id: str, path: str, source: str | None,
                  created_at: str) -> None:
    # norm_entscheidung (Auftrag 2026-08-08): diese Zeile entsteht als
    # unentschiedener Fakt -- anwenden() unten ist der Schritt, der die
    # Entscheidung trifft (setzt norm_rang UND norm_entscheidung zusammen,
    # niemals eines ohne das andere), nicht das Anlegen hier.
    conn.execute(
        """INSERT INTO knowledge_nodes
           (id, path, parent_path, project_id, title, summary, content, level, tags, source,
            created_at, updated_at, norm_entscheidung,
            norm_entschieden_von, norm_entschieden_am, norm_entschieden_grund)
           VALUES (?, ?, '/', 'shared', ?, 'summary', '', 1, '[]', ?, ?, ?, 'keine_norm', ?, ?, ?)""",
        (node_id, path, node_id, source, created_at, created_at,
         "skript:normrang.py", created_at, "Testvorrichtung vor der Rang-Ableitung -- noch kein Normtraeger"),
    )


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "knowledge.db"
        _init_temp_db(db_path)

        global_src = f"erzeugt aus {GLOBAL_CLAUDE_MD} (Stand 2026-08-05T00:00:00+02:00)"
        hub_src = f"erzeugt aus {HUB_CLAUDE_MD} (Stand 2026-08-05T00:00:00+02:00)"
        adr_src = "erzeugt aus docs/adr/001-use-drift-database.md (Stand 2026-08-05T00:00:00+02:00)"
        sammel_src = "normbestand.py::ensure_category"
        fakt_src = "erzeugt aus /Volumes/daten/Begod2026/hub/scripts/methodik_export.py (Stand X)"

        conn = sqlite3.connect(str(db_path))
        try:
            _insert_node(conn, "n-global", "/x/global", global_src, "2026-08-01T00:00:00+01:00")
            _insert_node(conn, "n-hub", "/x/hub", hub_src, "2026-08-02T00:00:00+01:00")
            _insert_node(conn, "n-adr", "/x/adr", adr_src, "2026-08-03T00:00:00+01:00")
            _insert_node(conn, "n-sammel", "/x/sammel", sammel_src, "2026-08-04T00:00:00+01:00")
            _insert_node(conn, "n-fakt", "/x/fakt", fakt_src, "2026-08-04T00:00:00+01:00")
            _insert_node(conn, "n-nosrc", "/x/nosrc", None, "2026-08-04T00:00:00+01:00")
            conn.commit()
        finally:
            conn.close()

        # Reine Ableitung, ohne DB -- die drei Muster und die Nicht-Treffer.
        assert rang_fuer_source(global_src) == 1
        assert rang_fuer_source(hub_src) == 2
        assert rang_fuer_source(adr_src) == 3
        assert rang_fuer_source(sammel_src) is None
        assert rang_fuer_source(fakt_src) is None
        assert rang_fuer_source(None) is None

        res1 = anwenden(db_path, apply=True)
        assert res1["je_rang"] == {1: 1, 2: 1, 3: 1}, res1["je_rang"]
        assert res1["ohne_rang"] == 3, res1  # sammel, fakt, nosrc
        assert len(res1["aenderungen"]) == 3
        assert res1["backup"] and Path(res1["backup"]).exists()

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            g = conn.execute("SELECT norm_rang, gilt_ab, gilt_bis FROM knowledge_nodes WHERE id='n-global'").fetchone()
            assert (g["norm_rang"], g["gilt_ab"], g["gilt_bis"]) == (1, "2026-08-01T00:00:00+01:00", None), dict(g)
            h = conn.execute("SELECT norm_rang FROM knowledge_nodes WHERE id='n-hub'").fetchone()
            assert h["norm_rang"] == 2
            a = conn.execute("SELECT norm_rang FROM knowledge_nodes WHERE id='n-adr'").fetchone()
            assert a["norm_rang"] == 3
            for nid in ("n-sammel", "n-fakt", "n-nosrc"):
                row = conn.execute("SELECT norm_rang FROM knowledge_nodes WHERE id=?", (nid,)).fetchone()
                assert row["norm_rang"] is None, (nid, row["norm_rang"])
        finally:
            conn.close()

        # Zweiter Lauf: identischer Bestand -> keine Aenderung, keine neue Sicherung.
        res2 = anwenden(db_path, apply=True)
        assert res2["aenderungen"] == [], res2["aenderungen"]
        assert res2["backup"] is None
        assert res2["je_rang"] == res1["je_rang"]

        # Dritter Lauf ohne --apply auf frischer Kopie: gleiche Zahlen, kein Schreiben.
        copy_path = tmp_path / "kopie.db"
        shutil.copy2(db_path, copy_path)
        res3 = anwenden(copy_path, apply=False)
        assert res3["je_rang"] == res1["je_rang"]
        assert res3["backup"] is None

    print("SELFTEST OK: Rang aus Herkunft, Fakt bleibt NULL, idempotent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
