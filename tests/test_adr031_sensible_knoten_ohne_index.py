"""ADR-031, Schritt 1 und 2: sensible Knoten stehen NICHT im Volltextindex.

Der Index ist der stille Weg um jede Spaltenverschluesselung herum -- solange
er den Klartext haelt, gibt er ihn heraus, egal was in der Spalte steht
(belegt in tests/test_e07_bestand_im_klartext.py). Deshalb kommt der
Ausschluss VOR der Verschluesselung.

Alle vier Uebergaenge werden geprueft, nicht nur der bequeme:
  anlegen sensibel      -> nie im Index
  anlegen normal        -> im Index (sonst waere die Sperre eine Attrappe)
  normal -> sensibel    -> Eintrag verschwindet
  sensibel -> normal    -> Eintrag entsteht
Die letzten beiden sind der Grund, warum knowledge_au in zwei Trigger
zerfaellt; mit einem einzigen waere genau hier ein beschaedigter Index
entstanden.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))

WORT = "meiershofstrasse"


@pytest.fixture()
def db(tmp_path):
    pfad = tmp_path / "t.db"
    conn = sqlite3.connect(str(pfad))
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    return conn


def _anlegen(conn, node_id: str, sensibel: int) -> None:
    conn.execute(
        "insert into knowledge_nodes (id, path, title, summary, content, "
        "project_id, anlass, norm_entscheidung, norm_entschieden_grund, "
        "norm_entschieden_von, source, sensibel) values (?,?,?,?,?,?,?,?,?,?,?,?)",
        (node_id, "/" + node_id, "Fall", f"WEG-Beschluss {WORT} 12b",
         f"WEG-Beschluss {WORT} 12b", "shared", "skript", "keine_norm",
         "Testfall ADR-031", "test", "erzeugt aus tests/test_adr031_...py",
         sensibel),
    )
    conn.commit()


def _treffer(conn) -> int:
    return conn.execute(
        "select count(*) from knowledge_fts where knowledge_fts match ?", (WORT,)
    ).fetchone()[0]


def test_sensibler_knoten_kommt_nicht_in_den_index(db):
    _anlegen(db, "s1", sensibel=1)
    assert _treffer(db) == 0


def test_normaler_knoten_kommt_sehr_wohl_in_den_index(db):
    """Die Gegenprobe. Ohne sie belegt der Test oben nur, dass die Suche
    nichts findet -- was auch ein kaputter Index waere."""
    _anlegen(db, "n1", sensibel=0)
    assert _treffer(db) == 1


def test_nachtraeglich_sensibel_entfernt_den_eintrag(db):
    _anlegen(db, "n2", sensibel=0)
    assert _treffer(db) == 1
    db.execute("update knowledge_nodes set sensibel = 1 where id = 'n2'")
    db.commit()
    assert _treffer(db) == 0


def test_nachtraeglich_entstuft_legt_den_eintrag_an(db):
    _anlegen(db, "s2", sensibel=1)
    assert _treffer(db) == 0
    db.execute("update knowledge_nodes set sensibel = 0 where id = 's2'")
    db.commit()
    assert _treffer(db) == 1


def test_der_index_bleibt_dabei_heil(db):
    """FTS5 mit externer Inhaltstabelle laesst sich still beschaedigen, wenn
    'delete' mit anderen Werten gerufen wird als beim Indizieren. Ein
    beschaedigter Index faellt sonst erst irgendwann bei einer fremden Suche
    auf -- deshalb hier die eingebaute Pruefung nach allen Uebergaengen."""
    _anlegen(db, "a", sensibel=0)
    _anlegen(db, "b", sensibel=1)
    db.execute("update knowledge_nodes set sensibel = 1 where id = 'a'")
    db.execute("update knowledge_nodes set sensibel = 0 where id = 'b'")
    db.execute("update knowledge_nodes set summary = 'geaendert' where id = 'b'")
    db.execute("delete from knowledge_nodes where id = 'a'")
    db.commit()
    db.execute("insert into knowledge_fts(knowledge_fts) values ('integrity-check')")


def test_vorgabe_ist_nicht_sensibel(db):
    """Wer die Spalte nicht kennt, schreibt weiter wie bisher -- und landet
    im Index. Das ist die richtige Vorgabe: unauffindbar wird nur, was
    ausdruecklich so gemeint ist."""
    db.execute(
        "insert into knowledge_nodes (id, path, title, summary, project_id, "
        "anlass, norm_entscheidung, norm_entschieden_grund, "
        "norm_entschieden_von, source) "
        "values ('v','/v','T',?,'shared','skript','keine_norm','x','test','y')",
        (WORT,))
    db.commit()
    assert db.execute("select sensibel from knowledge_nodes where id='v'").fetchone()[0] == 0
    assert _treffer(db) == 1


# ─── Schritt 2: der Schreibweg verschluesselt wirklich ──────────────────────

import os  # noqa: E402

GEHEIMWORT = "Meiershofstrasse"


@pytest.fixture()
def echter_weg(tmp_path, monkeypatch):
    """Der PRODUKTIVE Weg, nicht ein nachgebauter: knowledge_add/knowledge_read
    gegen eine frische Datenbank und eine eigene Schluesselablage."""
    import knowledge_mcp_server as kms
    sys.path.insert(0, str(WURZEL / "kern"))
    db = tmp_path / "t.db"
    conn = sqlite3.connect(str(db))
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db)
    monkeypatch.setenv("BRAINLEHR_SCHLUESSEL", str(tmp_path / "s.db"))
    return kms, db


def _sensibel_anlegen(kms):
    r = kms.knowledge_add(
        parent_path="/", title="Sensibler Fall", summary=f"WEG-Beschluss {GEHEIMWORT} 12b",
        content=f"Klaegerin wohnhaft {GEHEIMWORT} 12b", anlass="skript",
        norm_entscheidung="keine_norm", norm_entschieden_grund="Testfall",
        source="erzeugt aus tests/test_adr031_...py", sensibel=True)
    assert "error" not in r, r
    return r["id"]


def test_schritt2_kein_klartext_in_der_datei(echter_weg):
    kms, db = echter_weg
    _sensibel_anlegen(kms)
    assert GEHEIMWORT.encode() not in db.read_bytes(), (
        "Klartext in den Rohbytes -- irgendein Weg unter knowledge_add reicht "
        "ihn weiter (Vektor, Hinweisindex, Zugriffsprotokoll, Wikilinks)."
    )


def test_schritt2_gegenprobe_ohne_sensibel_steht_er_drin(echter_weg):
    """Ohne die Gegenprobe belegt der Test oben nur, dass IRGENDETWAS anders
    ist -- etwa dass der Knoten gar nicht geschrieben wurde."""
    kms, db = echter_weg
    r = kms.knowledge_add(
        parent_path="/", title="Normaler Fall", summary=f"WEG-Beschluss {GEHEIMWORT} 12b",
        anlass="skript", norm_entscheidung="keine_norm",
        norm_entschieden_grund="Testfall", source="erzeugt aus tests/...")
    assert "error" not in r, r
    assert GEHEIMWORT.encode() in db.read_bytes()


def test_schritt2_lesen_gibt_den_klartext_zurueck(echter_weg):
    kms, _ = echter_weg
    nid = _sensibel_anlegen(kms)
    gelesen = kms.knowledge_read(nid)
    assert GEHEIMWORT in gelesen["summary"], gelesen
    assert GEHEIMWORT in gelesen["content"], gelesen


def test_schritt2_ohne_schluessel_kein_inhalt_aber_die_tatsache_bleibt(echter_weg):
    """ADR-029 am echten Weg: nach der Schluesselvernichtung ist der Inhalt
    weg, der Knoten aber noch da und sagt, DASS geloescht wurde. Ein blosses
    'nicht gefunden' wuerde die Loeschung selbst verheimlichen."""
    kms, _ = echter_weg
    import schluesselablage
    nid = _sensibel_anlegen(kms)
    assert schluesselablage.vernichten(nid, 1_000_000.0) is True
    gelesen = kms.knowledge_read(nid)
    assert GEHEIMWORT not in gelesen["summary"] + gelesen["content"]
    assert "geloescht" in gelesen["summary"], gelesen["summary"]
    assert gelesen["id"] == nid and gelesen["title"] == "Sensibler Fall"


def test_schritt2_der_schluessel_liegt_nicht_in_der_bestandsdatei(echter_weg):
    """Laege er darin, waere jede Sicherung eine Kopie von Schloss UND
    Schluessel -- und eine Vernichtung aus jeder alten Sicherung wieder
    herstellbar. Genau das soll Crypto-Shredding verhindern."""
    kms, db = echter_weg
    import schluesselablage
    nid = _sensibel_anlegen(kms)
    geheim = schluesselablage.hole(nid)
    assert geheim and len(geheim) == 32
    assert geheim not in db.read_bytes()


def test_schritt2_alle_drei_teile_des_ac_e07_an_einem_fall(echter_weg):
    """BDW-E07-AC1 woertlich: "Daten, Index und Backup eines sensiblen
    Testfalls sind ohne autorisierten Schluessel nicht lesbar." Alle drei in
    EINEM Lauf, damit die Zeile nicht aus drei Teilbelegen zusammengesetzt
    wird, die nie gemeinsam gegolten haben."""
    import shutil
    kms, db = echter_weg
    sys.path.insert(0, str(WURZEL / "kern"))
    import sicherungen
    _sensibel_anlegen(kms)

    # 1 Daten
    assert GEHEIMWORT.encode() not in db.read_bytes()
    # 2 Index
    conn = sqlite3.connect(str(db))
    assert conn.execute(
        "select count(*) from knowledge_fts where knowledge_fts match ?",
        (GEHEIMWORT.lower(),)).fetchone()[0] == 0
    conn.close()
    # 3 Backup
    ziel = sicherungen.sicherungspfad(db, "20260819T230000")
    shutil.copy2(db, ziel)
    assert GEHEIMWORT.encode() not in ziel.read_bytes()


# ─── Schritt 3: der Fristlauf erreicht den Bestand (BDW-E13) ────────────────

def test_schritt3_fristlauf_vernichtet_den_schluessel_und_der_inhalt_ist_weg(echter_weg, tmp_path):
    """Der ganze Kreis in EINEM Lauf: anlegen -> Frist ablaufen lassen ->
    Fristlauf -> lesen. Der Knoten bleibt, der Inhalt ist unwiederbringlich
    weg, und der Nachweis sagt es, ohne ihn zu beschreiben."""
    kms, db = echter_weg
    sys.path.insert(0, str(WURZEL / "kern"))
    import aufbewahrung, schluesselablage

    r = kms.knowledge_add(
        parent_path="/", title="Fristfall", summary=f"WEG-Beschluss {GEHEIMWORT}",
        content="Klaegerin", tags=["datenklasse:rechtsfall"], anlass="skript",
        norm_entscheidung="keine_norm", norm_entschieden_grund="Testfall",
        source="erzeugt aus tests/...", sensibel=True)
    assert "error" not in r, r
    nid = r["id"]

    o = aufbewahrung.Aufbewahrungsordnung()
    o.eintragen(aufbewahrung.Datenklasse("rechtsfall", "WEG-Verfahren", frist_tage=1))

    conn = sqlite3.connect(str(db))
    assert aufbewahrung.sensible_knoten(conn) == {nid: "rechtsfall"}
    nachweis_pfad = tmp_path / "nachweis.jsonl"
    # Zeit als Parameter, nirgends eine Systemuhr: 10 Tage nach Anlage.
    jetzt = schluesselablage.hole(nid) and 0
    import time as _t
    nachweis = aufbewahrung.fristlauf_bestand(conn, o, _t.time() + 10 * 86400,
                                              nachweis_pfad)
    conn.close()

    assert [v["ref"] for v in nachweis["vernichtet"]] == [nid], nachweis
    assert schluesselablage.lage(nid) == "vernichtet"

    gelesen = kms.knowledge_read(nid)
    assert GEHEIMWORT not in gelesen["summary"] + gelesen["content"]
    assert "geloescht" in gelesen["summary"]
    assert gelesen["title"] == "Fristfall", "die Tatsache bleibt (ADR-029)"

    # Der Nachweis beschreibt den Inhalt NICHT.
    text = nachweis_pfad.read_text(encoding="utf-8")
    assert GEHEIMWORT not in text and "Klaegerin" not in text and "Fristfall" not in text


def test_schritt3_legal_hold_haelt_den_fristlauf_an(echter_weg):
    """Die riskante Haelfte aus BDW-E18, hier am echten Weg: solange eine
    Sperre steht, wird nichts vernichtet -- und der Lauf sagt es laut, statt
    still zu ueberspringen."""
    kms, db = echter_weg
    sys.path.insert(0, str(WURZEL / "kern"))
    import aufbewahrung, schluesselablage
    import time as _t

    r = kms.knowledge_add(
        parent_path="/", title="Gehaltener Fall", summary=f"WEG {GEHEIMWORT}",
        tags=["datenklasse:rechtsfall"], anlass="skript",
        norm_entscheidung="keine_norm", norm_entschieden_grund="Testfall",
        source="erzeugt aus tests/...", sensibel=True)
    nid = r["id"]
    schluesselablage.rechtssperre_setzen(nid, "Verfahren 4711 anhaengig", 1.0)

    o = aufbewahrung.Aufbewahrungsordnung()
    o.eintragen(aufbewahrung.Datenklasse("rechtsfall", "WEG-Verfahren", frist_tage=1))
    conn = sqlite3.connect(str(db))
    nachweis = aufbewahrung.fristlauf_bestand(conn, o, _t.time() + 10 * 86400)
    conn.close()

    assert nachweis["vernichtet"] == [], nachweis
    assert [g["ref"] for g in nachweis["gehalten"]] == [nid], nachweis
    assert schluesselablage.lage(nid) == "vorhanden"
    assert GEHEIMWORT in kms.knowledge_read(nid)["summary"]


def test_schritt3_ohne_datenklasse_faellt_der_knoten_auf_ohne_regel(echter_weg):
    """Ein sensibler Knoten ohne Etikett wird SICHTBAR, nicht still einer
    Frist zugeschlagen, die nie jemand fuer ihn entschieden hat (BDW-E12)."""
    kms, db = echter_weg
    sys.path.insert(0, str(WURZEL / "kern"))
    import aufbewahrung
    import time as _t
    nid = _sensibel_anlegen(kms)
    o = aufbewahrung.Aufbewahrungsordnung()
    conn = sqlite3.connect(str(db))
    nachweis = aufbewahrung.fristlauf_bestand(conn, o, _t.time() + 10 * 86400)
    conn.close()
    assert nachweis["ohne_regel"] == [nid], nachweis
    assert nachweis["vernichtet"] == []


def test_schritt3_fristlauf_verweigert_sich_solange_der_index_klartext_haelt(echter_weg):
    """DIE REIHENFOLGE, als Test statt als Absichtserklaerung. Steht ein
    sensibler Knoten noch im Volltextindex, wuerde ein Fristlauf eine
    Loeschung bescheinigen, die nicht stattfindet -- schlimmer als keine
    Loeschung. Nachgestellt, indem der Knoten nachtraeglich in den Index
    geschrieben wird."""
    kms, db = echter_weg
    sys.path.insert(0, str(WURZEL / "kern"))
    import aufbewahrung
    import time as _t
    nid = _sensibel_anlegen(kms)
    conn = sqlite3.connect(str(db))
    rowid = conn.execute("select rowid from knowledge_nodes where id = ?", (nid,)).fetchone()[0]
    conn.execute("insert into knowledge_fts(rowid, summary) values (?, ?)",
                 (rowid, "weg-beschluss meiershofstrasse"))
    conn.commit()
    o = aufbewahrung.Aufbewahrungsordnung()
    with pytest.raises(RuntimeError, match="Volltextindex"):
        aufbewahrung.fristlauf_bestand(conn, o, _t.time() + 10 * 86400)
    conn.close()
