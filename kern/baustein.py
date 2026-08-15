#!/usr/bin/env python3
"""Der Baustein-Vertrag -- was ein Dokument ist, woran eine Anmerkung haengt.

ANLASS: ADR-010 legt das Dokumentfenster fest (nativ, mehrbenutzerfaehig,
Zeichen fuer Zeichen ueber ein CRDT). Sein Schritt 2 ist bindend VOR dem ersten
Dokument: ein Anker, der eine Aenderung nicht ueberlebt, wandert STILL an die
falsche Stelle, und nachtraeglich ist nicht mehr rekonstruierbar, worauf eine
Anmerkung einmal zeigte. Diese Datei ist dieser Vertrag.

DREI ENTSCHEIDUNGEN, und jede hat eine Alternative, die schlechter ist:

1. DIE KENNUNG WIRD VERGEBEN, NIE ABGELEITET. Naheliegend waere eine Kennung
   aus dem Inhalt (Pruefsumme) -- sie waere ohne Zustand reproduzierbar. Genau
   das macht sie unbrauchbar: sie aendert sich mit jedem Buchstaben, und damit
   verliert jede Anmerkung ihren Bezug, sobald die KI tut, wozu die Anmerkung
   sie aufgefordert hat. Eine vergebene Kennung ueberlebt den Inhalt. Sie ist
   deshalb auch NICHT sprechend -- wer aus "b_einleitung" liest, was der
   Baustein enthaelt, baut die naechste stille Falle.

2. DER ANKER TRAEGT DREI ANGABEN, NICHT EINE. Kennung (haelt), Suchtext (heilt),
   Bereich (zeigt). Findet die Kennung nichts mehr, ist die Anmerkung VERWAIST
   und wird als solche angezeigt -- sie wandert nie ueber den Suchtext an eine
   aehnliche Stelle. Der Suchtext dient der Anzeige und der Wiedererkennung
   durch einen Menschen, nicht der automatischen Zuordnung. Dieselbe Trennung
   wie in `kern/fundstelle.py`, wo `belegt`, `markierbar` und `mehrdeutig` drei
   getrennte Aussagen sind statt einer.

3. ZURUECKGEGEBEN WIRD DER ERREICHTE ZUSTAND, NIE EINE BESTAETIGUNG. Ein "ok"
   ohne Zustand macht eine wirkungslose Umsetzung von einer wirksamen
   ununterscheidbar -- dieselbe Fehlerklasse, die in einer Nacht dreimal
   zuschlug (`L-db37c6`).

WAS HIER BEWUSST NICHT DRIN IST: kein CRDT (das ist die Transportschicht, nicht
der Vertrag), keine Speicherung, kein Dienst. Diese Datei sagt, WAS ein Dokument
ist -- nicht, wie es uebertragen oder abgelegt wird.

Aufruf:  python3 kern/baustein.py --selftest
         python3 kern/baustein.py --vertrag   (Musterantwort mit ALLEN Feldern)
"""

from __future__ import annotations

import argparse
import json
import secrets
from dataclasses import asdict, dataclass, field

# --- Bausteintypen ---------------------------------------------------------
# `feld` steht bewusst gleichberechtigt neben `absatz`: damit tragen Schriftsatz
# und Rechnung DIESELBE Struktur, und die Rechnungserstellung braucht keine
# zweite (Betreiber, 2026-08-14: "felder gleich mitdenken").
TYPEN = ("absatz", "ueberschrift", "tabelle", "grafik", "feld")

# --- Zustaende einer Anmerkung ---------------------------------------------
ZUSTAENDE = ("offen", "umgesetzt", "abgenommen", "abgelehnt")

# Erlaubte Uebergaenge. `umgesetzt -> offen` bleibt drin, weil eine Umsetzung
# zurueckgenommen werden koennen muss, ohne die Anmerkung zu verlieren.
# `abgenommen` und `abgelehnt` sind Endzustaende -- wer dort weiter will,
# schreibt eine neue Anmerkung, damit die alte Kette lesbar bleibt.
UEBERGAENGE = {
    "offen": ("umgesetzt", "abgelehnt"),
    "umgesetzt": ("abgenommen", "abgelehnt", "offen"),
    "abgenommen": (),
    "abgelehnt": (),
}

# --- Klassen einer Anmerkung -----------------------------------------------
# Entscheidet, ob die KI selbstaendig umsetzen DARF -- nicht, ob sie es tut.
# Ob sie es tut, entscheidet der Nutzer ueber einen Schalter; Vorgabe ist aus
# (Betreiber, 2026-08-14: "Weil es die soll User Entscheidung sein").
KLASSEN_LEICHT = ("tippfehler", "umbruch", "darstellung")
KLASSEN_SCHWER = ("inhalt", "zahl", "rechtssatz")
KLASSEN = KLASSEN_LEICHT + KLASSEN_SCHWER


class VertragsFehler(ValueError):
    """Etwas verstoesst gegen den Vertrag -- laut, nicht still."""


def neue_kennung() -> str:
    """Zwoelf Hex-Zeichen, vergeben statt abgeleitet. Siehe Entscheidung 1."""
    return secrets.token_hex(6)


@dataclass
class Baustein:
    kennung: str
    typ: str
    text: str = ""
    # Nur bei typ == "feld" belegt: der Name, unter dem ein Formular den Wert
    # kennt. Ein Feld ohne Namen ist ein Absatz mit Kasten drumherum.
    feldname: str | None = None
    # ADR-019 Entscheidung 1: Verschachtelung ueber ein ELTERNFELD, nicht ueber
    # Kind-Arrays -- Yjs kennt kein konfliktfreies Verschieben eines Knotens
    # zwischen Eltern (Kleppmann 2020). Die Liste bleibt flach, der Baum
    # entsteht beim Lesen ueber `baumreihenfolge()`. None heisst: Wurzel.
    eltern: str | None = None
    # Geschwister-Reihenfolge ist mit dem Elternfeld nicht mehr implizit ueber
    # die Array-Position gegeben und braucht ein eigenes Feld. Ein Gleitkomma-
    # Rang statt einer Ganzzahl: Umsortieren bleibt eine einzelne Feldaenderung
    # (neuer Wert zwischen zwei Nachbarn), ohne alle Geschwister neu zu
    # nummerieren.
    rang: float = 0.0
    # ADR-019 Entscheidung 2, korrigiert durch die Entwurfsprobe: Alternativtext
    # ist ein Feld an JEDEM Baustein (WCAG 2.2 verlangt ihn auch bei Tabellen),
    # nicht nur an grafik.
    alt: str = ""

    def __post_init__(self) -> None:
        if self.typ not in TYPEN:
            raise VertragsFehler(f"unbekannter Typ {self.typ!r}, erlaubt: {TYPEN}")
        if self.typ == "feld" and not self.feldname:
            raise VertragsFehler("ein Baustein vom Typ 'feld' braucht einen feldname")
        if self.typ != "feld" and self.feldname:
            raise VertragsFehler(f"feldname ist nur bei typ 'feld' erlaubt, nicht bei {self.typ!r}")

    def als_dict(self) -> dict:
        return asdict(self)


@dataclass
class Anker:
    """Wohin eine Anmerkung zeigt. Drei Angaben, siehe Entscheidung 2."""

    baustein: str            # haelt   -- die vergebene Kennung
    suchtext: str = ""       # heilt   -- fuer den Menschen, nie zum Zuordnen
    von: int | None = None   # zeigt   -- Zeichenbereich zum Zeitpunkt der Anmerkung
    bis: int | None = None

    def __post_init__(self) -> None:
        if not self.baustein:
            raise VertragsFehler("ein Anker ohne Bausteinkennung zeigt nirgendwohin")
        if (self.von is None) != (self.bis is None):
            raise VertragsFehler("Bereich braucht beide Grenzen oder keine")
        if self.von is not None and self.bis < self.von:
            raise VertragsFehler(f"Bereich laeuft rueckwaerts: {self.von} bis {self.bis}")

    def als_dict(self) -> dict:
        return asdict(self)


@dataclass
class Anmerkung:
    """Kein Kommentar am Rand, sondern ein Auftrag mit Anker (Knoten de9aba1a)."""

    kennung: str
    anker: Anker
    text: str
    klasse: str
    von_wem: str                      # "mensch" oder "modell"
    zustand: str = "offen"
    # Wurde sie selbstaendig umgesetzt, bleibt das sichtbar -- eine automatische
    # Aenderung, die aussieht wie eine bestaetigte, ist der Sinn der Auflage.
    selbstaendig_umgesetzt: bool = False
    verlauf: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.klasse not in KLASSEN:
            raise VertragsFehler(f"unbekannte Klasse {self.klasse!r}, erlaubt: {KLASSEN}")
        if self.zustand not in ZUSTAENDE:
            raise VertragsFehler(f"unbekannter Zustand {self.zustand!r}")
        if self.von_wem not in ("mensch", "modell"):
            raise VertragsFehler(f"von_wem ist 'mensch' oder 'modell', nicht {self.von_wem!r}")
        if not self.text.strip():
            raise VertragsFehler("eine Anmerkung ohne Text ist kein Auftrag")

    @property
    def darf_automatisch(self) -> bool:
        """Ob die Klasse eine selbstaendige Umsetzung ERLAUBT -- nicht, ob sie geschieht."""
        return self.klasse in KLASSEN_LEICHT

    def wechsle(self, neuer: str) -> str:
        """Setzt den Zustand und gibt den ERREICHTEN zurueck. Siehe Entscheidung 3."""
        if neuer not in ZUSTAENDE:
            raise VertragsFehler(f"unbekannter Zustand {neuer!r}")
        if neuer not in UEBERGAENGE[self.zustand]:
            raise VertragsFehler(
                f"Uebergang {self.zustand!r} -> {neuer!r} ist nicht vorgesehen; "
                f"moeglich waere: {UEBERGAENGE[self.zustand] or '(Endzustand)'}"
            )
        self.verlauf.append(f"{self.zustand}->{neuer}")
        self.zustand = neuer
        return self.zustand

    def als_dict(self) -> dict:
        d = asdict(self)
        d["darf_automatisch"] = self.darf_automatisch
        return d


def loese_anker(anker: Anker, bausteine: list[Baustein]) -> Baustein | None:
    """Findet den Baustein zum Anker -- oder gibt None und damit 'verwaist'.

    Ausdruecklich KEINE Suche ueber den Suchtext als Rueckfallweg: eine
    Anmerkung, die an eine aehnliche Stelle wandert, ist schlimmer als eine, die
    sichtbar ins Leere zeigt.
    """
    for b in bausteine:
        if b.kennung == anker.baustein:
            return b
    return None


def baumreihenfolge(bausteine: list[Baustein]) -> list[Baustein]:
    """Baut die Lesereihenfolge aus der flachen Liste -- Vorordnung, Eltern vor
    Kindern, Geschwister nach `rang` sortiert.

    WURZEL ist jeder Baustein ohne `eltern` UND jeder, dessen `eltern` auf eine
    nicht (mehr) vorhandene Kennung zeigt (Grenzwert aus ADR-019) -- er wird
    nicht stillschweigend verschluckt, nur weil sein Elternteil fehlt.

    ZYKLUS: ein Elternfeld erlaubt Ringe (A zeigt auf B, B auf A, oder ein
    Baustein zeigt auf sich selbst) -- ein Kind-Array haette das strukturell
    verhindert, das ist der Preis dieser Bauform. Ein besuchtes Kennung wird
    nie ein zweites Mal betreten, das bricht jeden Ring ohne Endlosrekursion.
    Kein Baustein aus einem Ring geht verloren: was nach dem Wurzel-Durchlauf
    noch fehlt, wird als eigene Wurzel nachgetragen.
    """
    nach_kennung = {b.kennung: b for b in bausteine}
    kinder_von: dict[str | None, list[Baustein]] = {}
    for b in bausteine:
        kinder_von.setdefault(b.eltern, []).append(b)
    for geschwister in kinder_von.values():
        geschwister.sort(key=lambda b: b.rang)

    ergebnis: list[Baustein] = []
    besucht: set[str] = set()

    def besuche(b: Baustein) -> None:
        if b.kennung in besucht:
            return
        besucht.add(b.kennung)
        ergebnis.append(b)
        for kind in kinder_von.get(b.kennung, ()):
            besuche(kind)

    wurzeln = [b for b in bausteine if b.eltern is None or b.eltern not in nach_kennung]
    wurzeln.sort(key=lambda b: b.rang)
    for w in wurzeln:
        besuche(w)

    for b in bausteine:
        if b.kennung not in besucht:
            besuche(b)

    return ergebnis


def vertragsmuster() -> dict:
    """Eine Antwort, in der JEDES Feld vorkommt -- die Vorlage fuer beide Sprachen.

    Wie bei `kern/fundstelle.py`: die native Seite ueberliest unbekannte
    Schluessel wortlos. Ein hier umbenanntes Feld kaeme dort also nie an, ohne
    dass irgendwo ein Fehler entstuende -- die Anmerkung saehe aus wie nicht
    vorhanden. Deshalb ein konstruierter Fall mit allen Feldern, kein echter.
    """
    b = Baustein(kennung="0123456789ab", typ="absatz", text="Erster Satz.")
    f = Baustein(kennung="ba9876543210", typ="feld", text="", feldname="rechnungsnummer")
    a = Anmerkung(
        kennung="ffeeddccbbaa",
        anker=Anker(baustein=b.kennung, suchtext="Erster Satz.", von=0, bis=12),
        text="Hier ist die Legende unleserlich.",
        klasse="darstellung",
        von_wem="mensch",
    )
    return {
        "typen": list(TYPEN),
        "zustaende": list(ZUSTAENDE),
        "uebergaenge": {k: list(v) for k, v in UEBERGAENGE.items()},
        "klassen_leicht": list(KLASSEN_LEICHT),
        "klassen_schwer": list(KLASSEN_SCHWER),
        "bausteine": [b.als_dict(), f.als_dict()],
        "anmerkung": a.als_dict(),
    }


def _selftest() -> int:
    # Kennungen werden vergeben, nicht abgeleitet -- zwei gleiche Inhalte,
    # zwei verschiedene Kennungen.
    assert neue_kennung() != neue_kennung()
    assert len(neue_kennung()) == 12

    # Typen: Grenzfall Feld.
    Baustein(kennung="a" * 12, typ="feld", text="", feldname="betrag")
    for kaputt in (
        dict(typ="feld", feldname=None),          # Feld ohne Namen
        dict(typ="absatz", feldname="betrag"),    # Name ohne Feld
        dict(typ="fussnote", feldname=None),      # Typ gibt es nicht
    ):
        try:
            Baustein(kennung="a" * 12, **kaputt)
        except VertragsFehler:
            pass
        else:
            raise AssertionError(f"haette fallen muessen: {kaputt}")

    # Anker: Bereich ganz oder gar nicht, und nie rueckwaerts.
    Anker(baustein="a" * 12)
    Anker(baustein="a" * 12, von=3, bis=3)         # Grenzwert: leerer Bereich ist erlaubt
    for kaputt in (dict(von=3), dict(bis=3), dict(von=5, bis=4), dict(baustein="")):
        try:
            Anker(**{"baustein": "a" * 12, **kaputt})
        except VertragsFehler:
            pass
        else:
            raise AssertionError(f"haette fallen muessen: {kaputt}")

    # Zustandswechsel gibt den ERREICHTEN Zustand zurueck, nicht True.
    a = Anmerkung(
        kennung="b" * 12,
        anker=Anker(baustein="a" * 12),
        text="Zahl stimmt nicht.",
        klasse="zahl",
        von_wem="mensch",
    )
    assert a.darf_automatisch is False           # schwere Klasse
    assert a.wechsle("umgesetzt") == "umgesetzt"
    assert a.wechsle("offen") == "offen"         # Ruecknahme moeglich
    assert a.wechsle("umgesetzt") == "umgesetzt"
    assert a.wechsle("abgenommen") == "abgenommen"
    assert a.verlauf == ["offen->umgesetzt", "umgesetzt->offen",
                         "offen->umgesetzt", "umgesetzt->abgenommen"]
    for verboten in ("offen", "umgesetzt", "abgelehnt"):   # Endzustand ist Endzustand
        try:
            a.wechsle(verboten)
        except VertragsFehler:
            pass
        else:
            raise AssertionError(f"aus 'abgenommen' nach {verboten!r} haette fallen muessen")

    # Der Sprung ueber einen Schritt faellt ebenfalls.
    b = Anmerkung(kennung="c" * 12, anker=Anker(baustein="a" * 12),
                  text="Tippfehler.", klasse="tippfehler", von_wem="modell")
    assert b.darf_automatisch is True
    try:
        b.wechsle("abgenommen")
    except VertragsFehler:
        pass
    else:
        raise AssertionError("offen -> abgenommen haette fallen muessen")

    # Ein Anker auf einen geloeschten Baustein ist VERWAIST, nicht umgehaengt --
    # auch wenn ein anderer Baustein denselben Text traegt.
    da = Baustein(kennung="1" * 12, typ="absatz", text="Erster Satz.")
    gleicher_text = Baustein(kennung="2" * 12, typ="absatz", text="Erster Satz.")
    anker = Anker(baustein=da.kennung, suchtext="Erster Satz.")
    assert loese_anker(anker, [da, gleicher_text]) is da
    assert loese_anker(anker, [gleicher_text]) is None

    # Das Vertragsmuster traegt jedes Feld -- sonst faellt die Gegenseite still aus.
    m = vertragsmuster()
    assert set(m["anmerkung"]) == {
        "kennung", "anker", "text", "klasse", "von_wem", "zustand",
        "selbstaendig_umgesetzt", "verlauf", "darf_automatisch",
    }
    assert set(m["bausteine"][0]) == {"kennung", "typ", "text", "feldname", "eltern", "rang", "alt"}
    assert set(m["anmerkung"]["anker"]) == {"baustein", "suchtext", "von", "bis"}

    # baumreihenfolge: leeres Dokument -> leere Reihenfolge.
    assert baumreihenfolge([]) == []

    # Zwei Ebenen tief, Geschwister nach rang: P vor seinem Kind C, C vor S
    # (S ist Wurzel-Geschwister mit hoeherem rang als P).
    p = Baustein(kennung="p" * 12, typ="absatz", text="P", rang=0.0)
    s = Baustein(kennung="s" * 12, typ="absatz", text="S", rang=1.0)
    c = Baustein(kennung="c" * 12, typ="absatz", text="C", eltern=p.kennung, rang=0.0)
    enkel = Baustein(kennung="e" * 12, typ="absatz", text="E", eltern=c.kennung, rang=0.0)
    geordnet = baumreihenfolge([s, p, enkel, c])   # absichtlich nicht in Baumreihenfolge uebergeben
    assert [b.kennung for b in geordnet] == [p.kennung, c.kennung, enkel.kennung, s.kennung]

    # Baustein ohne Eltern ist Wurzel (Grenzwert 1) -- oben bereits mitgeprueft
    # (p, s haben eltern=None und stehen beide im Ergebnis).

    # Eltern zeigt auf eine nicht existierende Kennung -> wird als Wurzel
    # behandelt, geht nicht verloren (Grenzwert).
    verwaister_elter = Baustein(kennung="v" * 12, typ="absatz", text="V",
                                eltern="9" * 12)
    ohne_eltern_bekannt = baumreihenfolge([verwaister_elter])
    assert [b.kennung for b in ohne_eltern_bekannt] == [verwaister_elter.kennung]

    # Zyklus 1: Baustein ist sein eigener Elternteil -- kein Endlosrekursion,
    # taucht genau einmal auf.
    selbst = Baustein(kennung="z" * 12, typ="absatz", text="Z", eltern="z" * 12)
    assert [b.kennung for b in baumreihenfolge([selbst])] == [selbst.kennung]

    # Zyklus 2: A -> B -> A, zwei Bausteine, keiner geht verloren, keine
    # Endlosschleife.
    a_ring = Baustein(kennung="a" * 12, typ="absatz", text="A", eltern="b" * 12)
    b_ring = Baustein(kennung="b" * 12, typ="absatz", text="B", eltern="a" * 12)
    im_ring = {b.kennung for b in baumreihenfolge([a_ring, b_ring])}
    assert im_ring == {a_ring.kennung, b_ring.kennung}

    print("baustein: Selbsttest bestanden")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--vertrag", action="store_true",
                   help="Musterantwort mit ALLEN Feldern -- die Vorlage, gegen die "
                        "beide Sprachen pruefen")
    a = p.parse_args()
    if a.selftest:
        return _selftest()
    if a.vertrag:
        print(json.dumps(vertragsmuster(), ensure_ascii=False, indent=2))
        return 0
    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
