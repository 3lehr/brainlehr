"""Wird der Plan mitgeschrieben, wenn Code entsteht?

DER ANLASS ist ein Knoten mit Rang 1 vom 2026-08-16
(/methodik/direktiven/dringend-an-brainlehr): "Sieben Betreiberentscheidungen
wurden umgesetzt, committet und gebaut -- aber nie in den Plan geschrieben.
Gemessen: null Vorkommen im Plantext. Aufgefallen nur, weil der Betreiber
selbst fragte."

Der Knoten verlangt ausdruecklich "einen Waechter, keinen Vorsatz". Gemessen
am 2026-08-20: Es gab keinen. Vier Tage lang war die Forderung eine Absicht.

WARUM MELDER UND NICHT WAECHTER, also Hinweis statt Veto: Nicht jeder Commit
gehoert in einen Plan. Ein Tippfehler, eine Umbenennung, ein Formatlauf --
wer die blockiert, wird umgangen, und dann wirkt gar nichts mehr. Der Melder
nennt das VERHAELTNIS und laesst den Menschen entscheiden.
"""
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent.parent / "melder"),
                str(Path(__file__).resolve().parent.parent)]
import planmitschrieb as pm  # noqa: E402


def test_code_ohne_plan_faellt_auf():
    lage = pm.pruefe([
        {"hash": "a1", "dateien": ["kern/x.py", "tests/test_x.py"]},
        {"hash": "b2", "dateien": ["melder/y.py"]},
    ])
    assert lage["ohne_plan"] == 2
    assert lage["mit_plan"] == 0


def test_plan_mitgeschrieben_zaehlt_nicht_als_befund():
    lage = pm.pruefe([
        {"hash": "a1", "dateien": ["kern/x.py", "docs/PLAN_X_2026-08-20.md"]},
    ])
    assert lage["ohne_plan"] == 0 and lage["mit_plan"] == 1


def test_reine_dokumentation_zaehlt_gar_nicht():
    """NEGATIVFALL: Ein Commit, der nur Text aendert, setzt keine Entscheidung
    um -- er darf den Nenner nicht aufblaehen. Sonst sinkt die Quote bei jedem
    Schreibtag, und der Melder misst Fleiss statt Disziplin."""
    lage = pm.pruefe([
        {"hash": "a1", "dateien": ["STAND.md", "README.md"]},
        {"hash": "b2", "dateien": ["docs/adr/ADR-099-irgendwas.md"]},
    ])
    assert lage["geprueft"] == 0, "Dokumentationscommits gehoeren nicht in den Nenner"


def test_der_nenner_ist_die_geprueft_menge():
    """Norm 17b14a32: Der Nenner ist die GEPRUEFTE Menge, nie die Befundliste.
    Sonst meldet der Melder '0 von 0' und sieht dabei gruen aus."""
    lage = pm.pruefe([
        {"hash": "a1", "dateien": ["kern/x.py"]},
        {"hash": "b2", "dateien": ["kern/y.py", "docs/PLAN_Z_2026-08-20.md"]},
        {"hash": "c3", "dateien": ["README.md"]},
    ])
    assert lage["geprueft"] == 2
    assert lage["ohne_plan"] + lage["mit_plan"] == lage["geprueft"]


def test_schweigt_wenn_alles_mitgeschrieben_ist():
    text = pm.als_text(pm.pruefe([
        {"hash": "a1", "dateien": ["kern/x.py", "docs/PLAN_A_2026-08-20.md"]}]))
    assert text == ""


def test_meldung_nennt_die_commits_namentlich():
    """Ein Melder, der nur eine Zahl nennt, zwingt zum Suchen. Wer die Hashes
    nennt, macht die Pruefung zu einem Blick."""
    text = pm.als_text(pm.pruefe([{"hash": "abc1234", "dateien": ["kern/x.py"]}]))
    assert "abc1234" in text


def test_plan_im_NACHBARCOMMIT_zaehlt_ebenfalls():
    """DER FEHLER MEINES ERSTEN ENTWURFS, gefunden beim ersten echten Lauf:
    Er meldete 13 von 13 Code-Commits als "ohne Plan" -- obwohl der Plan an
    diesem Tag fuenfmal fortgeschrieben worden war, nur in EIGENEN Commits.

    Code und Plan getrennt zu committen ist SAUBERER, nicht schlechter: Ein
    Sammelcommit ueber beides laesst sich nicht einzeln zurueecknehmen. Mein
    Melder mass damit die Commit-Granularitaet statt der Disziplin -- er
    haette jeden bestraft, der ordentlich trennt, und genau die belohnt, die
    alles in einen Commit werfen.

    Richtig ist das ZEITFENSTER: Gab es rund um diesen Code eine
    Planaenderung?"""
    lage = pm.pruefe([
        {"hash": "a1", "dateien": ["kern/x.py"]},
        {"hash": "b2", "dateien": ["docs/PLAN_Z_2026-08-20.md"]},
        {"hash": "c3", "dateien": ["melder/y.py"]},
    ], fenster=2)
    assert lage["ohne_plan"] == 0, (
        "Plan im Nachbarcommit muss zaehlen -- sonst bestraft der Melder "
        "sauberes Trennen")


def test_ohne_fenster_bleibt_es_streng():
    """Gegenprobe: Liegt WEIT entfernt kein Plan, bleibt der Befund."""
    lage = pm.pruefe([
        {"hash": "a1", "dateien": ["kern/x.py"]},
        {"hash": "b2", "dateien": ["kern/y.py"]},
        {"hash": "c3", "dateien": ["kern/z.py"]},
    ], fenster=2)
    assert lage["ohne_plan"] == 3
