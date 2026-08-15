"""Wirksamkeits-Beleg fuer haken/auftragshypothese_waechter.py -- Aufgabe 97,
Teil 2, Nachtrag.

ANLASS: Der Waechter selbst (Logik, Selbsttest, tests/test_auftragshypothese_
waechter.py) war schon fertig und gruen -- aber keiner dieser Tests ruft die
EXAKTE Zeile auf, die der Klient tatsaechlich ausfuehrt, wenn das Agent-
Werkzeug startet. "Steht in der Einstellungsdatei" ist genau die Verwechslung,
vor der die Hausregel warnt (siehe CLAUDE.md, Abschnitt "Es funktioniert
braucht einen Beleg") -- ein Text-Treffer beweist nicht, dass der Prozess
laeuft. Dieser Test tut das: er liest den ECHTEN Kommandostring aus
~/.claude/settings.json und fuehrt ihn wortwoertlich aus, mit echten
Eingaben.

ROT VOR GRUEN: Vor 2026-08-14 (siehe Sicherungskopien unter
~/.claude/settings.json.bak-2026-08-14T0010 und aelter) stand in der Datei
KEIN Eintrag, der das Agent-Werkzeug an diesen Haken haengt -- der Klient
haette ihn beim Start des Werkzeugs nie aufgerufen. test_vorher_rot_kein_
ausloeser_vor_2026_08_14 belegt das am echten historischen Artefakt. Seit
einer Sicherung von 2026-08-14 (09:30) steht der Eintrag, und
test_nachher_gruen_* belegt, dass er bei echter Ausfuehrung tatsaechlich
feuert bzw. schweigt.

Sieht der Code anders aus als hier beschrieben (Pfad des Hakens, Matcher,
Kommandozeile), halte dich an den Code und melde die Abweichung.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
WURZEL = _w

EINSTELLUNGEN = Path.home() / ".claude" / "settings.json"
ALTE_SICHERUNG_OHNE_EINTRAG = Path.home() / ".claude" / "settings.json.bak-2026-08-14T0010"
HAKEN_DATEI = "auftragshypothese_waechter.py"

# Echte Eingaben, keine erfundenen:
#  - POSITIV: woertliches Zitat aus dem Modul-Docstring selbst -- der reale
#    Agentenauftrag vom 2026-08-13, der diesen Haken ueberhaupt veranlasst hat
#    (drei Falschbefunde, dreimal die eigene Hypothese im Auftrag).
ECHTER_POSITIV_AUFTRAG = (
    "MESSUNG (2026-08-13, ueber die 72 Agent-Auftraege dieser Sitzung von "
    "heute): Miss, ob der Waechter greift. Vermutlich liegt es an einer "
    "fehlenden Verdrahtung -- pruefe die Einstellungsdatei und bestaetige das."
)
#  - NEGATIV: woertlicher Auftragstext von heute (2026-08-15, Aufgabe 71,
#    Sitzung baum-20260815T054407-65075), reine Facharbeit ohne Hypothese.
ECHTER_NEGATIV_AUFTRAG = (
    "FAKTEN\nZwei Messungen der Abrufguete widersprechen sich: 45 gegen 33 "
    "von 205 Zielen. Die Differenz ist nicht zuordenbar -- niemand kann "
    "sagen, gegen welchen Codestand, welchen Korpus und welchen Pfad jede "
    "gemessen wurde.\n\nDEINE AUFGABE IST NICHT, DIE DIFFERENZ ZU "
    "ERKLAEREN. Sie ist, sie ZUORDENBAR zu machen -- und dann zu messen, "
    "ob sie bleibt."
)


def _finde_kommando(settings_pfad: Path) -> tuple[str | None, str | None]:
    """Liefert (matcher, kommandostring) des PreToolUse-Eintrags, der auf
    HAKEN_DATEI zeigt -- oder (None, None), wenn keiner existiert."""
    try:
        d = json.loads(settings_pfad.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None, None
    for eintrag in d.get("hooks", {}).get("PreToolUse", []):
        for h in eintrag.get("hooks", []):
            cmd = h.get("command", "")
            if HAKEN_DATEI in cmd:
                return eintrag.get("matcher"), cmd
    return None, None


def _fuehre_kommando_aus(kommando: str, stdin_text: str) -> tuple[str, float]:
    start = time.perf_counter()
    lauf = subprocess.run(kommando, input=stdin_text, capture_output=True,
                           text=True, shell=True, timeout=30)
    dauer = time.perf_counter() - start
    assert lauf.returncode == 0, (
        f"Kommando aus settings.json muss immer exit 0 liefern, war "
        f"{lauf.returncode}: {lauf.stderr[:300]}")
    return lauf.stdout.strip(), dauer


def test_vorher_rot_kein_ausloeser_vor_2026_08_14():
    """Historischer Beleg: die Sicherung von vor der Verdrahtung enthaelt
    KEINEN PreToolUse-Eintrag fuer das Agent-Werkzeug, der auf diesen Haken
    zeigt -- der Klient haette ihn nie aufgerufen."""
    if not ALTE_SICHERUNG_OHNE_EINTRAG.exists():
        return  # Sicherung existiert nur auf der Maschine, auf der sie entstand.
    matcher, kommando = _finde_kommando(ALTE_SICHERUNG_OHNE_EINTRAG)
    assert kommando is None, (
        "Die alte Sicherung sollte VOR der Verdrahtung liegen -- wenn sie "
        "den Eintrag schon enthaelt, ist die falsche Datei als 'vorher' "
        "gewaehlt. Befund melden statt stillschweigend uebergehen.")


def test_nachher_gruen_echtes_kommando_meldet_echten_positiv_auftrag():
    """Fuehrt die EXAKTE Zeile aus der aktiven settings.json aus (nicht nur
    das Python-Modul direkt) -- mit einem echten, dokumentierten
    Agentenauftrag, der Messung und ungeschuetzte Hypothese mischt."""
    if not EINSTELLUNGEN.exists():
        return
    matcher, kommando = _finde_kommando(EINSTELLUNGEN)
    assert kommando is not None, (
        "Kein PreToolUse-Eintrag fuer das Agent-Werkzeug zeigt auf "
        f"{HAKEN_DATEI} -- der Waechter ist gebaut, aber nicht verdrahtet.")
    assert matcher is not None and "Agent" in matcher, (
        f"Matcher {matcher!r} deckt das Agent-Werkzeug nicht ab")

    eingabe = json.dumps({
        "tool_name": "Agent",
        "tool_input": {"description": "echter Auftrag", "prompt": ECHTER_POSITIV_AUFTRAG},
    })
    ausgabe, dauer = _fuehre_kommando_aus(kommando, eingabe)
    print(f"  Laufzeit eines Aufrufs: {dauer * 1000:.1f} ms")
    assert ausgabe, "Echtes Kommando aus settings.json meldet den echten Positivfall nicht"
    hso = json.loads(ausgabe)["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "ask", (
        "Entscheidung 'ask' erwartet (Hinweis statt Sperre, siehe Modulkopf "
        "zur Fehlalarm-Begruendung), war " + repr(hso["permissionDecision"]))
    assert "vermutlich liegt es an" in hso["permissionDecisionReason"].lower()
    assert dauer < 5.0, f"Haken haengt an JEDEM Agentenstart -- {dauer:.2f}s ist zu langsam"


def test_nachher_gruen_echtes_kommando_schweigt_bei_echtem_negativ_auftrag():
    """Gegenprobe in die andere Richtung: derselbe echte Kommandostring,
    echter facharbeitlicher Auftragstext von heute -- keine Ausgabe, das
    Werkzeug darf ungestoert starten."""
    if not EINSTELLUNGEN.exists():
        return
    _, kommando = _finde_kommando(EINSTELLUNGEN)
    if kommando is None:
        return  # bereits oben als eigener Fund gemeldet
    eingabe = json.dumps({
        "tool_name": "Agent",
        "tool_input": {"description": "echter Auftrag", "prompt": ECHTER_NEGATIV_AUFTRAG},
    })
    ausgabe, _ = _fuehre_kommando_aus(kommando, eingabe)
    assert ausgabe == "", (
        f"Echter facharbeitlicher Auftrag ohne Hypothese wurde faelschlich "
        f"gemeldet: {ausgabe!r}")


def test_nachher_gruen_andere_werkzeuge_bleiben_stumm():
    """Der Matcher darf NUR das Agent-Werkzeug treffen -- sonst waere jeder
    Bash-/Edit-Aufruf durch dieselbe Pipeline verlangsamt."""
    if not EINSTELLUNGEN.exists():
        return
    _, kommando = _finde_kommando(EINSTELLUNGEN)
    if kommando is None:
        return
    eingabe = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "vermutlich liegt es an X, miss es"},
    })
    ausgabe, _ = _fuehre_kommando_aus(kommando, eingabe)
    assert ausgabe == ""


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v", "-s"]))
