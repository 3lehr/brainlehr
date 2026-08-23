"""Jedes Modul, das ein ausgeliefertes Modul importiert, muss mitgeliefert sein.

ANLASS, gemessen 2026-08-23 beim ERSTEN Lauf einer frischen Installation: Ein
`pip install brainlehr` startete gar nicht -- `ModuleNotFoundError: No module
named 'gegenstand'`. kern/gegenstand.py war zwei Tage zuvor entstanden (P16)
und in keine der beiden handgepflegten Paketlisten eingetragen worden.

WARUM STATISCH UND NICHT UEBER EINEN ECHTEN BAU: Ein Test, der ein Rad baut,
eine virtuelle Umgebung anlegt und den Server startet, misst dasselbe -- und
braucht dafuer rund eine halbe Minute. Er waere damit der langsamste Test des
Hauses und wuerde uebersprungen. Diese Pruefung liest den Baum und ist in
Millisekunden fertig; der echte Bau bleibt die Handprobe vor einer
Veroeffentlichung.

WAS SIE AUSDRUECKLICH MITNIMMT: Importe INNERHALB von Funktionen. Genau die
sind gefaehrlich -- ein verzoegerter Import faellt beim Start nicht auf,
sondern erst, wenn die Funktion laeuft. Beim Paketbau am 2026-08-21 waren zwei
solche Importe nur deshalb gefunden worden, weil jemand alle fuenf Wege von
Hand durchlief; einer davon war die Normkonflikt-Pruefung in knowledge_add,
im Server in ein try/except gehuellt. Ihr Fehlen waere eine lautlos
abgeschaltete Pruefung gewesen.
"""
from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SUCHORTE = ("", "kern", "haken", "melder", "migrationen", "schreibpruefstand")


def _paketliste() -> dict[str, str]:
    d = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    return d["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]


def _lokales_modul(name: str) -> Path | None:
    """Gibt es zu diesem Importnamen eine Datei IM REPO? Nur dann ist er
    unsere Sache -- Fremdpakete und die Standardbibliothek gehen uns hier
    nichts an."""
    for ort in SUCHORTE:
        p = REPO / ort / f"{name}.py" if ort else REPO / f"{name}.py"
        if p.exists():
            return p.relative_to(REPO)
    return None


def _importierte_namen(datei: Path) -> set[str]:
    """Alle Top-Level-Namen, die diese Datei importiert -- auch aus
    Funktionsruempfen (ast.walk statt nur ast.Module.body)."""
    namen: set[str] = set()
    baum = ast.parse(datei.read_text(encoding="utf-8", errors="replace"))
    for k in ast.walk(baum):
        if isinstance(k, ast.Import):
            namen.update(a.name.split(".")[0] for a in k.names)
        elif isinstance(k, ast.ImportFrom) and k.level == 0 and k.module:
            namen.add(k.module.split(".")[0])
    return namen


def test_jedes_importierte_hausmodul_ist_im_paket():
    liste = _paketliste()
    ausgeliefert = {q for q in liste if q.endswith(".py")}
    fehlend: dict[str, set[str]] = {}
    for quelle in sorted(ausgeliefert):
        pfad = REPO / quelle
        if not pfad.exists():
            pytest.fail(f"{quelle} steht in der Paketliste, existiert aber nicht")
        for name in _importierte_namen(pfad):
            ziel = _lokales_modul(name)
            if ziel is None:
                continue                      # Fremdpaket oder stdlib
            if str(ziel) not in ausgeliefert:
                fehlend.setdefault(str(ziel), set()).add(quelle)
    assert not fehlend, (
        "Diese Hausmodule werden von ausgelieferten Dateien importiert, sind "
        "aber NICHT im Paket -- eine frische Installation startet damit nicht:\n"
        + "\n".join(f"  {m}  <- gebraucht von {', '.join(sorted(v))}"
                    for m, v in sorted(fehlend.items())))


def test_beide_paketlisten_sind_deckungsgleich():
    """Es gibt ZWEI handgepflegte Listen -- sdist.only-include und
    wheel.force-include. Sie sind am 2026-08-23 auseinandergelaufen, ohne dass
    etwas anschlug. Zwei Listen derselben Sache altern immer auseinander; wenn
    schon zwei, dann wenigstens mit Wache."""
    d = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    ziele = d["tool"]["hatch"]["build"]["targets"]
    sdist = set(ziele["sdist"]["only-include"])
    rad = set(ziele["wheel"]["force-include"])
    assert sdist == rad, (
        f"nur in sdist: {sorted(sdist - rad)}\nnur im Rad: {sorted(rad - sdist)}")
