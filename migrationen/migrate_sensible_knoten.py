#!/usr/bin/env python3
"""migrate_sensible_knoten.py -- ADR-031, Schritt 1 und 2 in eine GEWACHSENE
Datenbank ziehen.

schema.sql wirkt nur auf eine neu erstellte Datei. Zwei Fallen, beide hier
schon einmal bezahlt:

1. `CREATE TRIGGER IF NOT EXISTS` ERGAENZT, es ERSETZT NICHT (L-55075a). Der
   alte `knowledge_au` bliebe also stehen und wuerde sensible Knoten weiter
   indizieren -- neben den neuen Triggern, lautlos. Deshalb DROP vor CREATE.
2. Geprueft wird die INSTALLIERTE Fassung (`select sql from sqlite_master`),
   nicht die Datei. Eine Datei sagt nur, was gemeint war.

Idempotent: zweimal laufen aendert nichts und meldet das.

Aufruf:
    python3 migrationen/migrate_sensible_knoten.py            # nur pruefen
    python3 migrationen/migrate_sensible_knoten.py --apply
    python3 migrationen/migrate_sensible_knoten.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken", "melder", "migrationen")]

import re
import sqlite3
import sys
from pathlib import Path

WURZEL = _w


def _trigger_aus_schema(name: str) -> str:
    """Holt den Trigger woertlich aus schema.sql -- damit Migration und
    Erstanlage nie auseinanderlaufen. Eine abgetippte Kopie hier waere die
    naechste Stelle, an der sich beide Fassungen unterscheiden."""
    text = (WURZEL / "schema.sql").read_text(encoding="utf-8")
    m = re.search(r"CREATE TRIGGER IF NOT EXISTS " + name + r"\b.*?\nEND;", text, re.S)
    if not m:
        raise SystemExit(f"Trigger {name} steht nicht in schema.sql")
    return m.group(0)


def _hat_where(conn: sqlite3.Connection) -> bool:
    r = conn.execute(
        "select sql from sqlite_master where name = 'knowledge_au'").fetchone()
    return bool(r) and "old.sensibel" in r[0] and "new.sensibel" in r[0]


def zustand(conn: sqlite3.Connection) -> dict:
    spalten = [r[1] for r in conn.execute("pragma table_info(knowledge_nodes)")]
    trigger = [r[0] for r in conn.execute(
        "select name from sqlite_master where type='trigger' and name like 'knowledge_a%'")]
    return {
        "sensibel": "sensibel" in spalten,
        "chiffre": "chiffre" in spalten,
        "alter_au": "knowledge_au" in trigger and not _hat_where(conn),
        # Erkennungsmerkmal ist der WHERE-Zweig im INSTALLIERTEN Text, nicht
        # der Name -- der Trigger heisst nach wie vor knowledge_au.
        "neue_au": _hat_where(conn),
    }


def wandern(conn: sqlite3.Connection) -> list[str]:
    getan: list[str] = []
    z = zustand(conn)
    if not z["sensibel"]:
        conn.execute("alter table knowledge_nodes add column sensibel INTEGER NOT NULL DEFAULT 0")
        getan.append("Spalte sensibel")
    if not z["chiffre"]:
        conn.execute("alter table knowledge_nodes add column chiffre BLOB")
        getan.append("Spalte chiffre")
    # Die drei Trigger neu setzen: ai/ad tragen jetzt eine WHEN-Bedingung,
    # au zerfaellt in zwei. Erst loeschen, dann anlegen -- IF NOT EXISTS
    # wuerde die alten Fassungen stehen lassen.
    for name in ("knowledge_ai", "knowledge_ad", "knowledge_au",
                 "knowledge_au_del", "knowledge_au_ins"):
        conn.execute(f"drop trigger if exists {name}")
    for name in ("knowledge_ai", "knowledge_ad", "knowledge_au"):
        conn.execute(_trigger_aus_schema(name))
    getan.append("Trigger ai/ad mit WHEN, au mit WHERE je Haelfte")
    conn.commit()
    return getan


def _selftest() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "gewachsen.db"
        conn = sqlite3.connect(str(db))
        # GEWACHSENE Datenbank nachstellen: Schema OHNE die neuen Spalten und
        # mit dem alten knowledge_au -- also der Stand vor dieser Migration.
        alt = (WURZEL / "schema.sql").read_text(encoding="utf-8")
        # Die Spalten stehen seit 2026-08-19 in der CREATE-TABLE-Anweisung
        # (ein blankes ALTER in schema.sql ist nicht wiederholbar, siehe
        # Kommentar dort) -- fuer den GEWACHSENEN Ausgangszustand muessen sie
        # also aus der Tabellendefinition heraus, nicht aus einer ALTER-Zeile.
        alt = alt.replace(
            "    sensibel INTEGER NOT NULL DEFAULT 0,     -- ADR-031: nicht in den Volltextindex\n"
            "    chiffre BLOB,                            -- ADR-031: spaeter der Chiffretext\n", "")
        alt = alt.replace("\nWHEN new.sensibel = 0 BEGIN", " BEGIN")
        alt = alt.replace("\nWHEN old.sensibel = 0 BEGIN", " BEGIN")
        alt = alt.replace("\n    WHERE old.sensibel = 0;", ";")
        alt = alt.replace("\n    WHERE new.sensibel = 0;", ";")
        conn.executescript(alt)
        conn.commit()
        vorher = zustand(conn)
        assert not vorher["sensibel"] and not vorher["neue_au"], vorher

        wandern(conn)
        nachher = zustand(conn)
        assert nachher["sensibel"] and nachher["chiffre"], nachher
        assert nachher["neue_au"] and not nachher["alter_au"], (
            "der alte knowledge_au steht noch -- er wuerde sensible Knoten "
            "weiter indizieren, neben den neuen Triggern: %r" % (nachher,))

        # Die Migration wirkt wirklich, nicht nur formal.
        conn.execute(
            "insert into knowledge_nodes (id,path,title,summary,project_id,anlass,"
            "norm_entscheidung,norm_entschieden_grund,norm_entschieden_von,source,sensibel) "
            "values ('s','/s','T','weg-beschluss geheimwort','shared','skript',"
            "'keine_norm','x','test','y',1)")
        conn.execute(
            "insert into knowledge_nodes (id,path,title,summary,project_id,anlass,"
            "norm_entscheidung,norm_entschieden_grund,norm_entschieden_von,source,sensibel) "
            "values ('n','/n','T','weg-beschluss geheimwort','shared','skript',"
            "'keine_norm','x','test','y',0)")
        conn.commit()
        treffer = conn.execute(
            "select count(*) from knowledge_fts where knowledge_fts match 'geheimwort'"
        ).fetchone()[0]
        assert treffer == 1, f"sensibel und normal muessen sich unterscheiden, war {treffer}"
        conn.execute("insert into knowledge_fts(knowledge_fts) values ('integrity-check')")

        # Zweiter Lauf aendert nichts (idempotent).
        wandern(conn)
        assert zustand(conn) == nachher
        conn.execute("insert into knowledge_fts(knowledge_fts) values ('integrity-check')")
    print("migrate_sensible_knoten: Selbsttest gruen (4 Faelle: Spalten, alter "
          "Trigger weg, Wirkung 1 von 2 indiziert, zweiter Lauf folgenlos)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
        raise SystemExit(0)
    import ort  # noqa: E402
    conn = sqlite3.connect(str(ort.DB))
    z = zustand(conn)
    if "--apply" not in sys.argv:
        print(f"Zustand: {z}\n(nichts geaendert -- mit --apply anwenden)")
        raise SystemExit(0)
    for zeile in wandern(conn):
        print("erledigt:", zeile)
    print("Zustand danach:", zustand(conn))
