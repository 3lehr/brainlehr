from pathlib import Path
import pytest

def test_bdw_p21_ac1_kein_import_aus_kern():
    """BDW-P21-AC1: Der Adapter enthaelt keinen Import aus dem brainlehr-Kern."""
    # parents[2] verweist auf Begod2026/ (über tests/ und brainlehr/)
    hermes_dir = Path(__file__).resolve().parents[2] / "hermes-brainlehr"
    
    if not hermes_dir.exists():
        pytest.skip("hermes-brainlehr Repository nicht gefunden")
        
    for p in hermes_dir.rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        assert "import kern" not in text
        assert "from kern " not in text
        assert "import brainlehr" not in text
        assert "from brainlehr " not in text

def test_bdw_p21_ac2_lizenzreichweite():
    """BDW-P21-AC2: Die Lizenzdatei des Adapters nennt ausdruecklich, was sie NICHT deckt."""
    hermes_dir = Path(__file__).resolve().parents[2] / "hermes-brainlehr"
    
    if not hermes_dir.exists():
        pytest.skip("hermes-brainlehr Repository nicht gefunden")
        
    notice_file = hermes_dir / "NOTICE"
    text = notice_file.read_text(encoding="utf-8")
    assert "Installing this adapter does not install brainlehr" in text
