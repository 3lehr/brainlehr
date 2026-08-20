"""Die Urheber-Erkennung darf nicht am Verbundnamen des Betreibers haengen.

DER BEFUND (2026-08-20, gefunden beim oeffentlichen Export): In
URHEBER_MERKMALE stand "/begod2026/hub/claude.md" fest verdrahtet -- der
Verzeichnisname des Betreibers. Bei jedem anderen Nutzer greift die Regel
nicht, und eine vom Betreiber entschiedene Rang-2-Norm gilt dort als
fremdbestimmt.

DAS BESONDERE DARAN IST DIE BEGRUENDUNG DANEBEN: Zwei Zeilen darueber steht
seit dem 2026-08-10 als Kommentar, warum genau das falsch ist -- "in einem
weitergebbaren Repo ist das ein Personenbezug, und bei jedem anderen Nutzer
waere das Muster obendrein falsch". Fuer die globale CLAUDE.md wurde daraus
Path.home(); fuer die hub-Datei in der naechsten Zeile nicht. Die Einsicht
war da und wurde zur Haelfte angewandt.
"""
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent.parent / "kern"),
                str(Path(__file__).resolve().parent.parent)]
from herkunft_normentscheider import ist_urheber_betreiber  # noqa: E402


def test_hub_hausregeln_unter_fremdem_verbundnamen():
    """Der Fall, den es bei jedem anderen Nutzer gibt und hier nie gab."""
    assert ist_urheber_betreiber("erzeugt aus /home/andere/projekte/hub/CLAUDE.md")
    assert ist_urheber_betreiber("erzeugt aus /srv/arbeit/hub/CLAUDE.md (Stand X)")


def test_hub_hausregeln_hier_weiterhin_erkannt():
    """Gegenprobe: der bisherige Fall darf nicht verloren gehen."""
    assert ist_urheber_betreiber("erzeugt aus /Volumes/daten/Begod2026/hub/CLAUDE.md")


def test_fremdnorm_sticht_weiterhin():
    """NEGATIVFALL: Die Lockerung darf die Fremdnorm-Regel nicht aushebeln.
    Eine aufgezeichnete fremde Regel bleibt fremd, auch wenn der Pfad passt."""
    assert not ist_urheber_betreiber(
        "erzeugt aus /srv/hub/CLAUDE.md, zitiert BGH-Urteil")
    assert not ist_urheber_betreiber("erzeugt aus buckeberg/recht/BGH-Urteil")


def test_beliebiger_pfad_ohne_hub_trifft_nicht():
    """NEGATIVFALL zur Weite des Musters: nicht jede CLAUDE.md ist die des
    Betreibers -- nur die globale (ueber Path.home) und die im hub."""
    assert not ist_urheber_betreiber("erzeugt aus /srv/fremd/projekt/CLAUDE.md")
