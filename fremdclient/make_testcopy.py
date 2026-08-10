#!/usr/bin/env python3
"""Zieht eine Testkopie der echten knowledge.db nach shared-knowledge/fremdclient/.

Muster aus Commit 2cb22705f (migrate_normfelder.py::_backup): WAL-Checkpoint
(TRUNCATE) auf der ECHTEN DB vor dem Kopieren, sonst fehlen committete,
aber noch nicht zurueckgeschriebene Aenderungen aus dem WAL-Journal in der
Kopie. Schreibt NICHTS in die echte DB ausser dem Checkpoint selbst (das ist
kein Dateninhalt, nur WAL->Hauptdatei zurueckschreiben).
"""

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
import shutil
import sqlite3
import sys
from pathlib import Path

REAL_DB = Path(__file__).parent.parent / "knowledge.db"
TEST_DB = Path(__file__).parent / "knowledge.db"


def make_testcopy() -> Path:
    conn = sqlite3.connect(str(REAL_DB))
    try:
        busy, log_frames, checkpointed = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if busy:
            raise RuntimeError(
                f"WAL-Checkpoint blockiert (busy={busy}, log={log_frames} Frames, "
                f"{checkpointed} checkpointed) -- ein anderer Prozess schreibt gerade. "
                "Testkopie abgebrochen statt unvollstaendig angelegt."
            )
    finally:
        conn.close()
    shutil.copy2(REAL_DB, TEST_DB)
    return TEST_DB


if __name__ == "__main__":
    dest = make_testcopy()
    print(f"Testkopie: {dest}")
    sys.exit(0)
