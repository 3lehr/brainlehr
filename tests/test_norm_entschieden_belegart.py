"""SCHRITT 1 aus docs/PLAN_MENSCHLICHER_ENTSCHEID_2026-08-12.md: der
Datensatz lernt ENTSCHEIDER (norm_entschieden_von, vorhanden) von SCHREIBER
(actor, vorhanden) getrennt zu halten und bekommt eine neue Spalte
norm_entschieden_belegart -- womit ist belegt, dass ein Mensch entschieden
hat. Die Schranke fuer Rang 1/2 (kein Maschinenname in norm_entschieden_von)
wird NICHT gelockert, siehe test_negativfall_ohne_menschlichen_entscheider.

Alle Tests schreiben ROH per SQL, nicht ueber kms.knowledge_add()/
knowledge_update() -- die beiden Werkzeuge bieten bis Schritt 3 gar keinen
Parameter fuer norm_entschieden_von/-belegart (knowledge_add leitet den Wert
aus source/actor ab, knowledge_update schreibt immer actor). Das ist exakt
der Befund aus dem Auftrag: die Moeglichkeit, einen menschlichen Entscheider
einzutragen, entsteht auf Datensatzebene, benutzt wird sie erst in Schritt 3.
"""
from __future__ import annotations

import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import knowledge_mcp_server as kms  # noqa: E402

SCHEMA_SQL = (ROOT / "schema.sql").read_text(encoding="utf-8")

# Die Schema-Fassung VOR diesem Auftrag -- reproduziert den "gewachsenen
# Bestand" ohne die neue Spalte/Trigger, ohne sie von Hand nachzubauen.
#
# Bezugspunkt ist der BENANNTE Commit 0182b05^ (Elternteil des Commits, der
# die Spalte einfuehrte), NICHT "HEAD" oder "der Stand vor meiner Aenderung".
# Ein Rot-vor-Gruen-Beleg gegen ein bewegliches Ziel widerlegt sich selbst,
# sobald die Aenderung festgeschrieben ist: HEAD enthielt die Spalte zum
# Zeitpunkt, als dieser Test geschrieben wurde, noch nicht -- seit Commit
# 0182b05 enthaelt HEAD sie, und der Test waere stillschweigend gruen
# geworden, ohne dass er je wieder etwas belegt haette. Geprueft:
# `git show 0182b05^:schema.sql | grep -c norm_entschieden_belegart` == 0,
# `git show 0182b05:schema.sql | grep -c norm_entschieden_belegart` > 0.
_ALTE_SCHEMA_SQL = subprocess.run(
    ["git", "show", "0182b05^:schema.sql"], cwd=ROOT, capture_output=True,
    text=True, check=True,
).stdout


def _frisch(tmp_path: Path, schema: str = SCHEMA_SQL, name: str = "frisch.db") -> Path:
    db_path = tmp_path / name
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    return db_path


BASISZEILEN = dict(
    id="n1", path="/x/n1", parent_path="/", project_id="shared",
    title="t", summary="s", content="", level=1, tags="[]",
    source="Betreiber-Entscheidung im Gespraech 2026-08-13", created_at="2026-08-13T10:00:00+02:00",
    updated_at="2026-08-13T10:00:00+02:00", norm_entscheidung="norm_unbefristet",
    gilt_ab="2026-08-13", norm_entschieden_grund="Testfall", anlass="betreiber",
    actor="claude-code/opus-5",
)


def _insert(conn: sqlite3.Connection, **overrides) -> None:
    zeile = {**BASISZEILEN, **overrides}
    spalten = ", ".join(zeile)
    platzhalter = ", ".join("?" for _ in zeile)
    conn.execute(f"INSERT INTO knowledge_nodes ({spalten}) VALUES ({platzhalter})", list(zeile.values()))
    conn.commit()


def test_rot_alte_schema_kennt_die_spalte_noch_nicht(tmp_path):
    """ROT: dieselbe Zeile, dieselbe Testfunktion, auf der Schema-Fassung von
    VOR diesem Auftrag (git HEAD) -- bricht mit 'no such column', weil es
    norm_entschieden_belegart dort schlicht nicht gibt."""
    db_path = _frisch(tmp_path, schema=_ALTE_SCHEMA_SQL)
    conn = sqlite3.connect(str(db_path))
    with pytest.raises(sqlite3.OperationalError, match="no column named norm_entschieden_belegart"):
        _insert(conn, norm_rang=1, norm_entschieden_von="Markus Lehr",
                norm_entschieden_belegart="systemauth")
    conn.close()


def test_gruen_rang1_mit_menschlichem_entscheider_und_belegart_erlaubt(tmp_path):
    """GRUEN: dieselbe Zeile auf dem aktuellen schema.sql -- geht durch."""
    db_path = _frisch(tmp_path)
    conn = sqlite3.connect(str(db_path))
    _insert(conn, norm_rang=1, norm_entschieden_von="Markus Lehr",
            norm_entschieden_belegart="systemauth")
    zeile = conn.execute(
        "SELECT norm_entschieden_von, norm_entschieden_belegart, actor FROM knowledge_nodes WHERE id='n1'"
    ).fetchone()
    assert zeile == ("Markus Lehr", "systemauth", "claude-code/opus-5")
    # ENTSCHEIDER und SCHREIBER sind zwei verschiedene Werte in derselben
    # Zeile -- genau die Trennung, die der Auftrag verlangt.
    assert zeile[0] != zeile[2]
    conn.close()


def test_negativfall_ohne_menschlichen_entscheider_bleibt_abgewiesen(tmp_path):
    """Die Schranke ist NICHT gelockert: ein Maschinenname in
    norm_entschieden_von bleibt fuer Rang 1/2 verboten, mit oder ohne
    Belegart."""
    db_path = _frisch(tmp_path)
    conn = sqlite3.connect(str(db_path))
    with pytest.raises(sqlite3.IntegrityError, match="menschlichen Entscheider"):
        _insert(conn, norm_rang=1, norm_entschieden_von="claude-code/opus-5",
                norm_entschieden_belegart="systemauth", anlass="selbst")
    conn.close()


def test_negativfall_rang2_gilt_genauso(tmp_path):
    db_path = _frisch(tmp_path)
    conn = sqlite3.connect(str(db_path))
    with pytest.raises(sqlite3.IntegrityError, match="menschlichen Entscheider"):
        _insert(conn, norm_rang=2, norm_entschieden_von="gpt-5",
                norm_entschieden_belegart="systemauth", anlass="selbst")
    conn.close()


def test_belegart_ist_freiwillig_kein_bruch_fuer_bestandsschreiber(tmp_path):
    """BEWUSST KEINE Pflicht (Befund beim Bau, siehe Kommentar in schema.sql
    vor der Fassungshistorie): ein menschlicher Entscheider auf Rang 1/2 OHNE
    Belegart bleibt zulaessig -- ein erster Versuch, das zu erzwingen, brach
    20 bestehende Tests, die norm_entschieden_von schon lange als Mensch
    schreiben, ohne dass Belegart je verlangt war. RUECKWAERTSVERTRAEGLICH
    heisst hier: kein alter Schreibpfad (auch keiner INNERHALB dieses
    Auftrags) darf an einer neuen Spalte abbrechen."""
    db_path = _frisch(tmp_path)
    conn = sqlite3.connect(str(db_path))
    _insert(conn, norm_rang=1, norm_entschieden_von="Markus Lehr",
            norm_entschieden_belegart=None)
    zeile = conn.execute(
        "SELECT norm_entschieden_von, norm_entschieden_belegart FROM knowledge_nodes WHERE id='n1'"
    ).fetchone()
    assert tuple(zeile) == ("Markus Lehr", None)
    conn.close()


def test_belegart_wertebereich_check(tmp_path):
    """Nur die drei dokumentierten Werte sind zulaessig -- kein Wert, der
    'gelesen'/'verstanden' behauptet (Plan-Abschnitt 'Was der Beleg wirklich
    aussagt': Systemauthentisierung belegt Anwesenheit, nicht Verstehen)."""
    db_path = _frisch(tmp_path)
    conn = sqlite3.connect(str(db_path))
    with pytest.raises(sqlite3.IntegrityError, match="norm_entschieden_belegart unzulaessig"):
        _insert(conn, norm_rang=1, norm_entschieden_von="Markus Lehr",
                norm_entschieden_belegart="gelesen_bestaetigt")
    conn.close()
    # Gegenprobe: jeder der drei dokumentierten Werte geht durch, auf je
    # einer frischen DB.
    for i, wert in enumerate(("selbstauskunft", "systemauth", "kommandozeile")):
        db = _frisch(tmp_path, name=f"belegart-{i}.db")
        c = sqlite3.connect(str(db))
        _insert(c, norm_rang=1, norm_entschieden_von="Markus Lehr", norm_entschieden_belegart=wert)
        c.close()


def test_zweiter_negativfall_schreiber_kann_sich_noch_selbst_erklaeren(tmp_path):
    """EHRLICHER BEFUND (kein Verstecken): auf DIESER Stufe kann die
    Datenbank nicht pruefen, OB tatsaechlich ein Mensch entschieden hat --
    nur, DASS die drei Felder plausibel zueinander passen (kein
    Maschinenname, Belegart gesetzt). Ein Schreiber, der 'Markus Lehr' und
    'systemauth' frei erfindet, wird heute NICHT abgewiesen. Das ist keine
    Regression dieses Auftrags (die Pruefung existierte vorher so wenig wie
    die Spalte selbst) und exakt die Luecke, die Schritt 3
    (Systemauthentisierung in der App, siehe Plan) schliessen muss -- die
    DB-Schranke kann strukturell nicht mehr als Plausibilitaet pruefen, eine
    Identitaet kann nur die Systemauthentisierung belegen."""
    db_path = _frisch(tmp_path)
    conn = sqlite3.connect(str(db_path))
    # actor bleibt die Maschine (Schreiber), norm_entschieden_von behauptet
    # frei einen Menschen (Entscheider) -- die DB nimmt das ab.
    _insert(conn, norm_rang=1, norm_entschieden_von="Markus Lehr",
            norm_entschieden_belegart="systemauth", actor="claude-code/opus-5")
    zeile = conn.execute("SELECT norm_entschieden_von FROM knowledge_nodes WHERE id='n1'").fetchone()
    assert zeile == ("Markus Lehr",), "erwartete Luecke: Selbstauskunft wird heute noch angenommen"
    conn.close()


def test_beide_ausgangszustaende_bestehende_db_wird_nachgezogen(tmp_path, monkeypatch):
    """Zweiter Ausgangszustand: eine GEWACHSENE Datenbank (aus der alten
    Schema-Fassung angelegt, mit einer Altzeile drin) bekommt Spalte und
    Trigger durch kms.ensure_schema() nachgezogen, ohne die Altzeile
    inhaltlich zu aendern -- danach verhaelt sie sich wie eine frische DB."""
    db_path = tmp_path / "gewachsen.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_ALTE_SCHEMA_SQL)
    conn.commit()
    # Altzeile OHNE die neue Spalte einfuegen -- so sah der echte Bestand vor
    # diesem Auftrag aus.
    alte_basis = {k: v for k, v in BASISZEILEN.items()}
    alte_basis["norm_rang"] = 1
    alte_basis["norm_entschieden_von"] = "betreiber"
    spalten = ", ".join(alte_basis)
    platzhalter = ", ".join("?" for _ in alte_basis)
    conn.execute(f"INSERT INTO knowledge_nodes ({spalten}) VALUES ({platzhalter})", list(alte_basis.values()))
    conn.commit()
    conn.close()

    monkeypatch.setattr(kms, "DB_PATH", db_path)
    nachgezogene_conn = kms.get_db()  # ruft ensure_schema() intern auf
    spalten_jetzt = {r[1] for r in nachgezogene_conn.execute("PRAGMA table_info(knowledge_nodes)")}
    assert "norm_entschieden_belegart" in spalten_jetzt

    # Altzeile unveraendert -- kein Bestandsdatensatz inhaltlich angefasst.
    alt = nachgezogene_conn.execute(
        "SELECT norm_entschieden_von, norm_entschieden_belegart FROM knowledge_nodes WHERE id='n1'"
    ).fetchone()
    assert tuple(alt) == ("betreiber", None)

    # Und die nachgezogene DB verhaelt sich jetzt wie eine frische: grüner
    # Fall geht durch, Negativfall bleibt abgewiesen.
    nachgezogene_conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, content, "
        "level, tags, source, created_at, updated_at, norm_entscheidung, gilt_ab, "
        "norm_entschieden_grund, anlass, actor, norm_rang, norm_entschieden_von, norm_entschieden_belegart) "
        "VALUES ('n2','/x/n2','/','shared','t','s','',1,'[]','Betreiber-Entscheidung 2026-08-13',"
        "'2026-08-13T10:00:00+02:00','2026-08-13T10:00:00+02:00','norm_unbefristet','2026-08-13',"
        "'Testfall','betreiber','claude-code/opus-5',1,'Markus Lehr','systemauth')"
    )
    with pytest.raises(sqlite3.IntegrityError, match="menschlichen Entscheider"):
        nachgezogene_conn.execute(
            "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, content, "
            "level, tags, source, created_at, updated_at, norm_entscheidung, gilt_ab, "
            "norm_entschieden_grund, anlass, actor, norm_rang, norm_entschieden_von) "
            "VALUES ('n3','/x/n3','/','shared','t','s','',1,'[]','x',"
            "'2026-08-13T10:00:00+02:00','2026-08-13T10:00:00+02:00','norm_unbefristet','2026-08-13',"
            "'Testfall','unbekannt','claude-code/opus-5',1,'claude-code/opus-5')"
        )
    nachgezogene_conn.rollback()
    nachgezogene_conn.close()


def test_update_pfad_von_kern_herkunft_normentscheider_bleibt_unberuehrt(tmp_path):
    """Gegenprobe zur Wertebereichs-Pruefung: eine UPDATE-seitige Erstvergabe
    von norm_entschieden_von='betreiber' OHNE Belegart (wie
    kern/herkunft_normentscheider.py sie fuer Altzeilen faehrt, kein bu-
    Pflicht-Trigger vorhanden) bleibt moeglich -- dieses bestehende, tabu
    Werkzeug unter kern/ wird von diesem Auftrag nicht angefasst."""
    db_path = _frisch(tmp_path)
    conn = sqlite3.connect(str(db_path))
    _insert(conn, norm_rang=1, norm_entschieden_von="claude-code/opus-5",
            norm_entschieden_belegart=None, anlass="betreiber")
    # anlass='betreiber' umgeht die Herkunfts-Schranke beim INSERT (bestehendes
    # Verhalten, unveraendert) -- die Zeile steht mit Maschine als Entscheider.
    conn.execute("UPDATE knowledge_nodes SET norm_entschieden_von = 'betreiber' WHERE id = 'n1'")
    conn.commit()
    zeile = conn.execute(
        "SELECT norm_entschieden_von, norm_entschieden_belegart FROM knowledge_nodes WHERE id='n1'"
    ).fetchone()
    assert zeile == ("betreiber", None)
    conn.close()


def demo() -> None:
    """Kleinstes lauffaehiges Selbstcheck ohne pytest, fuer den schnellen
    Handlauf."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        db = _frisch(p)
        conn = sqlite3.connect(str(db))
        _insert(conn, norm_rang=1, norm_entschieden_von="Markus Lehr", norm_entschieden_belegart="systemauth")
        assert conn.execute("SELECT norm_entschieden_belegart FROM knowledge_nodes").fetchone() == ("systemauth",)
    print("test_norm_entschieden_belegart.demo ok")


if __name__ == "__main__":
    demo()
