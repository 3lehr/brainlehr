#!/usr/bin/env python3
"""Eine zweite, gefahrlose Instanz des Wissensservers einrichten.

ANLASS (Betreiberfrage 2026-08-11): "warum testest du nicht auf einer zweiten
instanz? waere auch ungefaehrlicher". Zu Recht -- bis heute lief jede Probe
gegen denselben Server und dieselbe Datenbank, mit der auch gearbeitet wird.
Dass dabei nichts passiert ist, war Sorgfalt, nicht Bauart.

WAS DIE PROBE-INSTANZ TRENNT UND WAS NICHT -- der Unterschied entscheidet,
wofuer sie taugt:

  GETRENNT    die Datenbank (BEGOD_KNOWLEDGE_DB). Schreibversuche, Migrationen,
              Trigger, kaputte Daten, Loeschungen -- nichts davon beruehrt den
              Bestand. Auch die Ausweise (BRAINLEHR_AUSWEISE), sonst braeuchte
              die Probe das echte Geheimnis.
  GETEILT     der Quelltext. Beide Instanzen laden dieselben .py-Dateien.
              Eine CODE-Aenderung wirkt daher erst, wenn der jeweilige Prozess
              neu startet -- und genau das ist der Gewinn: die Probe darf man
              jederzeit neu starten, weil niemand an ihr haengt.

DAMIT IST AUCH DIE ANDERE FRAGE BEANTWORTET ("wie bekommen wir sowas im
Livebetrieb eingespielt?"), und die Antwort ist zweigeteilt:

  SCHEMA UND DATEN gehen live, ohne Neustart. Bewiesen am 2026-08-11: Die
      Spalte `bedient_von` samt Trigger war in der laufenden Datenbank, bevor
      irgendjemand etwas neu gestartet hatte -- kern/schema_nachzug.py zieht
      beim naechsten Aufruf selbsttaetig nach.
  PYTHON-CODE geht NICHT live. Ein laufender Prozess haelt seine Module im
      Speicher; importlib.reload waere ein Trugschluss, weil bereits gebundene
      Referenzen (Werkzeugtabelle, offene Verbindungen) auf die alten Objekte
      zeigen. Der MCP-Server ist ein stdio-Prozess des Klienten: neu verbinden
      oder neue Sitzung, und er laeuft mit dem neuen Code. Er haelt keinen
      Zustand ausser der Datenbank -- deshalb kostet der Neustart nichts.

Aufruf:  python3 pflege/probeinstanz.py [--neu]
         --neu wirft eine vorhandene Probe-Datenbank weg und legt sie frisch an
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent

NAME = "knowledge-probe"
HEIMAT = Path.home() / ".brainlehr-probe"
KONFIG = Path.home() / ".claude.json"


def einrichten(neu: bool = False) -> dict:
    HEIMAT.mkdir(parents=True, exist_ok=True)
    db = HEIMAT / "knowledge.db"
    ausweise = HEIMAT / "ausweise.json"

    if neu and db.exists():
        db.unlink()

    frisch = not db.exists()
    if frisch:
        # Aus schema.sql, nicht als Kopie des Bestands: eine Kopie brächte
        # echte Inhalte in eine Umgebung, in der absichtlich Kaputtes probiert
        # wird -- und verwischt genau die Trennung, für die sie da ist.
        conn = sqlite3.connect(str(db))
        try:
            conn.executescript((_w / "schema.sql").read_text(encoding="utf-8"))
            conn.commit()
        finally:
            conn.close()

    eintrag = {
        "command": sys.executable,
        "args": [str(_w / "knowledge_mcp_server.py")],
        "env": {
            "BEGOD_KNOWLEDGE_DB": str(db),
            "BRAINLEHR_AUSWEISE": str(ausweise),
            # Kein BRAINLEHR_GEHEIMNIS: die Probe schreibt unbeglaubigt, bis
            # sie einen eigenen Gruendungsakt bekommt. Das echte Geheimnis hat
            # in einer Wegwerf-Umgebung nichts verloren.
            "BEGOD_KNOWLEDGE_ACTOR": "probe",
        },
    }

    if not KONFIG.exists():
        return {"fehler": f"{KONFIG} fehlt", "db": str(db)}

    sicherung = KONFIG.with_suffix(
        f".json.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(KONFIG, sicherung)

    konf = json.loads(KONFIG.read_text(encoding="utf-8"))
    server = konf.setdefault("mcpServers", {})
    vorher = NAME in server
    server[NAME] = eintrag
    KONFIG.write_text(json.dumps(konf, indent=2, ensure_ascii=False), encoding="utf-8")
    os.chmod(KONFIG, 0o600)

    return {"name": NAME, "db": str(db), "frisch": frisch,
            "eintrag_ersetzt": vorher, "sicherung": str(sicherung)}


def main() -> int:
    erg = einrichten(neu="--neu" in sys.argv)
    if "fehler" in erg:
        print(erg["fehler"], file=sys.stderr)
        return 1
    print(f"Probe-Instanz '{erg['name']}' eingerichtet")
    print(f"  Datenbank : {erg['db']} ({'frisch angelegt' if erg['frisch'] else 'bestand schon'})")
    print(f"  Ausweise  : {HEIMAT / 'ausweise.json'} (eigener Bestand)")
    print(f"  Eintrag   : {'ersetzt' if erg['eintrag_ersetzt'] else 'neu'} in ~/.claude.json")
    print(f"  Sicherung : {erg['sicherung']}")
    print()
    print("Sichtbar wird sie, sobald der Klient die Serverliste neu liest")
    print("(neue Sitzung). Danach steht neben 'knowledge' auch 'knowledge-probe'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
