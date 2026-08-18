"""Testet melder/fremdrollen.py -- Melder fuer erfundene Subagenten und
fremde Rollennamen (Terra/Luna/Sol/Hermes) in ~/.claude/skills/*/SKILL.md.

Ergaenzt den eingebauten `--selftest` (synthetische Dateien in tmp) um eine
pytest-Huelle, damit er in der normalen Suite mitlaeuft -- Vorbild ist die
Subprocess-Isolation aus test_alle_selftests.py: der CLI-Flag ist der einzige
stabile Vertrag ueber alle Melder hinweg, kein interner Funktionsname."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
ROOT = _w
sys.path.insert(0, str(ROOT))

import melder.fremdrollen as fr  # noqa: E402


def test_selftest_subprocess() -> None:
    """Rot-vor-gruen liegt im Modul selbst (Gegenproben je Fall); hier nur
    sicherstellen, dass der Aufruf-Vertrag (--selftest, Exit 0) haelt."""
    r = subprocess.run(
        [sys.executable, str(ROOT / "melder" / "fremdrollen.py"), "--selftest"],
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "selftest ok" in r.stdout


def test_fremde_rollen_wortgrenze() -> None:
    assert fr.fremde_rollen_in("Terra orchestriert, Luna fuehrt aus.") == {"Terra", "Luna"}
    assert fr.fremde_rollen_in("Wir bauen Solidaritaet fuer Lunartage.") == set()
    assert fr.fremde_rollen_in("Kein Bezug hier.") == set()


def test_angebotene_agenten_beide_muster() -> None:
    text = (
        "| Task | Use |\n|---|---|\n| x | `erfunden-eins` |\n"
        "Main thread will spawn `erfunden-zwei` for the edit.\n"
        "use `nit:` instead of a suggestion.\n"
    )
    gefunden = fr.angebotene_agenten(text)
    assert "erfunden-eins" in gefunden
    assert "erfunden-zwei" in gefunden
    assert "nit" not in gefunden, "'use' allein ist kein Verbkontext-Treffer"


def test_vorhandene_agenten_ueber_frontmatter_und_builtin(tmp_path: Path) -> None:
    agenten = tmp_path / "agents"
    agenten.mkdir()
    (agenten / "eigener.md").write_text("---\nname: eigener\ndescription: x\n---\n")
    namen = fr.vorhandene_agenten(agenten)
    assert "eigener" in namen
    assert "compliance" not in namen  # nur echte Dateien + Konstanten, nichts geraten
    assert "Explore" in namen  # eingebaut


def test_bericht_meldet_nur_luecken(tmp_path: Path) -> None:
    (tmp_path / "skills" / "s").mkdir(parents=True)
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "echt.md").write_text("---\nname: echt\ndescription: x\n---\n")
    (tmp_path / "skills" / "s" / "SKILL.md").write_text(
        "---\nname: s\ndescription: x\n---\n"
        "| Task | Use |\n|---|---|\n"
        "| ok | `echt` |\n"
        "| luecke | `phantom` |\n"
        "Sol steuert hier nichts, nur ein Test.\n"
    )
    funde = fr.bericht(tmp_path)
    namen = {f["name"] for f in funde["erfunden"]}
    assert namen == {"phantom"}
    rollen = {r["rolle"] for r in funde["rollen"]}
    assert rollen == {"Sol"}


def test_render_hinweisrecht_text() -> None:
    leer = fr.render({"erfunden": [], "rollen": []})
    assert "keine Funde" in leer
    voll = fr.render({"erfunden": [{"datei": "x", "name": "phantom"}], "rollen": []})
    assert "Hinweisrecht, kein Veto" in voll
    assert "phantom" in voll
