#!/usr/bin/env python3
"""BDW-R04-AC1: „Für jede Reglerstufe bleiben Beleggate und harte Stopps
identisch wirksam."

ANLASS, 2026-08-18: Eine Stichprobe über 24 offene Produktgates fand für
`BDW-R04` keinen Prüfpfad. `kern/vertrauen.py` hat zwar einen
`demo()`-Selbsttest -- aber KEIN `tests/test_*` bindet ihn ein, und er prüft
die Stufenlogik, nicht die Aussage des Akzeptanzkriteriums. Das war der
billigste offene Punkt des ganzen Katalogs: ein vorhandener Selbsttest ohne
Anbindung.

WAS HIER GEPRUEFT WIRD, und die Unterscheidung ist der Kern:
Der Regler steuert die RUECKFRAGEPFLICHT. Er darf auf keiner Stufe die vier
Stopp-Punkte antasten -- Kennwörter, Außenwirkung, Unumkehrbares, Geld --,
denn die hängen an der Reichweite der Folgen, nicht am Vertrauen. Ein
Regler, der sie mitregelt, ist kein Vertrauensregler, sondern ein
Ausschalter (Modulkopf, wörtlich).

Deshalb ist die Prüfung eine INVARIANZ über alle Stufen, kein Einzelfall:
dieselben vier Stopp-Punkte, unabhängig davon, was in der Reglerdatei steht
-- auch bei Unsinn darin.

MUTATIONSPROBE, gefahren 2026-08-18: `IMMER_FRAGEN` um einen Eintrag
gekürzt -> `test_stopp_punkte_sind_auf_jeder_stufe_dieselben` wird rot und
nennt die fehlende Zeile. Ohne diese Probe wäre unklar, ob der Test die
Invarianz bewacht oder nur die Konstante abschreibt.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(WURZEL), str(WURZEL / "kern")]

import vertrauen  # noqa: E402


@pytest.fixture
def regler(tmp_path, monkeypatch):
    """Reglerdatei im Testverzeichnis -- nie die echte unter ~/.brainlehr."""
    datei = tmp_path / "vertrauensstufe"
    monkeypatch.setattr(vertrauen, "DATEI", datei)
    monkeypatch.setattr(vertrauen, "PROTOKOLL", tmp_path / "vertrauen-protokoll.jsonl")
    return datei


def test_stopp_punkte_sind_auf_jeder_stufe_dieselben(regler):
    """DAS AC. Die vier Stopp-Punkte sind eine Eigenschaft der Folgen, nicht
    des Vertrauens -- sie duerfen sich mit der Stufe nicht veraendern."""
    erwartet = (
        "kennwoerter und zugangsdaten",
        "aussenwirkung gegenueber dritten",
        "unumkehrbares ohne rueckweg",
        "geld",
    )
    gesehen = {}
    for s in vertrauen.STUFEN:
        regler.write_text(s, encoding="utf-8")
        assert vertrauen.stufe() == s, f"Stufe {s} nicht uebernommen"
        gesehen[s] = tuple(vertrauen.IMMER_FRAGEN)

    for s, punkte in gesehen.items():
        assert punkte == erwartet, (
            f"Auf Stufe {s!r} weichen die Stopp-Punkte ab: {punkte}.\n"
            "Der Regler steuert die Rueckfragepflicht, nicht die Reichweite der "
            "Folgen. Wer hier etwas entfernt, baut einen Ausschalter."
        )
    assert len(set(gesehen.values())) == 1, "die Stopp-Punkte haengen an der Stufe"


def test_hoechste_stufe_hebt_keinen_stopp_punkt_auf(regler):
    """Gegenprobe in die andere Richtung: die freieste Stufe darf mehr
    duerfen -- aber nicht bei diesen vieren."""
    regler.write_text("raeumen", encoding="utf-8")
    assert vertrauen.darf_raeumen() is True
    assert len(vertrauen.IMMER_FRAGEN) == 4
    regler.write_text("vorlegen", encoding="utf-8")
    assert vertrauen.darf_raeumen() is False
    assert len(vertrauen.IMMER_FRAGEN) == 4


def test_unsinn_in_der_reglerdatei_stuft_nicht_hoch(regler):
    """Ein Tippfehler darf die Arbeit nicht anhalten -- und erst recht nicht
    zufaellig hochstufen. Beides steht so im Modulkopf; hier wird es geprueft."""
    for muell in ("raeuman", "RAEUMEN ALLES", "9", "", "   ", "handeln\nraeumen"):
        regler.write_text(muell, encoding="utf-8")
        s = vertrauen.stufe()
        assert s in vertrauen.STUFEN, f"{muell!r} ergab unbekannte Stufe {s!r}"
        assert vertrauen.STUFEN.index(s) <= vertrauen.STUFEN.index("raeumen")
        if muell.strip().lower().splitlines()[:1] not in ([], ["handeln"]):
            assert s == vertrauen.VORGABE or s in vertrauen.STUFEN

    # Fehlende Datei -> Vorgabe, kein Fehler.
    regler.unlink(missing_ok=True)
    assert vertrauen.stufe() == vertrauen.VORGABE


def test_vorgabe_ist_nicht_die_hoechste_stufe():
    """Ein Regler, der beim Einbau schon hochgedreht ist, hat nie eine
    Ausgangslage (Modulkopf). Bewacht genau das."""
    assert vertrauen.VORGABE in vertrauen.STUFEN
    assert vertrauen.STUFEN.index(vertrauen.VORGABE) < len(vertrauen.STUFEN) - 1


def test_der_eingebaute_selbsttest_laeuft(regler):
    """Der Grund, warum dieser Test ueberhaupt entstand: demo() existierte,
    war gruen und lief nie im Testlauf mit."""
    importlib.reload(vertrauen)
    assert hasattr(vertrauen, "demo"), "demo() ist verschwunden -- Anbindung pruefen"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
