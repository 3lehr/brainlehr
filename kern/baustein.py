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

# --- Herkunft eines Bausteins (ADR-021) -------------------------------------
# ANLASS: ADR-021 misst, dass kein Baustein heute sagen kann, ob sein Inhalt
# von Hand kommt oder aus dem Bestand abgeleitet wurde. Ohne dieses Merkmal
# ist der Fall des Betreibers (er ueberschreibt eine abgeleitete Zahl) gar
# nicht entscheidbar. Diese Datei baut NUR die Voraussetzung -- keinen
# Schreibweg in den Bestand (der ist der naechste, hier bewusst nicht
# gebaute Auftrag).
#
# VIER KANDIDATEN GEPRUEFT, ALLE VIER BLEIBEN:
#   eingegeben          -- von Hand getippt. VORGABE, deckungsgleich mit dem
#                           heutigen (einzigen) Verhalten.
#   abgeleitet           -- aus dem Wissensbestand uebernommen. Der einzige
#                           Fall aus dem Anlass des Betreibers.
#   vorschlag_angenommen -- ein Modellvorschlag (Anmerkung von_wem="modell"),
#                           den ein Mensch angenommen hat. Keine Ableitung aus
#                           dem Bestand, trotzdem nicht "von Hand" im Sinn von
#                           selbst formuliert -- eine dritte, eigene Herkunft.
#   importiert           -- aus einer fremden Quelle (z.B. WordPress, ADR-019
#                           offene Frage). Weder Handeingabe noch Bestand.
#
# HERKUNFT UND URHEBERSCHAFT SIND ZWEI VERSCHIEDENE ACHSEN, NICHT DIESELBE --
# die Vermutung aus dem Auftrag ist am Code bestaetigt, nicht widerlegt:
# `Anmerkung.von_wem` (unten) beantwortet "wer hat diesen AUFTRAG/Kommentar
# geschrieben" (mensch/modell) -- eine Aussage ueber eine Anmerkung am Rand.
# `Baustein.herkunft` beantwortet "woher kommt der BAUSTEIN-INHALT selbst" --
# eine Aussage ueber den Baustein. Ein Mensch kann einen abgeleiteten Wert
# von Hand tippen (dann Achse 1 = "mensch" an der Anmerkung, die ihn aendert,
# Achse 2 = vorher "abgeleitet", nachher "eingegeben" am Baustein, siehe
# `dokument.baustein_text_setzen`). Beide Achsen beantworten verschiedene
# Fragen, keine ersetzt die andere.
HERKUNFTSARTEN = ("eingegeben", "abgeleitet", "vorschlag_angenommen", "importiert")
HERKUNFT_VORGABE = "eingegeben"

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
    # ADR-021: woher der INHALT kommt -- siehe HERKUNFTSARTEN oben. Eigene
    # Achse, getrennt von Anmerkung.von_wem (Urheberschaft einer Anmerkung).
    herkunft: str = HERKUNFT_VORGABE
    # Nur bei herkunft != "eingegeben" belegt: die Kennung der Quelle (z.B.
    # ein Wissensknoten). Selbe Bauform wie feldname bei typ=="feld" -- ein
    # Pflichtfeld, das nur in EINEM Fall erlaubt ist. Diese Datei prueft NICHT,
    # ob die Kennung wirklich existiert (kein DB-Zugriff hier, dieselbe
    # Haltung wie bei `eltern` in dokument.py und wie bei "bestand:<id>" in
    # kern/belegvertrag.py::herkunftsart -- die Existenzpruefung waere der
    # Schreibweg, den dieser Auftrag ausdruecklich nicht baut).
    herkunftsquelle: str | None = None
    # Betreiber-Entscheidung 2026-08-15: ein einzelner aktueller Wert kann
    # weder sagen, ob eine Handaenderung die BESSERE war, noch eine
    # Ruecknahme ueberleben. NUR HERKUNFTSWECHSEL werden festgehalten, nicht
    # jede Textaenderung -- der Baustein liegt in einem CRDT, dessen
    # Bytebedarf je Zeichen im Dauerbetrieb von 2,8 auf 15,1 waechst
    # (L-55b830). Ein Verlauf ohne Obergrenze waere keine Gratisleistung; ein
    # Verlauf, der nur an Herkunftswechseln waechst, ist durch die Anzahl
    # ueberschriebener Ableitungen/Vorschlaege begrenzt, nicht durch jeden
    # Tastendruck. Jeder Eintrag: zeitpunkt, herkunft_vorher,
    # herkunftsquelle_vorher, text_vorher, zurueckgenommen_am (None, solange
    # offen). Siehe `herkunft_nach_textaenderung()` unten fuer die Logik, die
    # ihn fuellt, und `praeferenzpaare()` fuer das daraus GERECHNETE Urteil.
    herkunftsverlauf: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.typ not in TYPEN:
            raise VertragsFehler(f"unbekannter Typ {self.typ!r}, erlaubt: {TYPEN}")
        if self.typ == "feld" and not self.feldname:
            raise VertragsFehler("ein Baustein vom Typ 'feld' braucht einen feldname")
        if self.typ != "feld" and self.feldname:
            raise VertragsFehler(f"feldname ist nur bei typ 'feld' erlaubt, nicht bei {self.typ!r}")
        if self.herkunft not in HERKUNFTSARTEN:
            raise VertragsFehler(f"unbekannte Herkunft {self.herkunft!r}, erlaubt: {HERKUNFTSARTEN}")
        if self.herkunft == "eingegeben" and self.herkunftsquelle:
            raise VertragsFehler("herkunftsquelle ist nur bei abgeleiteter/importierter Herkunft erlaubt, nicht bei 'eingegeben'")
        if self.herkunft != "eingegeben" and not self.herkunftsquelle:
            raise VertragsFehler(f"herkunft {self.herkunft!r} braucht eine herkunftsquelle -- sonst ist 'abgeleitet' nur eine Behauptung")

    def als_dict(self) -> dict:
        return asdict(self)


def herkunft_nach_textaenderung(
    herkunft: str,
    herkunftsquelle: str | None,
    text_alt: str,
    text_neu: str,
    verlauf: list[dict],
    jetzt: str | None,
) -> tuple[str, str | None, list[dict]]:
    """Reine Funktion: aus dem bisherigen Herkunftszustand und dem neuen Text
    wird der Zustand NACH der Aenderung berechnet. Kein Seiteneffekt, kein
    DB-Zugriff, kein Zeitstempel-Erzeuger -- `jetzt` wird injiziert
    (Walkthrough-Doktrin), `kern/dokument.py` schreibt das Ergebnis in seinen
    Speicher (CRDT-Map) zurueck.

    ZWEI EREIGNISSE, EIN VERLAUF:

    1. WIDERSPRUCH -- der Baustein trug eine Herkunft != "eingegeben" (eine
       Ableitung, ein angenommener Vorschlag, ein Import) und der Text
       aendert sich. Die Handaenderung GEWINNT (unveraendert gegenueber dem
       bisherigen Verhalten), aber jetzt haelt ein Eintrag fest, WAS
       ueberschrieben wurde: Zeitpunkt, vorherige Herkunft, vorherige Quelle,
       vorheriger Text.

    2. RUECKNAHME -- der neue Text ist EXAKT der Text, der beim letzten noch
       offenen Widerspruch ueberschrieben wurde. Der Mensch hat seine eigene
       Aenderung zurueckgenommen, weil er erkennt, dass die Ableitung/der
       Vorschlag doch recht hatte (Betreiber, woertlich). Die Herkunft
       springt zurueck auf den vorherigen Wert -- der aktuelle Text IST
       wieder exakt das, was damals abgeleitet/vorgeschlagen wurde, das
       Feld beantwortet also wieder wahrheitsgemaess "woher kommt der
       aktuelle Inhalt". Der Eintrag wird nicht ersetzt, nur um
       `zurueckgenommen_am` ERGAENZT -- die Kette bleibt lesbar.

    GRENZWERT, ENTSCHIEDEN: nur EXAKTE Textgleichheit zaehlt als Ruecknahme,
    keine Aehnlichkeit. Ein Aehnlichkeitsmass braeuchte eine Schwelle, und
    Schwellen sind in diesem Projekt gemessen, nicht gesetzt (CLAUDE.md) --
    fuer Textaehnlichkeit existiert keine Messung. Ein zu weiches Mass wuerde
    ausserdem unabhaengige Zufallstreffer als Ruecknahme fehletikettieren,
    genau der Fehler, den die ganze Aenderung vermeiden soll.

    Nur der JUENGSTE offene Eintrag wird geprueft (nicht die ganze Liste) --
    "die letzte Aenderung entscheidet, nicht die erste".
    """
    verlauf = [dict(e) for e in verlauf]  # Kopie, kein Aliasing des Aufrufers

    if text_neu == text_alt:
        return herkunft, herkunftsquelle, verlauf  # kein Ereignis

    if verlauf and verlauf[-1].get("zurueckgenommen_am") is None \
            and verlauf[-1]["text_vorher"] == text_neu:
        eintrag = verlauf[-1]
        eintrag["zurueckgenommen_am"] = jetzt
        return eintrag["herkunft_vorher"], eintrag["herkunftsquelle_vorher"], verlauf

    if herkunft != "eingegeben":
        verlauf.append({
            "zeitpunkt": jetzt,
            "herkunft_vorher": herkunft,
            "herkunftsquelle_vorher": herkunftsquelle,
            "text_vorher": text_alt,
            "zurueckgenommen_am": None,
        })
        return "eingegeben", None, verlauf

    return herkunft, herkunftsquelle, verlauf


def praeferenzpaare(baustein: Baustein) -> list[dict]:
    """Rechnet aus dem Verlauf, welche Herkunftswechsel ein Praeferenzpaar
    fuers Training sind -- der Verlauf PROTOKOLLIERT nur Ereignisse, das
    Urteil ("wessen Fassung war besser") steht nirgends gespeichert, es wird
    HIER bei jedem Aufruf neu berechnet. Grund: ein gespeichertes Urteil
    muesste bei jeder Ruecknahme nachtraeglich UMGESCHRIEBEN werden -- ein
    Feld, das sich nachtraeglich als falsch herausstellen kann, ist die
    gleiche Fehlerklasse wie der Ein-Wert-Zustand, den diese Aenderung
    behebt. Berechnung ist immer aktuell, ein Feld waere es nur, solange
    niemand vergisst, es zu pflegen.

    JE EINTRAG EIN PAAR: `bevorzugt` ist "abgeleitet", wenn der Eintrag
    zurueckgenommen wurde (der Mensch hat der Ableitung/dem Vorschlag am
    Ende recht gegeben), sonst "mensch" (bislang nicht zurueckgenommen --
    der aktuelle Stand des Bausteins ist aktuell nicht der Vorschlagstext).
    Kein Eintrag im Verlauf -> keine Paare: ein nur einmal getippter oder
    nur wiederholt von Hand geaenderter Baustein (ohne je eine Ableitung zu
    tragen) erzeugt nie ein Ereignis.

    WAS DIESE FUNKTION AUSDRUECKLICH NICHT TUT: die eigentliche Auswahl von
    Trainingsmaterial ueber den ganzen Bestand. Das braeuchte einen
    Datenbankzugriff (welche Bausteine, welche Domaene, welche Freigabe),
    den diese Datei bewusst nicht hat (siehe Modulkopf). Diese Funktion
    liefert nur die Kandidaten EINES Bausteins.
    """
    aus = []
    for eintrag in baustein.herkunftsverlauf:
        zurueckgenommen = eintrag.get("zurueckgenommen_am") is not None
        aus.append({
            "herkunft_bewertet": eintrag["herkunft_vorher"],
            "herkunftsquelle": eintrag["herkunftsquelle_vorher"],
            "text_abgeleitet": eintrag["text_vorher"],
            "bevorzugt": "abgeleitet" if zurueckgenommen else "mensch",
            "zeitpunkt_widerspruch": eintrag["zeitpunkt"],
            "zeitpunkt_ruecknahme": eintrag.get("zurueckgenommen_am"),
        })
    return aus


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
    d = Baustein(kennung="fedcba987654", typ="absatz", text="42,00",
                herkunft="abgeleitet", herkunftsquelle="knoten:9f14c5f2")
    # Ein Baustein MIT Verlauf -- ein Vorschlag wurde ueberschrieben, dann
    # zurueckgenommen. Konstruiert, damit die native Seite auch dieses Feld
    # sieht, keine echte Historie.
    g = Baustein(kennung="112233445566", typ="absatz", text="der richtige Satz",
                herkunft="vorschlag_angenommen", herkunftsquelle="anmerkung:aa11bb22cc33",
                herkunftsverlauf=[{
                    "zeitpunkt": "2026-08-15T10:00:00+0200",
                    "herkunft_vorher": "vorschlag_angenommen",
                    "herkunftsquelle_vorher": "anmerkung:aa11bb22cc33",
                    "text_vorher": "der richtige Satz",
                    "zurueckgenommen_am": "2026-08-15T11:00:00+0200",
                }])
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
        "bausteine": [b.als_dict(), f.als_dict(), d.als_dict(), g.als_dict()],
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
    assert set(m["bausteine"][0]) == {
        "kennung", "typ", "text", "feldname", "eltern", "rang", "alt",
        "herkunft", "herkunftsquelle", "herkunftsverlauf",
    }
    assert set(m["anmerkung"]["anker"]) == {"baustein", "suchtext", "von", "bis"}

    # --- Herkunft (ADR-021) --------------------------------------------------
    # Vorgabe: unveraendertes Verhalten -- ein Baustein ohne Angabe ist
    # "eingegeben", genau wie vor dieser Aenderung.
    frei = Baustein(kennung="f" * 12, typ="absatz", text="Frei getippt.")
    assert frei.herkunft == "eingegeben"
    assert frei.herkunftsquelle is None

    # Gegenprobe Richtung 1: von Hand eingegeben bleibt wie bisher zulaessig,
    # auch OHNE Quellenkennung.
    Baustein(kennung="1" * 12, typ="absatz", text="x", herkunft="eingegeben")

    # Gegenprobe Richtung 2: abgeleitet wird UNTERSCHIEDEN -- braucht eine
    # Quellenkennung und traegt sie.
    abgeleitet = Baustein(kennung="2" * 12, typ="absatz", text="42,00",
                          herkunft="abgeleitet", herkunftsquelle="knoten:9f14c5f2")
    assert abgeleitet.herkunft == "abgeleitet"
    assert abgeleitet.herkunftsquelle == "knoten:9f14c5f2"

    # Die anderen beiden geprueften Kandidaten tragen dieselbe Pflicht.
    Baustein(kennung="3" * 12, typ="absatz", text="x",
            herkunft="vorschlag_angenommen", herkunftsquelle="anmerkung:aa11bb22cc33")
    Baustein(kennung="4" * 12, typ="absatz", text="x",
            herkunft="importiert", herkunftsquelle="wordpress:post-17")

    # Grenzwert: Quellenkennung leer bei nicht-eingegebener Herkunft faellt.
    for kaputt in (
        dict(herkunft="abgeleitet", herkunftsquelle=None),
        dict(herkunft="abgeleitet", herkunftsquelle=""),
        dict(herkunft="eingegeben", herkunftsquelle="knoten:9f14c5f2"),  # Quelle ohne Ableitung
        dict(herkunft="erfunden", herkunftsquelle=None),                 # Herkunft gibt es nicht
    ):
        try:
            Baustein(kennung="a" * 12, typ="absatz", text="x", **kaputt)
        except VertragsFehler:
            pass
        else:
            raise AssertionError(f"haette fallen muessen: {kaputt}")

    # Grenzwert: Quelle zeigt auf etwas Nichtexistierendes -- diese Datei hat
    # keinen DB-Zugriff und prueft das bewusst NICHT (dieselbe Haltung wie bei
    # `eltern`/`Anker.baustein`). Strukturell zulaessig, auch wenn "knoten:xxx"
    # nie vergeben wurde.
    Baustein(kennung="5" * 12, typ="absatz", text="x",
            herkunft="abgeleitet", herkunftsquelle="knoten:existiert-nicht")

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

    # Grenzwert: verschachtelte Bausteine mit GEMISCHTER Herkunft -- die
    # Baumbildung kennt kein "herkunft" und darf davon unbeeinflusst bleiben;
    # jeder Knoten traegt seine eigene, unabhaengig vom Elternteil.
    mp = Baustein(kennung="m" * 12, typ="absatz", text="Mutter", rang=0.0,
                 herkunft="abgeleitet", herkunftsquelle="knoten:mutter")
    mk = Baustein(kennung="n" * 12, typ="absatz", text="Kind", eltern=mp.kennung, rang=0.0,
                 herkunft="eingegeben")
    gemischt = baumreihenfolge([mp, mk])
    assert [b.kennung for b in gemischt] == [mp.kennung, mk.kennung]
    nach_kennung_gemischt = {b.kennung: b for b in gemischt}
    assert nach_kennung_gemischt[mp.kennung].herkunft == "abgeleitet"
    assert nach_kennung_gemischt[mk.kennung].herkunft == "eingegeben"

    # --- Herkunftsverlauf: der Dreischritt (Betreiber, 2026-08-15) -----------
    # Vorschlag angenommen -> Mensch aendert von Hand -> Mensch nimmt zurueck.
    # ROT vor dieser Aenderung: es gab kein Feld, das den Widerspruch und die
    # Ruecknahme getrennt haelt -- ein einzelner Wert kannte nur den letzten
    # Zustand.
    herkunft1, quelle1, verlauf1 = herkunft_nach_textaenderung(
        herkunft="vorschlag_angenommen", herkunftsquelle="anmerkung:aa11bb22cc33",
        text_alt="der richtige Satz", text_neu="mein Satz", verlauf=[], jetzt="t1",
    )
    assert (herkunft1, quelle1) == ("eingegeben", None), "Handaenderung gewinnt, wie bisher"
    assert verlauf1 == [{
        "zeitpunkt": "t1", "herkunft_vorher": "vorschlag_angenommen",
        "herkunftsquelle_vorher": "anmerkung:aa11bb22cc33",
        "text_vorher": "der richtige Satz", "zurueckgenommen_am": None,
    }], "der Widerspruch muss den vorherigen Zustand festhalten"

    herkunft2, quelle2, verlauf2 = herkunft_nach_textaenderung(
        herkunft=herkunft1, herkunftsquelle=quelle1,
        text_alt="mein Satz", text_neu="der richtige Satz", verlauf=verlauf1, jetzt="t2",
    )
    assert (herkunft2, quelle2) == ("vorschlag_angenommen", "anmerkung:aa11bb22cc33"), \
        "Ruecknahme muss die vorherige Herkunft wiederherstellen"
    assert verlauf2 == [{
        "zeitpunkt": "t1", "herkunft_vorher": "vorschlag_angenommen",
        "herkunftsquelle_vorher": "anmerkung:aa11bb22cc33",
        "text_vorher": "der richtige Satz", "zurueckgenommen_am": "t2",
    }], "derselbe Eintrag wird ERGAENZT, nicht ersetzt -- die Kette bleibt lesbar"

    # Ablesbar: erst Widerspruch, dann Nachgeben -- beides steht im selben Eintrag.
    paare = praeferenzpaare(Baustein(kennung="q" * 12, typ="absatz",
                                     text="der richtige Satz",
                                     herkunft=herkunft2, herkunftsquelle=quelle2,
                                     herkunftsverlauf=verlauf2))
    assert paare == [{
        "herkunft_bewertet": "vorschlag_angenommen", "herkunftsquelle": "anmerkung:aa11bb22cc33",
        "text_abgeleitet": "der richtige Satz", "bevorzugt": "abgeleitet",
        "zeitpunkt_widerspruch": "t1", "zeitpunkt_ruecknahme": "t2",
    }], "eine zurueckgenommene Handaenderung ist ein Paar zugunsten der Ableitung"

    # Negativfall 1: nur einmal getippt, nie geaendert -- kein Ereignis.
    frei2 = Baustein(kennung="r" * 12, typ="absatz", text="Nie angefasst.")
    assert praeferenzpaare(frei2) == []

    # Negativfall 2: zwei Handaenderungen hintereinander OHNE Vorschlag
    # dazwischen -- beide Male ist herkunft schon "eingegeben", kein Eintrag.
    h3, q3, v3 = herkunft_nach_textaenderung(
        herkunft="eingegeben", herkunftsquelle=None,
        text_alt="A", text_neu="B", verlauf=[], jetzt="t1",
    )
    assert (h3, q3, v3) == ("eingegeben", None, [])
    h4, q4, v4 = herkunft_nach_textaenderung(
        herkunft=h3, herkunftsquelle=q3, text_alt="B", text_neu="C", verlauf=v3, jetzt="t2",
    )
    assert (h4, q4, v4) == ("eingegeben", None, [])
    assert praeferenzpaare(Baustein(kennung="s" * 12, typ="absatz", text="C",
                                    herkunft=h4, herkunftsquelle=q4,
                                    herkunftsverlauf=v4)) == []

    # Grenzwert: Ruecknahme auf einen Text, der dem urspruenglichen nur
    # AEHNLICH ist (nicht identisch) -- zaehlt NICHT als Ruecknahme (s. o.
    # Begruendung in herkunft_nach_textaenderung), bleibt "eingegeben",
    # der offene Eintrag bleibt offen fuer die naechste Pruefung.
    h5, q5, v5 = herkunft_nach_textaenderung(
        herkunft="eingegeben", herkunftsquelle=None,
        text_alt="mein Satz", text_neu="der richtige Satz, fast",
        verlauf=verlauf1, jetzt="t3",
    )
    assert (h5, q5) == ("eingegeben", None), "aehnlich ist keine Ruecknahme"
    assert v5[-1]["zurueckgenommen_am"] is None, "der Eintrag bleibt offen"

    # Grenzwert: leerer Text als Ziel einer Ruecknahme -- funktioniert wie
    # jeder andere Text auch, kein Sonderfall.
    h6, q6, v6 = herkunft_nach_textaenderung(
        herkunft="abgeleitet", herkunftsquelle="knoten:x",
        text_alt="", text_neu="von Hand", verlauf=[], jetzt="t1",
    )
    assert v6 == [{
        "zeitpunkt": "t1", "herkunft_vorher": "abgeleitet",
        "herkunftsquelle_vorher": "knoten:x", "text_vorher": "",
        "zurueckgenommen_am": None,
    }]
    h7, q7, v7 = herkunft_nach_textaenderung(
        herkunft=h6, herkunftsquelle=q6, text_alt="von Hand", text_neu="",
        verlauf=v6, jetzt="t2",
    )
    assert (h7, q7) == ("abgeleitet", "knoten:x"), "Ruecknahme auf leeren Text funktioniert"
    assert v7[-1]["zurueckgenommen_am"] == "t2"

    # Grenzwert: Verlauf mit genau einem Eintrag, der noch offen ist -- ein
    # Text, der WEDER dem alten noch dem urspruenglich abgeleiteten gleicht,
    # loest keine Ruecknahme aus und haengt keinen zweiten Eintrag an, weil
    # die Herkunft bereits "eingegeben" ist.
    h8, q8, v8 = herkunft_nach_textaenderung(
        herkunft="eingegeben", herkunftsquelle=None,
        text_alt="mein Satz", text_neu="noch ein anderer Satz",
        verlauf=verlauf1, jetzt="t4",
    )
    assert len(v8) == 1, "keine neue Ableitung wurde ueberschrieben, kein neuer Eintrag"
    assert v8[0]["zurueckgenommen_am"] is None

    # Mutationsprobe (von Hand, hier dokumentiert): wird die Bedingung
    # `verlauf[-1]["text_vorher"] == text_neu` durch `text_neu in
    # verlauf[-1]["text_vorher"]` ersetzt (Teilstring statt Gleichheit),
    # muss Grenzwert 5 (aehnlich != identisch) rot werden. Wird die
    # Ruecknahme-Ergaenzung durch ein `verlauf.append(...)` ersetzt (neuer
    # Eintrag statt Ergaenzung des bestehenden), muss die Assertion
    # `verlauf2 == [...]` (ein einzelner Eintrag) rot werden.

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
