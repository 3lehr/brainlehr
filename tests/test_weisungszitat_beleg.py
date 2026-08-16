"""Weisungszitat-Pflicht (Auftrag 2026-08-16, docs/PLAN_VERTRAUENSREGLER_2026-08-16.md
Schritt 1, Knoten a6991a6b): DER FEHLENDE EINGANG. Der Herkunfts-Trigger
(knowledge_nodes_normrang_herkunft_bi/_bu) verlangt fuer Rang 1/2 einen
menschlichen Entscheider -- aber weder knowledge_add() noch knowledge_update()
boten vor diesem Auftrag einen Weg, ihn ABSICHTLICH einzutragen. norm_
entschieden_belegart='weisungszitat' ist dieser Weg, betreiber_weisung=... der
Parameter dazu -- und die neuen Trigger knowledge_nodes_norm_entschieden_
weisungszitat_pflicht_bi/_bu erzwingen, dass die Behauptung ein woertliches
Zitat traegt (deutsches Anfuehrungszeichen „, mindestens 10 Zeichen, dann ").

MERKMAL, KEINE SPERRE (wie art=mensch in kern/ausweis.py, L-33d3bd): geprueft
wird FORM, nicht WAHRHEIT -- siehe Modulkopf von BELEGART_TRIGGERS_SQL in
knowledge_mcp_server.py fuer die volle Einordnung.

ROT VOR GRUEN: vor diesem Auftrag lehnte schon der Wertebereichs-Trigger jeden
belegart='weisungszitat' rundheraus ab (der Wert existierte nicht) --
test_rot_alter_stand_kennt_weisungszitat_nicht reproduziert das gegen die
Schema-Fassung von HEAD^ (git show), nicht gegen eine nachgebaute Kopie.
"""
from __future__ import annotations

import subprocess
import sys as _sys
import sqlite3
from pathlib import Path as _Path

import pytest

ROOT = _Path(__file__).resolve().parents[1]
_sys.path[:0] = [str(ROOT)] + [str(ROOT / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import knowledge_mcp_server as kms  # noqa: E402

SCHEMA_SQL = (ROOT / "schema.sql").read_text(encoding="utf-8")
# Schema-Fassung VOR diesem Auftrag, ueber den Elter des Feature-Commits (git
# show) -- kein selbst nachgebauter Text, der beim naechsten Schema-Umbau
# stillschweigend veraltet (gleiches Muster wie
# tests/test_norm_entschieden_belegart.py::_ALTE_SCHEMA_SQL).
_ALTE_SCHEMA_SQL = subprocess.run(
    ["git", "show", "787ac08e^:schema.sql"], cwd=ROOT, capture_output=True, text=True, check=True,
).stdout


def _frisch(tmp_path: _Path, schema: str = SCHEMA_SQL, name: str = "frisch.db") -> _Path:
    db_path = tmp_path / name
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    return db_path


BASISZEILEN = dict(
    id="n1", path="/x/n1", parent_path="/", project_id="shared",
    title="t", summary="s", content="", level=1, tags="[]",
    source="x", created_at="2026-08-16T10:00:00+02:00", updated_at="2026-08-16T10:00:00+02:00",
    norm_entscheidung="norm_unbefristet", gilt_ab="2026-08-16",
    norm_entschieden_grund="Testfall", anlass="unbekannt", actor="claude-code/opus-5",
    norm_rang=1, norm_entschieden_von="betreiber",
)

WORTLAUT_LANG = '„ok ich bin bei dir! zudem das was an mir haengt lang genug!"'


def _insert(conn: sqlite3.Connection, **overrides) -> None:
    zeile = {**BASISZEILEN, **overrides}
    spalten = ", ".join(zeile)
    platzhalter = ", ".join("?" for _ in zeile)
    conn.execute(f"INSERT INTO knowledge_nodes ({spalten}) VALUES ({platzhalter})", list(zeile.values()))
    conn.commit()


# --- ROT vor GRUEN ----------------------------------------------------

def test_rot_alter_stand_kennt_weisungszitat_nicht(tmp_path):
    """ROT: auf der Schema-Fassung von VOR diesem Auftrag lehnt
    schon der Wertebereichs-Trigger jeden Versuch ab, norm_entschieden_
    belegart='weisungszitat' zu setzen -- der Eingang existierte nicht."""
    db_path = _frisch(tmp_path, schema=_ALTE_SCHEMA_SQL, name="alt.db")
    conn = sqlite3.connect(str(db_path))
    with pytest.raises(sqlite3.IntegrityError, match="unzulaessig"):
        _insert(conn, norm_entschieden_grund=WORTLAUT_LANG, norm_entschieden_belegart="weisungszitat")
    conn.close()


# --- GRUEN: Positivkontrolle -------------------------------------------

def test_gruen_langes_zitat_wird_akzeptiert(tmp_path):
    db_path = _frisch(tmp_path)
    conn = sqlite3.connect(str(db_path))
    _insert(conn, norm_entschieden_grund=WORTLAUT_LANG, norm_entschieden_belegart="weisungszitat")
    zeile = conn.execute(
        "SELECT norm_entschieden_von, norm_entschieden_belegart FROM knowledge_nodes WHERE id='n1'"
    ).fetchone()
    assert zeile == ("betreiber", "weisungszitat")
    conn.close()


# --- Negativfaelle -------------------------------------------------------

@pytest.mark.parametrize("grund", [
    "",
    None,
    "einfach nur Text ganz ohne Anfuehrungszeichen, beliebig lang genug",
    '„"',  # nur Anfuehrungszeichen, nichts dazwischen
    '„zu kurz!!"',  # 9 Zeichen zwischen den Zeichen, unter der Schwelle 10
], ids=["leer", "null", "kein_zitat", "nur_anfuehrungszeichen", "zu_kurz"])
def test_negativ_unbelegtes_weisungszitat_abgewiesen(tmp_path, grund):
    db_path = _frisch(tmp_path)
    conn = sqlite3.connect(str(db_path))
    with pytest.raises(sqlite3.IntegrityError, match="weisungszitat"):
        _insert(conn, norm_entschieden_grund=grund, norm_entschieden_belegart="weisungszitat")
    conn.close()


def test_grenzwert_genau_10_zeichen_reicht(tmp_path):
    """Grenzwert: genau 10 Zeichen zwischen den Anfuehrungszeichen reicht,
    9 nicht -- Schwelle und Schwelle-1. Der reale Anlass fuer diese Schwelle
    (statt der zunaechst gewaehlten 15): Knoten 3c524455 traegt als
    woertliches Betreiberzitat nur „Mit Historie." -- 13 Zeichen, eine
    vollstaendige, aber kurze Entscheidung. Eine Schwelle, die ein echtes
    Zitat abweist, waere keine Reibung gegen Missbrauch, sondern ein
    Hindernis fuer die Wahrheit."""
    db_path = _frisch(tmp_path)
    conn = sqlite3.connect(str(db_path))
    _insert(conn, norm_entschieden_grund='„' + ('x' * 10) + '"', norm_entschieden_belegart="weisungszitat")
    conn.close()

    db_path2 = _frisch(tmp_path, name="grenzwert_minus1.db")
    conn2 = sqlite3.connect(str(db_path2))
    with pytest.raises(sqlite3.IntegrityError, match="weisungszitat"):
        _insert(conn2, norm_entschieden_grund='„' + ('x' * 9) + '"', norm_entschieden_belegart="weisungszitat")
    conn2.close()


# --- Gegenrichtung: der bestehende Schutz bleibt stehen -----------------

def test_gegenrichtung_modellname_als_entscheider_bleibt_abgewiesen(tmp_path):
    """Die wichtigste Probe: ein Modellname in norm_entschieden_von wird bei
    Rang 1/2 weiterhin abgewiesen -- der neue Eingang schliesst eine Luecke,
    er reisst keine Tuer fuer die alte Sperre auf."""
    db_path = _frisch(tmp_path)
    conn = sqlite3.connect(str(db_path))
    with pytest.raises(sqlite3.IntegrityError, match="menschlichen Entscheider"):
        _insert(conn, norm_entschieden_von="claude-code/opus-5", norm_entschieden_belegart=None)
    conn.close()


def test_gegenrichtung_belegart_ohne_weisungszitat_bleibt_unbelastet(tmp_path):
    """Ein Knoten mit belegart='systemauth' (bestehender Wert) braucht KEIN
    Zitat -- die neue Pflicht greift ausschliesslich bei 'weisungszitat'."""
    db_path = _frisch(tmp_path)
    conn = sqlite3.connect(str(db_path))
    _insert(conn, norm_entschieden_von="Markus Lehr", norm_entschieden_belegart="systemauth",
            norm_entschieden_grund="kein Zitat noetig")
    conn.close()


# --- Selbstheilung bei einer spaeter geaenderten Mindestlaenge ----------

def test_ensure_belegart_triggers_zieht_geaenderte_mindestlaenge_nach(tmp_path, monkeypatch):
    """ROT VOR GRUEN am 2026-08-16 selbst: WEISUNGSZITAT_MINDESTLAENGE wurde
    nach dem ersten Bau von 15 auf 10 korrigiert (Knoten 3c524455 traegt nur
    ein 13 Zeichen langes echtes Zitat). Eine DB, die die Pflicht-Trigger
    schon mit der ALTEN Schwelle (15) installiert hatte, zog die Korrektur
    zunaechst NICHT nach -- _ensure_belegart_triggers pruefte nur, ob die
    Trigger FEHLEN, nicht ob ihre installierte Fassung noch der aktuellen
    WEISUNGSZITAT_MINDESTLAENGE entspricht (derselbe L-55075a-Fehler wie bei
    den CHECK-Triggern, nur unentdeckt an einer zweiten Stelle). Dieser Test
    installiert absichtlich die AELTERE Fassung (Schwelle 15) und prueft,
    dass kms.get_db() sie beim naechsten Verbindungsaufbau auf die aktuelle
    Schwelle nachzieht."""
    db_path = _frisch(tmp_path, name="veraltete_schwelle.db")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        "DROP TRIGGER IF EXISTS knowledge_nodes_norm_entschieden_weisungszitat_pflicht_bi;"
        "DROP TRIGGER IF EXISTS knowledge_nodes_norm_entschieden_weisungszitat_pflicht_bu;"
        "CREATE TRIGGER knowledge_nodes_norm_entschieden_weisungszitat_pflicht_bi "
        "BEFORE INSERT ON knowledge_nodes "
        "FOR EACH ROW WHEN NEW.norm_entschieden_belegart = 'weisungszitat' "
        "    AND (INSTR(COALESCE(NEW.norm_entschieden_grund, ''), '„') = 0 "
        "    OR INSTR(SUBSTR(COALESCE(NEW.norm_entschieden_grund, ''), "
        "            INSTR(COALESCE(NEW.norm_entschieden_grund, ''), '„') + 1), '\"') = 0 "
        "    OR INSTR(SUBSTR(COALESCE(NEW.norm_entschieden_grund, ''), "
        "            INSTR(COALESCE(NEW.norm_entschieden_grund, ''), '„') + 1), '\"') - 1 < 15) "
        "BEGIN SELECT RAISE(ABORT, 'veraltete Schwelle 15'); END;"
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(kms, "DB_PATH", db_path)
    verbunden = kms.get_db()
    verbunden.close()

    conn2 = sqlite3.connect(str(db_path))
    sql = conn2.execute(
        "SELECT sql FROM sqlite_master WHERE name='knowledge_nodes_norm_entschieden_weisungszitat_pflicht_bi'"
    ).fetchone()[0]
    conn2.close()
    assert "< 10" in sql, sql
    assert "15" not in sql, sql


# --- Werkzeugebene: kms.knowledge_add / knowledge_update -----------------

@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = _frisch(tmp_path, name="werkzeug.db")
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def test_knowledge_add_betreiber_weisung_setzt_von_und_belegart(temp_db):
    res = kms.knowledge_add(
        "/", "Betreiberweisung", "Zusammenfassung", source="Chat 2026-08-16",
        norm_rang=1, gilt_ab="2026-08-16", norm_entscheidung="norm_unbefristet",
        betreiber_weisung=WORTLAUT_LANG,
    )
    assert res.get("status") == "created", res
    conn = sqlite3.connect(str(temp_db))
    row = conn.execute(
        "SELECT norm_entschieden_von, norm_entschieden_belegart, norm_entschieden_grund "
        "FROM knowledge_nodes WHERE id = ?", (res["id"],)
    ).fetchone()
    conn.close()
    assert row == ("betreiber", "weisungszitat", WORTLAUT_LANG)


def test_knowledge_add_betreiber_weisung_zu_kurz_wird_klartext_abgelehnt(temp_db):
    res = kms.knowledge_add(
        "/", "Kurze Weisung", "Zusammenfassung",
        norm_rang=1, gilt_ab="2026-08-16", norm_entscheidung="norm_unbefristet",
        betreiber_weisung='„zu kurz!!"',
    )
    assert "error" in res, res
    assert "betreiber_weisung" in res["error"]


def test_knowledge_update_hebt_keine_norm_auf_rang1_mit_beleg(temp_db):
    add = kms.knowledge_add("/", "Ausstehend", "Zusammenfassung", source="Chat 2026-08-16",
                            norm_entscheidung="keine_norm",
                            norm_entschieden_grund="Rangeinstufung steht aus")
    assert add.get("status") == "created", add
    upd = kms.knowledge_update(
        add["id"], norm_rang=1, gilt_ab="2026-08-16", norm_entscheidung="norm_unbefristet",
        betreiber_weisung=WORTLAUT_LANG,
    )
    assert "error" not in upd, upd
    conn = sqlite3.connect(str(temp_db))
    row = conn.execute(
        "SELECT norm_rang, norm_entschieden_von, norm_entschieden_belegart, norm_entschieden_grund "
        "FROM knowledge_nodes WHERE id = ?", (add["id"],)
    ).fetchone()
    conn.close()
    assert row == (1, "betreiber", "weisungszitat", WORTLAUT_LANG)


def test_mcp_vertrag_reicht_betreiber_weisung_an_beide_werkzeuge(monkeypatch):
    gesehen = {}

    monkeypatch.setattr(kms, "knowledge_add",
                        lambda *args, **kwargs: gesehen.setdefault("add", kwargs))
    monkeypatch.setattr(kms, "knowledge_update",
                        lambda *args, **kwargs: gesehen.setdefault("update", kwargs))

    for name in ("knowledge_add", "knowledge_update"):
        assert "betreiber_weisung" in kms.TOOLS[name]["inputSchema"]["properties"]

    kms.TOOLS["knowledge_add"]["handler"]({
        "parent_path": "/", "title": "t", "summary": "s",
        "norm_entscheidung": "keine_norm", "norm_entschieden_grund": "Test",
        "betreiber_weisung": WORTLAUT_LANG,
    })
    kms.TOOLS["knowledge_update"]["handler"]({
        "node_id": "n1", "norm_entscheidung": "norm_unbefristet",
        "betreiber_weisung": WORTLAUT_LANG,
    })
    assert gesehen["add"]["betreiber_weisung"] == WORTLAUT_LANG
    assert gesehen["update"]["betreiber_weisung"] == WORTLAUT_LANG


def demo() -> None:
    """Kleinstes lauffaehiges Selbstcheck ohne pytest -- gegen ein frisches
    tmp-Verzeichnis, kein Bestand angefasst."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = _Path(td)
        db = _frisch(p)
        conn = sqlite3.connect(str(db))
        _insert(conn, norm_entschieden_grund=WORTLAUT_LANG, norm_entschieden_belegart="weisungszitat")
        assert conn.execute("SELECT norm_entschieden_belegart FROM knowledge_nodes").fetchone() == ("weisungszitat",)
        conn.close()

        db2 = _frisch(p, name="neg.db")
        conn2 = sqlite3.connect(str(db2))
        try:
            _insert(conn2, norm_entschieden_grund="kein Zitat", norm_entschieden_belegart="weisungszitat")
            raise AssertionError("haette abgelehnt werden muessen")
        except sqlite3.IntegrityError:
            pass
        conn2.close()
    print("test_weisungszitat_beleg.demo ok")


if __name__ == "__main__":
    demo()
