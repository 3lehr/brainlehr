"""Sprache eines Textes erkennen -- deutsch, englisch, oder ehrlich nichts.

BDW-P10, Auftrag B1b. Die Achse `sprache` in schema.sql ist bewusst NULL-faehig
und ohne Vorgabewert: was nicht erkannt ist, bleibt leer. Diese Datei liefert
genau das -- `None` ist ein Ergebnis, kein Fehlschlag. Ein geratenes 'de' liesse
sich spaeter nicht mehr von einem erkannten unterscheiden, und diese
Doppeldeutigkeit hat die Normschicht (norm_rang IS NULL) im selben Schema schon
einmal teuer bezahlt.

VERFAHREN: 36 Stoppwoerter, 18 je Sprache, gezaehlt als ganze Woerter auf
kleingeschriebenem Text. Kein Modell, keine Abhaengigkeit, reine Stdlib --
Stoppwoerter sind die haeufigsten Woerter einer Sprache, ein Satz ohne sie ist
kaum ein Satz. Gewaehlt sind nur Woerter, die in der anderen Sprache NICHT
vorkommen: 'in', 'so', 'man', 'was', 'will' und 'hat/hate' stehen deshalb
bewusst nicht in der Liste, obwohl sie haeufiger sind als manches, was drin
steht -- ein Wort, das beide Seiten zaehlen, verschiebt nur das Rauschen.

GRENZE (ponytail: absichtlich, Ausbau erst bei Bedarf): nur de/en. Eine dritte
Sprache faellt auf None, nicht auf die naechstbeste -- das ist die gewollte
Richtung. Wer Franzoesisch braucht, ergaenzt eine Liste und den Vergleich.
"""
from __future__ import annotations

import re

# 18 je Sprache. Schnittmenge ist leer -- das ist die Bedingung, unter der
# gezaehlte Treffer ueberhaupt etwas unterscheiden (Probe unten prueft es).
DE = frozenset("""der die das und nicht ist sind mit eine auch wird werden
                  von dem sich fuer oder dass""".split())
EN = frozenset("""the and of to is are with that this for not from have has
                  been it as which""".split())

# Mindesttrefferzahl des Siegers. Ein einzelnes 'the' in einem deutschen
# Zitat soll den Ausschlag nicht geben; zwei Treffer sind die billigste
# Schwelle, die das verhindert.
MINDEST = 2

_WORT = re.compile(r"[a-zäöüß]+")


def _falte(text: str) -> str:
    """Umlaute auf die Umschrift, die in der Stoppwortliste steht.

    Der Bestand traegt beide Schreibweisen -- 'fuer' in Dateien, die auf
    ASCII bestehen, 'für' in allem anderen. Wer nur eine kennt, misst die
    Schreibweise statt die Sprache."""
    for hin, her in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(hin, her)
    return text


def erkenne(text: str | None) -> str | None:
    """'de', 'en' oder None. None heisst: nicht erkannt, nicht geraten."""
    if not text:
        return None
    woerter = _WORT.findall(_falte(text.lower()))
    if not woerter:
        return None
    de = sum(1 for w in woerter if w in DE)
    en = sum(1 for w in woerter if w in EN)
    if de == en:
        return None
    sieger, punkte = ("de", de) if de > en else ("en", en)
    return sieger if punkte >= MINDEST else None


def _selftest() -> None:
    assert not (DE & EN), f"Stoppwort in beiden Listen: {sorted(DE & EN)}"
    assert len(DE) == len(EN) == 18, (len(DE), len(EN))

    assert erkenne("Die Sitzung wurde vertagt, weil der Antrag nicht vorlag.") == "de"
    assert erkenne("Für die Auswertung ist das Ergebnis nicht maßgeblich.") == "de"
    assert erkenne("The meeting was adjourned because the motion had not been filed.") == "en"
    assert erkenne("This is a note that has been written for the record.") == "en"

    # Negativfall -- hier liegt der eigentliche Wert: nichts wird geraten.
    assert erkenne(None) is None
    assert erkenne("") is None
    assert erkenne("qwertz zxcvb") is None
    assert erkenne("Kalibrierbremse Messlauf Abrufguete") is None, "Fachwoerter sind keine Sprache"
    assert erkenne("42 // 7 == 6") is None
    # Genau ein Treffer reicht nicht (MINDEST): ein englisches Zitat in einem
    # sonst wortlosen Fragment kippt die Aussage nicht.
    assert erkenne("Modul the Kalibrierung") is None
    # Gleichstand ist Unklarheit, nicht Muenzwurf.
    assert erkenne("und the") is None
    # Dritte Sprache faellt auf None, nicht auf die naechstbeste.
    assert erkenne("La sesión fue aplazada porque la moción no había sido presentada.") is None
    # Umschrift und Umlaut fuehren zum selben Ergebnis.
    assert erkenne("fuer die Sache") == erkenne("für die Sache") == "de"

    print("spracherkennung: alle Proben bestanden")


if __name__ == "__main__":
    _selftest()
