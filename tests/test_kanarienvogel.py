"""Der Selbsttest von kern/kanarienvogel.py (Aufgabe 63) laeuft im Testlauf
mit -- sonst ist er ein Skript, das niemand aufruft, und verrottet wie jedes
andere. Der Selbsttest selbst traegt die Rot-Probe (kaputter DB-Pfad,
fehlschlagende Einbettungsfunktion); hier zusaetzlich einzelne Assertions
gegen die echte brainlehr.db, damit ein `pytest -k kanarienvogel` auch ohne
den kompletten Selbsttest-Lauf etwas zeigt."""

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "kern"))

import kanarienvogel  # noqa: E402


def test_selftest():
    kanarienvogel._selftest()


def test_pruefen_gegen_echte_db():
    """Gleicher Weg wie query() (haken/knowledge_recall_hook.py): RO-
    Verbindung zur echten brainlehr.db muss antworten. Einbettung wird hier
    injiziert (kein Ollama-Netzwerkaufruf im Testlauf)."""
    befund = kanarienvogel.pruefen(embed_fn=lambda _t: [1.0])
    assert befund["db_ok"] is True
    assert befund["embedding_ok"] is True
    assert befund["fehler"] == []
    assert set(befund) == {"ts", "db_ok", "embedding_ok", "fehler"}


def test_rot_probe_kaputter_db_pfad(tmp_path):
    """ROT-PROBE (Auftrag, unverzichtbar): eine Wegwerfkopie ohne Datei am
    angegebenen Pfad meldet ALARM, statt zu schweigen -- die echte
    brainlehr.db bleibt dabei unberuehrt (nur der Pfad wird ausgetauscht,
    kein Schreibzugriff)."""
    kaputt = tmp_path / "nicht-vorhanden.db"
    befund = kanarienvogel.pruefen(db_path=kaputt, embed_fn=lambda _t: [1.0])
    assert befund["db_ok"] is False
    assert befund["embedding_ok"] is True
    assert "datenbank" in befund["fehler"][0]


def test_rot_probe_einbettung_liefert_nichts():
    befund = kanarienvogel.pruefen(embed_fn=lambda _t: None)
    assert befund["embedding_ok"] is False
    assert befund["db_ok"] is True


def test_alarm_nur_bei_ausfall(tmp_path):
    """KEINE Meldung bei Erfolg (Auftrag Punkt 3: eine 'alles gut'-Zeile bei
    jedem Aufruf wird ueberlesen), ALARM als Protokollzeile bei Ausfall."""
    alarm = tmp_path / "alarm.jsonl"

    kanarienvogel.pruefen_und_melden(embed_fn=lambda _t: [1.0], alarm_log=alarm)
    assert not alarm.exists()

    kaputt = tmp_path / "weg.db"
    kanarienvogel.pruefen_und_melden(db_path=kaputt, embed_fn=lambda _t: [1.0], alarm_log=alarm)
    assert alarm.exists()
    zeilen = alarm.read_text(encoding="utf-8").splitlines()
    assert len(zeilen) == 1
    zeile = json.loads(zeilen[0])
    assert zeile["db_ok"] is False
