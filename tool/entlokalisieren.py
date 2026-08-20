#!/usr/bin/env python3
"""Nimmt Heimatpfade und Verbundnamen aus Kommentaren und Docstrings.

DER BEFUND (brainlehr 2026-08-20, erster vollstaendiger oeffentlicher
Export): 144 von 731 Dateien scheiterten am Pruefer des oeffentlichen Repos --
`absolute-path` oder `private-context`. Nachgesehen war es fast durchweg
ERKLAERTEXT: "/Users/<name>/..." in einem Kommentar, "Begod2026" in einem
Docstring. Kein Geheimnis, aber die Verzeichnisstruktur und Nomenklatur des
Betreibers, und der Pruefer beanstandet sie zu Recht.

WARUM DAS MEHR IST ALS KOSMETIK: Eine einzige solche Zeile -- ein Pfad in
einem Fixture-String in kern/normrang.py -- blockierte ueber
knowledge_mcp_server und tests/conftest.py den GESAMTEN Testlauf des Exports.
27 Sammelfehler aus einem Erklaertext. Die Abhaengigkeitskette macht aus einem
kosmetischen Mangel einen totalen Ausfall.

DIE GRENZE IST DER GANZE PUNKT, und sie wird nicht verschoben:

    Kommentar    wird nie ausgewertet          -> ersetzen
    Docstring    wird nur gelesen              -> ersetzen
    Code         kann Verhalten tragen         -> MELDEN, nicht anfassen

Ein Pfad in ausgewertetem Code stillschweigend zu ersetzen macht aus einem
Befund eine Retusche: Der Export liefe dann anders als das Original, und
niemand wuesste es. Solche Stellen werden mit Zeilennummer aufgelistet und
von Hand entschieden -- so geschehen bei kern/normrang.py, wo der Selbsttest
danach gruen lief und damit belegte, dass der Pfad wirklich Fixture war.

Die Ersetzungstabelle ist NICHT nachgebaut, sondern aus pflege/export_offen.py
importiert: Zwei Kopien einer Regel driften auseinander, und dann entlokalisiert
der Quelltext anders als der Auszug.

Aufruf:
    python3 tool/entlokalisieren.py            # nur zeigen
    python3 tool/entlokalisieren.py --schreiben
"""
from __future__ import annotations

import argparse
import ast
import io
import sys
import tokenize
from pathlib import Path

_w = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(_w), str(_w / "pflege")]

from export_offen import ENTLOKALISIERUNG  # noqa: E402

REPO = _w


def _ersetze(text: str) -> str:
    for rx, ersatz in ENTLOKALISIERUNG:
        text = rx.sub(ersatz, text)
    return text


def _trifft(text: str) -> bool:
    return any(rx.search(text) for rx, _ in ENTLOKALISIERUNG)


def _docstring_bereiche(baum) -> set:
    """Zeilenbereiche aller Docstrings (Modul, Klasse, Funktion).

    Ueber ast statt ueber tokenize, weil nur ast weiss, WELCHE Zeichenkette
    an Docstring-Position steht -- ein STRING-Token allein sagt das nicht."""
    raus = set()
    for knoten in ast.walk(baum):
        if not isinstance(knoten, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                   ast.AsyncFunctionDef)):
            continue
        leib = getattr(knoten, "body", None)
        if not leib:
            continue
        erst = leib[0]
        if (isinstance(erst, ast.Expr) and isinstance(erst.value, ast.Constant)
                and isinstance(erst.value.value, str)):
            raus.update(range(erst.lineno, (erst.end_lineno or erst.lineno) + 1))
    return raus


def bearbeite(quelle: str):
    """(neuer_text, [(zeile, fundstelle), ...]) -- oder (None, []) bei Syntaxfehler.

    Der Syntaxfehler ist bewusst ein Totalausfall und keine Teilbearbeitung:
    ohne Parsebaum ist nicht entscheidbar, was Docstring und was Code ist, und
    eine halb entlokalisierte Datei waere schlimmer als eine unbearbeitete."""
    try:
        baum = ast.parse(quelle)
        marken = list(tokenize.generate_tokens(io.StringIO(quelle).readline))
    except (SyntaxError, tokenize.TokenError, IndentationError):
        return None, []

    doku = _docstring_bereiche(baum)
    zeilen = quelle.splitlines(keepends=True)
    aendern, rest = [], []
    for tok in marken:
        if not _trifft(tok.string):
            continue
        if tok.type == tokenize.COMMENT or (
                tok.type == tokenize.STRING and tok.start[0] in doku):
            aendern.append(tok)
        elif tok.type == tokenize.STRING:
            rest.append((tok.start[0], tok.string.strip()[:80]))

    for tok in reversed(aendern):
        (z, a), (z2, e) = tok.start, tok.end
        if z == z2:
            zeilen[z-1] = zeilen[z-1][:a] + _ersetze(tok.string) + zeilen[z-1][e:]
        else:  # mehrzeiliger Docstring
            ganz = "".join(zeilen[z-1:z2])
            vorn, hinten = zeilen[z-1][:a], zeilen[z2-1][e:]
            kern = ganz[len(vorn):len(ganz)-len(hinten)] if hinten else ganz[len(vorn):]
            zeilen[z-1:z2] = [vorn + _ersetze(kern) + hinten]
    return "".join(zeilen), rest


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--schreiben", action="store_true")
    p.add_argument("ordner", nargs="*", default=["kern", "melder", "haken", "tests",
                                                 "tool", "pflege", "berichte",
                                                 "migrationen", "schreibpruefstand"])
    args = p.parse_args()

    geaendert, offen, kaputt = 0, [], 0
    for ordner in args.ordner:
        wurzel = REPO / ordner
        pfade = [wurzel] if wurzel.is_file() else sorted(wurzel.rglob("*.py"))
        for datei in pfade:
            quelle = datei.read_text(encoding="utf-8", errors="strict")
            neu, rest = bearbeite(quelle)
            if neu is None:
                kaputt += 1
                continue
            if neu != quelle:
                geaendert += 1
                if args.schreiben:
                    datei.write_text(neu, encoding="utf-8")
            for z, txt in rest:
                offen.append((str(datei.relative_to(REPO)), z, txt))

    wort = "geaendert" if args.schreiben else "waeren zu aendern"
    print(f"{geaendert} Datei(en) {wort} (Kommentare und Docstrings)")
    if kaputt:
        print(f"{kaputt} Datei(en) nicht parsebar -- unangetastet gelassen")
    print(f"\n{len(offen)} Fundstelle(n) in AUSGEWERTETEM Code -- von Hand "
          f"entscheiden, nicht automatisch ersetzen:")
    for rel, z, txt in offen[:25]:
        print(f"  {rel}:{z}  {txt}")
    if len(offen) > 25:
        print(f"  ... und {len(offen)-25} weitere")
    return 0


if __name__ == "__main__":
    sys.exit(main())
