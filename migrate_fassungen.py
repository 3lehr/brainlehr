#!/usr/bin/env python3
"""migrate_fassungen.py -- zieht die Live-DB auf schema.sql nach: Tabelle
knowledge_fassungen, Index und Trigger knowledge_fassung_au.

Warum ueberhaupt: `knowledge_versions` traegt (id, version) und 2029 Zeilen,
alle auf 1 -- ein Zaehler, keine Historie. Ein UPDATE auf title/summary/
content/tags war damit endgueltig. Aufgefallen, als 384 Knoten maschinell
umgeschrieben werden sollten (docs/PLAN_UMSCHRIFT_2026-08-09.md).

schema.sql wirkt nur auf eine NEU erstellte Datei -- CREATE TABLE IF NOT
EXISTS greift bei vorhandener DB nicht fuer neue Objekte, die dort noch
fehlen (L-636a44). Ohne diesen Lauf bliebe die Live-DB ohne Archiv, und zwar
unbemerkt, weil nichts fehlschlaegt: es wird einfach nichts gesichert.

Der Lauf legt NUR an. Er schreibt keine Fassung fuer den Bestand -- was vor
diesem Lauf ueberschrieben wurde, ist weg und laesst sich nicht
rekonstruieren. Genau das steht auch in der Marke in schema_migrations.

Aufruf:
    python3 migrate_fassungen.py [--apply]
    python3 migrate_fassungen.py --selftest
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "haken"))
import ort  # noqa: E402

DDL = [
    """CREATE TABLE IF NOT EXISTS knowledge_fassungen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        node_id TEXT NOT NULL,
        path TEXT NOT NULL,
        title TEXT,
        summary TEXT,
        content TEXT,
        tags TEXT,
        actor TEXT,
        model TEXT,
        session TEXT,
        galt_bis TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_fassungen_node ON knowledge_fassungen(node_id, id DESC)",
    """CREATE TRIGGER IF NOT EXISTS knowledge_fassung_au AFTER UPDATE ON knowledge_nodes
    WHEN COALESCE(OLD.title,'')   <> COALESCE(NEW.title,'')
      OR COALESCE(OLD.summary,'') <> COALESCE(NEW.summary,'')
      OR COALESCE(OLD.content,'') <> COALESCE(NEW.content,'')
      OR COALESCE(OLD.tags,'')    <> COALESCE(NEW.tags,'')
    BEGIN
        INSERT INTO knowledge_fassungen (node_id, path, title, summary, content, tags, actor, model, session)
        VALUES (OLD.id, OLD.path, OLD.title, OLD.summary, OLD.content, OLD.tags, OLD.actor, OLD.model, OLD.session);
    END""",
]


def anwenden(conn: sqlite3.Connection) -> None:
    for sql in DDL:
        conn.execute(sql)
    conn.commit()


def steht_schon(conn: sqlite3.Connection) -> bool:
    return conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE name IN "
        "('knowledge_fassungen','knowledge_fassung_au','idx_fassungen_node')"
    ).fetchone()[0] == 3


def main() -> None:
    conn = sqlite3.connect(ort.DB)
    if steht_schon(conn):
        print(f"{ort.DB}: Fassungshistorie steht bereits, nichts zu tun.")
        conn.close()
        return
    if "--apply" not in sys.argv:
        print(f"{ort.DB}: Fassungshistorie FEHLT. Mit --apply anlegen.")
        conn.close()
        return
    anwenden(conn)
    print(f"{ort.DB}: angelegt -- {steht_schon(conn)}")
    conn.close()


def demo() -> None:
    """Gegenprobe in beide Richtungen plus Negativfall, auf einer
    Wegwerf-DB im Speicher. Rot gegen den Stand vor dieser Migration:
    ohne Trigger bleibt knowledge_fassungen leer."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE knowledge_nodes (id TEXT PRIMARY KEY, path TEXT, title TEXT, "
                 "summary TEXT, content TEXT, tags TEXT, actor TEXT, model TEXT, session TEXT, "
                 "norm_rang INTEGER)")
    conn.execute("INSERT INTO knowledge_nodes VALUES ('n1','/a','Alt','Kurz','Lang','[]','wer','was','s',NULL)")
    conn.commit()
    assert not steht_schon(conn), "Vorzustand: nichts da"
    anwenden(conn)
    assert steht_schon(conn), "nach dem Lauf muessen alle drei Objekte stehen"

    # Vorwaerts: eine echte Textaenderung archiviert die ALTE Fassung.
    conn.execute("UPDATE knowledge_nodes SET title='Neu' WHERE id='n1'")
    r = conn.execute("SELECT title, summary, actor FROM knowledge_fassungen").fetchall()
    assert r == [("Alt", "Kurz", "wer")], f"alte Fassung muss archiviert sein, war {r}"
    assert conn.execute("SELECT title FROM knowledge_nodes WHERE id='n1'").fetchone()[0] == "Neu"

    # Negativfall: ein UPDATE ohne Textaenderung darf NICHTS archivieren --
    # sonst waechst das Archiv bei jedem Zaehler-Update und wird unlesbar.
    conn.execute("UPDATE knowledge_nodes SET norm_rang=3 WHERE id='n1'")
    conn.execute("UPDATE knowledge_nodes SET title='Neu' WHERE id='n1'")
    assert conn.execute("SELECT COUNT(*) FROM knowledge_fassungen").fetchone()[0] == 1, \
        "Update ohne Textaenderung darf keine Fassung erzeugen"

    # Zweite echte Aenderung: Kette waechst, juengste zuerst lesbar.
    conn.execute("UPDATE knowledge_nodes SET content='Laenger' WHERE id='n1'")
    kette = conn.execute("SELECT title, content FROM knowledge_fassungen ORDER BY id DESC").fetchall()
    assert kette == [("Neu", "Lang"), ("Alt", "Lang")], f"Kette falsch: {kette}"

    # Wiederholter Lauf aendert nichts (idempotent).
    anwenden(conn)
    assert conn.execute("SELECT COUNT(*) FROM knowledge_fassungen").fetchone()[0] == 2
    conn.close()
    print("migrate_fassungen.demo ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
    else:
        main()
