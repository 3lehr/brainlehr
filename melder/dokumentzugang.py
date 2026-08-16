#!/usr/bin/env python3
"""Linie A aus docs/PLAN_DOKUMENTABLAGE_2026-08-16.md -- Dokumente bekommen
einen Zugang im Speicher.

DER ANLASS, woertlich vom Betreiber am 2026-08-16: "warum verweist die
datenbank nicht darauf und oder warum legen wir sowas nicht automatisch in die
datenbank ab? Es ist ja wissen 'pur'?!" -- nachdem eine sorgfaeltige
Videoauswertung im Repo lag und ueber den Abruf nicht auffindbar war.

GEMESSEN: 121 Dokumente unter docs/, davon nennt der Speicher **18** als
Quelle. 103 sind fuer jede Suche unsichtbar, darunter 38 Plaene, 3 Recherchen,
2 Konsile und beide Videoauswertungen. Der Abruf liest die Datenbank, die
Arbeit landet im Dateisystem -- dazwischen fehlte die Bruecke.

DIE BAUFORM: ein VERWEIS, keine Kopie. Der Knoten traegt Titel, den ersten
Absatz und den Pfad; die Datei bleibt das Langformat. Damit gibt es weiterhin
genau EINE Fassung des Inhalts -- zwei liefen unweigerlich auseinander.

NULL MODELLAUFRUFE: Titel ist die erste Ueberschrift, die Zusammenfassung der
erste Absatz. Beides stammt vom Autor des Dokuments, nicht von einer Maschine,
die sich etwas ausdenkt und bei jeder Aenderung erneut kostet.

WAS DIESES MODUL NICHT TUT: es schreibt nichts von selbst. Es liefert die
Liste dessen, was fehlt (`--fehlend`) und den fertigen Vorschlag je Dokument
(`--vorschlag`). Das Anlegen geht ueber knowledge_add und traegt damit einen
Ausweis -- ein Speicher, in den ein Skript ungefragt schreibt, verliert genau
die Eigenschaft, die ihn von einem Verzeichnis unterscheidet.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "kern")]

DOKUMENTE = _w / "docs"
DB = _w / "brainlehr.db"

# Welche Dokumente einen Zugang brauchen: die, die eine ERKENNTNIS tragen.
# Ein Startprompt ist eine Uebergabe fuer genau einen Faden und morgen
# gegenstandslos -- er gehoert nicht in einen Speicher, der auf Dauer angelegt
# ist. Die Unterscheidung steht hier und nicht im Kopf des Aufrufers, damit
# sie pruefbar ist.
TRAEGT_ERKENNTNIS = re.compile(
    r"^(PLAN|RECHERCHE|KONSIL|VIDEOAUSWERTUNG|ADR|BEFUND|MESSUNG|ANALYSE|DEFINITION|AUFBAU)",
    re.I)
KEIN_ZUGANG = re.compile(r"^(STARTPROMPT|PROMPT|CHATGPT)", re.I)


def _titel_und_absatz(pfad: Path) -> tuple[str, str]:
    """Erste Ueberschrift und erster Absatz -- beides vom Autor geschrieben.

    Der erste Absatz ist nicht immer die beste Zusammenfassung, aber er ist
    die ehrlichste: er steht so im Dokument. Eine erfundene waere besser
    lesbar und schlechter belegt."""
    text = pfad.read_text(encoding="utf-8", errors="ignore")
    titel = ""
    absatz: list[str] = []
    for zeile in text.splitlines():
        z = zeile.strip()
        if not titel:
            if z.startswith("# "):
                titel = z[2:].strip()
            continue
        if not z:
            if absatz:
                break
            continue
        if z.startswith("#"):
            if absatz:
                break
            continue
        absatz.append(z)
    return titel or pfad.stem, " ".join(absatz)[:600]


def bestand() -> set[str]:
    """Dateinamen, die im Speicher als Quelle vorkommen."""
    if not DB.exists():
        return set()
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    quellen = " || ".join(r[0] or "" for r in c.execute("select source from knowledge_nodes"))
    c.close()
    return {n for n in (p.name for p in DOKUMENTE.rglob("*.md")) if n in quellen}


def fehlend() -> list[Path]:
    vorhanden = bestand()
    treffer = []
    for p in sorted(DOKUMENTE.rglob("*.md")):
        if p.name in vorhanden or KEIN_ZUGANG.match(p.name):
            continue
        if TRAEGT_ERKENNTNIS.match(p.name):
            treffer.append(p)
    return treffer


def vorschlag(pfad: Path) -> dict:
    titel, absatz = _titel_und_absatz(pfad)
    rel = pfad.relative_to(_w)
    return {
        "parent_path": "/brainlehr/dokumente",
        "title": titel[:180],
        "summary": absatz or f"Dokument ohne einleitenden Absatz: {rel}",
        "source": f"Verweis auf {rel} (erzeugt von melder/dokumentzugang.py)",
        "norm_entscheidung": "keine_norm",
        "norm_entschieden_grund": ("Verweisknoten auf ein Dokument -- die Normfrage "
                                   "entscheidet der Inhalt des Dokuments, nicht der Zugang."),
        "tags": ["dokument", "verweis", pfad.name.split("_")[0].lower()],
    }


def demo() -> None:
    """Netzloser Selbsttest: prueft die Auswahlregel und das Lesen von Titel
    und erstem Absatz -- die beiden Stellen, an denen sich ein Fehler still
    fortpflanzen wuerde."""
    assert TRAEGT_ERKENNTNIS.match("PLAN_X_2026-01-01.md")
    assert TRAEGT_ERKENNTNIS.match("VIDEOAUSWERTUNG_2026-08-16_abc.md")
    assert not TRAEGT_ERKENNTNIS.match("STARTPROMPT_X.md")
    assert KEIN_ZUGANG.match("STARTPROMPT_X.md"), (
        "eine Uebergabe fuer einen Faden gehoert nicht in einen Dauerspeicher")

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "PLAN_probe.md"
        p.write_text("# Der Titel\n\n**Erster Absatz** mit Inhalt.\nZweite Zeile davon.\n\n"
                     "## Abschnitt\n\nDas hier nicht mehr.\n", encoding="utf-8")
        titel, absatz = _titel_und_absatz(p)
        assert titel == "Der Titel", titel
        assert absatz == "**Erster Absatz** mit Inhalt. Zweite Zeile davon.", absatz
        assert "Abschnitt" not in absatz, "der Absatz endet vor der naechsten Ueberschrift"

        leer = Path(d) / "PLAN_leer.md"
        leer.write_text("# Nur ein Titel\n", encoding="utf-8")
        assert _titel_und_absatz(leer) == ("Nur ein Titel", "")
    # Nach stderr: stdout traegt bei --vorschlag reines JSON, und ein
    # "demo: ok" davor macht jede Weiterverarbeitung kaputt.
    print("demo: ok", file=sys.stderr)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vorschlag", action="store_true",
                   help="fertige knowledge_add-Aufrufe als JSON")
    p.add_argument("--still", action="store_true")
    a = p.parse_args()
    offen = fehlend()
    if a.vorschlag:
        print(json.dumps([vorschlag(x) for x in offen], indent=1, ensure_ascii=False))
        return 0
    if not offen:
        if not a.still:
            print("Jedes Dokument mit Erkenntnis hat einen Zugang im Speicher.")
        return 0
    if not a.still:
        print(f"{len(offen)} Dokument(e) ohne Zugang im Speicher -- ueber den Abruf "
              f"unauffindbar:", file=sys.stderr)
        for x in offen:
            print(f"  {x.relative_to(_w)}", file=sys.stderr)
        print("\nVorschlaege: python3 melder/dokumentzugang.py --vorschlag", file=sys.stderr)
    return 1


if __name__ == "__main__":
    demo()
    raise SystemExit(main())
