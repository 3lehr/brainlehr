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
import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from baustein import (  # noqa: E402
    UEBERGAENGE,
    Anker,
    Anmerkung,
    Baustein,
    VertragsFehler,
    baumreihenfolge,
    neue_kennung,
)

BAUSTEINE = "bausteine"
ANMERKUNGEN = "anmerkungen"
META = "meta"
FASSUNGEN = "fassungen"

# ADR-019 Entscheidung 5: Sprache ist ein Feld am Dokument, nicht fest im
# LaTeX-Vorspann verdrahtet. Vorgabe deckungsgleich mit dem bisher fest
# verdrahteten Wert, damit ein Dokument ohne gesetzte Sprache genau das
# heutige Verhalten behaelt.
SPRACHE_VORGABE = "de-DE"


def leeres_dokument(kennung: int | None = None):
    """Ein Dokument mit beiden Listen -- und einer tragbaren Teilnehmerkennung."""
    from pycrdt import Array, Doc, Map

    from teilnehmer import neue_kennung as neue_teilnehmerkennung, pruefe

    doc = Doc(client_id=pruefe(kennung) if kennung is not None else neue_teilnehmerkennung())
    doc[BAUSTEINE] = Array()
    doc[ANMERKUNGEN] = Array()
    # ADR-019 Entscheidung 3: "veroeffentlicht" ist ein ZUSTAND mit Vorgabe
    # "nein", kein abgeleiteter Wert. Entscheidung 5: Sprache gehoert zum
    # Dokument, nicht zum Satzweg.
    doc[META] = Map({
        "sprache": SPRACHE_VORGABE,
        "veroeffentlicht": False,
        "veroeffentlicht_urheber": None,
        "veroeffentlicht_zeitpunkt": None,
    })
    # ADR-019 Entscheidung 4: der veroeffentlichte Stand bleibt rekonstruierbar.
    # Billigste Bauform: eine Kopie je Veroeffentlichung, keine volle
    # Versionierung (siehe `veroeffentlichen`).
    doc[FASSUNGEN] = Array()
    return doc


def _liste(doc, name):
    from pycrdt import Array

    return doc.get(name, type=Array)


def _liste_map(doc, name):
    from pycrdt import Map

    return doc.get(name, type=Map)


def baustein_anhaengen(doc, typ: str, text: str = "", feldname: str | None = None,
                       eltern: str | None = None, alt: str = "") -> str:
    """Legt einen Baustein an und gibt seine Kennung zurueck -- nicht True.

    `eltern` wird NICHT gegen den Bestand geprueft -- dieselbe Haltung wie bei
    `anmerkung_setzen`: ein Eltern-Baustein, der (noch) nicht existiert, ist
    erlaubt und wird beim Lesen als Wurzel behandelt (siehe
    `baustein.baumreihenfolge`). `rang` wird automatisch ans Ende der
    bestehenden Geschwister gehaengt -- wer umsortieren will, setzt den
    zurueckgegebenen Baustein-`rang` gezielt neu.
    """
    from pycrdt import Map

    geschwister_raenge = [b.rang for b in bausteine(doc) if b.eltern == eltern]
    rang = max(geschwister_raenge, default=-1.0) + 1.0
    b = Baustein(kennung=neue_kennung(), typ=typ, text=text, feldname=feldname,
                eltern=eltern, rang=rang, alt=alt)
    _liste(doc, BAUSTEINE).append(Map(b.als_dict()))
    return b.kennung


def bausteine(doc) -> list[Baustein]:
    """Alle Bausteine, FLACH in Ablagereihenfolge -- Eltern und Kinder liegen im
    selben Array (Elternfeld statt Kind-Array, ADR-019), darum ist hier nichts
    unsichtbar. Fuer die LESEreihenfolge (Eltern vor Kindern) siehe
    `bausteine_baum`."""
    aus = []
    for eintrag in _liste(doc, BAUSTEINE).to_py():
        aus.append(Baustein(**eintrag))
    return aus


def bausteine_baum(doc) -> list[Baustein]:
    """Bausteine in Lesereihenfolge (Vorordnung: Eltern vor Kindern, siehe
    `baustein.baumreihenfolge`). Das ist die Reihenfolge, in der ein Blatt
    gesetzt wird -- nicht die rohe Ablagereihenfolge."""
    return baumreihenfolge(bausteine(doc))


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
    """Anmerkungen, deren Baustein es nicht (mehr) gibt -- sichtbar, nicht still.

    Nutzt `bausteine_baum` (rekursiv) statt der rohen Liste -- bei der hier
    gewaehlten Speicherform (Elternfeld, kein Kind-Array) liegt zwar JEDER
    Baustein ohnehin flach im selben Array, `vorhanden` waere also mit
    `bausteine(doc)` inhaltlich identisch. Die Rekursion wird trotzdem
    verwendet, wie von ADR-019 verlangt (dieselbe Quelle wie `satz_quelle` und
    die Ableitungswache) -- eine kuenftige Bauform mit echten Kind-Arrays
    faende hier sofort einen Mitstreiter, statt dass jemand diese Stelle
    vergisst."""
    vorhanden = {b.kennung for b in bausteine_baum(doc)}
    return [a for a in anmerkungen(doc) if a.anker.baustein not in vorhanden]


# --- Sprache (ADR-019 Entscheidung 5) ---------------------------------------

def sprache(doc) -> str:
    return _liste_map(doc, META)["sprache"]


def sprache_setzen(doc, code: str) -> str:
    """Setzt die Sprache und gibt den gesetzten Wert zurueck, nie eine
    Bestaetigung (dieselbe Haltung wie `Anmerkung.wechsle`)."""
    if not code or not code.strip():
        raise VertragsFehler("eine leere Sprache ist keine Sprache")
    _liste_map(doc, META)["sprache"] = code
    return code


# --- Veroeffentlicht (ADR-019 Entscheidung 3) -------------------------------
#
# OFFENER PUNKT (Auflage der Entwurfsprobe): `urheber` ist hier ein PFLICHT-
# Parameter, den der Aufrufer beibringen muss. `kern/dokumentdienst.py::
# _anmeldung` liefert heute nur wahr/falsch zurueck, keine Identitaet -- der
# Dienst kann diese Funktion also noch nicht mit einem belegten Urheber
# aufrufen. Diese Funktion ist FERTIG UND GETESTET auf Dokumentebene; die
# Verdrahtung bis zum Netzwerkprotokoll ist es NICHT. Bis dahin bleibt es bei
# "vorgesehen, nicht verdrahtet" -- kein Feld wird gefuellt, das niemand
# echtes setzt.

def ist_veroeffentlicht(doc) -> bool:
    return bool(_liste_map(doc, META)["veroeffentlicht"])


def veroeffentlichungsstand(doc) -> dict:
    """Der volle Zustand -- fuer eine Oberflaeche, die mehr braucht als ja/nein."""
    m = _liste_map(doc, META)
    return {
        "veroeffentlicht": bool(m["veroeffentlicht"]),
        "urheber": m["veroeffentlicht_urheber"],
        "zeitpunkt": m["veroeffentlicht_zeitpunkt"],
    }


def veroeffentlichen(doc, urheber: str, jetzt: str | None = None) -> dict:
    """Veroeffentlicht das Dokument: setzt den Zustand mit Urheber und
    Zeitpunkt UND haelt eine Fassung des Standes fest (Entscheidung 4).

    `jetzt` ist injizierbar (Walkthrough-Doktrin) -- ohne diesen Parameter
    liesse sich ein Zeitstempel im Test nicht gegen einen festen Wert pruefen.
    Vorgabe ist `zeitmarke.jetzt()`, dieselbe EINE Quelle wie ueberall sonst.
    """
    from pycrdt import Map

    if not urheber or not urheber.strip():
        raise VertragsFehler("eine Veroeffentlichung ohne Urheber ist nicht belegt")
    if jetzt is None:
        import zeitmarke
        jetzt = zeitmarke.jetzt()

    m = _liste_map(doc, META)
    m["veroeffentlicht"] = True
    m["veroeffentlicht_urheber"] = urheber
    m["veroeffentlicht_zeitpunkt"] = jetzt

    fassung = {
        "urheber": urheber,
        "zeitpunkt": jetzt,
        "stand": base64.b64encode(doc.get_update()).decode("ascii"),
    }
    _liste(doc, FASSUNGEN).append(Map(fassung))
    return veroeffentlichungsstand(doc)


def fassungen(doc) -> list[dict]:
    """Alle bisher festgehaltenen Fassungen, aelteste zuerst. Billigste Bauform
    (Entscheidung 4): eine Kopie je Veroeffentlichung, keine volle
    Versionierung -- wer den Stand einer Fassung braucht, wendet ihr `stand`
    (ein CRDT-Update) auf ein leeres Dokument an."""
    return [dict(f) for f in _liste(doc, FASSUNGEN).to_py()]


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

    # --- Verschachtelung (ADR-019 Entscheidung 1) ---------------------------
    # ROT vor dieser Aenderung: es gab kein `eltern`-Feld, ein Kind-Baustein
    # war nicht baubar. GRUEN jetzt: ein Kind erscheint in `bausteine_baum`
    # direkt nach seinem Elternteil -- VOR einem spaeter angelegten
    # Geschwister der Wurzelebene. Genau diese Ordnung reisst, sobald jemand
    # `satz.satz_quelle` von `bausteine_baum` zurueck auf die rohe
    # Ablagereihenfolge (`bausteine`) umstellt (Mutationsprobe, siehe
    # `tests/test_satz.py`).
    baumdoc = leeres_dokument()
    wurzel = baustein_anhaengen(baumdoc, "ueberschrift", "Abschnitt 1")
    kind = baustein_anhaengen(baumdoc, "absatz", "Unterpunkt", eltern=wurzel)
    weitere_wurzel = baustein_anhaengen(baumdoc, "absatz", "Abschnitt 2")
    # Flache Ablage: Einfuegereihenfolge, das Kind zuletzt angehaengt.
    assert [b.kennung for b in bausteine(baumdoc)] == [wurzel, kind, weitere_wurzel]
    # Baumreihenfolge: das Kind steht direkt hinter seinem Elternteil.
    assert [b.kennung for b in bausteine_baum(baumdoc)] == [wurzel, kind, weitere_wurzel]

    # Grenzwert: zwei Ebenen tief.
    enkel = baustein_anhaengen(baumdoc, "absatz", "Tiefer", eltern=kind)
    assert [b.kennung for b in bausteine_baum(baumdoc)] == [wurzel, kind, enkel, weitere_wurzel]

    # Grenzwert: Baustein ohne Eltern -- oben bereits mitgeprueft (`wurzel`
    # und `weitere_wurzel` haben eltern=None und stehen beide im Ergebnis).

    # Grenzwert: Baustein mit sich selbst als Eltern -- ein Zyklus, den ein
    # Elternfeld erlaubt (Preis der Bauform, siehe baustein.baumreihenfolge).
    # Kein Fehler beim Anlegen, keine Endlosrekursion beim Lesen, kein
    # Verschwinden.
    from pycrdt import Map as _Map

    ring_kennung = neue_kennung()
    ring = Baustein(kennung=ring_kennung, typ="absatz", text="Ring", eltern=ring_kennung)
    _liste(baumdoc, BAUSTEINE).append(_Map(ring.als_dict()))
    im_baum = {b.kennung for b in bausteine_baum(baumdoc)}
    assert ring_kennung in im_baum, "ein Baustein im Zyklus darf nicht verschwinden"

    # Grenzwert: leeres Dokument.
    assert bausteine_baum(leeres_dokument()) == []

    # Verwaiste bleibt korrekt, auch fuer einen Kind-Baustein: eine Anmerkung
    # auf ein Kind ist NICHT verwaist, solange das Kind existiert.
    kinderdoc = leeres_dokument()
    kwurzel = baustein_anhaengen(kinderdoc, "ueberschrift", "A")
    kkind = baustein_anhaengen(kinderdoc, "absatz", "B", eltern=kwurzel)
    kanmerkung = anmerkung_setzen(kinderdoc, Anker(baustein=kkind), "auf das Kind", "darstellung", "mensch")
    assert verwaiste(kinderdoc) == [], "eine Anmerkung auf ein vorhandenes Kind ist nicht verwaist"

    # --- Sprache (Entscheidung 5) --------------------------------------------
    sprachdoc = leeres_dokument()
    assert sprache(sprachdoc) == "de-DE"      # Vorgabe, deckungsgleich mit dem alten Vorspann
    assert sprache_setzen(sprachdoc, "en-US") == "en-US"
    assert sprache(sprachdoc) == "en-US"
    try:
        sprache_setzen(sprachdoc, "")
    except VertragsFehler:
        pass
    else:
        raise AssertionError("leere Sprache haette fallen muessen")

    # --- Veroeffentlicht + Fassungen (Entscheidung 3+4) ----------------------
    vdoc = leeres_dokument()
    baustein_anhaengen(vdoc, "absatz", "Inhalt vor Veroeffentlichung.")
    assert ist_veroeffentlicht(vdoc) is False     # Vorgabe: nicht veroeffentlicht
    assert veroeffentlichungsstand(vdoc) == {
        "veroeffentlicht": False, "urheber": None, "zeitpunkt": None,
    }
    try:
        veroeffentlichen(vdoc, "")
    except VertragsFehler:
        pass
    else:
        raise AssertionError("Veroeffentlichung ohne Urheber haette fallen muessen")

    stand = veroeffentlichen(vdoc, "gamlehr", jetzt="2026-08-15T10:00:00Z")
    assert stand == {
        "veroeffentlicht": True, "urheber": "gamlehr", "zeitpunkt": "2026-08-15T10:00:00Z",
    }
    assert ist_veroeffentlicht(vdoc) is True
    assert len(fassungen(vdoc)) == 1
    erste_fassung = fassungen(vdoc)[0]
    assert erste_fassung["urheber"] == "gamlehr"
    assert erste_fassung["zeitpunkt"] == "2026-08-15T10:00:00Z"

    # Die Fassung ist wirklich der Stand ZU DEM ZEITPUNKT, keine Behauptung:
    # aus ihrem `stand` laesst sich der damalige Baustein-Text rekonstruieren.
    rekonstruiert = leeres_dokument()
    rekonstruiert.apply_update(base64.b64decode(erste_fassung["stand"]))
    assert [b.text for b in bausteine(rekonstruiert)] == ["Inhalt vor Veroeffentlichung."]

    # Zweite Veroeffentlichung haengt eine ZWEITE Fassung an, ueberschreibt die
    # erste nicht -- das ist der ganze Witz von Entscheidung 4.
    veroeffentlichen(vdoc, "gamlehr", jetzt="2026-08-15T11:00:00Z")
    assert len(fassungen(vdoc)) == 2

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
