"""Nach dem Umzug von hub/shared-knowledge nach brainlehr: kein Pfad darf
noch ueber den Uebergangsverweis laufen, und keine abgeleitete Wurzel darf
eine Ebene zu hoch zeigen.

Warum als Test und nicht als Sichtpruefung: beide Fehler sind stumm. Ein
Pfad ueber den Symlink funktioniert, solange der Symlink lebt, und faellt
danach lautlos aus (`|| true` in den Hooks). Eine Wurzel eine Ebene zu hoch
laesst jeden relativen `source` unbeobachtbar werden -- die Konfidenz faellt
dann still in Regime 3, statt zu melden.
"""
from pathlib import Path
import sys

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

UEBERGANGSVERWEIS = "hub/shared-knowledge"


def test_keine_pfadkonstante_laeuft_ueber_den_uebergangsverweis():
    """Konstanten, die eine Datei adressieren -- nicht Kommentare."""
    import build_node_index
    import kanten_aus_lehren

    for wert in (build_node_index.DB, build_node_index.OUT,
                 kanten_aus_lehren.DB_PATH):
        assert UEBERGANGSVERWEIS not in str(wert), f"{wert} laeuft ueber den Symlink"
        assert Path(wert).parent.resolve() == WURZEL, f"{wert} liegt nicht in brainlehr"


def test_verbundwurzel_zeigt_auf_begod2026_nicht_eine_ebene_hoeher():
    """brainlehr liegt jetzt NEBEN hub, nicht darin -- eine Ebene weniger.

    Gegenprobe in beide Richtungen: die Wurzel muss einen bekannten
    relativen Bezug aufloesen UND darf nicht einfach irgendein Verzeichnis
    sein, in dem zufaellig alles existiert.
    """
    import konfidenz

    assert (konfidenz.BEGOD_ROOT / "hub" / "scripts").is_dir()
    assert (konfidenz.BEGOD_ROOT / "brainlehr").is_dir(), \
        "brainlehr liegt NEBEN hub, nicht darin"
    assert konfidenz.beobachtbare_datei("hub/scripts/mycel.py") is not None
    assert konfidenz.beobachtbare_datei("gibt/es/nicht.py") is None


if __name__ == "__main__":
    test_keine_pfadkonstante_laeuft_ueber_den_uebergangsverweis()
    test_verbundwurzel_zeigt_auf_begod2026_nicht_eine_ebene_hoeher()
    print("ok")
