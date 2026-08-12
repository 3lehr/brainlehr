#!/usr/bin/env python3
"""Urfassung sichern, bevor S12 einen Knotentext ueberschreibt.

Plan docs/PLAN_S12_ZWEITER_ANLAUF_2026-08-11.md, Nachtrag 2026-08-12T07:20:
`knowledge_nodes` traegt genau ein title/summary/content -- kein Platz fuer
eine zweite Fassung. Entschieden: die Urfassung wandert in eine Nebentabelle,
der Knoten behaelt spaeter den neuen Text. Diese Datei baut NUR die Ablage
und den Weg zurueck -- das Umschreiben selbst (Schritt 3 des Plans) ist ein
spaeterer Schritt und nicht Teil dieser Datei.

EIN KNOTEN WIRD NUR EINMAL GESICHERT: node_id ist PRIMARY KEY, das Ablegen
laeuft ueber INSERT OR IGNORE. Ein zweiter Lauf nach dem Umschreiben trifft
also auf eine bereits belegte Zeile und laesst sie stehen -- sonst wuerde der
zweite Durchlauf die eigentliche Urfassung durch den schon veraenderten Text
ersetzen, und genau das soll die Sicherung verhindern.

NUR DIE BEHANDELTE HAELFTE wird gesichert (teilung_s12.haelfte). Die
unbehandelte Haelfte bleibt unberuehrt -- sie ist die Kontrollgruppe des
Plans und wird nie umgeschrieben, eine Sicherung fuer sie waere Vorbau ohne
Zweck.

Aufruf:
    python3 sicherung_s12.py --sichern              # Lauf ueber die behandelte Haelfte
    python3 sicherung_s12.py --zurueck <node_id>     # einen Knoten wortgleich wiederherstellen
    python3 sicherung_s12.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import sqlite3

import speicher
import teilung_s12
from knowledge_mcp_server import now_iso  # noqa: E402 -- kanonisches Zeitstempelformat

WURZEL = _w

SCHEMA = """
CREATE TABLE IF NOT EXISTS s12_urfassungen (
    node_id       TEXT PRIMARY KEY,   -- knowledge_nodes.id, unveraenderlich
    path          TEXT NOT NULL,      -- knowledge_nodes.path zum Sicherungszeitpunkt
    title         TEXT NOT NULL,
    summary       TEXT NOT NULL,
    content       TEXT,
    gesichert_am  TEXT NOT NULL
);
"""


def sichern_behandelte(conn: sqlite3.Connection, jetzt: str | None = None) -> dict:
    """Sichert die Urfassung jedes BEHANDELTEN Knotens, aendert am Knoten
    selbst nichts. Gibt den Nenner mit: gesichert, schon_gesichert (Zweitlauf
    traf auf eine bestehende Zeile), fehlend (Knoten aus bestand() verschwand
    zwischen Teilung und Lauf -- selten, aber ein Befund, kein Absturz).

    Schluessel ist die Knoten-`id` (teilung_s12.bestand() liefert seit der
    Umstellung auf den ID-Schluessel keine Pfade mehr) -- `path` wird nur noch
    informativ mitgesichert, zum Sicherungszeitpunkt gelesen."""
    conn.executescript(SCHEMA)
    jetzt = jetzt or now_iso()
    ids = teilung_s12.bestand(conn)["knoten"]
    behandelt = [i for i in ids if teilung_s12.haelfte("knoten", i) == teilung_s12.BEHANDELT]

    ergebnis = {"behandelt_gesamt": len(behandelt), "gesichert": 0,
                "schon_gesichert": 0, "fehlend": 0}
    for node_id in behandelt:
        zeile = conn.execute(
            "SELECT path, title, summary, content FROM knowledge_nodes WHERE id = ?",
            (node_id,)).fetchone()
        if zeile is None:
            ergebnis["fehlend"] += 1
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO s12_urfassungen "
            "(node_id, path, title, summary, content, gesichert_am) VALUES (?,?,?,?,?,?)",
            (node_id, zeile["path"], zeile["title"], zeile["summary"], zeile["content"], jetzt))
        if cur.rowcount == 1:
            ergebnis["gesichert"] += 1
        else:
            ergebnis["schon_gesichert"] += 1
    return ergebnis


def zurueckschreiben(conn: sqlite3.Connection, node_id: str) -> bool:
    """Schreibt die gesicherte Urfassung in den Knoten zurueck. False, wenn
    fuer diese id nichts gesichert wurde -- kein stiller No-Op.

    Schluessel ist die Knoten-`id`, nicht der Pfad -- der Pfad ist
    veraenderlich (migrationen/nachziehung_pfad_hygiene_2026-08-07.py) und
    waere zwischen Sicherung und Rueckweg nicht mehr verlaesslich derselbe."""
    zeile = conn.execute(
        "SELECT title, summary, content FROM s12_urfassungen WHERE node_id = ?",
        (node_id,)).fetchone()
    if zeile is None:
        return False
    conn.execute(
        "UPDATE knowledge_nodes SET title = ?, summary = ?, content = ?, updated_at = ? "
        "WHERE id = ?",
        (zeile["title"], zeile["summary"], zeile["content"], now_iso(), node_id))
    return True


def abgleichen_mit_neuer_teilung(conn: sqlite3.Connection, jetzt: str | None = None) -> dict:
    """Bringt s12_urfassungen mit der aktuellen (ID-basierten) Teilung in
    Uebereinstimmung, nachdem der Teilungsschluessel fuer Knoten von `path`
    auf `id` gewechselt ist (docs/PLAN_S12_ZWEITER_ANLAUF_2026-08-11.md,
    Nachtrag ID-Schluessel 2026-08-12). Die bisherigen 1009 Zeilen wurden
    unter dem alten PFAD-Schluessel gezogen; ihre Menge stimmt jetzt nicht
    mehr mit teilung_s12.bestand()/haelfte() (ID-Schluessel) ueberein.

    Regel, EINMAL bindend fuer diesen Wechsel:
    - Ein Knoten, der unter ALTEM und NEUEM Schluessel behandelt ist, bleibt
      unangetastet -- seine Zeile ist bereits die korrekte Urfassung und darf
      nicht durch eine erneute Abfrage ersetzt werden (Auftragsgrenze).
    - Ein Knoten, der nur noch unter dem ALTEN Schluessel behandelt war, wird
      aus der Tabelle entfernt: sein Original ist nachweislich unveraendert
      live in knowledge_nodes (siehe Bericht -- kein Umschreiben lief bislang),
      die Zeile ist also verzichtbare Redundanz und wuerde spaeter suggerieren,
      der Knoten stehe zur Neuformulierung an.
    - Ein Knoten, der nur unter dem NEUEN Schluessel behandelt ist, wird
      gesichert, wie sichern_behandelte() es fuer den Erstlauf tut.
    """
    conn.executescript(SCHEMA)
    alt_ids = {r[0] for r in conn.execute("SELECT node_id FROM s12_urfassungen")}
    ids = teilung_s12.bestand(conn)["knoten"]
    neu_ids = {i for i in ids if teilung_s12.haelfte("knoten", i) == teilung_s12.BEHANDELT}

    weiterhin = alt_ids & neu_ids
    entfernt = alt_ids - neu_ids
    neu_hinzu = neu_ids - alt_ids

    if entfernt:
        conn.executemany("DELETE FROM s12_urfassungen WHERE node_id = ?",
                          [(i,) for i in entfernt])

    jetzt = jetzt or now_iso()
    gesichert = 0
    for node_id in neu_hinzu:
        zeile = conn.execute(
            "SELECT path, title, summary, content FROM knowledge_nodes WHERE id = ?",
            (node_id,)).fetchone()
        if zeile is None:
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO s12_urfassungen "
            "(node_id, path, title, summary, content, gesichert_am) VALUES (?,?,?,?,?,?)",
            (node_id, zeile["path"], zeile["title"], zeile["summary"], zeile["content"], jetzt))
        if cur.rowcount == 1:
            gesichert += 1

    return {"weiterhin_gueltig": len(weiterhin), "entfernt": len(entfernt),
            "neu_gesichert": gesichert, "neu_behandelt_gesamt": len(neu_ids)}


# --- Selbsttest ------------------------------------------------------------

def _insert_node(conn: sqlite3.Connection, node_id: str, path: str,
                  title: str, summary: str, content: str, jetzt: str) -> None:
    conn.execute(
        """INSERT INTO knowledge_nodes
           (id, path, parent_path, project_id, title, summary, content, level, tags, source,
            created_at, updated_at, norm_entscheidung,
            norm_entschieden_von, norm_entschieden_am, norm_entschieden_grund)
           VALUES (?, ?, '/', 'shared', ?, ?, ?, 1, '[]', ?, ?, ?, 'keine_norm', ?, ?, ?)""",
        (node_id, path, title, summary, content, node_id, jetzt, jetzt,
         "skript:sicherung_s12.py", jetzt, "Testvorrichtung fuer die Urfassungs-Sicherung"),
    )


def _selftest() -> None:
    import tempfile

    tmp = _Path(tempfile.mkdtemp())
    db = tmp / "probe.db"
    schema_sql = (WURZEL / "schema.sql").read_text(encoding="utf-8")
    jetzt = "2026-08-12T08:00:00+02:00"

    with speicher.schreiben(db) as conn:
        conn.executescript(schema_sql)
        # Zwei Knoten je Haelfte besorgen -- ueber die Kennung selbst finden,
        # nicht raten, weil haelfte() deterministisch ist. Schluessel ist die
        # ID, nicht der Pfad -- der Pfad ist hier nur noch Nutzlast.
        kandidaten = [f"n-{i}" for i in range(40)]
        beh_id = next(k for k in kandidaten if teilung_s12.haelfte("knoten", k) == teilung_s12.BEHANDELT)
        unbeh_id = next(k for k in kandidaten if teilung_s12.haelfte("knoten", k) == teilung_s12.UNBEHANDELT)
        _insert_node(conn, beh_id, "/x/beh", "Alt-Titel", "Alt-Summary", "Alt-Text", jetzt)
        _insert_node(conn, unbeh_id, "/x/unbeh", "U-Titel", "U-Summary", "U-Text", jetzt)

    # 1) Erster Lauf sichert genau den behandelten Knoten.
    with speicher.schreiben(db) as conn:
        e1 = sichern_behandelte(conn, jetzt)
    assert e1["gesichert"] == 1 and e1["schon_gesichert"] == 0, e1

    # 2) Negativfall: der unbehandelte Knoten wurde NICHT gesichert.
    with speicher.lesen(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM s12_urfassungen").fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM s12_urfassungen WHERE node_id = ?", (unbeh_id,)
        ).fetchone()[0] == 0, "unbehandelter Knoten wurde gesichert -- das darf nicht sein"

    # 3) Knoten wird ueberschrieben (simuliert Schritt 3 des Plans).
    with speicher.schreiben(db) as conn:
        conn.execute(
            "UPDATE knowledge_nodes SET title=?, summary=?, content=?, updated_at=? WHERE id=?",
            ("Neu-Titel", "Neu-Summary", "Neu-Text", jetzt, beh_id))

    # 4) Zweite Sicherung NACH dem Ueberschreiben ueberschreibt die erste
    #    Zeile NICHT -- der Grenzfall, um den es im Auftrag geht.
    with speicher.schreiben(db) as conn:
        e2 = sichern_behandelte(conn, jetzt)
    assert e2["gesichert"] == 0 and e2["schon_gesichert"] == 1, e2
    with speicher.lesen(db) as conn:
        z = conn.execute("SELECT title, summary, content FROM s12_urfassungen WHERE node_id=?",
                          (beh_id,)).fetchone()
        assert (z["title"], z["summary"], z["content"]) == ("Alt-Titel", "Alt-Summary", "Alt-Text"), \
            "die zweite Sicherung hat das Original ueberschrieben"

    # 5) Rueckweg stellt den veraenderten Knoten wortgleich wieder her.
    with speicher.schreiben(db) as conn:
        vorher = conn.execute("SELECT title, summary, content FROM knowledge_nodes WHERE id=?", (beh_id,)).fetchone()
        assert (vorher["title"], vorher["summary"], vorher["content"]) == \
            ("Neu-Titel", "Neu-Summary", "Neu-Text")
        ok = zurueckschreiben(conn, beh_id)
    assert ok is True
    with speicher.lesen(db) as conn:
        nachher = conn.execute("SELECT title, summary, content FROM knowledge_nodes WHERE id=?", (beh_id,)).fetchone()
    assert (nachher["title"], nachher["summary"], nachher["content"]) == \
        ("Alt-Titel", "Alt-Summary", "Alt-Text"), \
        "Rueckweg hat den Knoten nicht wortgleich wiederhergestellt"

    # 6) Rueckweg fuer eine nie gesicherte id meldet False, kein stiller No-Op.
    with speicher.schreiben(db) as conn:
        assert zurueckschreiben(conn, "n-nie-gesichert") is False

    # 7) Abgleich mit neuer Teilung (Schluesselwechsel path->id): eine unter
    #    ALT und NEU behandelte Zeile bleibt stehen, eine nur-noch-alte wird
    #    entfernt, eine nur-neue wird ergaenzt.
    td2 = _Path(tempfile.mkdtemp())
    db2 = td2 / "probe2.db"
    with speicher.schreiben(db2) as conn:
        conn.executescript(schema_sql)
        kandidaten2 = [f"m-{i}" for i in range(60)]
        neu_ids = [k for k in kandidaten2 if teilung_s12.haelfte("knoten", k) == teilung_s12.BEHANDELT]
        alt_und_neu = neu_ids[0]
        nur_neu = neu_ids[1]
        nur_alt = next(k for k in kandidaten2 if k not in neu_ids)

        for nid in (alt_und_neu, nur_neu, nur_alt):
            _insert_node(conn, nid, f"/x/{nid}", f"T-{nid}", f"S-{nid}", f"C-{nid}", jetzt)

        conn.executescript(SCHEMA)
        # Alte Sicherung simulieren: nur alt_und_neu und nur_alt waren unter
        # dem frueheren PFAD-Schluessel als behandelt gesichert worden.
        for nid in (alt_und_neu, nur_alt):
            conn.execute(
                "INSERT INTO s12_urfassungen (node_id, path, title, summary, content, gesichert_am) "
                "VALUES (?,?,?,?,?,?)",
                (nid, f"/x/{nid}", f"T-{nid}", f"S-{nid}", f"C-{nid}", jetzt))

    with speicher.schreiben(db2) as conn:
        e3 = abgleichen_mit_neuer_teilung(conn, jetzt)
    with speicher.lesen(db2) as conn:
        rows = {r[0] for r in conn.execute("SELECT node_id FROM s12_urfassungen")}
    assert alt_und_neu in rows, "eine unter beiden Teilungen behandelte Zeile wurde entfernt -- Datenverlust"
    assert nur_alt not in rows, "eine nicht mehr behandelte Zeile blieb stehen"
    assert nur_neu in rows, "eine neu behandelte Zeile wurde nicht ergaenzt"
    assert (e3["entfernt"], e3["neu_gesichert"], e3["weiterhin_gueltig"]) == (1, 1, 1), e3

    print("selftest ok (7 Faelle, Gegenprobe in beide Richtungen)", file=_sys.stderr)


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sichern", action="store_true")
    p.add_argument("--abgleichen", action="store_true",
                    help="s12_urfassungen einmalig auf den ID-Schluessel nachziehen (Schluesselwechsel path->id)")
    p.add_argument("--zurueck", metavar="NODE_ID")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    if a.abgleichen:
        with speicher.schreiben() as conn:
            e = abgleichen_mit_neuer_teilung(conn)
        print(f"neu behandelt gesamt: {e['neu_behandelt_gesamt']} -- "
              f"weiterhin gueltig: {e['weiterhin_gueltig']}, entfernt: {e['entfernt']}, "
              f"neu gesichert: {e['neu_gesichert']}")
        return

    if a.sichern:
        with speicher.schreiben() as conn:
            e = sichern_behandelte(conn)
        print(f"behandelt: {e['behandelt_gesamt']} -- "
              f"gesichert: {e['gesichert']}, schon gesichert: {e['schon_gesichert']}, "
              f"fehlend: {e['fehlend']}")
        return

    if a.zurueck:
        with speicher.schreiben() as conn:
            ok = zurueckschreiben(conn, a.zurueck)
        if ok:
            print(f"zurueckgeschrieben: {a.zurueck}")
        else:
            print(f"keine Urfassung fuer {a.zurueck} gesichert -- nichts getan")
            _sys.exit(1)
        return

    p.print_help()


if __name__ == "__main__":
    main()
