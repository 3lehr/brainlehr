"""Ratsche: Wissenseintraege tragen keine absoluten Pfade vom Rechner des
Betreibers -- ausser den einzeln begruendeten Ausnahmen (Klasse B/C).

ANLASS 2026-08-15: 41(spaeter genauer: 39) Wissensknoten und 15(14) Lehren
trugen `<ablage>/<arbeitsbereich>`, `<ablage>/be_old`,
`<ablage>/videoki` oder `/Users/lehrmacbook` im Fliesstext -- ein
Rechnerpfad, der einem zweiten Leser nichts sagt und beim Repo-Umzug bricht.
Vorbild fuer die Bauform: tests/test_naht_ratsche.py.

DREI KLASSEN, nicht zwei -- sonst schlaegt die Ratsche bei jedem Eintrag der
Klasse B (Pfad TRAEGT die Aussage, z.B. der Ort des Agentenregisters) oder
Klasse C (Verweis auf ein fremdes Projekt wie be_old/videoki) an und wird
binnen einer Woche uebergangen. Jede Ausnahme in tests/absolute_pfade_basis.json
traegt deshalb eine Begruendung je Zeile -- eine Ausnahmeliste ohne
Begruendung ist keine.

WAS SIE NICHT KANN: sie prueft nur die vier bekannten Praefixe, nicht jeden
denkbaren absoluten Pfad (kein Check auf /etc, /tmp, /home -- die kommen im
Bestand heute nicht vor). Und sie ist grob je FELD, nicht je Fundstelle: ein
Feld mit einer Klasse-B-Stelle bleibt insgesamt ausgenommen, auch wenn im
selben Feld eine Klasse-A-Stelle stuende. Das ist bewusst so grob wie
naht_basis.json -- Zeilen zu einer Fundstellen-Ratsche gehoert nicht in
dieselbe Klasse.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
from kern import speicher  # noqa: E402

BASIS = WURZEL / "tests" / "absolute_pfade_basis.json"

MUSTER = re.compile(
    r"/(?:Volumes/daten/(?:Begod2026|be_old|videoki)|Users/lehrmacbook)[^\s`'\")]*"
)

NODE_FELDER = ["title", "summary", "content"]
LESSON_FELDER = ["description", "root_cause", "resolution", "prevention", "pruefstelle"]


def gefundene_felder(db: Path | None = None) -> set[tuple[str, str, str]]:
    """(tabelle, id, feld) fuer jedes Feld, das mindestens einen absoluten
    Pfad aus den vier bekannten Praefixen enthaelt."""
    treffer: set[tuple[str, str, str]] = set()
    with speicher.lesen(db) as conn:
        for row in conn.execute(f"SELECT id, {', '.join(NODE_FELDER)} FROM knowledge_nodes"):
            for feld in NODE_FELDER:
                wert = row[feld]
                if isinstance(wert, str) and MUSTER.search(wert):
                    treffer.add(("knowledge_nodes", row["id"], feld))
        try:
            spalten = [r[1] for r in conn.execute("PRAGMA table_info(lessons_learned)")]
        except sqlite3.OperationalError:
            spalten = []
        lesson_felder = [f for f in LESSON_FELDER if f in spalten]
        if lesson_felder:
            for row in conn.execute(
                f"SELECT id, {', '.join(lesson_felder)} FROM lessons_learned"
            ):
                for feld in lesson_felder:
                    wert = row[feld]
                    if isinstance(wert, str) and MUSTER.search(wert):
                        treffer.add(("lessons_learned", row["id"], feld))
    return treffer


def _basis() -> list[dict]:
    return json.loads(BASIS.read_text(encoding="utf-8"))


def _basis_schluessel() -> set[tuple[str, str, str]]:
    return {(e["tabelle"], e["id"], e["feld"]) for e in _basis()}


def test_keine_unbegruendeten_absoluten_pfade():
    ist = gefundene_felder()
    erlaubt = _basis_schluessel()
    neu = sorted(ist - erlaubt)
    assert not neu, (
        "Neue(s) Feld(er) mit absolutem Pfad ohne Begruendung: "
        + ", ".join(f"{t}/{i}.{f}" for t, i, f in neu)
        + " -- entweder den Pfad relativ zum Verbund machen (Klasse A) oder "
        "mit Begruendung in tests/absolute_pfade_basis.json eintragen "
        "(Klasse B/C)."
    )


def test_basis_bleibt_ehrlich():
    """Gegenprobe: eine Ausnahme, deren Feld inzwischen keinen absoluten Pfad
    mehr traegt (weil jemand es doch bereinigt hat), muss aus der Basis
    verschwinden -- sonst waechst der Spielraum still mit jeder Bereinigung."""
    ist = gefundene_felder()
    erlaubt = _basis_schluessel()
    erledigt = sorted(erlaubt - ist)
    assert not erledigt, (
        "Diese Ausnahmen stehen noch in tests/absolute_pfade_basis.json, ihr "
        "Feld traegt aber keinen absoluten Pfad mehr: "
        + ", ".join(f"{t}/{i}.{f}" for t, i, f in erledigt)
        + " -- aus der Basis streichen."
    )


def test_jede_ausnahme_hat_begruendung_und_klasse():
    for eintrag in _basis():
        assert eintrag.get("klasse") in ("B", "C"), eintrag
        assert eintrag.get("begruendung", "").strip(), (
            f"Ausnahme ohne Begruendung: {eintrag}"
        )


def _leere_testdb() -> Path:
    """Minimale Testkulisse -- nur die Spalten, die gefundene_felder() liest.
    Bewusst NICHT das volle schema.sql (dessen Normen-Trigger verlangen
    Felder, die mit dieser Ratsche nichts zu tun haben)."""
    tmp = Path(tempfile.mkdtemp())
    db = tmp / "probe.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE knowledge_nodes (id TEXT PRIMARY KEY, title TEXT, "
        "summary TEXT, content TEXT)"
    )
    conn.commit()
    conn.close()
    return db


def test_gegenprobe_beide_richtungen():
    """ROT VOR GRUEN, unabhaengig vom Produktivbestand: ein neuer absoluter
    Pfad in einer frischen Datenbank faellt auf; ein als Klasse-B markierter
    Fall (hier simuliert per eigener Basis-Datei) geht durch."""
    db = _leere_testdb()
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO knowledge_nodes (id, title, summary, content) VALUES "
        "('t-leck', 'Leck', 's', "
        "'Datei liegt unter /Volumes/daten/Begod2026/irgendwas.py')"
    )
    conn.execute(
        "INSERT INTO knowledge_nodes (id, title, summary, content) VALUES "
        "('t-b', 'Registerort', 's', "
        "'Massgeblich ist /Volumes/daten/Begod2026/hub/laufzeit/agent-register.jsonl, "
        "nicht raten.')"
    )
    conn.commit()
    conn.close()

    ist = gefundene_felder(db)
    # Beide Zeilen tragen einen absoluten Pfad -- die reine Erkennung sieht
    # (noch) keinen Unterschied zwischen A/B/C, das leistet erst die Basis.
    assert ("knowledge_nodes", "t-leck", "content") in ist
    assert ("knowledge_nodes", "t-b", "content") in ist

    # Nur wer in einer Basis-Datei mit Begruendung steht, gilt als gedeckt --
    # hier simuliert durch denselben Vergleich wie test_keine_unbegruendeten:
    erlaubt_simuliert = {("knowledge_nodes", "t-b", "content")}
    neu = ist - erlaubt_simuliert
    assert neu == {("knowledge_nodes", "t-leck", "content")}, (
        "Gegenprobe fehlgeschlagen: der neue Leck-Fall haette allein durchfallen "
        "muessen, der als Ausnahme gefuehrte Registerort-Fall haette durchgehen muessen."
    )


if __name__ == "__main__":
    import subprocess

    subprocess.run(["python3", "-m", "pytest", "-q", str(Path(__file__))])
