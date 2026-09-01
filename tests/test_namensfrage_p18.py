"""P18 (docs/PLAN_NAECHSTE_STUFE_2026-08-21.md, docs/REQUIREMENTS_BRAINLEHR.md):
eine natuerliche Namensfrage ("zeige mir alles was mit Frau X zu tun hat")
soll dieselben Ziele finden wie der blosse Name -- gemessen brach das an der
Anrede ("Frau"), die den Namen im Satz-OR verduennte und einen ANDEREN
Knoten (Frau Elvira Quenzelbach) vorzog.

ROT VOR GRUEN (gegen 2c37048f, unveraendert): kern/suchpfad_abruf.kandidaten()
lieferte fuer "zeige mir alles was mit Frau Döldissen zu tun hat" nur 1 von 3
bekannten Zielen (/frontend/buckeberg-design-guide-apple-hig), fuer den
blossen Namen "Döldissen" alle 3. runs/namensfrage_2026-08-21.json haelt den
rohen Lauf fest. test_realer_bestand_natuerliche_frage_findet_alle_drei_ziele
unten reproduziert das GRUEN und beweist per Mutation (namensfrage.eigennamen
stillgelegt), dass der Namensweg die Ursache ist, nicht ein DB-Zufall.
"""
from __future__ import annotations

import sqlite3
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "kern"), str(ROOT / "haken")]

import namensfrage  # noqa: E402
import ort  # noqa: E402
import suchpfad_abruf as sa  # noqa: E402

ZIELE = (
    "/frontend/buckeberg-design-guide-apple-hig",
    "/ops/buckeberg-absenderrolle-und-empfaenger",
    "/ops/buckeberg-zehn-einheiten-sind-in-jedem",
)


def test_negativtest_sachfrage_wird_nicht_als_namensfrage_behandelt():
    """Ein grossgeschriebenes deutsches Substantiv mitten im Satz ist kein
    Name -- die Anrede fehlt, also darf nichts erkannt werden. Und ein
    Grossbuchstabe am Satzanfang allein macht ebenfalls keinen Namen."""
    assert namensfrage.eigennamen("wie funktioniert die Herkunftsschranke") == []
    assert namensfrage.eigennamen("Wie geht es Ihnen") == []


def test_anrede_markiert_namen_ohne_selbst_gesucht_zu_werden():
    assert namensfrage.eigennamen(
        "zeige mir alles was mit Frau Döldissen zu tun hat") == ["Döldissen"]
    assert "Frau" not in namensfrage.eigennamen("Frau Döldissen kommt")


@pytest.mark.skipif(
    os.environ.get("BRAINLEHR_RUN_LIVE") != "1",
    reason="requires the explicitly selected live corpus; fresh partitions contain no corpus",
)
def test_realer_bestand_natuerliche_frage_findet_alle_drei_ziele():
    """AC1: dieselbe Frage in natuerlicher Form liefert dieselben Ziele wie
    der blosse Name -- 3 von 3, ueber den Produktivweg (suchpfad_abruf.
    kandidaten(), query_vec=None spart den Ollama-Aufruf, der Namensweg
    braucht ihn nicht)."""
    conn = sqlite3.connect(f"file:{ort.DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    nodes_name, _ = sa.kandidaten(conn, "Döldissen", None, 17)
    pfade_name = {n["path"] for n in nodes_name}
    assert set(ZIELE) <= pfade_name, (
        f"Vorbedingung verletzt: blosser Name muesste alle drei Ziele treffen, traf {pfade_name}")

    nodes_satz, _ = sa.kandidaten(
        conn, "zeige mir alles was mit Frau Döldissen zu tun hat", None, 17)
    pfade_satz = {n["path"] for n in nodes_satz}
    assert set(ZIELE) <= pfade_satz, (
        f"natuerliche Frage sollte wie der blosse Name alle drei Ziele treffen, traf nur {pfade_satz}")
    conn.close()


@pytest.mark.skipif(
    os.environ.get("BRAINLEHR_RUN_LIVE") != "1",
    reason="requires the explicitly selected live corpus; fresh partitions contain no corpus",
)
def test_mutationsprobe_ohne_namensweg_faellt_ein_ziel_wieder_raus(monkeypatch):
    """Beweist, dass der Namensweg die Ursache des Gewinns ist (nicht ein
    Zufall des heutigen Bestands): namensfrage.eigennamen() stillgelegt ->
    dieselbe Anfrage, die eben noch 3/3 lieferte, faellt auf den alten,
    verduennten Befund zurueck (rot vor diesem Auftrag, s. Moduldoc)."""
    conn = sqlite3.connect(f"file:{ort.DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    monkeypatch.setattr(sa.namensfrage, "eigennamen", lambda text: [])
    nodes_satz, _ = sa.kandidaten(
        conn, "zeige mir alles was mit Frau Döldissen zu tun hat", None, 17)
    pfade_satz = {n["path"] for n in nodes_satz}
    assert set(ZIELE) - pfade_satz, (
        "ohne Namensweg sollte mindestens ein Ziel wieder fehlen (alter Befund: 2 von 3) -- "
        "wenn nicht, liegt der Gewinn oben an etwas anderem als am Namensweg")
    conn.close()


def _schema_anlegen(conn: sqlite3.Connection) -> None:
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))


@pytest.fixture()
def synthetische_umlaut_db(tmp_path, monkeypatch):
    """POSITIVKONTROLLE (Auftrag P18): eine Namensvariante in zwei
    Schreibweisen (Umlaut/Umschrift) muss denselben Gegenstand finden.
    Im echten Bestand existiert keine solche Doppelschreibung fuer
    'Döldissen' (gemessen 2026-08-21, LIKE '%oeldissen%' liefert 0 Zeilen) --
    darum hier in einer Wegwerf-Testdatenbank hergestellt, nicht im Betrieb.
    Der Knotentext traegt bewusst die ASCII-Umschrift (Doeldissen), die
    Anfrage unten die Umlautform (Döldissen); schema.sql faltet beide beim
    Indizieren/Anfragen auf dieselbe Form (fold_de), s. knowledge_mcp_server.
    fold_de(). knowledge_add() statt Roh-INSERT (wie test_freigabe_suchpfade.py) --
    erspart die volle Constraint-Kette von knowledge_nodes (norm_entscheidung
    und Folgefelder), die fuer diesen Test nichts beitraegt."""
    import knowledge_mcp_server as kms

    db = tmp_path / "namensfrage_umlaut.db"
    conn = sqlite3.connect(db)
    _schema_anlegen(conn)
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db)

    kms.knowledge_add(
        "/", "Testknoten Umschrift", "ein Termin",
        content="Der Termin fuer Herr Doeldissen war am Montag angesetzt.",
        source="test", tags=["synthetisch"],
    )
    # Ablenkung: enthaelt dieselben Fuellwoerter der natuerlichen Frage
    # (zeige/mir/alles/mit/zu/tun/hat) UND die Anrede, aber NICHT den Namen --
    # ohne Namensweg wuerde sie den Zielknoten im bm25-Rang leicht ueberholen.
    kms.knowledge_add(
        "/", "Ablenkungsknoten", "ohne Bezug",
        content=("zeige mir alles was mit Herr Sonstwer zu tun hat, das hat "
                  "mit dem Termin nichts zu tun."),
        source="test", tags=["synthetisch"],
    )

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_umlaut_und_umschrift_finden_denselben_gegenstand(synthetische_umlaut_db):
    conn = synthetische_umlaut_db
    namen = namensfrage.eigennamen("zeige mir alles was mit Herr Döldissen zu tun hat")
    assert namen == ["Döldissen"]

    ziel_pfad = conn.execute(
        "SELECT path FROM knowledge_nodes WHERE title = 'Testknoten Umschrift'"
    ).fetchone()["path"]

    nodes, _ = sa.kandidaten(
        conn, "zeige mir alles was mit Herr Döldissen zu tun hat", None, 17)
    pfade = {n["path"] for n in nodes}
    assert ziel_pfad in pfade, (
        "Umlautform der Anfrage haette den in Umschrift geschriebenen Knoten finden muessen, "
        f"gefunden: {pfade}")
