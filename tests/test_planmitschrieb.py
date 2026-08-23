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


# --- Katalogmitschrieb -------------------------------------------------

def _c(hash_, nachricht, dateien=()):
    return {"hash": hash_, "nachricht": nachricht, "dateien": list(dateien)}


def test_entscheidungswort_ohne_katalog_faellt_auf():
    lage = pm.pruefe_katalog([
        _c("a1", "decide(x): Paket traegt nichts\n\nBetreiberentscheidung 2026-08-21, woertlich: ...")])
    assert lage["geprueft"] == 1 and lage["befunde"] == 1


def test_entscheidungswort_MIT_katalog_ist_sauber():
    """Norm-Fall: Commit 6c464372 traegt das Wort UND aendert den Katalog --
    er muss sauber sein. Findet die Regel ihn trotzdem, ist die Regel falsch,
    nicht der Commit."""
    lage = pm.pruefe_katalog([
        _c("6c464372", "decide(auslieferung): kein Bestand\n\nBetreiberentscheidung 2026-08-21",
           dateien=["docs/REQUIREMENTS_BRAINLEHR.md", "tests/test_requirements_brainlehr.py"])])
    assert lage["geprueft"] == 1 and lage["befunde"] == 0


def test_plural_wird_erkannt():
    """Reale Hausform (git log): 'Betreiberentscheidungen'. Muss ebenfalls
    treffen -- eine Anker-Regel, die nur die Einzahl kennt, wuerde die
    haeufigste Form im eigenen Log verfehlen."""
    lage = pm.pruefe_katalog([
        _c("p1", "docs(katalog): nachgetragen\n\nBetreiberentscheidungen vom 2026-08-21 eingearbeitet")])
    assert lage["geprueft"] == 1 and lage["befunde"] == 1


def test_jedes_wort_einzeln_trifft():
    """Je Zweig der Oder-Verkettung eine Zeile, die NUR diesen Zweig trifft --
    eine Zeile mit zwei Verdachtswoertern belegt nichts (L-8fce9c)."""
    for wort in ("Betreiberentscheidung", "Betreiberwort", "Betreiberweisung",
                 "Betreiberdirektive"):
        lage = pm.pruefe_katalog([_c("x", f"fix(y): kurz\n\n{wort} umgesetzt")])
        assert lage["befunde"] == 1, f"{wort} haette treffen muessen"


def test_klein_und_grossschreibung_egal():
    lage = pm.pruefe_katalog([_c("a1", "fix: kurz\n\nbetreiberweisung umgesetzt")])
    assert lage["befunde"] == 1


def test_verwandtes_wort_OHNE_praefix_ist_kein_treffer():
    """NEGATIVPROBE (L-8fce9c): 'Entscheidung' allein, ohne 'Betreiber'-
    Vorsilbe, ist keine Betreiberentscheidung -- die Regel darf nicht auf dem
    blossen Wortstamm 'entscheidung' anschlagen."""
    lage = pm.pruefe_katalog([
        _c("a1", "decide(x): kurz\n\nEine Entscheidung wurde getroffen")])
    assert lage["geprueft"] == 0 and lage["befunde"] == 0


def test_commit_ohne_entscheidungswort_zaehlt_nicht_in_den_nenner():
    """Der Nenner ist die Menge mit Entscheidungswort (Norm 17b14a32), nicht
    alle Commits."""
    lage = pm.pruefe_katalog([
        _c("a1", "fix(x): Tippfehler behoben"),
        _c("b2", "docs: README aktualisiert"),
    ])
    assert lage["geprueft"] == 0 and lage["befunde"] == 0


def test_beschreibendes_vorkommen_mitten_im_satz_zaehlt_NICHT():
    """NEGATIVPROBE mit echtem Wortlaut (Commit 4e10b217, der ERSTE Fehlalarm
    dieses Melders): Der Commit BAUT diesen Melder und nennt das Wort nur,
    weil er die eigene Regex beschreibt. Gemessen an den letzten 60 Commits
    steht eine echte Entscheidung am ZEILENANFANG, eine Beschreibung mitten
    im Satz -- daran und an nichts anderem wird unterschieden.

    Erwartungswert kommt aus der REGEL, nicht aus dem Lauf: 'nennt eine
    Commit-Nachricht ein Entscheidungswort (Betreiberentscheidung/...)' ist
    ein Satz UEBER das Wort, keine Entscheidung. Er darf den Nenner nicht
    einmal betreten (L-b034c4)."""
    lage = pm.pruefe_katalog([_c("4e10b217",
        "feat(katalog): Waechter gegen stillen Katalog-Rueckstand\n\n"
        "Der Melder beanstandet, wenn eine Commit-Nachricht ein "
        "Entscheidungswort (Betreiberentscheidung/Betreiberwort/...) traegt, "
        "ohne den Katalog anzufassen.")])
    assert lage["geprueft"] == 0 and lage["befunde"] == 0


def test_messcommit_mit_rueckbezug_zaehlt_NICHT():
    """Zweite Negativprobe, ebenfalls aus dem echten Log (a166cf99): Ein
    MESScommit beruft sich auf eine BEREITS eingetragene Zeile. Ein Rueckbezug
    ist keine neue Entscheidung und braucht keine neue Katalogzeile."""
    lage = pm.pruefe_katalog([_c("a166cf99",
        "measure(p19): 707 nutzersichtbare Textstellen\n\n"
        "Erhebung zu BDW-P19, Betreiberwort: nutzersichtbare Texte sollen "
        "der Sprache des Nutzers folgen.")])
    assert lage["geprueft"] == 0 and lage["befunde"] == 0


def test_katalog_der_den_commit_NENNT_macht_ihn_sauber():
    """Zweiter Weg zur Sauberkeit (2026-08-23): Der Commit aendert den Katalog
    nicht, aber der Katalog nennt ihn. Ohne diesen Weg bleibt jeder
    nachgetragene Beschluss fuer immer beanstandet, und eine Kennzahl, die
    man nicht auf null bringen kann, wird weggeklickt."""
    lage = pm.pruefe_katalog(
        [_c("d2674ac5", "feat(x): kurz\n\nBetreiberentscheidung 2026-08-21")],
        katalogtext="| BDW-P22 | `bauvermeidung` | ... Commit `d2674ac5` |")
    assert lage["geprueft"] == 1 and lage["befunde"] == 0


def test_zu_kurzer_hash_im_text_macht_NICHT_sauber():
    """NEGATIVPROBE zum zweiten Weg: Eine kurze Zeichenfolge kann zufaellig im
    Fliesstext stehen. Unter 7 Zeichen wird nicht freigesprochen -- sonst
    entwertet der neue Weg den ganzen Melder."""
    lage = pm.pruefe_katalog(
        [_c("abc12", "feat(x): kurz\n\nBetreiberentscheidung 2026-08-21")],
        katalogtext="hier steht abc12 mitten im Text")
    assert lage["befunde"] == 1


def test_fehlender_katalog_faellt_auf_das_strengere_verhalten_zurueck():
    """Fehlt der Katalog, ist der Text leer -- dann darf der zweite Weg NICHT
    versehentlich jeden freisprechen (leerer Text als Teilstring-Treffer)."""
    lage = pm.pruefe_katalog(
        [_c("d2674ac5", "feat(x): kurz\n\nBetreiberentscheidung 2026-08-21")],
        katalogtext="")
    assert lage["befunde"] == 1


def test_katalogmeldung_nennt_hashes_und_schweigt_wenn_sauber():
    voll = pm.als_text_katalog(pm.pruefe_katalog(
        [_c("abc1234", "fix: kurz\n\nBetreiberwort umgesetzt")]))
    assert "abc1234" in voll
    sauber = pm.als_text_katalog(pm.pruefe_katalog(
        [_c("a1", "fix: kurz\n\nBetreiberwort umgesetzt",
            dateien=["docs/REQUIREMENTS_BRAINLEHR.md"])]))
    assert sauber == ""
