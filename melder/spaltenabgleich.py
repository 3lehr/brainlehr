#!/usr/bin/env python3
"""J3 -- dieselbe Umkehrung wie J1, aber pro TABELLE und pro SPALTE statt als
Gesamttext, und als wiederverwendbare Bauform (`beidseitig`) statt als
Einzelfall.

ANLASS. melder/schemastand.py haelt schema.sql (SOLL) gegen die installierte
Datenbank (IST) -- aber als GANZEN CREATE-TABLE-Text: weicht eine Tabelle ab,
meldet es "Text weicht ab", nie welche Spalte. Fuer die Frage "welche Spalte
fehlt, welche ist zusaetzlich da" (Linie J, Punkt J3 -- "ist etwas da, das
nicht auf der Liste steht?") ist das zu grob. Dieser Melder liest je Tabelle
`PRAGMA table_info`, vergleicht Spaltenname UND -definition (Typ, NOT NULL,
Default, Primary-Key-Rang) und meldet namentlich.

BAUFORM: `beidseitig(soll, ist)` ist die eine Funktion, die die Umkehrung
traegt -- zwei Mengen rein, `nur_soll`/`nur_ist` raus. Sowohl der
Tabellenvergleich als auch der Spaltenvergleich rufen sie auf; ein
kuenftiger Melder mit derselben Frage (Anwesenheit vs. Vollstaendigkeit)
kann sie importieren, statt die Mengendifferenz erneut zu schreiben.

QUELLE DER WAHRHEIT wie bei schemastand.py: schema.sql wird in eine
Wegwerf-Datenbank ausgefuehrt und GENAUSO gelesen (PRAGMA table_info) wie
der Ist-Stand -- kein eigener SQL-Parser fuer Spaltendefinitionen.

Aufruf:
    python3 melder/spaltenabgleich.py --pruefen
    python3 melder/spaltenabgleich.py --selftest
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "kern"))
sys.path.insert(0, str(WURZEL / "haken"))
import speicher  # noqa: E402 -- eine Tuer zur Datenbank statt einer eigenen

SCHEMA_PFAD = WURZEL / "schema.sql"


def beidseitig(soll: set, ist: set) -> dict:
    """Die J3-Bauform: zwei Mengen rein, beide Richtungen der Abweichung
    raus. `nur_soll` = fehlt installiert, `nur_ist` = zusaetzlich installiert,
    von schema.sql nicht verlangt."""
    return {
        "nur_soll": sorted(soll - ist),
        "nur_ist": sorted(ist - soll),
    }


def _tabellen(conn: sqlite3.Connection) -> set[str]:
    zeilen = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {z["name"] for z in zeilen}


def _spalten(conn: sqlite3.Connection, tabelle: str) -> dict[str, tuple]:
    """Spaltenname -> (Typ, NOT NULL, Default, PK-Rang), aus PRAGMA
    table_info -- dieselbe Quelle fuer SOLL und IST, kein eigener Parser."""
    zeilen = conn.execute(f"PRAGMA table_info('{tabelle}')").fetchall()
    return {
        z["name"]: (z["type"], z["notnull"], z["dflt_value"], z["pk"])
        for z in zeilen
    }


def _soll_conn(schema_pfad: Path = SCHEMA_PFAD):
    """Wegwerf-Datenbank aus schema.sql, offen gehalten fuer die Dauer des
    Vergleichs (Tempverzeichnis loescht sich beim Verlassen)."""
    td = tempfile.TemporaryDirectory()
    tmp = Path(td.name) / "soll.db"
    with speicher.schreiben(tmp) as conn:
        conn.executescript(schema_pfad.read_text(encoding="utf-8"))
    return td, tmp


def vergleich(schema_pfad: Path = SCHEMA_PFAD, db: Path | None = None) -> dict:
    """Tabellenabgleich, dann je gemeinsamer Tabelle der Spaltenabgleich."""
    td, soll_pfad = _soll_conn(schema_pfad)
    try:
        with speicher.lesen(soll_pfad) as sconn, speicher.lesen(db) as iconn:
            soll_tabellen = _tabellen(sconn)
            ist_tabellen = _tabellen(iconn)
            tabellen = beidseitig(soll_tabellen, ist_tabellen)

            spalten: dict[str, dict] = {}
            for name in sorted(soll_tabellen & ist_tabellen):
                soll_sp = _spalten(sconn, name)
                ist_sp = _spalten(iconn, name)
                d = beidseitig(set(soll_sp), set(ist_sp))
                abweichend = sorted(
                    k for k in set(soll_sp) & set(ist_sp)
                    if soll_sp[k] != ist_sp[k]
                )
                if d["nur_soll"] or d["nur_ist"] or abweichend:
                    spalten[name] = {
                        "fehlt": d["nur_soll"],
                        "zusaetzlich": d["nur_ist"],
                        "abweichend": abweichend,
                    }
            return {"tabellen": tabellen, "spalten": spalten}
    finally:
        td.cleanup()


def bericht(ergebnis: dict) -> str:
    if not ergebnis["tabellen"]["nur_soll"] and not ergebnis["tabellen"]["nur_ist"] and not ergebnis["spalten"]:
        return "spaltenabgleich: keine Abweichung -- Tabellen und Spalten stimmen mit schema.sql ueberein."
    zeilen = ["spaltenabgleich: Abweichungen zwischen schema.sql (SOLL) und der installierten Datenbank (IST)"]
    t = ergebnis["tabellen"]
    if t["nur_soll"]:
        zeilen.append(f"  Tabellen in schema.sql, aber NICHT installiert ({len(t['nur_soll'])}): {', '.join(t['nur_soll'])}")
    if t["nur_ist"]:
        zeilen.append(f"  Tabellen installiert, aber NICHT in schema.sql ({len(t['nur_ist'])}): {', '.join(t['nur_ist'])}")
    for name, d in ergebnis["spalten"].items():
        if d["fehlt"]:
            zeilen.append(f"  {name}: Spalte(n) fehlen installiert: {', '.join(d['fehlt'])}")
        if d["zusaetzlich"]:
            zeilen.append(f"  {name}: Spalte(n) zusaetzlich installiert: {', '.join(d['zusaetzlich'])}")
        if d["abweichend"]:
            zeilen.append(f"  {name}: Spalte(n) mit abweichender Definition: {', '.join(d['abweichend'])}")
    return "\n".join(zeilen)


def _keine_meldung(ergebnis: dict) -> bool:
    return not ergebnis["tabellen"]["nur_soll"] and not ergebnis["tabellen"]["nur_ist"] and not ergebnis["spalten"]


def _selftest() -> None:
    import shutil

    tmp = Path(tempfile.mkdtemp())

    # 1) Negativfall: exakter Nachbau -> keine Meldung. Positivkontrolle
    #    fuer den Harness selbst -- wenn dieser Fall schon meldet, ist der
    #    Pruefstand kaputt, nicht schema.sql.
    exakt = tmp / "exakt.db"
    with speicher.schreiben(exakt) as conn:
        conn.executescript(SCHEMA_PFAD.read_text(encoding="utf-8"))
    ergebnis = vergleich(db=exakt)
    assert _keine_meldung(ergebnis), f"exakter Nachbau meldet faelschlich: {ergebnis}"

    # 2) Grenzwert: leere Datenbank (keine einzige Tabelle) -> ALLE
    #    schema.sql-Tabellen als 'nur_soll' fehlend, keine Ausnahme/Absturz.
    leer = tmp / "leer.db"
    with speicher.schreiben(leer):
        pass
    ergebnis = vergleich(db=leer)
    assert "schema_migrations" in ergebnis["tabellen"]["nur_soll"], ergebnis
    assert not ergebnis["spalten"], "leere DB hat keine gemeinsamen Tabellen, darf keine Spalten vergleichen"

    # 3) Tabelle fehlt komplett installiert.
    tab_fehlt = tmp / "tab_fehlt.db"
    shutil.copy(exakt, tab_fehlt)
    with speicher.schreiben(tab_fehlt) as conn:
        conn.execute("DROP TABLE schema_migrations")
    ergebnis = vergleich(db=tab_fehlt)
    assert "schema_migrations" in ergebnis["tabellen"]["nur_soll"], ergebnis

    # 4) Zusaetzliche Tabelle, von schema.sql nicht verlangt (der Fund-Fall:
    #    untergeschobenes Objekt, das keine Pruefung bisher als Ueberhang sah).
    tab_extra = tmp / "tab_extra.db"
    shutil.copy(exakt, tab_extra)
    with speicher.schreiben(tab_extra) as conn:
        conn.execute("CREATE TABLE gewachsen (id INTEGER PRIMARY KEY)")
    ergebnis = vergleich(db=tab_extra)
    assert "gewachsen" in ergebnis["tabellen"]["nur_ist"], ergebnis

    # 5) Spalte fehlt in einer gemeinsamen Tabelle.
    sp_fehlt = tmp / "sp_fehlt.db"
    shutil.copy(exakt, sp_fehlt)
    with speicher.schreiben(sp_fehlt) as conn:
        conn.execute("ALTER TABLE schema_migrations DROP COLUMN beschreibung")
    ergebnis = vergleich(db=sp_fehlt)
    assert "beschreibung" in ergebnis["spalten"]["schema_migrations"]["fehlt"], ergebnis

    # 6) Spalte zusaetzlich installiert, von schema.sql nicht verlangt.
    sp_extra = tmp / "sp_extra.db"
    shutil.copy(exakt, sp_extra)
    with speicher.schreiben(sp_extra) as conn:
        conn.execute("ALTER TABLE schema_migrations ADD COLUMN untergeschoben TEXT")
    ergebnis = vergleich(db=sp_extra)
    assert "untergeschoben" in ergebnis["spalten"]["schema_migrations"]["zusaetzlich"], ergebnis

    # 7) Grenzwert: gleicher Spaltenname, andere Definition (Typ) -- der
    #    Fall aus L-55075a auf Spaltenebene statt Triggerebene.
    sp_abweichend = tmp / "sp_abweichend.db"
    shutil.copy(exakt, sp_abweichend)
    with speicher.schreiben(sp_abweichend) as conn:
        conn.execute("ALTER TABLE schema_migrations DROP COLUMN beschreibung")
        conn.execute("ALTER TABLE schema_migrations ADD COLUMN beschreibung INTEGER")
    ergebnis = vergleich(db=sp_abweichend)
    d = ergebnis["spalten"]["schema_migrations"]
    assert "beschreibung" in d["abweichend"], ergebnis
    assert "beschreibung" not in d["fehlt"] and "beschreibung" not in d["zusaetzlich"], (
        "gleicher Name, anderer Typ als fehlend/zusaetzlich statt als 'abweichend' gemeldet"
    )

    print("selftest ok (7 Faelle, Negativfall + Grenzwerte beidseitig)", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pruefen", action="store_true", help="gegen die echte Datenbank pruefen")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        _selftest()
        return
    if args.pruefen or len(sys.argv) == 1:
        print(bericht(vergleich()))
        return
    parser.print_help()


if __name__ == "__main__":
    main()
