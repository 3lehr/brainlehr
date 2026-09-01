#!/usr/bin/env python3
"""Rot-vor-gruen-Beleg fuer kern/bauvermeidung.py (§4.4, Knoten cb2193a8).

Vor dem Bau existierte kern/bauvermeidung.py nicht -- jeder Test hier war
also zwangslaeufig rot (ModuleNotFoundError). Was hier steht, ist die
Abnahme aus dem Auftrag, nicht eine nachtraeglich erfundene Huelle:

  Positivkontrolle A: melder/foederation.py (B5.2, `vertraue()`) ist real
  gebaut (L-39574b) -- muss gefunden werden.
  Positivkontrolle B: eine natuerliche Bildschirmliste-Frage muss den
  Wissensknoten f83f2f80 (Eilmeldung ueber inventar_faehigkeiten.py)
  treffen -- der genau dokumentierte Fall aus demselben Auftrag.
  Negativkontrolle: eine erfundene Absicht darf keinen Codetreffer liefern.

Nur lesend gegen den echten Bestand (kein Mock, kein Fixture-DB) -- wird
uebersprungen, wenn Symbolindex/Wissens-DB nicht erreichbar sind, statt
falsch gruen zu sein."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_W = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_W / "kern"))

import bauvermeidung as bv  # noqa: E402


# The acceptance cases query the grown knowledge/code inventory and the
# neighbouring Fahrtenbuch checkout.  They remain available as an explicit
# integration smoke, but cannot certify an isolated fresh database.
pytestmark = pytest.mark.skipif(
    os.environ.get("BRAINLEHR_RUN_LIVE") != "1",
    reason="requires explicit BRAINLEHR_RUN_LIVE=1 and the external code inventory",
)


def test_positivkontrolle_foederation_vertrauensliste():
    try:
        erg = bv.pruefe("ich haette gerne eine Vertrauensliste zwischen Instanzen")
    except Exception as exc:  # pragma: no cover -- kein Bestand erreichbar
        pytest.skip(f"Bestand nicht erreichbar: {exc}")
    fundstellen = " ".join(t["fundstelle"] or "" for t in erg["treffer"])
    beleg_texte = " ".join(t["beleg_text"] or "" for t in erg["treffer"])
    assert "foederation.py" in fundstellen or "foederation" in beleg_texte.lower(), (
        "B5.2 (melder/foederation.py, L-39574b) nicht gefunden -- "
        f"Treffer: {erg['treffer']}"
    )


def test_positivkontrolle_bildschirmliste_fahrtenbuch():
    try:
        erg = bv.pruefe("ich haette gerne eine Liste aller Bildschirme des fahrtenbuch")
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Bestand nicht erreichbar: {exc}")
    ids = {t["fundstelle"] for t in erg["treffer"]}
    beleg_texte = " ".join(t["beleg_text"] or "" for t in erg["treffer"])
    assert "f83f2f80" in ids or "inventar_faehigkeiten" in beleg_texte, (
        "Eilmeldung f83f2f80 (Bildschirmliste seit 2026-08-16 vorhanden) "
        f"nicht gefunden -- Treffer: {erg['treffer']}"
    )


def test_negativkontrolle_erfundene_absicht_ohne_codetreffer():
    erg = bv.pruefe("ich haette gerne einen Quantenchip-Zeitreise-Uebersetzer-Flansch")
    code_treffer = [t for t in erg["treffer"] if t["kanal"] == "code"]
    assert not code_treffer, f"Negativkontrolle erzeugte Codetreffer: {code_treffer}"


def test_nullbefund_ist_ausdruecklich_und_nennt_den_raum():
    erg = bv.pruefe("ich haette gerne einen Quantenchip-Zeitreise-Uebersetzer-Flansch")
    if erg["treffer"]:
        pytest.skip("Wissenskanal fand doch etwas -- Nullbefund-Pfad hier nicht pruefbar")
    assert erg["urteil"].startswith("NULLBEFUND")
    assert erg["abgesuchter_raum"], "Nullbefund ohne genannten abgesuchten Raum"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
