#!/usr/bin/env python3
"""Zieht die Spalten-Vorgabewerte der INSTALLIERTEN Datenbank auf UTC nach.

Aufgabe 111 Schritt 2, docs/PLAN_UTC_2026-08-14.md.

DIE LUECKE, die dieses Skript schliesst, ist acht Tage alt: Am 2026-08-06
wurde beschlossen "innen UTC, aussen Ortszeit", und schema.sql wurde auf
strftime('%Y-%m-%dT%H:%M:%SZ','now') gesetzt. Die installierte Datenbank
behielt ihren alten Vorgabewert -- strftime('%Y-%m-%dT%H:%M:%S+01:00','now',
'localtime') -- weil ein Vorgabewert in SQLite nur ueber einen Tabellenneubau
zu aendern ist und niemand ihn angefasst hat.

WAS DAS ANRICHTET: Der Wert ist die abgelesene Wanduhr, das Anhaengsel ist
konstant. In der Sommerzeit ist die Angabe damit als Zeitpunkt eine Stunde zu
spaet. Betroffen ist JEDER Schreibvorgang, der die Spalte nicht selbst setzt.

Fuenf Spalten in drei Tabellen, gemessen 2026-08-14:
    knowledge_nodes.created_at, .updated_at
    lessons_learned.first_seen, .last_seen
    access_log.timestamp

BAUFORM wie migrationen/lauf_widerrufsarchiv_schluessel_2026-08-14.py: neue
Tabelle, Daten uebernehmen, GEGENZAEHLEN, erst dann die alte wegwerfen. Die
Gegenzaehlung steht vor dem DROP -- danach ist sie nicht mehr moeglich.

DER FEHLER, DEN DIESES SKRIPT BEIM ERSTEN LAUF GEMACHT HAT, und warum er hier
steht statt stillschweigend behoben zu sein: `DROP TABLE` nimmt in SQLite ALLE
Indizes und Trigger der Tabelle mit. Der erste Lauf am 2026-08-14 hat damit 52
von 96 Schemaobjekten geloescht -- 7 Indizes und 45 Trigger, darunter jede
einzelne Norm- und Herkunftsschranke. Die Daten blieben unversehrt, die
Zusicherungen darueber waren weg.

Aufgefallen ist es sofort, aber NICHT durch dieses Skript: melder/schemastand.py
meldete beim naechsten Aufruf "49 in schema.sql, aber NICHT installiert". Ohne
diesen Melder waere eine Datenbank ohne Trigger zurueckgeblieben, die sich
voellig normal verhaelt -- bis zum ersten Schreibvorgang, den eigentlich eine
Schranke haette abweisen muessen. Der Melder aus Aufgabe 96 hat sich damit
zweimal an einem Tag bezahlt gemacht, beide Male an einem Fehler, den er nicht
kennen konnte.

Das Skript sichert Indizes und Trigger jetzt selbst und legt sie danach wieder
an. Drei der wiederhergestellten Trigger stehen ueberhaupt nicht in schema.sql
(knowledge_nodes_herkunft_bu, knowledge_nodes_norm_entschieden_belegart_
pflicht_bi, lessons_herkunft_bu) -- wer sie aus schema.sql neu erzeugen wollte,
haette sie endgueltig verloren.

WAS DIESES SKRIPT NICHT TUT: die vorhandenen Werte umrechnen. Das ist Schritt
3 und laeuft getrennt, weil die Reihenfolge bindend ist -- wer den Bestand vor
den Erzeugern umrechnet, rechnet gegen laufende Schreiber.
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

ALT = "strftime('%Y-%m-%dT%H:%M:%S+01:00', 'now', 'localtime')"
NEU = "strftime('%Y-%m-%dT%H:%M:%SZ', 'now')"

BETROFFEN = ("knowledge_nodes", "lessons_learned", "access_log")


def _neubau_sql(alte_sql: str, tabelle: str) -> str:
    """Dieselbe Tabelle, nur mit UTC-Vorgabewert -- aus dem INSTALLIERTEN SQL
    abgeleitet, nicht aus schema.sql abgeschrieben.

    Der Unterschied ist wesentlich: die installierte Tabelle traegt Spalten,
    die schema.sql erst seit heute kennt (siehe Aufgabe 110), und sie traegt
    sie in ihrer eigenen Reihenfolge. Wer hier schema.sql nimmt, baut eine
    Tabelle, in die der Bestand nicht mehr passt.
    """
    neu = alte_sql.replace(ALT, NEU)
    # Auch die Schreibweise ohne Leerzeichen nach dem Komma abdecken -- SQLite
    # gibt zurueck, was einmal eingegeben wurde, und das war nicht ueberall
    # gleich formatiert.
    neu = re.sub(r"strftime\('%Y-%m-%dT%H:%M:%S\+01:00',\s*'now',\s*'localtime'\)", NEU, neu)
    return re.sub(r"CREATE TABLE\s+(\"?)" + tabelle + r"\1",
                  f"CREATE TABLE {tabelle}_neu", neu, count=1)


def main() -> int:
    geaendert = []
    with speicher.schreiben() as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        for tabelle in BETROFFEN:
            zeile = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name = ?", (tabelle,)
            ).fetchone()
            if not zeile:
                print(f"{tabelle}: nicht vorhanden, uebersprungen")
                continue
            if ALT not in zeile[0] and "'localtime'" not in zeile[0]:
                print(f"{tabelle}: traegt bereits einen UTC-Vorgabewert, nichts zu tun")
                continue

            spalten = [r[1] for r in conn.execute(f"PRAGMA table_info({tabelle})")]
            liste = ", ".join(f'"{s}"' for s in spalten)
            vorher = conn.execute(f"SELECT COUNT(*) FROM {tabelle}").fetchone()[0]

            conn.executescript(_neubau_sql(zeile[0], tabelle))
            conn.execute(f"INSERT INTO {tabelle}_neu ({liste}) SELECT {liste} FROM {tabelle}")
            nachher = conn.execute(f"SELECT COUNT(*) FROM {tabelle}_neu").fetchone()[0]
            # VOR dem Wegwerfen der Quelle. Danach ist die Gegenprobe nicht
            # mehr moeglich, und ein Skript, das erst hinterher zaehlt, zaehlt
            # nur noch sein eigenes Ergebnis.
            assert nachher == vorher, (
                f"{tabelle}: uebernommen {nachher}, erwartet {vorher} -- nichts geloescht")

            # Indizes und Trigger DIESER Tabelle sichern, BEVOR sie
            # faellt -- DROP TABLE nimmt sie mit. Aus sqlite_master, nicht aus
            # schema.sql: drei Trigger im Bestand stehen dort gar nicht.
            anhaengsel = [r[0] for r in conn.execute(
                "SELECT sql FROM sqlite_master WHERE tbl_name = ? AND type IN "
                "('index','trigger') AND sql IS NOT NULL", (tabelle,))]

            conn.execute(f"DROP TABLE {tabelle}")
            conn.execute(f"ALTER TABLE {tabelle}_neu RENAME TO {tabelle}")

            for sql in anhaengsel:
                conn.execute(sql)
            zurueck = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE tbl_name = ? AND type IN "
                "('index','trigger') AND sql IS NOT NULL", (tabelle,)).fetchone()[0]
            assert zurueck == len(anhaengsel), (
                f"{tabelle}: {zurueck} von {len(anhaengsel)} Indizes/Triggern zurueck "
                "-- Schranken fehlen, Datenbank NICHT benutzen")
            geaendert.append((tabelle, vorher))
            print(f"{tabelle}: Vorgabewert auf UTC, {vorher} Zeilen und "
                  f"{len(anhaengsel)} Indizes/Trigger uebernommen")
        conn.execute("PRAGMA foreign_keys = ON")

    if not geaendert:
        print("nichts geaendert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
