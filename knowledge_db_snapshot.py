"""Momentaufnahme der knowledge.db (Auftrag 2026-08-08, Teil 2): Kopie des
heutigen Bestands, damit spaeter aufgezeichnete Anfragen (recall_log.jsonl,
siehe knowledge_recall_replay.py) gegen GENAU diesen Stand erneut abgerufen
werden koennen, nicht gegen einen, der seither weitergewachsen ist.

Aufruf: python3 knowledge_db_snapshot.py [zielverzeichnis]
Vorgabe-Zielverzeichnis: shared-knowledge/snapshots/
Dateiname: knowledge_YYYY-MM-DD.db (mehrfacher Aufruf am selben Tag
ueberschreibt -- die letzte Momentaufnahme des Tages gilt).
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parent
DB = SHARED_KNOWLEDGE / "knowledge.db"
SNAPSHOT_DIR = SHARED_KNOWLEDGE / "snapshots"


def freeze(zielverzeichnis: Path | None = None, quelle: Path | None = None) -> dict:
    """Kopiert knowledge.db per sqlite3-Online-Backup-API (konsistent auch
    bei gleichzeitigem Schreibzugriff einer anderen Sitzung -- ein reines
    Datei-Kopieren koennte mitten in einer Schreibtransaktion greifen).
    Rueckgabe: Pfad, Datum, Groesse in Byte, Bestandsgroessen zum
    Aufnahmezeitpunkt."""
    quelle = quelle or DB
    ziel_dir = zielverzeichnis or SNAPSHOT_DIR
    ziel_dir.mkdir(parents=True, exist_ok=True)
    datum = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ziel = ziel_dir / f"knowledge_{datum}.db"

    src = sqlite3.connect(f"file:{quelle}?mode=ro", uri=True)
    dst = sqlite3.connect(str(ziel))
    try:
        with dst:
            src.backup(dst)
    finally:
        dst.close()
        src.close()

    conn = sqlite3.connect(f"file:{ziel}?mode=ro", uri=True)
    try:
        nodes = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        lessons = conn.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
    finally:
        conn.close()

    return {
        "pfad": str(ziel),
        "datum": datum,
        "bytes": ziel.stat().st_size,
        "bestand_knowledge_nodes": nodes,
        "bestand_lessons_learned": lessons,
    }


def demo() -> None:
    """Selbsttest gegen eine kleine eigene Quell-DB (kein Zugriff auf die
    echte knowledge.db noetig -- schnell, deterministisch)."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        quelle = Path(td) / "quelle.db"
        conn = sqlite3.connect(str(quelle))
        conn.executescript((SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, "
            "content, level, source, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
            "VALUES ('n1', '/t', 'shared', 'T', 'S', NULL, 0, 'test', "
            "'keine_norm', 'skript:knowledge_db_snapshot.py', 'Testvorrichtung, keine echte Norm-Pruefung')"
        )
        conn.commit()
        conn.close()

        r = freeze(Path(td) / "snap", quelle=quelle)
        assert Path(r["pfad"]).exists(), r
        assert r["bytes"] > 0, r
        assert r["bestand_knowledge_nodes"] == 1, r
        assert r["bestand_lessons_learned"] == 0, r

        # Zweiter Aufruf am selben Tag ueberschreibt (gleicher Dateiname), kein zweiter Snapshot.
        r2 = freeze(Path(td) / "snap", quelle=quelle)
        assert r2["pfad"] == r["pfad"], (r, r2)
        print("demo ok:", r)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
        sys.exit(0)
    ziel = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    ergebnis = freeze(ziel)
    print(f"Momentaufnahme: {ergebnis['pfad']}")
    print(f"Datum: {ergebnis['datum']}")
    print(f"Groesse: {ergebnis['bytes']} Byte")
    print(f"Bestand: {ergebnis['bestand_knowledge_nodes']} Knoten, "
          f"{ergebnis['bestand_lessons_learned']} Lehren")
