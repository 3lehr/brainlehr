"""Tests fuer kern/zitatpruefer.py am echten Fall (Knoten a146403a, L-3d4320).

Quelle ist das Protokoll der Eigentuemerversammlung vom 04.09.2025, TOP 5,
woertlich: "Die jaehrliche Zufuehrung zur Erhaltungsruecklage betraegt
derzeit 15.000 EUR. Dieser Betrag reicht bei weitem nicht aus, um groessere
Modernisierungsmassnahmen am Gebaeude (z.B. Heizungsmodernisierung) in
absehbarer Zeit zu finanzieren. Es wird beschlossen, die jaehrliche
Zufuehrung zur Erhaltungsruecklage ab dem 01.01.2026 von derzeit 15.000 EUR
auf 30.000 EUR zu erhoehen."
"""
from __future__ import annotations

from pathlib import Path

from kern.zitatpruefer import (
    normalisieren,
    pruefe_dokument,
    traeger_abweichungen,
    zitate_aus_markdown,
)

PROTOKOLL_TEXT = (
    "Die jaehrliche Zufuehrung zur Erhaltungsruecklage betraegt derzeit "
    "15.000 EUR. Dieser Betrag reicht bei weitem nicht aus, um groessere "
    "Modernisierungsmassnahmen am Gebaeude (z.B. Heizungsmodernisierung) in "
    "absehbarer Zeit zu finanzieren. Es wird beschlossen, die jaehrliche "
    "Zufuehrung zur Erhaltungsruecklage ab dem 01.01.2026 von derzeit "
    "15.000 EUR auf 30.000 EUR zu erhoehen."
)


def _protokoll(tmp_path: Path) -> Path:
    p = tmp_path / "protokoll_2025-09-04.md"
    p.write_text(PROTOKOLL_TEXT, encoding="utf-8")
    return p


def test_echter_fall_schlaegt_an(tmp_path: Path) -> None:
    """Die verschaerfte Uebernahme kommt im Quelltext nicht byte-gleich vor."""
    _protokoll(tmp_path)
    dokument = tmp_path / "dokument.md"
    dokument.write_text(
        "> Die Ruecklage ist bereits erhoeht: 2025 einstimmig von 15.000 EUR "
        "auf 30.000 EUR, ausdruecklich fuer die Heizungsmodernisierung -- "
        "die Sanierung ist mit Geld hinterlegt, bevor sie beschlossen ist.\n"
        "> -- Quelle: protokoll_2025-09-04.md\n",
        encoding="utf-8",
    )
    befunde = pruefe_dokument(dokument)
    assert len(befunde) == 1
    assert befunde[0].art == "abweichung"
    assert "Ruecklage ist bereits erhoeht" in befunde[0].detail


def test_negativfall_korrektes_zitat_schlaegt_nicht_an(tmp_path: Path) -> None:
    """Ohne diesen Test bestuende der erste Test auch bei einem Pruefer,
    der grundsaetzlich alles beanstandet."""
    _protokoll(tmp_path)
    dokument = tmp_path / "dokument.md"
    dokument.write_text(
        "> die jaehrliche Zufuehrung zur Erhaltungsruecklage ab dem "
        "01.01.2026 von derzeit 15.000 EUR auf 30.000 EUR zu erhoehen\n"
        "> -- Quelle: protokoll_2025-09-04.md\n",
        encoding="utf-8",
    )
    befunde = pruefe_dokument(dokument)
    assert befunde == []


def test_zitat_ohne_fundstelle_wird_gemeldet(tmp_path: Path) -> None:
    _protokoll(tmp_path)
    dokument = tmp_path / "dokument.md"
    dokument.write_text(
        "> Die jaehrliche Zufuehrung betraegt derzeit 15.000 EUR.\n",
        encoding="utf-8",
    )
    befunde = pruefe_dokument(dokument)
    assert len(befunde) == 1
    assert befunde[0].art == "keine_fundstelle"


def test_grenzwert_ein_zeichen_abweichung_schlaegt_an(tmp_path: Path) -> None:
    _protokoll(tmp_path)
    dokument = tmp_path / "dokument.md"
    # "30.000" -> "30.001": ein einziges abweichendes Zeichen im Wortkoerper.
    dokument.write_text(
        "> die jaehrliche Zufuehrung zur Erhaltungsruecklage ab dem "
        "01.01.2026 von derzeit 15.000 EUR auf 30.001 EUR zu erhoehen\n"
        "> -- Quelle: protokoll_2025-09-04.md\n",
        encoding="utf-8",
    )
    befunde = pruefe_dokument(dokument)
    assert len(befunde) == 1
    assert befunde[0].art == "abweichung"


def test_grenzwert_nur_normalisierung_schlaegt_nicht_an(tmp_path: Path) -> None:
    """Zeilenumbruch mitten im Zitat und typografische Anfuehrungszeichen --
    genau die zwei Faelle, die normalisieren() laut Docstring durchlaesst."""
    _protokoll(tmp_path)
    dokument = tmp_path / "dokument.md"
    dokument.write_text(
        "> die jaehrliche Zufuehrung zur Erhaltungsruecklage ab dem\n"
        "> 01.01.2026 von derzeit 15.000 EUR auf   30.000 EUR zu erhoehen\n"
        "> -- Quelle: protokoll_2025-09-04.md\n",
        encoding="utf-8",
    )
    befunde = pruefe_dokument(dokument)
    assert befunde == []


def test_normalisieren_bildet_typografische_anfuehrungszeichen_ab() -> None:
    assert normalisieren("„Zitat“") == '"Zitat"'
    assert normalisieren("‚Zitat‘") == "'Zitat'"
    assert normalisieren("a\n\n  b") == "a b"


def test_zitate_aus_markdown_parst_abschnitt() -> None:
    zitate = zitate_aus_markdown(
        "> Wortlaut\n> -- Quelle: datei.md, Abschnitt: TOP 5\n"
    )
    assert len(zitate) == 1
    assert zitate[0].quelle == "datei.md"
    assert zitate[0].abschnitt == "TOP 5"
    assert zitate[0].text == "Wortlaut"


def test_traeger_abweichungen_zaehlt_fehlende_und_hinzugekommene_woerter() -> None:
    paare = [(
        "die jaehrliche Zufuehrung zur Erhaltungsruecklage betraegt derzeit "
        "15.000 EUR (z.B. Heizungsmodernisierung)",
        "die Ruecklage ist bereits erhoeht ausdruecklich fuer die "
        "Heizungsmodernisierung",
    )]
    ergebnis = traeger_abweichungen(paare)
    assert len(ergebnis) == 1
    eintrag = ergebnis[0]
    assert eintrag["abweichungen"] > 0
    assert "Heizungsmodernisierung)" in eintrag["fehlend"] or \
        "Heizungsmodernisierung" in eintrag["fehlend"]
    assert "erhoeht" in eintrag["hinzugekommen"]


def test_traeger_abweichungen_identischer_wortlaut_ist_leer() -> None:
    ergebnis = traeger_abweichungen([("gleicher Text", "gleicher Text")])
    assert ergebnis[0]["abweichungen"] == 0
    assert ergebnis[0]["fehlend"] == []
    assert ergebnis[0]["hinzugekommen"] == []
