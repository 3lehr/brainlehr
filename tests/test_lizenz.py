"""Die Lizenz ist AGPL-3.0, und sie steht dort, wo jemand sie liest.

DER BEFUND (2026-08-20): github.com/3lehr/brainlehr stand seit dem 2026-08-17
oeffentlich unter **MIT**. Beschlossen war AGPL-3.0 plus CLA. Der Betreiber
dazu woertlich: "nit mit wurde nicht bewusst gewaehlt!" und "wir wollte
zuerst die strengere lizenz!!!" -- MIT kam als VORGABEWERT beim Neuanlegen
des Exports hinein, nicht durch eine Entscheidung. In der Historie jenes
Baums gab es nie eine AGPL-Fassung, deshalb sah kein Diff verdaechtig aus.

WARUM ES NIEMAND BEMERKTE, und das ist die eigentliche Luecke: Der
vorhandene push_guard.py prueft Ziel, Zweig und Commit-Uebergang -- die
Woerter "lizenz" und "license" kommen in seiner Logik nicht vor. Und die
README nannte die Lizenz des FREMDMATERIALS (NASA, GermanQuAD) ausfuehrlich
und ehrlich, die des eigenen Codes gar nicht. Niemand liest LICENSE, jeder
liest README. Eine Regel ohne Mechanismus ist eine Absicht.

Diese Datei ist der Mechanismus. Sie faellt rot, sobald jemand die Lizenz
wechselt, ohne es auch dort hinzuschreiben, wo es gelesen wird.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_lizenzdatei_ist_agpl():
    text = (REPO / "LICENSE").read_text(encoding="utf-8")
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in text, (
        "LICENSE traegt nicht die AGPL -- beschlossen ist AGPL-3.0 plus CLA")
    assert "Version 3" in text


def test_keine_zweite_lizenz_im_repo():
    """NEGATIVFALL: Genau so ist es passiert -- eine MIT-Datei stand da, und
    weil sie von Anfang an dastand, sah kein Diff verdaechtig aus."""
    text = (REPO / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" not in text
    assert "Permission is hereby granted, free of charge" not in text, (
        "das ist der MIT-Wortlaut")


def test_readme_nennt_die_lizenz():
    """Der Ort, an dem sie tatsaechlich gelesen wird."""
    text = (REPO / "README.md").read_text(encoding="utf-8")
    assert "AGPL" in text, (
        "die README nennt die Lizenz des eigenen Codes nicht -- genau diese "
        "Luecke liess MIT drei Tage unbemerkt oeffentlich stehen")


def test_beitragsablauf_mit_cla_vorhanden():
    """Die AGPL war nie allein beschlossen, sondern mit CLA."""
    p = REPO / "CONTRIBUTING.md"
    assert p.is_file(), "CONTRIBUTING.md fehlt -- die AGPL galt mit CLA"
    assert "CLA" in p.read_text(encoding="utf-8")
