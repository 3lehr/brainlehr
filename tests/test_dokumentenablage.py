"""Tests fuer die Dokumentenablage (P15, ADR-032, Auftrag 2026-08-21).

ROT VOR GRUEN, Bezugspunkt 2e81884b: dort gibt es weder die Spalte
`dokument_pfad` noch die Pflicht-Trigger darauf. `test_rot_an_2e81884b_*`
belegt das gegen den ECHTEN Schemastand aus git -- kein Nachbau von Hand, der
beim naechsten Umbau abweichen koennte.

Die Zusicherung, um die es geht, steht in ADR-032: ein Dokumentknoten ohne
Pruefsumme ist "eine Kopie mit Absichtserklaerung". An 2e81884b liess sich
genau so ein Knoten anlegen -- die Spalte existierte nicht, also gab es auch
nichts zu erzwingen.
"""
from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "kern"))

import dokumentenablage as da  # noqa: E402

BEZUG = "2e81884b"
TS = "2026-08-21T12:00:00+0200"


@pytest.fixture()
def frisch(tmp_path, monkeypatch) -> sqlite3.Connection:
    """Ausgangszustand 1 von 2: frisch aus schema.sql angelegt."""
    monkeypatch.setenv(da.ENV_ABLAGE, str(tmp_path / "ablage"))
    conn = sqlite3.connect(str(tmp_path / "frisch.db"))
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    yield conn
    conn.close()


def _datei(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


# --- ROT an 2e81884b -------------------------------------------------------

@pytest.fixture()
def schema_bezug() -> str:
    return subprocess.run(["git", "show", f"{BEZUG}:schema.sql"],
                          cwd=WURZEL, capture_output=True, text=True,
                          check=True).stdout


def test_rot_an_2e81884b_keine_spalte_und_keine_pflicht(tmp_path, schema_bezug):
    """Der Stand vor dem Auftrag kennt weder Spalte noch Trigger. Damit ist
    der Negativfall aus BDW-P15-AC1 dort nicht nur ungeprueft, sondern
    unpruefbar -- und das ist der Befund, nicht der Nebensatz."""
    conn = sqlite3.connect(str(tmp_path / "alt.db"))
    conn.executescript(schema_bezug)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(knowledge_nodes)")}
    assert "dokument_pfad" not in cols
    trg = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE '%dokument%'")}
    assert trg == set()
    conn.close()


def test_rot_an_2e81884b_modul_gibt_es_nicht():
    """Zweiter Suchweg fuer dieselbe negative Existenzaussage (L-39574b):
    nicht nur die Spalte fehlte, das ganze Modul fehlte."""
    r = subprocess.run(["git", "cat-file", "-e", f"{BEZUG}:kern/dokumentenablage.py"],
                       cwd=WURZEL, capture_output=True, text=True)
    assert r.returncode != 0, "kern/dokumentenablage.py existierte bereits an " + BEZUG


# --- BDW-P15-AC1: beide Stellungen, Fund ueber die Zusammenfassung ---------

def _fts_pfade(conn: sqlite3.Connection, wort: str) -> set[str]:
    return {r[0] for r in conn.execute(
        "SELECT path FROM knowledge_fts WHERE knowledge_fts MATCH ?", (f'"{wort}"',))}


def test_ac1_beide_stellungen_und_fund_ueber_zusammenfassung(frisch, tmp_path):
    a = _datei(tmp_path, "vertrag.txt", "Verwaltervertrag\nGrundverguetung 50,00 EUR\n")
    r1 = da.ablegen(frisch, a, domaene="buckeberg", titel="Verwaltervertrag",
                    zusammenfassung="Grundverguetung und Laufzeit der Verwaltung",
                    herkunft="Test", ts=TS)
    assert r1["ort"] == da.ORT_DOMAENE
    assert Path(r1["datei"]) == a.resolve(), "Vorgabe darf die Datei nicht bewegen"
    # gefunden wird ueber ein Wort, das NUR in der Zusammenfassung steht --
    # nicht im Titel, sonst belegte der Treffer den Titelkanal.
    assert r1["knoten"] in _fts_pfade(frisch, "laufzeit")

    b = _datei(tmp_path, "protokoll.txt", "Versammlung\nBeschluss zur Dachsanierung\n")
    da.ort_setzen(frisch, "buckeberg", da.ORT_BRAINLEHR, ts=TS)
    r2 = da.ablegen(frisch, b, domaene="buckeberg", titel="Protokoll 2026",
                    zusammenfassung="Beschluss ueber die Dachsanierung",
                    herkunft="Test", ts=TS)
    assert r2["ort"] == da.ORT_BRAINLEHR
    assert not b.exists() and Path(r2["datei"]).is_file(), "Datei ist nicht gewandert"
    assert str(da.ablage_wurzel()) in r2["datei"]
    assert r2["knoten"] in _fts_pfade(frisch, "dachsanierung")

    # Die Pruefsumme wird in BEIDEN Stellungen gefuehrt -- das ist der Punkt,
    # den die Einstellung ausdruecklich NICHT entscheidet.
    hashes = dict(frisch.execute(
        "SELECT path, quell_hash FROM knowledge_nodes WHERE dokument_pfad IS NOT NULL"))
    assert all(h for h in hashes.values()) and len(hashes) == 2


def test_ac1_negativfall_ohne_quellhash_wird_abgewiesen(frisch, tmp_path):
    a = _datei(tmp_path, "x.txt", "inhalt")
    with pytest.raises(sqlite3.IntegrityError, match="quell_hash fehlt"):
        frisch.execute(
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, level,"
            " source, created_at, updated_at, dokument_pfad, norm_entscheidung,"
            " norm_entschieden_von, norm_entschieden_grund)"
            " VALUES ('x1','/dokumente/x','p','t','s',1,'h',?,?,?,'keine_norm','t','g')",
            (TS, TS, str(a)))


def test_ac1_negativfall_auch_beim_nachtraeglichen_setzen(frisch, tmp_path):
    """Die UPDATE-Fassung ist nicht Zierrat: herkunft_unveraenderlich.sql
    sperrt nur die AENDERUNG eines gesetzten quell_hash, nicht das
    nachtraegliche Anhaengen eines Verweises an einen Knoten ohne Hash."""
    frisch.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, level,"
        " source, created_at, updated_at, norm_entscheidung, norm_entschieden_von,"
        " norm_entschieden_grund)"
        " VALUES ('x2','/ohne/hash','p','t','s',1,'h',?,?,'keine_norm','t','g')", (TS, TS))
    with pytest.raises(sqlite3.IntegrityError, match="quell_hash fehlt"):
        frisch.execute("UPDATE knowledge_nodes SET dokument_pfad = ? WHERE path = '/ohne/hash'",
                       (str(_datei(tmp_path, "y.txt", "inhalt")),))


# --- Gegenprobe in BEIDE Richtungen ---------------------------------------

def test_waechter_schweigt_wenn_nichts_passiert_ist(frisch, tmp_path):
    a = _datei(tmp_path, "still.txt", "unveraendert")
    da.ablegen(frisch, a, domaene="buckeberg", titel="Still",
               zusammenfassung="nichts passiert hier", herkunft="Test", ts=TS)
    assert da.pruefen(frisch) == [], "ein Waechter, der immer anschlaegt, wird weggeklickt"


def test_waechter_meldet_aenderung_und_verlust(frisch, tmp_path):
    a = _datei(tmp_path, "wandel.txt", "Fassung eins")
    r = da.ablegen(frisch, a, domaene="buckeberg", titel="Wandel",
                   zusammenfassung="wird gleich veraendert", herkunft="Test", ts=TS)
    a.write_text("Fassung zwei", encoding="utf-8")
    b = da.pruefen(frisch)
    assert [x["befund"] for x in b] == ["geaendert"] and b[0]["knoten"] == r["knoten"]
    assert b[0]["erwartet"] == r["quell_hash"] and b[0]["ist"] != r["quell_hash"]
    a.unlink()
    assert [x["befund"] for x in da.pruefen(frisch)] == ["fehlt"]


# --- Beteiligte als Gegenstand, nicht als Name im Text (ADR-028) -----------

def test_beteiligte_haengen_an_gegenstand_bezug(frisch, tmp_path):
    a = _datei(tmp_path, "brief.txt", "Schreiben")
    r = da.ablegen(frisch, a, domaene="buckeberg", titel="Schreiben",
                   zusammenfassung="Anschreiben der Verwaltung", herkunft="Test", ts=TS,
                   beteiligte=[{"art": "person", "name": "Doeldissen", "rolle": "verfasst_von"},
                               {"art": "person", "name": "WEG Buckeberg", "rolle": "gerichtet_an"}])
    rollen = {b["rolle"]: b["name"] for b in r["beteiligte"]}
    assert rollen == {"verfasst_von": "Doeldissen", "gerichtet_an": "WEG Buckeberg"}
    gebunden = frisch.execute(
        "SELECT rolle FROM gegenstand_bezug WHERE node_path = ? ORDER BY rolle",
        (r["knoten"],)).fetchall()
    assert [g[0] for g in gebunden] == ["gerichtet_an", "verfasst_von"]
    # Derselbe Name ein zweites Mal legt KEINEN zweiten Gegenstand an --
    # sonst waere die stabile ID wieder ein Name (ADR-028).
    b = _datei(tmp_path, "brief2.txt", "Zweites Schreiben")
    r2 = da.ablegen(frisch, b, domaene="buckeberg", titel="Schreiben 2",
                    zusammenfassung="Zweites Anschreiben", herkunft="Test", ts=TS,
                    beteiligte=[{"art": "person", "name": "Doeldissen", "rolle": "betrifft"}])
    assert r2["beteiligte"][0]["rolle"] == "betrifft"
    ids = {g[0] for g in frisch.execute(
        "SELECT gegenstand_id FROM gegenstand_bezug WHERE rolle IN ('verfasst_von','betrifft')")}
    assert len(ids) == 1, "derselbe Name hat zwei Gegenstaende erzeugt"


# --- Auszug ----------------------------------------------------------------

def test_auszug_erbt_datei_pruefsumme_und_trennung(frisch, tmp_path):
    a = _datei(tmp_path, "prot.txt", "TOP 4: Dachsanierung beschlossen")
    r = da.ablegen(frisch, a, domaene="buckeberg", titel="Protokoll",
                   zusammenfassung="Versammlung 2026", herkunft="Test", ts=TS,
                   mandant="buckeberg", kreis="verwaltung", freigabe="intern")
    p = da.auszug(frisch, r["knoten"], titel="Dachsanierung beschlossen",
                  text="Die Versammlung beschliesst die Dachsanierung einstimmig.",
                  fundstelle="Seite 2, TOP 4", ts=TS)
    row = frisch.execute(
        "SELECT dokument_pfad, quell_hash, parent_path, mandant, kreis, freigabe, source"
        " FROM knowledge_nodes WHERE path = ?", (p,)).fetchone()
    assert row[0] == r["datei"] and row[1] == r["quell_hash"] and row[2] == r["knoten"]
    assert (row[3], row[4], row[5]) == ("buckeberg", "verwaltung", "intern")
    assert "Seite 2, TOP 4" in row[6], "die Fundstelle steht nicht in der Herkunft"


def test_auszug_verlangt_einen_dokumentknoten(frisch):
    frisch.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, level,"
        " source, created_at, updated_at, norm_entscheidung, norm_entschieden_von,"
        " norm_entschieden_grund)"
        " VALUES ('x3','/kein/dokument','p','t','s',1,'h',?,?,'keine_norm','t','g')", (TS, TS))
    with pytest.raises(ValueError, match="kein Dokumentknoten"):
        da.auszug(frisch, "/kein/dokument", titel="t", text="x", fundstelle="s1", ts=TS)


# --- Die Einstellung -------------------------------------------------------

def test_einstellung_vorgabe_ist_domaene_ohne_jede_zeile(frisch):
    assert frisch.execute("SELECT count(*) FROM knowledge_config WHERE key LIKE 'ablage.%'"
                          ).fetchone()[0] == 0
    assert da.ort(frisch, "buckeberg") == "domaene"
    assert da.ort(frisch, "openlehr_einzelunternehmer") == "domaene"


def test_einstellung_ist_je_domaene_und_nicht_je_haus(frisch):
    da.ort_setzen(frisch, "openlehr_einzelunternehmer", da.ORT_BRAINLEHR, ts=TS)
    assert da.ort(frisch, "openlehr_einzelunternehmer") == "brainlehr"
    assert da.ort(frisch, "buckeberg") == "domaene", "die Einstellung hat auf das Haus gewirkt"


def test_einstellung_lehnt_unbekannten_wert_ab(frisch):
    with pytest.raises(ValueError):
        da.ort_setzen(frisch, "buckeberg", "irgendwo", ts=TS)
    frisch.execute("INSERT INTO knowledge_config (key, value, updated_at)"
                   " VALUES ('ablage.buckeberg','irgendwo',?)", (TS,))
    with pytest.raises(ValueError):
        da.ort(frisch, "buckeberg")


# --- Ausgangszustand 2 von 2: die gewachsene Datenbank ---------------------

def test_gewachsene_db_ohne_spalte_bricht_ensure_schema_nicht_ab(tmp_path, monkeypatch,
                                                                schema_bezug):
    """Die FALLE (L-1ffae7): _ensure_core_schema spielt schema.sql per
    executescript ein, BEVOR kern/schema_nachzug.py die Spalte ergaenzt, und
    faengt den OperationalError -- alles hinter der Bruchstelle faellt lautlos
    aus. Darum stehen die beiden Trigger am DATEIENDE.

    Geprueft wird gegen eine Datenbank aus dem ECHTEN Schema von 2e81884b,
    also Trigger und Indizes inhaltsbestimmt mitgeschnitten (L-e12296), nicht
    nachgebaut."""
    sys.path.insert(0, str(WURZEL))
    import knowledge_mcp_server as kms

    db = tmp_path / "gewachsen.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(schema_bezug)
    vor_tab = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    vor_trg = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0]
    vor_idx = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='index'").fetchone()[0]
    assert "dokument_pfad" not in {r[1] for r in conn.execute("PRAGMA table_info(knowledge_nodes)")}
    conn.close()

    monkeypatch.setattr(kms, "DB_PATH", db)
    kms.get_db().close()

    conn = sqlite3.connect(str(db))
    assert "dokument_pfad" in {r[1] for r in conn.execute("PRAGMA table_info(knowledge_nodes)")}
    trg = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE '%dokument%'")}
    assert trg == {"knowledge_nodes_dokument_quellhash_pflicht_bi",
                   "knowledge_nodes_dokument_quellhash_pflicht_bu"}
    # nichts hinter der Bruchstelle verloren
    for art, vorher in (("table", vor_tab), ("trigger", vor_trg), ("index", vor_idx)):
        nachher = conn.execute(
            f"SELECT count(*) FROM sqlite_master WHERE type='{art}'").fetchone()[0]
        assert nachher >= vorher, f"{art}: {vorher} -> {nachher}"

    # und die Ablage laeuft auf dem gewachsenen Bestand genauso.
    monkeypatch.setenv(da.ENV_ABLAGE, str(tmp_path / "ablage"))
    a = _datei(tmp_path, "gewachsen.txt", "Bestandsdokument")
    r = da.ablegen(conn, a, domaene="buckeberg", titel="Bestandsdokument",
                   zusammenfassung="auf einer gewachsenen Datenbank abgelegt",
                   herkunft="Test", ts=TS)
    assert r["quell_hash"] and da.pruefen(conn) == []
    # Der Hash laesst sich nicht nachtraeglich entfernen. Es meldet hier die
    # AELTERE Schranke (herkunft_unveraenderlich.sql, per Anlegereihenfolge
    # zuerst am Zug) und nicht die neue -- gepruefte Beobachtung, nicht
    # Annahme: beide decken denselben Weg ab, und der neue BU-Trigger traegt
    # den Fall, den die alte NICHT kennt (Verweis nachtraeglich an einen
    # Knoten OHNE Hash haengen, siehe
    # test_ac1_negativfall_auch_beim_nachtraeglichen_setzen).
    with pytest.raises(sqlite3.IntegrityError,
                       match="Herkunftsfeld unveraenderlich|quell_hash fehlt"):
        conn.execute("UPDATE knowledge_nodes SET quell_hash = NULL WHERE path = ?",
                     (r["knoten"],))
    conn.close()


# --- Geltung ---------------------------------------------------------------

@pytest.mark.parametrize("gilt_ab,gilt_bis,erwartet", [
    (None, None, ("keine_norm", None)),
    ("2026-01-01", None, ("norm_unbefristet", 4)),
    ("2026-01-01", "2028-12-31", ("norm_befristet", 4)),
])
def test_geltung_passt_zu_den_vorhandenen_normtriggern(frisch, tmp_path,
                                                       gilt_ab, gilt_bis, erwartet):
    a = _datei(tmp_path, f"g{gilt_ab}{gilt_bis}.txt", "inhalt")
    r = da.ablegen(frisch, a, domaene="buckeberg", titel="Geltung",
                   zusammenfassung="mit Geltungszeitraum", herkunft="Test", ts=TS,
                   gilt_ab=gilt_ab, gilt_bis=gilt_bis)
    row = frisch.execute("SELECT norm_entscheidung, norm_rang FROM knowledge_nodes"
                         " WHERE path = ?", (r["knoten"],)).fetchone()
    assert tuple(row) == erwartet


def test_gilt_bis_ohne_gilt_ab_wird_abgelehnt(frisch, tmp_path):
    with pytest.raises(ValueError, match="ab wann"):
        da.ablegen(frisch, _datei(tmp_path, "h.txt", "x"), domaene="buckeberg",
                   titel="t", zusammenfassung="s", herkunft="Test", ts=TS,
                   gilt_bis="2028-12-31")
