"""speicherherkunft haengt an antwort_abruf.py --stop (Auftrag 94,
docs/PLAN_GESAMT_2026-08-13.md, Schritt 0, "Linie 0").

ANLASS, woertlich aus dem Auftrag: ein Befund samt Zahlen (0,531 gegen
0,527, daraus die Modellwahl bge-m3) wurde als eigene Aussage weitergegeben,
obwohl er vollstaendig aus einem eingespielten Knoten stammte. Diese Datei
prueft die VERDRAHTUNG (antwort_abruf.py ruft melder/speicherherkunft.py
auf, kopiert es nicht) -- die Merkmalslogik selbst hat ihren eigenen
Selbsttest in melder/speicherherkunft.py.
"""
from __future__ import annotations

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

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL / "haken"))
sys.path.insert(0, str(WURZEL / "melder"))

import antwort_abruf as aa  # type: ignore  # noqa: E402
import speicherherkunft as sh  # type: ignore  # noqa: E402


def _transcript(tmp_path: Path, text: str) -> Path:
    t = tmp_path / "transcript.jsonl"
    t.write_text(json.dumps({
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": text}]},
    }) + "\n", encoding="utf-8")
    return t


def _fuelltext(kern: str) -> str:
    """Auf MIN_LEN (400 Zeichen) auffuellen -- modus_stop() kehrt darunter
    frueh zurueck, bevor irgendein Melder ueberhaupt laeuft."""
    antwort = kern + " Fuelltext, damit die Mindestlaenge steht. " * 15
    assert len(antwort) >= aa.MIN_LEN
    return antwort


def _log_zeile_schreiben(pfad: Path, **feld) -> None:
    with open(pfad, "a", encoding="utf-8") as f:
        f.write(json.dumps(feld, ensure_ascii=False) + "\n")


def _still_stellen(monkeypatch) -> None:
    """Die anderen drei Stop-Melder abschalten -- dieser Test prueft nur
    speicherherkunft, nicht das ganze Bouquet an modus_stop()."""
    monkeypatch.setattr(aa, "top_begriffe", lambda antwort, n=aa.MAX_BEGRIFFE: [])
    monkeypatch.setattr(aa, "_normbezug_melden", lambda antwort: None)
    monkeypatch.setattr(aa, "_existenzpruefung_melden", lambda antwort: None)


def test_stop_meldet_unattributierte_speicherzahl(tmp_path, monkeypatch, capsys):
    """Rot vor der Aenderung: der Anlassfall (Zahl aus dem Block, keine
    Nennung) erzeugte vorher KEINE Meldung an diesem Haltepunkt -- diese
    Verdrahtung gab es nicht. Nachher schlaegt sie an."""
    _still_stellen(monkeypatch)
    log = tmp_path / "recall_log.jsonl"
    monkeypatch.setattr(sh.ort, "RECALL_LOG", log)
    _log_zeile_schreiben(log, session="testsess", zahlen=["0,531", "0,527"],
                          node_ids=[], lessons=[])

    antwort = _fuelltext("Deshalb bge-m3: 0,531 gegen 0,527 in der Messung.")
    payload = {"transcript_path": str(_transcript(tmp_path, antwort)), "session_id": "testsess"}
    aa.modus_stop(payload)

    ausgabe = capsys.readouterr().out
    assert "UNGEKENNZEICHNET (speicherherkunft)" in ausgabe
    assert "0,531" in ausgabe


def test_stop_schweigt_bei_nennung(tmp_path, monkeypatch, capsys):
    """Negativfall, der wichtigere laut Auftrag: dieselbe Zahl, aber die
    Antwort nennt den Speicher ('brainlehr sagt') -- keine Meldung."""
    _still_stellen(monkeypatch)
    log = tmp_path / "recall_log.jsonl"
    monkeypatch.setattr(sh.ort, "RECALL_LOG", log)
    _log_zeile_schreiben(log, session="testsess", zahlen=["0,531", "0,527"],
                          node_ids=[], lessons=[])

    antwort = _fuelltext("Dazu brainlehr sagt: 0,531 gegen 0,527 in der Messung.")
    payload = {"transcript_path": str(_transcript(tmp_path, antwort)), "session_id": "testsess"}
    aa.modus_stop(payload)

    assert "UNGEKENNZEICHNET (speicherherkunft)" not in capsys.readouterr().out


def test_stop_schweigt_ohne_bezug_zum_block(tmp_path, monkeypatch, capsys):
    """Negativfall: eine Antwort ohne jeden Bezug zum eingespielten Block
    darf nicht anschlagen."""
    _still_stellen(monkeypatch)
    log = tmp_path / "recall_log.jsonl"
    monkeypatch.setattr(sh.ort, "RECALL_LOG", log)
    _log_zeile_schreiben(log, session="testsess", zahlen=["0,531", "0,527"],
                          node_ids=[], lessons=[])

    antwort = _fuelltext("Der Testlauf ist gruen, alles wie erwartet, ohne jede Zahl.")
    payload = {"transcript_path": str(_transcript(tmp_path, antwort)), "session_id": "testsess"}
    aa.modus_stop(payload)

    assert "UNGEKENNZEICHNET (speicherherkunft)" not in capsys.readouterr().out


def test_haeufiges_wort_loest_nicht_aus(tmp_path, monkeypatch, capsys):
    """Grenzwert: 'Speicher' kommt in Block-Kontext und Antwort zufaellig
    vor, ist aber kein Merkmal -- darf allein nicht ausloesen."""
    _still_stellen(monkeypatch)
    log = tmp_path / "recall_log.jsonl"
    monkeypatch.setattr(sh.ort, "RECALL_LOG", log)
    _log_zeile_schreiben(log, session="testsess", zahlen=["0,531"], node_ids=[], lessons=[])

    antwort = _fuelltext("Der Speicher kennt dieses Thema schon lange, ohne Zahl hier.")
    payload = {"transcript_path": str(_transcript(tmp_path, antwort)), "session_id": "testsess"}
    aa.modus_stop(payload)

    assert "UNGEKENNZEICHNET (speicherherkunft)" not in capsys.readouterr().out


def test_speicherherkunftsfehler_reisst_den_stop_hook_nicht_mit(tmp_path, monkeypatch, capsys):
    """Fehlerfall: wirft speicherherkunft.melde(), muss antwort_abruf.py
    trotzdem sein eigenes Ergebnis liefern und darf nicht crashen."""
    _still_stellen(monkeypatch)

    def wirft(*_a, **_kw):
        raise RuntimeError("kaputt, absichtlich")
    monkeypatch.setattr(sh, "melde", wirft)

    antwort = _fuelltext("Ganz gewoehnliche Antwort, ohne jeden Bezug.")
    payload = {"transcript_path": str(_transcript(tmp_path, antwort)), "session_id": "testsess"}
    aa.modus_stop(payload)  # darf nicht werfen

    assert "UNGEKENNZEICHNET (speicherherkunft)" not in capsys.readouterr().out
