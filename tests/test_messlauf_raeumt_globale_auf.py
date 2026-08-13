"""Rot vor gruen (2026-08-14): pruefstand/messlauf.py::run() bog drei
Modulglobale um und stellte sie nie zurueck --

    embeddings.embed_text   (auf synthetische Vektoren bzw. auf None)
    kms.DB_PATH             (auf die Wegwerf-DB im tempdir)
    hook.DB                 (dieselbe)

Als Skript aufgerufen war das folgenlos: der Prozess endet danach. Im selben
Prozess ist es Fernwirkung. tests/test_paretolauf.py importiert `paretolauf`,
das `messlauf` importiert, und laesst dessen Lauf laufen -- ab da sah JEDER
spaeter laufende Test ein embed_text, das None liefert, und einen DB-Pfad in
einem laengst geloeschten tempdir.

Sichtbar wurde es als zwei Proben in tests/test_vektor_identitaet.py, die
allein gruen sind und in der vollen Suite rot ("assert None == [0.1, 0.2]").
Die Fehlermeldung zeigte also auf das Opfer, nie auf die Quelle -- deshalb
prueft dieser Test die QUELLE, nicht das Symptom.

Rot-Probe gefahren: gegen den Stand vor dem Fix schlagen alle drei
Zusicherungen unten fehl (embed_text bleibt die messlauf-Lambda, DB_PATH und
hook.DB zeigen in das geloeschte tempdir).
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w), str(_w / "pruefstand")] + [
    str(_w / o) for o in ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import embeddings  # noqa: E402
import knowledge_mcp_server as kms  # noqa: E402
import knowledge_recall_hook as hook  # noqa: E402
import messlauf  # noqa: E402


def test_run_stellt_umgebogene_globale_zurueck():
    vorher = (embeddings.embed_text, kms.DB_PATH, hook.DB)

    messlauf.run(timestamp="2026-08-05T00:00:00+0200")

    assert embeddings.embed_text is vorher[0], (
        "messlauf.run() hat embeddings.embed_text nicht zurueckgestellt -- "
        "jeder danach laufende Test bekommt synthetische Vektoren oder None"
    )
    assert kms.DB_PATH == vorher[1], "kms.DB_PATH zeigt noch in die Wegwerf-DB"
    assert hook.DB == vorher[2], "hook.DB zeigt noch in die Wegwerf-DB"


def test_run_stellt_auch_nach_einem_fehler_zurueck(monkeypatch):
    """Gegenprobe: waere die Sicherung nur am Erfolgspfad (statt in finally),
    bliebe der Zustand bei jedem Abbruch mitten im Lauf verschmutzt -- und ein
    Abbruch ist genau der Fall, in dem niemand hinsieht."""
    vorher = embeddings.embed_text

    def _platzt(*a, **kw):
        raise RuntimeError("absichtlicher Abbruch mitten im Lauf")

    monkeypatch.setattr(messlauf, "_run_ungesichert", _platzt)
    try:
        messlauf.run(timestamp="2026-08-05T00:00:00+0200")
    except RuntimeError:
        pass
    else:
        raise AssertionError("der gefaelschte Abbruch kam nicht durch")

    assert embeddings.embed_text is vorher
