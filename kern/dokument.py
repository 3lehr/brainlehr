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
    herkunft_nach_textaenderung,
    neue_kennung,
    praeferenzpaare as _praeferenzpaare_baustein,
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
                       eltern: str | None = None, alt: str = "",
                       herkunft: str = "eingegeben", herkunftsquelle: str | None = None) -> str:
    """Legt einen Baustein an und gibt seine Kennung zurueck -- nicht True.

    `eltern` wird NICHT gegen den Bestand geprueft -- dieselbe Haltung wie bei
    `anmerkung_setzen`: ein Eltern-Baustein, der (noch) nicht existiert, ist
    erlaubt und wird beim Lesen als Wurzel behandelt (siehe
    `baustein.baumreihenfolge`). `rang` wird automatisch ans Ende der
    bestehenden Geschwister gehaengt -- wer umsortieren will, setzt den
    zurueckgegebenen Baustein-`rang` gezielt neu.

    `herkunft`/`herkunftsquelle` (ADR-021): woher der INHALT stammt, siehe
    `baustein.HERKUNFTSARTEN`. Vorgabe "eingegeben" -- ein Aufruf ohne diese
    Parameter verhaelt sich exakt wie vor dieser Erweiterung. Wer hier
    "abgeleitet" setzt, macht das VOR dieser Funktion aus, sie schreibt nur,
    was uebergeben wird -- den Schreibweg aus dem Wissensbestand baut diese
    Datei ausdruecklich nicht.
    """
    from pycrdt import Map

    geschwister_raenge = [b.rang for b in bausteine(doc) if b.eltern == eltern]
    rang = max(geschwister_raenge, default=-1.0) + 1.0
    b = Baustein(kennung=neue_kennung(), typ=typ, text=text, feldname=feldname,
                eltern=eltern, rang=rang, alt=alt,
                herkunft=herkunft, herkunftsquelle=herkunftsquelle)
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


def _finde_baustein(doc, kennung: str):
    liste = _liste(doc, BAUSTEINE)
    for i, eintrag in enumerate(liste.to_py()):
        if eintrag["kennung"] == kennung:
            return i, eintrag
    return None, None


def baustein_loeschen(doc, kennung: str) -> str:
    """Entfernt einen Baustein und gibt seine Kennung zurueck.

    Anmerkungen, die daran haengen, werden NICHT geloescht und NICHT
    umgehaengt -- der Anker haelt die Kennung fest (baustein.py Entscheidung
    2), also wird eine solche Anmerkung ab jetzt von `verwaiste()` gemeldet.
    Kinder des geloeschten Bausteins bleiben liegen und werden beim naechsten
    Lesen ueber `baumreihenfolge` als eigene Wurzel behandelt (derselbe
    Grenzwert wie bei einem von Anfang an fehlenden Elternteil)."""
    i, eintrag = _finde_baustein(doc, kennung)
    if eintrag is None:
        raise VertragsFehler(f"kein Baustein mit Kennung {kennung!r}")
    del _liste(doc, BAUSTEINE)[i]
    return kennung


def baustein_verschieben(doc, kennung: str, eltern: str | None) -> str:
    """Haengt einen Baustein unter ein neues Elternfeld um (oder an die Wurzel,
    `eltern=None`). Gibt den gesetzten Elternwert zurueck.

    Die Kennung des verschobenen Bausteins aendert sich NICHT -- ein Anker,
    der darauf zeigt, ueberlebt die Verschiebung unveraendert. Genau das ist
    der Zweck von "Kennung wird vergeben, nie abgeleitet" (baustein.py
    Entscheidung 1): eine Anmerkung haengt an einer Kennung, nicht an einer
    Position im Baum.

    `eltern` wird NICHT gegen den Bestand geprueft, dieselbe Haltung wie bei
    `baustein_anhaengen`. Ein Baustein als sein eigener Elternteil wird
    dagegen abgelehnt -- das waere kein Nebeneffekt gleichzeitiger Bearbeitung
    (den Fall laesst `baumreihenfolge` bewusst zu), sondern ein einzelner
    lokaler Aufruf, der sich ohne Grund selbst einen Ring baut."""
    i, eintrag = _finde_baustein(doc, kennung)
    if eintrag is None:
        raise VertragsFehler(f"kein Baustein mit Kennung {kennung!r}")
    if eltern == kennung:
        raise VertragsFehler("ein Baustein kann nicht sein eigener Elternteil werden")
    eintrag_map = _liste(doc, BAUSTEINE)[i]
    eintrag_map["eltern"] = eltern
    return eltern


def baustein_text_setzen(doc, kennung: str, text: str, jetzt: str | None = None) -> str:
    """Setzt den Text eines Bausteins und gibt ihn zurueck.

    Der Anker einer Anmerkung zeigt danach unveraendert auf denselben
    Baustein -- ob sie inhaltlich noch gilt, ist eine Entscheidung eines
    Menschen oder Modells (`zustand_setzen`), keine, die diese Funktion
    trifft: eine Aenderung kann einen Auftrag erledigen oder gegenstandslos
    machen, beides sieht von hier aus gleich aus. Was sich automatisch
    aendert: ein Anker mit `von`/`bis` kann nach einer Kuerzung ueber das neue
    Textende hinauszeigen -- das faengt `bereichsfehler()`, nicht diese
    Funktion.

    ADR-021 FRAGE 2, NEU ENTSCHIEDEN (Betreiber 2026-08-15): Diese Funktion
    ist der einzige heute gebaute Weg, mit dem ein Mensch einen Bausteintext
    im Dokumentfenster ueberschreibt -- sie IST die "Handaenderung" aus dem
    Anlass. Trug der Baustein bisher eine Herkunft ungleich "eingegeben"
    (also "abgeleitet"/"vorschlag_angenommen"/"importiert"), GEWINNT die
    Handaenderung weiterhin: die Herkunft wird auf "eingegeben"
    zurueckgesetzt, die Quellenkennung geloescht -- unveraendert gegenueber
    vorher. NEU: das wird nicht mehr STILL geloescht, sondern in
    `Baustein.herkunftsverlauf` festgehalten (Zeitpunkt, vorherige Herkunft,
    vorherige Quelle, vorheriger Text), und eine spaetere Ruecknahme -- der
    Text kehrt exakt zum ueberschriebenen Stand zurueck -- stellt die
    vorherige Herkunft wieder her, statt die Quelle nach dem verlorenen
    Widerspruch fuer immer als "eingegeben" stehen zu lassen. Die ganze
    Logik liegt in `baustein.herkunft_nach_textaenderung()` (pure Funktion,
    kein CRDT-Wissen); diese Funktion schreibt nur deren Ergebnis in die
    Map. `jetzt` ist injizierbar (Walkthrough-Doktrin), Vorgabe
    `zeitmarke.jetzt()`, dieselbe Quelle wie bei `veroeffentlichen`."""
    i, eintrag = _finde_baustein(doc, kennung)
    if eintrag is None:
        raise VertragsFehler(f"kein Baustein mit Kennung {kennung!r}")
    if jetzt is None:
        import zeitmarke
        jetzt = zeitmarke.jetzt()
    eintrag_map = _liste(doc, BAUSTEINE)[i]
    herkunft_neu, quelle_neu, verlauf_neu = herkunft_nach_textaenderung(
        herkunft=eintrag.get("herkunft", "eingegeben"),
        herkunftsquelle=eintrag.get("herkunftsquelle"),
        text_alt=eintrag.get("text", ""),
        text_neu=text,
        verlauf=eintrag.get("herkunftsverlauf") or [],
        jetzt=jetzt,
    )
    eintrag_map["text"] = text
    eintrag_map["herkunft"] = herkunft_neu
    eintrag_map["herkunftsquelle"] = quelle_neu
    eintrag_map["herkunftsverlauf"] = verlauf_neu
    return text


def praeferenzpaare(doc) -> list[dict]:
    """Alle Praeferenzpaar-Kandidaten ueber JEDEN Baustein des Dokuments --
    gerechnet aus `Baustein.herkunftsverlauf`, siehe
    `baustein.praeferenzpaare()` fuer die Begruendung, warum das GERECHNET
    statt gespeichert wird. Jeder Eintrag traegt zusaetzlich `baustein`, die
    Kennung, sonst waere ein Treffer nicht einem Baustein zuzuordnen."""
    aus = []
    for b in bausteine(doc):
        for paar in _praeferenzpaare_baustein(b):
            aus.append({"baustein": b.kennung, **paar})
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


def mitwirkende(doc) -> dict[str, list[str]]:
    """Wer hat hier gearbeitet -- Anmerkungskennungen je 'mensch' und 'modell'.

    Gesamtplan F5, woertlich: "'modell' kommt in kern/dokument.py nur als Wert
    in einem Selbsttest vor... das Modell hat dort noch nie gesessen." Diese
    Funktion ist die Antwort auf genau die Frage, die dort fehlte: nicht "gibt
    es das Feld", sondern "kann irgendjemand am Dokument selbst nachlesen, wer
    beigetragen hat".

    DIE UNTERSCHEIDUNG SITZT AN DER ANMERKUNG (`Anmerkung.von_wem`), NICHT AN
    EINER EIGENEN TEILNEHMERKENNUNG UND NICHT AN EINEM AUSWEIS. Eine CRDT-
    Teilnehmerkennung (`kern/teilnehmer.py`) ist nur eine Zahl ohne Bedeutung --
    jeder Klient bekommt irgendeine, ein Modell-Klient ist darin nicht von
    einem Menschen zu unterscheiden. Ein Ausweis fuer die KI ist laut ADR-010
    ausdruecklich NICHT gebaut ("die Naht fuer spaeter, wird heute nicht
    gebaut"). Der Anker ist also nicht die zweitbeste Wahl, sondern die
    einzige, die heute etwas trägt.
    """
    aus: dict[str, list[str]] = {"mensch": [], "modell": []}
    for a in anmerkungen(doc):
        aus[a.von_wem].append(a.kennung)
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


def bereichsfehler(doc) -> list[Anmerkung]:
    """Anmerkungen, deren Baustein noch existiert, deren Zeichenbereich
    (`Anker.von`/`bis`) aber nicht mehr in den AKTUELLEN Text des Bausteins
    passt -- unterscheidet sich von `verwaiste()`: dort fehlt der Baustein
    ganz, hier ist er da, nur kuerzer geworden als der Bereich, auf den die
    Anmerkung zeigt. Wie bei `verwaiste()` wird nichts automatisch
    umgehaengt, nur sichtbar gemacht -- eine Anmerkung ohne Bereichsangabe
    (`bis=None`) kann per Definition nicht in diesen Fehler laufen, ihr
    genuegt der Baustein."""
    nach_kennung = {b.kennung: b for b in bausteine(doc)}
    treffer = []
    for a in anmerkungen(doc):
        b = nach_kennung.get(a.anker.baustein)
        if b is None:
            continue   # das ist verwaist, nicht bereichsfehler -- siehe verwaiste()
        if a.anker.bis is not None and a.anker.bis > len(b.text):
            treffer.append(a)
    return treffer


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
    assert baustein_loeschen(doc, erster) == erster
    verwaist_jetzt = {a.kennung for a in verwaiste(doc)}
    assert a1 in verwaist_jetzt, "Anmerkung muss verwaisen statt auf den gleichen Text zu springen"
    assert a2 not in verwaist_jetzt
    try:
        baustein_loeschen(doc, "999999999999")
    except VertragsFehler:
        pass
    else:
        raise AssertionError("Loeschen eines nie vorhandenen Bausteins haette fallen muessen")

    # --- Verschieben (F7: der Anker haelt die Kennung, keine Position) ------
    # ROT waere hier: eine Anmerkung, die nach dem Umhaengen am falschen
    # Baustein haengt oder verwaist. GRUEN: sie bleibt exakt am Ziel, auch
    # wenn der Baum sich unter ihr umbaut.
    verschiebedoc = leeres_dokument()
    alter_platz = baustein_anhaengen(verschiebedoc, "ueberschrift", "Alt")
    neuer_platz = baustein_anhaengen(verschiebedoc, "ueberschrift", "Neu")
    ziel = baustein_anhaengen(verschiebedoc, "absatz", "Zieltext.", eltern=alter_platz)
    verankert = anmerkung_setzen(verschiebedoc, Anker(baustein=ziel, suchtext="Ziel"),
                                 "haengt am Ziel", "inhalt", "mensch")
    assert [b.kennung for b in bausteine_baum(verschiebedoc)] == [alter_platz, ziel, neuer_platz]
    assert baustein_verschieben(verschiebedoc, ziel, neuer_platz) == neuer_platz
    assert [b.kennung for b in bausteine_baum(verschiebedoc)] == [alter_platz, neuer_platz, ziel]
    assert verwaiste(verschiebedoc) == [], "eine Verschiebung darf nicht verwaisen lassen"
    assert {a.kennung: a.anker.baustein for a in anmerkungen(verschiebedoc)}[verankert] == ziel, \
        "der Anker muss die Kennung halten, unabhaengig vom neuen Elternfeld"
    try:
        baustein_verschieben(verschiebedoc, ziel, ziel)
    except VertragsFehler:
        pass
    else:
        raise AssertionError("ein Baustein als sein eigener Elternteil haette fallen muessen")
    try:
        baustein_verschieben(verschiebedoc, "999999999999", None)
    except VertragsFehler:
        pass
    else:
        raise AssertionError("Verschieben eines nie vorhandenen Bausteins haette fallen muessen")

    # --- Textaenderung und Bereichsfehler (F7 Frage 2+3) --------------------
    # Der Anker bleibt gueltig, solange der Baustein existiert -- eine
    # Textaenderung loescht die Anmerkung nicht. Ein Bereich (von/bis), der
    # nach einer Kuerzung ueber das neue Textende hinauszeigt, wird trotzdem
    # sichtbar gemeldet, getrennt von "verwaist".
    textdoc = leeres_dokument()
    mit_bereich = baustein_anhaengen(textdoc, "absatz", "Ein langer Satz mit vielen Worten.")
    ohne_bereich = baustein_anhaengen(textdoc, "absatz", "Kurz.")
    a_bereich = anmerkung_setzen(textdoc, Anker(baustein=mit_bereich, suchtext="langer", von=4, bis=10),
                                 "hier ist das Wort falsch", "inhalt", "mensch")
    a_ohne = anmerkung_setzen(textdoc, Anker(baustein=ohne_bereich), "generell pruefen",
                              "darstellung", "mensch")
    assert bereichsfehler(textdoc) == [], "beide Bereiche passen noch in den jeweiligen Text"
    assert baustein_text_setzen(textdoc, mit_bereich, "Kurz.") == "Kurz."
    fehlerhaft = {a.kennung for a in bereichsfehler(textdoc)}
    assert fehlerhaft == {a_bereich}, "nur der gekuerzte Baustein mit Bereichsangabe faellt auf"
    assert a_ohne not in fehlerhaft, "ein Anker ohne Bereich kann nicht in einen Bereichsfehler laufen"
    assert {a.kennung for a in verwaiste(textdoc)} == set(), "der Baustein existiert weiterhin, das ist kein Verwaisen"
    # Gegenprobe: eine unveraenderte Anmerkung an einem unveraenderten
    # Baustein bleibt unveraendert.
    unveraendert = anmerkungen(textdoc)
    assert baustein_text_setzen(textdoc, ohne_bereich, "Kurz.") == "Kurz."   # gleicher Text zurueckgeschrieben
    assert anmerkungen(textdoc) == unveraendert
    try:
        baustein_text_setzen(textdoc, "999999999999", "x")
    except VertragsFehler:
        pass
    else:
        raise AssertionError("Textaenderung an einem nie vorhandenen Baustein haette fallen muessen")

    # Grenzwert: Dokument ganz ohne Anmerkungen -- beide Meldefunktionen bleiben leer.
    leer = leeres_dokument()
    baustein_anhaengen(leer, "absatz", "Text ohne jede Anmerkung.")
    assert verwaiste(leer) == []
    assert bereichsfehler(leer) == []

    # Die Teilnehmerkennung bleibt unter der Schranke -- auch hier. Grenzwert
    # BEIDSEITIG: 2**32-1 traegt (Swift-Seite schneidet erst DAHINTER ab),
    # 2**32 faellt -- unsere Vergabe LAESST das Verdoppeln also gar nicht zu,
    # statt es nur zu melden (ADR-010, L-44dc9f).
    assert leeres_dokument(2**32 - 1).client_id == 2**32 - 1
    try:
        leeres_dokument(2**32)
    except KennungsFehler:
        pass
    else:
        raise AssertionError("Kennung ueber 2^32-1 haette fallen muessen")

    # --- Mensch UND Modell am selben Dokument, gleichzeitig, unterscheidbar --
    # (Gesamtplan F5: "das Modell hat dort noch nie gesessen" -- ROT war vor
    # `mitwirkende()`: es gab keine Stelle im Code, die diese Frage
    # beantwortete, nur der freie Blick in jede einzelne Anmerkung.)
    von_mensch = leeres_dokument()
    an_stelle = baustein_anhaengen(von_mensch, "absatz", "Ein Satz mit einem Fehler drin.")
    von_modell = leeres_dokument(neue_teilnehmerkennung())
    von_modell.apply_update(von_mensch.get_update())   # beide sehen denselben Baustein

    a_mensch = anmerkung_setzen(von_mensch, Anker(baustein=an_stelle, suchtext="Fehler"),
                                "das muss anders klingen", "inhalt", "mensch")
    a_modell = anmerkung_setzen(von_modell, Anker(baustein=an_stelle, suchtext="Fehler"),
                                "Tippfehler: 'drin' -> 'darin'.", "tippfehler", "modell")

    zusammen = leeres_dokument()
    zusammen.apply_update(von_mensch.get_update())
    zusammen.apply_update(von_modell.get_update())

    wer = mitwirkende(zusammen)
    assert wer["mensch"] == [a_mensch], wer
    assert wer["modell"] == [a_modell], wer
    nach_kennung = {a.kennung: a for a in anmerkungen(zusammen)}
    assert nach_kennung[a_modell].darf_automatisch is True    # tippfehler
    assert nach_kennung[a_mensch].darf_automatisch is False   # inhalt

    # Gegenprobe: eine Anmerkung des Modells, die der Mensch VERWIRFT, bleibt
    # im Verlauf sichtbar -- kein spurloses Verschwinden.
    zustand_setzen(zusammen, a_modell, "abgelehnt")
    nach_ablehnung = {a.kennung: a for a in anmerkungen(zusammen)}[a_modell]
    assert nach_ablehnung.zustand == "abgelehnt"
    assert nach_ablehnung.verlauf == ["offen->abgelehnt"]
    assert a_modell in mitwirkende(zusammen)["modell"], "verworfen ist nicht verschwunden"

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

    # --- Herkunft (ADR-021) ---------------------------------------------------
    # ROT vor dieser Aenderung: `baustein_anhaengen` kannte keine Herkunft,
    # jeder Baustein sah gleich aus, egal ob getippt oder abgeleitet.
    herkdoc = leeres_dokument()

    # Gegenprobe Richtung 1: von Hand eingegeben verhaelt sich WIE BISHER --
    # ein Aufruf ohne die neuen Parameter aendert nichts am alten Verhalten.
    getippt = baustein_anhaengen(herkdoc, "absatz", "Frei getippt.")
    assert [b for b in bausteine(herkdoc) if b.kennung == getippt][0].herkunft == "eingegeben"

    # Gegenprobe Richtung 2: abgeleitet wird UNTERSCHIEDEN und traegt die Quelle.
    abgeleitet = baustein_anhaengen(herkdoc, "feld", "42,00", feldname="betrag",
                                    herkunft="abgeleitet", herkunftsquelle="knoten:9f14c5f2")
    ab_baustein = [b for b in bausteine(herkdoc) if b.kennung == abgeleitet][0]
    assert ab_baustein.herkunft == "abgeleitet"
    assert ab_baustein.herkunftsquelle == "knoten:9f14c5f2"

    # Der eigentliche Fall aus dem Anlass des Betreibers: der Mensch
    # ueberschreibt den abgeleiteten Wert im Dokumentfenster von Hand -- die
    # Handaenderung GEWINNT, die Ableitung wird geloest (Frage 2).
    assert baustein_text_setzen(herkdoc, abgeleitet, "drei haben zugestimmt") == "drei haben zugestimmt"
    umgestellt = [b for b in bausteine(herkdoc) if b.kennung == abgeleitet][0]
    assert umgestellt.herkunft == "eingegeben", "eine Handaenderung muss die Ableitung loesen"
    assert umgestellt.herkunftsquelle is None, "die geloeste Quelle darf nicht stehen bleiben"
    # NEU (Betreiber 2026-08-15): der Widerspruch wird festgehalten, nicht
    # still ueberschrieben.
    assert len(umgestellt.herkunftsverlauf) == 1
    assert umgestellt.herkunftsverlauf[0]["herkunft_vorher"] == "abgeleitet"
    assert umgestellt.herkunftsverlauf[0]["herkunftsquelle_vorher"] == "knoten:9f14c5f2"
    assert umgestellt.herkunftsverlauf[0]["text_vorher"] == "42,00"
    assert umgestellt.herkunftsverlauf[0]["zurueckgenommen_am"] is None

    # Gegenprobe: ein bereits "eingegeben"er Baustein bleibt beim Ueberschreiben
    # unberuehrt -- kein wiederholtes Zuruecksetzen von etwas, das nicht
    # abgeleitet war.
    assert baustein_text_setzen(herkdoc, getippt, "Nochmal getippt.") == "Nochmal getippt."
    weiterhin = [b for b in bausteine(herkdoc) if b.kennung == getippt][0]
    assert weiterhin.herkunft == "eingegeben"

    # Verschachtelte Bausteine mit gemischter Herkunft ueberleben die Baumbildung.
    mutter = baustein_anhaengen(herkdoc, "absatz", "Mutter", herkunft="abgeleitet",
                                herkunftsquelle="knoten:mutter")
    kind_eingegeben = baustein_anhaengen(herkdoc, "absatz", "Kind", eltern=mutter)
    baum = {b.kennung: b for b in bausteine_baum(herkdoc)}
    assert baum[mutter].herkunft == "abgeleitet"
    assert baum[kind_eingegeben].herkunft == "eingegeben"

    # --- Herkunftsverlauf: der Dreischritt auf Dokumentebene -----------------
    # Vorschlag angenommen -> Mensch aendert von Hand -> Mensch nimmt zurueck.
    # ROT vor dieser Aenderung: `baustein_text_setzen` loeschte die
    # Quellenkennung STILL, `praeferenzpaare(doc)` gab es nicht -- Widerspruch
    # und Nachgeben waren aus dem Dokument nicht ablesbar.
    dreidoc = leeres_dokument()
    vorschlag = baustein_anhaengen(dreidoc, "absatz", "der richtige Satz",
                                   herkunft="vorschlag_angenommen",
                                   herkunftsquelle="anmerkung:aa11bb22cc33")
    baustein_text_setzen(dreidoc, vorschlag, "mein Satz", jetzt="2026-08-15T10:00:00+0200")
    nach_widerspruch = [b for b in bausteine(dreidoc) if b.kennung == vorschlag][0]
    assert nach_widerspruch.herkunft == "eingegeben"
    assert len(nach_widerspruch.herkunftsverlauf) == 1
    assert nach_widerspruch.herkunftsverlauf[0]["zurueckgenommen_am"] is None

    baustein_text_setzen(dreidoc, vorschlag, "der richtige Satz", jetzt="2026-08-15T11:00:00+0200")
    nach_ruecknahme = [b for b in bausteine(dreidoc) if b.kennung == vorschlag][0]
    assert nach_ruecknahme.herkunft == "vorschlag_angenommen", \
        "Ruecknahme muss die vorherige Herkunft wiederherstellen"
    assert nach_ruecknahme.herkunftsquelle == "anmerkung:aa11bb22cc33"
    assert len(nach_ruecknahme.herkunftsverlauf) == 1, "ERGAENZT, kein zweiter Eintrag"
    assert nach_ruecknahme.herkunftsverlauf[0]["zurueckgenommen_am"] == "2026-08-15T11:00:00+0200"

    # Ablesbar aus dem Dokument: erst Widerspruch, dann Nachgeben.
    paare_dreidoc = praeferenzpaare(dreidoc)
    assert paare_dreidoc == [{
        "baustein": vorschlag,
        "herkunft_bewertet": "vorschlag_angenommen", "herkunftsquelle": "anmerkung:aa11bb22cc33",
        "text_abgeleitet": "der richtige Satz", "bevorzugt": "abgeleitet",
        "zeitpunkt_widerspruch": "2026-08-15T10:00:00+0200",
        "zeitpunkt_ruecknahme": "2026-08-15T11:00:00+0200",
    }]

    # Negativfall 1: nur einmal getippt, nie geaendert -- kein Paar.
    einmaldoc = leeres_dokument()
    baustein_anhaengen(einmaldoc, "absatz", "Nie angefasst.")
    assert praeferenzpaare(einmaldoc) == []

    # Negativfall 2: zwei Handaenderungen hintereinander ohne Vorschlag
    # dazwischen -- kein Paar, keine Herkunft wechselt je von "eingegeben" weg.
    zweidoc = leeres_dokument()
    nur_hand = baustein_anhaengen(zweidoc, "absatz", "A")
    baustein_text_setzen(zweidoc, nur_hand, "B", jetzt="t1")
    baustein_text_setzen(zweidoc, nur_hand, "C", jetzt="t2")
    assert praeferenzpaare(zweidoc) == []

    # Zwei Teilnehmer sehen denselben Verlauf, in derselben Uebertragung --
    # dieselbe Garantie wie bei Zustand und Anker weiter oben.
    zweiter_dreidoc = leeres_dokument(neue_teilnehmerkennung())
    zweiter_dreidoc.apply_update(dreidoc.get_update())
    assert praeferenzpaare(zweiter_dreidoc) == paare_dreidoc

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
