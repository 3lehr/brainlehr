"""Wer eine Maschine fuehrt, muss am Datensatz stehen -- nicht nur im Ausweis.

BEFUND, der diese Tests veranlasst (2026-08-11, Betreiberweisung "chatgpt kann
den gleichen Ausweis benutzen, muss aber mitgeben dass chatgpt gefuehrt von
markus"):

`bedient_von` steht im Ausweis und wird bei `knowledge_anmelden` einmal
zurueckgegeben -- danach ist es weg. In schema.sql kam es nicht vor. Ein von
ChatGPT geschriebener Knoten trug also `actor='chatgpt'`, und niemand konnte
spaeter sagen, dass ein Mensch dahinterstand. Genau diese Zurechnung ist der
Zweck des ganzen Ausweiswesens: Ein Modell kann sie sich sonst nur selbst
zuschreiben.

DIE ENTSCHEIDENDE ZUSICHERUNG ist nicht, DASS das Feld gefuellt wird, sondern
WOHER es kommt: ausschliesslich aus dem beglaubigten Ausweis, nie aus einem
Argument. Waere es ein Parameter, koennte jeder Schreiber "gefuehrt von
markus" behaupten -- und das Feld waere wertlos, bauartgleich zur alten
actor-Luecke (B4.1: wer `actor="betreiber"` mitschickte, WAR Betreiber).
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

import ausweis  # type: ignore  # noqa: E402
import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


@pytest.fixture()
def welt(tmp_path, monkeypatch):
    """Eigene Datenbank UND eigener Ausweisbestand -- nichts Echtes wird beruehrt."""
    db = tmp_path / "knowledge.db"
    conn = sqlite3.connect(str(db))
    conn.executescript((_w / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db)

    ausweise = tmp_path / "ausweise.json"
    monkeypatch.setenv("BRAINLEHR_AUSWEISE", str(ausweise))
    monkeypatch.delenv("BRAINLEHR_GEHEIMNIS", raising=False)

    chef = ausweis.anlegen("chefin", ["betreiber"], art="mensch", pfad=ausweise)
    pin = ausweis.einladen("bot", bedient_von="chefin", rollen=["schreiber"],
                           aussteller=chef, pfad=ausweise)
    bot = ausweis.einloesen(pin, pfad=ausweise)["geheimnis"]
    return {"db": db, "ausweise": ausweise, "chef": chef, "bot": bot}


def _anlegen(**mehr):
    return kms.knowledge_add(
        parent_path="/", title=f"Probe {uuid.uuid4().hex[:8]}",
        summary="Probeknoten fuer die Fuehrungskette.",
        source="Test test_gefuehrt_von.py",
        norm_entscheidung="keine_norm",
        norm_entschieden_grund="Testknoten ohne normative Wirkung.",
        **mehr)


def _spalte(db, node_id, spalte):
    conn = sqlite3.connect(str(db))
    try:
        zeile = conn.execute(
            f"SELECT {spalte} FROM knowledge_nodes WHERE id=?", (node_id,)).fetchone()
    finally:
        conn.close()
    assert zeile, f"Knoten {node_id} fehlt"
    return zeile[0]


def test_schema_kennt_das_feld():
    """ROT VOR GRUEN: bis 2026-08-11 stand bedient_von in keiner Tabelle.

    Geprueft wird an der ANGELEGTEN Datenbank, nicht per Textsuche in
    schema.sql -- eine Suche nach dem Tabellenblock endet am ersten ");" und
    damit mitten in einem DEFAULT-Ausdruck. Genau daran ist die erste Fassung
    dieses Tests gescheitert und meldete Fehlen, wo nichts fehlte."""
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript((_w / "schema.sql").read_text(encoding="utf-8"))
        for tabelle in ("knowledge_nodes", "lessons_learned", "access_log"):
            spalten = [r[1] for r in conn.execute(f"PRAGMA table_info({tabelle})")]
            assert "bedient_von" in spalten, f"{tabelle} kennt bedient_von nicht"
    finally:
        conn.close()


def test_beglaubigter_schreiber_hinterlaesst_seinen_menschen(welt, monkeypatch):
    """Der eigentliche Zweck."""
    monkeypatch.setenv("BRAINLEHR_GEHEIMNIS", welt["bot"])
    erg = _anlegen()
    assert "error" not in erg, erg
    assert _spalte(welt["db"], erg["id"], "bedient_von") == "chefin"


def test_argument_kann_es_nicht_setzen(welt, monkeypatch):
    """NEGATIVFALL, und er ist wichtiger als der Positivfall.

    Waere das Feld ueber einen Parameter setzbar, koennte jeder Schreiber eine
    menschliche Deckung behaupten -- dieselbe Luecke, die bei actor bestand."""
    monkeypatch.delenv("BRAINLEHR_GEHEIMNIS", raising=False)
    try:
        erg = _anlegen(bedient_von="chefin")
    except TypeError:
        return  # es gibt gar keinen solchen Parameter -- die staerkste Antwort
    # Falls je einer eingefuehrt wird: er darf den Wert nicht in den Datensatz
    # bringen. Abweisen und Ignorieren sind beide zulaessig.
    if "error" not in erg:
        assert _spalte(welt["db"], erg["id"], "bedient_von") != "chefin", \
            "ein Argument hat eine menschliche Deckung erschlichen"


def test_ohne_ausweis_bleibt_es_leer(welt, monkeypatch):
    """Kein Ausweis, kein Mensch dahinter -- und das darf kein Fehler sein:
    unbeglaubigte Schreiber bleiben ausdruecklich zulaessig."""
    monkeypatch.delenv("BRAINLEHR_GEHEIMNIS", raising=False)
    erg = _anlegen()
    assert "error" not in erg, erg
    assert not _spalte(welt["db"], erg["id"], "bedient_von")


def test_mensch_fuehrt_sich_nicht_selbst(welt, monkeypatch):
    """GRENZFALL: Schreibt der Mensch selbst, gibt es niemanden ueber ihm.
    Ein 'chefin wird gefuehrt von chefin' waere eine leere Aussage."""
    monkeypatch.setenv("BRAINLEHR_GEHEIMNIS", welt["chef"])
    erg = _anlegen()
    assert "error" not in erg, erg
    assert not _spalte(welt["db"], erg["id"], "bedient_von")


def test_das_feld_ist_unveraenderlich(welt, monkeypatch):
    """Herkunft wird nicht nachtraeglich umgeschrieben -- sonst ist die ganze
    Kette wertlos. Gleiche Zusicherung wie fuer source."""
    monkeypatch.setenv("BRAINLEHR_GEHEIMNIS", welt["bot"])
    erg = _anlegen()
    conn = sqlite3.connect(str(welt["db"]))
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE knowledge_nodes SET bedient_von='wer anders' WHERE id=?",
                         (erg["id"],))
            conn.commit()
    finally:
        conn.close()
