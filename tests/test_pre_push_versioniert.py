"""Quelle gegen Betrieb: laeuft der installierte pre-push-Haken das, was im
Repo steht?

ANLASS, gemessen 2026-08-18: .git/hooks/pre-push trug neun Verweise auf
melder/kartenstand.py, melder/dokumentzugang.py und melder/ablaufpflicht.py --
der geteilte Installer hub/scripts/install_push_guard.py kannte davon KEINEN,
und `git ls-files | grep pre-push` fand nichts. Die drei Waechter lebten
ausschliesslich in einer unversionierten Datei: ein `--force`-Lauf des
Installers, ein frischer Klon oder ein neuer Arbeitsbaum haette sie still
entfernt, und der Commit, der sie eingefuehrt hat, haette sie weiter behauptet
(dieselbe Klasse wie L-083b95).

Dieser Test prueft NICHT Zeichengleichheit -- der lokale Haken darf
Zusaetze tragen. Er prueft, dass jeder WAECHTER, den die versionierte Fassung
aufruft, auch im installierten Haken vorkommt. Fehlt einer, ist er im Betrieb
weg, egal was im Repo steht."""

import re
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]
VERSIONIERT = WURZEL / "haken" / "git" / "pre-push"
INSTALLIERT = WURZEL / ".git" / "hooks" / "pre-push"

# Was der Haken aufruft: melder/x.py oder haken/x.py hinter $repo_root.
_AUFRUF = re.compile(r"\$repo_root/((?:melder|haken)/[a-z_]+\.py)")


def waechter(text: str) -> set[str]:
    return set(_AUFRUF.findall(text))


def test_versionierte_fassung_existiert_und_laeuft():
    assert VERSIONIERT.exists(), "haken/git/pre-push fehlt -- der Haken waere wieder unversioniert"
    assert waechter(VERSIONIERT.read_text(encoding="utf-8")), "kein einziger Waechter im Haken"


def test_jeder_versionierte_waechter_existiert_als_datei():
    for rel in sorted(waechter(VERSIONIERT.read_text(encoding="utf-8"))):
        assert (WURZEL / rel).exists(), f"{rel} wird im Haken gerufen, existiert aber nicht"


def test_installierter_haken_kennt_jeden_versionierten_waechter():
    """Der eigentliche Zweck: nennt der laufende Haken dieselben Waechter?"""
    if not INSTALLIERT.exists():
        pytest.fail("kein .git/hooks/pre-push installiert -- kein Waechter laeuft. "
                    "Installieren: cp haken/git/pre-push .git/hooks/pre-push && chmod +x")
    fehlend = waechter(VERSIONIERT.read_text(encoding="utf-8")) - waechter(
        INSTALLIERT.read_text(encoding="utf-8"))
    assert not fehlend, (
        "im Betrieb fehlen Waechter, die das Repo vorschreibt: " + ", ".join(sorted(fehlend))
        + " -- neu installieren: cp haken/git/pre-push .git/hooks/pre-push && chmod +x")
