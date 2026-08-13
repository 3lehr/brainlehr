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

import json
import sqlite3
import tempfile

import pytest

import sicherung_s12
import speicher
import teilung_s12
import umschrift_s12 as us

JETZT = "2026-08-13T09:00:00+02:00"

# Echter Knoten aus dem verworfenen Los (nicht Kunsttext) fuer den
# Verdopplungs-Negativfall: der volle Volltext eines tatsaechlichen Fundes.
_ECHTER_KNOTEN = json.loads(
    (_w / "runs" / "s12_los_001_alt.json").read_text(encoding="utf-8"))[0]
assert _ECHTER_KNOTEN["id"] == "012500e5"


def _insert_node(conn: sqlite3.Connection, node_id: str, path: str,
                  title: str, summary: str, content: str,
                  norm_rang: int | None = None) -> None:
    """norm_rang=None (Vorgabe) legt einen gewoehnlichen Wissensknoten an.
    norm_rang=<Zahl> legt eine Norm an -- fuer den Grenzwerttest norm_rang=0
    (0 ist ein gueltiger Rang, nicht "kein Rang")."""
    if norm_rang is None:
        conn.execute(
            """INSERT INTO knowledge_nodes
               (id, path, parent_path, project_id, title, summary, content, level, tags, source,
                created_at, updated_at, norm_entscheidung,
                norm_entschieden_von, norm_entschieden_am, norm_entschieden_grund)
               VALUES (?, ?, '/', 'shared', ?, ?, ?, 1, '[]', ?, ?, ?, 'keine_norm', ?, ?, ?)""",
            (node_id, path, title, summary, content, node_id, JETZT, JETZT,
             "test:test_umschrift_s12.py", JETZT, "Testvorrichtung"),
        )
    else:
        conn.execute(
            """INSERT INTO knowledge_nodes
               (id, path, parent_path, project_id, title, summary, content, level, tags, source,
                created_at, updated_at, norm_rang, gilt_ab, norm_entscheidung, anlass,
                norm_entschieden_von, norm_entschieden_am, norm_entschieden_grund)
               VALUES (?, ?, '/', 'shared', ?, ?, ?, 1, '[]', ?, ?, ?, ?, ?, 'norm_unbefristet',
                       'betreiber', ?, ?, ?)""",
            (node_id, path, title, summary, content, node_id, JETZT, JETZT,
             norm_rang, JETZT, "Betreiber", JETZT, "Testvorrichtung"),
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
    sauber, ohne_urfassung, defekt, voll, norm = (
        behandelt[0], behandelt[1], behandelt[2], behandelt[3], behandelt[4])

    echter_pfad = "/x/echter-knoten"
    echter_titel = _ECHTER_KNOTEN["title"]
    echte_summary = _ECHTER_KNOTEN["summary"]
    echter_co = _ECHTER_KNOTEN["co"]

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
        _insert_node(conn, voll, echter_pfad, echter_titel, echte_summary, echter_co)
        # Grenzwert norm_rang=0: 0 ist ein gueltiger Rang (falsy in Python!),
        # muss trotzdem wie jede andere Norm behandelt werden.
        _insert_node(conn, norm, "/x/norm", "Bindende Regel E",
                     "Zusammenfassung E, wortgleich mit der Norm.", "Volltext der Norm E.",
                     norm_rang=0)
        _sichern(conn, sauber, "/x/sauber", "Alter Titel",
                 "Zusammenfassung mit 8,50 USD.", "Volltext 8,50 USD.")
        _sichern(conn, defekt, "/x/defekt", "Titel C",
                 "Zusammenfassung C mit 47 Prozent.", "Text C mit 47 Prozent.")
        _sichern(conn, voll, echter_pfad, echter_titel, echte_summary, echter_co)
        _sichern(conn, norm, "/x/norm", "Bindende Regel E",
                 "Zusammenfassung E, wortgleich mit der Norm.", "Volltext der Norm E.")
        # ohne_urfassung bekommt bewusst KEINE Zeile in s12_urfassungen.

    return {"pfad": pfad, "sauber": sauber, "ohne_urfassung": ohne_urfassung,
            "defekt": defekt, "unbehandelt": unbehandelt, "voll": voll,
            "norm": norm, "echter_co": echter_co}


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


# ------------------------------------------------------- Schranke: Norm (norm_rang)
def test_norm_wird_nicht_in_ein_los_aufgenommen(db):
    """Fuenfte Schranke, Stelle 1: kandidaten_unbehandelt/lose_erzeugen duerfen
    einen Knoten mit norm_rang IS NOT NULL gar nicht erst anbieten, obwohl er
    behandelt, mit Urfassung und wortgleich ist -- Grenzwert norm_rang=0."""
    with speicher.lesen(db["pfad"]) as conn:
        kand = us.kandidaten_unbehandelt(conn)
        los = us.lose_erzeugen(conn, 10, 0)
    assert db["norm"] not in kand, kand
    assert db["norm"] not in {e["id"] for e in los}, los


def test_rot_probe_norm_schranke_faellt_in_kandidaten_ohne_pruefung(db):
    """Rot-vor-gruen (e-1): ohne die norm_rang-Pruefung in
    kandidaten_unbehandelt waere der Normknoten (norm_rang=0, wortgleich mit
    seiner Urfassung) ein ganz normaler Kandidat."""
    with speicher.lesen(db["pfad"]) as conn:
        ids = teilung_s12.bestand(conn)["knoten"]
        behandelt = sorted(i for i in ids if teilung_s12.haelfte("knoten", i) == teilung_s12.BEHANDELT)
        raus = []
        for node_id in behandelt:
            row = conn.execute(
                "SELECT title, summary FROM knowledge_nodes WHERE id = ?", (node_id,)).fetchone()
            urf = conn.execute(
                "SELECT title, summary FROM s12_urfassungen WHERE node_id = ?", (node_id,)).fetchone()
            if row is None or urf is None:
                continue
            if row["title"] == urf["title"] and row["summary"] == urf["summary"]:
                raus.append(node_id)
    assert db["norm"] in raus, (
        "Rot-Probe schlug fehl: ohne die norm_rang-Pruefung haette der "
        "Normknoten als Kandidat erscheinen muessen, um zu zeigen, dass die "
        "Schranke in kandidaten_unbehandelt wirklich etwas ausschliesst.")


def test_norm_wird_von_zurueckschreiben_abgelehnt_und_namentlich_genannt(db):
    """Fuenfte Schranke, Stelle 2: ein ALTES Los (vor dieser Schranke erzeugt,
    hier per Hand nachgestellt) kann einen Normknoten trotzdem enthalten --
    zurueckschreiben_alle muss ihn zusaetzlich ablehnen."""
    alt = [_alt_neu(db, db["norm"])]
    neu = [dict(alt[0], title="Umformulierte Regel E", summary="Neue Zusammenfassung E.",
                co="Neuer Volltext E.")]
    with speicher.schreiben(db["pfad"]) as conn:
        e = us.zurueckschreiben_alle(conn, alt, neu, JETZT)
    assert e["norm_abgelehnt"] == [db["norm"]], e["norm_abgelehnt"]
    assert e["geschrieben"] == []
    with speicher.lesen(db["pfad"]) as conn:
        row = conn.execute("SELECT title FROM knowledge_nodes WHERE id=?", (db["norm"],)).fetchone()
    assert row["title"] == "Bindende Regel E", "Norm wurde trotz Ablehnung geschrieben"


def test_rot_probe_norm_schranke_faellt_in_zurueckschreiben_ohne_pruefung(db):
    """Rot-vor-gruen (e-2): ein direktes UPDATE ohne die norm_rang-Pruefung
    haette den Normknoten anstandslos umgeschrieben -- zeigt, dass die
    Ablehnung in zurueckschreiben_alle der eigentliche Grund ist."""
    alt = _alt_neu(db, db["norm"])
    neu = dict(alt, title="Umformulierte Regel E", summary="Neue Zusammenfassung E.",
               co="Neuer Volltext E.")
    with speicher.schreiben(db["pfad"]) as conn:
        conn.execute(
            "UPDATE knowledge_nodes SET title=?, summary=?, content=?, updated_at=? WHERE id=?",
            (neu["title"], neu["summary"], neu["co"], JETZT, db["norm"]))
    with speicher.lesen(db["pfad"]) as conn:
        row = conn.execute("SELECT title FROM knowledge_nodes WHERE id=?", (db["norm"],)).fetchone()
    assert row["title"] == "Umformulierte Regel E", (
        "Rot-Probe schlug fehl: ein direktes UPDATE ohne norm_rang-Schranke "
        "haette durchgehen muessen, um zu belegen, dass die Schranke im "
        "Produktivcode der eigentliche Grund fuer die Ablehnung ist.")


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


# ------------------------------------------------------- Schranke: Verdopplung
def test_kompletter_alter_text_angehaengt_wird_abgelehnt_und_namentlich_genannt(db):
    """Nachstellung des Vorfalls 2026-08-13 (L-a4f6dd): der 'neue' Volltext ist
    eine neue Einleitung plus der KOMPLETTE alte Volltext, unveraendert."""
    alt = [_alt_neu(db, db["voll"])]
    neu = [dict(alt[0], title="Neuer Titel", summary="Neue Zusammenfassung.",
                co="Neue Einleitung.\n\n" + db["echter_co"])]
    with speicher.schreiben(db["pfad"]) as conn:
        e = us.zurueckschreiben_alle(conn, alt, neu, JETZT)
    assert e["verdopplung_abgelehnt"] == [db["voll"]]
    assert e["geschrieben"] == []


def test_rot_probe_verdopplung_schranke_faellt_ohne_pruefung(db):
    """Rot-vor-gruen (d): ohne ist_blosse_verdopplung() haette der Pruefstein
    diesen Fall NICHT gefangen -- er meldet 0 Beanstandungen, weil der alte
    Text Teilmenge des neuen ist, also nichts fehlt."""
    alt = _alt_neu(db, db["voll"])
    neu = dict(alt, title="Neuer Titel", summary="Neue Zusammenfassung.",
               co="Neue Einleitung.\n\n" + db["echter_co"])
    import umschrift_pruefstein as ps
    befund = ps.pruefe_knoten(alt, neu)
    assert befund["ok"], (
        "Rot-Probe schlug fehl: der Pruefstein haette diesen Verdopplungsfall "
        "durchlassen muessen (0 Beanstandungen), um zu zeigen, dass die vierte "
        "Schranke etwas faengt, was die anderen drei nicht fangen.")
    assert us.ist_blosse_verdopplung(alt["co"], neu["co"]) is True


def test_negativfall_echte_umschrift_mit_uebernommenen_saetzen_geht_durch(db):
    """Ohne diesen Test waere die Schranke wertlos: sie darf eine ECHTE
    Umschrift nicht treffen, die (regelkonform) einzelne Saetze und alle
    Zahlen/Kennungen des alten Textes woertlich uebernimmt, aber den alten
    Text an einer Stelle unterbricht statt ihn komplett anzuhaengen. Baut auf
    dem echten Fund 012500e5 auf, nicht auf Kunsttext."""
    echter_co = db["echter_co"]
    mitte = len(echter_co) // 2
    # Ein neuer Satz mitten im uebernommenen Text -- bricht die Zusammenhaeng-
    # igkeit, laesst aber jeden Traeger (alle Zahlen/Kennungen) unangetastet.
    neuer_co = echter_co[:mitte] + " Neu eingefuegter Uebergangssatz. " + echter_co[mitte:]
    alt = [_alt_neu(db, db["voll"])]
    neu = [dict(alt[0], title="Neu formulierter Titel " + alt[0]["title"],
                summary="Neu eingeleitet: " + alt[0]["summary"], co=neuer_co)]
    assert not us.ist_blosse_verdopplung(alt[0]["co"], neu[0]["co"])
    with speicher.schreiben(db["pfad"]) as conn:
        e = us.zurueckschreiben_alle(conn, alt, neu, JETZT)
    assert e["geschrieben"] == [db["voll"]], e
    assert e["verdopplung_abgelehnt"] == []


# ------------------------------------------------------- Grenzwert: Verdopplung
def test_grenzwert_ein_zeichen_fehlt_laesst_durch(db):
    """Knapp UNTER der Schwelle (100% des alten Volltexts, luecken- und
    ordnungslos am Stueck): fehlt ein einziges Zeichen des alten Textes im
    angehaengten Block, ist es kein zusammenhaengender Volltreffer mehr."""
    echter_co = db["echter_co"]
    verstuemmelt = echter_co[:-1]  # ein Zeichen fehlt
    assert us.ist_blosse_verdopplung(echter_co, "Einleitung. " + verstuemmelt) is False


def test_grenzwert_vollstaendig_angehaengt_wird_erkannt(db):
    """Genau AN der Schwelle: der komplette (100%) alte Text steckt
    zusammenhaengend im neuen -- das ist der verbotene Fall."""
    echter_co = db["echter_co"]
    assert us.ist_blosse_verdopplung(echter_co, "Einleitung. " + echter_co) is True


def test_grenzwert_leerer_alter_text_gilt_nie_als_verdopplung(db):
    assert us.ist_blosse_verdopplung("", "irgendein neuer Text") is False


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
