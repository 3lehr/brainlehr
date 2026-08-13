#!/usr/bin/env python3
"""normfundstelle.py -- aus "§ 16 Abs. 2 Satz 2 WEG" wird der Wortlaut, der dort steht.

ANLASS (Betreiber, 2026-08-13): "lieber alles richtig und universell machen
statt quick and dirty". Der Anlass war eine Handpflege-Aufgabe -- 19 HTML-
Quellen in buckeberg tragen ihre Fundstelle im Klartext im falschen Feld. Die
haette man abtippen koennen. Dann waeren es beim naechsten Gesetz wieder 19.

WAS DIESES MODUL LOEST, und es ist die allgemeinere Aufgabe: Ein Beleg nennt
eine Norm ("§ 16 Abs. 2 Satz 2 WEG"). Um die Stelle im Dokument zu MARKIEREN,
braucht die Anzeige aber keinen Verweis, sondern WORTLAUT -- die Zeichenfolge,
nach der sie suchen kann. Dieses Modul schlaegt die Bruecke, fuer jede Norm in
jedem Dokument dieser Bauart.

WARUM DAS UEBER buckeberg HINAUSGEHT: Dieselbe Bauform tragen alle Auszuege
von gesetze-im-internet.de -- also auch der Steuerrechtsbestand von openlehr.
Ein Verfahren, das "§ 16 Abs. 2 WEG" aufloest, loest auch "§ 4 Abs. 5 EStG".

ABGRENZUNG zu kern/normbezug.py: Das dortige erkenne() findet, DASS eine Norm
zitiert wird, und liefert die Kennung "WEG §16" -- Absatz und Satz wirft es
weg, weil es sie fuer die Belegpruefung nicht braucht. Hier braucht man sie,
denn sie sind der Unterschied zwischen "irgendwo in diesem Paragraphen" und
"diese Zeile". Deshalb ein eigenes, feineres Zergliedern statt eines Umbaus
an normbezug -- dessen Kennung bleibt die Waehrung fuer den Belegabgleich.

DIE FEHLKLASSE, gegen die hier gebaut wird: eine Fundstelle zu ERFINDEN. Wenn
Absatz 7 nicht existiert oder Satz 4 in einem dreisaetzigen Absatz verlangt
wird, ist die Antwort None -- nicht der naechstbeste Absatz. Eine falsch
gesetzte Markierung sieht im Raum wie ein Beleg aus, und dort widerspricht ihr
niemand.

GEMESSEN am 2026-08-13: Alle 18 HTML-Quellen in buckeberg sind iso-8859-1 und
deklarieren das auch. Die Kodierung wird darum AUS DER DEKLARATION gelesen und
nicht geraten -- wer utf-8 annimmt, bekommt einen UnicodeDecodeError bei jedem
Umlaut, und wer blind latin-1 nimmt, verstuemmelt jedes echte utf-8-Dokument.

Aufruf:
    python3 kern/normfundstelle.py --norm "§ 16 Abs. 2 Satz 2 WEG" --datei <pfad.html>
    python3 kern/normfundstelle.py --norm "§ 28 WEG" --datei <pfad.html> --alle
    python3 kern/normfundstelle.py --selftest
"""

from __future__ import annotations

import argparse
import html as html_mod
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# "§ 16 Abs. 2 Satz 2 WEG" / "§ 9b Abs. 1 Satz 3 WEG" / "§ 559a BGB"
# Paragraphenzahlen tragen oft einen Buchstaben (9b, 26a, 559a) -- der gehoert
# zur Nummer, nicht zum Gesetz.
# In ZWEI Schritten statt in einem Muster, und das ist kein Stilfrage:
# Die deutsche Normgliederung ist offen nach unten -- Absatz, Satz, Nummer,
# Halbsatz, Buchstabe, Alternative, Ziffer, und in Verordnungen noch mehr.
# Ein Muster, das die Stufen aufzaehlt, ist bei der naechsten Stufe still
# falsch: es liest dann das GLIEDERUNGSWORT als Gesetzeskuerzel. Genau so
# geschehen bei "§ 19 Abs. 2 Nr. 6 WEG" -> Gesetz "Nr".
# Darum: erst den Paragraphen, dann alles bis zum ersten Wort, das KEIN
# Gliederungswort ist -- das ist das Gesetz. Die Stufen dazwischen werden
# einzeln gelesen, unbekannte einfach uebersprungen statt missdeutet.
_PARAGRAF = re.compile(r"§+\s*(?P<paragraf>\d+[a-z]?)", re.UNICODE)
_WORT = re.compile(r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß]{0,14}", re.UNICODE)
_STUFE = re.compile(
    r"\b(?P<wort>Abs|Absatz|S|Satz|Nr|Nrn|Halbs|Buchst|lit|Alt|Ziff)\.?\s*(?P<zahl>\d+)",
    re.UNICODE,
)

# Gliederungswoerter sehen aus wie Gesetzeskuerzel und sind keine. Ohne diese
# Liste liest der Parser "§ 19 Abs. 2 Nr. 6 WEG" als Gesetz "Nr" -- gemessen
# am 2026-08-13 an buckeberg-Quelle 33. Die deutsche Normgliederung ist
# tiefer als Absatz und Satz: darunter liegen Nummer, Buchstabe, Halbsatz und
# Alternative, und jede davon steht vor dem Gesetzeskuerzel.
_GLIEDERUNG = {"Nr", "Nrn", "Abs", "Satz", "Halbs", "Buchst", "lit", "Alt",
               "Ziff", "Anlage", "Anhang", "Art"}

# Absatzmarken "(1)" am Anfang eines Absatzes. Bewusst nicht irgendwo mitten
# im Satz -- "(2)" in einer Aufzaehlung waere sonst ein Absatzbeginn.
_ABSATZMARKE = re.compile(r"(?:^|(?<=[.\s]))\((\d{1,2})\)\s")

# Satzende: Punkt, dem ein Leerzeichen und ein Grossbuchstabe folgt. Bricht bei
# Abkuerzungen -- die haeufigsten stehen darum in _KEINE_SATZGRENZE.
_SATZENDE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ„])")
_KEINE_SATZGRENZE = ("Abs.", "Nr.", "Satz", "lit.", "Art.", "Buchst.", "S.",
                     "vgl.", "bzw.", "z. B.", "u. a.", "ggf.", "Halbs.")


@dataclass
class Normstelle:
    gesetz: str
    paragraf: str
    absatz: int | None = None
    satz: int | None = None
    nummer: int | None = None

    @property
    def kennung(self) -> str:
        """Dieselbe Waehrung wie normbezug.erkenne() -- fuer den Belegabgleich."""
        return f"{self.gesetz} §{self.paragraf}"

    def __str__(self) -> str:
        teile = [f"§ {self.paragraf}"]
        if self.absatz:
            teile.append(f"Abs. {self.absatz}")
        if self.satz:
            teile.append(f"Satz {self.satz}")
        if self.nummer:
            teile.append(f"Nr. {self.nummer}")
        teile.append(self.gesetz)
        return " ".join(teile)


def zergliedere(text: str) -> Normstelle | None:
    """Zerlegt eine Normangabe in ihre Teile. None, wenn keine erkennbar ist.

    Sucht weiter, wenn als Gesetz ein Gliederungswort herauskaeme -- der
    naechste Treffer ist dann das echte Kuerzel.
    """
    p = _PARAGRAF.search(text or "")
    if not p:
        return None

    # Das Gesetz ist das erste grossgeschriebene Wort nach dem Paragraphen,
    # das kein Gliederungswort ist. Ohne Fund: keine Normstelle -- eine
    # Paragraphennummer allein gehoert zu keinem bestimmten Gesetz.
    rest = text[p.end():]
    gesetz = None
    for w in _WORT.finditer(rest):
        if w.group(0).rstrip(".") not in _GLIEDERUNG:
            gesetz, bis = w.group(0), w.start()
            break
    if gesetz is None:
        return None

    stufen = {m.group("wort").rstrip("."): int(m.group("zahl"))
              for m in _STUFE.finditer(rest[:bis])}
    return Normstelle(
        gesetz=gesetz,
        paragraf=p.group("paragraf"),
        absatz=stufen.get("Abs") or stufen.get("Absatz"),
        satz=stufen.get("Satz") or stufen.get("S"),
        nummer=stufen.get("Nr") or stufen.get("Nrn"),
    )


# ─── HTML zu Text ─────────────────────────────────────────────────────────

def kodierung(rohbytes: bytes) -> str:
    """Kodierung aus der Deklaration lesen, nicht raten.

    Gemessen: alle 18 HTML-Quellen in buckeberg sind iso-8859-1 und sagen es
    auch. utf-8 anzunehmen bricht bei jedem Umlaut; blind latin-1 zu nehmen
    verstuemmelt jedes echte utf-8-Dokument. Die Datei weiss es selbst.
    """
    m = re.search(rb"charset=[\"']?([A-Za-z0-9_-]+)", rohbytes[:4096])
    if m:
        return m.group(1).decode("ascii", "replace").lower()
    try:
        rohbytes.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp1252"   # der haeufigste Fall ohne Angabe, und latin-1-vertraeglich


def text_aus_html(rohbytes: bytes) -> str:
    """Sichtbarer Text: Skript und Stil raus, Tags raus, Entities aufgeloest."""
    s = rohbytes.decode(kodierung(rohbytes), errors="replace")
    s = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html_mod.unescape(s)
    # Geschuetzte Leerzeichen sind Leerzeichen -- sonst scheitert jede Suche
    # an einer Stelle, die fuer das Auge identisch aussieht.
    return re.sub(r"[\s ]+", " ", s).strip()


# ─── Zerlegen ─────────────────────────────────────────────────────────────

def gesetze_im_text(text: str) -> set[str]:
    """Gesetzeskuerzel, die das Dokument selbst fuehrt.

    Nur der ANFANG wird gelesen: Dort steht der Titel. Weiter hinten verweist
    fast jede Norm auf fremde Gesetze ("nach Massgabe des § 47 der
    Grundbuchordnung"), und wer die mitzaehlt, haelt am Ende jedes Dokument
    fuer jedes Gesetz zustaendig -- die Probe waere dann immer bestanden und
    damit wertlos.
    """
    return set(re.findall(r"\b([A-ZÄÖÜ][A-Za-zÄÖÜ]{0,8}(?:G|GB|O|V))\b", text[:400]))


def absaetze(text: str) -> dict[int, str]:
    """Absatznummer -> Wortlaut. Leer, wenn das Dokument keine Marken traegt."""
    stellen = [(m.start(), int(m.group(1)), m.end()) for m in _ABSATZMARKE.finditer(text)]
    if not stellen:
        return {}
    ergebnis: dict[int, str] = {}
    for i, (_, nummer, ende) in enumerate(stellen):
        schluss = stellen[i + 1][0] if i + 1 < len(stellen) else len(text)
        # Nur den ERSTEN Treffer je Nummer nehmen. Ein Gesetzesauszug enthaelt
        # oft Verweise auf andere Paragraphen mit eigenen Absatzmarken; die
        # kommen spaeter und duerfen den echten Absatz nicht ueberschreiben.
        if nummer not in ergebnis:
            ergebnis[nummer] = text[ende:schluss].strip()
    return ergebnis


def nummer_im_absatz(absatz: str, nummer: int) -> str | None:
    """Wortlaut der Aufzaehlungsnummer, oder None.

    Gesetzestexte schreiben "1." oder "1)". Gesucht wird nur an einer
    Zaehlposition -- nach Satzende oder Semikolon --, damit eine Jahreszahl
    oder ein Geldbetrag nicht als Aufzaehlungspunkt durchgeht.
    """
    m = _nummernmarke(nummer).search(absatz)
    if not m:
        return None
    rest = absatz[m.end():]
    weiter = _nummernmarke(nummer + 1).search(rest)
    return (rest[:weiter.start()] if weiter else rest).strip() or None


def _nummernmarke(nummer: int) -> re.Pattern:
    """"1." als Aufzaehlungspunkt, aber nicht als Teil einer Zahl.

    Die Nummern folgen im Gesetzestext oft auf ein KOMMA, nicht auf einen
    Punkt ("... gehoeren insbesondere 1. die Aufstellung einer Hausordnung,
    2. die ordnungsmaessige Erhaltung ..."). Ein Muster, das Satzende verlangt,
    findet sie nie -- gemessen an § 19 Abs. 2 WEG.

    Was sie trotzdem von einer Zahl trennt, ist der Blick NACH der Marke: auf
    einen Aufzaehlungspunkt folgt Text, auf eine gebrochene Zahl folgt eine
    Ziffer ("2. 500 Euro"). Und davor darf keine Ziffer stehen, sonst wird aus
    "12." die Nummer 2.
    """
    return re.compile(rf"(?<!\d){nummer}[.)]\s+(?!\d)")


def saetze(absatz: str) -> list[str]:
    """Saetze eines Absatzes. Abkuerzungen brechen die Zerlegung nicht."""
    roh = _SATZENDE.split(absatz)
    zusammen: list[str] = []
    for teil in roh:
        if zusammen and zusammen[-1].rstrip().endswith(_KEINE_SATZGRENZE):
            zusammen[-1] = zusammen[-1] + " " + teil
        else:
            zusammen.append(teil)
    return [t.strip() for t in zusammen if t.strip()]


# ─── die eigentliche Aufloesung ───────────────────────────────────────────

def wortlaut(rohbytes: bytes, stelle: Normstelle) -> dict:
    """Der Wortlaut an dieser Normstelle -- oder eine Begruendung, warum nicht.

    Rueckgabe traegt IMMER `gefunden`; bei False steht in `grund`, woran es
    lag. Kein Rueckfall auf den naechstbesten Absatz: Absatz 7 in einem
    Paragraphen mit drei Absaetzen ist ein Befund, kein Rundungsfehler.
    """
    text = text_aus_html(rohbytes)
    if not text:
        return {"gefunden": False, "grund": "Das Dokument enthaelt keinen lesbaren Text."}

    # Steht in diesem Dokument ueberhaupt der gesuchte Paragraph?
    kopf = re.search(rf"§\s*{re.escape(stelle.paragraf)}\b", text)
    if not kopf:
        return {"gefunden": False,
                "grund": f"§ {stelle.paragraf} kommt in diesem Dokument nicht vor."}

    # UND handelt es sich ueberhaupt um dasselbe Gesetz? Ohne diese Probe
    # findet "§ 72 GEG" seine Stelle in einem Dokument ueber das GModG --
    # gemessen am 2026-08-13 bei buckeberg-Quelle 11: Das GEG wurde zum
    # 2026-07-29 ersetzt, die hinterlegte Datei nachgezogen, das Beschriftungs-
    # feld nicht. Eine Paragraphennummer allein ist keine Identitaet; sie
    # existiert in jedem Gesetz.
    kuerzel = gesetze_im_text(text)
    if kuerzel and stelle.gesetz not in kuerzel:
        return {"gefunden": False,
                "grund": (f"Das Dokument fuehrt {'/'.join(sorted(kuerzel))}, "
                          f"gesucht war {stelle.gesetz}."),
                "gesetz_im_dokument": sorted(kuerzel)}

    abs_map = absaetze(text)

    if stelle.absatz is None:
        # Ohne Absatzangabe ist der Anfang des NORMTEXTS die ehrlichste
        # Antwort -- nicht die Stelle, an der "§ 72" zuerst auftaucht. Das ist
        # naemlich der Seitenkopf ("§ 72 GModG - Einzelnorm zurueck weiter
        # Nichtamtliches Inhaltsverzeichnis"), und den zu markieren hiesse,
        # auf die Navigationsleiste zu zeigen statt auf das Gesetz.
        if abs_map:
            return {"gefunden": True, "ebene": "paragraf",
                    "suchtext": _knapp(abs_map[min(abs_map)]),
                    "wortlaut": abs_map[min(abs_map)],
                    "absaetze_vorhanden": sorted(abs_map)}
        # Einabsaetzige Norm (§ 45 WEG, § 667 BGB tragen keine "(1)"-Marke).
        # Hier ist der Paragraphenkopf die richtige Stelle -- aber der ECHTE,
        # nicht der aus der Seitenkopfzeile. Unterscheidbar sind sie daran,
        # dass im Seitenkopf direkt das Gesetzeskuerzel folgt ("§ 45 WEG -
        # Einzelnorm"), im Normtext dagegen die Ueberschrift ("§ 45 Fristen
        # der Anfechtungsklage").
        echt = _echter_paragrafenkopf(text, stelle) or kopf
        return {"gefunden": True, "ebene": "paragraf",
                "suchtext": _knapp(text[echt.start():echt.start() + 200]),
                "absaetze_vorhanden": []}
    if not abs_map:
        return {"gefunden": False,
                "grund": "Das Dokument gliedert keine Absaetze, die Stelle ist nicht eingrenzbar.",
                "absaetze_vorhanden": []}
    if stelle.absatz not in abs_map:
        return {"gefunden": False,
                "grund": f"Absatz {stelle.absatz} gibt es hier nicht.",
                "absaetze_vorhanden": sorted(abs_map)}

    absatztext = abs_map[stelle.absatz]

    if stelle.nummer is not None and stelle.satz is None:
        # Nummern sind die Ebene unter dem Absatz, nicht unter dem Satz --
        # eine Aufzaehlung gehoert typischerweise zu EINEM Satz ("... wenn
        # 1. ..., 2. ..."). Darum hier vor der Satzzerlegung.
        nr = nummer_im_absatz(absatztext, stelle.nummer)
        if nr is None:
            return {"gefunden": False,
                    "grund": f"Nummer {stelle.nummer} steht nicht in Absatz {stelle.absatz}.",
                    "absaetze_vorhanden": sorted(abs_map)}
        return {"gefunden": True, "ebene": "nummer",
                "suchtext": _knapp(nr), "wortlaut": nr,
                "absaetze_vorhanden": sorted(abs_map)}

    if stelle.satz is None:
        return {"gefunden": True, "ebene": "absatz",
                "suchtext": _knapp(absatztext),
                "wortlaut": absatztext,
                "absaetze_vorhanden": sorted(abs_map)}

    s = saetze(absatztext)
    if stelle.satz > len(s):
        return {"gefunden": False,
                "grund": f"Absatz {stelle.absatz} hat {len(s)} Saetze, Satz {stelle.satz} gibt es nicht.",
                "saetze_vorhanden": len(s),
                "absaetze_vorhanden": sorted(abs_map)}

    satztext = s[stelle.satz - 1]
    return {"gefunden": True, "ebene": "satz",
            "suchtext": _knapp(satztext),
            "wortlaut": satztext,
            "saetze_vorhanden": len(s),
            "absaetze_vorhanden": sorted(abs_map)}


def _echter_paragrafenkopf(text: str, stelle: Normstelle) -> re.Match | None:
    """Der Paragraphenkopf im Normtext, nicht der in der Seitenkopfzeile.

    Beide sehen fast gleich aus. Der Unterschied steht direkt dahinter: Die
    Kopfzeile schreibt "§ 45 WEG - Einzelnorm", der Normtext "§ 45 Fristen der
    Anfechtungsklage". Wer den ersten Treffer nimmt, markiert die
    Navigationsleiste.
    """
    for m in re.finditer(rf"§\s*{re.escape(stelle.paragraf)}\b", text):
        danach = text[m.end():m.end() + len(stelle.gesetz) + 3].lstrip()
        if not danach.startswith(stelle.gesetz):
            return m
    return None


def _knapp(t: str, zeichen: int = 60) -> str:
    """Ein Suchtext, der lang genug zum Treffen und kurz genug zum Finden ist.

    An einer Wortgrenze abgeschnitten -- ein halbes Wort findet keine Suche,
    und der Anfang eines Satzes ist der stabilste Teil: Wer spaeter zitiert,
    kuerzt hinten.
    """
    t = t.strip()
    if len(t) <= zeichen:
        return t
    schnitt = t.rfind(" ", 0, zeichen)
    return t[:schnitt if schnitt > zeichen // 2 else zeichen].strip()


def loese(bezeichnung: str, datei: Path) -> dict:
    """Die eine Tuer: Normangabe plus Dokument -> Suchtext oder Begruendung."""
    stelle = zergliedere(bezeichnung)
    if stelle is None:
        return {"gefunden": False, "grund": "In dieser Angabe steht keine erkennbare Norm."}
    if not datei.is_file():
        return {"gefunden": False, "grund": "Das Dokument liegt nicht vor.",
                "norm": str(stelle)}
    e = wortlaut(datei.read_bytes(), stelle)
    e["norm"] = str(stelle)
    e["kennung"] = stelle.kennung
    e["datei"] = str(datei)
    return e


# ─── Selbsttest ───────────────────────────────────────────────────────────

_PROBE = (
    b'<html><head><meta charset="iso-8859-1"></head><body>'
    b'<p>Gesetz \xfcber das Wohnungseigentum (WEG) &#167; 16 &#160; Nutzungen und Kosten</p>'
    b'<p>(1) Erster Satz des ersten Absatzes. Zweiter Satz nach &#167; 47 Abs. 2 der '
    b'Grundbuchordnung. Dritter Satz.</p>'
    b'<p>(2) Die Kosten tragen alle. Die Wohnungseigent&#252;mer k&#246;nnen abweichendes '
    b'beschlie&#223;en.</p>'
    b'<script>var x = "(9) kein Absatz";</script></body></html>'
)


def _selftest() -> int:
    # Zergliedern -- die drei Ebenen und die Buchstaben-Paragraphen.
    z = zergliedere("§ 16 Abs. 2 Satz 2 WEG — abweichende Kostenverteilung")
    assert (z.gesetz, z.paragraf, z.absatz, z.satz) == ("WEG", "16", 2, 2), z
    assert z.kennung == "WEG §16"
    z2 = zergliedere("§ 9b Abs. 1 Satz 3 WEG")
    assert (z2.paragraf, z2.absatz, z2.satz) == ("9b", 1, 3), z2
    assert zergliedere("§ 559a BGB").paragraf == "559a"
    assert zergliedere("§ 28 WEG").absatz is None
    # Gliederungswoerter sind keine Gesetze -- der Fall aus Quelle 33.
    z3 = zergliedere("§ 19 Abs. 2 Nr. 6 WEG — Bestellung eines zertifizierten Verwalters")
    assert (z3.gesetz, z3.paragraf, z3.absatz, z3.nummer) == ("WEG", "19", 2, 6), z3
    assert str(z3) == "§ 19 Abs. 2 Nr. 6 WEG", str(z3)
    for wort in ("Nr.", "Halbs.", "Buchst.", "Ziff."):
        z4 = zergliedere(f"§ 5 Abs. 1 {wort} 2 EStG")
        assert z4 and z4.gesetz == "EStG", (wort, z4)

    # Aufzaehlungsnummern -- und was KEINE ist.
    auf = "Voraussetzung ist, dass 1. ein Beschluss vorliegt; 2. die Frist gewahrt ist; 3. Ende."
    assert nummer_im_absatz(auf, 2).startswith("die Frist"), nummer_im_absatz(auf, 2)
    assert nummer_im_absatz(auf, 9) is None
    # Eine gebrochene Zahl ist kein Aufzaehlungspunkt -- Ziffer danach.
    assert nummer_im_absatz("Der Betrag von 2. 500 Euro ist faellig.", 2) is None
    # Und "12." ist nicht die Nummer 2 -- Ziffer davor.
    assert nummer_im_absatz("Vorschrift 12. der Anlage gilt.", 2) is None
    # Der echte Fall aus § 19 Abs. 2 WEG: die Nummern folgen auf ein KOMMA.
    komma = ("Zur Verwaltung gehoeren insbesondere 1. die Aufstellung einer Hausordnung, "
             "2. die ordnungsmaessige Erhaltung, 3. die angemessene Versicherung.")
    assert nummer_im_absatz(komma, 1).startswith("die Aufstellung"), nummer_im_absatz(komma, 1)
    assert nummer_im_absatz(komma, 2).startswith("die ordnungsmaessige"), nummer_im_absatz(komma, 2)
    assert nummer_im_absatz(komma, 3).startswith("die angemessene")
    assert nummer_im_absatz(komma, 4) is None
    # Negativfall: keine Norm heisst None, nicht ein leeres Objekt.
    assert zergliedere("Rechnung vom 12. Mai") is None
    assert zergliedere("") is None

    # Kodierung wird gelesen, nicht geraten.
    assert kodierung(_PROBE) == "iso-8859-1"
    assert kodierung(b"<html>ohne Angabe, reines ASCII</html>") == "utf-8"

    t = text_aus_html(_PROBE)
    assert "Wohnungseigentum" in t and "über" in t, t[:80]
    # Skript darf nicht als Text durchkommen -- sonst zaehlt "(9)" als Absatz.
    assert "var x" not in t

    a = absaetze(t)
    assert sorted(a) == [1, 2], sorted(a)
    assert a[2].startswith("Die Kosten tragen alle")

    # Satzzerlegung: "Abs." darf keine Satzgrenze erzeugen.
    s1 = saetze(a[1])
    assert len(s1) == 3, s1
    assert "Grundbuchordnung" in s1[1] and s1[1].startswith("Zweiter Satz")

    # Die gesuchte Stelle.
    e = wortlaut(_PROBE, Normstelle("WEG", "16", 2, 2))
    assert e["gefunden"] and e["ebene"] == "satz"
    assert e["wortlaut"].startswith("Die Wohnungseigentümer können abweichendes")

    # Absatzebene ohne Satz.
    e = wortlaut(_PROBE, Normstelle("WEG", "16", 2))
    assert e["gefunden"] and e["ebene"] == "absatz"

    # Paragraphenebene ohne Absatz: der Normtext, nicht der Seitenkopf.
    e = wortlaut(_PROBE, Normstelle("WEG", "16"))
    assert e["gefunden"] and e["ebene"] == "paragraf"
    assert e["suchtext"].startswith("Erster Satz"), e["suchtext"]
    assert "Einzelnorm" not in e["suchtext"] and "Inhaltsverzeichnis" not in e["suchtext"]

    # Gesetzesabgleich -- die Probe, die Quelle 11 aufgedeckt hat.
    assert gesetze_im_text("Gesetz über das Wohnungseigentum (WEG) § 16") == {"WEG"}
    # Nur der Anfang zaehlt: ein Verweis weiter hinten macht das Dokument nicht
    # zustaendig, sonst waere die Probe immer bestanden.
    fern = "Titel (WEG) § 16" + " Fuelltext." * 60 + " nach § 47 der GBO und dem EStG"
    assert gesetze_im_text(fern) == {"WEG"}
    e = wortlaut(_PROBE, Normstelle("GModG", "16", 1))
    assert not e["gefunden"] and "WEG" in e["grund"] and "GModG" in e["grund"], e
    # Gegenprobe: das richtige Gesetz kommt weiterhin durch.
    assert wortlaut(_PROBE, Normstelle("WEG", "16", 1))["gefunden"]

    # NEGATIVFAELLE -- der eigentliche Zweck. Nie der naechstbeste Absatz.
    e = wortlaut(_PROBE, Normstelle("WEG", "16", 7))
    assert not e["gefunden"] and "Absatz 7" in e["grund"] and e["absaetze_vorhanden"] == [1, 2]
    e = wortlaut(_PROBE, Normstelle("WEG", "16", 2, 9))
    assert not e["gefunden"] and e["saetze_vorhanden"] == 2
    e = wortlaut(_PROBE, Normstelle("WEG", "99"))
    assert not e["gefunden"] and "§ 99" in e["grund"]
    e = wortlaut(b"<html><body>ohne alles</body></html>", Normstelle("WEG", "16"))
    assert not e["gefunden"]

    # Grenzwert: Satz 1 und der letzte Satz muessen beide gehen.
    assert wortlaut(_PROBE, Normstelle("WEG", "16", 1, 1))["gefunden"]
    assert wortlaut(_PROBE, Normstelle("WEG", "16", 1, 3))["gefunden"]
    assert not wortlaut(_PROBE, Normstelle("WEG", "16", 1, 4))["gefunden"]

    # _knapp schneidet an einer Wortgrenze, nie mitten im Wort.
    lang = "Die Wohnungseigentuemer koennen eine abweichende Verteilung der Kosten beschliessen"
    k = _knapp(lang, 40)
    assert len(k) <= 40 and not lang[len(k):len(k) + 1].isalpha() or k == lang[:len(k)]
    assert " " not in k[-1:], k

    print("normfundstelle: Selbsttest bestanden")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--norm", help='z. B. "§ 16 Abs. 2 Satz 2 WEG"')
    p.add_argument("--datei", type=Path)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        return _selftest()
    if not (a.norm and a.datei):
        p.print_help()
        return 2
    import json
    print(json.dumps(loese(a.norm, a.datei), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
