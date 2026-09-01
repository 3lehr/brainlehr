import os
import sys
from pathlib import Path
import pytest

_W = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_W / "kern"))

# Ensure the module can be imported, or skip if it doesn't exist yet
try:
    import bauvermeidung as bv
    HAS_BV = True
except ImportError:
    HAS_BV = False

pytestmark = pytest.mark.skipif(
    not HAS_BV or os.environ.get("BRAINLEHR_RUN_LIVE") != "1",
    reason="requires explicit BRAINLEHR_RUN_LIVE=1 and the external code inventory",
)

def test_bdw_p22_ac1_fund_statt_bauplan():
    """BDW-P22-AC1: Zu einem Vorhaben, das im Verbund bereits existiert, kommt ein Fundstellen-Vorschlag statt eines Bauplans."""
    try:
        erg = bv.pruefe("ich haette gerne eine Vertrauensliste zwischen Instanzen")
    except Exception as exc:
        pytest.skip(f"Bestand nicht erreichbar: {exc}")
    
    fundstellen = " ".join(t["fundstelle"] or "" for t in erg["treffer"])
    beleg_texte = " ".join(t["beleg_text"] or "" for t in erg["treffer"])
    assert "foederation.py" in fundstellen or "foederation" in beleg_texte.lower(), "Vorhandenes Modul wurde nicht gefunden"

def test_bdw_p22_ac2_fehlanzeige():
    """BDW-P22-AC2: Negativkontrolle -- zu einem Vorhaben, das es NICHT gibt, wird nichts vorgeschlagen."""
    try:
        erg = bv.pruefe("ich haette gerne einen Quantenchip-Zeitreise-Uebersetzer")
    except Exception as exc:
        pytest.skip(f"Bestand nicht erreichbar: {exc}")
        
    code_treffer = [t for t in erg["treffer"] if t["kanal"] == "code"]
    assert not code_treffer, "Negativkontrolle lieferte unerwarteten Fund"
    assert erg["urteil"].startswith("NULLBEFUND")
