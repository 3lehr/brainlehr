#!/usr/bin/env python3
"""Soll gegen Ist: haelt schema.sql gegen die INSTALLIERTEN Schemaobjekte.

ANLASS. Zweimal in einer Woche hat genau diese Luecke zugeschlagen, beide
Male bei gruenen Tests. Am 2026-08-13 (L-55075a) wurde ein fehlerhafter
norm_art-Trigger in schema.sql korrigiert -- die INSTALLIERTE Fassung blieb
falsch, weil `CREATE TRIGGER IF NOT EXISTS` nur ERGAENZT, nie ERSETZT. Am
2026-08-08 (L-96db3e) trug die Erstanlage aus schema.sql 2 Trigger, 6
Tabellen und 2 Spalten WENIGER als der gewachsene Bestand. Es gab bis heute
keine Stelle, die schema.sql (SOLL) gegen sqlite_master (IST) haelt.

WIE VERGLICHEN WIRD, und warum nicht per Regex-Zerlegung von schema.sql: Aus
schema.sql wird in einer Wegwerf-Datenbank ein SOLL-Stand ERZEUGT (per
executescript) und danach genauso aus sqlite_master GELESEN wie der Ist-
Stand -- dieselbe Quelle der Wahrheit fuer beide Seiten. Das erspart einen
selbstgebauten SQL-Parser (der bei CREATE VIRTUAL TABLE ... USING fts5(...)
oder mehrzeiligen Trigger-Bodies mit eigenen Semikola leicht danebenliegt)
und behandelt FTS5-Schattentabellen (knowledge_fts_data, _idx, _docsize, ...)
automatisch richtig: sie entstehen auf BEIDEN Seiten aus derselben
CREATE-VIRTUAL-TABLE-Zeile und faellen darum nie als Ueberhang auf.

WAS DIE NORMALISIERUNG DURCHLAESST, und was nicht:
  - Leerraum (Zeilenumbrueche, mehrfache Leerzeichen, Einrueckung) wird zu
    einem einzelnen Leerzeichen geglaettet und Rand getrimmt. Reine
    Formatierung ist keine inhaltliche Abweichung.
  - Gross-/Kleinschreibung bleibt UNANGETASTET. Der belegte Anlassfall
    (L-55075a) war ein Trigger, dessen FEHLER im Text steckte -- zwei
    Schreibweisen desselben Bezeichners (etwa NEW.id vs new.ID) zeigen eher
    eine andere Bearbeitungsquelle an als reines Rauschen, und wer das
    wegnormalisiert, riskiert genau die Sorte Abweichung zu verschlucken,
    die dieser Melder finden soll. Lieber einmal zu viel melden.
  - sqlite_master-Zeilen ohne SQL-Text (Autoindizes zu UNIQUE-Constraints,
    `sqlite_sequence`) werden ausgeschlossen: das sind keine in schema.sql
    benannten Objekte, sondern Nebenwirkungen der Engine, und sie zaehlen
    auf beiden Seiten identisch, tragen also nie ein Signal.

Aufruf:
    python3 melder/schemastand.py --pruefen    # Abweichungen gegen die echte DB
    python3 melder/schemastand.py --selftest
"""
from __future__ import annotations

import argparse
import re
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
OBJEKTTYPEN = ("table", "trigger", "index", "view")


def _normalisiert(sql: str) -> str:
    """Nur Leerraum wird geglaettet, siehe Docstring oben zur Begruendung."""
    return re.sub(r"\s+", " ", sql.strip())


def _objekte(conn: sqlite3.Connection) -> dict[tuple[str, str], str]:
    """Tabellen, Trigger, Indizes, Sichten -- benannt und mit SQL-Text.
    Autoindizes/`sqlite_sequence` (Praefix 'sqlite_', kein eigener CREATE in
    schema.sql) fallen heraus."""
    zeilen = conn.execute(
        "SELECT type, name, sql FROM sqlite_master "
        "WHERE type IN ({}) AND sql IS NOT NULL".format(
            ",".join("?" for _ in OBJEKTTYPEN)
        ),
        OBJEKTTYPEN,
    ).fetchall()
    return {
        (z["type"], z["name"]): _normalisiert(z["sql"])
        for z in zeilen
        if not z["name"].startswith("sqlite_")
    }


def _soll(schema_pfad: Path = SCHEMA_PFAD) -> dict[tuple[str, str], str]:
    """schema.sql frisch in eine Wegwerf-Datenbank ausgefuehrt, danach genauso
    gelesen wie der Ist-Stand -- siehe Docstring oben."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "soll.db"
        with speicher.schreiben(tmp) as conn:
            conn.executescript(schema_pfad.read_text(encoding="utf-8"))
        with speicher.lesen(tmp) as conn:
            return _objekte(conn)


def vergleich(schema_pfad: Path = SCHEMA_PFAD, db: Path | None = None) -> dict:
    """Vergleich in beide Richtungen plus abweichendes SQL bei gleichem Namen.
    `db=None` liest ueber speicher.lesen() die echte Datenbank (BRAINLEHR_DB /
    BEGOD_KNOWLEDGE_DB / brainlehr.db) -- nur lesend, nie schreibend."""
    soll = _soll(schema_pfad)
    with speicher.lesen(db) as conn:
        ist = _objekte(conn)
    return {
        "nur_in_schema_sql": sorted(soll.keys() - ist.keys()),
        "nur_installiert": sorted(ist.keys() - soll.keys()),
        "abweichendes_sql": sorted(k for k in soll.keys() & ist.keys() if soll[k] != ist[k]),
    }


def bericht(ergebnis: dict) -> str:
    if not any(ergebnis.values()):
        return "schemastand: keine Abweichung -- schema.sql und die installierte Datenbank stimmen ueberein."
    zeilen = ["schemastand: Abweichungen zwischen schema.sql (SOLL) und der installierten Datenbank (IST)"]
    if ergebnis["nur_in_schema_sql"]:
        zeilen.append(f"  in schema.sql, aber NICHT installiert ({len(ergebnis['nur_in_schema_sql'])}):")
        zeilen += [f"    - {t} {n}" for t, n in ergebnis["nur_in_schema_sql"]]
    if ergebnis["nur_installiert"]:
        zeilen.append(f"  installiert, aber NICHT in schema.sql ({len(ergebnis['nur_installiert'])}):")
        zeilen += [f"    - {t} {n}" for t, n in ergebnis["nur_installiert"]]
    if ergebnis["abweichendes_sql"]:
        zeilen.append(f"  beidseitig vorhanden, ABWEICHENDES SQL ({len(ergebnis['abweichendes_sql'])}):")
        zeilen += [f"    - {t} {n}" for t, n in ergebnis["abweichendes_sql"]]
    return "\n".join(zeilen)


def _selftest() -> None:
    import shutil

    tmp = Path(tempfile.mkdtemp())

    # 1) Negativfall: exakt aus schema.sql angelegt -> keine Meldung.
    exakt = tmp / "exakt.db"
    with speicher.schreiben(exakt) as conn:
        conn.executescript(SCHEMA_PFAD.read_text(encoding="utf-8"))
    ergebnis = vergleich(db=exakt)
    assert not any(ergebnis.values()), f"exakter Nachbau meldet faelschlich: {ergebnis}"

    # 2) Historischer Fall (L-55075a): ein Trigger installiert, dessen SQL
    #    von schema.sql abweicht -- muss NAMENTLICH als 'abweichendes_sql'
    #    erscheinen, nicht bloss als vorhanden gelten.
    abweichend = tmp / "abweichend.db"
    shutil.copy(exakt, abweichend)
    with speicher.schreiben(abweichend) as conn:
        conn.execute("DROP TRIGGER knowledge_ad")
        conn.execute(
            "CREATE TRIGGER knowledge_ad AFTER DELETE ON knowledge_nodes BEGIN "
            "SELECT 1; END"  # inhaltlich verstuemmelt: loescht die FTS-Zeile nicht mehr
        )
    ergebnis = vergleich(db=abweichend)
    assert ("trigger", "knowledge_ad") in ergebnis["abweichendes_sql"], ergebnis
    assert ("trigger", "knowledge_ad") not in ergebnis["nur_installiert"], (
        "als 'nur_installiert' statt als 'abweichendes_sql' gemeldet -- falsche Klasse"
    )

    # 3) Erstanlage-Luecke: ein Trigger fehlt installiert komplett.
    luecke = tmp / "luecke.db"
    shutil.copy(exakt, luecke)
    with speicher.schreiben(luecke) as conn:
        conn.execute("DROP TRIGGER knowledge_ad")
    ergebnis = vergleich(db=luecke)
    assert ("trigger", "knowledge_ad") in ergebnis["nur_in_schema_sql"], ergebnis

    # 4) Gewachsener Ueberhang: ein Objekt installiert, das schema.sql nicht kennt.
    ueberhang = tmp / "ueberhang.db"
    shutil.copy(exakt, ueberhang)
    with speicher.schreiben(ueberhang) as conn:
        conn.execute("CREATE TABLE gewachsen (id INTEGER PRIMARY KEY)")
    ergebnis = vergleich(db=ueberhang)
    assert ("table", "gewachsen") in ergebnis["nur_installiert"], ergebnis

    # 5) Grenzwert, Seite A: nur Leerraum abweichend -> KEINE Meldung.
    nur_leerraum = tmp / "nur_leerraum.db"
    shutil.copy(exakt, nur_leerraum)
    with speicher.schreiben(nur_leerraum) as conn:
        conn.execute("DROP INDEX idx_nodes_path")
        conn.execute("CREATE   INDEX   idx_nodes_path ON knowledge_nodes(path)")
    ergebnis = vergleich(db=nur_leerraum)
    assert ("index", "idx_nodes_path") not in ergebnis["abweichendes_sql"], (
        "reine Leerraum-Abweichung faelschlich gemeldet: " + str(ergebnis)
    )

    # 5b) Grenzwert, Seite B: nur Gross-/Kleinschreibung abweichend -> WIRD gemeldet.
    nur_gross = tmp / "nur_gross.db"
    shutil.copy(exakt, nur_gross)
    with speicher.schreiben(nur_gross) as conn:
        conn.execute("DROP INDEX idx_nodes_path")
        conn.execute("CREATE INDEX idx_nodes_path ON KNOWLEDGE_NODES(path)")
    ergebnis = vergleich(db=nur_gross)
    assert ("index", "idx_nodes_path") in ergebnis["abweichendes_sql"], (
        "reine Gross-/Kleinschreib-Abweichung nicht gemeldet: " + str(ergebnis)
    )

    print("selftest ok (5 Faelle, Negativfall + Grenzwert beidseitig)", file=sys.stderr)


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
