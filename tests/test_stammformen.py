"""Deutsche Komposita muessen den Abruf nicht mehr blockieren (S12 Stufe 1).

BEFUND, der das veranlasst (PLAN_DESTILLE_2026-08-09.md §S12, gemessen
2026-08-09): Die Abrufguete liegt bei 20 % (7 von 35) gegen ~91 % beim
Standard-Hybrid-RAG und 25-33 % bei einfacher Dense-only-Suche. Wir liegen
unter dem SCHWACHEN Referenzwert. Als Ursache benannt: eine fehlende Stufe --
gesucht wird mit dem rohen Prompt.

Stufe 1 ist ausdruecklich die BILLIGE: deterministische Erweiterung ohne
Modell, kostet nichts je Prompt und ist vollstaendig nachvollziehbar.

WARUM DAS HIER UEBERHAUPT GREIFT, gemessen am 2026-08-11: knowledge_fts nutzt
`tokenize="trigram case_sensitive 0"` -- also einen Trigramm-Index, keinen
Wortindex. Eine Phrasensuche ist dort eine SUBSTRING-Suche. Damit findet ein
kuerzerer Stamm mehr als das vollstaendige Wort, und zwar nachweisbar:

    "buerger"       ->  6 Treffer
    "einbuergerung" ->  3 Treffer

Der Abruf nutzte das nicht: er suchte das Kompositum als Ganzes. "Kilometergeld"
und "Kilometersatz" haben so keinen gemeinsamen Treffer, obwohl beide
"kilometer" enthalten.

WAS HIER AUSDRUECKLICH NICHT PASSIERT: keywords() bleibt unveraendert. An
dessen Ergebnis haengt MIN_HITS (die Zahl verschiedener Prompt-Begriffe im
Treffertext, Wert 3 nach Pareto-Messung). Wuerde die Erweiterung dort
einfliessen, waere jeder Stamm ein zusaetzlicher Zaehler und die
Fehlalarmquote von 0,000 waere still dahin. Erweitert wird nur die SUCHE.


NACHTRAG 2026-08-11T12:15:00+0200 -- DIESE TESTS SIND ABSICHTLICH XFAIL:

Die Messung, die sie veranlasst hat, ist ueberholt. S12 nennt 20 Prozent
Abrufguete; gegen den Pruefkorpus V2 gemessen sind es heute 33/35 = 94,3
Prozent. Der Rueckstand, den die Stammformen schliessen sollten, existiert
nicht mehr. Die heutige Fehlstelle liegt woanders: 10 von 10 Faellen, in denen
der Abruf schweigen soll, sprechen -- ein Fehlalarm von 100 Prozent, waehrend
MIN_HITS=3 einst mit 0,000 gemessen war.

Nicht geloescht, weil die Zerlegung sachlich richtig bleibt: der Trigramm-Index
macht Teilwortsuche moeglich, und "buerger" findet nachweislich mehr (6) als
"einbuergerung" (3). Sie ist nur nicht mehr das Dringendste. Wer sie baut,
findet hier die Faelle fertig vor -- mit strict=True, damit ein gebauter
Stammformer diese Datei sofort rot faerbt statt still gruen zu bleiben.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Absichtlich xfail, Begruendung im Modulkopf. strict=True, damit ein spaeter
# gebauter Stammformer die Datei sofort ROT faerbt statt still gruen zu bleiben.
# NICHT als Modul-Marker: test_keywords_bleibt_unveraendert ist die Gegenprobe
# und besteht schon heute -- unter einem pauschalen xfail waere sie XPASS und
# damit rot. Genau das hat strict=True beim ersten Versuch aufgedeckt.
WARTET = pytest.mark.xfail(
    reason="S12 ueberholt: Abrufguete heute 94,3 statt 20 Prozent",
    strict=True)

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w), str(_w / "haken"), str(_w / "kern")]

import knowledge_recall_hook as hook  # noqa: E402


@WARTET
def test_kompositum_bekommt_einen_stamm():
    """Der Fall aus dem Plan, woertlich."""
    erweitert = hook.stammformen(["kilometergeld"])
    assert "kilometergeld" in erweitert, "das Original muss erhalten bleiben"
    assert any(s in erweitert for s in ("kilometer", "kilomet")), \
        f"kein brauchbarer Stamm in {erweitert}"


@WARTET
def test_deutsche_endungen_fallen_weg():
    for wort, stamm in (("einbuergerung", "einbuerger"),
                        ("aenderungen", "aenderung"),
                        ("knoten", "knot")):
        erweitert = hook.stammformen([wort])
        assert any(e.startswith(stamm[:6]) and e != wort for e in erweitert), \
            f"{wort}: kein Stamm gebildet, nur {erweitert}"


@WARTET
def test_kurze_woerter_bleiben_unangetastet():
    """GRENZWERT. Ein Stamm unter fuenf Zeichen trifft im Trigramm-Index fast
    alles -- die Erweiterung wuerde Rauschen erzeugen statt Treffer."""
    for kurz in ("test", "haken", "nodes"):
        assert hook.stammformen([kurz]) == [kurz], \
            f"{kurz} wurde unnoetig zerlegt: {hook.stammformen([kurz])}"


@WARTET
def test_keine_doppelten_und_stabile_reihenfolge():
    """Das Original steht immer vorn: die Suche gewichtet nicht, aber ein
    stabiler Ausdruck ist nachvollziehbar und im Protokoll vergleichbar."""
    erweitert = hook.stammformen(["messungen", "messung"])
    assert erweitert[0] == "messungen"
    assert len(erweitert) == len(set(erweitert)), f"Doppelte in {erweitert}"


@WARTET
def test_die_menge_bleibt_gedeckelt():
    """NEGATIVFALL: Ohne Deckel waechst der Suchausdruck mit jedem Begriff,
    und ein FTS5-Ausdruck mit hundert ODER-Zweigen ist langsam UND unpraezise.
    keywords() liefert hoechstens 8 Begriffe; mehr als das Doppelte darf die
    Erweiterung daraus nicht machen."""
    viele = ["einbuergerung", "kilometergeld", "aenderungen", "abrufguete",
             "wissensknoten", "pruefkorpus", "sitzungsmelder", "ausweisstelle"]
    assert len(hook.stammformen(viele)) <= 2 * len(viele)


@WARTET
def test_der_suchausdruck_enthaelt_die_staemme():
    """Der Weg, den der Abruf wirklich nimmt -- fts_match, nicht die
    Hilfsfunktion allein."""
    ausdruck = hook.fts_match(["einbuergerung"])
    assert '"einbuergerung"' in ausdruck
    assert " OR " in ausdruck, "der Stamm fehlt im Suchausdruck"


def test_keywords_bleibt_unveraendert():
    """DIE WICHTIGSTE GEGENPROBE: An keywords() haengt MIN_HITS=3, dessen
    Fehlalarmquote von 0,000 gemessen ist. Eine Erweiterung dort wuerde jeden
    Stamm mitzaehlen und die Quote still verschieben."""
    text = "wie ist die einbuergerung beim kilometergeld geregelt"
    kws = hook.keywords(text)
    assert "einbuergerung" in kws and "kilometergeld" in kws
    for k in kws:
        assert k in text.lower(), f"{k!r} steht nicht im Prompt -- keywords erweitert"
