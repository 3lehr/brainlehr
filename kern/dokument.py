#!/usr/bin/env python3
"""Der Baustein-Vertrag, abgebildet auf ein CRDT-Dokument.

Schritt 4 aus `docs/PLAN_DOKUMENTDIENST_2026-08-14.md`. `kern/baustein.py`
sagt, WAS ein Dokument ist -- diese Datei sagt, wie es im gemeinsamen Dokument
liegt, damit zwei Teilnehmer dasselbe sehen.

WARUM ES ZWEI DATEIEN SIND: Der Vertrag muss ohne `pycrdt` laufen. Sonst
haengt die Frage "was ist eine gueltige Anmerkung" an einer Abhaengigkeit, und
ein Werkzeug, das nur pruefen will, muesste die halbe Transportschicht laden.
Dieselbe Trennung wie bei `kern/teilnehmer.py`, wo `pruefe()` ohne pycrdt
auskommt.

ANMERKUNGEN LIEGEN IM SELBEN DOKUMENT WIE DIE BAUSTEINE. Das ist die
eigentliche Entscheidung dieser Datei, und sie ist keine Bequemlichkeit: ein
zweiter Kanal fuer Anmerkungen wuerde bei jedem Verbindungsabriss zulassen,
dass Dokument und Anmerkung verschieden weit sind -- und dann zeigt ein
Auftrag auf einen Baustein, den es in dieser Fassung noch nicht oder nicht
mehr gibt. Im selben Dokument ist das ausgeschlossen: beides kommt in
derselben Uebertragung oder gar nicht.

DER ANKER LOEST UEBER DIE KENNUNG AUF, NIE UEBER DEN TEXT. Findet die Kennung
nichts, ist die Anmerkung VERWAIST und wird als solche gemeldet. Der Suchtext
ist fuer den Menschen da, der wiedererkennen will, worum es ging -- nicht fuer
das Programm, das zuordnet. Eine Anmerkung, die an eine aehnliche Stelle
wandert, ist schlimmer als eine, die sichtbar ins Leere zeigt: die erste sieht
richtig aus.

Aufruf:  python3 kern/dokument.py --selftest
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from baustein import (  # noqa: E402
    UEBERGAENGE,
    Anker,
    Anmerkung,
    Baustein,
    VertragsFehler,
    neue_kennung,
)

BAUSTEINE = "bausteine"
ANMERKUNGEN = "anmerkungen"


def leeres_dokument(kennung: int | None = None):
    """Ein Dokument mit beiden Listen -- und einer tragbaren Teilnehmerkennung."""
    from pycrdt import Array, Doc

    from teilnehmer import neue_kennung as neue_teilnehmerkennung, pruefe

    doc = Doc(client_id=pruefe(kennung) if kennung is not None else neue_teilnehmerkennung())
    doc[BAUSTEINE] = Array()
    doc[ANMERKUNGEN] = Array()
    return doc


def _liste(doc, name):
    from pycrdt import Array

    return doc.get(name, type=Array)


def baustein_anhaengen(doc, typ: str, text: str = "", feldname: str | None = None) -> str:
    """Legt einen Baustein an und gibt seine Kennung zurueck -- nicht True."""
    from pycrdt import Map

    b = Baustein(kennung=neue_kennung(), typ=typ, text=text, feldname=feldname)
    _liste(doc, BAUSTEINE).append(Map(b.als_dict()))
    return b.kennung


def bausteine(doc) -> list[Baustein]:
    aus = []
    for eintrag in _liste(doc, BAUSTEINE).to_py():
        aus.append(Baustein(**eintrag))
    return aus


def anmerkung_setzen(doc, anker: Anker, text: str, klasse: str, von_wem: str) -> str:
    """Haengt einen Auftrag an eine Stelle. Gibt die Kennung der Anmerkung zurueck.

    Der Anker wird NICHT gegen den Bestand geprueft: eine Anmerkung auf einen
    Baustein, den es (noch) nicht gibt, ist erlaubt und wird als verwaist
    gemeldet. Waere sie verboten, muesste der Setzende den Bestand kennen -- und
    bei zwei gleichzeitigen Teilnehmern kennt ihn niemand vollstaendig.
    """
    from pycrdt import Map

    a = Anmerkung(
        kennung=neue_kennung(), anker=anker, text=text, klasse=klasse, von_wem=von_wem
    )
    d = a.als_dict()
    d.pop("darf_automatisch", None)   # abgeleitet, wird nicht gespeichert
    _liste(doc, ANMERKUNGEN).append(Map(d))
    return a.kennung


def anmerkungen(doc) -> list[Anmerkung]:
    aus = []
    for eintrag in _liste(doc, ANMERKUNGEN).to_py():
        roh = dict(eintrag)
        roh["anker"] = Anker(**roh["anker"])
        roh["verlauf"] = list(roh.get("verlauf") or [])
        aus.append(Anmerkung(**roh))
    return aus


def _finde(doc, kennung: str):
    liste = _liste(doc, ANMERKUNGEN)
    for i, eintrag in enumerate(liste.to_py()):
        if eintrag["kennung"] == kennung:
            return i, eintrag
    return None, None


def zustand_setzen(doc, kennung: str, neuer: str) -> str:
    """Setzt den Zustand und gibt den ERREICHTEN zurueck, nie eine Bestaetigung.

    Der Uebergang wird ueber `baustein.Anmerkung.wechsle` geprueft -- also
    gegen dieselbe Tabelle, gegen die auch ein Werkzeug ohne CRDT prueft.
    """
    i, eintrag = _finde(doc, kennung)
    if eintrag is None:
        raise VertragsFehler(f"keine Anmerkung mit Kennung {kennung!r}")
    roh = dict(eintrag)
    roh["anker"] = Anker(**roh["anker"])
    roh["verlauf"] = list(roh.get("verlauf") or [])
    a = Anmerkung(**roh)
    erreicht = a.wechsle(neuer)

    eintrag_map = _liste(doc, ANMERKUNGEN)[i]
    eintrag_map["zustand"] = erreicht
    eintrag_map["verlauf"] = a.verlauf
    return erreicht


def verwaiste(doc) -> list[Anmerkung]:
    """Anmerkungen, deren Baustein es nicht (mehr) gibt -- sichtbar, nicht still."""
    vorhanden = {b.kennung for b in bausteine(doc)}
    return [a for a in anmerkungen(doc) if a.anker.baustein not in vorhanden]


def _selftest() -> int:
    try:
        from pycrdt import Doc, Text  # noqa: F401
    except ImportError:
        print("dokument: uebersprungen -- pycrdt fehlt (siehe requirements.txt)")
        return 0

    from teilnehmer import KennungsFehler

    doc = leeres_dokument()
    erster = baustein_anhaengen(doc, "absatz", "Erster Satz.")
    mitte = baustein_anhaengen(doc, "grafik", "Abbildung 1")
    letzter = baustein_anhaengen(doc, "feld", "", feldname="rechnungsnummer")
    assert [b.typ for b in bausteine(doc)] == ["absatz", "grafik", "feld"]

    # Grenzwerte: erster, letzter, und einer, den es nie gab.
    a1 = anmerkung_setzen(doc, Anker(baustein=erster, suchtext="Erster Satz."),
                          "Tippfehler im ersten Wort.", "tippfehler", "mensch")
    a2 = anmerkung_setzen(doc, Anker(baustein=letzter),
                          "Feldname passt nicht.", "inhalt", "modell")
    a3 = anmerkung_setzen(doc, Anker(baustein="000000000000"),
                          "zeigt ins Leere", "darstellung", "mensch")
    assert len(anmerkungen(doc)) == 3
    assert [a.kennung for a in verwaiste(doc)] == [a3], "nur die dritte zeigt ins Leere"

    # Die Klasse entscheidet, ob selbstaendige Umsetzung ERLAUBT waere.
    nach_kennung = {a.kennung: a for a in anmerkungen(doc)}
    assert nach_kennung[a1].darf_automatisch is True      # tippfehler
    assert nach_kennung[a2].darf_automatisch is False     # inhalt

    # Zustand: der erreichte kommt zurueck, und er steht danach im Dokument.
    assert zustand_setzen(doc, a1, "umgesetzt") == "umgesetzt"
    assert {a.kennung: a.zustand for a in anmerkungen(doc)}[a1] == "umgesetzt"
    assert {a.kennung: a.verlauf for a in anmerkungen(doc)}[a1] == ["offen->umgesetzt"]
    try:
        zustand_setzen(doc, a2, "abgenommen")            # Sprung ueber einen Schritt
    except VertragsFehler:
        pass
    else:
        raise AssertionError("offen -> abgenommen haette fallen muessen")
    try:
        zustand_setzen(doc, "ffffffffffff", "umgesetzt")  # gibt es nicht
    except VertragsFehler:
        pass
    else:
        raise AssertionError("unbekannte Anmerkung haette fallen muessen")
    assert "abgenommen" not in UEBERGAENGE["offen"], "Vertrag hat sich geaendert"

    # Der Kern der Sache: ZWEI Teilnehmer, und der zweite sieht Baustein UND
    # Anmerkung samt Zustand -- in derselben Uebertragung.
    from teilnehmer import neue_kennung as neue_teilnehmerkennung

    zweiter_doc = leeres_dokument(neue_teilnehmerkennung())
    zweiter_doc.apply_update(doc.get_update())
    assert [b.kennung for b in bausteine(zweiter_doc)] == [erster, mitte, letzter]
    drueben = {a.kennung: a for a in anmerkungen(zweiter_doc)}
    assert drueben[a1].zustand == "umgesetzt"
    assert drueben[a1].anker.baustein == erster
    assert [a.kennung for a in verwaiste(zweiter_doc)] == [a3]

    # Negativfall zum Verwaisen, und er ist der eigentliche Beleg: ein zweiter
    # Baustein mit GLEICHEM Text darf die Anmerkung nicht einfangen, wenn ihr
    # eigener geloescht wird.
    doppelter_text = baustein_anhaengen(doc, "absatz", "Erster Satz.")
    assert doppelter_text != erster
    liste = _liste(doc, BAUSTEINE)
    for i, b in enumerate(liste.to_py()):
        if b["kennung"] == erster:
            del liste[i]
            break
    verwaist_jetzt = {a.kennung for a in verwaiste(doc)}
    assert a1 in verwaist_jetzt, "Anmerkung muss verwaisen statt auf den gleichen Text zu springen"
    assert a2 not in verwaist_jetzt

    # Die Teilnehmerkennung bleibt unter der Schranke -- auch hier.
    try:
        leeres_dokument(2**32)
    except KennungsFehler:
        pass
    else:
        raise AssertionError("Kennung ueber 2^32-1 haette fallen muessen")

    print("dokument: Selbsttest bestanden")
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
