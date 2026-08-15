#!/usr/bin/env python3
"""agentenanker_einspielung.py -- SubagentStart-Haken, Teil 2 des verengten
Abrufs (ADR-022, Entscheidung 3). Gegenstueck zu `agentenanker_abruf.py`
(PreToolUse, Matcher Agent), das dort schon GERECHNET hat -- SubagentStart
traegt den Auftragstext selbst nicht (siehe Docstring dort), darum spielt
dieser Haken nur ein, was der andere in der Pending-Datei hinterlegt hat.

FIFO je Sitzung, aeltester Eintrag zuerst geleert -- dieselbe Naeherung wie
`hub/scripts/agent_register_hook.py::_pop_pending`: bei mehreren gleichzeitig
gestarteten Agenten in derselben Sitzung ist die Zuordnung best-effort in
Aufrufreihenfolge, keine ID-exakte Zustellung (SubagentStart liefert keine
tool_use_id, mit der sich das haerter binden liesse -- selbes Vorbild, selbe
Grenze).

FAIL-OPEN: kein Eintrag, kaputte Datei, kaputtes JSON -> exit 0, nichts
ausgegeben. Ein Fehler hier darf den Agentenstart NIEMALS verhindern.

Selbsttest: python3 agentenanker_einspielung.py --selftest
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

PENDING = Path(tempfile.gettempdir()) / "claude-agentenanker-pending.jsonl"


def pop_fuer_sitzung(pending_pfad: Path, session: str) -> str | None:
    """Aeltesten Pending-Block dieser Sitzung entnehmen (FIFO), Rest zurueck-
    schreiben. Kaputte Zeilen werden stillschweigend uebersprungen -- weder
    Ursache fuer einen Fehler noch fuer verlorene andere Sitzungen."""
    try:
        with open(pending_pfad, encoding="utf-8") as f:
            zeilen = f.readlines()
    except OSError:
        return None

    gefunden = None
    rest = []
    for zeile in zeilen:
        z = zeile.strip()
        if not z:
            continue
        if gefunden is None:
            try:
                d = json.loads(z)
            except Exception:
                continue
            if d.get("session") == session and d.get("block"):
                gefunden = str(d["block"])
                continue
        rest.append(zeile if zeile.endswith("\n") else zeile + "\n")

    if gefunden is None:
        return None
    try:
        with open(pending_pfad, "w", encoding="utf-8") as f:
            f.writelines(rest)
    except OSError:
        pass
    return gefunden


def main() -> int:
    try:
        eingabe = json.load(sys.stdin)
    except Exception:
        return 0
    session = str(eingabe.get("session_id") or "")
    if not session:
        return 0
    # Muss zum tatsaechlich feuernden Ereignis passen (siehe regelwechsel.py-
    # Vermerk: ein falsches Etikett verwirft der Klient den additionalContext
    # ohne Fehlermeldung -- ein stiller zweiter Blindgaenger).
    ereignis = str(eingabe.get("hook_event_name") or "SubagentStart")

    try:
        block = pop_fuer_sitzung(PENDING, session)
    except Exception:
        return 0
    if not block:
        return 0

    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": ereignis, "additionalContext": block},
        "systemMessage": "Existenzprobe zu diesem Auftrag im Kontext",
        "continue": True,
        "suppressOutput": True,
    }))
    return 0


def _selftest() -> int:
    import contextlib
    import io

    ok = True
    with tempfile.TemporaryDirectory() as td:
        pfad = Path(td) / "pending.jsonl"
        rows = [
            {"session": "s1", "ts": 1.0, "block": "erster block s1"},
            {"session": "s2", "ts": 2.0, "block": "block s2"},
            {"session": "s1", "ts": 3.0, "block": "zweiter block s1"},
        ]
        with open(pfad, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
            f.write("{kaputt\n")

        b = pop_fuer_sitzung(pfad, "s1")
        okk = b == "erster block s1"
        ok &= okk
        print(f"  FIFO: aeltester s1-Block zuerst: {'OK' if okk else 'FEHLER (' + str(b) + ')'}")

        rest = pfad.read_text(encoding="utf-8")
        okk = "block s2" in rest and "zweiter block s1" in rest and "erster block s1" not in rest
        ok &= okk
        print(f"  Rest bleibt erhalten, Entnommenes verschwindet: {'OK' if okk else 'FEHLER'}")

        # Grenzwert: Sitzung ohne Eintrag -> None, kein Fehler
        b2 = pop_fuer_sitzung(pfad, "unbekannt")
        okk = b2 is None
        ok &= okk
        print(f"  Unbekannte Sitzung -> kein Treffer: {'OK' if okk else 'FEHLER'}")

        # Grenzwert: Datei fehlt komplett
        b3 = pop_fuer_sitzung(Path(td) / "fehlt.jsonl", "s1")
        okk = b3 is None
        ok &= okk
        print(f"  Fehlende Pending-Datei -> kein Fehler: {'OK' if okk else 'FEHLER'}")

        # main(): Treffer -> hookSpecificOutput mit passendem hookEventName
        pfad2 = Path(td) / "pending2.jsonl"
        pfad2.write_text(json.dumps({"session": "sX", "ts": 1.0, "block": "TEXT"}) + "\n",
                          encoding="utf-8")
        global PENDING
        alt = PENDING
        PENDING = pfad2
        alt_stdin = sys.stdin
        try:
            buf = io.StringIO()
            sys.stdin = io.StringIO(json.dumps(
                {"session_id": "sX", "hook_event_name": "SubagentStart"}))
            with contextlib.redirect_stdout(buf):
                main()
            ausgabe = buf.getvalue()
        finally:
            sys.stdin = alt_stdin
            PENDING = alt
        d = json.loads(ausgabe)
        okk = (d["hookSpecificOutput"]["hookEventName"] == "SubagentStart"
               and d["hookSpecificOutput"]["additionalContext"] == "TEXT")
        ok &= okk
        print(f"  main() spielt Treffer mit korrektem Etikett ein: {'OK' if okk else 'FEHLER'}")

        # Gegenprobe: leere Pending-Datei -> main() schweigt
        pfad3 = Path(td) / "leer.jsonl"
        pfad3.write_text("", encoding="utf-8")
        PENDING = pfad3
        try:
            buf = io.StringIO()
            sys.stdin = io.StringIO(json.dumps(
                {"session_id": "sX", "hook_event_name": "SubagentStart"}))
            with contextlib.redirect_stdout(buf):
                main()
            ausgabe = buf.getvalue()
        finally:
            sys.stdin = alt_stdin
            PENDING = alt
        okk = ausgabe == ""
        ok &= okk
        print(f"  Gegenprobe: leere Pending-Datei -> still: {'OK' if okk else 'FEHLER'}")

    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
