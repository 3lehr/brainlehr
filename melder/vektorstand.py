#!/usr/bin/env python3
"""Ein Vektor, der einen Text beschreibt, den es so nicht mehr gibt -- und
niemand fragt danach.

ANLASS, 2026-08-11: knowledge_embeddings fuehrt je Zeile text_checksum, eine
sha256 ueber genau den Text, der eingebettet wurde (siehe build_embeddings.py).
Gemessen: 0 von 2121 Knoten und 0 von 748 Lehren haben GAR KEINE Einbettung --
das Nachziehen funktioniert. Aber 28 von 2121 Knoten tragen einen VERALTETEN
Vektor: ihr heutiger Text ergibt eine andere Pruefsumme als die gespeicherte.
Fuer diesen Zustand gab es keinen Melder -- die Pruefsumme wird beim Schreiben
ausgewertet, aber niemand fragt im Bestand nach.

ZWEI FRAGEN, GETRENNT, fuer Knoten UND Lehren:
  - wie viele Eintraege haben GAR KEINE Einbettung (keine Zeile in
    knowledge_embeddings fuer irgendeinen ihrer Zielbereiche)
  - wie viele haben eine, deren Pruefsumme NICHT MEHR PASST (Modell oder Text
    haben sich seit dem letzten Lauf geaendert)

Die Textzusammensetzung wird hier NICHT abgeschrieben, sondern aus
build_embeddings.node_text()/lesson_text() importiert -- sonst gibt es zwei
Stellen, die behaupten zu wissen, was eingebettet wurde, und sie koennten
auseinanderlaufen.

Aufruf:
    python3 vektorstand.py --pruefen     # Zahlen fuer Knoten und Lehren
    python3 vektorstand.py --melder      # nur sprechen, wenn etwas fehlt/veraltet ist
    python3 vektorstand.py --selftest
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "haken"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "kern"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import speicher  # noqa: E402 -- eine Tuer zur Datenbank statt einer eigenen
import build_embeddings  # noqa: E402 -- eine Wahrheit ueber den Einbettungstext
import embeddings  # noqa: E402 -- fuer das erwartete Modell


def _zeilenstatus(conn: sqlite3.Connection, kind: str, ref_id, project_ids: list[str],
                   model: str, checksum: str) -> str:
    """'fehlt': fuer KEINEN Zielbereich existiert eine Zeile in knowledge_embeddings.
    'veraltet': mindestens eine Zeile existiert, aber Modell oder Pruefsumme weichen
    von dem ab, was der heutige Text ergibt.
    'ok': jede Zielbereichs-Zeile passt."""
    zeilen = [
        conn.execute(
            "SELECT model, text_checksum FROM knowledge_embeddings "
            "WHERE kind = ? AND ref_id = ? AND project_id = ?",
            (kind, ref_id, pid),
        ).fetchone()
        for pid in project_ids
    ]
    if all(z is None for z in zeilen):
        return "fehlt"
    if any(z is None or z[0] != model or z[1] != checksum for z in zeilen):
        return "veraltet"
    return "ok"


def pruefen(conn: sqlite3.Connection | None = None) -> dict:
    """Zaehlt fehlende/veraltete Vektoren fuer Knoten und Lehren, getrennt.
    Jede Zahl hat ihren Nenner (Gesamtzahl der Eintraege der jeweiligen Art)."""
    if conn is not None:
        return _pruefen_mit(conn)
    with speicher.lesen() as eigene:
        return _pruefen_mit(eigene)


def _pruefen_mit(conn: sqlite3.Connection) -> dict:
    model = embeddings.DEFAULT_EMBED_MODEL

    nodes = conn.execute(
        "SELECT id, path, project_id, title, summary, content FROM knowledge_nodes"
    ).fetchall()
    knoten_fehlt = knoten_veraltet = 0
    for n in nodes:
        checksum = build_embeddings._text_checksum(build_embeddings.node_text(n))
        status = _zeilenstatus(conn, "node", n["id"], [n["project_id"]], model, checksum)
        if status == "fehlt":
            knoten_fehlt += 1
        elif status == "veraltet":
            knoten_veraltet += 1

    lessons = conn.execute(
        "SELECT id, node_path, projects, description, root_cause, prevention FROM lessons_learned"
    ).fetchall()
    lehren_fehlt = lehren_veraltet = 0
    for l in lessons:
        checksum = build_embeddings._text_checksum(build_embeddings.lesson_text(l))
        ziele = build_embeddings.resolve_lesson_projects(l["projects"])
        status = _zeilenstatus(conn, "lesson", l["id"], ziele, model, checksum)
        if status == "fehlt":
            lehren_fehlt += 1
        elif status == "veraltet":
            lehren_veraltet += 1

    return {
        "knoten_gesamt": len(nodes), "knoten_fehlt": knoten_fehlt, "knoten_veraltet": knoten_veraltet,
        "lehren_gesamt": len(lessons), "lehren_fehlt": lehren_fehlt, "lehren_veraltet": lehren_veraltet,
    }


def melden(conn: sqlite3.Connection | None = None) -> dict | None:
    """URTEIL im Sinne von pruefer.py. FEHLKLASSE: ein Vektor beschreibt einen
    Text, den es so nicht mehr gibt -- die Suche liefert gegen den alten
    Stand, nicht gegen den aktuellen Eintrag.
    PREIS EINES FEHLALARMS: keiner -- die Pruefsumme wird mit derselben
    Funktion gebildet wie beim Schreiben (build_embeddings.node_text() /
    lesson_text()), keine eigene Ratekette, die abweichen koennte."""
    e = pruefen(conn)
    gesamt = e["knoten_fehlt"] + e["knoten_veraltet"] + e["lehren_fehlt"] + e["lehren_veraltet"]
    if gesamt == 0:
        return None
    return {
        "pruefung": "vektorstand:fehlende_oder_veraltete_einbettungen",
        "befund": (
            f"Knoten: {e['knoten_fehlt']}/{e['knoten_gesamt']} ohne Einbettung, "
            f"{e['knoten_veraltet']}/{e['knoten_gesamt']} mit veralteter Pruefsumme. "
            f"Lehren: {e['lehren_fehlt']}/{e['lehren_gesamt']} ohne Einbettung, "
            f"{e['lehren_veraltet']}/{e['lehren_gesamt']} mit veralteter Pruefsumme."
        ),
        "fehlklasse": "Vektor beschreibt einen Text, den es so nicht mehr gibt -- "
                      "die Suche liefert gegen den alten Stand, nicht gegen den aktuellen Eintrag",
        "fehlalarm_kostet": "keiner: dieselbe Pruefsummenfunktion wie beim Schreiben, "
                             "keine eigene Ratekette",
    }


def _selftest() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE knowledge_nodes (id INTEGER PRIMARY KEY, path TEXT, project_id TEXT, "
        "title TEXT, summary TEXT, content TEXT)"
    )
    conn.execute(
        "CREATE TABLE lessons_learned (id INTEGER PRIMARY KEY, node_path TEXT, projects TEXT, "
        "description TEXT, root_cause TEXT, prevention TEXT)"
    )
    conn.execute(
        "CREATE TABLE knowledge_embeddings (kind TEXT, ref_id TEXT, project_id TEXT, "
        "model TEXT, text_checksum TEXT)"
    )

    model = embeddings.DEFAULT_EMBED_MODEL

    # 1) Knoten mit passender Pruefsumme -> NICHT gemeldet.
    conn.execute("INSERT INTO knowledge_nodes VALUES (1, 'p/aktuell', 'shared', 'T1', 'S1', 'C1')")
    row1 = conn.execute("SELECT * FROM knowledge_nodes WHERE id=1").fetchone()
    checksum1 = build_embeddings._text_checksum(build_embeddings.node_text(row1))
    conn.execute("INSERT INTO knowledge_embeddings VALUES ('node', '1', 'shared', ?, ?)",
                 (model, checksum1))

    # 2) Knoten mit GEAENDERTER Pruefsumme (Text wurde seither editiert) -> "veraltet".
    conn.execute("INSERT INTO knowledge_nodes VALUES (2, 'p/geaendert', 'shared', 'T2-neu', 'S2', 'C2')")
    conn.execute("INSERT INTO knowledge_embeddings VALUES ('node', '2', 'shared', ?, 'alte-pruefsumme-passt-nicht-mehr')",
                 (model,))

    # 3) Knoten ganz OHNE Einbettung -> "fehlt", eigene Kategorie.
    conn.execute("INSERT INTO knowledge_nodes VALUES (3, 'p/neu', 'shared', 'T3', 'S3', 'C3')")

    r = pruefen(conn)
    assert r["knoten_gesamt"] == 3, r
    assert r["knoten_fehlt"] == 1, r
    assert r["knoten_veraltet"] == 1, r

    # 4) Gegenprobe: ein sauberer Bestand (nur Fall 1) laesst den Melder schweigen.
    sauber = sqlite3.connect(":memory:")
    sauber.row_factory = sqlite3.Row
    sauber.execute(
        "CREATE TABLE knowledge_nodes (id INTEGER PRIMARY KEY, path TEXT, project_id TEXT, "
        "title TEXT, summary TEXT, content TEXT)"
    )
    sauber.execute(
        "CREATE TABLE lessons_learned (id INTEGER PRIMARY KEY, node_path TEXT, projects TEXT, "
        "description TEXT, root_cause TEXT, prevention TEXT)"
    )
    sauber.execute(
        "CREATE TABLE knowledge_embeddings (kind TEXT, ref_id TEXT, project_id TEXT, "
        "model TEXT, text_checksum TEXT)"
    )
    sauber.execute("INSERT INTO knowledge_nodes VALUES (1, 'p/aktuell', 'shared', 'T1', 'S1', 'C1')")
    row1b = sauber.execute("SELECT * FROM knowledge_nodes WHERE id=1").fetchone()
    checksum1b = build_embeddings._text_checksum(build_embeddings.node_text(row1b))
    sauber.execute("INSERT INTO knowledge_embeddings VALUES ('node', '1', 'shared', ?, ?)",
                    (model, checksum1b))
    assert melden(sauber) is None, "ein sauberer Bestand darf den Melder nicht ausloesen"

    # 5) Der verunreinigte Bestand loest den Melder aus, mit Nenner je Kategorie.
    m = melden(conn)
    assert m is not None
    assert "1/3" in m["befund"] and m["fehlklasse"] and m["fehlalarm_kostet"], m

    print("selftest ok (5 Faelle, Gegenprobe in beide Richtungen)", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pruefen", action="store_true", help="Zahlen fuer Knoten und Lehren ausgeben")
    p.add_argument("--melder", action="store_true", help="nur sprechen, wenn etwas fehlt/veraltet ist")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    if a.melder:
        m = melden()
        if m:
            print(f"⚠️ Vektorstand: {m['befund']} ({m['fehlklasse']})")
        return

    e = pruefen()
    print(f"Knoten: {e['knoten_gesamt']} gesamt, {e['knoten_fehlt']} ohne Einbettung, "
          f"{e['knoten_veraltet']} mit veralteter Pruefsumme")
    print(f"Lehren: {e['lehren_gesamt']} gesamt, {e['lehren_fehlt']} ohne Einbettung, "
          f"{e['lehren_veraltet']} mit veralteter Pruefsumme")
    gesamt = e["knoten_fehlt"] + e["knoten_veraltet"] + e["lehren_fehlt"] + e["lehren_veraltet"]
    sys.exit(1 if gesamt else 0)


if __name__ == "__main__":
    main()
