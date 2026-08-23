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

Dieselbe Uebergangsform gilt fuer den Dateinamen ohne gesetzte Variable:
knowledge.db hiess die Datei bis 2026-08-11, brainlehr.db ist der neue Name
(zwei Speicher im Verbund hiessen beide knowledge.db und unterschieden sich
nur im Ordner -- eine Fehlerquelle, siehe Auftrag zum Umzug). Existiert
brainlehr.db bereits, wird sie genommen, ohne Hinweis. Sonst faellt dieses
Modul auf knowledge.db zurueck und meldet das einmal pro Prozess auf stderr.
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
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent


def _installiert(wurzel: Path) -> bool:
    """Laeuft brainlehr als INSTALLIERTES Paket statt aus einem Arbeitsbaum?

    Erkannt am Ort, nicht an einer Umgebungsvariablen: Liegt die Wurzel unter
    site-packages oder dist-packages, gehoert sie pip und nicht dem Nutzer."""
    return any(teil in ("site-packages", "dist-packages") for teil in wurzel.parts)


def _nutzerablage() -> Path:
    """~/.brainlehr -- der Ort, an dem der Bestand pip ueberlebt.

    ANLASS, gemessen 2026-08-23 beim ersten Lauf einer FRISCHEN Installation:
    Ohne diesen Zweig landete die Datenbank in
    site-packages/brainlehr_kern/brainlehr.db. Ein `pip install --upgrade`
    oder `pip uninstall` haette damit den gesamten Wissensbestand geloescht --
    lautlos, weil niemand seine Daten dort vermutet.

    Der Ordner ist nicht neu erfunden: ~/.brainlehr/dienst-kennzahlen.json
    liegt schon dort. Es ist bereits die Nutzerablage dieses Hauses, sie war
    nur fuer die Datenbank nie benutzt worden."""
    return Path.home() / ".brainlehr"


def _ermittle_db(wurzel: Path, neu: str | None, alt: str | None) -> Path:
    if neu or alt:
        return Path(neu or alt)
    if _installiert(wurzel):
        # Kein Hinweis auf den alten Dateinamen: Wer frisch installiert, hat
        # nie eine knowledge.db gehabt. Ein Umbenennungshinweis waere dort
        # nicht nur nutzlos, sondern falsch -- er nennt eine Datei, die es
        # nie gab, als erstes, was das Programm ueberhaupt sagt.
        heim = _nutzerablage()
        heim.mkdir(parents=True, exist_ok=True)
        return heim / "brainlehr.db"
    kandidat = wurzel / "brainlehr.db"
    if kandidat.exists():
        return kandidat
    # Der Hinweis nur, wenn die alte Datei WIRKLICH daliegt. Vorher erschien er
    # auch dann, wenn ueberhaupt keine Datenbank existierte -- also genau bei
    # dem Nutzer, der am wenigsten damit anfangen kann.
    if (wurzel / "knowledge.db").exists():
        print(
            "hinweis: knowledge.db ist der alte Dateiname, bitte auf brainlehr.db umbenennen",
            file=sys.stderr,
        )
    return wurzel / "knowledge.db"


_neu = os.environ.get("BRAINLEHR_DB")
_alt = os.environ.get("BEGOD_KNOWLEDGE_DB")
if not _neu and _alt:
    print(
        "hinweis: BEGOD_KNOWLEDGE_DB ist veraltet, bitte BRAINLEHR_DB setzen",
        file=sys.stderr,
    )
DB = _ermittle_db(WURZEL, _neu, _alt)
SERVER = WURZEL / "knowledge_mcp_server.py"
REGISTER = WURZEL / "auftraege.jsonl"
RECALL_LOG = WURZEL / "recall_log.jsonl"
SCHATTEN_LOG = WURZEL / "schatten_log.jsonl"
# Auftrag A3 (docs/PLAN_BETRIEBSPROFILE_2026-08-20.md): schreibt kern/embeddings.py,
# wenn die Aussetzer-Sicherung pausiert (5 Fehler in Folge) -- gelesen von
# melder/einbettungsaussetzer.py beim Sitzungsstart. Denselben Kanal wie
# RECALL_LOG/SCHATTEN_LOG: append-only JSONL neben der DB, kein fest
# verdrahteter Name in den beiden Modulen selbst.
AUSSETZER_LOG = WURZEL / "einbettungsausfaelle.jsonl"

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
