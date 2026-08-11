#!/usr/bin/env python3
"""Eine Einladungs-PIN einloesen und das Geheimnis DIREKT in die
Klientenkonfiguration schreiben -- ohne es anzuzeigen.

WARUM DIESES SKRIPT UEBERHAUPT EXISTIERT, obwohl es das MCP-Werkzeug
`knowledge_anmelden` schon gibt: Dessen Antwort enthaelt das Geheimnis, und
sein eigener Hinweistext sagt, wohin es gehoert -- "in die Konfiguration des
Klienten als BRAINLEHR_GEHEIMNIS, nicht in den Gespraechsverlauf". Ruft der
Assistent das Werkzeug auf, landet es aber genau dort: in seinem Kontext und
damit im Transkript, dauerhaft. Dieses Skript schliesst die Luecke -- es
laeuft als eigener Prozess, schreibt in einem Zug und gibt nur zurueck, wie
viele Zeichen gesetzt wurden.

Die PIN selbst darf durch den Verlauf laufen: sie ist einmalig, befristet und
nach der Einloesung verbraucht. Genau dafuer ist sie gebaut -- der Mensch gibt
sie ausser Band weiter, und die Einloesung ist der Beweis, dass er es tat.

Aufruf:  python3 pflege/pin_einloesen.py <PIN>
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path.insert(0, str(_w / "kern"))

import ausweis  # noqa: E402

KONFIG = Path.home() / ".claude.json"


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    pin = sys.argv[1].strip()

    try:
        erg = ausweis.einloesen(pin)
    except PermissionError as fehler:
        # Der Grund steht in der Meldung des Moduls (abgelaufen, verbraucht,
        # unbekannt) -- nicht selbst umformulieren, sonst geht er verloren.
        print(f"nicht eingeloest: {fehler}", file=sys.stderr)
        return 1

    geheimnis = erg["geheimnis"]  # ab hier nie drucken, nie protokollieren

    if not KONFIG.exists():
        print(f"{KONFIG} fehlt -- nichts geschrieben.", file=sys.stderr)
        return 1

    # Sicherung VOR dem Schreiben: die Datei traegt die gesamte
    # Klientenkonfiguration, nicht nur diesen einen Wert.
    sicherung = KONFIG.with_suffix(
        f".json.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(KONFIG, sicherung)

    konf = json.loads(KONFIG.read_text(encoding="utf-8"))
    knoten = konf.setdefault("mcpServers", {}).setdefault("knowledge", {})
    env = knoten.setdefault("env", {})
    env["BRAINLEHR_GEHEIMNIS"] = geheimnis
    # Der actor MUSS der Ausweisname sein, sonst misst das Feld nichts: es
    # stand zuvor auf einem Personennamen, waehrend eine Maschine schrieb --
    # genau die Tautologie, die der Pruefer mit 88 % meldet.
    env["BEGOD_KNOWLEDGE_ACTOR"] = erg["name"]

    KONFIG.write_text(json.dumps(konf, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    os.chmod(KONFIG, 0o600)

    print(f"angemeldet als '{erg['name']}' (bedient von {erg['bedient_von']})")
    print(f"rollen: {', '.join(erg['rollen'])}")
    print(f"geheimnis gesetzt: {len(geheimnis)} Zeichen, nicht ausgegeben")
    print(f"sicherung: {sicherung}")
    print("wirksam, sobald der Klient den Wissensserver neu startet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
