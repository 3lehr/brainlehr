"""Entlokalisierung von QUELLTEXT -- Kommentare und Docstrings, sonst nichts.

DER BEFUND, der dieses Werkzeug verlangt (brainlehr 2026-08-20): Beim ersten
vollstaendigen Export scheiterten 144 von 731 Dateien an `absolute-path` oder
`private-context`. Nachgesehen: fast durchweg Heimatpfade und Verbundnamen in
KOMMENTAREN und DOCSTRINGS -- Erklaertext, kein Verhalten. Eine einzige davon
(kern/normrang.py, ein Pfad in einem Fixture-String) blockierte ueber
knowledge_mcp_server und tests/conftest.py den GESAMTEN Testlauf des Exports.

Die Grenze ist der ganze Punkt: Ein Kommentar wird nie ausgewertet, ein
Docstring nur gelesen. Ein Pfad in ausgewertetem Code dagegen kann Verhalten
tragen -- der wird gemeldet, nicht ersetzt. Wer beides gleich behandelt,
retuschiert einen Befund weg.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tool"))
import entlokalisieren as el  # noqa: E402


def test_kommentar_wird_ersetzt():
    q = '# liegt unter /Users/jemand/Begod2026/x\nX = 1\n'
    neu, rest = el.bearbeite(q)
    assert "/Users/jemand/" not in neu and "Begod2026" not in neu
    assert "<heim>/" in neu and "<arbeitsbereich>" in neu
    assert "X = 1" in neu
    assert rest == []


def test_docstring_wird_ersetzt():
    q = 'def f():\n    """liegt in Begod2026 unter /Volumes/platte/y"""\n    return 1\n'
    neu, rest = el.bearbeite(q)
    assert "Begod2026" not in neu and "/Volumes/platte/" not in neu
    assert "return 1" in neu
    assert rest == []


def test_ausgewerteter_code_wird_gemeldet_nicht_ersetzt():
    """DER NEGATIVFALL, und er ist der Grund fuer das ganze Werkzeug:
    Ein Pfad in ausgewertetem Code kann Verhalten tragen. Ihn stillschweigend
    zu ersetzen macht aus einem Befund eine Retusche -- und der Export laeuft
    dann anders als das Original, ohne dass es jemand merkt."""
    q = 'DB = "/Users/jemand/daten.db"\n'
    neu, rest = el.bearbeite(q)
    assert neu == q, "ausgewerteter Code bleibt unangetastet"
    assert rest and rest[0][0] == 1, "und wird mit Zeilennummer gemeldet"


def test_syntaxfehler_faellt_nicht_still_durch():
    """Eine Datei, die sich nicht parsen laesst, wird NICHT halb bearbeitet."""
    neu, rest = el.bearbeite("def f(\n")
    assert neu is None and rest == []


def test_datei_ohne_fund_bleibt_bytegleich():
    q = 'def f():\n    """harmlos"""\n    return 1\n'
    neu, rest = el.bearbeite(q)
    assert neu == q and rest == []


def test_wer_die_regel_traegt_wird_nicht_von_ihr_bearbeitet():
    """Eine Datei, die das gesuchte Muster im Klartext NENNEN muss, darf es
    behalten -- sonst zerstoert die Regel ihre eigene Grundlage.

    Zweimal an einem Tag passiert (2026-08-20): kern/normrang.py beschreibt
    "Rang 1 == globale CLAUDE.md" und der Code prueft genau diesen Namen; die
    Ersetzung machte die Doku falsch. Und dieses Werkzeug selbst erklaerte,
    wonach es sucht -- nach dem eigenen Lauf stand dort der Platzhalter, und
    das Beispiel war weg.

    Die Ausnahme ist eng: nur die zwei Dateien, die die Regel TRAGEN. Jede
    andere Datei, die zufaellig davon spricht, wird normal bearbeitet."""
    assert "tool/entlokalisieren.py" in el.AUSNAHMEN
    assert "pflege/export_offen.py" in el.AUSNAHMEN
    assert "kern/speicher.py" not in el.AUSNAHMEN, "die Ausnahme bleibt eng"
