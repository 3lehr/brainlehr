"""Tests fuer BEGOD_KNOWLEDGE_DB (Auftrag 2026-08-06, Fremdclient-Test-Vorbereitung).

Zweck der Variable: knowledge_mcp_server.py haengte DB_PATH fest an
__file__ -- kein Betrieb ausserhalb des Verzeichnisses moeglich, kein
gefahrloser Test gegen einen fremden MCP-Client (LM Studio/qwen).

Zwei Dinge werden hier geprueft:
1. Rueckwaertsvertraeglichkeit: ohne gesetzte Variable exakt der alte,
   fest verdrahtete Pfad.
2. Die Zusicherung, die den Fremdclient-Test ueberhaupt sicher macht --
   zeigt BEGOD_KNOWLEDGE_DB auf die ECHTE brainlehr.db, bricht sie ab,
   damit ein fremder Client nie versehentlich gegen den echten Bestand
   schreibt.
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

import importlib.util
import os
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
REAL_DB = SHARED_KNOWLEDGE / "brainlehr.db"


def _load_server_module():
    """Frisches Modul-Objekt, damit DB_PATH bei jedem Aufruf neu aus der
    aktuellen Umgebung berechnet wird (Modul-Level-Konstante, kein Reload
    ueber sys.modules moeglich).

    SEIT 2026-08-23 reicht das allein nicht mehr: knowledge_mcp_server holt
    seinen Pfad ueber `import ort`, und `ort` steht dann schon mit dem ZUERST
    berechneten Wert in sys.modules -- gesetzt von tests/conftest.py, das den
    ganzen Lauf auf einen Schnappschuss umbiegt. Ein frisches Servermodul
    bekaeme also den alten Pfad zurueck, und der Test pruefte nichts mehr.
    Deshalb werden BEIDE Ladewege derselben Datei mitverworfen ("ort" per
    sys.path, "haken.ort" als Namespace-Paket)."""
    for _mod in ("ort", "haken.ort", "haken"):
        sys.modules.pop(_mod, None)
    spec = importlib.util.spec_from_file_location(
        "knowledge_mcp_server_envtest", SHARED_KNOWLEDGE / "knowledge_mcp_server.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ohne_env_var_unveraendertes_verhalten(monkeypatch):
    # BEIDE Namen wegraeumen. Der Test stammt aus der Zeit, als es nur den
    # alten gab; seit 2026-08-11 sticht BRAINLEHR_DB, und seit 2026-08-23
    # setzt conftest.py ihn fuer den ganzen Lauf. Ein Test, der seine eigene
    # Voraussetzung nicht herstellt, prueft die Voraussetzung des Nachbarn.
    monkeypatch.delenv("BEGOD_KNOWLEDGE_DB", raising=False)
    monkeypatch.delenv("BRAINLEHR_DB", raising=False)
    mod = _load_server_module()
    assert mod.DB_PATH == REAL_DB


def test_env_var_ueberschreibt_pfad(monkeypatch, tmp_path):
    testkopie = tmp_path / "testkopie.db"
    # Der ALTE Name wird gesetzt und der neue weggeraeumt -- genau das ist der
    # Fall, den dieser Test sichert: die Uebergangsform muss weiter wirken.
    monkeypatch.delenv("BRAINLEHR_DB", raising=False)
    monkeypatch.setenv("BEGOD_KNOWLEDGE_DB", str(testkopie))
    mod = _load_server_module()
    assert mod.DB_PATH == testkopie


def assert_not_real_db(db_path: Path) -> None:
    """Zusicherung fuer den Fremdclient-Test: bricht ab, wenn BEGOD_KNOWLEDGE_DB
    auf die echte brainlehr.db zeigt. Reiner Pfadvergleich (resolve()), keine
    Datenbankverbindung -- funktioniert auch, wenn die Datei gerade WAL-Locks haelt."""
    if Path(db_path).resolve() == REAL_DB.resolve():
        raise AssertionError(
            f"BEGOD_KNOWLEDGE_DB zeigt auf die echte Datenbank ({REAL_DB}) -- "
            "Fremdclient-Test abgebrochen, um sie nicht zu gefaehrden."
        )


def test_zusicherung_bricht_bei_echter_db_ab():
    with pytest.raises(AssertionError, match="echte Datenbank"):
        assert_not_real_db(REAL_DB)


def test_zusicherung_laesst_testkopie_durch(tmp_path):
    testkopie = tmp_path / "testkopie.db"
    testkopie.touch()
    assert_not_real_db(testkopie)  # darf nicht werfen
