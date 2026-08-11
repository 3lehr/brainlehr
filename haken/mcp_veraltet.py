#!/usr/bin/env python3
"""
mcp_veraltet.py — meldet veraltete knowledge_mcp_server.py-Prozesse (UserPromptSubmit-Hook).

Ein laufender MCP-Server haelt beim Start geladenen Code im Speicher. Wird die
Quelldatei danach repariert, schreiben alle noch laufenden Prozesse weiter mit
dem alten (falschen) Code in die gemeinsame brainlehr.db — kein Melder bisher.

Erkennung ohne Servereingriff: Prozessstart (ps lstart) je Prozess mit der
mtime von knowledge_mcp_server.py vergleichen. Datei neuer als Prozessstart
-> Prozess veraltet.

Nur melden, nichts toeten/neu starten. Hoechstens 1x pro Session (Marker in
/tmp). ps/Datei nicht lesbar -> still bleiben. IMMER exit 0.
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
import json
import os
import subprocess
import sys
import time
from datetime import datetime

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import ort  # Ein Ort fuer den Pfad, siehe haken/ort.py (L-6c6661)
SERVER_FILE = str(ort.SERVER)
STATE_DIR = "/tmp"
LSTART_FMT = "%a %b %d %H:%M:%S %Y"


def state_path(session_id: str) -> str:
    sid = "".join(c for c in (session_id or "unknown") if c.isalnum() or c in "-_")[:12]
    return os.path.join(STATE_DIR, f"claude-mcp-veraltet-{sid}.txt")


def humanize(seconds: float) -> str:
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}min"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h"
    return f"{hours // 24}d"


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    marker = state_path(payload.get("session_id"))
    if os.path.exists(marker):
        return

    try:
        mtime = os.path.getmtime(SERVER_FILE)
    except OSError:
        return

    try:
        pids = subprocess.run(
            ["pgrep", "-f", SERVER_FILE], capture_output=True, text=True, timeout=2
        ).stdout.split()
    except Exception:
        return
    if not pids:
        return

    try:
        out = subprocess.run(
            ["ps", "-o", "lstart=", "-p", ",".join(pids)],
            capture_output=True, text=True, timeout=2,
        ).stdout
    except Exception:
        return

    stale_ages = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            started = datetime.strptime(line, LSTART_FMT).timestamp()
        except Exception:
            continue
        if mtime > started:
            stale_ages.append(time.time() - mtime)

    if not stale_ages:
        return

    try:
        with open(marker, "w") as f:
            f.write("1")
    except Exception:
        pass

    print(
        f"knowledge_mcp_server.py: {len(stale_ages)} laufende Prozess(e) veraltet "
        f"(Reparatur vor {humanize(max(stale_ages))} noch nicht geladen) — Sitzung neu starten."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
