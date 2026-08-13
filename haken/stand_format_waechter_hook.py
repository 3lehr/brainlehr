#!/usr/bin/env python3
"""PostToolUse-Haken: STAND.md gegen ihr Pflichtformat pruefen.

Anlass (Aufgabe 103): STAND.md ist die EINE Datei, die der Betreiber nach
einer Abwesenheit liest. Am 2026-08-13 stand sie bei 56 Zeilen statt der
vorgeschriebenen 10 -- von zwei Sitzungen unabhaengig voneinander verletzt,
von keiner bemerkt (Commit c90be15). Die Regel existierte, ein Mechanismus
nicht. Dieser Haken ist der Mechanismus.

Pflichtformat ermittelt aus der Sache, nicht behauptet: Commit c90be15
("docs(brainlehr): STAND auf Pflichtformat -- 56 Zeilen waren 5,6-fach
darueber") legt die Datei nach dem Kuerzen auf exakt 10 Zeilen fest
(`git show c90be15:STAND.md | wc -l` == 10) und benennt die Regel woertlich:
"Die Hausregel schreibt fuer STAND.md hoechstens 10 Zeilen vor." Deckt sich
mit der Angabe im Auftrag -- keine Abweichung zu melden.

Er BLOCKIERT nicht und AENDERT die Datei nicht: PostToolUse laeuft erst nach
dem Schreibzugriff, ein Veto waere wirkungslos, und ein automatisches Kuerzen
wuerde genau das Wissen loeschen, das die eigentliche Regel (fluechtiger
Uebergabe-Zettel, kein Archiv) erst manuell aussortieren soll. Der Befund geht
als additionalContext ans Modell, das dann selbst kuerzt.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

LIMIT = 10


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except Exception:
        return 0
    pfad = (daten.get("tool_input") or {}).get("file_path")
    if not pfad or Path(pfad).name != "STAND.md" or not Path(pfad).exists():
        return 0
    try:
        zeilen = len(Path(pfad).read_text(encoding="utf-8").splitlines())
    except Exception:
        return 0
    if zeilen <= LIMIT:
        return 0
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": (
                        f"STAND-Waechter: STAND.md hat {zeilen} Zeilen, "
                        f"Pflichtformat ist hoechstens {LIMIT}."
                    ),
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
