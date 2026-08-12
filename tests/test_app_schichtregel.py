"""Zwei Zusicherungen der Schichtregel aus docs/PLAN_APP_SCHICHTEN_2026-08-12.md,
Abschnitt "Die Regel, die das Ganze zusammenhaelt":

1. BrainlehrCore (Schalenkern) kennt keine Oberflaechenbibliothek: kein
   `import SwiftUI`, kein `import AppKit`. Wer dort eine Fensterklasse
   benutzt, macht die spaetere Portierung auf Windows/Linux still teurer.
2. app/Sources spricht mit dem Bestand nur ueber den Dienst: nirgends ein
   direkter SQLite-Zugriff aus Swift.

VERBOT STATT RATSCHE (anders als tests/test_naht_ratsche.py und
tests/test_produktivcode_nutzt_ort.py): dort gab es beim Einziehen der Wache
bereits Bestand, der sofort rot geworden waere. Hier ist der Schalenkern laut
Auftrag zwei Dateien gross und der Bestand heute (2026-08-12) sauber -- die
Wache wird VOR dem Wachsen eingezogen, wie der Plan es verlangt ("eine Regel,
die erst nach dem Bau eingezogen wird, findet nur noch Altlasten"). Eine
Ratsche waere hier die falsche Bauform: sie erlaubt genau das Wachsen, das
verhindert werden soll.

Kommentarzeilen zaehlen nicht, aus demselben Grund wie in
tests/test_naht_ratsche.py dokumentiert: eine Datei, die im Kommentar
erklaert, warum hier KEIN `import SwiftUI` steht, wuerde sich sonst selbst
anzeigen. Nur einzeilige `//`-Kommentare werden erkannt (kein `/* */` ueber
mehrere Zeilen) -- dieselbe bewusste Vereinfachung wie bei den Python-Wachen,
die auch nur eine Kommentarform abdecken.
"""
from __future__ import annotations

import re
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
QUELLEN = WURZEL / "app" / "Sources"
KERN = QUELLEN / "BrainlehrCore"

IMPORT_VERBOTEN = re.compile(r"^\s*import\s+(SwiftUI|AppKit)\b")
SQLITE_VERBOTEN = re.compile(r"\bsqlite3\b", re.IGNORECASE)


def _codezeile(zeile: str) -> str:
    """Schneidet einen einzeiligen '//'-Kommentar ab. Ein String-Literal mit
    '//' gibt es im heutigen Bestand nicht; dieselbe bewusste Grenze wie bei
    den Python-Wachen (sie erkennen auch nur '#')."""
    return zeile.split("//", 1)[0]


def _swift_dateien(basis: Path) -> list[Path]:
    return sorted(basis.rglob("*.swift")) if basis.is_dir() else []


def oberflaechenimporte_im_kern() -> dict[str, list[str]]:
    treffer: dict[str, list[str]] = {}
    for datei in _swift_dateien(KERN):
        fundstellen = [
            f"{datei.relative_to(WURZEL)}:{nr}: {zeile.strip()}"
            for nr, zeile in enumerate(datei.read_text(encoding="utf-8").splitlines(), start=1)
            if IMPORT_VERBOTEN.match(_codezeile(zeile))
        ]
        if fundstellen:
            treffer[str(datei.relative_to(WURZEL))] = fundstellen
    return treffer


def sqlite_zugriffe_in_der_schale() -> dict[str, list[str]]:
    treffer: dict[str, list[str]] = {}
    for datei in _swift_dateien(QUELLEN):
        fundstellen = [
            f"{datei.relative_to(WURZEL)}:{nr}: {zeile.strip()}"
            for nr, zeile in enumerate(datei.read_text(encoding="utf-8").splitlines(), start=1)
            if SQLITE_VERBOTEN.search(_codezeile(zeile))
        ]
        if fundstellen:
            treffer[str(datei.relative_to(WURZEL))] = fundstellen
    return treffer


def test_schalenkern_kennt_keine_oberflaechenbibliothek():
    dateien = _swift_dateien(KERN)
    assert dateien, f"keine .swift-Dateien unter {KERN} gefunden -- Wache prueft nichts"

    treffer = oberflaechenimporte_im_kern()
    assert not treffer, (
        "BrainlehrCore importiert eine Oberflaechenbibliothek: "
        + "; ".join(z for zeilen in treffer.values() for z in zeilen)
        + " -- das macht die spaetere Portierung auf Windows/Linux still "
        "teurer (docs/PLAN_APP_SCHICHTEN_2026-08-12.md). SwiftUI/AppKit "
        "gehoeren ausschliesslich in app/Sources/BrainlehrApp."
    )


def test_schale_oeffnet_keine_datenbank_direkt():
    dateien = _swift_dateien(QUELLEN)
    assert dateien, f"keine .swift-Dateien unter {QUELLEN} gefunden -- Wache prueft nichts"

    treffer = sqlite_zugriffe_in_der_schale()
    assert not treffer, (
        "Direkter SQLite-Zugriff unter app/Sources: "
        + "; ".join(z for zeilen in treffer.values() for z in zeilen)
        + " -- der Weg zum Bestand fuehrt ausschliesslich ueber den Dienst "
        "(docs/PLAN_APP_SCHICHTEN_2026-08-12.md)."
    )
