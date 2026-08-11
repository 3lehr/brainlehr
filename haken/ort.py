"""Wo liegt brainlehr — ein Ort, an dem das entschieden wird.

Bis zum 2026-08-08 stand der Pfad in jeder Datei einzeln, absolut und
ausgeschrieben. L-6c6661 hat das gemessen: BEGOD_KNOWLEDGE_DB wurde nur von
einem Teil der Skripte geachtet (3 ja, 3 nein) — was schlimmer ist als gar
keine Variable, weil es Sicherheit vortaeuscht. Wer sie setzte und dachte,
er arbeite auf einer Testkopie, schrieb in Wahrheit in den Betrieb.

Hier gilt: die Wurzel ist der Ordner ueber diesem, und BEGOD_KNOWLEDGE_DB
sticht sie fuer die Datenbank. Kein zweiter Kandidat, keine Ratekette.

Seit 2026-08-11 gibt es zwei Namen. BRAINLEHR_DB ist der neue, massgebliche --
das BEGOD-Praefix stammt aus der Zeit, als dieser Speicher noch unter
hub/shared-knowledge im BEGOD-Verbund lag; brainlehr zog am 2026-08-08 in ein
eigenes Repository und soll auch bei Dritten laufen, die den Verbundnamen nie
gehoert haben. BEGOD_KNOWLEDGE_DB bleibt bewusst bestehen: 52 Stellen setzen
ihn (Doku, Tests, Kommandozeilen), ein hartes Umschalten haette laufende
Sitzungen und fremde Skripte gebrochen. Sind beide gesetzt, gewinnt
BRAINLEHR_DB. Wird nur der alte Name benutzt, meldet dieses Modul das einmal
pro Prozess auf stderr -- ein Hinweis pro Aufruf wuerde nur weggeblendet.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent

_neu = os.environ.get("BRAINLEHR_DB")
_alt = os.environ.get("BEGOD_KNOWLEDGE_DB")
if not _neu and _alt:
    print(
        "hinweis: BEGOD_KNOWLEDGE_DB ist veraltet, bitte BRAINLEHR_DB setzen",
        file=sys.stderr,
    )
DB = Path(_neu or _alt or (WURZEL / "knowledge.db"))
SERVER = WURZEL / "knowledge_mcp_server.py"
REGISTER = WURZEL / "auftraege.jsonl"
RECALL_LOG = WURZEL / "recall_log.jsonl"
SCHATTEN_LOG = WURZEL / "schatten_log.jsonl"

# Die Verbundwurzel (hub/, fahrtenbuch/, openlehr/ ... nebeneinander). Seit
# brainlehr NEBEN hub liegt statt darin, ist sie aus dem eigenen Ort nicht
# mehr ableitbar: ein Arbeitsbaum liegt drei Ebenen tiefer, und "zwei nach
# oben" landete dann in .claude/. Darum absolut -- und nur hier.
VERBUND = Path("/Volumes/daten/Begod2026")
