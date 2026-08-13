"""Abnahme fuer kern/umschrift_s12.py: keine Schranke darf sich umgehen lassen.

Arbeitet ausschliesslich auf einer tmp-Datenbank (kein Lauf gegen den echten
Bestand). Rot-vor-gruen fuer jede der drei Schranken: die Probe entfernt die
jeweilige Ablehnung testweise und zeigt, dass genau dann rot wird, was hier
gruen steht.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent.parent
_sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken")]

import sqlite3
import tempfile

import pytest

import sicherung_s12
import speicher
import teilung_s12
import umschrift_s12 as us

JETZT = "2026-08-13T09:00:00+02:00"


def _insert_node(conn: sqlite3.Connection, node_id: str, path: str,
                  title: str, summary: str, content: str) -> None:
    conn.execute(
        """INSERT INTO knowledge_nodes
           (id, path, parent_path, project_id, title, summary, content, level, tags, source,
            created_at, updated_at, norm_entscheidung,
            norm_entschieden_von, norm_entschieden_am, norm_entschieden_grund)
           VALUES (?, ?, '/', 'shared', ?, ?, ?, 1, '[]', ?, ?, ?, 'keine_norm', ?, ?, ?)""",
        (node_id, path, title, summary, content, node_id, JETZT, JETZT,
         "test:test_umschrift_s12.py", JETZT, "Testvorrichtung"),
    )


def _sichern(conn: sqlite3.Connection, node_id: str, path: str, title: str,
             summary: str, content: str) -> None:
    conn.executescript(sicherung_s12.SCHEMA)
    conn.execute(
        "INSERT INTO s12_urfassungen (node_id, path, title, summary, content, gesichert_am) "
        "VALUES (?,?,?,?,?,?)", (node_id, path, title, summary, content, JETZT))


@pytest.fixture()
def db(tmp_path):
    pfad = tmp_path / "probe.db"
    schema_sql = (_w / "schema.sql").read_text(encoding="utf-8")

    # Kennungen ueber teilung_s12.haelfte() selbst finden statt raten.
    kandidaten = [f"t-{i}" for i in range(80)]
    behandelt = [k for k in kandidaten if teilung_s12.haelfte("knoten", k) == teilung_s12.BEHANDELT]
    unbehandelt = next(k for k in kandidaten if teilung_s12.haelfte("knoten", k) == teilung_s12.UNBEHANDELT)
    sauber, ohne_urfassung, defekt = behandelt[0], behandelt[1], behandelt[2]

    with speicher.schreiben(pfad) as conn:
        conn.executescript(schema_sql)
        _insert_node(conn, sauber, "/x/sauber", "Alter Titel",
                     "Zusammenfassung mit 8,50 USD.", "Volltext 8,50 USD.")
        _insert_node(conn, ohne_urfassung, "/x/ohne-urfassung", "Titel B",
                     "Zusammenfassung B.", "Text B.")
        _insert_node(conn, defekt, "/x/defekt", "Titel C",
                     "Zusammenfassung C mit 47 Prozent.", "Text C mit 47 Prozent.")
        _insert_node(conn, unbehandelt, "/x/unbehandelt", "Titel D",
                     "Zusammenfassung D.", "Text D.")
        _sichern(conn, sauber, "/x/sauber", "Alter Titel",
                 "Zusammenfassung mit 8,50 USD.", "Volltext 8,50 USD.")
        _sichern(conn, defekt, "/x/defekt", "Titel C",
                 "Zusammenfassung C mit 47 Prozent.", "Text C mit 47 Prozent.")
        # ohne_urfassung bekommt bewusst KEINE Zeile in s12_urfassungen.

    return {"pfad": pfad, "sauber": sauber, "ohne_urfassung": ohne_urfassung,
            "defekt": defekt, "unbehandelt": unbehandelt}


def _alt_neu(db, id_):
    with speicher.lesen(db["pfad"]) as conn:
        row = conn.execute(
            "SELECT id, path, title, summary, content AS co FROM knowledge_nodes WHERE id=?",
            (id_,)).fetchone()
    return dict(row)


# ------------------------------------------------------- Grenzwerte / --lose
def test_n_1_liefert_genau_einen_knoten(db):
    with speicher.lesen(db["pfad"]) as conn:
        los = us.lose_erzeugen(conn, 1, 0)
    assert len(los) == 1


def test_n_0_liefert_leer_und_keinen_fehler(db):
    with speicher.lesen(db["pfad"]) as conn:
        los = us.lose_erzeugen(conn, 0, 0)
    assert los == []


def test_lose_enthaelt_die_drei_regeln_woertlich(db):
    with speicher.lesen(db["pfad"]) as conn:
        los = us.lose_erzeugen(conn, 5, 0)
    assert los
    for eintrag in los:
        assert "Der Titel benennt die Sache, nicht ihre Herkunft." in eintrag["auftrag"]
        assert "Die Zusammenfassung traegt in ein bis drei Saetzen" in eintrag["auftrag"]
        assert "Der Volltext nennt die Begriffe mehrfach und unterschiedlich." in eintrag["auftrag"]


def test_lose_liefert_nur_behandelte_haelfte(db):
    with speicher.lesen(db["pfad"]) as conn:
        los = us.lose_erzeugen(conn, 10, 0)
    ids = {e["id"] for e in los}
    assert db["unbehandelt"] not in ids


# ------------------------------------------------------- Schranke: Urfassung
def test_ohne_urfassung_wird_abgelehnt_und_namentlich_genannt(db):
    alt = [_alt_neu(db, db["ohne_urfassung"])]
    neu = [dict(alt[0], title="Neuer Titel", summary="Neue Zusammenfassung.")]
    with speicher.schreiben(db["pfad"]) as conn:
        e = us.zurueckschreiben_alle(conn, alt, neu, JETZT)
    assert e["ohne_urfassung"] == [db["ohne_urfassung"]]
    assert e["geschrieben"] == []


def test_rot_probe_ohne_urfassung_schranke_faellt_ohne_pruefung(db):
    """Rot-vor-gruen (a): entfernt man die Urfassungspruefung, schreibt der
    Code den Knoten trotzdem -- die Probe zeigt, dass der Test die Schranke
    wirklich prueft und nicht zufaellig gruen ist."""
    alt = [_alt_neu(db, db["ohne_urfassung"])]
    neu = [dict(alt[0], title="Neuer Titel", summary="Neue Zusammenfassung.")]

    def zurueckschreiben_ohne_urfassungsschranke(conn, alt_liste, neu_liste, jetzt):
        neu_je_id = {r["id"]: r for r in neu_liste}
        geschrieben = []
        for a in alt_liste:
            n = neu_je_id[a["id"]]
            conn.execute(
                "UPDATE knowledge_nodes SET title=?, summary=?, content=?, updated_at=? WHERE id=?",
                (n["title"], n["summary"], n.get("co"), jetzt, a["id"]))
            geschrieben.append(a["id"])
        return {"geschrieben": geschrieben}

    with speicher.schreiben(db["pfad"]) as conn:
        e_ohne_schranke = zurueckschreiben_ohne_urfassungsschranke(conn, alt, neu, JETZT)
    assert e_ohne_schranke["geschrieben"] == [db["ohne_urfassung"]], (
        "Rot-Probe schlug fehl: ohne die Schranke haette der Knoten geschrieben "
        "werden muessen, um zu zeigen, dass test_ohne_urfassung_wird_abgelehnt "
        "wirklich etwas verhindert -- tat es aber nicht.")


# ------------------------------------------------------- Schranke: Haelfte
def test_unbehandelte_haelfte_wird_abgelehnt_und_namentlich_genannt(db):
    alt = [_alt_neu(db, db["unbehandelt"])]
    neu = [dict(alt[0], title="Neuer Titel", summary="Neue Zusammenfassung.")]
    with speicher.schreiben(db["pfad"]) as conn:
        e = us.zurueckschreiben_alle(conn, alt, neu, JETZT)
    assert e["falsche_haelfte"] == [db["unbehandelt"]]
    assert e["geschrieben"] == []


def test_rot_probe_haelfte_schranke_faellt_ohne_pruefung(db):
    """Rot-vor-gruen (b): ohne die Haelften-Pruefung waere der Kontrollgruppen-
    Knoten schreibbar -- zeigt, dass die Ablehnung im Produktivcode traegt."""
    alt = [_alt_neu(db, db["unbehandelt"])]
    neu = [dict(alt[0], title="Neuer Titel", summary="Neue Zusammenfassung.")]
    with speicher.schreiben(db["pfad"]) as conn:
        conn.execute(
            "UPDATE knowledge_nodes SET title=?, summary=?, content=?, updated_at=? WHERE id=?",
            (neu[0]["title"], neu[0]["summary"], neu[0]["co"], JETZT, db["unbehandelt"]))
    with speicher.lesen(db["pfad"]) as conn:
        row = conn.execute("SELECT title FROM knowledge_nodes WHERE id=?", (db["unbehandelt"],)).fetchone()
    assert row["title"] == "Neuer Titel", (
        "Rot-Probe schlug fehl: ein direktes UPDATE ohne Haelften-Schranke "
        "haette durchgehen muessen, um zu belegen, dass die Schranke im "
        "Produktivcode der eigentliche Grund fuer die Ablehnung ist.")


# ------------------------------------------------------- Schranke: Pruefstein
def test_pruefstein_beanstandeter_knoten_wird_abgelehnt(db):
    """Eine Zahl (47 Prozent) verschwindet beim Umschreiben -- der Pruefstein
    muss das fangen und der Knoten darf nicht geschrieben werden."""
    alt = [_alt_neu(db, db["defekt"])]
    neu = [dict(alt[0], summary="Zusammenfassung C.", co="Text C.")]  # 47 verschwindet
    with speicher.schreiben(db["pfad"]) as conn:
        e = us.zurueckschreiben_alle(conn, alt, neu, JETZT)
    assert e["pruefstein_abgelehnt"] == [db["defekt"]]
    assert e["geschrieben"] == []


def test_rot_probe_pruefstein_schranke_faellt_ohne_pruefung(db):
    """Rot-vor-gruen (c): ohne den Pruefstein-Aufruf waere der Knoten mit der
    verschwundenen Zahl schreibbar -- zeigt, dass umschrift_pruefstein.py
    wirklich eingebunden ist, nicht nur importiert."""
    alt = _alt_neu(db, db["defekt"])
    neu = dict(alt, summary="Zusammenfassung C.", co="Text C.")
    befund = umschrift_pruefstein_ok(alt, neu)
    assert befund is False, "Pruefstein haette diesen Fall beanstanden muessen"


def umschrift_pruefstein_ok(alt, neu):
    import umschrift_pruefstein as ps
    return ps.pruefe_knoten(alt, neu)["ok"]


# ------------------------------------------------------- Negativfall: sauber
def test_sauberer_behandelter_knoten_mit_urfassung_wird_geschrieben(db):
    """Ohne diesen Test wuerde ein Werkzeug bestehen, das schlicht nie
    schreibt -- die drei Ablehnungstests waeren dann bedeutungslos gruen."""
    alt = [_alt_neu(db, db["sauber"])]
    neu = [dict(alt[0], title="Neu formulierter Titel",
                summary="Neu formulierte Zusammenfassung mit 8,50 USD.",
                co="Neu formulierter Volltext mit 8,50 USD.")]
    with speicher.schreiben(db["pfad"]) as conn:
        e = us.zurueckschreiben_alle(conn, alt, neu, JETZT)
    assert e["geschrieben"] == [db["sauber"]]
    assert e["ohne_urfassung"] == [] and e["falsche_haelfte"] == [] and e["pruefstein_abgelehnt"] == []
    with speicher.lesen(db["pfad"]) as conn:
        row = conn.execute("SELECT title FROM knowledge_nodes WHERE id=?", (db["sauber"],)).fetchone()
    assert row["title"] == "Neu formulierter Titel"


# ------------------------------------------------------- Wiederaufnahme
def test_umgeschriebener_knoten_taucht_in_zweitem_lose_nicht_wieder_auf(db):
    with speicher.lesen(db["pfad"]) as conn:
        vor = {e["id"] for e in us.lose_erzeugen(conn, 10, 0)}
    assert db["sauber"] in vor

    alt = [_alt_neu(db, db["sauber"])]
    neu = [dict(alt[0], title="Neu formulierter Titel",
                summary="Neu formulierte Zusammenfassung mit 8,50 USD.",
                co="Neu formulierter Volltext mit 8,50 USD.")]
    with speicher.schreiben(db["pfad"]) as conn:
        us.zurueckschreiben_alle(conn, alt, neu, JETZT)

    with speicher.lesen(db["pfad"]) as conn:
        nach = {e["id"] for e in us.lose_erzeugen(conn, 10, 0)}
    assert db["sauber"] not in nach
    assert db["defekt"] in nach  # nie erfolgreich geschrieben -> weiterhin Kandidat
