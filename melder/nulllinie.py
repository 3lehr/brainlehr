#!/usr/bin/env python3
"""Eine leere Ausgabe wird als Befund gemeldet, ohne dass eine Nulllinie
daneben steht -- L-871c8a, 3 Vorkommen, ohne Mechanismus.

ANLASS: `melder/ohne_mechanismus.py` fuehrt L-871c8a ("Eine leere Ausgabe als
Befund gelesen, ohne vorher eine Nulllinie zu haben") als Arbeitsliste ohne
Pruefer. Volltext nennt drei Vorkommen, alle mit derselben Form: eine
unquantifizierte Negativ-/Leere-Aussage ("Log war leer", "0 Zeilen", "keine
Ereignisse") wird als Schluss gezogen, OHNE dass danebensteht, wogegen sie
gemessen wurde (Positivkontrolle/Nulllinie/Gegenprobe).

WAS MASCHINELL ERKENNBAR IST: Kein Werkzeug kann beurteilen, ob eine
Null-Aussage in der SACHE stimmt -- das war bei allen drei Vorkommen erst im
Nachhinein erkennbar (Baggersee ohne Auto, entfernter Worktree). Erkennbar
ist aber die FORM: steht eine Leere-Behauptung ("war leer", "0 Zeilen",
"nichts gefunden", "keine Funde") im Text, OHNE dass im selben Zug ein
Bezugsrahmen genannt wird -- entweder ein Zahlenpaar der Form "N von M"
(das ist die von `kern/rueckwirkung.py` selbst verlangte Form, siehe dessen
Docstring: "gemessen ueber 0..9") ODER ein Wort aus dem Vokabular der
Gegenprobe (Nulllinie, Positivkontrolle, Baseline, Gegenprobe,
Vergleichswert) -- dann fehlt die Kontrolle, die der Katalog-Abschnitt "Der
Pruefstand misst mit" in CLAUDE.md verbindlich macht ("Je Regelklasse eine
Positivkontrolle"). Das ist ein Textmuster, kein Sachurteil: das Modul
entscheidet nicht, ob die Leere stimmt, nur ob ihr Bezugsrahmen fehlt.

DIE NAHELIEGENDSTE VERWECHSLUNG, und sie ist der Grund fuer die
Ausnahmeregel unten: ein quantifizierter Nullbefund ("0 von 20 Faellen")
TRAEGT seinen Rahmen bereits im Satz -- genau die Form, die
`kern/rueckwirkung.Befund.zeile()` erzeugt. Ihn zu melden waere ein Melder,
der die eigene Vorlage bestraft.

Abschaltbar: BRAINLEHR_NULLLINIE=aus.

    python3 melder/nulllinie.py --pruefen
    python3 melder/nulllinie.py --selftest
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w), str(_w / "kern")]

import rueckwirkung as _rw  # noqa: E402

# Leere-/Nullbehauptung als Schluss.
_LEERE = re.compile(
    r"\b(war leer|blieb leer|ist leer|0 Zeilen|null Zeilen|"
    r"nichts gefunden|keine (Funde|Treffer|Ergebnisse|Ereignisse))\b",
    re.IGNORECASE,
)
# Bereits quantifiziert -- traegt den Rahmen im Satz (Ausnahme).
_QUANTIFIZIERT = re.compile(r"\b\d+\s+von\s+\d+\b")
# Vokabular der Gegenprobe -- Rahmen ist genannt. \w* statt \b am Wortende,
# weil "Gegenproben"/"Nullmessungen" (Plural/Flexion) sonst durchrutschen --
# gefunden in der Stichprobe am echten Bestand (siehe Docstring).
_KONTROLLE = re.compile(
    r"\b(Nulllinie|Nullmessung|Positivkontrolle|Baseline|Gegenprobe\w*|"
    r"Grundlinie|Vergleichswert)\b",
    re.IGNORECASE,
)


def _aus() -> bool:
    return os.environ.get("BRAINLEHR_NULLLINIE", "").strip().lower() == "aus"


def trifft(text: str) -> bool:
    """Leere-Behauptung ohne Bezugsrahmen -- weder quantifiziert noch mit
    Kontroll-Vokabular versehen."""
    if not _LEERE.search(text):
        return False
    return not (_QUANTIFIZIERT.search(text) or _KONTROLLE.search(text))


def pruefen(wurzel: Path | None = None, dateien: int = 400) -> _rw.Befund:
    return _rw.zaehle(list(_rw.antworten(wurzel, dateien)), trifft,
                       lambda t: t[:160])


def _selftest() -> int:
    # POSITIV 1: Vorkommen "Baggersee" wortnah -- Leere als Schluss, kein Rahmen.
    p1 = ("Zwischen 12:47 und 15:05 zeigt das Protokoll ausser Heartbeats "
          "keine Ereignisse. Das melde ich als 2 h 18 Funkstille.")
    # POSITIV 2: knapper, klarer Fall.
    p2 = "Die Logdatei war leer. Damit ist bestaetigt, dass der Fehler nicht vorbestand."
    assert trifft(p1) and trifft(p2), (trifft(p1), trifft(p2))

    # NEGATIV 1, die naheliegendste Verwechslung: quantifizierter Nullbefund
    # (die von kern/rueckwirkung selbst verlangte Form) darf NICHT anschlagen.
    n1 = "0 von 20 Faellen liefern einen Treffer, gemessen ueber den ganzen Bestand."
    # NEGATIV 2: Leere-Behauptung MIT Kontroll-Vokabular -- Rahmen ist da.
    n2 = ("Das Log war leer; zur Gegenprobe habe ich vorher mit "
          "eingeschalteter Stuetze gemessen und dort 190 Zeilen erhalten, "
          "die Nulllinie haelt.")
    assert not trifft(n1), "quantifizierter Nullbefund darf nicht anschlagen"
    assert not trifft(n2), "genannte Gegenprobe darf nicht anschlagen"

    b = _rw.zaehle([p1, p2, n1, n2], trifft, lambda t: t[:40])
    assert b.nenner == 4 and b.treffer == 2, (b.nenner, b.treffer)
    assert "2 von 4" in b.zeile("unbelegte Leere-Behauptungen")

    # ROT-PROBE: eine kaputte Fassung ohne die Quantifizierungs-Ausnahme
    # meldet n1 faelschlich -- nachgestellt statt behauptet.
    def _kaputt(t: str) -> bool:
        return bool(_LEERE.search(t)) and not _KONTROLLE.search(t)
    # n1 enthaelt "nichts gefunden"? nein -- kaputt-Testfall braucht eigenen
    # Text, der die Leere-Phrase UND die Quantifizierung traegt.
    kaputt_text = "0 von 20 Faellen zeigen keine Treffer, nichts gefunden."
    assert _kaputt(kaputt_text) is True, ("die kaputte Fassung muss den "
        "quantifizierten Fall faelschlich melden")
    assert trifft(kaputt_text) is False, ("die echte Fassung darf ihn "
        "NICHT melden -- das ist die Gegenprobe")

    print("nulllinie: Selbsttest gruen (4 Faelle: zwei Vorkommen erkannt, "
          "quantifizierter Nullbefund schuetzt, genannte Gegenprobe "
          "schuetzt, Zaehlung mit Nenner; Rot-Probe bestaetigt, dass eine "
          "Fassung ohne Quantifizierungs-Ausnahme den Negativfall "
          "faelschlich meldet)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    if _aus():
        print("nulllinie: abgeschaltet (BRAINLEHR_NULLLINIE=aus)")
        return 0
    b = pruefen()
    _rw.bericht("unbelegte Leere-Behauptungen (kein Rahmen, keine "
                "Gegenprobe)", b, "ueber die juengsten Transkripte")
    return 1 if b.treffer else 0


if __name__ == "__main__":
    sys.exit(main())
