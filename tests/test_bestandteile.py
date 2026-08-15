"""Tests fuer kern/bestandteile.py (I1). Rot vor gruen: die Datei war heute
noch nicht da -- vor diesem Auftrag gab es KEINEN Mechanismus, der eine
Anforderung von einem Katalogeintrag unterschied; jede Domaene bekam alles
(SeitenleistenEintrag.allCases ungefiltert, siehe app/Sources/Atelier/
HauptFenster.swift vor dieser Aenderung). Diese Tests pruefen die neue
Entscheidungsfunktion, nicht die alte Abwesenheit."""

from __future__ import annotations

import re
from pathlib import Path

from kern.bestandteile import KATALOG, gewaehrt

SWIFT_KATALOG = (
    Path(__file__).resolve().parent.parent
    / "app/Sources/BrainlehrCore/BestandteilRegistry.swift"
)


def test_bekannter_bestandteil_mit_erfuellter_auflage_wird_gewaehrt():
    assert gewaehrt(["dokumentfenster"]) == ["dokumentfenster"]


def test_unbekannter_bestandteil_wird_verworfen_ohne_fehler():
    # Grenzwert: kein KeyError, keine Ausnahme -- stille Ablehnung.
    assert gewaehrt(["nichtdererfundene"]) == []


def test_zweimal_derselbe_angefordert_wird_dedupliziert():
    # Grenzwert: doppelte Anforderung fuehrt nicht zu doppeltem Laden.
    assert gewaehrt(["dokumentfenster", "dokumentfenster"]) == ["dokumentfenster"]


def test_bestandteil_mit_unerfuellter_auflage_wird_verweigert():
    # Grenzwert: bekannt, aber ADR-016 Auflage 3 offen -> nicht gewaehrt.
    assert KATALOG["tabellenkalkulation"].auflagen_erfuellt is False
    assert gewaehrt(["tabellenkalkulation"]) == []


def test_domaene_ohne_angabe_bekommt_nichts():
    # Grenzwert: leere Anforderung -> leere Gewaehrung, kein Vorgabewert.
    assert gewaehrt([]) == []


def test_gemischte_anforderung_nur_der_gueltige_teil_laedt():
    ergebnis = gewaehrt(["dokumentfenster", "tabellenkalkulation", "unbekannt"])
    assert ergebnis == ["dokumentfenster"]


def test_namen_stimmen_mit_swift_ueberein():
    """Verhindert, dass Python- und Swift-Katalog auseinanderlaufen (siehe
    Moduldoc kern/bestandteile.py). Liest die 'case'-Zeilen des Swift-Enums
    und vergleicht die Namensmenge mit KATALOG."""
    text = SWIFT_KATALOG.read_text(encoding="utf-8")
    enum_block = re.search(r"enum Bestandteil:.*?\{(.*?)\}", text, re.S)
    assert enum_block, "Bestandteil-Enum in der Swift-Datei nicht gefunden."
    swift_namen = set(re.findall(r"case\s+(\w+)", enum_block.group(1)))
    assert swift_namen == set(KATALOG.keys())
