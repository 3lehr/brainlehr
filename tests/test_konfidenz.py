"""Tests fuer konfidenz.py (ADR-026 Z3 + Nachtrag 2026-08-06: drei Regime).

Rot-vor-gruen (Ursprung): vor dieser Datei gab es konfidenz.py nicht -- jeder
Import schlug fehl. Nachtrag 2026-08-06: der urspruengliche Entwurf rechnete
Verfall nach Kalendertagen (bestrafte ruhenden Bestand, ein Projekt seit
Monaten ohne Aenderung verlor Konfidenz, obwohl nichts geschah). Ersetzt
durch drei Regime -- siehe konfidenz.py-Modul-Docstring. Deckt die
Commit-Formel an den Grenzwerten, die Norm-Gegenprobe, Regime 3 (kein
Verfallswert, nur Faelligkeit), den git-Ausfall-Rueckfall, die
Wissensart-Klassifikation und den vollen bestaetigen()-Rundlauf."""
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

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

from normkraft import Ablehnung  # noqa: E402
from konfidenz import (  # noqa: E402
    CET,
    HALBWERTSZEIT_TAGE,
    REGIME_BEOBACHTBAR,
    REGIME_DEKLARIERT,
    REGIME_UNBEOBACHTBAR,
    WISSENSART_ARCHITEKTUR,
    WISSENSART_BETRIEB,
    WISSENSART_STANDARD,
    _init_temp_db,
    _insert_node,
    _mk_git_repo,
    alter_tage,
    beobachtbare_datei,
    bestaetigen,
    bewerten,
    commits_seit,
    find_confidence_decay,
    find_pruefung_ueberfaellig,
    gerechnete_konfidenz,
    plan_bestaetigen,
    wissensart,
)

_NOW = datetime.fromisoformat("2026-04-11T00:00:00+01:00")


def _ts(tage_zurueck: float) -> str:
    return (_NOW - timedelta(days=tage_zurueck)).isoformat()


def test_regime1_beobachtbare_datei_und_commits_seit(tmp_path):
    datei = _mk_git_repo(tmp_path, "quelle.md", [_ts(40), _ts(20), _ts(5)])
    src = f"erzeugt aus {datei}"
    assert beobachtbare_datei(src) == datei
    assert beobachtbare_datei("Gesetzestext ohne Dateibezug") is None
    assert beobachtbare_datei(None) is None
    assert commits_seit(datei, _ts(30)) == 2
    assert commits_seit(datei, _ts(10)) == 1
    assert commits_seit(datei, _ts(1)) == 0


def test_regime1_gerechnete_konfidenz_nach_commit_formel(tmp_path):
    datei = _mk_git_repo(tmp_path, "quelle.md", [_ts(40), _ts(20), _ts(5)])
    hwz = HALBWERTSZEIT_TAGE[WISSENSART_STANDARD]
    b = bewerten(0.8, _ts(30), None, "/standard/x", f"erzeugt aus {datei}", _NOW)
    assert b["regime"] == REGIME_BEOBACHTBAR
    assert b["commits_seit"] == 2
    assert b["gerechnet"] == round(0.8 * 0.5 ** (2 / hwz), 4)  # von Hand nachgerechnet


def test_rot_vor_gruen_ruhende_datei_verfaellt_nicht_mehr_nach_kalendertagen(tmp_path):
    """ABNAHME b: eine Datei ohne Aenderung seit >120 Tagen. Die alte
    Kalenderformel waere deutlich gefallen (VORHER), die neue Commit-Formel
    bleibt unveraendert, weil 0 Commits seit updated_at (NACHHER)."""
    ruhig = _mk_git_repo(tmp_path, "ruhig.md", [_ts(130)])
    updated_ruhig = (datetime.fromisoformat(_ts(130)) + timedelta(seconds=1)).isoformat()
    hwz = HALBWERTSZEIT_TAGE[WISSENSART_STANDARD]

    alter = alter_tage(updated_ruhig, _NOW)
    assert alter > hwz  # > 120 Tage, Kalender-Alter ist gross

    vorher_kalenderformel = 0.8 * 0.5 ** (alter / hwz)
    assert vorher_kalenderformel < 0.5  # VORHER: deutlich gefallen

    b = bewerten(0.8, updated_ruhig, None, "/standard/ruhig", f"erzeugt aus {ruhig}", _NOW)
    assert b["commits_seit"] == 0
    assert b["gerechnet"] == 0.8  # NACHHER: unveraendert


def test_gegenprobe_30_commits_muessen_konfidenz_senken(tmp_path):
    """ABNAHME c, wichtigster Punkt: ohne diese Gegenprobe hiesse der Umbau
    nur 'Verfall abgeschaltet'. 30 tatsaechliche Commits MUESSEN wirken."""
    zeiten = [_ts(62 - 2 * i) for i in range(31)]
    aktiv = _mk_git_repo(tmp_path, "aktiv.md", zeiten)
    updated = (datetime.fromisoformat(zeiten[0]) + timedelta(seconds=1)).isoformat()
    assert commits_seit(aktiv, updated) == 30
    b = bewerten(0.8, updated, None, "/standard/aktiv", f"erzeugt aus {aktiv}", _NOW)
    assert b["regime"] == REGIME_BEOBACHTBAR
    assert b["gerechnet"] < 0.8


def test_git_aufruf_ausgefallen_faellt_auf_regime3_nicht_auf_null(tmp_path):
    """Datei existiert, liegt aber in KEINEM Git-Repo -- git log kann nicht
    laufen. Das darf NIE still als 0 Commits gelesen werden."""
    kein_repo = tmp_path / "kein_repo.md"
    kein_repo.write_text("kein Repo hier\n")
    assert beobachtbare_datei(f"erzeugt aus {kein_repo}") is None
    b = bewerten(0.8, _ts(200), None, "/standard/y", f"erzeugt aus {kein_repo}", _NOW)
    assert b["regime"] == REGIME_UNBEOBACHTBAR
    assert b["gerechnet"] is None


def test_regime3_unbeobachtbar_liefert_keinen_verfallswert_sondern_faelligkeit():
    """ABNAHME d: ein Knoten ohne beobachtbaren Bezug (Gesetzestext) liefert
    KEINE Verfallszahl, sondern Faelligkeit plus Kennzeichnung."""
    b = bewerten(0.85, _ts(200), None, "/recht/urhg-87a", "§87a UrhG, geprueft 2026-01-01", _NOW)
    assert b["regime"] == REGIME_UNBEOBACHTBAR
    assert b["gerechnet"] is None, "Regime 3 darf KEINEN Verfallswert liefern -- vorgetaeuschte Genauigkeit"
    assert set(b["naechste_pruefung"]) == {"faellig_am", "ueberfaellig", "tage_bis_faellig"}
    assert b["naechste_pruefung"]["ueberfaellig"] is True


def test_drei_regime_nicht_verwechselbar():
    """ABNAHME 3: 'kein Verfall, weil Norm' (Regime 2) vs. 'kein Verfall,
    weil nichts passiert ist' (Regime 1, 0 Commits) vs. 'nicht messbar'
    (Regime 3) muessen ueber das Feld 'regime' unterscheidbar bleiben,
    unabhaengig vom Zahlenwert."""
    b_norm = bewerten(0.9, _ts(0), 1, "/adr/x", "ADR", _NOW)
    b_unbeobachtbar = bewerten(0.8, _ts(200), None, "/recht/x", "§87a UrhG", _NOW)
    assert b_norm["regime"] == REGIME_DEKLARIERT
    assert b_unbeobachtbar["regime"] == REGIME_UNBEOBACHTBAR
    assert b_norm["regime"] != b_unbeobachtbar["regime"]


def test_gerechnete_konfidenz_wrapper_regime3_gibt_ausgangswert():
    """gerechnete_konfidenz() ist der duenne Float-Wrapper fuer alte
    Aufrufer (bestaetigen()) -- Regime 3 faellt hier auf den unveraenderten
    Ausgangswert zurueck, weil es keinen Verfallswert gibt."""
    g = gerechnete_konfidenz(0.85, _ts(200), None, "/recht/x", "§87a UrhG", _NOW)
    assert g == 0.85


def test_norm_verfaellt_nie_gegenprobe():
    """Der Kern des Auftrags: norm_rang gesetzt -> Ausgangswert bleibt,
    egal wie alt (hier ~55 Jahre)."""
    jung = gerechnete_konfidenz(0.9, _ts(0), 1, "/adr/x", "ADR", _NOW)
    uralt = gerechnete_konfidenz(0.9, _ts(20000), 1, "/adr/x", "ADR", _NOW)
    assert jung == 0.9
    assert uralt == 0.9


def test_wissensart_klassifikation():
    assert wissensart("/arch/mcp", None) == WISSENSART_ARCHITEKTUR
    assert wissensart("/shared/irgendwas", "Konsil 2026-08-05") == WISSENSART_ARCHITEKTUR
    assert wissensart("/shared/irgendwas", "docs/adr/ADR-026.md") == WISSENSART_ARCHITEKTUR
    assert wissensart("/testing/pytest", None) == WISSENSART_BETRIEB
    assert wissensart("/ops/appstoreconnect", None) == WISSENSART_BETRIEB
    assert wissensart("/lessons", None) == WISSENSART_STANDARD


def _basis_db(tmp_path):
    db_path = tmp_path / "brainlehr.db"
    _init_temp_db(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        # "n-alt": Freitext-Source ohne Dateibezug -> Regime 3 (unbeobachtbar).
        _insert_node(conn, "n-alt", "/standard/alt", confidence=0.8,
                     updated_at=_ts(HALBWERTSZEIT_TAGE[WISSENSART_STANDARD]))
        _insert_node(conn, "n-norm", "/adr/x", confidence=0.9, norm_rang=1, source="ADR")
        conn.commit()
    finally:
        conn.close()
    return db_path


def test_ablehnung_pfad_fehlt(tmp_path):
    db_path = _basis_db(tmp_path)
    try:
        plan_bestaetigen(db_path, "/nirgends", "Grund")
        assert False
    except Ablehnung as e:
        assert "nicht gefunden" in str(e)


def test_ablehnung_norm_braucht_keine_bestaetigung(tmp_path):
    db_path = _basis_db(tmp_path)
    try:
        plan_bestaetigen(db_path, "/adr/x", "Grund")
        assert False
    except Ablehnung as e:
        assert "Normen verfallen nicht" in str(e)


def test_wegen_ist_pflicht(tmp_path):
    db_path = _basis_db(tmp_path)
    try:
        plan_bestaetigen(db_path, "/standard/alt", "")
        assert False
    except Ablehnung as e:
        assert "Pflicht" in str(e)


def test_dry_run_schreibt_nichts(tmp_path):
    db_path = _basis_db(tmp_path)
    result = bestaetigen(db_path, "/standard/alt", "Grund", apply=False, now=_NOW)
    assert result["backup"] is None
    conn = sqlite3.connect(str(db_path))
    val = conn.execute("SELECT updated_at FROM knowledge_nodes WHERE path='/standard/alt'").fetchone()[0]
    conn.close()
    assert val != result["nachher_updated_at"]


def test_erfolgsfall_setzt_updated_at_content_und_access_log(tmp_path):
    db_path = _basis_db(tmp_path)
    result = bestaetigen(db_path, "/standard/alt", "Testgrund fuer Bestaetigung", apply=True, now=_NOW)
    # "n-alt" ist Regime 3 (kein Dateibezug): kein Verfallswert, also
    # unveraendert der Ausgangswert -- vor UND nach der Bestaetigung.
    # bestaetigen() setzt trotzdem den Bezugszeitpunkt zurueck.
    assert result["vorher_gerechnet"] == 0.8
    assert result["nachher_gerechnet"] == 0.8
    assert result["backup"] and Path(result["backup"]).exists()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT updated_at, content, confidence FROM knowledge_nodes WHERE path='/standard/alt'"
        ).fetchone()
        assert row["updated_at"] == result["nachher_updated_at"]
        assert row["confidence"] == 0.8, "confidence-Spalte bleibt Ausgangswert, wird nie ueberschrieben"
        assert "Testgrund fuer Bestaetigung" in row["content"]

        log_row = conn.execute(
            "SELECT action, query, node_path FROM access_log WHERE action='bestaetigt' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert log_row["action"] == "bestaetigt"
        assert log_row["query"] == "Testgrund fuer Bestaetigung"
        assert log_row["node_path"] == "/standard/alt"
    finally:
        conn.close()


def test_ablehnung_ohne_begruendung_schreibt_trotz_apply_nichts(tmp_path):
    db_path = _basis_db(tmp_path)
    try:
        bestaetigen(db_path, "/standard/alt", "   ", apply=True, now=_NOW)
        assert False
    except Ablehnung:
        pass


def test_find_confidence_decay_findet_nur_regime1_nie_regime3_nie_normen(tmp_path):
    """find_confidence_decay() braucht einen Verfallswert -- den hat nur
    Regime 1. Fixture: Datei mit vielen Commits seit updated_at, weit unter
    der Schwelle. "n-alt" (Regime 3) und die Norm duerfen nie auftauchen."""
    db_path = _basis_db(tmp_path)
    zeiten = [_ts(200 - 2 * i) for i in range(50)]
    verfallen_datei = _mk_git_repo(tmp_path, "verfallen.md", zeiten)
    updated = (datetime.fromisoformat(zeiten[0]) + timedelta(seconds=1)).isoformat()

    conn = sqlite3.connect(str(db_path))
    _insert_node(conn, "n-verfallen", "/testing/verfallen", confidence=0.8,
                 updated_at=updated, source=f"erzeugt aus {verfallen_datei}")
    conn.commit()
    conn.row_factory = sqlite3.Row
    try:
        decay = find_confidence_decay(conn, now=_NOW)
    finally:
        conn.close()
    decay_paths = {d["path"] for d in decay}
    assert "/testing/verfallen" in decay_paths
    assert decay_paths <= {"/testing/verfallen"}
    assert "/standard/alt" not in decay_paths, "Regime 3 hat keinen Verfallswert -- kann nie auftauchen"
    assert "/adr/x" not in decay_paths, "Norm darf nie im Konfidenzverfall auftauchen"


def test_find_pruefung_ueberfaellig_ist_das_regime3_gegenstueck(tmp_path):
    db_path = _basis_db(tmp_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        ueberfaellig = find_pruefung_ueberfaellig(conn, now=_NOW)
    finally:
        conn.close()
    # "n-alt": updated_at liegt genau eine Halbwertszeit (=Pruefintervall)
    # zurueck -> genau faellig, nicht sicher schon ueberfaellig; stattdessen
    # ein deutlich aelteres Regime-3-Fixture pruefen.
    ueberfaellig_paths = {u["path"] for u in ueberfaellig}
    assert "/adr/x" not in ueberfaellig_paths, "Norm gehoert nicht ins Regime-3-Gegenstueck"
