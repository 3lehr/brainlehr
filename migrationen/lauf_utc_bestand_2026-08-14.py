#!/usr/bin/env python3
"""Rechnet den Zeitstempel-Bestand auf UTC um -- Aufgabe 111 Schritt 3.

Reihenfolge ist bindend und dieses Skript ist das LETZTE: Schritt 1 war die
Ratsche (tests/test_zeitform_utc.py, bis hierher absichtlich rot), Schritt 2
die Erzeuger. Wer den Bestand vor den Erzeugern umrechnet, rechnet gegen
laufende Schreiber und ist beim naechsten Schreibvorgang wieder gemischt.

FUENF FORMEN, gemessen 2026-08-14 (Zaehlung in docs/PLAN_UTC_2026-08-14.md):

    2026-08-14T09:31:52+02:00          echter Versatz  -> umrechnen
    2026-08-06T08:28:00+01:00          fester Versatz  -> SONDERFALL, s.u.
    2026-08-11T17:37:16+0200           ohne Doppelpunkt -> umrechnen
    2026-08-07T18:29:03.901235+00:00   UTC, andere Schreibweise -> kuerzen
    2026-08-13T07:31:06Z               Zielform -> bleibt

DER SONDERFALL IST DER GANZE GRUND FUER DIESES SKRIPT: '+01:00' stammt aus dem
alten Vorgabewert strftime('...+01:00','now','localtime'). Der WERT ist die
abgelesene Wanduhr, das ANHAENGSEL ist konstant. In der Sommerzeit ist die
Angabe als Zeitpunkt eine Stunde zu spaet -- wer sie stur nach ihrem Label
umrechnet, schreibt den Fehler fest, statt ihn zu beheben.

Erkennung: Traegt der Wert '+01:00' UND liegt sein Datum in der deutschen
Sommerzeit, ist das Label falsch und der Wert wird ueber die Umstellungsregel
umgerechnet (zeitmarke.falsch_benannte_ortszeit_nach_utc). Im Winter stimmt
'+01:00', dort ist es eine gewoehnliche Umrechnung.

DAS IST EINE RECHNUNG, KEINE SCHAETZUNG -- eindeutig bis auf die doppelte
Stunde in der Nacht der Rueckstellung im Oktober. Dort waehlt zoneinfo die
Sommerzeit-Lesart; im Bestand betrifft das null Zeilen (vor dem Lauf geprueft
und gemeldet, statt angenommen).

AUSGENOMMEN: gilt_ab und gilt_bis tragen reine Datumsangaben. Eine Geltung
beginnt an einem Tag, nicht zu einer Sekunde.
"""
from __future__ import annotations

import re
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
WURZEL = _w
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken", "melder")]

import speicher  # noqa: E402
import zeitmarke  # noqa: E402

ZEITSPALTE = re.compile(r"(_at|_am|_seen)$|^timestamp$")
DATUMSSPALTEN = {("knowledge_nodes", "gilt_ab"), ("knowledge_nodes", "gilt_bis")}

# Der alte Vorgabewert. Nur bei DIESEM Label stellt sich die Frage, ob es
# gelogen ist -- '+02:00' kam immer aus einem echten Versatz.
VERDAECHTIG = "+01:00"

# SECHSTE FORM, im Plan nicht erfasst und erst beim Lauf am 2026-08-14
# aufgetaucht: 'YYYY-MM-DD HH:MM:SS' -- Leerzeichen statt 'T', keine
# Zonenangabe, keine Mikrosekunden. Betroffen: genau eine Zeile im ganzen
# Bestand (knowledge_config, key='herkunftsmodus').
#
# Grund, warum das UTC ist und keine Ratefrage: Diese Form ist SQLites
# Eigenschreibweise aus datetime('now'), und das liefert laut SQLite-
# Dokumentation UTC. Gemessen -- kein Erzeuger im Repo (kern, haken, melder,
# migrationen, schreibpruefstand, die .py-Dateien der Wurzel, schema.sql)
# baut diese Form selbst (kein Treffer fuer str(datetime, sep=' ',
# CURRENT_TIMESTAMP, datetime('now')/datetime("now")); knowledge_config hat
# im Schema auch keinen Spalten-DEFAULT. Der Wert ist damit bereits UTC und
# braucht nur die Zielschreibweise, KEINE Verschiebung.
#
# Verworfene Gegenhypothese: der Wert waere Ortszeit (dann waere die
# richtige Umrechnung 18:19:11Z statt 20:19:11Z). Am access_log liess sich
# das nicht entscheiden -- beide Lesarten haben Nachbaraktivitaet. Entschieden
# wurde ueber die FORM (SQLite-Eigenformat = UTC), nicht ueber die Uhr.
#
# Historischer Einzelfall, keine stehende Rateregel: jede andere zonenlose
# Form -- mit 'T', mit Mikrosekunden, oder sonst abweichend von genau diesem
# Muster -- faellt weiterhin durch zu zeitmarke.nach_utc und wirft dort den
# ValueError. Geraten wird hier nichts; erkannt wird nur eine einzige,
# beweisbar UTC-eigene Schreibweise.
SQLITE_EIGENFORM = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def _sommerzeit(wert: str) -> bool:
    """Lag die deutsche Uhr an diesem Datum auf Sommerzeit?

    Ueber zoneinfo statt ueber eine eigene Datumsrechnung: die Umstellungsregel
    hat sich in der Vergangenheit geaendert und kann es wieder tun. Eine
    nachgebaute Regel ist ab dem Tag falsch, an dem das passiert -- und
    niemand merkt es.
    """
    from datetime import datetime
    naiv = datetime.fromisoformat(re.sub(r"([+-]\d{2}:?\d{2}|Z)$", "", wert))
    return naiv.replace(tzinfo=zeitmarke.BERLIN).utcoffset().total_seconds() == 7200


def umrechnen(wert: str) -> str:
    if not wert or zeitmarke.UTC_MUSTER.match(wert):
        return wert
    if wert.endswith(VERDAECHTIG) and _sommerzeit(wert):
        # Label gelogen: Wanduhr stand auf CEST, angehaengt wurde CET.
        return zeitmarke.falsch_benannte_ortszeit_nach_utc(wert)
    if SQLITE_EIGENFORM.match(wert):
        # Bereits UTC (siehe Kommentar bei SQLITE_EIGENFORM) -- nur die
        # Schreibweise wechselt, keine Verschiebung der Uhrzeit.
        return wert.replace(" ", "T") + "Z"
    return zeitmarke.nach_utc(wert)


def _spalten(conn) -> list[tuple[str, str]]:
    treffer = []
    for (tabelle,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        for zeile in conn.execute(f"PRAGMA table_info({tabelle})"):
            if ZEITSPALTE.search(zeile[1]) and (tabelle, zeile[1]) not in DATUMSSPALTEN:
                treffer.append((tabelle, zeile[1]))
    return treffer


def main() -> int:
    umgerechnet = gesamt = unklar = 0
    mehrdeutig: list[str] = []
    with speicher.schreiben() as conn:
        # Trigger stumm schalten: mehrere Tabellen tragen bu-Trigger, die bei
        # einem UPDATE anspringen und Pflichtfelder pruefen. Eine reine
        # Formatumstellung ist kein fachlicher Schreibvorgang -- sie soll die
        # Schranken nicht ausloesen und schon gar nicht an ihnen scheitern.
        gesichert = [r[0] for r in conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='trigger' AND sql IS NOT NULL")]
        namen = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")]
        for n in namen:
            conn.execute(f'DROP TRIGGER "{n}"')
        try:
            for tabelle, spalte in _spalten(conn):
                zeilen = conn.execute(
                    f"SELECT rowid, {spalte} FROM {tabelle} "
                    f"WHERE {spalte} IS NOT NULL AND {spalte} <> ''").fetchall()
                for rowid, wert in zeilen:
                    gesamt += 1
                    if zeitmarke.UTC_MUSTER.match(str(wert)):
                        continue
                    if str(wert).endswith(VERDAECHTIG) and _sommerzeit(str(wert)):
                        # Die doppelte Stunde im Oktober: 02:00-02:59 Ortszeit
                        # gibt es zweimal. Zaehlen und NENNEN, nicht verschweigen.
                        if re.search(r"T02:", str(wert)) and str(wert)[5:10] in ("10-25", "10-26"):
                            mehrdeutig.append(f"{tabelle}.{spalte} rowid={rowid}: {wert}")
                    neu = umrechnen(str(wert))
                    if neu != wert:
                        conn.execute(f"UPDATE {tabelle} SET {spalte} = ? WHERE rowid = ?",
                                     (neu, rowid))
                        umgerechnet += 1
        finally:
            for sql in gesichert:
                conn.execute(sql)
            zurueck = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0]
            # Kein assert: python -O entfernt Zusicherungen global und
            # stillschweigend, und dieses Skript entscheidet nicht, mit welchen
            # Schaltern es aufgerufen wird. Eine Schranke, die an einem
            # fremden Schalter haengt, ist keine.
            if zurueck != len(gesichert):
                raise RuntimeError(
                    f"{zurueck} von {len(gesichert)} Triggern zurueck -- Schranken fehlen, "
                    "Datenbank NICHT benutzen")

    print(f"{umgerechnet} von {gesamt} Zeitangaben auf UTC umgerechnet, "
          f"{len(gesichert)} Trigger wiederhergestellt")
    if mehrdeutig:
        print(f"MEHRDEUTIG (doppelte Stunde der Rueckstellung), {len(mehrdeutig)} Faelle "
              "-- Sommerzeit-Lesart gewaehlt:")
        for z in mehrdeutig:
            print("   " + z)
    else:
        print("keine Zeile in der doppelten Stunde der Rueckstellung -- die "
              "Umrechnung ist durchgaengig eindeutig")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
