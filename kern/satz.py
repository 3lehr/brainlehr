#!/usr/bin/env python3
"""Der Satzweg: aus einem Dokument (`kern/dokument.py`) wird LaTeX-Quelle.

Vorspann ist WOERTLICH aus `spikes/pdf_a3_erechnung/rechnung.tex` uebernommen
(dort gemessen: verapdf -f ua1 PASS und -f 3u PASS auf derselben Datei) --
kein neuer Vorspann, um die belegten Eigenschaften (PDF/A-3, PDF/UA) nicht zu
verlieren.

KENNUNG IM BLATT: jeder Baustein bekommt eine \\label{bau:<kennung>} VOR
seinem Inhalt. Alternative waere ein reiner Kommentar (%-Zeile) gewesen --
verworfen, weil ein Kommentar im PDF selbst nicht mehr auffindbar ist,
waehrend ein \\label spaeter per \\ref/\\pageref oder per PDF-Struktur
(Tagging ist ohnehin an, s.o.) auf die Seite zurueckfuehrt. WAS DAS NICHT
KANN: ein Label zeigt auf die SEITE, nicht auf die exakte Zeichenposition
innerhalb eines Absatzes -- fuer "welcher Baustein ist das" reicht es, fuer
"welches Zeichen im Baustein" nicht.

MASKIERUNG: Nutzertext kann \\, {, }, $, &, %, # enthalten (z.B. aus einem
eingelesenen Beleg) und darf den Satzlauf nicht brechen oder etwas
ausfuehren lassen. `\\` muss zuerst maskiert werden, sonst maskiert die
Maskierung selbst sich kaputt.

Aufruf:  python3 kern/satz.py --selftest
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dokument import bausteine_baum, sprache  # noqa: E402

VORSPANN = r"""\DocumentMetadata{
  pdfversion=1.7,
  pdfstandard={A-3U,UA-1},
  lang=SPRACHE,
  tagging=on,
  testphase={phase-III,math,table,bookmarks}
}
\documentclass{article}
\usepackage{fontspec}
\usepackage{hyperref}
\hypersetup{pdftitle={TITEL},pdflang={SPRACHE}}

\begin{document}
"""

NACHSPANN = r"""\end{document}
"""

# EIN Durchlauf ueber die Zeichen, nicht sequentielles str.replace(): sonst
# wuerde die Ersetzung von "\" (die selbst { und } einfuehrt) von der
# nachfolgenden Ersetzung von "{"/"}" nochmal erwischt und kaputt-maskiert.
_MASKEN = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "%": r"\%",
    "#": r"\#",
    "_": r"\_",
    "^": r"\^{}",
    "~": r"\~{}",
}


def maskiere(text: str) -> str:
    """Macht Nutzertext satzsicher -- kein Steuerzeichen kommt roh durch."""
    return "".join(_MASKEN.get(ch, ch) for ch in text)


def satz_quelle(doc, titel: str) -> str:
    """Baut die LaTeX-Quelle aus allen Bausteinen des Dokuments.

    `titel` ist PFLICHT und hat keinen Vorgabewert -- PDF/UA-1 verlangt einen
    Dokumenttitel (dc:title, ISO 14289-1:2014 Klausel 7.1). Ein Vorgabewert
    waere hier die schlechtere Wahl: er erzeugt ein formal bestehendes Blatt
    mit einem nichtssagenden Titel, und genau den liest ein Screenreader vor.
    Gefunden hat das die Satzwache beim ersten Lauf -- der Vorspann war aus
    dem Spike uebernommen, wo der Titel im Rumpf stand statt im Vorspann."""
    vorspann = (VORSPANN
               .replace("TITEL", maskiere(titel))
               .replace("SPRACHE", maskiere(sprache(doc))))
    teile = [vorspann]
    # `bausteine_baum` statt der rohen Ablage: Kinder erscheinen in
    # Lesereihenfolge direkt hinter ihrem Elternteil (ADR-019, Auflage der
    # Entwurfsprobe zu kern/satz.py:86 -- siehe baustein.baumreihenfolge).
    for b in bausteine_baum(doc):
        teile.append(f"\\label{{bau:{b.kennung}}}\n")
        text = maskiere(b.text)
        if b.typ == "feld":
            teile.append(f"\\textbf{{{maskiere(b.feldname or '')}}}: {text}\n\n")
        else:
            teile.append(f"{text}\n\n")
    teile.append(NACHSPANN)
    return "".join(teile)


def _selftest() -> int:
    # Maskierung, wortwoertlich erwartet. Die fruehere Fassung fragte
    # `roh not in sicher` fuer jedes Sonderzeichen einzeln -- das KANN nicht
    # halten: die Ersetzung enthaelt das Zeichen selbst ("#" steckt in "\#",
    # "{}" in "\textbackslash{}"). Die Probe schlug damit gegen die korrekte
    # Maskierung an und lief nie, weil das Modul nicht in der Selbsttestliste
    # stand (gefunden 2026-08-15T06:20:00+0200 beim ersten Aufruf).
    assert maskiere("\\newpage{}$x&y%z#") == (
        r"\textbackslash{}newpage\{\}\$x\&y\%z\#"
    ), maskiere("\\newpage{}$x&y%z#")

    # Jedes gefuehrte Zeichen wird wirklich ersetzt, keines faellt aus der
    # Tabelle -- die Gegenprobe zur Zeile darueber, die nur eine Auswahl traf.
    for ch, ersatz in _MASKEN.items():
        assert maskiere(ch) == ersatz, (ch, maskiere(ch))

    # Der eigentliche Zweck: kein Steuerbefehl ueberlebt. Ein roher Backslash
    # vor einem Wort waere einer -- nach der Maskierung darf es keinen geben.
    sicher = maskiere("\\newpage \\input{/etc/passwd}")
    assert "\\newpage" not in sicher, sicher
    assert "\\input" not in sicher, sicher

    # Grenzwerte: leerer Text bleibt leer, harmloser Text bleibt unveraendert.
    assert maskiere("") == ""
    assert maskiere("Rechnung 2026, Position 3") == "Rechnung 2026, Position 3"

    try:
        import pycrdt  # noqa: F401
    except ImportError:
        print("satz: Baumreihenfolge-Probe uebersprungen -- pycrdt fehlt")
        print("satz: Selbsttest bestanden")
        return 0

    from dokument import baustein_anhaengen, leeres_dokument, sprache_setzen

    # ROT vor ADR-019: `satz_quelle` lief flach ueber die Ablagereihenfolge,
    # ein spaeter angehaengtes Kind stand hinter jedem spaeteren Geschwister
    # der Wurzelebene statt direkt hinter seinem Elternteil. GRUEN jetzt:
    # `bausteine_baum` liefert die Lesereihenfolge. Wird `satz_quelle` auf
    # `dokument.bausteine` (flach) zurueckgestellt, faellt genau diese
    # Reihenfolge um -- das ist die Mutationsprobe fuer kern/satz.py:86.
    doc = leeres_dokument()
    wurzel = baustein_anhaengen(doc, "ueberschrift", "Abschnitt 1")
    spaetere_wurzel = baustein_anhaengen(doc, "absatz", "Abschnitt 2")
    kind = baustein_anhaengen(doc, "absatz", "Unterpunkt von 1", eltern=wurzel)
    quelle = satz_quelle(doc, "Baumprobe")
    pos_kind = quelle.index(f"bau:{kind}")
    pos_spaetere_wurzel = quelle.index(f"bau:{spaetere_wurzel}")
    assert pos_kind < pos_spaetere_wurzel, (
        "das Kind muss vor dem spaeter angelegten Geschwister der Wurzelebene "
        "stehen -- sonst laeuft satz_quelle flach statt in Baumreihenfolge"
    )

    # Sprache wandert in den Vorspann, statt fest "de-DE" zu sein.
    assert "lang=de-DE" in satz_quelle(doc, "Titel")
    sprache_setzen(doc, "en-US")
    quelle_en = satz_quelle(doc, "Titel")
    assert "lang=en-US" in quelle_en and "pdflang={en-US}" in quelle_en
    assert "lang=de-DE" not in quelle_en

    print("satz: Selbsttest bestanden")
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
