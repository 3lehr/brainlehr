"""Eine einzelne Lehre muss freigegeben werden koennen (Auftrag 2026-08-11).

BEFUND, der das veranlasst (docs/PROMPT_FREIGABE_LEHREN_2026-08-11.md, Zahlen
dort gemessen): `lessons_learned.freigabe` steht bei 753 von 753 Zeilen auf
'intern'. Das ist die ENTWORFENE Vorgabe, kein Defekt -- migrate_freigabe.py
haelt ausdruecklich fest: "keine Massenzuweisung ... jeder Bestandsknoten
bleibt 'intern', bis jemand ihn einzeln entscheidet."

Der Defekt ist, dass es keinen Weg gibt, sie einzeln zu aendern. Solange der
fehlt, liest der Pruefer die Spalte als "gebaute Regel ohne Wirkung" -- und das
waere erst dann ein berechtigter Vorwurf, wenn ein Weg existierte und niemand
ihn nutzte.

ZWEI ABWEICHUNGEN VOM AUFTRAG, am Code gemessen und hier festgehalten, weil
sie die Bauform bestimmen:

1. Der Auftrag nennt `knowledge_freigeben` als Vorbild fuer Knoten. Das
   Werkzeug hat mit der Spalte `freigabe` NICHTS zu tun -- es macht ein
   Zurueckziehen rueckgaengig (Spalte `zurueckgezogen`). Reine
   Namensgleichheit.
2. Fuer Knoten gibt es ueberhaupt keinen Einzel-Schreibweg. Die 106 offenen
   Knoten stammen aus einer MASSENZUWEISUNG per rohem SQL in
   melder/selbstbeschreibung.py ("UPDATE knowledge_nodes SET freigabe='offen'
   WHERE path LIKE ...") -- ohne access_log-Eintrag, also an der Auditkette
   vorbei. Genau das, was migrate_freigabe.py ausschliesst.

Deshalb ist die Kernfunktion hier tabellenunabhaengig gebaut: Ein reines
Lehren-Werkzeug haette garantiert einen fast gleichen Zwilling fuer Knoten
nach sich gezogen -- die Fehlerklasse aus L-0de1a9 (vierzehn `_ensure_<spalte>`-
Funktionen, jede fuer sich korrekt).
"""
from __future__ import annotations

import sqlite3
import sys
import uuid
from pathlib import Path

import pytest

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                            ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402

STUFEN = ("offen", "intern", "gesperrt")


@pytest.fixture()
def db(tmp_path, monkeypatch):
    pfad = tmp_path / "knowledge.db"
    conn = sqlite3.connect(str(pfad))
    conn.executescript((_w / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", pfad)
    return pfad


def _lehre(db) -> str:
    erg = kms.lesson_record(
        type_="insight", description=f"Probe {uuid.uuid4().hex[:8]}",
        root_cause="Testfall.", resolution="Testfall.", prevention="Testfall.",
        severity="low", projects=["brainlehr"])
    assert "error" not in erg, erg
    return erg["id"]


def _stufe(db, lehre_id: str) -> str:
    conn = sqlite3.connect(str(db))
    try:
        zeile = conn.execute("SELECT freigabe FROM lessons_learned WHERE id=?",
                             (lehre_id,)).fetchone()
    finally:
        conn.close()
    assert zeile, f"Lehre {lehre_id} fehlt"
    return zeile[0]


def test_werte_trigger_existieren(db):
    """Die Schranke gehoert in die DATENBANK, nicht in den Aufrufer.

    Gemessen 2026-08-11: 32 Serverprozesse arbeiten gleichzeitig auf derselben
    Datei, der aelteste mit 23 Stunden altem Code (Knoten 4603f990). Ein
    Trigger gilt ab seiner Anlage fuer alle; eine Pruefung in Python nur fuer
    neu gestartete."""
    conn = sqlite3.connect(str(db))
    try:
        namen = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' "
            "AND name LIKE '%lessons%freigabe%'")]
    finally:
        conn.close()
    assert any(n.endswith("_bi") for n in namen), f"kein INSERT-Trigger: {namen}"
    assert any(n.endswith("_bu") for n in namen), f"kein UPDATE-Trigger: {namen}"


def test_vorgabe_bleibt_intern(db):
    """GEGENPROBE: Der Schreibweg darf die Vorgabe nicht verschieben."""
    assert _stufe(db, _lehre(db)) == "intern"


def test_eine_lehre_wird_freigegeben(db):
    """ROT VOR GRUEN: bis 2026-08-11 gab es keinen Weg dorthin."""
    lehre = _lehre(db)
    erg = kms.freigabe_setzen(lehre, "offen")
    assert "error" not in erg, erg
    assert _stufe(db, lehre) == "offen"


def test_rueckweg_geht_ebenso(db):
    """Der Auftrag verlangt die Gegenprobe in BEIDE Richtungen. Anders als bei
    norm_entscheidung ist freigabe ausdruecklich keine einmal bindende
    Entscheidung (Spaltenkommentar in schema.sql)."""
    lehre = _lehre(db)
    kms.freigabe_setzen(lehre, "offen")
    kms.freigabe_setzen(lehre, "intern")
    assert _stufe(db, lehre) == "intern"


@pytest.mark.parametrize("stufe", STUFEN)
def test_alle_drei_stufen_einzeln(db, stufe):
    """GRENZWERT: jeder erlaubte Wert einzeln, nicht nur der bequeme."""
    lehre = _lehre(db)
    assert "error" not in kms.freigabe_setzen(lehre, stufe)
    assert _stufe(db, lehre) == stufe


def test_unzulaessige_stufe_wird_abgewiesen(db):
    """NEGATIVFALL. Geprueft wird nicht DASS abgewiesen wird, sondern dass die
    Zeile unveraendert bleibt -- ein abgewiesener Aufruf, der trotzdem
    schreibt, waere schlimmer als gar keine Pruefung."""
    lehre = _lehre(db)
    erg = kms.freigabe_setzen(lehre, "halboffen")
    assert "error" in erg
    assert _stufe(db, lehre) == "intern"


def test_unbekannte_kennung_meldet_statt_zu_schweigen(db):
    erg = kms.freigabe_setzen("gibtsnicht-4711", "offen")
    assert "error" in erg


def test_vorgang_steht_im_protokoll(db):
    """Der Auftrag verlangt es ausdruecklich: die Entscheidung gehoert ins
    access_log wie jede andere. Ohne das waere sie der einzige Eingriff in die
    Sichtbarkeit, der keine Spur hinterlaesst -- genau der Mangel der
    Massenzuweisung in melder/selbstbeschreibung.py."""
    lehre = _lehre(db)
    kms.freigabe_setzen(lehre, "offen")
    conn = sqlite3.connect(str(db))
    try:
        zeilen = conn.execute(
            "SELECT action, node_path FROM access_log WHERE action LIKE '%freigabe%'"
        ).fetchall()
    finally:
        conn.close()
    assert zeilen, "kein Protokolleintrag zur Freigabe"


def test_keine_massenzuweisung_moeglich(db):
    """Der Auftrag verbietet sie. Das Werkzeug nimmt genau EINE Kennung --
    eine Liste oder ein Muster darf es gar nicht erst annehmen."""
    a, b = _lehre(db), _lehre(db)
    erg = kms.freigabe_setzen(f"{a},{b}", "offen")
    assert "error" in erg
    assert _stufe(db, a) == "intern" and _stufe(db, b) == "intern"


def test_das_werkzeugschema_bietet_den_weg_an():
    """Ein Feld, das die Funktion kennt und das Schema nicht nennt, ist fuer
    ein Sprachmodell nicht vorhanden -- es sieht nur das Schema. Genau diese
    Luecke hatte `gattung` bis heute frueh (Commit 99e4af9)."""
    werkzeug = kms.TOOLS["freigabe_setzen"]
    felder = werkzeug["inputSchema"]["properties"]
    assert felder["stufe"]["enum"] == list(STUFEN), \
        "der Wertebereich im Schema weicht vom Trigger ab"
    assert werkzeug["inputSchema"]["required"] == ["eintrag_id", "stufe"]
    assert "individually" in werkzeug["description"], \
        "die Beschreibung muss sagen, dass einzeln entschieden wird"


def test_handler_reicht_durch(db):
    """Der Weg, den der Klient nimmt -- ueber den Handler, nicht die Funktion."""
    lehre = _lehre(db)
    erg = kms.TOOLS["freigabe_setzen"]["handler"](
        {"eintrag_id": lehre, "stufe": "gesperrt"})
    assert "error" not in erg, erg
    assert _stufe(db, lehre) == "gesperrt"
