#!/usr/bin/env python3
"""zahlenbezug.py -- erkennt, wenn die eigene ANTWORT eine ZAHL aus Annahme
oder Modellwissen traegt, statt aus einer Quelle.

ANLASS (Betreiber, 2026-08-12, Doktrin siehe docs/DOKTRIN_MODELLWISSEN_2026-08-12.md):
Am 2026-08-12 wurde in einer Sitzung eine Temperaturkurve fuer ein Entscheidungs-
dokument MODELLIERT statt gemessen. Wortlaut der spaeteren Selbstauskunft:
"Ich habe die Temperaturkurve modelliert, nicht gemessen. Jahresmittel und
Amplitude stammen aus meinem Modellwissen, gekennzeichnet als Annahme." Auf
Nachfrage stellte sich heraus, dass echte Wetterdaten und Zukunftsprojektionen
frei verfuegbar sind. Es war das ZWEITE Vorkommen derselben Fehlklasse an
diesem Tag (das erste betraf Rechtsnormen, siehe normbezug.py).

DRITTER MELDER DERSELBEN FAMILIE (normbezug.py, existenzpruefung.py): Haken
auf die eigene ANTWORT, gleiche Bauform, gleiche drei Auflagen -- messbar aus
dem Text, benannte Fehlklasse, Preis eines Fehlalarms beziffert. Schweigt,
wenn nichts anschlaegt.

ENTSCHEIDUNG ZUR ERKENNUNG (Auftrag verlangt ausdruecklich eine Begruendung,
keine Vorgabe): Der Hinweis im Auftrag ist zutreffend und wird NICHT verworfen,
sondern bewusst gewaehlt -- mit offen benanntem Preis. In beiden Vorfaellen hat
der Assistent die Annahme SELBST gekennzeichnet ("gekennzeichnet als Annahme",
"aus meinem Modellwissen"). Eine Erkennung an dieser Selbstkennzeichnung hat
kaum Fehlalarme, weil die Signalwoerter selten und spezifisch sind (gemessen an
echtem Sitzungsmaterial, siehe messungen/zahlenbezug_fehlalarm.py). Der Preis:
sie faengt NICHT die gefaehrlicheren Faelle, in denen die Kennzeichnung fehlt --
eine Zahl, selbstbewusst genannt, ohne jeden Vorbehalt. Diese Faelle kann ein
Textmuster nicht von einer echten Quellenangabe unterscheiden, ohne die Quelle
selbst zu pruefen (dieselbe Grenze wie bei normbezug.py: "Es prueft NICHT, ob
eine Aussage richtig ist"). Ein Melder, der auf jede unbelegte Zahl anschlaegt,
waere am echten Material nicht 10, sondern dreistellig Prozent Fehlalarm
(jede Zeilen-, Test- und Datumsangabe ist eine "Zahl ohne Zitat") -- unbrauchbar
nach der eigenen Vorgabe dieses Auftrags.

WAS DAS WERKZEUG NICHT TUT: Es prueft NICHT, ob eine genannte Zahl richtig
oder falsch ist -- das kann kein Programm. Es prueft, ob die Antwort selbst
sagt, dass eine Zahl aus Annahme/Modellwissen statt aus einer Quelle stammt,
und ob in derselben Aussage ueberhaupt eine zahlenwertige Groesse benannt wird
(Kennzahlen wie "Kurve", "Mittelwert", "Amplitude" zaehlen mit, auch ohne
literale Ziffer -- der Ausloesesatz selbst enthaelt keine, siehe Selbsttest).

FEHLKLASSE: unbelegte Zahl aus Modellwissen/Annahme, im Text selbst gekennzeichnet.
PREIS EINES FEHLALARMS: gering -- eine Wiedervorlage zu viel, siehe normbezug.py.
Der umgekehrte Fehler (eine gekennzeichnete Annahme bleibt unbemerkt) ist teurer:
sie geht sonst unveraendert in ein Dokument, das nach aussen geht.

Aufruf:
    python3 zahlenbezug.py --text "..."
    python3 zahlenbezug.py --stop        # Stop-Hook: liest die letzte Antwort
    python3 zahlenbezug.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import json
import re
import sys

# --- Signal: die Antwort kennzeichnet eine Groesse als NICHT aus einer
# Quelle stammend -- eng gefasst, jedes Wort einzeln an echtem Material
# geprueft (siehe messungen/zahlenbezug_fehlalarm.py). Bewusst NICHT dabei:
# blosses "geschaetzt"/"vermutlich"/"angenommen" allein -- diese Woerter
# tragen im Alltag zu oft harmlose Vermutungen ueber Ursachen, nicht ueber
# Zahlen, und haetten die Fehlalarmquote am echten Material ueber die im
# Auftrag genannte Zehn-Prozent-Schwelle getrieben.
_SIGNAL = re.compile(
    r"(?i)\b(modellwissen|gekennzeichnet als annahme|als annahme gekennzeichnet|"
    r"ungeprüfte annahme|ungeprueft(?:e|es)? annahme|nicht gemessen|"
    r"aus (?:meinem|dem) gedächtnis|aus (?:meinem|dem) gedaechtnis|"
    r"aus (?:meiner|der) erinnerung|aus (?:meinen|den) trainingsdaten|"
    r"soweit ich weiß|soweit ich weiss|ohne quelle|über den daumen|"
    r"ueber den daumen|grob geschätzt|grob geschaetzt|schätzungsweise|"
    r"schaetzungsweise)\b")

# --- Zahlenwertige Groesse: eine literale Ziffernfolge ODER ein Wort, das
# eine Kennzahl benennt. Die Wortliste ist noetig, weil der Ausloesesatz des
# Anlassfalls selbst KEINE Ziffer enthaelt ("Jahresmittel und Amplitude
# stammen aus meinem Modellwissen") -- ohne sie wuerde dieser Melder am
# eigenen Anlassfall schweigen. Bewusst OHNE Wortgrenze links: deutsche
# Komposita haengen die Kennzahl an ("Temperaturkurve", "Fehlerquote").
_QUANT = re.compile(
    r"(?i)(\d[\d.,]*\s*%?|kurve|mittelwert|durchschnitt|amplitude|"
    r"jahresmittel|kennzahl|quote\b|rate\b|prozent|anteil\b|betrag\b|"
    r"kosten\b|preis\b|menge\b|anzahl\b|wert\b|schätzwert|schaetzwert|"
    r"spanne\b|bandbreite\b)")

# Woran sich der naechste Schritt orientiert: freie amtliche Quellen fuer
# die haeufigsten Groessenarten. Anlassfall Wetter/Klima zuerst, weil er der
# Ausloeser war; die uebrigen sind die naechstliegenden Nachbarfaelle
# (Betreiber-Auftrag laesst offen, ob eine Liste sinnvoll ist -- hier bewusst
# JA, weil "geh nachschlagen" ohne Angabe WO wieder in Modellwissen ("ich
# glaube da gibt es sowas") abgleiten wuerde, derselbe Fehler auf einer
# Ebene hoeher).
_QUELLEN_HINWEIS = (
    "je nach Groesse gibt es eine freie amtliche Quelle statt Modellwissen: "
    "Wetter/Klima -> DWD Open Data, Copernicus/C3S; Wirtschaft/Bevoelkerung "
    "-> Destatis, Eurostat; Recht -> gesetze-im-internet.de, EUR-Lex "
    "(siehe normbezug.py). Dort nachschlagen, dann die Zahl mit Datum und "
    "Quelle im Text ersetzen."
)


def _saetze(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", text or "") if s.strip()]


def treffer(text: str) -> list[str]:
    """Saetze der Antwort, die eine Zahl/Kennzahl als aus Annahme oder
    Modellwissen stammend kennzeichnen. Ein Satz je Treffer, dublettenfrei,
    in Reihenfolge des Auftretens."""
    gefunden: list[str] = []
    for satz in _saetze(text):
        if satz in gefunden:
            continue
        if _SIGNAL.search(satz) and _QUANT.search(satz):
            gefunden.append(satz)
    return gefunden


def melde(befunde: list[str]) -> str:
    """Text fuer den Stop-Hook. Leer, wenn nichts anschlaegt -- ein Melder,
    der auch bei Ordnung spricht, wird nach drei Tagen uebergangen."""
    if not befunde:
        return ""
    zeilen = ["ZAHL AUS ANNAHME/MODELLWISSEN — kein Beleg aus einer Quelle:"]
    for satz in befunde:
        kurz = satz if len(satz) <= 160 else satz[:157] + "..."
        zeilen.append(f'  "{kurz}"')
    zeilen.append(f"  -> {_QUELLEN_HINWEIS}")
    return "\n".join(zeilen)


def pruefe(text: str) -> str:
    return melde(treffer(text))


# --- Selbsttest --------------------------------------------------------------

def _selftest() -> None:
    # --- POSITIVKONTROLLE: der echte Anlassfall, woertlich -----------------
    anlass = ("Ich habe die Temperaturkurve modelliert, nicht gemessen. "
              "Jahresmittel und Amplitude stammen aus meinem Modellwissen, "
              "gekennzeichnet als Annahme.")
    t = treffer(anlass)
    assert t, "Anlassfall nicht erkannt -- Positivkontrolle gescheitert"
    assert any("Temperaturkurve" in s for s in t), t
    m = melde(t)
    assert "ZAHL AUS ANNAHME/MODELLWISSEN" in m and "DWD" in m, m

    # --- NEGATIVFALL: Zahlen AUS einer Quelle loesen NICHTS aus -------------
    quelle = ("Ausgangslage 2026-08-12T12:00, selbst gemessen: 863 passed, "
              "1 skipped, 7 xfailed, 0 failed.")
    assert treffer(quelle) == [], treffer(quelle)

    laut_quelle = "Laut DWD lag das Jahresmittel 2025 bei 10,3 Grad."
    assert treffer(laut_quelle) == [], treffer(laut_quelle)

    # --- Grenzfaelle: nur Signal ODER nur Quant loest nichts aus -----------
    nur_signal = "Das ist ungepruefte Annahme, aber es geht um keine Groesse."
    assert treffer(nur_signal) == [], treffer(nur_signal)

    nur_quant = "Der Mittelwert liegt laut Messreihe bei 4,2."
    assert treffer(nur_quant) == [], treffer(nur_quant)

    # --- gewoehnlicher Text loest nichts aus --------------------------------
    harmlos = "Der Test ist gruen. Die Funktion tut, was sie soll."
    assert treffer(harmlos) == [], treffer(harmlos)

    # --- Dublettenfrei: derselbe Satz zweimal im Text -> ein Treffer -------
    doppelt = anlass + " " + anlass
    assert len(treffer(doppelt)) == len(set(treffer(doppelt)))

    # --- Meldung schweigt bei Ordnung ---------------------------------------
    assert melde([]) == ""

    print("zahlenbezug.py: Selbsttest gruen")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--text")
    p.add_argument("--stop", action="store_true",
                   help="Stop-Hook: liest die letzte Antwort aus stdin (JSON)")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()

    if args.selftest:
        _selftest()
        return 0

    text = args.text
    if args.stop and not text:
        try:
            text = json.load(sys.stdin).get("text", "")
        except (json.JSONDecodeError, ValueError):
            return 0
    if not text:
        p.error("--text oder --stop mit JSON auf stdin")

    meldung = pruefe(text)
    if meldung:
        print(meldung)
        return 1
    print("zahlenbezug: keine unbelegte Zahl aus Annahme/Modellwissen erkannt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
