"""Deckt pruefkorpus.py netzlos ab: IDF/Zirkularitaetspruefung ist der Kern
des Auftrags (Plan hub/docs/PLAN_ABRUFGUETE_2026-08-07.md Schritt 1) und muss
ohne Ollama/DB pruefbar sein. Kein Mock fuer die Pruefung selbst -- sie ist
reine Mengenlehre ueber tokenize()/build_idf().
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import random
import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))
sys.path.insert(0, str(SHARED_KNOWLEDGE / "kern"))

import pruefkorpus as pk  # noqa: E402


def _mini_bestand():
    nodes = [
        {"id": "n1", "path": "/a/x", "title": "Existenzgruender Broschuere",
         "summary": "Amtliche Beschreibung fuer Existenzgruender in Niedersachsen.",
         "content": "", "norm_rang": None, "gilt_ab": None},
        {"id": "n2", "path": "/a/y", "title": "Direktive ueber Ausfallzeiten",
         "summary": "Ausfallzeiten kosten in der Testphase nichts, gilt systemweit.",
         "content": "", "norm_rang": 1, "gilt_ab": "2026-01-01"},
    ]
    lessons = [
        {"id": "L-1", "type": "antipattern", "severity": "high",
         "description": "AlertDialog showDialog erzeugt Vollbild-Weissraum in ActionScreen.",
         "root_cause": "Globaler Shim faengt showDialog ab.",
         "prevention": "ActionScreen(expandPrimaryAction:true) verwenden."},
        {"id": "L-2", "type": "error", "severity": "low",
         "description": "Ein einmaliger Fehler ohne Wiederholung.",
         "root_cause": "Netzwerk-Flake.", "prevention": "Retry."},
    ]
    return nodes, lessons


def test_tokenize_faltet_und_filtert_stopwoerter():
    kws = pk.tokenize("Die Existenzgründer-Broschüre und das Fahrtenbuch")
    assert "existenzgruender" in kws or "existenzgruenderbroschuere" in kws  # gefaltet
    assert "und" not in kws  # Stopwort
    assert "das" not in kws  # Stopwort


def test_build_idf_zaehlt_dokumentfrequenz_korrekt():
    nodes, lessons = _mini_bestand()
    idf, n_docs, df = pk.build_idf(nodes, lessons)
    assert n_docs == 4  # 2 Nodes + 2 Lessons
    assert df["actionscreen"] == 1  # nur in L-1
    assert idf["actionscreen"] > 0


def test_zirkularitaet_schlaegt_an_bei_woertlicher_titel_uebernahme():
    """ABNAHME: Aufgabe, die den Zieltitel woertlich enthaelt, MUSS verworfen werden."""
    nodes, lessons = _mini_bestand()
    idf, n_docs, df = pk.build_idf(nodes, lessons)
    target_text = pk.lesson_text(lessons[0])
    zirkulaer = "Wie loese ich das Problem mit ActionScreen und showDialog?"
    collision = pk.is_circular(zirkulaer, target_text, idf, df)
    assert collision, "woertliche Uebernahme haette Kollision zeigen muessen"
    assert {"actionscreen", "showdialog"} <= collision


def test_zirkularitaet_lehnt_frei_formulierte_aufgabe_nicht_ab():
    """Gegenprobe: andere Wortwahl fuer dieselbe Sache darf nicht durchfallen."""
    nodes, lessons = _mini_bestand()
    idf, n_docs, df = pk.build_idf(nodes, lessons)
    target_text = pk.lesson_text(lessons[0])
    frei = ("Im Fahrtenbuch soll ein Bestaetigungsschirm ohne weissen Rand "
            "erscheinen, bevor eine Fahrt beendet wird.")
    assert not pk.is_circular(frei, target_text, idf, df)


def test_haeufiges_wort_gilt_nicht_als_selten():
    """Grenzwert RARE_MAX_DF: ein Wort mit df > RARE_MAX_DF darf keine
    Kollision ausloesen, auch wenn es woertlich geteilt wird."""
    haeufige_nodes = [
        {"id": f"n{i}", "path": f"/x{i}", "title": "Uebersicht", "summary": "Uebersicht ueber alles",
         "content": "", "norm_rang": None, "gilt_ab": None}
        for i in range(pk.RARE_MAX_DF + 3)
    ]
    idf, n_docs, df = pk.build_idf(haeufige_nodes, [])
    assert df["uebersicht"] > pk.RARE_MAX_DF
    assert pk.rare_terms("Uebersicht ist da", idf, df) == set()


def test_grenzwert_rare_max_df_exakt():
    """Grenzwertpruefung: df == RARE_MAX_DF gilt noch als selten, df == RARE_MAX_DF+1 nicht mehr."""
    genau_grenze = [
        {"id": f"n{i}", "path": f"/g{i}", "title": "Grenzwort", "summary": "x",
         "content": "", "norm_rang": None, "gilt_ab": None}
        for i in range(pk.RARE_MAX_DF)
    ]
    idf, _, df = pk.build_idf(genau_grenze, [])
    assert df["grenzwort"] == pk.RARE_MAX_DF
    assert pk.rare_terms("Grenzwort", idf, df) == {"grenzwort"}

    ueber_grenze = genau_grenze + [
        {"id": "extra", "path": "/extra", "title": "Grenzwort", "summary": "x",
         "content": "", "norm_rang": None, "gilt_ab": None}
    ]
    idf2, _, df2 = pk.build_idf(ueber_grenze, [])
    assert df2["grenzwort"] == pk.RARE_MAX_DF + 1
    assert pk.rare_terms("Grenzwort", idf2, df2) == set()


def test_pick_candidates_respektiert_kategorie_filter():
    nodes, lessons = _mini_bestand()
    picks = pk.pick_candidates(nodes, lessons, random.Random(1))
    assert all(l["type"] in ("pattern", "antipattern") for l in picks["lesson"])
    assert picks["lesson"][0]["id"] == "L-1"  # L-2 ist type=error, faellt raus
    assert all(n["norm_rang"] is None for n in picks["fact"])
    assert all(n["norm_rang"] is not None and n["gilt_ab"] for n in picks["norm"])


def test_pick_candidates_leerer_pool_liefert_leere_liste():
    """Negativfall: keine passenden Lessons -> keine Ausnahme, leere Liste."""
    nodes, _ = _mini_bestand()
    picks = pk.pick_candidates(nodes, [], random.Random(1))
    assert picks["lesson"] == []


def test_generate_task_gibt_nach_max_attempts_auf(monkeypatch):
    """Liefert das lokale Modell immer eine zirkulaere Antwort, wird der
    Eintrag nach MAX_ATTEMPTS Versuchen uebersprungen, nicht endlos wiederholt."""
    nodes, lessons = _mini_bestand()
    idf, _, df = pk.build_idf(nodes, lessons)
    target_text = pk.lesson_text(lessons[0])

    calls = {"n": 0}

    def immer_zirkulaer(prompt, model=pk.MODEL, timeout=pk.TIMEOUT):
        calls["n"] += 1
        return "ActionScreen und showDialog sind das Problem.", None, 0

    monkeypatch.setattr(pk, "_generate", immer_zirkulaer)
    result = pk.generate_task(target_text, idf, df, random.Random(1))
    assert result["accepted"] is False
    assert calls["n"] == pk.MAX_ATTEMPTS
    assert len(result["attempts"]) == pk.MAX_ATTEMPTS


def test_generate_task_akzeptiert_sobald_zirkularitaet_verschwindet(monkeypatch):
    """Erster Versuch kollidiert, zweiter (mit Vermeidungshinweis im Prompt) nicht."""
    nodes, lessons = _mini_bestand()
    idf, _, df = pk.build_idf(nodes, lessons)
    target_text = pk.lesson_text(lessons[0])

    responses = iter([
        ("ActionScreen und showDialog sind das Problem.", None, 0),
        ("Ein Bestaetigungsschirm ohne weissen Rand soll erscheinen.", None, 0),
    ])

    def gestaffelt(prompt, model=pk.MODEL, timeout=pk.TIMEOUT):
        return next(responses)

    monkeypatch.setattr(pk, "_generate", gestaffelt)
    result = pk.generate_task(target_text, idf, df, random.Random(1))
    assert result["accepted"] is True
    assert "Bestaetigungsschirm" in result["task"]
    assert len(result["attempts"]) == 2
    assert result["attempts"][0]["collision"]  # erster Versuch kollidierte
    assert result["attempts"][1]["collision"] == []


def test_generate_task_ollama_fehler_zaehlt_als_versuch_kein_absturz(monkeypatch):
    """Netzfehler/Timeout darf generate_task nicht mit einer Exception verlassen."""
    nodes, lessons = _mini_bestand()
    idf, _, df = pk.build_idf(nodes, lessons)
    target_text = pk.lesson_text(lessons[0])

    def fehler(prompt, model=pk.MODEL, timeout=pk.TIMEOUT):
        return None, "Ollama-Aufruf fehlgeschlagen: Timeout", 1

    monkeypatch.setattr(pk, "_generate", fehler)
    result = pk.generate_task(target_text, idf, df, random.Random(1))
    assert result["accepted"] is False
    assert len(result["attempts"]) == pk.MAX_ATTEMPTS
    assert all(a["error"] for a in result["attempts"])


def test_append_jsonl_schreibt_sofort(tmp_path):
    path = tmp_path / "pruefkorpus.jsonl"
    pk._append_jsonl({"a": 1}, path=path)
    pk._append_jsonl({"a": 2}, path=path)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
