#!/usr/bin/env python3
"""endgueltig_entfernen.py -- Auftrag 2026-08-06 (Luecke "kein Loeschweg fuer
die KI"). Der MENSCHLICHE Gegenpart zu knowledge_zurueckziehen (MCP-Werkzeug,
reversibel, KI darf es ohne Rueckfrage aufrufen). Dieses Skript loescht eine
Zeile aus knowledge_nodes ECHT und endgueltig -- kein Rueckweg danach.

NICHT aus knowledge_mcp_server.py aufrufbar: kein Eintrag in dessen TOOLS-
Dict ruft dieses Skript oder importiert seine delete()-Funktion (grep
bestaetigt das, siehe Test). Nur von Hand: verlangt die Knotenkennung UND
eine woertlich getippte Bestaetigung (REQUIRED_CONFIRMATION), macht vorher
PRAGMA wal_checkpoint(TRUNCATE) plus Sicherungskopie (Lehre L-218f1e, gleiches
Muster wie jede andere additive Migration in diesem Verzeichnis). Der
Loeschvorgang landet im access_log wie jeder andere Schreibzugriff (importiert
log_access aus knowledge_mcp_server -- die Abhaengigkeit geht nur in diese
Richtung, der Server importiert dieses Skript nicht).

Usage:
    .venv/bin/python shared-knowledge/endgueltig_entfernen.py <node_id_oder_pfad>
    .venv/bin/python shared-knowledge/endgueltig_entfernen.py --selftest
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import knowledge_mcp_server as kms  # noqa: E402  -- nur log_access/now_iso wiederverwendet

DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (HERE / "brainlehr.db"))
CET = timezone(timedelta(hours=1))
REQUIRED_CONFIRMATION = "ENDGUELTIG LOESCHEN"


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
    stamp = datetime.now(CET).strftime("%Y%m%dT%H%M%S")
    dest = db_path.parent / f"{db_path.name}.bak-{stamp}"
    shutil.copy2(db_path, dest)
    return dest


def delete_node(db_path: Path, kennung: str, bestaetigung: str) -> dict:
    """Kein Backup, keine Aenderung, solange bestaetigung nicht exakt
    REQUIRED_CONFIRMATION ist -- geprueft VOR jedem Schreibzugriff."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id, path, title FROM knowledge_nodes WHERE id = ? OR path = ?",
            (kennung, kennung),
        ).fetchone()
        if not row:
            return {"error": f"Node not found: {kennung}", "status": "abgebrochen"}
        if bestaetigung != REQUIRED_CONFIRMATION:
            return {
                "error": f"Bestaetigung fehlt oder falsch (erwartet exakt {REQUIRED_CONFIRMATION!r}). "
                         "Nichts geloescht.",
                "status": "abgebrochen", "id": row["id"], "path": row["path"],
            }
    finally:
        conn.close()

    backup_path = _backup(db_path)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("DELETE FROM knowledge_nodes WHERE id = ?", (row["id"],))
        kms.log_access(conn, row["path"], "endgueltig_entfernen", query=row["id"],
                        actor=os.environ.get("USER") or "mensch")
        conn.commit()
    finally:
        conn.close()

    return {"status": "geloescht", "id": row["id"], "path": row["path"],
            "title": row["title"], "backup": str(backup_path)}


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()

    args = [a for a in sys.argv[1:] if a != "--selftest"]
    if not args:
        print("Usage: endgueltig_entfernen.py <node_id_oder_pfad> [Bestaetigung]")
        return 1
    kennung = args[0]
    bestaetigung = args[1] if len(args) > 1 else input(
        f"Knoten {kennung!r} ENDGUELTIG loeschen, kein Rueckweg. "
        f"Zum Bestaetigen exakt eingeben: {REQUIRED_CONFIRMATION!r}\n> "
    )

    if not DB_PATH.exists():
        print(f"FEHLER: {DB_PATH} nicht gefunden.")
        return 1

    res = delete_node(DB_PATH, kennung, bestaetigung)
    print(res)
    return 0 if res.get("status") == "geloescht" else 1


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "brainlehr.db"
        schema_sql = (HERE / "schema.sql").read_text(encoding="utf-8")
        conn = sqlite3.connect(str(db_path))
        conn.executescript(schema_sql)
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, anlass, "
            "norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
            "VALUES ('n1', '/x', 'shared', 'Titel', 'Summary', 'Inhalt', 0, 'quelle', 'unbekannt', "
            "'keine_norm', 'skript:endgueltig_entfernen.py', 'Testvorrichtung, keine echte Norm-Pruefung')"
        )
        conn.commit()
        conn.close()

        # Ohne Bestaetigung: nichts geloescht.
        res1 = delete_node(db_path, "n1", "falsch")
        assert res1["status"] == "abgebrochen", res1
        conn = sqlite3.connect(str(db_path))
        assert conn.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE id='n1'").fetchone()[0] == 1
        conn.close()

        # Mit Bestaetigung: geloescht, Sicherung vorhanden, im access_log.
        res2 = delete_node(db_path, "n1", REQUIRED_CONFIRMATION)
        assert res2["status"] == "geloescht", res2
        assert Path(res2["backup"]).exists()
        conn = sqlite3.connect(str(db_path))
        assert conn.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE id='n1'").fetchone()[0] == 0
        logged = conn.execute(
            "SELECT COUNT(*) FROM access_log WHERE action='endgueltig_entfernen' AND node_path='/x'"
        ).fetchone()[0]
        assert logged == 1, "Loeschung fehlt im access_log"
        conn.close()

    print("SELFTEST OK: ohne Bestaetigung nichts geloescht, mit Bestaetigung Zeile weg + Sicherung + access_log.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
