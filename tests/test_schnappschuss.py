"""Belege fuer kern/schnappschuss.py -- INT-SNAP-001: ein Lauf liest einen
festgehaltenen Stand, nicht bei jedem Aufruf die gegenwaertige DB.

Sieht der Code anders aus als hier beschrieben: dem Code folgen, Abweichung
melden. Harness-Abweichung ist ein Befund, nicht selbst umgehen.

Alle Tests gegen eine tmp-DB aus schema.sql, nie gegen den echten Bestand."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "kern"))

import schnappschuss  # noqa: E402


def _neue_db(pfad: Path) -> None:
    """Minimale, schema.sql-foermige knowledge_nodes-Tabelle statt des vollen
    Skripts: schema.sql traegt gegen knowledge_nodes ueber 20 BEFORE-INSERT-
    Trigger (Normrang, Freigabe, Gattung, ...), die eine eigene, in diesem
    Auftrag TABU-gebundene Schreibfunktion (kms.knowledge_add) voraussetzen,
    um befuellt zu werden -- siehe tests/conftest.py::
    _norm_entscheidung_test_default. Diese Datei prueft schnappschuss.py,
    nicht die Normrang-Regeln von knowledge_nodes; der Vorgabe-Nachbau in
    tests/test_bestand_schnappschuss.py (dieselbe Truppe) geht denselben
    Weg."""
    conn = sqlite3.connect(str(pfad))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE knowledge_nodes (id TEXT PRIMARY KEY, path TEXT)")
        conn.commit()
    finally:
        conn.close()


def _knoten_einfuegen(pfad: Path, id_: str) -> None:
    conn = sqlite3.connect(str(pfad))
    try:
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path) VALUES (?, ?)",
            (id_, f"/test/{id_}"),
        )
        conn.commit()
    finally:
        conn.close()


def _anzahl_knoten_live(pfad: Path) -> int:
    """Genau der Weg, der OHNE Schnappschuss ueblich ist: mode=ro, aber bei
    JEDEM Aufruf frisch gegen die lebende Datei."""
    conn = sqlite3.connect(f"file:{pfad}?mode=ro", uri=True)
    try:
        return conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    finally:
        conn.close()


def test_rot_ohne_schnappschuss_sieht_zweiter_lesevorgang_die_aenderung(tmp_path):
    """ROT-BELEG (wird durch dieses Modul nicht benutzt, zeigt nur das
    Problem, das es loest): zwei Lesevorgaenge gegen die lebende Datei,
    dazwischen ein Schreibvorgang -- der zweite Lesevorgang sieht die
    Aenderung. Genau das darf gegen einen festgehaltenen Stand NICHT
    passieren (siehe naechster Test)."""
    quelle = tmp_path / "live.db"
    _neue_db(quelle)
    _knoten_einfuegen(quelle, "n1")

    erster = _anzahl_knoten_live(quelle)
    _knoten_einfuegen(quelle, "n2")
    zweiter = _anzahl_knoten_live(quelle)

    assert erster == 1
    assert zweiter == 2, (
        "ROT-BELEG bestaetigt: ohne Schnappschuss aendert sich das Ergebnis "
        "zwischen zwei Lesevorgaengen -- Meldung: erster=1, zweiter=2"
    )


def test_gruen_schnappschuss_ignoriert_spaetere_aenderung(tmp_path):
    """GRUEN-BELEG: derselbe Ablauf, jetzt ueber schnappschuss.festhalten()/
    lesen(). Der zweite Lesevorgang gegen den EINEN festgehaltenen Stand
    darf die Aenderung nicht sehen."""
    quelle = tmp_path / "live.db"
    _neue_db(quelle)
    _knoten_einfuegen(quelle, "n1")

    stand = schnappschuss.festhalten(quelle, tmp_path / "schnappschuesse")
    with schnappschuss.lesen(stand) as conn:
        erster = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]

    _knoten_einfuegen(quelle, "n2")

    with schnappschuss.lesen(stand) as conn:
        zweiter = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]

    assert erster == 1
    assert zweiter == 1, (
        f"GRUEN-BELEG verletzt: Schnappschuss haette die spaetere Aenderung "
        f"nicht sehen duerfen, sah {zweiter} statt 1"
    )


def test_grenzwert_schreibung_genau_vor_festhalten_ist_enthalten(tmp_path):
    """Grenzwertentscheidung: eine Schreibung, die VOR dem Aufruf von
    festhalten() committet ist, gehoert garantiert dazu."""
    quelle = tmp_path / "live.db"
    _neue_db(quelle)
    _knoten_einfuegen(quelle, "genau-davor")  # committet, dann erst festhalten()

    stand = schnappschuss.festhalten(quelle, tmp_path / "schnappschuesse")

    with schnappschuss.lesen(stand) as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM knowledge_nodes WHERE id='genau-davor'"
        ).fetchone()[0]
    assert n == 1, "Schreibung unmittelbar vor festhalten() haette enthalten sein muessen"


def test_negativfall_unbekannte_kennung_meldet_sich_laut(tmp_path):
    """Eine Kennung, die es nicht gibt, liefert einen sprechenden Fehler,
    keine stille Leere und kein neu angelegtes leeres Verzeichnis."""
    try:
        with schnappschuss.lesen("diese-kennung-gibt-es-nicht", tmp_path / "schnappschuesse"):
            pass
        assert False, "unbekannte Kennung haette FileNotFoundError auffangen sollen"
    except FileNotFoundError as exc:
        assert "diese-kennung-gibt-es-nicht" in str(exc)


def test_kennung_als_reine_zeichenkette_reicht_zum_lesen(tmp_path):
    """'lies X gegen genau diesen Stand' muss auch mit NUR der Kennung
    funktionieren (ein anderer Prozess haette kein Schnappschuss-Objekt,
    nur die Zeichenkette)."""
    quelle = tmp_path / "live.db"
    _neue_db(quelle)
    _knoten_einfuegen(quelle, "n1")

    stand = schnappschuss.festhalten(quelle, tmp_path / "schnappschuesse")
    kennung_als_text = stand.kennung
    assert isinstance(kennung_als_text, str)

    with schnappschuss.lesen(kennung_als_text, tmp_path / "schnappschuesse") as conn:
        n = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    assert n == 1


def test_schreibversuch_gegen_schnappschuss_scheitert(tmp_path):
    """mode=ro wie bei kern/speicher.lesen(): ein Schreibversuch scheitert
    sofort und laut, statt still zu gelingen."""
    quelle = tmp_path / "live.db"
    _neue_db(quelle)

    stand = schnappschuss.festhalten(quelle, tmp_path / "schnappschuesse")
    with schnappschuss.lesen(stand) as conn:
        try:
            conn.execute("INSERT INTO knowledge_nodes (id, path) VALUES ('x', '/x')")
            assert False, "Schreibversuch gegen den Schnappschuss haette scheitern muessen"
        except sqlite3.OperationalError:
            pass


def test_selftest_laeuft_durch():
    schnappschuss._selftest()
