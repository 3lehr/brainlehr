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

NACHTRAG, 2026-08-15, Frage des Betreibers ("brauchen wir einen Melder fuer
den Vektorraum"): Der Melder existierte schon, war aber an keinem Ereignis
verdrahtet (gemessen: kein Treffer in ~/.claude/settings.json, in keinem
melder/pruefer.py-Import, in keiner SOLLEN_LAUFEN-Liste) -- muss von Hand
aufgerufen werden. Ausserdem deckte er nur zwei von fuenf Teilfragen ab. Die
anderen drei, EINZELN gemessen statt vermutet:
  - Modellwechsel (c): das Modell steht LAENGST je Zeile in der Spalte `model`
    (siehe unten, _zeilenstatus vergleicht z[0] != model) -- die Annahme im
    Auftrag, das sei nicht erfasst, war falsch, gemessen am Schema.
  - Kappung vor dem Einbetten (d): embeddings.wird_gekappt() existierte schon,
    wurde aber nur als Nebenprodukt eines echten (Ollama-aufrufenden) Baulaufs
    ausgegeben, nicht als eigenstaendige, billige Lesepruefung. War eine
    Meldeluecke, keine Datenluecke -- unten ergaenzt.
  - Dimension (e): `dim` steht ebenfalls schon je Zeile, geprueft wurde sie nie
    gegen die tatsaechliche Byteslaenge des Vektors. War ebenfalls eine
    Meldeluecke, keine Datenluecke -- unten ergaenzt.

FUENF FRAGEN, GETRENNT, fuer Knoten UND Lehren:
  - wie viele Eintraege haben GAR KEINE Einbettung (keine Zeile in
    knowledge_embeddings fuer irgendeinen ihrer Zielbereiche)
  - wie viele haben eine, deren Pruefsumme NICHT MEHR PASST (Modell oder Text
    haben sich seit dem letzten Lauf geaendert)
  - wie viele wuerden beim naechsten Bau VOR dem Einbetten GEKAPPT (Text
    laenger als die num_ctx-Zeichengrenze)
  - wie viele gespeicherte Vektoren haben eine DIMENSION, die nicht zur
    eigenen Byteslaenge passt (Korruption) oder vom Rest des Modells abweicht

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

    # Aufgabe 69 (build_embeddings.py) zaehlt das GEKAPPT-Ereignis nur als
    # Nebenprodukt eines echten Baulaufs (ruft Ollama fuer jeden neuen Text).
    # Hier dieselbe Grenzfunktion (embeddings.wird_gekappt) rein textbasiert
    # ausgewertet, ohne ein einziges Modell aufzurufen -- lesend, billig.
    knoten_gekappt = sum(1 for n in nodes if embeddings.wird_gekappt(build_embeddings.node_text(n)))
    lehren_gekappt = sum(1 for l in lessons if embeddings.wird_gekappt(build_embeddings.lesson_text(l)))

    # Dimension: 'dim' und die Byteslaenge des Vektors stehen beide schon in
    # der Zeile -- kein neues Feld, nur ein Vergleich, der bisher niemand zog.
    dim_zeilen = conn.execute(
        "SELECT dim, length(vector) AS vlen FROM knowledge_embeddings WHERE model = ?", (model,)
    ).fetchall()
    dim_korrupt = sum(1 for r in dim_zeilen if r["dim"] is not None and r["dim"] != r["vlen"] // 4)
    dim_werte = sorted({r["dim"] for r in dim_zeilen if r["dim"] is not None})

    return {
        "knoten_gesamt": len(nodes), "knoten_fehlt": knoten_fehlt, "knoten_veraltet": knoten_veraltet,
        "lehren_gesamt": len(lessons), "lehren_fehlt": lehren_fehlt, "lehren_veraltet": lehren_veraltet,
        "knoten_gekappt": knoten_gekappt, "lehren_gekappt": lehren_gekappt,
        "dim_gesamt": len(dim_zeilen), "dim_korrupt": dim_korrupt, "dim_werte": dim_werte,
    }


def melden(conn: sqlite3.Connection | None = None) -> dict | None:
    """URTEIL im Sinne von pruefer.py. FEHLKLASSE: ein Vektor beschreibt einen
    Text, den es so nicht mehr gibt -- die Suche liefert gegen den alten
    Stand, nicht gegen den aktuellen Eintrag.
    PREIS EINES FEHLALARMS: keiner -- die Pruefsumme wird mit derselben
    Funktion gebildet wie beim Schreiben (build_embeddings.node_text() /
    lesson_text()), keine eigene Ratekette, die abweichen koennte."""
    e = pruefen(conn)
    dim_mehrdeutig = 1 if len(e["dim_werte"]) > 1 else 0
    gesamt = (e["knoten_fehlt"] + e["knoten_veraltet"] + e["lehren_fehlt"] + e["lehren_veraltet"]
               + e["knoten_gekappt"] + e["lehren_gekappt"] + e["dim_korrupt"] + dim_mehrdeutig)
    if gesamt == 0:
        return None
    befund = (
        f"Knoten: {e['knoten_fehlt']}/{e['knoten_gesamt']} ohne Einbettung, "
        f"{e['knoten_veraltet']}/{e['knoten_gesamt']} mit veralteter Pruefsumme, "
        f"{e['knoten_gekappt']}/{e['knoten_gesamt']} beim Einbetten gekappt. "
        f"Lehren: {e['lehren_fehlt']}/{e['lehren_gesamt']} ohne Einbettung, "
        f"{e['lehren_veraltet']}/{e['lehren_gesamt']} mit veralteter Pruefsumme, "
        f"{e['lehren_gekappt']}/{e['lehren_gesamt']} beim Einbetten gekappt. "
        f"Vektoren: {e['dim_korrupt']}/{e['dim_gesamt']} mit Dimension ungleich Byteslaenge"
    )
    if dim_mehrdeutig:
        befund += f", verschiedene Dimensionen im selben Modell: {e['dim_werte']}"
    else:
        befund += "."
    return {
        "pruefung": "vektorstand:fehlende_veraltete_gekappte_oder_verkorkste_einbettungen",
        "befund": befund,
        "fehlklasse": "Vektor beschreibt einen Text, den es so nicht mehr gibt, nie gerechnet wurde, "
                      "nur teilweise gerechnet wurde (Kappung vor dem Einbetten) oder mit einer "
                      "Dimension nicht zum Rest des Bestands passt -- die Suche liefert falsch oder "
                      "unvollstaendig, ohne dass irgendwo ein Fehler auftaucht",
        "fehlalarm_kostet": "keiner: dieselbe Pruefsummenfunktion wie beim Schreiben (kein eigenes "
                             "Rateverfahren), Kappungsgrenze und Dimension direkt aus embeddings.py "
                             "bzw. der gespeicherten Zeile, kein geschaetzter Wert",
    }


_SCHEMA = (
    "CREATE TABLE knowledge_nodes (id INTEGER PRIMARY KEY, path TEXT, project_id TEXT, "
    "title TEXT, summary TEXT, content TEXT)",
    "CREATE TABLE lessons_learned (id INTEGER PRIMARY KEY, node_path TEXT, projects TEXT, "
    "description TEXT, root_cause TEXT, prevention TEXT)",
    "CREATE TABLE knowledge_embeddings (kind TEXT, ref_id TEXT, project_id TEXT, "
    "model TEXT, text_checksum TEXT, vector BLOB, dim INTEGER)",
)


def _neue_db() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    for stmt in _SCHEMA:
        c.execute(stmt)
    return c


def _vek(n: int = 4) -> bytes:
    """Ein Vektor der Laenge n, korrekt gepackt -- fuer Zeilen, deren
    Dimension zur eigenen Byteslaenge passen SOLL."""
    return embeddings.pack_embedding([0.1] * n)


def _selftest() -> None:
    conn = _neue_db()
    model = embeddings.DEFAULT_EMBED_MODEL

    # 1) Knoten mit passender Pruefsumme -> NICHT gemeldet.
    conn.execute("INSERT INTO knowledge_nodes VALUES (1, 'p/aktuell', 'shared', 'T1', 'S1', 'C1')")
    row1 = conn.execute("SELECT * FROM knowledge_nodes WHERE id=1").fetchone()
    checksum1 = build_embeddings._text_checksum(build_embeddings.node_text(row1))
    conn.execute("INSERT INTO knowledge_embeddings VALUES ('node', '1', 'shared', ?, ?, ?, 4)",
                 (model, checksum1, _vek()))

    # 2) Knoten mit GEAENDERTER Pruefsumme (Text wurde seither editiert) -> "veraltet".
    conn.execute("INSERT INTO knowledge_nodes VALUES (2, 'p/geaendert', 'shared', 'T2-neu', 'S2', 'C2')")
    conn.execute("INSERT INTO knowledge_embeddings VALUES "
                 "('node', '2', 'shared', ?, 'alte-pruefsumme-passt-nicht-mehr', ?, 4)",
                 (model, _vek()))

    # 3) Knoten ganz OHNE Einbettung -> "fehlt", eigene Kategorie.
    conn.execute("INSERT INTO knowledge_nodes VALUES (3, 'p/neu', 'shared', 'T3', 'S3', 'C3')")

    # 6) Knoten mit passender Pruefsumme, aber Inhalt laenger als die
    # Kappungsgrenze (Aufgabe 69/embeddings.wird_gekappt) -> "gekappt", auch
    # wenn Checksumme und Modell in Ordnung sind.
    lang = "x" * (embeddings.zeichengrenze() + 500)
    conn.execute("INSERT INTO knowledge_nodes VALUES (4, 'p/lang', 'shared', 'T4', 'S4', ?)", (lang,))
    row4 = conn.execute("SELECT * FROM knowledge_nodes WHERE id=4").fetchone()
    checksum4 = build_embeddings._text_checksum(build_embeddings.node_text(row4))
    conn.execute("INSERT INTO knowledge_embeddings VALUES ('node', '4', 'shared', ?, ?, ?, 4)",
                 (model, checksum4, _vek()))

    # 7) Zeile mit KORRUPTER Dimension: dim behauptet 8, der Vektor ist 4 float lang.
    conn.execute("INSERT INTO knowledge_nodes VALUES (5, 'p/korrupt', 'shared', 'T5', 'S5', 'C5')")
    row5 = conn.execute("SELECT * FROM knowledge_nodes WHERE id=5").fetchone()
    checksum5 = build_embeddings._text_checksum(build_embeddings.node_text(row5))
    conn.execute("INSERT INTO knowledge_embeddings VALUES ('node', '5', 'shared', ?, ?, ?, 8)",
                 (model, checksum5, _vek(4)))

    r = pruefen(conn)
    assert r["knoten_gesamt"] == 5, r
    assert r["knoten_fehlt"] == 1, r
    assert r["knoten_veraltet"] == 1, r
    assert r["knoten_gekappt"] == 1, r
    assert r["dim_korrupt"] == 1, r

    # 4) Gegenprobe: ein sauberer Bestand (nur Fall 1) laesst den Melder schweigen --
    # das gilt jetzt fuer ALLE Pruefungen, nicht nur fehlt/veraltet.
    sauber = _neue_db()
    sauber.execute("INSERT INTO knowledge_nodes VALUES (1, 'p/aktuell', 'shared', 'T1', 'S1', 'C1')")
    row1b = sauber.execute("SELECT * FROM knowledge_nodes WHERE id=1").fetchone()
    checksum1b = build_embeddings._text_checksum(build_embeddings.node_text(row1b))
    sauber.execute("INSERT INTO knowledge_embeddings VALUES ('node', '1', 'shared', ?, ?, ?, 4)",
                   (model, checksum1b, _vek()))
    assert melden(sauber) is None, "ein sauberer Bestand darf den Melder nicht ausloesen"

    # 8) Gegenprobe in die andere Richtung: EINE Zeile desselben Modells mit
    # abweichender (aber in sich korrekter) Dimension loest trotzdem aus --
    # das ist kein einzelner korrupter Datensatz, sondern ein Modell, das
    # nicht mehr durchgaengig dieselbe Vektorlaenge liefert.
    mehrdeutig = _neue_db()
    mehrdeutig.execute("INSERT INTO knowledge_nodes VALUES (1, 'p/a', 'shared', 'T1', 'S1', 'C1')")
    mehrdeutig.execute("INSERT INTO knowledge_nodes VALUES (2, 'p/b', 'shared', 'T2', 'S2', 'C2')")
    for rid, n in ((1, 4), (2, 8)):
        row = mehrdeutig.execute("SELECT * FROM knowledge_nodes WHERE id=?", (rid,)).fetchone()
        cs = build_embeddings._text_checksum(build_embeddings.node_text(row))
        mehrdeutig.execute("INSERT INTO knowledge_embeddings VALUES ('node', ?, 'shared', ?, ?, ?, ?)",
                            (str(rid), model, cs, _vek(n), n))
    m_mehrdeutig = melden(mehrdeutig)
    assert m_mehrdeutig is not None, "zwei verschiedene Dimensionen im selben Modell muessen ausloesen"
    assert "verschiedene Dimensionen" in m_mehrdeutig["befund"], m_mehrdeutig

    # 5) Der verunreinigte Bestand loest den Melder aus, mit Nenner je Kategorie.
    m = melden(conn)
    assert m is not None
    assert "1/5" in m["befund"] and m["fehlklasse"] and m["fehlalarm_kostet"], m

    print("selftest ok (8 Faelle inkl. Kappung/Dimension, Gegenprobe in beide Richtungen)",
          file=sys.stderr)


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
          f"{e['knoten_veraltet']} mit veralteter Pruefsumme, {e['knoten_gekappt']} beim Einbetten gekappt")
    print(f"Lehren: {e['lehren_gesamt']} gesamt, {e['lehren_fehlt']} ohne Einbettung, "
          f"{e['lehren_veraltet']} mit veralteter Pruefsumme, {e['lehren_gekappt']} beim Einbetten gekappt")
    print(f"Vektoren: {e['dim_gesamt']} im aktuellen Modell, {e['dim_korrupt']} mit Dimension "
          f"ungleich Byteslaenge, Dimensionen im Bestand: {e['dim_werte']}")
    dim_mehrdeutig = 1 if len(e["dim_werte"]) > 1 else 0
    gesamt = (e["knoten_fehlt"] + e["knoten_veraltet"] + e["lehren_fehlt"] + e["lehren_veraltet"]
              + e["knoten_gekappt"] + e["lehren_gekappt"] + e["dim_korrupt"] + dim_mehrdeutig)
    sys.exit(1 if gesamt else 0)


if __name__ == "__main__":
    main()
