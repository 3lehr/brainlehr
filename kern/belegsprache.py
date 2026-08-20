#!/usr/bin/env python3
"""Eine Frage, eine Wortliste: woran erkennt man einen Beleg im Text?

ANLASS, 2026-08-20, beim Push aufgelaufen: `melder/ablaufpflicht.py` und
`melder/rotprobe.py` pruefen DIESELBE Frage -- sagt dieser Commit, wie belegt
wurde? -- mit ZWEI verschiedenen Wortlisten. Der Ablauf war:

  1. ablaufpflicht hielt einen Commit an, dessen Nachricht "Selbsttest 7
     Faelle" sagte. Das Wort stand nicht in seiner Liste.
  2. Der Commit, der DAS behob, wurde von rotprobe angehalten -- seine
     Nachricht sagte "Gemessen ueber 1 204 Commits", und `gemessen` stand
     nicht in DESSEN Liste. Damit widersprach rotprobe seinem eigenen
     Docstring ("manche Behebungen sind an einer MESSUNG belegt").

Wer beiden Waechtern genuegen will, muss beide Wortlisten auswendig kennen --
und daran scheitert ein Mensch, nicht an der Regel. Deshalb hier, an einer
Stelle.

WAS DAS MODUL NICHT TUT: Es beurteilt die GUETE eines Belegs nicht. Es
erkennt, ob ueberhaupt einer benannt ist. Das ist der Unterschied zwischen
einem Waechter und einem Gutachter, und nur der erste laesst sich verdrahten.

BEIDE RICHTUNGEN ZAEHLEN, und das ist Absicht: "rot vor gruen" ist ein Beleg,
"geaendert, nicht verifiziert" ebenso. Was NICHT zaehlt, ist Schweigen.

    python3 kern/belegsprache.py --selftest
"""
from __future__ import annotations

import re
import sys

# Der Beleg gilt als benannt, wenn der Text sagt WIE belegt wurde -- oder
# ehrlich sagt, dass nicht belegt wurde. Jede Zeile stammt aus einer echten
# Commit-Nachricht dieses Verbunds, keine aus der Vorstellung.
BELEG = re.compile(
    # rot vor gruen, in allen Schreibweisen der Hausregel
    r"rot vor gr(?:ü|ue)n|rot-probe|rot vor|rot gegen|war (vorher )?rot|vorher rot"
    r"|schlug (vorher )?fehl|durchgerutscht"
    # Messung und Gegenprobe -- eine Messung IST ein Beleg
    # KEINE schliessende Wortgrenze, und das ist gemessen statt gewaehlt: Mit
    # `\bgemessen\b` verfehlt die Liste "gemessene", "gemessenen",
    # "Gegenproben", "Selbsttests" -- am echten Bestand 36 Commits mehr als
    # stumm gezaehlt als die Vorgaengerliste. Eine Zusammenlegung, die enger
    # ist als ihre Teile, ist keine.
    #
    # ABER die FUEHRENDE Wortgrenze bleibt, und sie ist der eigentliche
    # Gewinn: Die Vorgaengerlisten trafen `beleg` und `gemessen` als
    # Teilzeichenkette und zaehlten damit "UNgemessen" und "UNbelegt" als
    # Beleg -- also das Gegenteil. Gemessen an 1 207 Commits: 17 Faelle, die
    # die alte Liste erkannte und diese nicht; nachgesehen sind sie
    # ueberwiegend genau diese Verneinungen. `Gegenbeleg` ist der eine echte
    # Verlust und steht deshalb eigens drin.
    r"|\bgemessen|\bgegenprob|\bgegenbeleg|\babnahme|\bbeleg"
    # Kontrollen und Nulllinie -- die Begriffe, die dieses Haus taeglich
    # benutzt und die bis 2026-08-20 in dieser Liste FEHLTEN. Aufgefallen an
    # einem eigenen Commit, der "Positivkontrolle bestanden: treffer_heute
    # [15, 35]" schrieb und vom Waechter trotzdem als beleglos beanstandet
    # wurde. Dieselbe Klasse wie `gr[uü]n` gegen `gruen` (L-8fce9c, drittes
    # Vorkommen): der Waechter prueft seine Woerter, nicht die Sache.
    # Positiv- und Negativkontrolle stehen ausdruecklich BEIDE drin -- die
    # Negativkontrolle ist die, die vergessen wird (L-dd4b40).
    r"|\bpositivkontrolle|\bnegativkontrolle|\bnulllinie|\bstichprobe"
    # Selbsttest und Testlauf, mit Zahl
    r"|\bselbsttest|\bselftest|\bsuite gr(?:ü|ue)n"
    r"|\d+ ?(xctest-)?f(?:ä|ae)lle gr(?:ü|ue)n|\btests? gr(?:ü|ue)n\b|\d+ passed"
    # die ehrliche Gegenrichtung: kein Beleg, aber gesagt
    r"|nicht verifiziert|nicht gepr[uü]ft|ungepr[uü]ft"
    r"|deckten den fehler nicht|am ger[aä]t nicht|handprobe"
    # englisch
    r"|verified|measured|proven|red before green|failed before|was red"
    r"|counter-?check|(^|\n)\s*-?\s*red:",
    re.I)


def genannt(text: str) -> bool:
    """Nennt dieser Text einen Beleg -- oder sagt er ehrlich, dass keiner da ist?"""
    return bool(BELEG.search(text or ""))


def _selftest() -> int:
    # Beide Richtungen, jede Form aus einer echten Commit-Nachricht.
    for satz in ("Beleg rot vor gruen: Test war vorher rot",
                 "Rot gegen 858c82c4: fand 0 statt 1",
                 "Abnahme gefahren, Push wurde abgewiesen",
                 "gemessen ueber 117 Anfragen",
                 "Gemessen ueber 1 204 Commits seit dem 2026-08-01",
                 "Selbsttest 7 Faelle, darunter drei Negativfaelle",
                 "126 passed, 1 skipped",
                 "377 XCTest-Faelle gruen",
                 "Tests gruen, aber sie deckten den Fehler nicht ab",
                 "geaendert, nicht verifiziert",
                 "im Kopflauf belegt, am Geraet nicht",
                 "Verified: focused pytest set -- 17 passed",
                 "- Red: 1 failed because the property was absent"):
        assert genannt(satz), satz

    # DIE VERNEINUNG DARF NICHT ALS BELEG ZAEHLEN -- die Vorgaengerlisten
    # trafen `beleg`/`gemessen` als Teilzeichenkette und zaehlten damit das
    # Gegenteil des Belegs.
    assert not genannt("Die Wirkung ist ungemessen geblieben.")
    assert not genannt("Fuenf Commits sind unbelegt.")
    # `Gegenbeleg` dagegen IST einer und steht eigens in der Liste.
    assert genannt("Gegenbeleg desselben Tages: der Waechter fing es.")
    # Seit 2026-08-20: die Kontrollbegriffe, die dieses Haus taeglich
    # benutzt und die vorher fehlten. Aufgefallen an einem eigenen Commit,
    # der "Positivkontrolle bestanden" schrieb und beanstandet wurde.
    for satz in _NEUE_BELEGFORMEN:
        assert genannt(satz), satz
    for satz in _KEIN_BELEG_TROTZ_AEHNLICHER_WOERTER:
        assert not genannt(satz), satz

    # SCHWEIGEN zaehlt nicht -- ohne diese Faelle waere die Liste so weit,
    # dass sie jede Nachricht durchlaesst.
    for satz in ("Aufraeumen und Umbenennen von zwei Funktionen",
                 "Farbe von red auf blau geaendert",
                 "Kleinigkeit am Regex",
                 ""):
        assert not genannt(satz), satz

    print("belegsprache: Selbsttest gruen (13 Belegformen in zwei Sprachen "
          "und beiden Richtungen, Verneinung zaehlt NICHT als Beleg, "
          "4 Faelle Schweigen bleiben stumm)")
    return 0


# Faelle, die die Liste vor dem 2026-08-20 NICHT erkannte -- als
# Zusicherung, nicht als Kommentar.
_NEUE_BELEGFORMEN = (
    "Positivkontrolle bestanden: treffer_heute [15, 35]",
    "Negativkontrolle mitgebaut, damit aus dem zu engen kein zu weiter wird",
    "Nulllinie erhoben, 247 von 1275",
    "Stichprobe von Hand angesehen, 10 von 10 echt",
)
_KEIN_BELEG_TROTZ_AEHNLICHER_WOERTER = (
    "Kontrolle ueber das Projekt zurueckgewonnen",
    "Die Linie im Diagramm faellt ab",
)


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else 0)
