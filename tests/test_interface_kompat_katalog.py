"""Gates zu docs/REQUIREMENTS_INTERFACE_KOMPAT.md (Teilkatalog zu BDW-F07).

Die vier ROTEN Gates unten sind mit xfail(strict=True) markiert: sie messen
Nähte, die es heute nachweislich nicht gibt (gemessener Ausgangsstand im
Katalog). Strikt heißt: sobald die Naht gebaut ist, wird der Test hier laut,
statt still grün zu verrotten -- ein Rot, das niemand sieht, ist keins.
"""

import json
import sqlite3
import sys
from pathlib import Path

import pytest

from kern import domaene

WURZEL = Path(__file__).resolve().parents[1]
KATALOG = WURZEL / "docs" / "REQUIREMENTS_INTERFACE_KOMPAT.md"
ROOT = WURZEL / "docs" / "REQUIREMENTS_BRAINLEHR.md"
OPENLEHR = Path("/Volumes/daten/Begod2026/openlehr_einzelunternehmer")

INTERFACES = (
    "INT-PKG-001", "INT-VER-001", "INT-VER-002", "INT-API-001", "INT-API-002",
    "INT-REG-001", "INT-DNST-001", "INT-UPD-001", "INT-SNAP-001", "INT-GATE-001",
)


def _paket(**zusatz):
    basis = {
        "domaene": "vertragsprobe",
        "bezeichnung": "Vertragsprobe",
        "herkunft": "test",
        "stand": "2026-08-18T05:00:00+0200",
        "quellen": {"z1": {"bezeichnung": "Betriebsausgaben"}},
        "regeln": [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}],
        "contract_version": 1,
        "dienst": {},
        "oberflaeche": {"fassung": 1, "bildschirme": []},
    }
    basis.update(zusatz)
    return basis


@pytest.fixture
def frische_db(tmp_path):
    db = tmp_path / "vertrag.db"
    conn = sqlite3.connect(str(db))
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    conn.close()
    return db


# --- gruen: der Katalog ist genau EIN untergeordneter Teilkatalog ----------

def test_katalog_ist_untergeordnet_und_vollstaendig():
    text = KATALOG.read_text(encoding="utf-8")
    assert "Untergeordnet zu `docs/REQUIREMENTS_BRAINLEHR.md`; lokale IDs sind nur Umsetzungsgates." in text
    assert "BDW-F07" in text, "Ohne Anker am Root waere das ein zweiter Root-Katalog."
    zeilen = {z.split("|")[1].strip(): z for z in text.splitlines() if z.startswith("| INT-")}
    assert set(zeilen) == set(INTERFACES)
    for kennung, zeile in zeilen.items():
        assert f"TEST-{kennung.removeprefix('INT-')}" in zeile or "TEST-INT-" in zeile
        assert zeile.count("|") == 7, f"{kennung}: Producer/Consumer-Matrix unvollstaendig"
    assert "contract_version" in text and "| `1` |" in text
    assert ROOT.read_text(encoding="utf-8").count("docs/REQUIREMENTS_INTERFACE_KOMPAT.md") == 1


# --- rot: die Naht, die es noch nicht gibt --------------------------------

def test_int_ver_001_unbekannte_major_wird_abgewiesen():
    """Fail-closed statt raten -- OPENLEHR_KERNEL_UND_APP_VERTRAG_V1 §2 Nr. 1.
    Rot vor gruen: vor kern/domaene._VERTRAG_VERSION nahm pruefe() beide
    Faelle an (XPASS(strict) am 2026-08-18)."""
    assert domaene.pruefe(_paket())["angenommen"] is True, "contract_version 1 ist die gueltige Fassung"

    ohne = _paket()
    del ohne["contract_version"]
    assert domaene.pruefe(ohne)["angenommen"] is False
    assert "contract_version" in domaene.pruefe(ohne)["grund"]

    kuenftig = domaene.pruefe(_paket(contract_version=2))
    assert kuenftig["angenommen"] is False
    assert "Fassung" in kuenftig["grund"]


def test_int_ver_002_alle_echten_pakete_tragen_die_version():
    """Ein Vertrag, den die realen Pakete nicht erfuellen, ist keiner."""
    pakete = [WURZEL / "pakete" / "steuer.domaene.json",
              OPENLEHR / "wissen" / "einzelunternehmer.domaene.json"]
    for pfad in pakete:
        assert pfad.exists(), f"{pfad} fehlt -- rot, nicht uebersprungen"
        assert json.loads(pfad.read_text(encoding="utf-8"))["contract_version"] == 1


@pytest.mark.xfail(strict=True, reason="INT-UPD-001 nicht gebaut: speichere() nutzt INSERT OR IGNORE")
def test_int_upd_001_reimport_aktualisiert_gleiche_kennung(frische_db):
    domaene.speichere(_paket(), db=frische_db)
    neu = _paket(quellen={"z1": {"bezeichnung": "Betriebsausgaben, neue Fassung"}})
    domaene.speichere(neu, db=frische_db)
    with sqlite3.connect(str(frische_db)) as conn:
        inhalt = " ".join(r[0] or "" for r in conn.execute("select summary from knowledge_nodes"))
    assert "neue Fassung" in inhalt


@pytest.mark.xfail(strict=True, reason="INT-DNST-001 nicht gebaut: dienst wird geprueft, aber nie persistiert")
def test_int_dnst_001_dienst_wird_persistiert(frische_db):
    domaene.speichere(_paket(dienst={"kennung": "de.vertragsprobe.dienst", "start": "manuell"}), db=frische_db)
    with sqlite3.connect(str(frische_db)) as conn:
        treffer = conn.execute(
            "select count(*) from knowledge_nodes where tags like '%art:dienst%'"
        ).fetchone()[0]
    assert treffer == 1


@pytest.mark.xfail(strict=True, reason="INT-GATE-001 nicht gebaut: der Cross-Repo-Test darf noch skippen")
def test_int_gate_001_cross_repo_gate_skippt_nicht():
    quelle = OPENLEHR / "dienst" / "tests" / "test_euer_vorschlag.py"
    assert quelle.exists(), "Gegenpfad fehlt -- das ist rot, nicht uebersprungen"
    assert "pytest.skip" not in quelle.read_text(encoding="utf-8")
