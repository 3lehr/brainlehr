#!/usr/bin/env python3
"""Meldet neue Schreibvorgaenge in brainlehr (knowledge.db), waehrend anderswo gearbeitet wird.

Abweichung vom Auftrag: lessons_learned hat keine Spalte created_at, nur
first_seen/last_seen -> first_seen wird als Zeitstempel verwendet.
"""

# Liegt eine Ebene unter der Wurzel: die Wurzel muss auf den Suchpfad,
# sonst findet `import knowledge_mcp_server` nichts. Muster aus haken/.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
SHARED_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("BEGOD_KNOWLEDGE_DB", os.path.join(SHARED_DIR, "knowledge.db"))
RECALL_LOG = os.path.join(SHARED_DIR, "recall_log.jsonl")
STAND_PATH = os.path.join(SHARED_DIR, ".neuschreibungen_stand.json")

SCHREIB_AKTIONEN = ("add", "lesson", "update", "lesson_update", "relation_add")


def db_connect():
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5)


def stand_laden():
    if not os.path.exists(STAND_PATH):
        return {"access_log_id": 0, "recall_zeilen": 0, "ts": "1970-01-01T00:00:00+00:00"}
    with open(STAND_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def stand_schreiben(stand):
    with open(STAND_PATH, "w", encoding="utf-8") as f:
        json.dump(stand, f, ensure_ascii=False)


def recall_zeilen_zaehlen():
    if not os.path.exists(RECALL_LOG):
        return 0
    with open(RECALL_LOG, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def projekt_aus_lessons(projects_text):
    """Liefert Projektnamen aus lessons_learned.projects. Kaputtes JSON -> 'unlesbar'."""
    try:
        werte = json.loads(projects_text)
    except json.JSONDecodeError:
        return ["unlesbar"]
    if isinstance(werte, list):
        return [str(w) for w in werte] or ["unbekannt"]
    return [str(werte)]


def projekte_im_fenster(con, seit_ts):
    """Zaehlt Projekt-Nennungen aus Datensaetzen, die seit seit_ts neu sind."""
    zaehler = {}
    for (projects_text,) in con.execute(
        "SELECT projects FROM lessons_learned WHERE first_seen > ?", (seit_ts,)
    ):
        for p in projekt_aus_lessons(projects_text):
            zaehler[p] = zaehler.get(p, 0) + 1
    for (project_id,) in con.execute(
        "SELECT project_id FROM knowledge_nodes WHERE created_at > ?", (seit_ts,)
    ):
        p = project_id or "unbekannt"
        zaehler[p] = zaehler.get(p, 0) + 1
    return zaehler


def pruefen(con, stand, schwelle):
    (letzte_id,) = con.execute(
        "SELECT COALESCE(MAX(id), 0) FROM access_log"
    ).fetchone()
    platzhalter = ",".join("?" * len(SCHREIB_AKTIONEN))
    (neue_schreibvorgaenge,) = con.execute(
        f"SELECT COUNT(*) FROM access_log WHERE id > ? AND action IN ({platzhalter})",
        (stand["access_log_id"], *SCHREIB_AKTIONEN),
    ).fetchone()

    aktuelle_recall_zeilen = recall_zeilen_zaehlen()
    neue_abrufe = max(0, aktuelle_recall_zeilen - stand["recall_zeilen"])

    neuer_stand = {
        "access_log_id": max(letzte_id, stand["access_log_id"]),
        "recall_zeilen": aktuelle_recall_zeilen,
        "ts": datetime.now(BERLIN).isoformat(timespec="seconds"),
    }

    if neue_schreibvorgaenge < schwelle:
        return None, neuer_stand

    zaehler = projekte_im_fenster(con, stand["ts"])
    projekt_teil = ", ".join(f"{p}:{n}" for p, n in sorted(zaehler.items()))
    zeile = f"brainlehr: {neue_schreibvorgaenge} neue Schreibvorgaenge, {neue_abrufe} neue Abrufe [{projekt_teil}]"
    return zeile, neuer_stand


def main():
    ap = argparse.ArgumentParser(description="Meldet neue Schreibvorgaenge in brainlehr")
    ap.add_argument("--schwelle", type=int, default=5)
    ap.add_argument("--wache", action="store_true", help="Dauerlauf statt Einmalpruefung")
    ap.add_argument("--takt", type=int, default=120, help="Sekunden zwischen Pruefungen im Wache-Modus")
    ap.add_argument("--stand-setzen", action="store_true", help="Wasserstand auf jetzt, keine Meldung")
    args = ap.parse_args()

    if args.stand_setzen:
        con = db_connect()
        try:
            (letzte_id,) = con.execute("SELECT COALESCE(MAX(id), 0) FROM access_log").fetchone()
        finally:
            con.close()
        stand_schreiben({
            "access_log_id": letzte_id,
            "recall_zeilen": recall_zeilen_zaehlen(),
            "ts": datetime.now(BERLIN).isoformat(timespec="seconds"),
        })
        return 0

    if args.wache:
        while True:
            stand = stand_laden()
            try:
                con = db_connect()
                try:
                    zeile, neuer_stand = pruefen(con, stand, args.schwelle)
                finally:
                    con.close()
                if zeile:
                    print(zeile, flush=True)
                    stand_schreiben(neuer_stand)
            except sqlite3.Error as e:
                print(f"brainlehr: db-fehler ({e})", flush=True)
            time.sleep(args.takt)

    stand = stand_laden()
    con = db_connect()
    try:
        zeile, neuer_stand = pruefen(con, stand, args.schwelle)
    finally:
        con.close()
    if zeile:
        print(zeile)
        stand_schreiben(neuer_stand)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
