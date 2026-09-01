"""Test fuer haken/auftragshypothese_waechter.py -- Aufgabe 97, Teil 2.

Sieht der Code anders aus als hier beschrieben, halte dich an den Code und
melde die Abweichung.

Die Faelle 'negativ_real' und 'pruefstein_real' sind woertliche Ausschnitte
aus echten Agentenauftraegen von heute (2026-08-13, Sitzungsprotokoll unter
~/.claude/projects/-Volumes-daten-<arbeitsbereich>-brainlehr--claude-worktrees-hallo-01e380/).
Reine Facharbeit, keine Zugangsdaten, keine personenbezogenen Daten.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path.insert(0, str(_w / "haken"))

import auftragshypothese_waechter as waechter  # noqa: E402

HAKEN = _w / "haken" / "auftragshypothese_waechter.py"


def _rufe_haken(tool_name: str, tool_input: dict) -> dict:
    eingabe = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    lauf = subprocess.run(
        [sys.executable, str(HAKEN)], input=eingabe,
        capture_output=True, text=True, timeout=30,
    )
    assert lauf.returncode == 0, f"Haken muss immer exit 0 liefern, war {lauf.returncode}"
    if not lauf.stdout.strip():
        return {}
    return json.loads(lauf.stdout)


def test_positiv_messung_und_ungeschuetzte_hypothese_wird_gemeldet():
    prompt = (
        "Miss, ob die Wache im Testlauf anschlaegt. Vermutlich liegt es an "
        "einer falschen Kodierung -- danach ist die Sache klar."
    )
    fund = waechter.pruefe(prompt)
    assert fund is not None
    assert "vermutlich liegt es an" in fund.lower()


def test_negativfall_fakten_ohne_schlussfolgerung_wird_nicht_gemeldet():
    """Woertlicher Ausschnitt aus Aufgabe 71 ('Welle 1c: Abrufzahlen
    zuordenbar machen'), Agentenauftrag von heute -- reine Fakten, keine
    Hypothese des Auftraggebers."""
    negativ_real = (
        "FAKTEN\nZwei Messungen der Abrufguete widersprechen sich: 45 gegen "
        "33 von 205 Zielen. Die Differenz ist nicht zuordenbar -- niemand "
        "kann sagen, gegen welchen Codestand, welchen Korpus und welchen "
        "Pfad jede gemessen wurde.\n\nDEINE AUFGABE IST NICHT, DIE DIFFERENZ "
        "ZU ERKLAEREN. Sie ist, sie ZUORDENBAR zu machen -- und dann zu "
        "messen, ob sie bleibt.\n\nREIHENFOLGE, bindend:\n1. Die beiden "
        "Ergebnisdateien unter runs/ finden ... Diese Bestandsaufnahme ist "
        "Teil des Ergebnisses.\n2. ERST DANN entscheiden, ob die Differenz "
        "aus dem Vorhandenen erklaerbar ist oder ob eine NEUMESSUNG noetig "
        "ist. Rate nicht."
    )
    assert waechter.pruefe(negativ_real) is None


def test_pruefstein_hypothese_mit_widerlegen_auflage_wird_nicht_gemeldet():
    """Woertlicher Ausschnitt aus 'Caveman gegen den Antwort-Abruf',
    Agentenauftrag von heute -- Hypothese, ausdruecklich zur Widerlegung
    aufgegeben. Die richtige Form, darf NICHT gemeldet werden."""
    pruefstein_real = (
        "Wie gross ist die Schnittmenge? Die Vermutung im Auftrag lautet, "
        "dass gestrichene Artikel und Fuellwoerter ohnehin durch die "
        "IDF-Gewichtung fallen -- PRUEFE das, statt es zu uebernehmen, und "
        "widerlege es wenn moeglich."
    )
    assert waechter.pruefe(pruefstein_real) is None


def test_grenzwert_hypothese_ohne_messauftrag_wird_nicht_gemeldet():
    assert waechter.pruefe("Der Verdacht liegt auf dem alten Cache. Baue die neue Route.") is None


def test_grenzwert_widerlegen_ausserhalb_des_fensters_schuetzt_nicht_mehr():
    weit_entfernt = (
        "Pruefe die Wache. Vermutlich liegt es an X. " + ("Fuelltext. " * 80) +
        "Am Ende noch: widerlege, falls du Zeit hast."
    )
    assert waechter.pruefe(weit_entfernt) is not None


def test_werkzeugfilter_nur_agent_tool_wird_geprueft():
    antwort = _rufe_haken("Bash", {"command": "vermutlich liegt es an X, miss es"})
    assert antwort == {}


def test_echte_hakeneingabe_liefert_gueltiges_pretooluse_json():
    prompt = (
        "Miss, ob die Wache im Testlauf anschlaegt. Vermutlich liegt es an "
        "einer falschen Kodierung -- danach ist die Sache klar."
    )
    antwort = _rufe_haken("Agent", {"description": "Test", "prompt": prompt})
    hso = antwort["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "allow"
    assert "vermutlich liegt es an" in hso["permissionDecisionReason"].lower()


def test_leere_oder_kaputte_eingabe_liefert_exit_0_ohne_ausgabe():
    lauf = subprocess.run(
        [sys.executable, str(HAKEN)], input="{kaputt json",
        capture_output=True, text=True, timeout=30,
    )
    assert lauf.returncode == 0
    assert lauf.stdout.strip() == ""


def test_selftest_laeuft_durch():
    lauf = subprocess.run(
        [sys.executable, str(HAKEN), "--selftest"],
        capture_output=True, text=True, timeout=30,
    )
    assert lauf.returncode == 0, lauf.stdout + lauf.stderr
    assert "selftest ok" in lauf.stdout
