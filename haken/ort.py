"""Wo liegt brainlehr — ein Ort, an dem das entschieden wird.

Bis zum 2026-08-08 stand der Pfad in jeder Datei einzeln, absolut und
ausgeschrieben. L-6c6661 hat das gemessen: BEGOD_KNOWLEDGE_DB wurde nur von
einem Teil der Skripte geachtet (3 ja, 3 nein) — was schlimmer ist als gar
keine Variable, weil es Sicherheit vortaeuscht. Wer sie setzte und dachte,
er arbeite auf einer Testkopie, schrieb in Wahrheit in den Betrieb.

Hier gilt: die Wurzel ist der Ordner ueber diesem, und BEGOD_KNOWLEDGE_DB
sticht sie fuer die Datenbank. Kein zweiter Kandidat, keine Ratekette.
"""
from __future__ import annotations

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

import os
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent

DB = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (WURZEL / "knowledge.db"))
SERVER = WURZEL / "knowledge_mcp_server.py"
REGISTER = WURZEL / "auftraege.jsonl"
RECALL_LOG = WURZEL / "recall_log.jsonl"
SCHATTEN_LOG = WURZEL / "schatten_log.jsonl"

# Die Verbundwurzel (hub/, fahrtenbuch/, openlehr/ ... nebeneinander). Seit
# brainlehr NEBEN hub liegt statt darin, ist sie aus dem eigenen Ort nicht
# durch blosses Hochzaehlen ableitbar: ein Arbeitsbaum liegt drei Ebenen
# tiefer, und "zwei nach oben" landete dann in .claude/.
#
# Bis 2026-08-10 stand hier deshalb der absolute Pfad EINES Rechners. Das war
# fuer den Betrieb richtig und fuer ein weitergebbares Repo falsch: wer es
# klont, bekommt einen Pfad, den es bei ihm nicht gibt -- und weil nichts
# fehlschlaegt, sondern nur nichts gefunden wird, merkt er es spaet.
#
# Jetzt am MERKMAL gesucht statt am Namen, dieselbe Idee wie die Repo-Wurzel
# an schema.sql weiter oben: nach oben, bis ein Verzeichnis gefunden ist, das
# hub/ enthaelt. BEGOD_VERBUND sticht das, wo die Ableitung nicht greift.
def _verbundwurzel() -> Path:
    gesetzt = os.environ.get("BEGOD_VERBUND")
    if gesetzt:
        return Path(gesetzt)
    p = WURZEL
    while p != p.parent:
        if (p / "hub").is_dir():
            return p
        p = p.parent
    # Kein Verbund gefunden -- eine Einzelinstallation. Der Ordner ueber dem
    # Repo ist die ehrlichste Annahme; wer mehr braucht, setzt BEGOD_VERBUND.
    return WURZEL.parent


VERBUND = _verbundwurzel()
