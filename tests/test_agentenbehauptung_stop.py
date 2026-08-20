#!/usr/bin/env python3
"""agentenbehauptung als Stop-Haken auf den EIGENEN letzten Zug.

ANLASS: L-706807 steht bei vier Vorkommen und ist auf Regelrang eskaliert
("Was ein Agent MELDET, ist nie das, was er GETAN hat"). Der Melder dazu
existiert seit dem 2026-08-20 und haengt an nichts -- er prueft 400
Transkriptdateien im Nachhinein. Als Startmelder waere er nutzlos: er
meldete jeden Tag dieselben alten Treffer.

WIRKSAM ist er nur an EINER Stelle -- am Ende des Zuges, in dem die
Behauptung faellt. Genau dort laeuft schon `melder/rueckfrageschleife.py`
als Stop-Haken, und dessen `_letzte_antwort()` liefert bereits, was hier
gebraucht wird: den Text der letzten Antwort UND ob im Zug ein Werkzeug
lief. Kein zweiter Weg, kein Nachbau.

ROT VOR GRUEN: Faellt gegen den Stand davor -- `pruefe_letzten_zug`
existiert dort nicht.
"""
from __future__ import annotations

import json
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "melder")]

import pytest  # noqa: E402

import agentenbehauptung as ab  # noqa: E402


def _transcript(tmp_path, text: str, mit_werkzeug: bool):
    zeilen = [json.dumps({"type": "user", "message": {"role": "user", "content": "los"}})]
    if mit_werkzeug:
        zeilen.append(json.dumps({"type": "assistant", "message": {"role": "assistant",
                      "content": [{"type": "tool_use", "name": "Bash", "input": {}}]}}))
    zeilen.append(json.dumps({"type": "assistant", "message": {"role": "assistant",
                  "content": [{"type": "text", "text": text}]}}))
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(zeilen), encoding="utf-8")
    return p


BEHAUPTUNG = ("Ich habe die Recherche angestossen, drei Straenge parallel: "
              "euer eigener Bestand, die Rechtsfragen und die Maszdaten.")


def test_behauptung_ohne_werkzeug_schlaegt_an(tmp_path):
    t = _transcript(tmp_path, BEHAUPTUNG, mit_werkzeug=False)
    assert ab.pruefe_letzten_zug(t) is not None


def test_dieselbe_behauptung_mit_werkzeug_schweigt(tmp_path):
    """NEGATIVFALL, und der wichtigste: Wer die Handlung wirklich ausgefuehrt
    hat, wird nicht beanstandet. Ohne diese Zeile waere der Haken eine
    Sperre gegen jede Fortschrittsmeldung."""
    t = _transcript(tmp_path, BEHAUPTUNG, mit_werkzeug=True)
    assert ab.pruefe_letzten_zug(t) is None


def test_harmloser_text_schweigt(tmp_path):
    t = _transcript(tmp_path, "Die Zahl liegt bei 15 von 35, gemessen ueber den Pruefkorpus.",
                    mit_werkzeug=False)
    assert ab.pruefe_letzten_zug(t) is None


def test_fehlende_datei_wirft_nicht(tmp_path):
    """Ein Haken darf den Zug nie mit einem eigenen Fehler anhalten."""
    assert ab.pruefe_letzten_zug(tmp_path / "gibtsnicht.jsonl") is None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
