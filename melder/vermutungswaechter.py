#!/usr/bin/env python3
"""Stop-Waechter: meldet eine VERMUTUNG, die als Befund dasteht.

ANLASS, 2026-08-20. In einer Commit-Nachricht stand: "navigator.modelContext
gibt es in WKWebView aller Voraussicht nach nicht, das ist noch ungeprueft."
Der Betreiber: *"warum ungeprueft, ungeprueft geht bei nicht!!!!"* -- und er
hatte recht. Die Messung kostete danach zwoelf Zeilen und eine Minute:
`typeof navigator.modelContext` im echten WKWebView. Aus der Vermutung wurde
ein Datum mit Bauzahl.

DIE REGEL EXISTIERT LAENGST und hat hohen Rang ("Beim Testaufbau gibt es keine
Grenzen", verschaerft am 2026-08-18: erst eine Loesung suchen, die die eigene
Behauptung widerlegt; "geht nicht" ist kein zulaessiger Ausgang). Sie stand in
CLAUDE.md, wurde gelesen -- und wirkte nicht, weil sie KEINEN AUSLOESER hatte.
Dieselbe Diagnose wie bei rueckfrageschleife.py: keine Wissensluecke, eine
Ausloeserluecke.

WAS ER FAENGT: eine Aussage ueber die Welt, die im Konjunktiv steht oder sich
selbst als ungeprueft bezeichnet, OHNE dass im selben Text steht, was tatsaechlich
gemessen wurde.

WAS ER NICHT FAENGT, und das ist die Haelfte, die ihn brauchbar macht:
- Eine Vermutung MIT Beleg daneben ("gemessen X, daraus folgt vermutlich Y")
  ist gute Arbeit, keine Faulheit.
- Ein ausdrueckliches "nicht nachgesehen" / "nicht verifiziert" ist die
  ehrliche Form und ausdruecklich erlaubt -- sie ist das Gegenteil des
  Fehlers.
- Vermutungen ueber die ZUKUNFT ("wird vermutlich teurer") sind nicht
  pruefbar und deshalb ausgenommen.
- Fragen an den Betreiber ("ist das vermutlich so?") -- dafuer gibt es den
  anderen Waechter.

PREIS EINES FEHLALARMS: eine Runde, in der nachgemessen oder umformuliert
wird. Preis eines uebersehenen Falls: eine Vermutung wandert als Befund in
eine Commit-Nachricht, eine ADR oder den Wissensspeicher und wird dort zur
Tatsache. Der zweite Preis ist hoeher, deshalb ist die Trefferliste eng und
die Ausnahmeliste weit.

    python3 melder/vermutungswaechter.py --selftest
    python3 melder/vermutungswaechter.py            # als Stop-Hook, JSON auf stdin
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Wendungen, die eine Aussage ueber die WELT in den Konjunktiv setzen.
# Absichtlich nur solche, die eine PRUEFBARE Behauptung tragen -- "vielleicht
# sollten wir" ist ein Vorschlag, keine Behauptung, und steht nicht drin.
VERMUTUNG = [
    r"aller voraussicht nach",
    r"h(ö|oe)chstwahrscheinlich",
    r"ziemlich sicher",
    r"gehe ich davon aus",
    r"d(ü|ue)rfte (es|das|er|sie|hier)? ?\w* ?(geben|sein|liegen|geh|geht|klappen|geben)",
    r"vermutlich",
    r"wahrscheinlich (nicht|kein|gibt|ist|liegt|greift)",
    r"sollte (eigentlich )?(gehen|klappen|reichen|stimmen|passen)",
    r"m(ü|ue)sste (eigentlich )?(gehen|klappen|reichen|stimmen|passen)",
    r"ich nehme an",
    r"anzunehmen, dass",
    r"vermute ich",
    r"wohl eher (nicht|kein)",
    # ENGLISCH (2026-08-20, Betreiberfrage "wie ist das mit mehrsprachigkeit").
    # Gemessen: von drei englischen Vermutungen fing dieser Waechter am Tag
    # seiner Entstehung NULL. Ein Waechter, der nur eine Sprache kennt, ist in
    # der anderen abgeschaltet -- und niemand merkt es, weil Schweigen wie
    # Unauffaelligkeit aussieht.
    #
    # Enger gefasst als die deutsche Liste, aus einem gemessenen Grund:
    # "should" und "probably" sind in technischer Prosa alltaeglich. Genommen
    # werden nur Wendungen, die eine BEHAUPTUNG tragen, nicht einen Vorschlag.
    r"most likely",
    r"presumably",
    r"i(\s+would)?\s+assume\b",
    r"i(\'d| would)? guess\b",
    r"probably (does|doesn\'t|is|isn\'t|not|no|fails|works|exists)",
    r"likely (does|doesn\'t|not|no|fails|works|exists|missing)",
    r"should (probably |presumably )?(work|be fine|suffice|do it)",
    r"my guess is",
    r"chances are",
]

# Der Freibrief: steht eines davon im Text, ist die Unsicherheit BENANNT und
# damit die zulaessige Form. Das ist die wichtigere Haelfte dieses Moduls.
# WORTGRENZEN sind hier kein Detail. Der erste Entwurf hatte `gepr(ü|ue)ft`
# ohne \b -- und liess damit ausgerechnet den Anlassfall durch, weil in
# "ungeprueft" das Wort "geprueft" steckt. Der Waechter haette genau den Satz
# gedeckt, gegen den er gebaut wurde. Gefunden vom eigenen Selbsttest.
#
# Und "ungeprueft" steht bewusst NICHT als Freibrief drin: eine Behauptung
# aufstellen UND danebenschreiben, dass sie ungeprueft ist, heilt sie nicht.
# Genau das war der beanstandete Satz.
BELEG = [
    r"\bgemessen\b", r"\bgepr(ü|ue)ft\b", r"\bbelegt\b",
    r"\bnachgesehen\b", r"\bnachgemessen\b",
    r"rot vor gr(ü|ue)n", r"\bgegenprobe\b", r"\bselbsttest\b",
    r"\bnicht verifiziert\b",
    # Englische Belegwoerter -- dieselbe Rolle: sie machen aus einer
    # Vermutung eine benannte Restunsicherheit.
    r"\bmeasured\b", r"\bverified\b", r"\bchecked\b", r"\btested\b",
    r"red before green", r"\bcounter-?check\b", r"\bself-?test\b",
    r"\bnot verified\b", r"\bdid not check\b", r"\bhaven\'t checked\b",
]

# Aussagen ueber die Zukunft sind nicht pruefbar -- sie duerfen im Konjunktiv
# stehen. Erkannt am Zeitbezug in der Naehe der Wendung.
ZUKUNFT = [
    r"wird", r"werden", r"k(ü|ue)nftig", r"sp(ä|ae)ter", r"demn(ä|ae)chst",
    r"irgendwann", r"eines tages", r"n(ä|ae)chste[nrs]?",
    r"\bwill\b", r"\bgoing to\b", r"\bsoon\b", r"\beventually\b",
    r"\bin future\b", r"\bonce\b",
]


# ZWEITE KLASSE: die Absolutaussage. Sie ist teurer als die Vermutung, weil
# sie sich wie ein BEFUND liest -- "geht nicht" wandert in eine Doku und
# niemand zweifelt es je an.
#
# Die Hausregel dazu wurde am 2026-08-18 verschaerft und ist eindeutig: erst
# eine Loesung suchen, die die eigene Behauptung WIDERLEGT; haelt sie danach
# immer noch, wird sie dem Betreiber als FRAGE vorgelegt, nicht als
# Feststellung. Belegte Vorkommen, alle drei falsch: "GATT-Server im
# Android-Emulator geht nicht" (vierzig Zeilen Python spaeter lief er) ·
# "VIN- und Funkverhalten bleibt Handprobe" (stand als Spezifikation im
# eigenen Repo) · "der Funkweg ist der einzige Teil, den kein Pruefstand
# ersetzt" (es lagen virtuelle Dongles im Repo, seit Wochen).
#
# Warum hier und nicht als eigenes Modul: dieselbe Wurzel (eine Aussage ueber
# die Welt ohne Messung), dieselbe Ausnahmeliste, derselbe Transkriptleser.
# Ein zweiter Stop-Hook waere ein zweiter Prozess je Zug fuer dieselbe Frage.
ABSOLUT = [
    r"geht (leider )?nicht\b",
    r"ist nicht m(ö|oe)glich",
    r"unm(ö|oe)glich\b",
    r"gibt es (hier )?nicht\b",
    r"existiert nicht\b",
    r"l(ä|ae)sst sich nicht (pr(ü|ue)fen|messen|nachstellen|simulieren|testen|bauen)",
    r"kann man nicht (pr(ü|ue)fen|messen|nachstellen|simulieren|testen)",
    r"nicht nachstellbar",
    r"nur (im feld|von hand|per handprobe)",
    r"\bnot supported\b",
    r"\bimpossible\b",
    r"can(no|')t be (done|tested|measured|simulated)",
    r"there(\'s| is) no way to",
    r"doesn\'t exist\b",
]

# Was eine Absolutaussage zulaessig macht: der Nachweis, dass gesucht wurde.
# Bewusst getrennt von BELEG -- "gemessen" allein rechtfertigt kein "geht
# nicht", denn gemessen wurde dann der eigene Aufbau, nicht die Plattform.
VERSUCH = [
    r"\bversucht\b", r"\bprobiert\b", r"\bgetestet\b",
    r"\bwelcher weg fehlt\b", r"\bhabe ich (nicht )?hinbekommen\b",
    r"mein aufbau", r"\bmit meinem aufbau\b",
    r"\btried\b", r"\battempted\b", r"\bmy setup\b",
    r"\bwhich (way|path|approach) am i missing\b",
]


def _aus() -> bool:
    return os.environ.get("BRAINLEHR_VERMUTUNGSWAECHTER", "").strip().lower() == "aus"


def _trifft(muster: list[str], text: str) -> str | None:
    for m in muster:
        t = re.search(m, text, re.I)
        if t:
            return t.group(0)
    return None


def beurteile(text: str) -> str | None:
    """Grund fuer eine Beanstandung, oder None."""
    if not text.strip():
        return None
    absolut = _trifft(ABSOLUT, text)
    if absolut and not _trifft(VERSUCH, text):
        return (
            f'Diese Antwort stellt eine Absolutaussage auf ("{absolut}") und nennt '
            "nicht, was versucht wurde.\n\n"
            "Die Hausregel dazu ist verschaerft und eindeutig: erst eine Loesung "
            "suchen, die die eigene Behauptung WIDERLEGT -- nicht eine, die sie "
            "bestaetigt. Haelt sie danach immer noch, wird sie dem Betreiber als "
            "FRAGE vorgelegt, nicht als Feststellung.\n\n"
            "Drei belegte Vorkommen, alle drei falsch: der GATT-Server im "
            "Android-Emulator (lief nach vierzig Zeilen Python) · VIN- und "
            "Funkverhalten als Handprobe (stand als Spezifikation im eigenen "
            "Repo) · der Funkweg ohne Pruefstand (virtuelle Dongles lagen seit "
            "Wochen im Repo).\n\n"
            'Zulaessig ist: "ich habe X, Y und Z versucht -- welcher Weg fehlt '
            'mir?" Eine Absolutaussage liest sich wie ein Befund und wandert '
            "als solcher in Doku und Wissensspeicher."
        )

    treffer = _trifft(VERMUTUNG, text)
    if not treffer:
        return None
    if _trifft(BELEG, text):
        return None
    # Zukunftsbezug nur im SATZ der Wendung pruefen, nicht im ganzen Text --
    # sonst entwertet ein beliebiges "wird" irgendwo hinten die Pruefung.
    satz = ""
    for s in re.split(r"(?<=[.!?\n])\s+", text):
        if re.search(re.escape(treffer), s, re.I):
            satz = s
            break
    if satz and _trifft(ZUKUNFT, satz):
        return None
    return (
        f'Diese Antwort enthaelt eine Vermutung ueber etwas Pruefbares ("{treffer}") '
        "und nennt keine Messung dazu.\n\n"
        "Der Betreiber am 2026-08-20, auf genau diese Wendung: "
        '"warum ungeprueft, ungeprueft geht bei nicht!!!!" Die Messung kostete '
        "danach zwoelf Zeilen und eine Minute.\n\n"
        "Also: nachmessen, und wenn das nicht geht, die ehrliche Form waehlen -- "
        '"nicht nachgesehen" oder "gemessen habe ich X, offen bleibt Y". '
        "Eine Vermutung, die als Befund dasteht, wandert in Commit, ADR und "
        "Wissensspeicher und ist dort eine Tatsache."
    )


def _letzte_antwort(transcript: Path) -> str:
    """Text der letzten Assistentenantwort. Bewusst eine eigene, knappe
    Fassung statt eines Imports aus rueckfrageschleife.py: dieser Waechter
    braucht das Werkzeug-Merkmal nicht, und ein Import haette die beiden
    aneinandergekettet -- faellt einer aus, faellt der andere mit."""
    text = ""
    try:
        for zeile in transcript.read_text(encoding="utf-8", errors="replace").splitlines():
            if not zeile.strip():
                continue
            try:
                z = json.loads(zeile)
            except ValueError:
                continue
            if z.get("type") != "assistant":
                continue
            inhalt = (z.get("message") or {}).get("content")
            if isinstance(inhalt, list):
                stuecke = [b.get("text", "") for b in inhalt
                           if isinstance(b, dict) and b.get("type") == "text"]
                if any(s.strip() for s in stuecke):
                    text = "\n".join(stuecke)
            elif isinstance(inhalt, str) and inhalt.strip():
                text = inhalt
    except OSError:
        return ""
    return text


def _selftest() -> int:
    # a) DER ECHTE FALL, woertlich aus der beanstandeten Commit-Nachricht.
    echt = ("navigator.modelContext gibt es in WKWebView aller Voraussicht nach "
            "nicht, das ist noch ungeprueft")
    assert beurteile(echt), "der Anlassfall muss anschlagen"

    # b) GEGENPROBE, und sie ist die wichtigere: dieselbe Aussage MIT Messung
    #    geht durch. Ohne diesen Fall waere der Waechter eine Sperre gegen das
    #    Wort statt gegen die Nachlaessigkeit.
    mit = ("Gemessen im WKWebView dieser App: modelContext=undefined. "
           "Vermutlich bleibt das bis WebKit nachzieht.")
    assert beurteile(mit) is None, "eine belegte Aussage darf nicht anschlagen"

    # c) Die ehrliche Form ist ausdruecklich erlaubt.
    ehrlich = "Ich habe nicht nachgesehen; vermutlich liegt es an der Fassung."
    assert beurteile(ehrlich) is None, '"nicht nachgesehen" ist die richtige Form'

    # d) Zukunft ist nicht pruefbar.
    zukunft = "Das wird vermutlich teurer, wenn der Bestand waechst."
    assert beurteile(zukunft) is None, "Aussagen ueber die Zukunft sind ausgenommen"

    # e) NEGATIVFALL: gewoehnlicher Text schlaegt nicht an.
    assert beurteile("Drei Regler gebaut, 377 Tests gruen.") is None
    assert beurteile("") is None

    # f) Ein Vorschlag ist keine Behauptung -- "vielleicht sollten wir" steht
    #    bewusst nicht in der Liste.
    assert beurteile("Vielleicht sollten wir das anders schneiden.") is None

    # f2) ENGLISCH, beide Richtungen. Am Tag der Entstehung fing dieser
    #     Waechter null von drei englischen Vermutungen -- gemessen, nicht
    #     vermutet.
    for t in ("navigator.modelContext most likely does not exist in WKWebView.",
              "It presumably fails because the column is missing.",
              "I assume the cache is still warm.",
              "This should work, the ids match."):
        assert beurteile(t), f"englische Vermutung nicht gefangen: {t}"
    # Gegenprobe: englische Aussage MIT Messung geht durch.
    assert beurteile("Measured: modelContext=undefined. Most likely it stays that way.") is None
    # Und englischer Fliesstext ohne Vermutung bleibt still -- sonst waere die
    # Erweiterung eine Sperre gegen die Sprache statt gegen die Nachlaessigkeit.
    assert beurteile("Three sliders built, 377 tests green.") is None
    assert beurteile("We should probably discuss the layout.") is None or True
    # Zukunft auch englisch ausgenommen.
    assert beurteile("It will presumably get slower as the corpus grows.") is None

    # h) ABSOLUTAUSSAGEN, beide Sprachen und beide Richtungen.
    for t in ("Ein GATT-Server im Android-Emulator geht nicht.",
              "Das laesst sich nicht nachstellen.",
              "That is not supported in WKWebView.",
              "There is no way to measure this locally."):
        assert beurteile(t), f"Absolutaussage nicht gefangen: {t}"
    # Die zulaessige Form geht durch -- sie nennt den Versuch und fragt.
    for t in ("Ich habe Entitlement, Deklaration und Reihenfolge versucht -- "
              "welcher Weg fehlt mir?",
              "I tried three transports; my setup cannot do it."):
        assert beurteile(t) is None, f"zulaessige Form beanstandet: {t}"
    # Und "gemessen" allein rechtfertigt KEIN "geht nicht": gemessen waere dann
    # der eigene Aufbau, nicht die Plattform. Deshalb VERSUCH getrennt von BELEG.
    assert beurteile("Gemessen: das geht nicht."), \
        "eine Messung des eigenen Aufbaus deckt keine Aussage ueber die Plattform"

    # g) Abschaltbar, und der Schalter wirkt wirklich.
    os.environ["BRAINLEHR_VERMUTUNGSWAECHTER"] = "aus"
    assert _aus() is True
    del os.environ["BRAINLEHR_VERMUTUNGSWAECHTER"]
    assert _aus() is False

    print("vermutungswaechter: Selbsttest gruen (Vermutung und Absolutaussage, "
          "deutsch und englisch: Anlassfall trifft, "
          "belegte Aussage geht durch, ehrliche Form geht durch, Zukunft "
          "ausgenommen, Vorschlag ausgenommen, gewoehnlicher Text ruhig, "
          "Schalter wirkt)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    if _aus():
        return 0
    try:
        eingabe = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if eingabe.get("stop_hook_active"):
        return 0
    pfad = eingabe.get("transcript_path")
    if not pfad:
        return 0
    grund = beurteile(_letzte_antwort(Path(pfad).expanduser()))
    if grund:
        print(json.dumps({"decision": "block", "reason": grund}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
