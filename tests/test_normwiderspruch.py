"""Widersprueche zwischen gleichrangigen Normen finden.

DER ANLASS: Der Wettbewerbsvergleich vom 2026-08-20 fand bei `holographic`
(dem einzigen rein lokalen der acht Anbieter) ein `contradict()`, das
brainlehr fehlt. Normkonflikte fallen hier bisher nur auf, wenn ein Mensch
stolpert -- L-2bba13 haelt einen seit dem 2026-08-08 als "ungeloest" fest.

DER WEG DORTHIN WAR EIN NULLBEFUND, und er gehoert zur Begruendung:
Der naheliegende Ansatz -- hohe BEDEUTUNGSAEHNLICHKEIT bei gleichem Rang --
findet Widersprueche NICHT. Gemessen am 2026-08-20 ueber 47 Rang-1-Normen
(1 081 Paare): Der bekannte Konflikt aus L-2bba13 landete auf Rang 266, und
die acht aehnlichsten Paare waren durchweg verwandte Regeln, kein einziger
Widerspruch. Der Grund ist eine Eigenschaft von Einbettungen: "X ist erlaubt"
und "X ist verboten" liegen dicht beieinander -- sie erfassen Themennaehe,
nicht Wahrheitswert.

WAS TRAEGT, ist holographics Umkehrung (retrieval.py:355-430): hohe
WORTUEBERLAPPUNG bei NIEDRIGER Bedeutungsnaehe. Zwei Texte, die dieselben
Begriffe nennen und trotzdem semantisch auseinanderliegen. Damit landete
derselbe Konflikt auf Rang 3 von 12.

WARUM GLEICHER RANG: Zwei Normen verschiedenen Rangs koennen einander
stechen (lex superior). Zwei gleichrangige koennen es nicht -- dort ist ein
Widerspruch ungeloest und bleibt es, bis ein Mensch entscheidet. Genau das
sagt L-2bba13: "weder lex superior noch lex specialis noch lex posterior
entscheidet".
"""
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent.parent / "melder"),
                str(Path(__file__).resolve().parent.parent)]
import normwiderspruch as nw  # noqa: E402


def test_gemeinsame_woerter_bei_ferner_bedeutung_ist_verdaechtig():
    """Der Kern des Verfahrens, an gestellten Werten."""
    assert nw.verdacht(ueberlappung=0.30, bedeutung=0.40) > \
           nw.verdacht(ueberlappung=0.30, bedeutung=0.90)


def test_hohe_bedeutungsnaehe_allein_ist_KEIN_verdacht():
    """DER NULLBEFUND ALS TESTZEILE: Zwei Texte, die dasselbe sagen, sind
    keine Widersprueche -- egal wie aehnlich sie sind. Genau daran ist der
    erste Ansatz gescheitert (Rang 266 von 1 081)."""
    assert nw.verdacht(ueberlappung=0.05, bedeutung=0.95) < 0


def test_wortueberlappung_ignoriert_fuellwoerter():
    a = "Der Nutzer sieht die Oberflaeche und das Bedienelement"
    b = "Die Oberflaeche zeigt dem Nutzer ein Bedienelement"
    c = "Ein Agent liest den Auftrag und meldet die Abweichung"
    assert nw.ueberlappung(a, b) > nw.ueberlappung(a, c)


def test_identische_texte_sind_kein_widerspruch():
    """NEGATIVFALL: Volle Ueberlappung UND volle Bedeutungsnaehe -- das ist
    eine Dublette, kein Konflikt. Ohne diese Zeile meldete der Melder jede
    doppelt erfasste Regel."""
    assert nw.verdacht(ueberlappung=1.0, bedeutung=1.0) <= 0


def test_schwelle_ist_ausdruecklich_ungemessen():
    """Die Wortschwelle 0,10 stammt aus EINEM Lauf gegen EINEN bekannten
    Konflikt. Sie ist geraten, nicht kalibriert -- und das muss im Modul
    stehen, sonst wird sie beim naechsten Lesen fuer gemessen gehalten."""
    quelle = (Path(nw.__file__)).read_text(encoding="utf-8")
    assert "ungemessen" in quelle.lower() or "geraten" in quelle.lower()


def test_paare_kommen_sortiert_und_mit_beiden_werten():
    """Ein Verdacht ohne seine beiden Eingangsgroessen ist nicht pruefbar --
    der Leser muss sehen, WORAN es lag."""
    paare = nw.finde(
        [("a", "/x/eins", "Oberflaeche Nutzer Bedienelement Name", [1.0, 0.0]),
         ("b", "/x/zwei", "Oberflaeche Nutzer Bedienelement verbergen", [0.0, 1.0]),
         ("c", "/x/drei", "Ganz anderes Thema Fahrzeug Motor", [1.0, 0.0])])
    assert paare, "kein Paar gefunden, obwohl zwei Texte dieselben Woerter tragen"
    erst = paare[0]
    assert {"ueberlappung", "bedeutung", "verdacht", "a", "b"} <= set(erst)
    assert paare == sorted(paare, key=lambda p: -p["verdacht"])
