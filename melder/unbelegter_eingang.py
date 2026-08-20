#!/usr/bin/env python3
"""Ein entfernter/ersetzter Eingang wird an seinen Konsumenten unbelegt weiter behauptet.

ANLASS: `L-bbd7fb`, vier belegte Vorkommen (`docs/LEHREN_MECHANISMUS_PRUEFUNG_2026-08-20.md`,
Abschnitt "L-bbd7fb"). Ein Wert, der fehlt oder unvollstaendig ist, wird durch
einen neutralen Fuellwert ersetzt oder ein Teilurteil einfach ausgelassen --
und die Ausgabe behauptet danach weiterhin ungebrochene Genauigkeit bzw.
Vollstaendigkeit.

Der Bericht wertet vier Vorkommen einzeln aus und kommt zu einem geteilten
Urteil: zwei Bauformen sind strukturell fangbar, eine dritte nicht. Dieses
Modul setzt NUR die zwei mechanisierbar beurteilten Klassen um:

  KLASSE 1 "signatur_fallback" (Fund B, RadarNormalizer; Fund C, room_risk):
    ein neutraler Fuellwert (Signatur `?? 0.5`) ersetzt eine fehlende
    Teilgroesse in einem Verbund/Komposit-Score, UND derselbe Bereich meldet
    `isEstimated: false` -- behauptet also unveraendert eine belastbare
    Messung, obwohl ein Teil davon geraten ist.

  KLASSE 2 "unvollstaendiges_aggregat" (Fund A, ampel_config.dart):
    ein Aggregat mit optionalen Teilurteilen (`if (has...)`-Gates vor einem
    Rangfolgen-/Status-Ergebnis) kennt keinen eigenen Zustand fuer
    "Datengrundlage unvollstaendig" -- faellt bei fehlendem Teilurteil also
    lautlos auf das naechst schwaechere VORHANDENE Urteil zurueck, statt das
    als eigenen Zustand auszuweisen.

AUSDRUECKLICH NICHT GEPRUEFT: Fund D (TrendsScreen/HistoryScreen, ein
`??`-Fallback zwischen zwei fachlich verschiedenen, aber gleich skalierten
Feldern wie Wandoberflaechenfeuchte und Raumluftfeuchte). Der Bericht stuft
das als nicht mechanisierbar ein: die Erkennung braucht eine Liste fachlich
nicht austauschbarer, gleich skalierter Feldpaare, die aus der Domaene
(Bauphysik) folgt und im Code nirgends steht -- ein neues, zu pflegendes
Artefakt, kein Struktursignal. Ein generischer Grep faende hier nur Rauschen
(jeder `??`-Fallback zwischen zwei Zahlen saehe gleich aus).

Grenze wie bei rotprobe.py: dieses Modul urteilt nicht ueber die fachliche
Richtigkeit, es verlangt nur, dass die Struktur nicht lautlos vorkommt.

    python3 melder/unbelegter_eingang.py --selftest
    python3 melder/unbelegter_eingang.py --pruefe-verlauf [--wurzel <pfad>]
    python3 melder/unbelegter_eingang.py --pruefe-bestand [--wurzel <pfad>]  # exit 1 bei Fund

Abschaltbar ueber BRAINLEHR_UNBELEGTER_EINGANG=aus (wirkt auf --pruefe-bestand).
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "kern")]
import rueckwirkung  # noqa: E402

# ponytail: reines Regex-Struktursignal, kein AST. Deckt Dart/JS/TS-Syntax
# (`?? 0.5`, `if (has...)`) ab, faengt Python-Aequivalente (`or 0.5`,
# `.get(x, 0.5)`) nicht. Erweitern, wenn ein Fund in anderer Syntax auftaucht.
_ENDUNGEN = (".dart", ".ts", ".tsx", ".js", ".jsx")
_AUSGENOMMEN = {"node_modules", ".git", "build", ".dart_tool", "dist", ".venv"}

_FALLBACK_0_5 = re.compile(r"\?\?\s*0?\.5\b")
_ESTIMATED_FALSE = re.compile(r"isEstimated\s*[:=]\s*false", re.I)
_HAS_GATE = re.compile(r"if\s*\(\s*has\w+\s*\)", re.I)
_AGGREGAT_HINWEIS = re.compile(
    r"\b(switch\s*\(|Rangfolge|Ampel\w*|overallStatus|riskScore|RiskScore)\b")
_UNVOLLSTAENDIG_ZUSTAND = re.compile(
    r"\b(gray|grau|incomplete|unvollst(ä|ae)ndig|unbekannt|unknown|undetermined)\b",
    re.I)


def signatur_fallback(text: str) -> bool:
    """Klasse 1: neutraler Fuellwert 0.5 UND unveraendert 'isEstimated: false'."""
    return bool(_FALLBACK_0_5.search(text)) and bool(_ESTIMATED_FALSE.search(text))


# ponytail: Fenster statt Funktionsgrenzen -- kein Parser im Haus, der
# Klammerblöcke sauber trennt. 30 Zeilen deckt Fund A (Gate und Rangfolge im
# selben kurzen Funktionskoerper); ein grosses File mit unabhaengigem
# Gate+Switch ausserhalb des Fensters faellt dadurch NICHT mehr rein (per
# Stichprobe gemessen: 06-08-20, siehe Docstring-Fussnote unten).
_FENSTER = 30


def unvollstaendiges_aggregat(text: str) -> bool:
    """Klasse 2: bedingte Teilurteile NAHE einem Rangfolgen-Aggregat, ohne
    einen eigenen Zustand fuer unvollstaendige Datengrundlage in derselben
    Umgebung. Geprueft je Fenster um ein `if (has...)`-Gate, nicht ueber die
    ganze Datei -- ein Gate und ein voellig unverwandter `switch` 800 Zeilen
    weiter unten in derselben Datei sind kein Fund (Stichprobe 2026-08-20:
    genau dieser Fall in wohlair/lib/.../bauphysik_cards.dart war mit
    datei-weiter Pruefung ein Fehlalarm, `if (hasSavings)` vs. unabhaengigem
    UI-`switch`)."""
    zeilen = text.splitlines()
    for i, z in enumerate(zeilen):
        if not _HAS_GATE.search(z):
            continue
        fenster = "\n".join(zeilen[max(0, i - _FENSTER):i + _FENSTER])
        if _AGGREGAT_HINWEIS.search(fenster) and not _UNVOLLSTAENDIG_ZUSTAND.search(fenster):
            return True
    return False


def pruefe_text(pfad: str, text: str) -> list[str]:
    """Ein Text -> Liste der Befundzeilen (leer, wenn nichts gefunden)."""
    funde = []
    if signatur_fallback(text):
        funde.append(
            f"{pfad}: Klasse 1 (Signatur-Fallback) -- Fuellwert `?? 0.5` und "
            "`isEstimated: false' im selben Text. Prueft der Fallback-Zweig "
            "das Ergebnis als geschaetzt, oder wird ungebrochene Genauigkeit "
            "behauptet? (L-bbd7fb, Fund B/C)")
    if unvollstaendiges_aggregat(text):
        funde.append(
            f"{pfad}: Klasse 2 (unvollstaendiges Aggregat) -- `if (has...)`-"
            "Gates vor einem Rangfolgen-/Status-Ergebnis, aber kein "
            "'unvollstaendig'/'unbekannt'/'gray'-Zustand im Text. Faellt das "
            "Aggregat bei fehlendem Teilurteil lautlos auf das naechst "
            "schwaechere VORHANDENE Urteil zurueck? (L-bbd7fb, Fund A)")
    return funde


def _quelldateien(wurzel: Path):
    for p in wurzel.rglob("*"):
        if not p.is_file() or p.suffix not in _ENDUNGEN:
            continue
        if _AUSGENOMMEN & set(p.parts):
            continue
        yield p


def _lies(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _repo_wurzel() -> Path:
    w = Path(__file__).resolve().parent
    while not (w / "schema.sql").exists() and w != w.parent:
        w = w.parent
    return w


def _aus() -> bool:
    return os.environ.get("BRAINLEHR_UNBELEGTER_EINGANG", "").strip().lower() == "aus"


def _pruefe_bestand(wurzel: Path) -> tuple[list[str], int]:
    dateien = list(_quelldateien(wurzel))
    funde: list[str] = []
    for p in dateien:
        funde.extend(pruefe_text(str(p.relative_to(wurzel)), _lies(p)))
    return funde, len(dateien)


def _verlauf(wurzel: Path) -> int:
    dateien = list(_quelldateien(wurzel))
    rahmen = (f"ueber {len(dateien)} Quelldateien ({', '.join(_ENDUNGEN)}) unter "
              f"{wurzel}, node_modules/build/.git ausgeklammert")

    b1 = rueckwirkung.zaehle(dateien, lambda p: signatur_fallback(_lies(p)),
                              lambda p: str(p.relative_to(wurzel)))
    rueckwirkung.bericht("Klasse 1 (Signatur-Fallback)", b1, rahmen)

    b2 = rueckwirkung.zaehle(dateien, lambda p: unvollstaendiges_aggregat(_lies(p)),
                              lambda p: str(p.relative_to(wurzel)))
    rueckwirkung.bericht("Klasse 2 (unvollstaendiges Aggregat)", b2, rahmen)
    return 0


def _selftest() -> int:
    # -- Klasse 1: zwei POSITIVFAELLE --
    pos1a = """
    double _normalizeSurface(Reading r) {
      final teil = r.surface ?? 0.5;
      final achse = (teil + r.raum + r.wand) / 3;
      return Achswert(achse, isEstimated: false);
    }
    """
    assert signatur_fallback(pos1a)
    pos1b = "score = fehlt ?? 0.5; result.isEstimated = false;"
    assert signatur_fallback(pos1b)

    # -- Klasse 1: zwei NEGATIVFAELLE --
    # a) Fuellwert vorhanden, aber als geschaetzt ausgewiesen -> kein Fund.
    neg1a = "score = fehlt ?? 0.5; result.isEstimated = true;"
    assert not signatur_fallback(neg1a)
    # b) 'isEstimated: false' vorhanden, aber kein 0.5-Fuellwert -> kein Fund.
    neg1b = "return Achswert(gemessen, isEstimated: false);"
    assert not signatur_fallback(neg1b)

    # -- Klasse 2: zwei POSITIVFAELLE --
    pos2a = """
    AmpelStatus overallAmpelConfigured(Room r) {
      var status = AmpelStatus.green;
      if (hasIrData) { status = combine(status, irUrteil); }
      if (hasHumidity) { status = combine(status, humidityUrteil); }
      return switch (status) { _ => status };
    }
    """
    assert unvollstaendiges_aggregat(pos2a)
    pos2b = "if (hasSensor) x = riskScore(a); overallStatus = rangfolge(x);"
    assert unvollstaendiges_aggregat(pos2b)

    # -- Klasse 2: zwei NEGATIVFAELLE --
    # a) derselbe Aufbau, aber mit explizitem Unvollstaendig-Zustand -> kein Fund.
    neg2a = pos2a.replace(
        "return switch (status) { _ => status };",
        "if (!hasIrData) return AmpelStatus.gray; return switch (status) { _ => status };")
    assert not unvollstaendiges_aggregat(neg2a)
    # b) 'if (has...)'-Gate ohne jeden Aggregat-/Rangfolgen-Hinweis -> kein Fund
    #    (reiner Lesezugriff, kein Score/Status/Switch in der Naehe).
    neg2b = "if (hasIrData) { logIt(irValue); }"
    assert not unvollstaendiges_aggregat(neg2b)

    # -- AUSDRUECKLICH AUSSEN VOR: Fund D (Feldpaar-Vermischung) darf NICHT
    #    anschlagen, weder als Klasse 1 noch als Klasse 2 -- das ist die
    #    bewusst ausgelassene dritte Klasse, kein blinder Fleck.
    fund_d = "double val(Room r) => r.correctedRhPct ?? r.surfaceRhPct;"
    assert not signatur_fallback(fund_d)
    assert not unvollstaendiges_aggregat(fund_d)

    # -- pruefe_text buendelt beide Klassen --
    assert len(pruefe_text("x.dart", pos1a)) == 1
    assert pruefe_text("x.dart", neg1a) == []

    # -- Schalter wirkt --
    os.environ["BRAINLEHR_UNBELEGTER_EINGANG"] = "aus"
    assert _aus() is True
    del os.environ["BRAINLEHR_UNBELEGTER_EINGANG"]
    assert _aus() is False

    print("unbelegter_eingang: Selbsttest gruen (8 Faelle: Klasse 1 zwei "
          "Positiv-/zwei Negativfaelle, Klasse 2 zwei Positiv-/zwei "
          "Negativfaelle, Fund D bewusst ausgenommen, Schalter wirkt)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()

    wurzel = _repo_wurzel()
    if "--wurzel" in sys.argv:
        i = sys.argv.index("--wurzel")
        if len(sys.argv) > i + 1:
            wurzel = Path(sys.argv[i + 1]).resolve()

    if "--pruefe-verlauf" in sys.argv:
        return _verlauf(wurzel)

    if "--pruefe-bestand" in sys.argv:
        if _aus():
            print("unbelegter_eingang: abgeschaltet (BRAINLEHR_UNBELEGTER_EINGANG=aus)")
            return 0
        funde, n = _pruefe_bestand(wurzel)
        print(f"unbelegter_eingang: {len(funde)} Fund(e) unter {n} Quelldateien")
        for f in funde:
            print("  " + f)
        return 1 if funde else 0

    print(__doc__.strip().splitlines()[-4].strip(), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
