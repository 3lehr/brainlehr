#!/usr/bin/env python3
"""
mcp_veraltet.py — meldet veraltete Brainlehr-MCP-Prozesse (UserPromptSubmit-Hook).

Ein laufender MCP-Server haelt beim Start geladenen Code im Speicher. Wird die
Quelldatei danach repariert, schreiben alle noch laufenden Prozesse weiter mit
dem alten (falschen) Code in die gemeinsame brainlehr.db — kein Melder bisher.

Erkennung ohne Servereingriff: Prozessstart (ps lstart) je Prozess mit der
mtime der beim Start geladenen relevanten Laufzeitdateien vergleichen. Eine
Datei neuer als Prozessstart -> Prozess veraltet.

Nur melden, nichts toeten/neu starten. Hoechstens 1x pro Session (Marker in
/tmp) -- ausser bei manuellem Aufruf mit ``--erneut``, das ignoriert den
Marker (L-47a196: ein Sitzungsmarker darf beim Aufruf von Hand nicht
Schweigen erzeugen). ps/Datei nicht lesbar -> still bleiben. IMMER exit 0.

Je Fund wird der Elternprozess ermittelt: gehoert er selbst zu einem
Claude-Code-Fenster (Pfad enthaelt ``Contents/MacOS/claude``), erreicht ein
Sitzungsneustart den Fund. Sonst haelt ein fremder Prozess (z.B. ein anderer
MCP-Klient) den Server -- dort hilft ein Neustart der Claude-Fenster nicht,
das wird pro Fund ausdruecklich gesagt (L-47a196).
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
# Python lädt beide Module einmal beim Prozessstart. Der Scorer beeinflusst die
# sichtbare ``bestandslage`` direkt, ohne dass sich der Server-Wrapper ändert.
RUNTIME_FILES = (_Path(SERVER_FILE), _w / "kern" / "relevanzlage.py")
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


def latest_runtime_mtime() -> float:
    """Änderungsgrenze des Codes, den der MCP-Prozess beim Start lädt."""
    return max(os.path.getmtime(path) for path in RUNTIME_FILES)


def eigenes_fenster(eltern_kommando: str) -> bool:
    """Läuft der Elternprozess selbst als Claude-Code-Fenster?"""
    return "Contents/MacOS/claude" in eltern_kommando


def halter_label(eltern_kommando: str) -> str:
    """Sprechender Name des Halters aus der Kommandozeile des Elternprozesses."""
    tokens = eltern_kommando.split()
    for t in tokens:
        if t.endswith(".py"):
            return os.path.basename(t)
    return os.path.basename(tokens[0]) if tokens else "unbekannt"


def ist_serverinstanz(kommando: str) -> bool:
    """Laeuft in diesem Prozess wirklich der Server -- oder steht sein Pfad nur
    als TEXT in der Kommandozeile?

    `pgrep -f` sucht in der vollen Kommandozeile. Das Claude-Programm traegt
    den Serverpfad in seinem `--mcp-config`-JSON mit sich; es wird damit
    gefunden, obwohl es den Server nur STARTET, statt ihn zu sein. Gemessen
    2026-08-19: von 14 gemeldeten Funden waren vier solche Textreffer
    (PID 10662, 10663, 63304, 63305) -- und die Gesamtzahl stimmte trotzdem,
    weil zufaellig vier echte Instanzen zu Recht fehlten (nach der Aenderung
    gestartet). Vier Fehlalarme, die vier korrekte Auslassungen aufheben,
    sind die gefaehrlichste Sorte Zahl: sie uebersteht eine Stichprobe auf
    die Summe.

    Unterscheidungsmerkmal: In einer echten Instanz ist der Pfad ein eigenes
    ARGUMENT des Interpreters, steht also als vollstaendiges, durch
    Leerzeichen getrenntes Feld da. Im JSON steckt er in Anfuehrungszeichen
    und Klammern und ist deshalb nie ein eigenes Feld."""
    return SERVER_FILE in kommando.split()


def prozessliste(pids: list[str]) -> list[tuple[str, str, float]]:
    """(pid, ppid, start-timestamp) je laufendem MCP-Prozess."""
    out = subprocess.run(
        # command= zusaetzlich, damit ist_serverinstanz() blosse Textreffer
        # aussortieren kann -- lstart hat feste Feldzahl, das Kommando kommt
        # deshalb ZULETZT und wird als Rest gelesen.
        ["ps", "-o", "pid=,ppid=,lstart=,command=", "-p", ",".join(pids)],
        capture_output=True, text=True, timeout=2,
    ).stdout
    ergebnis = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        felder = line.split(maxsplit=2)
        if len(felder) < 3:
            continue
        pid, ppid, rest = felder
        # lstart belegt genau 5 Felder ("Wed Aug 19 10:35:16 2026"), alles
        # danach ist das Kommando.
        zeit_felder = rest.split(maxsplit=5)
        if len(zeit_felder) < 5:
            continue
        zeit = " ".join(zeit_felder[:5])
        kommando = zeit_felder[5] if len(zeit_felder) > 5 else ""
        try:
            started = datetime.strptime(zeit, LSTART_FMT).timestamp()
        except Exception:
            continue
        if not ist_serverinstanz(kommando):
            continue
        ergebnis.append((pid, ppid, started))
    return ergebnis


def eltern_kommandos(ppids: set[str]) -> dict[str, str]:
    """ppid -> Kommandozeile, fuer die Halter-Bestimmung."""
    if not ppids:
        return {}
    out = subprocess.run(
        ["ps", "-o", "pid=,command=", "-p", ",".join(sorted(ppids))],
        capture_output=True, text=True, timeout=2,
    ).stdout
    ergebnis = {}
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        teile = line.split(maxsplit=1)
        if len(teile) == 2:
            ergebnis[teile[0]] = teile[1]
    return ergebnis


def auswerten(prozesse: list[tuple[str, str, float]], eltern: dict[str, str], mtime: float) -> list[str]:
    """Meldungszeilen je veraltetem Fund -- Kern der Bewertung, ohne ps-Aufruf."""
    zeilen = []
    for pid, ppid, started in prozesse:
        if not (mtime > started):
            continue  # bei Gleichstand gewinnt der Prozess (jünger oder gleich alt wie der Code)
        alter = humanize(time.time() - mtime)
        eltern_cmd = eltern.get(ppid, "")
        if eigenes_fenster(eltern_cmd):
            zeilen.append(
                f"PID {pid} (Reparatur vor {alter} noch nicht geladen) — "
                f"eigenes Claude-Fenster, Sitzung neu starten."
            )
        else:
            halter = halter_label(eltern_cmd)
            zeilen.append(
                f"PID {pid} (Reparatur vor {alter} noch nicht geladen) — "
                f"gehalten von {halter} (PID {ppid}), dort neu starten. "
                f"Ein Neustart der Claude-Fenster erreicht diesen Fund nicht."
            )
    return zeilen


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    erneut = "--erneut" in sys.argv[1:]
    marker = state_path(payload.get("session_id"))
    if not erneut and os.path.exists(marker):
        return

    try:
        mtime = latest_runtime_mtime()
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
        prozesse = prozessliste(pids)
        eltern = eltern_kommandos({ppid for _pid, ppid, _t in prozesse})
    except Exception:
        return

    zeilen = auswerten(prozesse, eltern, mtime)
    if not zeilen:
        return

    try:
        with open(marker, "w") as f:
            f.write("1")
    except Exception:
        pass

    print(f"Brainlehr MCP: {len(zeilen)} laufende Prozess(e) veraltet.")
    for z in zeilen:
        print(f"  {z}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
