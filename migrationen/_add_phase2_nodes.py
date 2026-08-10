#!/usr/bin/env python3
"""Adds Phase 2 summary nodes to knowledge.db."""

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
import sqlite3
import uuid
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB = Path(__file__).parent / "knowledge.db"
CET = timezone(timedelta(hours=1))
now = datetime.now(CET).strftime("%Y-%m-%dT%H:%M:%S+01:00")

conn = sqlite3.connect(str(DB))
conn.execute("PRAGMA journal_mode=WAL")

nodes = [
    (str(uuid.uuid4())[:12], "/lessons/phase2-summary", "/lessons", "shared",
     "Meta-Optimierung Phase 2 Zusammenfassung",
     "Phase 2: Knowledge-DB, MCP-Server, Tests, Fehler-Lern-System, Timestamps, CodeGen, Prompt-Templates.",
     "Phase 2 abgeschlossen: 5 Phasen (A-E), 11 Artefakte, 133/133 Tests gruen. 6 MCP-Server mit 66 Tools. 39 Knowledge-Nodes. 9 Prompt-Templates. Zeitstempel-Pflicht D-TS-001. codeGeneration.instructions Stack-spezifisch.",
     2, json.dumps(["meta-optimization", "phase2", "summary"]), "konsil/meta-opt-phase2", 0.95, now, now),
    (str(uuid.uuid4())[:12], "/tools/lesson-recorder", "/tools", "shared",
     "Lesson Recorder CLI",
     "CLI-Tool fuer automatisches Fehler-Lern-System mit Reflexion-Pattern (Threshold n>=3).",
     "lesson_recorder.py: record|bump|query|stats|auto-rules. Erkennt aehnliche Lessons, bumpt Occurrences, generiert automatisch .instructions.md Regeln bei >=3 Wiederholungen.",
     1, json.dumps(["lesson", "error-learning", "reflexion"]), "implementation", 0.9, now, now),
]

for n in nodes:
    conn.execute(
        "INSERT OR IGNORE INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, content, level, tags, source, confidence, created_at, updated_at, "
        "norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'keine_norm','skript:_add_phase2_nodes.py','Zusammenfassungsknoten, kein Normtext')",
        n
    )
conn.commit()
total = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
print(f"OK: {len(nodes)} Nodes hinzugefuegt. Total: {total}")
conn.close()
