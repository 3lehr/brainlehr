#!/usr/bin/env python3
"""zitatpruefer.py -- prueft Zitate in Markdown-Dokumenten byte-gleich gegen
ihre Quelle. Rein mechanisch: kein Sprachmodell, kein Urteil ueber Bedeutung.

ANLASS (Knoten a146403a, Lehre L-3d4320): Im Protokoll der
Eigentuemerversammlung vom 04.09.2025 stand woertlich, die JAEHRLICHE
ZUFUEHRUNG zur Erhaltungsruecklage werde ab 2026 von 15.000 auf 30.000 EUR
erhoeht -- mit "z.B. Heizungsmodernisierung" als BEISPIEL fuer einen
moeglichen Verwendungszweck. Im Dokument wurde daraus "die Ruecklage ist
bereits erhoeht ... ausdruecklich fuer die Heizungsmodernisierung -- die
Sanierung ist mit Geld hinterlegt, bevor sie beschlossen ist". Drei
Verschaerfungen in einem Satz, alle in dieselbe Richtung, gingen durch Commit,
vier PDFs und einen 25-seitigen Band. Gefunden hat es ein Mensch mit einer
Frage.

TEIL 1 -- ZITATFORMAT: Markdown-Blockquote + Attributionszeile.

    > Die jaehrliche Zufuehrung zur Erhaltungsruecklage betraegt derzeit
    > 15.000 EUR.
    > -- Quelle: protokoll_2025-09-04.md, Abschnitt: TOP 5

Begruendung: Ein Blockquote (`>`) ist bereits die native Markdown-Auszeichnung
fuer "das ist woertlich, nicht meine Formulierung" -- kein Sondersyntax noetig,
jeder Editor und jeder Renderer stellt es korrekt dar. Die Attributionszeile
direkt darunter (beginnend mit `--` oder `--` Variante `—`, dann `Quelle:`)
haelt Zitat und Fundstelle raeumlich zusammen, statt sie ueber Fussnoten oder
ein Anhangsregister zu trennen, wo sie beim Schreiben leicht auseinanderlaufen.
Der Abschnitt ist optional (`, Abschnitt: ...`), die Quelldatei nicht.

EIN ZITAT OHNE FUNDSTELLE (Blockquote ohne folgende `-- Quelle:`-Zeile) ist
kein Zitat, sondern eine unbelegte Behauptung im Zitatgewand. Es wird als
eigener Befund gemeldet (Art `keine_fundstelle`), nicht stillschweigend
uebersprungen -- sonst waere ein weggelassenes Attribut der billigste Weg,
der Pruefung zu entgehen.

TEIL 2 -- NORMALISIERUNG (`normalisieren`): Zwei Aenderungen, beide bewusst
gewaehlt, beide lassen genau EINEN Fall durch:

  1. Lauf aus Leerraum (Leerzeichen, Tab, Zeilenumbruch) wird zu einem
     einzelnen Leerzeichen zusammengefasst, Rand getrimmt. LAESST DURCH: ein
     Zitat, das beim Abtippen ueber mehrere Zeilen umgebrochen oder mit
     doppeltem Leerzeichen erfasst wurde -- PDF-Extraktion und Handabschrift
     brechen Zeilen unterschiedlich, ohne den Wortlaut zu aendern.
  2. Typografische Anfuehrungszeichen (" " ' ' „ ‚) werden auf gerade
     Zeichen (" ') abgebildet. LAESST DURCH: ein Zitat, das mit den
     "schoenen" Anfuehrungszeichen eines Textverarbeitungsprogramms statt der
     geraden ASCII-Zeichen der Quelle abgetippt wurde.

  Was NICHT normalisiert wird: Gross-/Kleinschreibung, Satzzeichen ausser
  Anfuehrungszeichen, Wortreihenfolge, jedes einzelne Zeichen im Wortkoerper.
  Ein einziges abweichendes Zeichen dort schlaegt an -- genau das war der
  echte Fall: "die Ruecklage ist bereits erhoeht" kommt im Protokoll an
  keiner Stelle byte-gleich vor.

TEIL 3 -- RICHTUNG DER ABWEICHUNGEN (`traeger_abweichungen`): Wo eine Quelle
zusammengefasst statt zitiert wird, gibt es keinen Blockquote zum
byte-Vergleich. Diese Funktion zaehlt trotzdem mechanisch: sie nimmt Paare
(Quellwortlaut, Textwortlaut) entgegen, zerlegt beide in Woerter und meldet
per `difflib.SequenceMatcher`, welche Woerter aus der Quelle im Text fehlen
und welche im Text hinzugekommen sind, die die Quelle nicht enthaelt.

WARUM DIE RICHTUNG (verschaerfend / abschwaechend / neutral) HIER NICHT
BEWERTET WIRD: Ob "jaehrliche Zufuehrung" zu "die Ruecklage" wird, ist eine
Verschaerfung -- aber das folgt aus der BEDEUTUNG der Woerter (Fluss- vs.
Bestandsgroesse), nicht aus ihrer Differenz als Zeichenketten. Eine Wortliste
kann nicht wissen, ob ein weggefallenes Wort einschraenkte oder nur
schmueckte. Diese Einordnung bleibt Menschen oder einem Sprachmodell
vorbehalten -- die Funktion liefert die Zutaten (was fehlt, was hinzukam,
wie viele), trifft aber kein Urteil.

Aufruf:
    python3 -m kern.zitatpruefer <dokument.md> [--quellwurzel VERZEICHNIS]
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ATTRIB_RE = re.compile(
    r"^\s*(?:--|—|-)\s*Quelle:\s*(?P<quelle>[^,]+?)"
    r"(?:,\s*Abschnitt:\s*(?P<abschnitt>.+?))?\s*$"
)

# Typografische Anfuehrungszeichen -> gerade. Siehe Docstring Teil 2, Fall 2.
_ANFUEHRUNG = str.maketrans({
    "“": '"', "”": '"', "„": '"',
    "‘": "'", "’": "'", "‚": "'",
})


def normalisieren(text: str) -> str:
    """Leerraum-Laeufe -> ein Leerzeichen, typografische Anfuehrungszeichen
    -> gerade. Siehe Docstring Teil 2 fuer die zwei Faelle, die das
    ausdruecklich durchlaesst -- und dass sonst nichts angeglichen wird."""
    text = text.translate(_ANFUEHRUNG)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class Zitat:
    text: str
    quelle: str | None
    abschnitt: str | None
    zeile: int  # 1-basierte Zeilennummer im Dokument, wo der Block beginnt


@dataclass
class Befund:
    zitat: Zitat
    art: str  # "keine_fundstelle" | "abweichung"
    detail: str


def zitate_aus_markdown(text: str) -> list[Zitat]:
    """Findet Blockquote+Attribution-Paare (Teil 1). Ein Blockquote ohne
    folgende Attributionszeile liefert ein Zitat mit quelle=None -- die
    Meldung dazu passiert in pruefe_dokument, nicht hier."""
    zeilen = text.splitlines()
    zitate: list[Zitat] = []
    i = 0
    n = len(zeilen)
    while i < n:
        if not zeilen[i].startswith(">"):
            i += 1
            continue
        start = i
        rohzeilen = []
        while i < n and zeilen[i].startswith(">"):
            inhalt = zeilen[i][1:]
            if inhalt.startswith(" "):
                inhalt = inhalt[1:]
            rohzeilen.append(inhalt)
            i += 1
        # letzte Zeile(n) auf Attribution pruefen (ueblich: genau die letzte)
        quelle = abschnitt = None
        koerper = rohzeilen
        for k in range(len(rohzeilen) - 1, -1, -1):
            m = ATTRIB_RE.match(rohzeilen[k])
            if m:
                quelle = m.group("quelle").strip()
                abschnitt = (m.group("abschnitt") or "").strip() or None
                koerper = rohzeilen[:k]
                break
        zitate.append(Zitat(
            text="\n".join(koerper).strip(),
            quelle=quelle,
            abschnitt=abschnitt,
            zeile=start + 1,
        ))
    return zitate


def pruefe_zitat(zitat: Zitat, quellwurzel: Path) -> Befund | None:
    """Teil 2: byte-gleiche (normalisierte) Pruefung. None = kein Befund."""
    if zitat.quelle is None:
        return Befund(zitat, "keine_fundstelle",
                       "Blockquote ohne Fundstelle (keine '-- Quelle:'-Zeile)")
    quelldatei = quellwurzel / zitat.quelle
    if not quelldatei.is_file():
        return Befund(zitat, "quelle_fehlt",
                       f"Quelldatei nicht gefunden: {quelldatei}")
    quellinhalt = normalisieren(quelldatei.read_text(encoding="utf-8"))
    zitattext = normalisieren(zitat.text)
    if zitattext not in quellinhalt:
        return Befund(zitat, "abweichung",
                       f"Zeichenfolge kommt in {zitat.quelle} nicht vor: "
                       f"{zitat.text!r}")
    return None


def pruefe_dokument(dokument: Path, quellwurzel: Path | None = None) -> list[Befund]:
    """Liest ein Markdown-Dokument, prueft jedes Zitat, gibt alle Befunde
    zurueck (leer = alles belegt)."""
    if quellwurzel is None:
        quellwurzel = dokument.parent
    text = dokument.read_text(encoding="utf-8")
    befunde = []
    for zitat in zitate_aus_markdown(text):
        befund = pruefe_zitat(zitat, quellwurzel)
        if befund is not None:
            befunde.append(befund)
    return befunde


def traeger_abweichungen(paare: list[tuple[str, str]]) -> list[dict]:
    """Teil 3: fuer jedes Paar (Quellwortlaut, Textwortlaut) die Woerter
    zaehlen, die in der Zusammenfassung fehlen bzw. hinzugekommen sind.
    Bewertet NICHT, ob das eine Verschaerfung ist -- siehe Docstring."""
    ergebnisse = []
    for quelle, text in paare:
        quelle_woerter = quelle.split()
        text_woerter = text.split()
        sm = difflib.SequenceMatcher(a=quelle_woerter, b=text_woerter)
        fehlend: list[str] = []
        hinzugekommen: list[str] = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in ("delete", "replace"):
                fehlend.extend(quelle_woerter[i1:i2])
            if tag in ("insert", "replace"):
                hinzugekommen.extend(text_woerter[j1:j2])
        ergebnisse.append({
            "quelle": quelle,
            "text": text,
            "fehlend": fehlend,
            "hinzugekommen": hinzugekommen,
            "abweichungen": len(fehlend) + len(hinzugekommen),
        })
    return ergebnisse


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dokument", type=Path)
    ap.add_argument("--quellwurzel", type=Path, default=None)
    args = ap.parse_args(argv)
    befunde = pruefe_dokument(args.dokument, args.quellwurzel)
    if not befunde:
        print("keine Befunde")
        return 0
    for b in befunde:
        print(f"Zeile {b.zitat.zeile} [{b.art}]: {b.detail}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
