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


def test_tabellenkalkulation_alle_adr016_ladebedingungen_erfuellt():
    # PLAN_I3_TABELLE_2026-08-15.md, Schritt 1+2: Auflage 3 gemessen+
    # aufgehoben (2026-08-15T14:10:23+0200), Auflage 1/2 (Positivliste) im
    # Spike gebaut und ueber tests/test_univer_positivliste.py belegt --
    # also jetzt gewaehrt, nicht mehr verweigert wie vor diesem Auftrag.
    assert KATALOG["tabellenkalkulation"].auflagen_erfuellt is True
    assert gewaehrt(["tabellenkalkulation"]) == ["tabellenkalkulation"]


def test_domaene_ohne_angabe_bekommt_nichts():
    # Grenzwert: leere Anforderung -> leere Gewaehrung, kein Vorgabewert.
    # Gegenprobe zur Anforderung oben: eine Domaene OHNE Anforderung bekommt
    # die Tabelle nicht, obwohl deren Auflagen erfuellt sind -- Anfordern
    # bleibt Pflicht, kein Vorgabewert schaltet still mit frei.
    assert gewaehrt([]) == []
    assert "tabellenkalkulation" not in gewaehrt(["dokumentfenster"])


def test_gemischte_anforderung_beide_bekannten_teile_laden():
    ergebnis = gewaehrt(["dokumentfenster", "tabellenkalkulation", "unbekannt"])
    assert ergebnis == ["dokumentfenster", "tabellenkalkulation"]


def test_namen_stimmen_mit_swift_ueberein():
    """Verhindert, dass Python- und Swift-Katalog auseinanderlaufen (siehe
    Moduldoc kern/bestandteile.py). Liest die 'case'-Zeilen des Swift-Enums
    und vergleicht die Namensmenge mit KATALOG."""
    text = SWIFT_KATALOG.read_text(encoding="utf-8")
    enum_block = re.search(r"enum Bestandteil:.*?\{(.*?)\}", text, re.S)
    assert enum_block, "Bestandteil-Enum in der Swift-Datei nicht gefunden."
    swift_namen = set(re.findall(r"case\s+(\w+)", enum_block.group(1)))
    assert swift_namen == set(KATALOG.keys())
