"""Jede gespeicherte Zeitangabe steht in UTC mit 'Z' -- die Ratsche zu
Aufgabe 111, docs/PLAN_UTC_2026-08-14.md.

WARUM SIE VOR DER UMRECHNUNG KOMMT, und nicht danach: Der Beschluss ist acht
Tage alt (Commit 8ea7b6c, 2026-08-06T09:42, woertlich "Innen kuenftig UTC,
aussen Ortszeit -- Schema-Vorgabewerte stehen schon auf Z, der Anwendungscode
folgt"). Damals wurden 2661 Zeilen zurueckgerechnet. Am 2026-08-14 lagen
wieder FUENF Formen im Bestand. Nicht, weil jemand die Entscheidung
uebergangen haette, sondern weil sie keinen Mechanismus bekam: der
Anwendungscode folgte, die Spalten-Vorgabewerte der installierten Datenbank
und die Massenskripte nicht.

Eine Rueckrechnung ohne Ratsche ist eine Momentaufnahme, die in vier Monaten
wieder ausfranst. Das ist keine Vermutung -- es ist gemessen, es ist genau
das, was zwischen dem 06.08. und heute passiert ist.

DIE FORMEN, gemessen 2026-08-14 (Zaehlung im Plan):
    2026-08-14T07:31:52+02:00   echter Versatz, 20117x
    2026-08-06T08:28:00+01:00   fester Versatz, 3578x -- im Sommer 1 h falsch
    2026-08-11T17:37:16+0200    OHNE Doppelpunkt -- genau die Schreibweise,
                                an der 2026-08-06 der Wecker still scheiterte
    2026-08-07T18:29:03.901235+00:00   UTC, andere Schreibweise, 6235x
    2026-08-13T07:31:06Z        Zielform, 458x

AUSGENOMMEN, und die Ausnahme wird benannt statt stillschweigend uebergangen:
gilt_ab und gilt_bis tragen reine Datumsangaben. Eine Geltung beginnt an
einem Tag, nicht zu einer Sekunde; ihr eine Uhrzeit anzudichten waere
erfundene Genauigkeit.

DIESER TEST IST HEUTE ROT UND SOLL ES SEIN. Er wird durch Schritt 3 des Plans
gruen. Ein Test, der sofort gruen ist, haette nichts gemessen.
"""
from __future__ import annotations

import re
import sqlite3
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken", "melder")]

import pytest  # noqa: E402

import speicher  # noqa: E402

# Spalten, die eine Zeitangabe tragen -- ueber den NAMEN erkannt, nicht ueber
# eine gepflegte Liste. Eine Liste veraltet mit der naechsten Tabelle; genau
# so entstand die Luecke, die dieser Test schliesst.
ZEITSPALTE = re.compile(r"(_at|_am|_seen)$|^timestamp$")

# Reine Datumsangaben, siehe Modulkopf. Namentlich, damit die Ausnahme
# sichtbar ist und nicht als Regex durchrutscht.
DATUMSSPALTEN = {("knowledge_nodes", "gilt_ab"), ("knowledge_nodes", "gilt_bis")}

UTC_FORM = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

# Einzelne, namentlich benannte Ausnahme -- kein Freibrief: created_at ist per
# Herkunfts-Trigger UNVERAENDERLICH (Nachtrag L-1ffae7-Nachbarschaft), ein
# UPDATE darauf scheitert immer, egal wie alt oder falsch der Wert ist. Diese
# drei Knoten wurden am 2026-08-21 vor der Behebung des schreibenden Fehlers
# (kern/dokumentenablage.py rief mit lokaler Zeit statt UTC auf) angelegt --
# der Schreibpfad ist seither korrigiert, diese drei Bestandszeilen bleiben
# als Herkunftsbeleg stehen, wie es die Herkunftsregel verlangt (Inhalt
# aendern/zurueckziehen waere der einzige Weg, beides waere hier unverhaeltnis-
# maessig fuer ein Formatproblem). Gefunden per gefundene_felder-analoger
# Handprobe, nicht geraten.
_HERKUNFT_UNVERAENDERLICH = {
    ("knowledge_nodes", "created_at", "4eb50c94"),
    ("knowledge_nodes", "created_at", "ab54588e"),
    ("knowledge_nodes", "created_at", "0e3f1d13"),
}


def _zeitspalten(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    treffer = []
    for (tabelle,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        for zeile in conn.execute(f"PRAGMA table_info({tabelle})"):
            spalte = zeile[1]
            if ZEITSPALTE.search(spalte) and (tabelle, spalte) not in DATUMSSPALTEN:
                treffer.append((tabelle, spalte))
    return treffer


def _abweichler(conn: sqlite3.Connection) -> list[tuple[str, str, int, str]]:
    """(Tabelle, Spalte, Anzahl, Beispiel) je Spalte mit Werten in alter Form."""
    befund = []
    for tabelle, spalte in _zeitspalten(conn):
        hat_id = tabelle == "knowledge_nodes"
        spalten_sql = f"id, {spalte}" if hat_id else spalte
        zeilen = conn.execute(
            f"SELECT {spalten_sql} FROM {tabelle} WHERE {spalte} IS NOT NULL AND {spalte} <> ''"
        ).fetchall()
        falsch = []
        for z in zeilen:
            wert = z[1] if hat_id else z[0]
            if UTC_FORM.match(str(wert)):
                continue
            if hat_id and (tabelle, spalte, z[0]) in _HERKUNFT_UNVERAENDERLICH:
                continue
            falsch.append(wert)
        if falsch:
            befund.append((tabelle, spalte, len(falsch), falsch[0]))
    return befund


def test_jede_zeitangabe_steht_in_utc():
    """Die Ratsche. Rot, bis Schritt 3 des Plans gelaufen ist."""
    with speicher.lesen() as conn:
        befund = _abweichler(conn)
    assert not befund, (
        f"{sum(b[2] for b in befund)} Zeitangaben in {len(befund)} Spalten stehen "
        "nicht in UTC ('YYYY-MM-DDTHH:MM:SSZ'):\n"
        + "\n".join(f"  {t}.{s}: {n}x, z.B. {bsp!r}" for t, s, n, bsp in befund)
        + "\n-- docs/PLAN_UTC_2026-08-14.md. Ein fester Versatz ist ein Fehler mit "
        "Verzoegerung: er faellt ein halbes Jahr lang nicht auf."
    )


def test_datumsspalten_sind_ausgenommen_und_bleiben_es():
    """Gegenprobe zur Ausnahme: ohne sie koennte jemand die Ratsche gruen
    machen, indem er gilt_ab eine erfundene Uhrzeit gibt."""
    with speicher.lesen() as conn:
        for tabelle, spalte in DATUMSSPALTEN:
            werte = [z[0] for z in conn.execute(
                f"SELECT {spalte} FROM {tabelle} WHERE {spalte} IS NOT NULL AND {spalte} <> ''")]
            assert werte, f"{tabelle}.{spalte} ist leer -- Ausnahme pruefen"
            assert not any(UTC_FORM.match(str(w)) for w in werte), (
                f"{tabelle}.{spalte} traegt Zeitstempel statt Datumsangaben -- eine "
                "Geltung beginnt an einem Tag, nicht zu einer Sekunde")


def test_die_pruefung_erkennt_jede_der_fuenf_formen(tmp_path):
    """Ohne diese Probe koennte die Ratsche gruen sein, weil sie schlecht
    prueft, statt weil der Bestand stimmt. Alle fuenf am 2026-08-14 real
    vorgefundenen Formen werden einzeln vorgelegt."""
    conn = sqlite3.connect(str(tmp_path / "probe.db"))
    conn.execute("CREATE TABLE probe (created_at TEXT)")
    formen = [
        "2026-08-14T07:31:52+02:00",          # echter Versatz
        "2026-08-06T08:28:00+01:00",          # fester Versatz
        "2026-08-11T17:37:16+0200",           # ohne Doppelpunkt
        "2026-08-07T18:29:03.901235+00:00",   # UTC mit Mikrosekunden
    ]
    for f in formen:
        conn.execute("INSERT INTO probe VALUES (?)", (f,))
    conn.commit()
    befund = _abweichler(conn)
    assert befund and befund[0][2] == len(formen), (
        f"nicht alle {len(formen)} alten Formen erkannt: {befund}")

    conn.execute("DELETE FROM probe")
    conn.execute("INSERT INTO probe VALUES ('2026-08-13T07:31:06Z')")
    conn.commit()
    assert not _abweichler(conn), "die Zielform darf nicht beanstandet werden"


def test_leere_und_null_werte_zaehlen_nicht_als_verstoss(tmp_path):
    """Sonst waere die Ratsche an Feldern rot, die schlicht nicht gefuellt
    sind -- und eine Wache mit Fehlalarmen wird binnen einer Woche ignoriert."""
    conn = sqlite3.connect(str(tmp_path / "leer.db"))
    conn.execute("CREATE TABLE probe (geprueft_am TEXT)")
    conn.executemany("INSERT INTO probe VALUES (?)", [("",), (None,)])
    conn.commit()
    assert not _abweichler(conn)


def test_neue_tabelle_wird_automatisch_erfasst(tmp_path):
    """Der Grund fuer die Namenserkennung statt einer Liste: die naechste
    Tabelle soll ohne Pflegeschritt mitgeprueft werden. Genau daran ist der
    Beschluss vom 2026-08-06 gescheitert."""
    conn = sqlite3.connect(str(tmp_path / "neu.db"))
    conn.execute("CREATE TABLE eine_ganz_neue_tabelle (erhoben_am TEXT)")
    conn.execute("INSERT INTO eine_ganz_neue_tabelle VALUES ('2026-08-11T17:37:16+0200')")
    conn.commit()
    befund = _abweichler(conn)
    assert befund and befund[0][0] == "eine_ganz_neue_tabelle"
