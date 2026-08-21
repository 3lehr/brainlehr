"""Auftrag B1 (docs/PLAN_GESAMTBAU_2026-08-21.md §2): die vier Achsen im Schema.

mandant (wem gehoeren die Daten) · kreis (wer darf sie sehen, BDW-E22) ·
sprache (erkannt, nie geraten, BDW-P10) · Geltung je Kreis als eigene Tabelle
(BDW-E23). Dazu die eine Spalte fuer Strang F (forderung_stand), damit
schema.sql in diesem Zug nur einmal angefasst wird.

BEIDE Ausgangszustaende sind Pflicht -- frisch angelegt UND gewachsen. Der
gewachsene ist der, den der Betrieb hat, und der wird sonst nie gefahren.
Je Achse steht ein Negativtest daneben: eine Spalte, die Falsches annimmt,
traegt keine Zusicherung.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken")]

import sqlite3  # noqa: E402

import pytest  # noqa: E402

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402
import schema_nachzug  # type: ignore  # noqa: E402

ACHSEN = ("mandant", "kreis", "sprache")

# Pflichtfelder eines Knotens, die Trigger erzwingen -- ohne sie scheitert
# jeder INSERT aus einem Grund, der mit diesem Auftrag nichts zu tun hat.
_KNOTEN_SPALTEN = ("id, path, parent_path, level, title, summary, source, "
                   "updated_at, norm_entscheidung, norm_entschieden_von, "
                   "norm_entschieden_grund")
_KNOTEN_WERTE = "'{id}', '{path}', NULL, 0, 't', 's', 'test', 'jetzt', " \
                "'keine_norm', 'skript:test', 'Testvorrichtung'"


def _knoten(conn, ident: str, pfad: str, extra_spalten: str = "",
            extra_werte: str = "") -> None:
    conn.execute(
        f"INSERT INTO knowledge_nodes ({_KNOTEN_SPALTEN}{extra_spalten}) "
        f"VALUES ({_KNOTEN_WERTE.format(id=ident, path=pfad)}{extra_werte})"
    )


def _spalten(conn, tabelle: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({tabelle})")}


@pytest.fixture
def frisch(tmp_path, monkeypatch):
    """Ausgangszustand 1: leere Datei -> ensure_schema."""
    db = tmp_path / "frisch.db"
    # Ohne diesen Griff sichert schema_nachzug beim ersten ALTER die ECHTE
    # Betriebsdatenbank weg -- der Testlauf haette eine Nebenwirkung im
    # Bestand. Gemessen an kms.ensure_schema: nachziehen(conn, db_path=DB_PATH).
    monkeypatch.setattr(kms, "DB_PATH", db)
    conn = sqlite3.connect(db)
    kms.ensure_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def gewachsen(tmp_path, monkeypatch):
    """Ausgangszustand 2: eine Datenbank OHNE die Achsen, mit Bestandszeile.

    Hergestellt, indem die Achsen aus einer vollstaendigen Datenbank wieder
    entfernt werden -- das ist naeher am Betrieb als eine handgebaute
    Minimaltabelle, weil alle Trigger und Indizes drumherum echt bleiben.
    """
    db = tmp_path / "gewachsen.db"
    monkeypatch.setattr(kms, "DB_PATH", db)
    conn = sqlite3.connect(db)
    kms.ensure_schema(conn)
    _knoten(conn, "alt1", "/alt")
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description) "
        "VALUES ('L-alt1', 'insight', 'Bestandslehre')"
    )
    conn.commit()

    for idx in ("idx_nodes_mandant", "idx_nodes_kreis"):
        conn.execute(f"DROP INDEX IF EXISTS {idx}")
    conn.execute("DROP TABLE IF EXISTS geltung_je_kreis")
    # Jeden Trigger wegnehmen, der eine der gleich entfallenden Spalten nennt.
    # SQLite verweigert sonst das DROP COLUMN ("error in trigger ... after drop
    # column"). Ueber den INHALT gesucht statt ueber eine Namensliste: eine
    # Liste altert. Genau daran ist diese Vorrichtung am 2026-08-21 kaputt
    # gegangen, als Strang F die forderung_stand-Trigger einzog -- die
    # Vorrichtung kannte sie nicht, und der Ausgangszustand 'gewachsen' liess
    # sich nicht mehr herstellen. Dieselbe Fehlklasse wie in
    # tests/test_anlass_schema_backfill.py, dort zweimal.
    _entfallend = set(ACHSEN) | {"forderung_stand"}
    for name, sql in conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='trigger'").fetchall():
        if sql and any(f"NEW.{s}" in sql or f"OLD.{s}" in sql for s in _entfallend):
            conn.execute(f"DROP TRIGGER IF EXISTS {name}")
    for tabelle in ("knowledge_nodes", "lessons_learned"):
        for spalte in ACHSEN:
            if spalte in _spalten(conn, tabelle):
                conn.execute(f"ALTER TABLE {tabelle} DROP COLUMN {spalte}")
    if "forderung_stand" in _spalten(conn, "knowledge_nodes"):
        conn.execute("ALTER TABLE knowledge_nodes DROP COLUMN forderung_stand")
    conn.commit()
    yield conn
    conn.close()


# --- Ausgangszustand 1: frisch ------------------------------------------

def test_frisch_traegt_alle_achsen(frisch):
    for tabelle in ("knowledge_nodes", "lessons_learned"):
        fehlt = [s for s in ACHSEN if s not in _spalten(frisch, tabelle)]
        assert not fehlt, f"{tabelle}: {fehlt} fehlen nach ensure_schema"
    assert "forderung_stand" in _spalten(frisch, "knowledge_nodes")

    tabellen = {r[0] for r in frisch.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert "geltung_je_kreis" in tabellen

    indizes = {r[0] for r in frisch.execute(
        "SELECT name FROM sqlite_master WHERE type='index'")}
    assert "idx_nodes_mandant" in indizes and "idx_nodes_kreis" in indizes


def test_frisch_vorgabewerte(frisch):
    _knoten(frisch, "n1", "/x")
    zeile = frisch.execute(
        "SELECT mandant, kreis, sprache, forderung_stand "
        "FROM knowledge_nodes WHERE id='n1'").fetchone()
    assert zeile == ("lokal", "", None, None)


# --- Ausgangszustand 2: gewachsen ---------------------------------------

def test_gewachsen_bekommt_achsen_und_behaelt_bestand(gewachsen):
    for tabelle in ("knowledge_nodes", "lessons_learned"):
        assert not [s for s in ACHSEN if s in _spalten(gewachsen, tabelle)], \
            "Fixture unbrauchbar: Achsen waren vorher schon da"

    kms.ensure_schema(gewachsen)

    for tabelle in ("knowledge_nodes", "lessons_learned"):
        fehlt = [s for s in ACHSEN if s not in _spalten(gewachsen, tabelle)]
        assert not fehlt, f"{tabelle}: {fehlt} nicht nachgezogen"
    assert "forderung_stand" in _spalten(gewachsen, "knowledge_nodes")
    assert "geltung_je_kreis" in {r[0] for r in gewachsen.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}

    knoten = gewachsen.execute(
        "SELECT path, mandant, kreis, sprache FROM knowledge_nodes "
        "WHERE id='alt1'").fetchone()
    assert knoten == ("/alt", "lokal", "", None), knoten
    lehre = gewachsen.execute(
        "SELECT description, mandant, kreis, sprache FROM lessons_learned "
        "WHERE id='L-alt1'").fetchone()
    assert lehre == ("Bestandslehre", "lokal", "", None), lehre


def test_zweiter_lauf_ist_nulldurchgang(gewachsen):
    kms.ensure_schema(gewachsen)
    vor = gewachsen.execute(
        "SELECT * FROM knowledge_nodes WHERE id='alt1'").fetchone()
    schema = (_w / "schema.sql").read_text(encoding="utf-8")
    assert schema_nachzug.nachziehen(gewachsen, schema) == {}, \
        "zweiter Lauf haette Spalten geschrieben"
    kms.ensure_schema(gewachsen)
    assert gewachsen.execute(
        "SELECT * FROM knowledge_nodes WHERE id='alt1'").fetchone() == vor


# --- Negativtest je Achse ------------------------------------------------

@pytest.mark.parametrize("achse", ["mandant", "kreis"])
def test_null_wird_abgelehnt(frisch, achse):
    with pytest.raises(sqlite3.IntegrityError):
        _knoten(frisch, f"n_{achse}", f"/n_{achse}",
                extra_spalten=f", {achse}", extra_werte=", NULL")


@pytest.mark.parametrize("achse", ["mandant", "kreis"])
def test_null_wird_auch_an_lehren_abgelehnt(frisch, achse):
    with pytest.raises(sqlite3.IntegrityError):
        frisch.execute(
            f"INSERT INTO lessons_learned (id, type, description, {achse}) "
            f"VALUES ('L-{achse}', 'insight', 'x', NULL)")


def test_sprache_bleibt_null_statt_geraten(frisch):
    """Kein DEFAULT auf sprache: was nicht erkannt ist, bleibt leer.

    Ein Vorgabewert waere hier geraten -- und ein geratenes 'de' laesst sich
    spaeter nicht mehr von einem erkannten unterscheiden."""
    _knoten(frisch, "n_sp", "/n_sp")
    assert frisch.execute(
        "SELECT sprache FROM knowledge_nodes WHERE id='n_sp'").fetchone()[0] is None

    import spracherkennung  # type: ignore
    assert spracherkennung.erkenne("qwertz zxcvb") is None
    assert spracherkennung.erkenne("") is None
    assert spracherkennung.erkenne(
        "Die Sitzung wurde vertagt, weil der Antrag nicht vorlag.") == "de"
    assert spracherkennung.erkenne(
        "The meeting was adjourned because the motion had not been filed.") == "en"


def _geltung(conn, art: str, ident: str, kreis: str):
    """Was gilt fuer diesen Kreis: der eigene Eintrag, sonst die Spaltenvorgabe.

    Bewusst hier im Test formuliert und nicht im Produktivcode -- B1 baut die
    Achsen, nicht die Auswertung."""
    return conn.execute(
        "SELECT COALESCE(g.gilt_ab, n.gilt_ab), COALESCE(g.gilt_bis, n.gilt_bis) "
        "FROM knowledge_nodes n "
        "LEFT JOIN geltung_je_kreis g "
        "  ON g.eintrag_art = ? AND g.eintrag_id = n.id AND g.kreis = ? "
        "WHERE n.id = ?", (art, kreis, ident)).fetchone()


def test_geltung_je_kreis_wirkt_nur_fuer_ihren_kreis(frisch):
    # norm_befristet statt keine_norm: die Normschicht-Trigger verlangen, dass
    # gilt_ab nur bei gesetztem norm_rang steht. Ohne das scheitert der INSERT
    # aus einem Grund, der mit den Achsen nichts zu tun hat.
    frisch.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, level, title, "
        "summary, source, updated_at, norm_entscheidung, norm_entschieden_von, "
        "norm_entschieden_grund, norm_rang, gilt_ab, gilt_bis) "
        "VALUES ('n_g', '/n_g', NULL, 0, 't', 's', 'test', 'jetzt', "
        "'norm_befristet', 'skript:test', 'Testvorrichtung', 3, "
        "'2026-01-01', '2026-12-31')")
    frisch.execute(
        "INSERT INTO geltung_je_kreis (eintrag_art, eintrag_id, kreis, gilt_ab, gilt_bis) "
        "VALUES ('knoten', 'n_g', 'A', '2026-06-01', '2030-01-01')")

    assert _geltung(frisch, "knoten", "n_g", "A") == ("2026-06-01", "2030-01-01")
    # Der eigentliche Punkt der Tabelle: Kreis B sieht davon nichts.
    assert _geltung(frisch, "knoten", "n_g", "B") == ("2026-01-01", "2026-12-31")
    assert _geltung(frisch, "knoten", "n_g", "") == ("2026-01-01", "2026-12-31")


def test_geltung_je_kreis_ist_je_kreis_einmalig(frisch):
    frisch.execute(
        "INSERT INTO geltung_je_kreis (eintrag_art, eintrag_id, kreis, gilt_ab) "
        "VALUES ('lehre', 'L-1', 'A', '2026-01-01')")
    with pytest.raises(sqlite3.IntegrityError):
        frisch.execute(
            "INSERT INTO geltung_je_kreis (eintrag_art, eintrag_id, kreis, gilt_ab) "
            "VALUES ('lehre', 'L-1', 'A', '2027-01-01')")
    # dieselbe Lehre in einem anderen Kreis ist dagegen erlaubt
    frisch.execute(
        "INSERT INTO geltung_je_kreis (eintrag_art, eintrag_id, kreis, gilt_ab) "
        "VALUES ('lehre', 'L-1', 'B', '2027-01-01')")


def test_gewachsen_bekommt_die_indizes_erst_im_zweiten_lauf(gewachsen):
    """Gemessene Decke, nicht Wunschverhalten -- siehe Kommentar am Ende von
    schema.sql. _ensure_core_schema spielt schema.sql VOR dem Spaltennachzug
    ein; ein CREATE INDEX auf die noch fehlende Spalte bricht ab. Deshalb
    stehen genau diese beiden Zeilen am Dateiende: dort kostet der Abbruch
    nichts weiter. Der Test haelt fest, dass es so und nicht anders ist --
    wer die Reihenfolge im Aufrufer repariert, sieht ihn rot werden und weiss,
    dass er die richtige Stelle getroffen hat."""
    def indizes():
        return {r[0] for r in gewachsen.execute(
            "SELECT name FROM sqlite_master WHERE type='index'")}

    kms.ensure_schema(gewachsen)
    assert "mandant" in _spalten(gewachsen, "knowledge_nodes")
    assert "idx_nodes_mandant" not in indizes()

    kms.ensure_schema(gewachsen)
    assert {"idx_nodes_mandant", "idx_nodes_kreis"} <= indizes()
