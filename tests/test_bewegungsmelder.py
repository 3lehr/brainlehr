"""Abnahme fuer melder/bewegungsmelder.py. Ruft NIE die echten Untermelder --
`ausfuehrer` wird immer gestellt, ein Test, der sechs Melder startet, misst
deren Laufzeit statt der Vergleichslogik."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "melder"))
import bewegungsmelder as bm  # noqa: E402


def test_gleiche_zahl_keine_meldung():
    alt = {"gatestand": {"ok": True, "werte": {"a.belegt": 28}}}
    neu = {"gatestand": {"ok": True, "werte": {"a.belegt": 28}}}
    assert bm.vergleichen(alt, neu) == []


def test_geaenderte_zahl_meldet_alt_neu_richtung_beide_richtungen():
    alt = {"gatestand": {"ok": True, "werte": {"a.belegt": 28}}}
    hoch = {"gatestand": {"ok": True, "werte": {"a.belegt": 30}}}
    runter = {"gatestand": {"ok": True, "werte": {"a.belegt": 26}}}
    assert bm.vergleichen(alt, hoch) == ["gatestand.a.belegt: 28 -> 30 (gestiegen um 2)"]
    assert bm.vergleichen(alt, runter) == ["gatestand.a.belegt: 28 -> 26 (gefallen um 2)"]


def test_erstlauf_ohne_gespeicherten_stand_meldet_nichts():
    neu = {"gatestand": {"ok": True, "werte": {"a.belegt": 30}}}
    assert bm.vergleichen({}, neu) == []


def test_negativfall_melder_stuerzt_ab_bricht_lauf_nicht_ab():
    def ausfuehrer(argv: list[str]) -> str:
        if "vier_nenner.py" in argv[0]:
            raise subprocess.TimeoutExpired(cmd=argv, timeout=1)
        if "kennungskollision.py" in argv[0]:
            return "kein Zahlwort hier"
        if "rasterblick.py" in argv[0]:
            raise RuntimeError("kaputt")
        return "REQUIREMENTS_X.md: 5/10 belegt, 1 ohne Gate-Lauf"

    ergebnis = bm.sammeln(ausfuehrer)
    assert ergebnis["vier_nenner"]["ok"] is False
    assert ergebnis["kennungskollision"]["ok"] is False
    assert ergebnis["rasterblick"]["ok"] is False
    assert ergebnis["gatestand"]["ok"] is True
    # Ein Melder mit lesbarer Zahl bleibt trotz der drei Ausfaelle daneben brauchbar.
    assert ergebnis["gatestand"]["werte"]["REQUIREMENTS_X.belegt"] == 5


def test_lauf_schreibt_stand_und_liest_ihn_wieder(tmp_path, monkeypatch):
    stand_pfad = tmp_path / "stand.json"
    monkeypatch.setattr(bm, "STAND_PFAD", stand_pfad)

    neu = {"gatestand": {"ok": True, "werte": {"a.belegt": 5}}}
    assert bm._stand_lesen() == {}
    bm._stand_schreiben(neu)
    assert json.loads(stand_pfad.read_text()) == neu
    assert bm._stand_lesen() == neu


def test_parser_gatestand_vektorstand_rasterblick_kennungskollision_viernenner_derivatfrische():
    assert bm._p_gatestand("REQUIREMENTS_BRAINLEHR.md: 28/56 belegt, 5 ohne Gate-Lauf, 23 vertagt") == {
        "REQUIREMENTS_BRAINLEHR.belegt": 28,
        "REQUIREMENTS_BRAINLEHR.gesamt": 56,
        "REQUIREMENTS_BRAINLEHR.offen": 5,
        "REQUIREMENTS_BRAINLEHR.vertagt": 23,
    }
    assert bm._p_kennungskollision(
        "docs/: 0 Kennungskollision(en), 4 spaeteres Wiederaufgreifen (kein Befund)"
    ) == {"kollisionen": 0, "wiederaufgreifen": 4}
    assert bm._p_rasterblick("81 Ergebnisdatei(en) ohne Rastervermerk:\n  x.json") == {"ohne_vermerk": 81}
    assert bm._p_vier_nenner("A: 160/320 ...\nB: 8/160 ...") == {
        "a.trefer": 160, "a.nenner": 320, "b.trefer": 8, "b.nenner": 160,
    }
    assert bm._p_derivatfrische(
        "Bestand: 1492 Dateien · 6 Dokumente mit erklaertem Stand und Quellenlink\n"
        "Ueberholt (Stand aelter als 21 Tage): 0\nBefunde: 1 aelter als ihre Quelle\n"
    ) == {"dateien": 1492, "derivate": 6, "ueberholt": 0, "befunde": 1}
    assert bm._p_vektorstand(
        "Knoten: 10 gesamt, 1 ohne Einbettung, 2 mit veralteter Pruefsumme, 0 beim Einbetten gekappt"
    ) == {"knoten.gesamt": 10, "knoten.fehlt": 1, "knoten.veraltet": 2, "knoten.gekappt": 0}
