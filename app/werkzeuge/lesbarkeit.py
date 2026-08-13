#!/usr/bin/env python3
"""lesbarkeit.py -- wie viele Felder traegt ein Bildschirm, ohne dass jemand aufsteht.

ANLASS (Betreiber, 2026-08-13): "1,5 meter aber grosser 4k Fernseher als
zweitmonitor" -- und, wichtiger: "die app muss alle scenarien tragen nicht nur
das morgige!"

DER FEHLER, GEGEN DEN DIESE DATEI GEBAUT IST -- und es war meiner: Ich hatte
die Bauform der App an EINEM Termin gemessen (ein eingebauter Bildschirm,
346 mm breit, 2 m Abstand) und daraus geschlossen, ein Raster sei "arithmetisch
ausgeschlossen". Das Ergebnis stimmte fuer diesen einen Fall und war als
Aussage ueber die App falsch. Eine Zahl, die aus genau einem Szenario stammt,
gehoert nicht in eine Bauformentscheidung -- sie gehoert in eine Funktion, die
man mit dem naechsten Szenario erneut aufruft.

Darum steht hier kein Ergebnis, sondern die Rechnung. Wer eine neue Lage hat
(anderer Schirm, anderer Abstand, andere Dokumente), ruft sie auf, statt eine
Doku zu suchen, in der eine alte Zahl steht.

GEMESSEN, nicht geschaetzt (2026-08-13, 29 Quellen-PDFs aus buckeberg):
  Fliesstextgroesse   Median 10,9 pt   Spanne 6,8 - 30,0
  x-Hoehe je Punkt    Median 0,547     (an gerenderten Glyphen vermessen)
  Seitenformat        26 von 29 sind A4

MODELLWISSEN, ausdruecklich gekennzeichnet: Fluessiges Lesen setzt eine x-Hoehe
von etwa 0,2 Sehwinkelgrad voraus (kritische Schriftgroesse). Das stammt aus
meinem Wissen, nicht aus einer Messung an diesen Menschen. Deshalb ist die
Schwelle ein PARAMETER und keine Konstante im Rechenweg -- und deshalb gibt
--tabelle sie in drei Stufen aus, damit sichtbar bleibt, wie stark das Ergebnis
daran haengt.

Aufruf:
    python3 app/werkzeuge/lesbarkeit.py --diagonale 65 --abstand 1500
    python3 app/werkzeuge/lesbarkeit.py --tabelle
    python3 app/werkzeuge/lesbarkeit.py --selftest
"""

from __future__ import annotations

import argparse
import math
import sys

# --- gemessene Eigenschaften des Bestands ---------------------------------
FLIESSTEXT_PT = 10.9          # Median ueber 29 Quellen-PDFs
X_HOEHE_ANTEIL = 0.547        # x-Hoehe je Punktgroesse, Median
PT_IN_MM = 25.4 / 72.0
A4_BREITE_MM, A4_HOEHE_MM = 210.0, 297.0

# --- Modellwissen, bewusst als Parameter ----------------------------------
SCHWELLE_FLUESSIG = 0.20      # Grad Sehwinkel, fluessiges Lesen
SCHWELLE_KNAPP = 0.14
SCHWELLE_ENTZIFFERN = 0.10


def noetige_x_hoehe_mm(abstand_mm: float, schwelle_grad: float = SCHWELLE_FLUESSIG) -> float:
    """Wie gross muss die x-Hoehe auf dem Schirm sein, damit man sie liest."""
    return abstand_mm * math.tan(math.radians(schwelle_grad))


def vergroesserung(abstand_mm: float, pt: float = FLIESSTEXT_PT,
                   x_anteil: float = X_HOEHE_ANTEIL,
                   schwelle_grad: float = SCHWELLE_FLUESSIG) -> float:
    """Faktor, um den eine Seite ueber ihre Originalgroesse hinaus muss."""
    vorhanden = pt * x_anteil * PT_IN_MM
    if vorhanden <= 0:
        raise ValueError("Schriftgroesse muss groesser als null sein")
    return noetige_x_hoehe_mm(abstand_mm, schwelle_grad) / vorhanden


def schirm_mm(diagonale_zoll: float, breit: int = 16, hoch: int = 9) -> tuple[float, float]:
    """Breite und Hoehe in mm aus Diagonale und Seitenverhaeltnis."""
    d = diagonale_zoll * 25.4
    norm = math.hypot(breit, hoch)
    return d * breit / norm, d * hoch / norm


def felder(diagonale_zoll: float, abstand_mm: float, breit: int = 16, hoch: int = 9,
           schwelle_grad: float = SCHWELLE_FLUESSIG) -> dict:
    """Wie viele A4-Seiten passen lesbar nebeneinander und uebereinander.

    Ganze Felder, nicht Flaechenanteile: ein halbes Feld traegt keine halbe
    Seite, es traegt gar keine. Wer die Flaeche teilt statt die Felder zu
    zaehlen, bekommt "2,7 Felder" und baut daraus drei.
    """
    f = vergroesserung(abstand_mm, schwelle_grad=schwelle_grad)
    seite_b, seite_h = A4_BREITE_MM * f, A4_HOEHE_MM * f
    s_b, s_h = schirm_mm(diagonale_zoll, breit, hoch)
    spalten, zeilen = int(s_b // seite_b), int(s_h // seite_h)
    return {
        "diagonale_zoll": diagonale_zoll,
        "abstand_mm": abstand_mm,
        "schwelle_grad": schwelle_grad,
        "schirm_mm": (round(s_b), round(s_h)),
        "vergroesserung": round(f, 2),
        "seite_mm": (round(seite_b), round(seite_h)),
        "spalten": spalten,
        "zeilen": zeilen,
        "felder": spalten * zeilen,
        # Quer gelegt passt oft eine Seite mehr -- und ein Vertrag laesst sich
        # querformatig genauso lesen, nur mit mehr Scrollen.
        "felder_quer": int(s_b // seite_h) * int(s_h // seite_b),
    }


def _zeile(e: dict) -> str:
    return (f"  {e['diagonale_zoll']:>5.0f}\"  {e['abstand_mm']/1000:>4.1f} m   "
            f"{e['schirm_mm'][0]:>5}x{e['schirm_mm'][1]:<5}  Faktor {e['vergroesserung']:>5.2f}  "
            f"Seite {e['seite_mm'][0]:>4}x{e['seite_mm'][1]:<4}  "
            f"{e['spalten']}x{e['zeilen']} = {e['felder']:>2} Felder")


def tabelle() -> str:
    zeilen = ["Wie viele A4-Seiten traegt ein Schirm im Fliesstext (Median 10,9 pt)?",
              "Modellwissen-Schwelle in drei Stufen -- sie ist der unsicherste Teil.", ""]
    for name, schwelle in (("fluessig lesen", SCHWELLE_FLUESSIG),
                           ("knapp", SCHWELLE_KNAPP),
                           ("nur entziffern", SCHWELLE_ENTZIFFERN)):
        zeilen.append(f"[{name}, {schwelle}°]")
        for diag, abst in ((14, 1500), (14, 2000), (43, 1500), (55, 1500),
                           (65, 1500), (75, 1500), (85, 1500), (65, 2500)):
            zeilen.append(_zeile(felder(diag, abst, schwelle_grad=schwelle)))
        zeilen.append("")
    return "\n".join(zeilen)


def _selftest() -> int:
    # Naeher heisst kleiner: die noetige x-Hoehe waechst mit dem Abstand.
    assert noetige_x_hoehe_mm(1500) < noetige_x_hoehe_mm(2000)
    # Und sie ist proportional -- der halbe Abstand, die halbe Hoehe.
    assert abs(noetige_x_hoehe_mm(2000) / noetige_x_hoehe_mm(1000) - 2.0) < 1e-9

    # Ein groesserer Schirm traegt nie weniger Felder.
    for a in (1200, 1500, 2000):
        werte = [felder(d, a)["felder"] for d in (14, 32, 55, 65, 85)]
        assert werte == sorted(werte), f"nicht monoton bei {a} mm: {werte}"
    # Und ein groesserer Abstand nie mehr.
    werte = [felder(65, a)["felder"] for a in (1000, 1500, 2000, 3000)]
    assert werte == sorted(werte, reverse=True), werte

    # Seitenverhaeltnis: 16:9 bei 65 Zoll ist rund 1440 mm breit.
    b, h = schirm_mm(65)
    assert 1430 < b < 1450 and 800 < h < 820, (b, h)
    assert abs(math.hypot(b, h) - 65 * 25.4) < 1e-6

    # Der Fall, der die Regel begruendet hat: eingebauter Schirm, 2 m,
    # traegt keine einzige Seite -- und derselbe Rechenweg sagt fuer einen
    # grossen Fernseher etwas anderes. Genau das war der Fehler.
    assert felder(14, 2000)["felder"] == 0
    assert felder(65, 1500)["felder"] >= 1

    # Negativfall: unsinnige Eingabe wird abgelehnt, nicht gerundet.
    try:
        vergroesserung(1500, pt=0)
    except ValueError:
        pass
    else:
        raise AssertionError("Schriftgroesse 0 muss abgelehnt werden")

    # Grenzwert: Abstand 0 heisst Faktor 0 -- keine Ausnahme, aber auch keine
    # Aussage. Wer damit rechnet, bekommt sehr viele Felder und merkt es.
    assert vergroesserung(0) == 0.0

    print("lesbarkeit: Selbsttest bestanden")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--diagonale", type=float, help="Bildschirmdiagonale in Zoll")
    p.add_argument("--abstand", type=float, default=1500, help="Betrachtungsabstand in mm")
    p.add_argument("--verhaeltnis", default="16:9")
    p.add_argument("--schwelle", type=float, default=SCHWELLE_FLUESSIG,
                   help=f"Sehwinkel in Grad (Vorgabe {SCHWELLE_FLUESSIG}, Modellwissen)")
    p.add_argument("--tabelle", action="store_true")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        return _selftest()
    if a.tabelle or not a.diagonale:
        print(tabelle())
        return 0
    b, h = (int(x) for x in a.verhaeltnis.split(":"))
    e = felder(a.diagonale, a.abstand, b, h, a.schwelle)
    print(_zeile(e))
    print(f"  quer gelegt: {e['felder_quer']} Felder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
