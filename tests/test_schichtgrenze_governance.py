#!/usr/bin/env python3
"""BDW-R01-AC1: „Eine Boundary-Prüfung ordnet Governance Brainlehr und
Fachlogik Openlehr zu."

ANLASS, 2026-08-18: Die Vermessung aller 42 offenen Produktgates fand für
`BDW-R01` keinen Prüfpfad -- obwohl die Zweischicht seit ADR-007 gilt und
in jedem Plan zitiert wird. Eine Grenze, die niemand prüft, ist eine
Absichtserklärung.

WAS HIER GEPRUEFT WIRD, und die Richtung ist entscheidend:
Es wird nicht geprüft, ob openlehr Governance enthält -- dieses Repo kann
über openlehr nichts aussagen, und ein Test, der ein fremdes Repo liest,
bricht, sobald es umzieht. Geprüft wird die Seite, für die dieses Repo
zuständig ist: **im brainlehr-Kern liegt keine Fachlogik einer Domäne.**

Der Kern trägt, was für JEDE Domäne gilt -- Geltung, Rang, Ausweis,
Freigabe, Abruf, Ablösung. Sobald dort ein Steuersatz, eine Umlagefrist
oder ein Kontenrahmen steht, ist die Grenze gebrochen: dann rechnet der
Kern für eine Domäne mit, und die nächste Domäne erbt Regeln, die für sie
falsch sind.

ABGRENZUNG, ohne die der Test Fehlalarme produziert:
Ein Fachbegriff im ERKLAERENDEN TEXT ist kein Bruch. Der Modulkopf von
`kern/abloesung.py` erklärt die Ablösung am Beispiel einer Hausverwaltung,
und `kern/domaene.py` muss das Wort „Domäne" führen. Beanstandet wird nur
Fachlogik im CODE -- Konstanten, Zuordnungen, Rechenwege.

MUTATIONSPROBE, gefahren 2026-08-18: eine Zeile `UMSATZSTEUER = 0.19` in
`kern/` eingefügt -> Test rot und nennt Datei samt Zeile. Danach entfernt,
grün. Ohne diese Probe wäre unklar, ob der Test die Grenze bewacht oder nur
die heutige Dateiliste beschreibt.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
KERN = WURZEL / "kern"

# Fachbegriffe zweier Domänen dieses Verbunds: Steuer (openlehr) und
# WEG-Verwaltung (buckeberg). Bewusst konkret -- ein allgemeines Wort wie
# „Konto" oder „Frist" träfe den Kern zu Recht, weil er selbst Fristen führt.
FACHBEGRIFFE = re.compile(
    r"(umsatzsteuer|vorsteuer|kleinunternehmer|einkommensteuer|gewerbesteuer"
    r"|elster|eur_rechnung|kontenrahmen|skr\d\d|abschreibung|afa_"
    r"|hausgeld|wohngeld|umlageschluessel|miteigentumsanteil|jahresabrechnung"
    r"|wirtschaftsplan|beschlusssammlung|heizkostenverordnung|weg_paragraf)",
    re.I,
)

# Diese Dateien dürfen Fachbegriffe führen: sie bilden die Naht zur Domäne
# ab, statt selbst zu rechnen. Jede Ausnahme braucht einen Grund -- eine
# wachsende Liste ist selbst der Befund.
NAHTSTELLEN = {
    "domaene.py",       # nimmt Domänenpakete entgegen, prüft ihre Form
    "gattung_filter.py",
}


def _kerndateien() -> list[Path]:
    return sorted(p for p in KERN.glob("*.py") if p.name not in NAHTSTELLEN)


def _codezeilen(pfad: Path) -> list[tuple[int, str]]:
    """Nur echter Code -- Docstrings und Kommentare fallen heraus.

    Ohne diese Trennung schlägt der Test bei jedem erklärenden Beispiel an,
    und ein Wächter mit Fehlalarmen wird abgeschaltet statt gelesen."""
    quelle = pfad.read_text(encoding="utf-8")
    zeilen = quelle.splitlines()
    docstring_zeilen: set[int] = set()
    try:
        baum = ast.parse(quelle)
    except SyntaxError:
        return [(i, z) for i, z in enumerate(zeilen, 1) if not z.strip().startswith("#")]
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Expr) and isinstance(knoten.value, ast.Constant) \
                and isinstance(knoten.value.value, str):
            docstring_zeilen.update(range(knoten.lineno, (knoten.end_lineno or knoten.lineno) + 1))
        # Selbsttest- und Kulissenfunktionen tragen BEISPIELDATEN, keine
        # Fachlogik. Beim ersten Lauf schlug der Test auf
        # kern/abloesung.py::_selftest an, wo eine abgeloeste Hausverwaltung
        # als Beispiel dient ("Jahresabrechnung dreimal verspaetet") -- das
        # ist der Gegenstand des Tests, nicht eine Regel des Kerns.
        if isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                "selftest" in knoten.name or "demo" in knoten.name
                or "kulisse" in knoten.name or knoten.name.startswith("_beispiel")):
            docstring_zeilen.update(range(knoten.lineno, (knoten.end_lineno or knoten.lineno) + 1))
    return [(i, z) for i, z in enumerate(zeilen, 1)
            if i not in docstring_zeilen and not z.strip().startswith("#")]


def test_kern_traegt_keine_domaenenfachlogik():
    """DAS AC. Der Kern gilt für jede Domäne -- also darf keine in ihm stehen."""
    funde = []
    for pfad in _kerndateien():
        for nr, zeile in _codezeilen(pfad):
            treffer = FACHBEGRIFFE.search(zeile)
            if treffer:
                funde.append(f"{pfad.relative_to(WURZEL)}:{nr}: {treffer.group(0)} -- {zeile.strip()[:80]}")
    assert not funde, (
        "Fachlogik einer Domäne im brainlehr-Kern (ADR-007, BDW-R01):\n  "
        + "\n  ".join(funde)
        + "\n\nDer Kern trägt, was für JEDE Domäne gilt. Sobald dort ein Steuersatz oder "
          "eine Umlageregel steht, erbt die nächste Domäne Regeln, die für sie falsch sind. "
          "Gehört in das Domänenpaket, nicht hierher."
    )


def test_kern_traegt_die_governance_selbst():
    """Gegenrichtung, und ohne sie ist der Test oben wertlos: Ein leerer Kern
    bestünde ihn auch. Die Governance-Bausteine MUESSEN hier liegen."""
    erwartet = {
        "ausweis.py": "wer fragt",
        "abloesung.py": "was ist überholt",
        "gegenstand.py": "wie hieß es früher",
        "normbestand.py": "welche Norm gilt",
    }
    fehlend = [f"{name} ({zweck})" for name, zweck in erwartet.items()
               if not (KERN / name).exists()]
    assert not fehlend, (
        "Governance-Bausteine fehlen im Kern -- dann trägt brainlehr seine eigene "
        "Schicht nicht: " + ", ".join(fehlend))


def test_pruefung_findet_ueberhaupt_etwas():
    """Positivkontrolle. Ohne sie wäre der Test oben grün, weil der
    Regulärausdruck nichts findet -- grün aus dem falschen Grund."""
    assert _kerndateien(), "keine Kerndateien gefunden -- Pfad prüfen"
    assert FACHBEGRIFFE.search("UMSATZSTEUER = 0.19")
    assert FACHBEGRIFFE.search("if umlageschluessel == 'mea':")
    assert not FACHBEGRIFFE.search("def geltung(rang, gilt_bis):")


def test_erklaerung_und_beispieldaten_schlagen_nicht_an():
    """Die Abgrenzung, ohne die der Test Fehlalarme produziert -- und sie hat
    beim ersten Lauf sofort zugeschlagen: kern/abloesung.py erklärt die
    Ablösung am Beispiel einer Hausverwaltung (Modulkopf) UND benutzt sie als
    Testfall in _selftest(). Beides ist der Gegenstand, nicht eine Regel des
    Kerns. Erklärender Text und Selbsttestdaten sind ausgenommen, echter Code
    nicht."""
    quelle = KERN / "abloesung.py"
    assert quelle.exists()
    assert FACHBEGRIFFE.search(quelle.read_text(encoding="utf-8")), (
        "Beispiel verschwunden -- dann prüft dieser Test die Abgrenzung nicht mehr")
    im_code = [z for _, z in _codezeilen(quelle) if FACHBEGRIFFE.search(z)]
    assert not im_code, f"unerwartet im Code statt in Erklärung/Beispiel: {im_code}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
