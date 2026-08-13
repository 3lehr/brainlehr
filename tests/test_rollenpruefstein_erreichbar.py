"""Der Rollen-Pruefstein gegen lokale ANTWORTLAEUFE (L-a69129, dreimal
aufgetreten, zur Regel eskaliert) sitzt in schreiblauf.rolle_pruefen(). Er
nuetzt nur, wo er auch ERREICHT wird -- und genau das war die Luecke.

Gemessen am 2026-08-14: vier Stellen rufen einen Ollama-Endpunkt.
kern/embeddings.py und messungen/abschneidegrenze_bge_m3.py rufen /api/embed
-- Einbettung, kein Antwortlauf, der Pruefstein ist dort gegenstandslos
(Anthropic bietet ohnehin keinen Einbettungsendpunkt, das bleibt lokal).
/api/generate rufen drei: schreibpruefstand/schreiblauf.py (geht durch den
Pruefstein) sowie kern/fenstergroesse.py und
schreibpruefstand/normfeld_versuch.py -- beide haben einen EIGENEN
Aufrufweg, weil schreiblauf._call_ollama() kein options-Feld (num_ctx) kennt
und kein prompt_eval_count liefert, und beide liefen damit an der Sperre
vorbei. In normfeld_versuch.py ist die Ursache genau benennbar: die Kopie
kopierte den Pruefstein nicht mit, weil er im Original eine Ebene hoeher
sitzt (in _call_with_retry, nicht in _call_ollama).

Dieser Test ist die Ratsche dagegen, dass eine vierte Stelle denselben Weg
noch einmal nimmt. Er prueft nicht, ob jemand die Sperre ABSICHTLICH umgeht
-- das kann er nicht -- sondern ob sie ueberhaupt im Weg liegt.

Rot vor gruen, in zwei Stufen: test_fenstergroesse_geht_durch_den_pruefstein
schlug gegen den Stand davor fehl (rolle_pruefen wurde nie gerufen). Und die
Ratsche selbst hat normfeld_versuch.py gefunden -- die Stelle war beim
Schreiben dieses Tests NICHT bekannt, sie stand in keiner Aufgabe und in
keinem Plan.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
WURZEL = _w
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import pytest  # noqa: E402

import fenstergroesse as fg  # noqa: E402
import schreiblauf as sl  # noqa: E402

# Ordner mit Produktivcode. tests/ und docs/ duerfen den Endpunkt nennen.
DURCHSUCHT = ("kern", "messungen", "melder", "haken", "schreibpruefstand",
              "migrationen", "pruefstand")


def _dateien_mit_generate() -> list[_Path]:
    treffer = []
    for ordner in DURCHSUCHT:
        wurzel = WURZEL / ordner
        if not wurzel.exists():
            continue
        for pfad in sorted(wurzel.rglob("*.py")):
            text = pfad.read_text(encoding="utf-8")
            # Nur echte Aufrufe zaehlen, nicht die Erwaehnung im Fliesstext.
            # Gemessener Fehlalarm ohne diese Bedingung:
            # schreibpruefstand/matrix_lauf.py nennt den Endpunkt in seinem
            # Modulkopf ("Ollama-Modelle ueber schreiblauf.py (/api/generate,
            # ...)"), faehrt aber ueber schreiblauf.run() und damit durch den
            # Pruefstein. Merkmal des echten Aufrufs ist die URL-Zusammen-
            # setzung, also ein f-String.
            #
            # ponytail: Textmerkmal statt AST. Deckenwert -- wer die URL aus
            # einer Konstanten zusammensetzt, faellt durch. Auf AST umstellen,
            # sobald ein solcher Fall auftritt.
            for zeile in text.splitlines():
                if "/api/generate" not in zeile:
                    continue
                if zeile.lstrip().startswith("#"):
                    continue
                if 'f"' not in zeile and "f'" not in zeile:
                    continue
                treffer.append(pfad)
                break
    return treffer


def test_jede_generate_stelle_liegt_hinter_dem_pruefstein():
    """Die eigentliche Ratsche. Wird sie rot, hat jemand einen dritten
    /api/generate-Weg gebaut -- dann gehoert dort rolle_pruefen() hin (mit
    ausdruecklicher Rolle), nicht dieser Test angepasst."""
    ohne = [p.relative_to(WURZEL) for p in _dateien_mit_generate()
            if "rolle_pruefen" not in p.read_text(encoding="utf-8")]
    assert not ohne, (
        f"{len(ohne)} Datei(en) rufen /api/generate ohne den Rollen-Pruefstein: "
        + ", ".join(str(p) for p in ohne)
        + " -- L-a69129: ein lokaler ANTWORTLAUF ist auch mit BRAINLEHR_LOKAL "
        "nicht freigebbar. Rolle ausdruecklich benennen und "
        "schreiblauf.rolle_pruefen() vor den Aufruf setzen."
    )


def test_embed_stellen_brauchen_den_pruefstein_nicht():
    """Gegenprobe zur Abgrenzung: ohne sie bestuende der Test darueber auch
    bei einer Ratsche, die schlicht JEDEN Ollama-Aufruf verlangt -- und dann
    waere die Einbettung mitgesperrt, fuer die es gar keinen Ersatz gibt."""
    text = (WURZEL / "kern" / "embeddings.py").read_text(encoding="utf-8")
    assert "/api/embed" in text
    assert "/api/generate" not in text
    assert "rolle_pruefen" not in text


def test_fenstergroesse_geht_durch_den_pruefstein(monkeypatch):
    """Rot vor dem Fix: _call_ollama() rief rolle_pruefen() nie."""
    gerufen = []
    monkeypatch.setattr(sl, "rolle_pruefen",
                        lambda rolle, model, base_url: gerufen.append(rolle))

    class _Antwort:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"response": "x", "prompt_eval_count": 7}'

    monkeypatch.setattr(fg.urllib.request, "urlopen",
                        lambda req, timeout=None: _Antwort())

    fg._call_ollama("Probetext", num_ctx=2048)

    assert gerufen == ["messobjekt"], (
        "kern/fenstergroesse.py muss den Rollen-Pruefstein mit der "
        f"ausdruecklichen Rolle 'messobjekt' durchlaufen, gerufen wurde {gerufen!r}"
    )


def test_beantworten_bleibt_gesperrt():
    """Negativfall, sonst bestuende der Test darueber auch bei einem
    Pruefstein, der gar nichts ablehnt. Die Rolle 'beantworten' ist auch mit
    BRAINLEHR_LOKAL nicht freigebbar -- ein Skript kann keinen Subagenten
    starten, der Lauf gehoert in den Hauptfaden."""
    with pytest.raises(RuntimeError, match="L-a69129"):
        sl.rolle_pruefen("beantworten", "gemma4:12b", "http://127.0.0.1:11434")


def test_messobjekt_bleibt_ohne_freigabe_erlaubt():
    """Gegenrichtung: waere alles gesperrt, koennte der Schreibpruefstand
    seinen eigenen Messgegenstand nicht mehr messen."""
    sl.rolle_pruefen("messobjekt", "gemma4:12b", "http://127.0.0.1:11434")
