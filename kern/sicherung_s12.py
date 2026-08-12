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
    python3 sicherung_s12.py --zurueck <path>        # einen Knoten wortgleich wiederherstellen
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
    zwischen Teilung und Lauf -- selten, aber ein Befund, kein Absturz)."""
    conn.executescript(SCHEMA)
    jetzt = jetzt or now_iso()
    pfade = teilung_s12.bestand(conn)["knoten"]
    behandelt = [p for p in pfade if teilung_s12.haelfte("knoten", p) == teilung_s12.BEHANDELT]

    ergebnis = {"behandelt_gesamt": len(behandelt), "gesichert": 0,
                "schon_gesichert": 0, "fehlend": 0}
    for pfad in behandelt:
        zeile = conn.execute(
            "SELECT id, title, summary, content FROM knowledge_nodes WHERE path = ?",
            (pfad,)).fetchone()
        if zeile is None:
            ergebnis["fehlend"] += 1
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO s12_urfassungen "
            "(node_id, path, title, summary, content, gesichert_am) VALUES (?,?,?,?,?,?)",
            (zeile["id"], pfad, zeile["title"], zeile["summary"], zeile["content"], jetzt))
        if cur.rowcount == 1:
            ergebnis["gesichert"] += 1
        else:
            ergebnis["schon_gesichert"] += 1
    return ergebnis


def zurueckschreiben(conn: sqlite3.Connection, path: str) -> bool:
    """Schreibt die gesicherte Urfassung in den Knoten zurueck. False, wenn
    fuer diesen Pfad nichts gesichert wurde -- kein stiller No-Op."""
    zeile = conn.execute(
        "SELECT node_id, title, summary, content FROM s12_urfassungen WHERE path = ?",
        (path,)).fetchone()
    if zeile is None:
        return False
    conn.execute(
        "UPDATE knowledge_nodes SET title = ?, summary = ?, content = ?, updated_at = ? "
        "WHERE id = ?",
        (zeile["title"], zeile["summary"], zeile["content"], now_iso(), zeile["node_id"]))
    return True


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
        # nicht raten, weil haelfte() deterministisch ist.
        kandidaten = [f"/x/{i}" for i in range(40)]
        behandelt = next(p for p in kandidaten if teilung_s12.haelfte("knoten", p) == teilung_s12.BEHANDELT)
        unbehandelt = next(p for p in kandidaten if teilung_s12.haelfte("knoten", p) == teilung_s12.UNBEHANDELT)
        _insert_node(conn, "n-beh", behandelt, "Alt-Titel", "Alt-Summary", "Alt-Text", jetzt)
        _insert_node(conn, "n-unbeh", unbehandelt, "U-Titel", "U-Summary", "U-Text", jetzt)

    # 1) Erster Lauf sichert genau den behandelten Knoten.
    with speicher.schreiben(db) as conn:
        e1 = sichern_behandelte(conn, jetzt)
    assert e1["gesichert"] == 1 and e1["schon_gesichert"] == 0, e1

    # 2) Negativfall: der unbehandelte Knoten wurde NICHT gesichert.
    with speicher.lesen(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM s12_urfassungen").fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM s12_urfassungen WHERE path = ?", (unbehandelt,)
        ).fetchone()[0] == 0, "unbehandelter Knoten wurde gesichert -- das darf nicht sein"

    # 3) Knoten wird ueberschrieben (simuliert Schritt 3 des Plans).
    with speicher.schreiben(db) as conn:
        conn.execute(
            "UPDATE knowledge_nodes SET title=?, summary=?, content=?, updated_at=? WHERE id='n-beh'",
            ("Neu-Titel", "Neu-Summary", "Neu-Text", jetzt))

    # 4) Zweite Sicherung NACH dem Ueberschreiben ueberschreibt die erste
    #    Zeile NICHT -- der Grenzfall, um den es im Auftrag geht.
    with speicher.schreiben(db) as conn:
        e2 = sichern_behandelte(conn, jetzt)
    assert e2["gesichert"] == 0 and e2["schon_gesichert"] == 1, e2
    with speicher.lesen(db) as conn:
        z = conn.execute("SELECT title, summary, content FROM s12_urfassungen WHERE path=?",
                          (behandelt,)).fetchone()
        assert (z["title"], z["summary"], z["content"]) == ("Alt-Titel", "Alt-Summary", "Alt-Text"), \
            "die zweite Sicherung hat das Original ueberschrieben"

    # 5) Rueckweg stellt den veraenderten Knoten wortgleich wieder her.
    with speicher.schreiben(db) as conn:
        vorher = conn.execute("SELECT title, summary, content FROM knowledge_nodes WHERE id='n-beh'").fetchone()
        assert (vorher["title"], vorher["summary"], vorher["content"]) == \
            ("Neu-Titel", "Neu-Summary", "Neu-Text")
        ok = zurueckschreiben(conn, behandelt)
    assert ok is True
    with speicher.lesen(db) as conn:
        nachher = conn.execute("SELECT title, summary, content FROM knowledge_nodes WHERE id='n-beh'").fetchone()
    assert (nachher["title"], nachher["summary"], nachher["content"]) == \
        ("Alt-Titel", "Alt-Summary", "Alt-Text"), \
        "Rueckweg hat den Knoten nicht wortgleich wiederhergestellt"

    # 6) Rueckweg fuer einen nie gesicherten Pfad meldet False, kein stiller No-Op.
    with speicher.schreiben(db) as conn:
        assert zurueckschreiben(conn, "/x/nie-gesichert") is False

    print("selftest ok (6 Faelle, Gegenprobe in beide Richtungen)", file=_sys.stderr)


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sichern", action="store_true")
    p.add_argument("--zurueck", metavar="PATH")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
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
