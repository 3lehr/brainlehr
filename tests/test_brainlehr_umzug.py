"""brainlehr.py — Erstanlage an einem leeren Ort und Rundlauf des Bestands.

Plan hub/docs/PLAN_BRAINLEHR_EIGENSTAENDIG_2026-08-08.md, Schritte S2 und S3.

ROT VOR GRUEN, gemessen am echten Bestand, bevor es das Werkzeug gab:
* eine Erstanlage trug 6 Tabellen und 2 Spalten weniger als der Betrieb
  (eskalation_historie, eskalation_vorschlag, lessons_learned.pruefstelle,
  knowledge_embeddings.text_checksum -- dazu zwei Tabellen, die dort nichts
  verloren haben, siehe NICHT_KERN unten),
* 644 von 644 Lehren wurden beim Einlesen abgewiesen (`no column pruefstelle`),
* 113 von 1989 Knoten ebenso (`parent_path zeigt auf keinen vorhandenen
  Knoten` -- Kinder standen vor ihren Eltern),
* 1919 Knoten mit norm_entscheidung='offen' waren ueberhaupt nicht
  einlesbar, weil der Pflicht-Trigger genau diesen Wert beim Anlegen abweist.

Der letzte Punkt ist der Grund fuer den einen Sonderweg in brainlehr.rein()
(Pflicht-Trigger fuer die Dauer des Einlesens heraus, danach wiederhergestellt
und geprueft). Er wird hier mitgeprueft: nach dem Einlesen muss die
Herkunftsschranke wieder greifen.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import json
import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import brainlehr  # type: ignore  # noqa: E402
import knowledge_mcp_server as kms  # type: ignore  # noqa: E402

BETRIEB_DB = SHARED_KNOWLEDGE / "knowledge.db"

# Tabellen, die absichtlich NICHT zur Erstanlage gehoeren. Beide sind
# nachgesehen, nicht vermutet:
#   lost_and_found  Rohauswurf von `.recover` aus der Bergung vom 2026-08-07
#                   (L-84869f) -- Seitennummern und namenlose Spalten c0..c28
#   mycel_*         Ableitung eines Analyseskripts, jederzeit neu erzeugbar
NICHT_KERN = ("lost_and_found", "mycel_")


def _tabellen_und_spalten(conn: sqlite3.Connection) -> dict[str, set[str]]:
    bild = {}
    for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        if t.startswith(NICHT_KERN) or t.endswith(("_fts", "_data", "_idx", "_docsize", "_config", "_content")):
            continue
        bild[t] = {r[1] for r in conn.execute(f"PRAGMA table_info({t})")}
    return bild


def test_init_legt_regelbewehrte_datenbank_an(tmp_path, capsys):
    """S2: ein Befehl, ein leerer Ort, eine benutzbare brainlehr."""
    ziel = tmp_path / "neuer_ort"
    assert brainlehr.init(ziel) == 0
    db = ziel / "knowledge.db"
    assert db.exists()

    conn = sqlite3.connect(db)
    trigger = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    assert "knowledge_nodes_herkunft_bu" in trigger
    assert "lessons_herkunft_bu" in trigger
    conn.close()


def test_init_ueberschreibt_keinen_bestand(tmp_path):
    """Die eine Zusicherung, die eine Erstanlage geben muss."""
    ziel = tmp_path / "ort"
    assert brainlehr.init(ziel) == 0
    db = ziel / "knowledge.db"
    vorher = db.stat().st_size
    assert brainlehr.init(ziel) == 1  # zweiter Lauf verweigert
    assert db.stat().st_size == vorher


def test_rundlauf_erhaelt_bestand_und_herkunft(tmp_path):
    """S3: raus -> init -> rein. Zeilenzahlen gleich, Herkunft unveraendert,
    Schranke danach wieder scharf."""
    quelle = tmp_path / "quelle.db"
    conn = sqlite3.connect(quelle)
    kms.ensure_schema(conn)
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, level, title, summary, "
        "source, updated_at, created_at, actor, session, norm_entscheidung, "
        "norm_entschieden_von, norm_entschieden_grund) VALUES "
        "('a1', '/a', NULL, 0, 'Ast', 's', 'test', 'jetzt', 'damals', 'actor-A', "
        "'sitzung-A', 'keine_norm', 'actor-A', 'Testvorrichtung')"
    )
    # Kind NACH dem Elternknoten eingefuegt, im Auszug aber egal -- die
    # Sortierung beim Herausschreiben ist genau das, was hier geprueft wird.
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, level, title, summary, "
        "source, updated_at, created_at, actor, norm_entscheidung, "
        "norm_entschieden_von, norm_entschieden_grund) VALUES "
        "('b1', '/a/b', '/a', 1, 'Kind', 's', 'test', 'jetzt', 'damals', 'actor-A', "
        "'keine_norm', 'actor-A', 'Testvorrichtung')"
    )
    # Der Altbestandsfall: norm_entscheidung='offen' laesst sich nur ueber den
    # Sonderweg wieder einlesen. Direkt eingefuegt, weil der Pflicht-Trigger
    # genau das beim Anlegen verbietet -- das ist der Punkt.
    conn.execute("DROP TRIGGER knowledge_nodes_norm_entscheidung_pflicht_bi")
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, level, title, summary, "
        "source, updated_at, created_at, actor, norm_entscheidung) VALUES "
        "('c1', '/a/c', '/a', 1, 'Altbestand', 's', 'test', 'jetzt', 'damals', "
        "'actor-A', 'offen')"
    )
    kms.ensure_schema(conn)  # Trigger zurueck, wie im Betrieb
    conn.commit()
    conn.close()

    auszug = tmp_path / "auszug.jsonl"
    assert brainlehr.raus(auszug, quelle) == 0

    ziel_ordner = tmp_path / "ziel"
    assert brainlehr.init(ziel_ordner) == 0
    ziel = ziel_ordner / "knowledge.db"
    assert brainlehr.rein(auszug, ziel) == 0, "Rundlauf muss vollstaendig sein"

    z = sqlite3.connect(ziel)
    assert z.execute("SELECT count(*) FROM knowledge_nodes").fetchone()[0] == 3
    # Der Altbestand behaelt seine Unentschiedenheit -- ein Import, der 'offen'
    # zu 'keine_norm' umbiegt, wuerde behaupten, jemand haette entschieden.
    assert z.execute(
        "SELECT norm_entscheidung FROM knowledge_nodes WHERE id='c1'"
    ).fetchone()[0] == "offen"
    # Herkunft unveraendert mitgereist
    assert z.execute("SELECT actor, session, created_at FROM knowledge_nodes "
                     "WHERE id='a1'").fetchone() == ("actor-A", "sitzung-A", "damals")
    # Volltext wurde von den Triggern beim Einlesen mit aufgebaut
    assert z.execute("SELECT count(*) FROM knowledge_fts").fetchone()[0] == 3
    # und die Schranke greift wieder
    with pytest.raises(sqlite3.IntegrityError, match="Herkunftsfeld unveraenderlich"):
        z.execute("UPDATE knowledge_nodes SET actor='fremd' WHERE id='a1'")
    z.close()


def test_rein_verweigert_nicht_leere_zieldatenbank(tmp_path):
    """Zusammenfuehren ist eine andere Aufgabe als Wiederherstellen und wird
    nicht geraten."""
    quelle = tmp_path / "q.db"
    conn = sqlite3.connect(quelle)
    kms.ensure_schema(conn)
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, level, title, summary, "
        "source, updated_at, norm_entscheidung, norm_entschieden_von, "
        "norm_entschieden_grund) VALUES ('a1', '/a', NULL, 0, 't', 's', 'test', "
        "'jetzt', 'keine_norm', 'a', 'g')"
    )
    conn.commit()
    conn.close()
    auszug = tmp_path / "a.jsonl"
    brainlehr.raus(auszug, quelle)
    assert brainlehr.rein(auszug, quelle) == 1  # Ziel ist nicht leer


@pytest.mark.skipif(not BETRIEB_DB.exists(), reason="keine Betriebsdatenbank an diesem Ort")
def test_erstanlage_traegt_dasselbe_schema_wie_der_betrieb(tmp_path):
    """Die Kennzahl aus dem Plan (Erfolgsmass 1), als Test statt als Durchsicht.

    Sie darf nur in eine Richtung ausschlagen: der Betrieb darf nichts
    kennen, was eine Erstanlage nicht bekommt. Umgekehrt ist harmlos -- eine
    frische Datenbank darf einer alten voraus sein.
    """
    neu = sqlite3.connect(tmp_path / "neu.db")
    kms.ensure_schema(neu)
    betrieb = sqlite3.connect(f"file:{BETRIEB_DB}?mode=ro", uri=True)
    n, b = _tabellen_und_spalten(neu), _tabellen_und_spalten(betrieb)
    neu.close()
    betrieb.close()

    fehlende_tabellen = sorted(set(b) - set(n))
    fehlende_spalten = {t: sorted(b[t] - n[t]) for t in set(b) & set(n) if b[t] - n[t]}
    assert not fehlende_tabellen, f"Erstanlage fehlen Tabellen: {fehlende_tabellen}"
    assert not fehlende_spalten, f"Erstanlage fehlen Spalten: {fehlende_spalten}"


def test_haken_zeigt_baut_ein_und_doppelt_nicht(tmp_path, monkeypatch, capsys):
    """Die Automatik muss sich anschliessen lassen, sonst ist sie nur
    mitgeliefert und nicht wirksam. Drei Zusicherungen in einem Lauf:
    in einer leeren Umgebung fehlen alle vier, nach --einbauen stehen sie,
    und ein zweiter Lauf aendert nichts (sonst wachsen die Eintraege bei
    jedem Aufruf).

    ROT VOR GRUEN: vor dem Verb gab es nichts, was die Haken eintraegt —
    ein frischer Klon haette die Dateien gehabt und nichts, was sie ruft.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    assert brainlehr.haken(einbauen=False) == 1
    assert capsys.readouterr().out.count("[fehlt ]") == 4

    assert brainlehr.haken(einbauen=True) == 0
    ziel = tmp_path / ".claude" / "settings.json"
    daten = json.loads(ziel.read_text(encoding="utf-8"))
    anzahl = sum(len(g["hooks"]) for ev in daten["hooks"] for g in daten["hooks"][ev])
    assert anzahl == 4

    assert brainlehr.haken(einbauen=True) == 0
    assert "Alles angeschlossen" in capsys.readouterr().out
    assert json.loads(ziel.read_text(encoding="utf-8")) == daten
