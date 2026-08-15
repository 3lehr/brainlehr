#!/usr/bin/env python3
"""F6 im Gesamtplan, EIN Modul fuer beide Haelften: die schnelle Darstellung
UND der Waechter, der sie gegen das gesetzte Blatt prueft.

TEIL 1 -- SCHNELLE DARSTELLUNG (`vorschau_text`/`vorschau_segmente`): reiner
Text aus `dokument.bausteine_baum`, OHNE lualatex. Ein voller Satzlauf
(`kern/satz.py` -> lualatex) dauert gemessen 1,1 s (kalt 1,20 s, warm 1,12 s)
-- zu langsam zum Tippen. Diese Darstellung ist die zweite, schnelle Ansicht:
kein Aufruf von lualatex, keine LaTeX-Maskierung (die betrifft nur den
Satzweg -- ein "&" bleibt hier "&", nicht "\\&").

TEIL 2 -- DRIFT-WAECHTER (`pruefe_drift`): prueft die Darstellung aus Teil 1
gegen das GESETZTE BLATT (`kern/satz.py` -> lualatex).

DRITTES PAAR, keine Ersatzpruefung: `kern/satzwache.py` prueft bereits ein
Paar (Baustein-QUELLE gegen Blatt, drei Eigenschaften Vollstaendigkeit/Treue/
Konformitaet) -- NUR GELESEN, nicht dupliziert. Dieser Waechter prueft ein
ANDERES Paar: die schnelle Darstellung gegen dasselbe Blatt. Beide Seiten
entstehen aus demselben Baustein-Baum (ADR-019), darum ist jede Abweichung ein
Fehler in einer der beiden ABLEITUNGEN -- nie ein legitimer inhaltlicher
Unterschied. AUSSEHEN darf abweichen (die Darstellung ist kein LaTeX-Satz),
INHALT nicht.

RICHTUNG -- ENTSCHEIDUNG: beidseitig, aus zwei getrennten Gruenden gemeldet:
  NUR_IN_DARSTELLUNG (vom Plan verlangt): die Darstellung zeigt Text, der im
  Blatt nicht vorkommt -- ein Nutzer tippt/liest etwas, das nie gedruckt wird
  oder anders gedruckt wird. Der Auftragsfall.
  NUR_IM_BLATT (Gegenrichtung, geprueft und fuer gleich schwer befunden):
  der wahre Baustein-Text steht im Blatt, aber die Darstellung zeigt ihn nicht
  (z.B. eine veraltete, gecachte Fassung). Ein Nutzer, der nach der schnellen
  Darstellung abnimmt, hat dann einen Blattinhalt nie gesehen. Dieselbe
  Fehlerklasse mit vertauschten Rollen -- beide fallen den Waechter.

WAS DIESER WAECHTER NICHT PRUEFT (Abgrenzung zu kern/satzwache.py, um nichts
zu doppeln):
  - Ob ein Baustein VOLLSTAENDIG im Blatt vorkommt (Label je Kennung) --
    das ist satzwache.pruefe_vollstaendigkeit, unabhaengig von der Darstellung.
  - Ob der Baustein-TEXT (die Quelle) im Blatt vorkommt -- das ist
    satzwache.pruefe_treue. Dieser Waechter vergleicht die DARSTELLUNG, nicht
    die Quelle direkt (auch wenn beide aus demselben Baum kommen: die
    Darstellung ist eine eigene Ableitung mit eigenem Fehlerpotential).
  - PDF/A-3, PDF/UA -- satzwache.pruefe_konformitaet.
  - Was der Satz WEGLAESST (fehlender Alternativtext, leere Ueberschrift) --
    das ist eine QUALITAETSPRUEFUNG am Blatt selbst, keine Drift zwischen zwei
    ANSICHTEN, und gehoert (falls gewuenscht) in eine eigene Satzwache-Regel,
    nicht hierher.

MASKIERUNG IST KEINE DRIFT: `kern/satz.py` maskiert Sonderzeichen fuer LaTeX
("&" -> "\\&"), lualatex setzt sie, `pdftotext` liest sie zurueck als
Klartext-Zeichen. Verglichen wird daher IMMER gegen den GERENDERTEN, per
`kern.satzwache.pdf_text` gelesenen Blatt-Text -- nie gegen die rohe
LaTeX-Quelle. Ein Vergleich gegen die Quelle waere die Falle, vor der die
Aufgabenstellung ausdruecklich warnt: "\\&" enthaelt "&" nicht als Teilstring
der Darstellung, waere also faelschlich "fehlend".

Aufruf:  python3 kern/driftwaechter.py --selftest
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from baustein import Baustein, baumreihenfolge  # noqa: E402
from dokument import bausteine, bausteine_baum  # noqa: E402
from satzwache import _normalisiere  # noqa: E402


# --- Teil 1: schnelle Darstellung -------------------------------------------

def vorschau_segmente(doc) -> dict[str, str]:
    """Ein Textsegment je Baustein, Kennung -> Text, in Baumreihenfolge
    (Iterationsreihenfolge von dict bleibt Einfuegereihenfolge, Python >=3.7).
    Rohtext -- keine Maskierung, das ist Sache von `kern.satz.maskiere`."""
    segmente: dict[str, str] = {}
    for b in bausteine_baum(doc):
        if b.typ == "feld":
            segmente[b.kennung] = f"{b.feldname or ''}: {b.text}"
        else:
            segmente[b.kennung] = b.text
    return segmente


def vorschau_text(doc) -> str:
    """Der volle Anzeigetext, Segmente in Baumreihenfolge, leere ausgelassen."""
    return "\n\n".join(t for t in vorschau_segmente(doc).values() if t)


# --- Teil 2: Drift-Waechter --------------------------------------------------

@dataclass
class DriftBericht:
    nur_in_darstellung: list[str] = field(default_factory=list)
    nur_im_blatt: list[str] = field(default_factory=list)

    def bestanden(self) -> bool:
        return not self.nur_in_darstellung and not self.nur_im_blatt


def _vergleiche(geordnet: list[Baustein], segmente: dict[str, str], blatt_text: str) -> DriftBericht:
    """Der reine Vergleich, ohne PDF-Erzeugung -- testbar ohne lualatex.
    `segmente` und `blatt_text` sind Parameter statt intern erzeugt, damit die
    Rot-Probe unten mit fabrizierten Werten arbeiten kann."""
    norm_blatt = _normalisiere(blatt_text)
    bericht = DriftBericht()
    for b in geordnet:
        segment_norm = _normalisiere(segmente.get(b.kennung, ""))
        wahr_norm = _normalisiere(b.text)

        if segment_norm and segment_norm not in norm_blatt:
            bericht.nur_in_darstellung.append(b.kennung)

        # Gegenrichtung nur gemeldet, wenn der wahre Text wirklich im Blatt
        # steht -- sonst waere es ein Vollstaendigkeitsfehler von satzwache.py
        # (Baustein fehlt im Satz ueberhaupt), keine Drift zwischen den zwei
        # ANSICHTEN, die dieser Waechter vergleicht.
        if wahr_norm and wahr_norm in norm_blatt and wahr_norm not in segment_norm:
            bericht.nur_im_blatt.append(b.kennung)
    return bericht


def pruefe_drift(doc, blatt_text: str) -> DriftBericht:
    """Vergleicht `vorschau_segmente(doc)` gegen den bereits GERENDERTEN
    Blatt-Text (z.B. von `kern.satzwache.pdf_text`). Erzeugt selbst kein PDF --
    das bleibt bei satzwache.satz_lauf, um lualatex nicht doppelt einzubinden."""
    return _vergleiche(baumreihenfolge(bausteine(doc)), vorschau_segmente(doc), blatt_text)


def _selftest() -> int:
    from dokument import baustein_anhaengen, leeres_dokument

    # --- Grenzwerte fuer Teil 1 (Darstellung) -------------------------------
    doc0 = leeres_dokument()
    assert vorschau_segmente(doc0) == {}
    assert vorschau_text(doc0) == ""
    k1 = baustein_anhaengen(doc0, "absatz", "Erster Satz.")
    assert vorschau_segmente(doc0) == {k1: "Erster Satz."}
    k2 = baustein_anhaengen(doc0, "feld", "42,00", feldname="betrag")
    assert vorschau_segmente(doc0)[k2] == "betrag: 42,00"
    doc0b = leeres_dokument()
    k3 = baustein_anhaengen(doc0b, "absatz", "Preis: 5 & 10 % Rabatt, #1_2^3")
    assert vorschau_segmente(doc0b)[k3] == "Preis: 5 & 10 % Rabatt, #1_2^3"  # roh, unmaskiert

    # --- Positivkontrolle je Fehlerklasse: ein Fall, der SICHER anschlaegt --

    # 1) NUR_IN_DARSTELLUNG: die Darstellung zeigt einen Text, den das Blatt
    #    nicht enthaelt (simuliert eine erfundene/veraltete Darstellung).
    b_alt = Baustein(kennung="a" * 12, typ="absatz", text="Preis 100 Euro")
    segmente_drift = {b_alt.kennung: "Preis 999 Euro"}
    blatt_ohne_999 = "Rechnung. Preis 100 Euro. Ende."
    bericht = _vergleiche([b_alt], segmente_drift, blatt_ohne_999)
    assert bericht.nur_in_darstellung == [b_alt.kennung], bericht
    assert not bericht.bestanden()

    # 2) NUR_IM_BLATT: das Blatt enthaelt den wahren Text, die Darstellung
    #    zeigt eine veraltete Fassung (Cache-Fall).
    segmente_veraltet = {b_alt.kennung: "Preis (wird geladen...)"}
    blatt_korrekt = "Rechnung. Preis 100 Euro. Ende."
    bericht2 = _vergleiche([b_alt], segmente_veraltet, blatt_korrekt)
    assert bericht2.nur_im_blatt == [b_alt.kennung], bericht2
    assert not bericht2.bestanden()

    # Rot-vor-gruen, dokumentiert: VOR diesem Modul gab es keine Pruefung fuer
    # dieses Paar (Darstellung/Blatt) -- kern/satzwache.py prueft nur
    # Quelle/Blatt (siehe dessen Modulkopf), eine eigene Darstellung existierte
    # gar nicht. Die zwei Faelle oben waeren also bis zu diesem Modul still
    # durchgelaufen; die Assertions oben zeigen, dass sie JETZT anschlagen.

    # --- Gegenprobe: identische Aussage in beiden Formen meldet NICHTS -----
    doc = leeres_dokument()
    baustein_anhaengen(doc, "absatz", "Erster Satz.")
    baustein_anhaengen(doc, "feld", "42,00", feldname="betrag")
    blatt_ok = "Vorspann. Erster Satz. betrag: 42,00 Nachspann."
    assert pruefe_drift(doc, blatt_ok).bestanden()

    # --- Grenzwerte fuer Teil 2 (Waechter) ----------------------------------

    # Leeres Dokument -> nichts zu vergleichen, besteht trivial.
    assert pruefe_drift(leeres_dokument(), "Vorspann. Nachspann.").bestanden()

    # Verschachtelte Bausteine: Kind-Drift wird ueber die eigene Kennung
    # erkannt, das unbeteiligte Elternteil bleibt sauber.
    doc_baum = leeres_dokument()
    wurzel = baustein_anhaengen(doc_baum, "ueberschrift", "Abschnitt 1")
    kind = baustein_anhaengen(doc_baum, "absatz", "Unterpunkt", eltern=wurzel)
    segmente_baum = vorschau_segmente(doc_baum)
    segmente_baum[kind] = "FALSCHER TEXT"
    geordnet = baumreihenfolge(bausteine(doc_baum))
    bericht_baum = _vergleiche(geordnet, segmente_baum, "Abschnitt 1. Unterpunkt.")
    assert bericht_baum.nur_in_darstellung == [kind], bericht_baum
    assert wurzel not in bericht_baum.nur_in_darstellung

    # Sonderzeichen: die Maskierung im Blatt ("&" -> "\&" -> lualatex ->
    # pdftotext -> "&") ist KEINE Drift. Simuliert hier durch einen
    # Blatt-Text, der bereits die GERENDERTE (nicht die maskierte) Form
    # traegt -- so wuerde pdftotext ihn tatsaechlich liefern.
    doc_sz = leeres_dokument()
    baustein_anhaengen(doc_sz, "absatz", "Preis: 5 & 10 % Rabatt")
    blatt_sz = "Vorspann. Preis: 5 & 10 % Rabatt. Nachspann."
    assert pruefe_drift(doc_sz, blatt_sz).bestanden()
    # Naiver Vergleich gegen die MASKIERTE Quelle waere hier faelschlich rot
    # (siehe Modulkopf) -- gegen den echten satz.py-Weg zusaetzlich unten
    # geprueft, wenn lualatex verfuegbar ist.

    print("driftwaechter: reine Proben (Darstellung + Vergleich) bestanden")

    # --- Integrationsprobe mit echtem Satzweg, nur wenn lualatex/pdftotext da --
    import shutil
    if not shutil.which("lualatex") or not shutil.which("pdftotext"):
        print("driftwaechter: Integrationsprobe uebersprungen -- lualatex/pdftotext fehlt")
        print("driftwaechter: Selbsttest bestanden")
        return 0

    from satz import satz_quelle
    from satzwache import pdf_text, satz_lauf

    doc_echt = leeres_dokument()
    baustein_anhaengen(doc_echt, "absatz", "Preis: 5 & 10 % Rabatt, #1_2^3")
    quelle = satz_quelle(doc_echt, "Driftprobe")
    verzeichnis = Path(tempfile.mkdtemp())
    try:
        pdf, grund = satz_lauf(verzeichnis, quelle)
        assert pdf is not None, grund
        text, textgrund = pdf_text(pdf)
        assert not textgrund, textgrund
        bericht_echt = pruefe_drift(doc_echt, text)
        assert bericht_echt.bestanden(), (
            f"Sonderzeichen faelschlich als Drift gemeldet: {bericht_echt}"
        )
    finally:
        shutil.rmtree(verzeichnis, ignore_errors=True)

    print("driftwaechter: Integrationsprobe (echter Satzweg) bestanden")
    print("driftwaechter: Selbsttest bestanden")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        return _selftest()
    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
