"""Der Nenner entscheidet, ob eine Quote etwas bedeutet.

Aufgabe 108. Die S12-Auswertung vom 2026-08-13T21:28 rechnete ueber ALLE
Zielinstanzen einer Haelfte (101 und 104) und ergab +0,93 Prozentpunkte --
Rauschen. Behandelt wurden aber nur 225 von 1101 gesicherten Knoten; der Rest
sind Normen und Fremdbestand, beide vom Umschriftverfahren ausgenommen. Ein
Effekt an den behandelten Knoten wurde damit mit unberuehrten Zielen
verduennt.

ERGEBNIS DER RICHTIGEN RECHNUNG (2026-08-14, runs/s12_nenner_2026-08-14.json):
Von 205 Zielinstanzen liegen 34 in der vergleichbaren Teilmenge -- 14
behandelte, 20 unbehandelte. Die behandelte Zelle liegt damit unter der
Mindestzahl. Das Urteil lautet "mit diesem Korpus nicht entscheidbar".

DAS IST NICHT DASSELBE WIE "KEINE WIRKUNG", und der Unterschied ist der ganze
Zweck dieser Datei. Die Rohzahlen wuerden 5/14 gegen 11/20 lauten, also
scheinbar SCHLECHTER nach der Behandlung -- eine Quote aus 14 Faellen sieht
nur wie eine Antwort aus. Wer sie meldet, hat eine Zahl ohne Aussage in die
Welt gesetzt; wer sie als Nullergebnis meldet, hat eine Massnahme
faelschlich verworfen. Rund 2 Millionen Token haengen an dieser
Unterscheidung.

SYMMETRIE IST PFLICHT: In der unbehandelten Haelfte gibt es per Definition
keine behandelten Knoten. Verglichen wird deshalb die Teilmenge der
VERGLEICHBAREN Knoten -- arbeitsbestand, keine Norm -- in beiden Haelften
nach derselben Regel. Ohne das misst der Vergleich die Auswahl statt die
Wirkung.
"""
from __future__ import annotations

import sqlite3
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
WURZEL = _w
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "melder", "messungen")]

import pytest  # noqa: E402

import s12_nenner as sn  # noqa: E402


@pytest.fixture()
def db(tmp_path, monkeypatch):
    conn = sqlite3.connect(str(tmp_path / "probe.db"))
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    # Die Schranken des echten Schemas stehen dieser Vorrichtung im Weg -- sie
    # prueft eine reine Mengenoperation, keinen Schreibpfad. Alle bi-Trigger
    # auf knowledge_nodes fallen, statt sie einzeln aufzuzaehlen: eine Liste
    # veraltet mit der naechsten Schranke, und dann faellt die Vorrichtung
    # aus einem Grund aus, der mit ihrem Gegenstand nichts zu tun hat.
    for (name,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' "
            "AND tbl_name='knowledge_nodes' AND name LIKE '%_bi'").fetchall():
        conn.execute(f'DROP TRIGGER "{name}"')
    return conn


def _knoten(conn, node_id, pfad, *, norm=None, gattung="arbeitsbestand"):
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, level, "
        "source, norm_rang, gattung, norm_entscheidung, norm_entschieden_von, "
        "norm_entschieden_grund) VALUES (?,?,'shared','T','S',0,'test',?,?, "
        "'keine_norm','skript:test','Test')",
        (node_id, pfad, norm, gattung))


def _urfassung(conn, node_id, pfad, titel):
    conn.execute(
        "INSERT INTO s12_urfassungen (node_id, path, title, summary, content, gesichert_am) "
        "VALUES (?,?,?,'S',NULL,'2026-08-12T00:00:00Z')", (node_id, pfad, titel))


def test_behandelt_heisst_text_weicht_von_der_urfassung_ab(db):
    """Nicht 'stand auf der Liste', sondern 'ist tatsaechlich anders'. Das
    Umschriftwerkzeug hat sechs Schranken; welche Knoten es am Ende angefasst
    hat, steht nur im Text."""
    _knoten(db, "a1", "/a/1")
    _knoten(db, "a2", "/a/2")
    _urfassung(db, "a1", "/a/1", "ANDERER Titel")   # geaendert
    _urfassung(db, "a2", "/a/2", "T")               # unveraendert
    assert sn.behandelte_knoten(db) == {"a1"}


def test_normen_und_fremdbestand_sind_nicht_vergleichbar(db):
    """Sie kamen fuer eine Behandlung nie in Frage -- dieselben Schranken wie
    im Umschriftwerkzeug. Ohne diese Grenze rechnet der Vergleich Treffer
    gegeneinander, die auf verschiedenen Mengen beruhen."""
    _knoten(db, "n1", "/n/1")
    _knoten(db, "n2", "/n/2", norm=2)
    _knoten(db, "n3", "/n/3", gattung="nachschlagewerk")
    assert sn.vergleichbare_knoten(db) == {"n1"}


def _lauf(einzel):
    return {"einzel": einzel}


def test_zu_kleine_teilmenge_meldet_nicht_entscheidbar_statt_null(db, monkeypatch):
    """DER KERN. Eine Quote aus wenigen Faellen ist keine Antwort. Sie als
    Nullergebnis zu melden, wuerde eine Massnahme faelschlich verwerfen."""
    _knoten(db, "k1", "/k/1")
    _urfassung(db, "k1", "/k/1", "ANDERS")
    monkeypatch.setattr(sn.teilung_s12, "id_je_pfad", lambda conn, pfade: {"/k/1": "k1"})

    erg = sn.auswerten(_lauf([{"art": "knoten", "id": "/k/1", "haelfte": "behandelt",
                               "treffer": True}]), db)
    assert erg["belastbar"] is False
    assert erg["zu_kleine_zellen"]
    assert erg["zellen"]["behandelt"]["gesamt"] == 1


def test_gegenprobe_grosse_teilmenge_wird_gerechnet(db, monkeypatch):
    """Ohne diese Richtung bestuende der Test darueber auch bei einer
    Auswertung, die IMMER 'nicht entscheidbar' sagt -- und die waere
    wertlos."""
    pfade = {}
    einzel = []
    for i in range(sn.MINDESTZAHL):
        for halb in ("behandelt", "unbehandelt"):
            nid, pfad = f"{halb[:1]}{i}", f"/{halb}/{i}"
            _knoten(db, nid, pfad)
            if halb == "behandelt":
                _urfassung(db, nid, pfad, "ANDERS")
            pfade[pfad] = nid
            einzel.append({"art": "knoten", "id": pfad, "haelfte": halb, "treffer": i % 2 == 0})
    monkeypatch.setattr(sn.teilung_s12, "id_je_pfad", lambda conn, p: pfade)

    erg = sn.auswerten(_lauf(einzel), db)
    assert erg["belastbar"] is True
    assert erg["zellen"]["behandelt"]["gesamt"] == sn.MINDESTZAHL
    assert erg["zellen"]["behandelt"]["quote"] is not None


def test_lehren_zaehlen_nicht_mit(db, monkeypatch):
    """Das Umschriftverfahren hat nie eine Lehre angefasst. Sie in einer
    Messung seiner Wirkung mitzuzaehlen, verduennt genau das, was gemessen
    werden soll -- derselbe Fehler wie der urspruengliche Nenner, nur eine
    Ebene tiefer."""
    monkeypatch.setattr(sn.teilung_s12, "id_je_pfad", lambda conn, p: {})
    erg = sn.auswerten(_lauf([{"art": "lehre", "id": "L-1", "haelfte": "behandelt",
                               "treffer": True}]), db)
    assert erg["zellen"]["behandelt"]["gesamt"] == 0
    assert erg["ausserhalb_der_teilmenge"] == 1


def test_unbehandelter_knoten_in_der_behandelten_haelfte_faellt_heraus(db, monkeypatch):
    """Der Grund fuer die ganze Aufgabe: In der behandelten Haelfte liegen
    1097 Knoten, angefasst wurden 225. Die uebrigen sind kein Beleg fuer die
    Wirkung der Umschrift -- in keine Richtung."""
    _knoten(db, "u1", "/u/1")  # vergleichbar, aber ohne Urfassung -> nie behandelt
    monkeypatch.setattr(sn.teilung_s12, "id_je_pfad", lambda conn, p: {"/u/1": "u1"})
    erg = sn.auswerten(_lauf([{"art": "knoten", "id": "/u/1", "haelfte": "behandelt",
                               "treffer": True}]), db)
    assert erg["zellen"]["behandelt"]["gesamt"] == 0
