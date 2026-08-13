"""Existenzpruefung haengt jetzt an antwort_abruf.py --stop, nicht mehr am
Eintrag in .claude/settings.json (Auftrag 2026-08-13).

FAKT, gemessen: haken/existenzpruefung.py kommt in 0 von 949 Stop-Ausloesungen
vor -- der projekteigene .claude/settings.json-Eintrag lief nie. Nur
antwort_abruf.py --stop ist belegt gelaufen (719x). Diese Datei prueft, dass
die Pruefung jetzt DORT haengt -- sie ruft die vorhandene Logik aus
existenzpruefung.py auf, kopiert sie nicht.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import json
import sqlite3
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL / "haken"))

import antwort_abruf as aa  # type: ignore  # noqa: E402
import existenzpruefung as ep  # type: ignore  # noqa: E402


def _transcript(tmp_path: Path, text: str) -> Path:
    t = tmp_path / "transcript.jsonl"
    t.write_text(json.dumps({
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": text}]},
    }) + "\n", encoding="utf-8")
    return t


def _fuelltext(kern: str) -> str:
    """Auf MIN_LEN (400 Zeichen) auffuellen -- modus_stop() kehrt darunter
    frueh zurueck, bevor die Existenzpruefung ueberhaupt laeuft."""
    antwort = kern + " Fuelltext, damit die Mindestlaenge steht. " * 15
    assert len(antwort) >= aa.MIN_LEN
    return antwort


def test_stop_meldet_existenzverneinung_mit_bestandstreffer(tmp_path, monkeypatch, capsys):
    """Rot vor der Aenderung: der Stop-Eintrag in .claude/settings.json lief
    nie (0 von 949), also kam vorher aus antwort_abruf.py --stop nie eine
    Existenzpruefungs-Meldung -- unabhaengig vom Inhalt der Antwort."""
    db = tmp_path / "k.db"
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE knowledge_nodes (path TEXT, title TEXT, summary TEXT)")
    c.execute("INSERT INTO knowledge_nodes VALUES "
              "('/mess/korpus','Pruefkorpus V3 fuer den Abrufvergleich','...')")
    c.commit()
    c.close()
    orig = ep.bestand_fragen
    monkeypatch.setattr(ep, "bestand_fragen",
                         lambda _db, anfrage, grenze=3: orig(db, anfrage, grenze))
    # Der eigentliche Abruf (top_begriffe/knowledge_search) ist nicht
    # Gegenstand dieses Tests -- leer zurueckgeben, damit modus_stop nach der
    # Existenzpruefung sauber frueh zurueckkehrt.
    monkeypatch.setattr(aa, "top_begriffe", lambda antwort, n=aa.MAX_BEGRIFFE: [])

    antwort = _fuelltext("Fuer den Pruefkorpus Abrufvergleich haben wir noch keine Messdaten.")
    payload = {"transcript_path": str(_transcript(tmp_path, antwort)), "session_id": "testsess"}
    aa.modus_stop(payload)

    ausgabe = capsys.readouterr().out
    assert "NACHGEFRAGT (existenzpruefung)" in ausgabe
    assert "Pruefkorpus" in ausgabe


def test_stop_schweigt_ohne_verneinung(tmp_path, monkeypatch, capsys):
    """Negativfall: eine gewoehnliche Antwort ohne Existenzverneinung darf
    keine Meldung der Existenzpruefung erzeugen -- ein Signal, das nur in
    eine Richtung ausschlagen kann, ist keine Messung."""
    monkeypatch.setattr(aa, "top_begriffe", lambda antwort, n=aa.MAX_BEGRIFFE: [])

    antwort = _fuelltext("Der Testlauf ist gruen, alles wie erwartet.")
    payload = {"transcript_path": str(_transcript(tmp_path, antwort)), "session_id": "testsess"}
    aa.modus_stop(payload)

    assert "NACHGEFRAGT (existenzpruefung)" not in capsys.readouterr().out


def test_existenzpruefungsfehler_reisst_den_stop_hook_nicht_mit(tmp_path, monkeypatch, capsys):
    """Fehlerfall: wirft die Existenzpruefung, muss antwort_abruf.py trotzdem
    sein eigenes Ergebnis liefern und darf nicht crashen -- ein Haken, der
    den Faden anhaelt, ist schlimmer als einer, der schweigt."""
    def wirft(*_a, **_kw):
        raise RuntimeError("kaputt, absichtlich")
    monkeypatch.setattr(ep, "verneinungen", wirft)
    monkeypatch.setattr(aa, "top_begriffe", lambda antwort, n=aa.MAX_BEGRIFFE: [])

    antwort = _fuelltext("Ganz gewoehnliche Antwort, ohne jede Verneinung darin.")
    payload = {"transcript_path": str(_transcript(tmp_path, antwort)), "session_id": "testsess"}
    aa.modus_stop(payload)  # darf nicht werfen

    assert "NACHGEFRAGT (existenzpruefung)" not in capsys.readouterr().out
