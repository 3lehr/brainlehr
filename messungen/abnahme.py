#!/usr/bin/env python3
"""Abnahme je Planabschnitt -- hat er ein maschinell pruefbares
Fertig-Kriterium, und ist es erfuellt? (Auftrag 2026-08-09,
Wissensknoten 82d678f2.)

Anlass: Der Anstoss laeuft schon von selbst (23 Haken), aber niemand
prueft, ob ein Planschritt WIRKLICH fertig ist -- das steht bisher in
Prosa ("GEBAUT am ...") und ein Agent, der seinen eigenen Fortschritt
meldet, ist dafuer die schlechteste Quelle (Lehre L-706807: zweimal am
selben Tag Erfolg gemeldet, den das Protokoll widerlegte).

HARTE GRENZE, die diese Erhebung ehrlich macht: ein durchlaufender
--selftest belegt, dass das WERKZEUG tut was es soll -- NICHT, dass der
Planschritt INHALTLICH erledigt ist. Ein --melder, der schweigt, belegt
nur, dass er auf dem GEGENWAERTIGEN Bestand nichts zu melden hat, nicht
dass der Bestand vollstaendig ist. Diese Erhebung misst PRUEFBARKEIT,
keine Fertigstellung. Wer beides verwechselt, baut eine Autonomie, die
sich selbst gruen meldet.

Reuse (kein Nachbau der Abschnittserkennung): planordnung._analysiere()
liest die Abschnitte ueber planbindung._abschnitte() (Grenze ist JEDE
Ueberschrift, doppelte Kennungen wie S1b/S12 bleiben unterscheidbar) und
die je Abschnitt genannten Dateinamen ueber planordnung._dateien_in().
planordnung._label() haengt bei mehrfach vorkommender Kennung den Index
an, damit die Tabelle eindeutig bleibt.

Aufruf:
    python3 abnahme.py               # gegen docs/PLAN_*.md
    python3 abnahme.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

# Liegt eine Ebene unter der Wurzel: die Wurzel muss auf den Suchpfad,
# sonst findet `import knowledge_mcp_server` nichts. Muster aus haken/.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import planordnung  # reuse: _analysiere() -> Abschnitte + genannte Dateien je Abschnitt

WURZEL = Path(__file__).resolve().parent.parent  # eine Ebene tiefer seit dem Umzug 2026-08-10
ZEITGRENZE_SEK = 60

# Dieselbe Schreibweise wie in pruefer.py/planbindung.py/arbeitsmelder.py/
# normachsen.py/rasterblick.py: add_argument("--selftest", ...) bzw.
# add_argument("--melder", ...). Textsuche statt "--help" ausfuehren, weil
# letzteres jede genannte Datei einmal importieren wuerde -- mit allen
# Nebenwirkungen eines Moduls, das seine DB-Verbindung im Kopf oeffnet.
_ADD_ARG_RE = re.compile(r'add_argument\(\s*["\']--(selftest|melder)["\']')


def _schalter(pfad: Path) -> set[str]:
    try:
        text = pfad.read_text(encoding="utf-8")
    except OSError:
        return set()
    return set(_ADD_ARG_RE.findall(text))


@dataclass
class Ergebnis:
    art: str                 # "selbsttest" | "melder" | "kein_kriterium"
    erfuellt: bool | None    # True/False, oder None bei kein_kriterium/Zeitueberschreitung
    text: str                 # kurze Begruendung, fuer die Tabelle


def _lauf(pfad: Path, schalter: str, basis: Path, zeitgrenze: int) -> tuple[bool | None, str]:
    """Fuehrt `python3 <pfad> --<schalter>` mit Zeitgrenze aus.
    Zeitueberschreitung ist ein EIGENES Ergebnis (erfuellt=None), kein
    Fehlschlag -- Auftrag, Pflichtfall (e)."""
    try:
        p = subprocess.run(
            [sys.executable, str(pfad), f"--{schalter}"],
            capture_output=True, text=True, timeout=zeitgrenze, cwd=basis,
        )
    except subprocess.TimeoutExpired:
        return None, f"Zeitueberschreitung (>{zeitgrenze}s)"

    if schalter == "selftest":
        if p.returncode == 0:
            return True, "Selbsttest durchgelaufen"
        letzte_zeile = (p.stderr or p.stdout).strip().splitlines()[-1:] or [""]
        return False, f"Selbsttest fehlgeschlagen (exit {p.returncode}): {letzte_zeile[0][:80]}"

    # --melder: erfuellt, wenn er schweigt (Hauskonvention, siehe Docstring).
    if p.returncode != 0:
        return False, f"Melder-Aufruf fehlgeschlagen (exit {p.returncode})"
    ausgabe = (p.stdout + p.stderr).strip()
    if not ausgabe:
        return True, "Melder schweigt"
    return False, f"Melder meldet: {ausgabe.splitlines()[0][:80]}"


def _kriterium(dateinamen: list[str], basis: Path = WURZEL,
               zeitgrenze: int = ZEITGRENZE_SEK) -> Ergebnis:
    if not dateinamen:
        return Ergebnis("kein_kriterium", None, "keine Datei genannt")

    kandidaten = [(name, basis / name) for name in dateinamen]
    vorhandene = [(name, pfad) for name, pfad in kandidaten if pfad.is_file()]
    if not vorhandene:
        return Ergebnis("kein_kriterium", None,
                         f"genannte Datei(en) nicht gefunden: {', '.join(dateinamen)}")

    # 1. selbsttest hat Vorrang vor melder (Auftrag, Reihenfolge der Arten).
    for name, pfad in vorhandene:
        if "selftest" in _schalter(pfad):
            erfuellt, text = _lauf(pfad, "selftest", basis, zeitgrenze)
            return Ergebnis("selbsttest", erfuellt, f"{name}: {text}")
    for name, pfad in vorhandene:
        if "melder" in _schalter(pfad):
            erfuellt, text = _lauf(pfad, "melder", basis, zeitgrenze)
            return Ergebnis("melder", erfuellt, f"{name}: {text}")

    namen = ", ".join(name for name, _ in vorhandene)
    return Ergebnis("kein_kriterium", None,
                     f"Datei(en) vorhanden, aber ohne --selftest/--melder: {namen}")


@dataclass
class Zeile:
    plandatei: str
    kennung: str
    titel: str
    ergebnis: Ergebnis


def _erhebe(plan_dir: Path, basis: Path = WURZEL,
            zeitgrenze: int = ZEITGRENZE_SEK) -> list[Zeile]:
    zeilen: list[Zeile] = []
    for datei in sorted(plan_dir.glob("PLAN_*.md")):
        a = planordnung._analysiere(datei)
        for idx, ab in enumerate(a.abschnitte):
            erg = _kriterium(a.dateien_je[idx], basis, zeitgrenze)
            zeilen.append(Zeile(datei.name, planordnung._label(a, idx), ab.titel, erg))
    return zeilen


def _status_text(erg: Ergebnis) -> str:
    if erg.art == "kein_kriterium":
        return "kein Kriterium"
    if erg.erfuellt is True:
        return "erfuellt"
    if erg.erfuellt is False:
        return "NICHT erfuellt"
    return "Zeitueberschreitung"


def _drucke(zeilen: list[Zeile]) -> None:
    print(
        "GRENZE: ein gruener Selbsttest belegt das WERKZEUG, nicht den "
        "Planschritt. Ein schweigender Melder belegt nur den heutigen "
        "Bestand, keine Vollstaendigkeit.\n"
    )
    header = f"{'Kennung':10} {'Art':13} {'Ergebnis':20} Titel"
    print(header)
    print("-" * len(header))
    mit_kriterium = erfuellt = ohne = 0
    for z in zeilen:
        titel_kurz = z.titel if len(z.titel) <= 55 else z.titel[:52] + "..."
        status = _status_text(z.ergebnis)
        print(f"{z.kennung:10} {z.ergebnis.art:13} {status:20} {titel_kurz}")
        print(f"           {z.ergebnis.text}")
        if z.ergebnis.art == "kein_kriterium":
            ohne += 1
        else:
            mit_kriterium += 1
            if z.ergebnis.erfuellt is True:
                erfuellt += 1
    print()
    print(f"{mit_kriterium} von {len(zeilen)} Abschnitten haben ein Kriterium, "
          f"{erfuellt} davon erfuellt, {ohne} ohne Kriterium.")


# ---------------------------------------------------------------------------
# Selbsttest -- eigenes Verzeichnis, eigene erfundene Planabschnitte und
# Werkzeugdateien. Keine echte DB, kein Modellaufruf, kein Zugriff auf den
# echten Plan.
# ---------------------------------------------------------------------------

def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        basis = Path(tmp)

        (basis / "gruen.py").write_text(
            "import argparse, sys\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--selftest', action='store_true')\n"
            "a = p.parse_args()\n"
            "print('ok')\n"
            "sys.exit(0)\n",
            encoding="utf-8",
        )
        (basis / "rot.py").write_text(
            "import argparse, sys\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--selftest', action='store_true')\n"
            "a = p.parse_args()\n"
            "print('kaputt', file=sys.stderr)\n"
            "sys.exit(1)\n",
            encoding="utf-8",
        )
        (basis / "ohne_schalter.py").write_text(
            "import argparse\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--irgendwas', action='store_true')\n"
            "p.parse_args()\n",
            encoding="utf-8",
        )
        (basis / "langsam.py").write_text(
            "import argparse, time\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--selftest', action='store_true')\n"
            "p.parse_args()\n"
            "time.sleep(5)\n",
            encoding="utf-8",
        )
        (basis / "melder_still.py").write_text(
            "import argparse\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--melder', action='store_true')\n"
            "p.parse_args()\n",
            encoding="utf-8",
        )
        (basis / "melder_laut.py").write_text(
            "import argparse\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--melder', action='store_true')\n"
            "p.parse_args()\n"
            "print('etwas stimmt nicht')\n",
            encoding="utf-8",
        )

        # Kennung MUSS "S<zahl>[buchstabe]" sein (planbindung._HEADER_RE) --
        # "Sa" o.ae. waere gar kein Abschnittskopf und wuerde still verschluckt.
        plan = basis / "PLAN_TEST.md"
        plan.write_text(
            "### S1 · gruener Selbsttest\nSiehe `gruen.py`.\n\n"
            "### S2 · roter Selbsttest\nSiehe `rot.py`.\n\n"
            "### S3 · keine Datei genannt\nNur Text, nichts Pruefbares.\n\n"
            "### S4 · Datei fehlt\nSiehe `nicht_da.py`.\n\n"
            "### S5 · Datei ohne Schalter\nSiehe `ohne_schalter.py`.\n\n"
            "### S6 · Zeitueberschreitung\nSiehe `langsam.py`.\n\n"
            "### S7 · schweigender Melder\nSiehe `melder_still.py`.\n\n"
            "### S8 · lauter Melder\nSiehe `melder_laut.py`.\n",
            encoding="utf-8",
        )

        zeilen = _erhebe(basis, basis=basis, zeitgrenze=1)
        by = {z.kennung: z for z in zeilen}
        assert len(zeilen) == 8, f"erwartet 8 Abschnitte, bekommen {len(zeilen)}"

        # (a) gruener Selbsttest -> erfuellt
        assert by["S1"].ergebnis.art == "selbsttest"
        assert by["S1"].ergebnis.erfuellt is True, by["S1"].ergebnis.text

        # (b) roter Selbsttest -> Kriterium vorhanden, NICHT erfuellt
        assert by["S2"].ergebnis.art == "selbsttest"
        assert by["S2"].ergebnis.erfuellt is False, by["S2"].ergebnis.text

        # (c) keine Datei genannt -> kein_kriterium
        assert by["S3"].ergebnis.art == "kein_kriterium"
        assert "keine Datei genannt" in by["S3"].ergebnis.text

        # (d) Datei genannt, existiert nicht -> kein_kriterium, unterschieden von (e)
        assert by["S4"].ergebnis.art == "kein_kriterium"
        assert "nicht gefunden" in by["S4"].ergebnis.text

        # Datei da, aber ohne --selftest/--melder -> kein_kriterium, mit anderem Text als (d)
        assert by["S5"].ergebnis.art == "kein_kriterium"
        assert "ohne --selftest/--melder" in by["S5"].ergebnis.text
        assert by["S5"].ergebnis.text != by["S4"].ergebnis.text

        # (e) laenger als Zeitgrenze -> Zeitueberschreitung, kein Fehlschlag
        assert by["S6"].ergebnis.art == "selbsttest"
        assert by["S6"].ergebnis.erfuellt is None, by["S6"].ergebnis.text
        assert "Zeitueberschreitung" in by["S6"].ergebnis.text

        # melder: schweigen == erfuellt, sprechen == nicht erfuellt
        assert by["S7"].ergebnis.art == "melder"
        assert by["S7"].ergebnis.erfuellt is True, by["S7"].ergebnis.text
        assert by["S8"].ergebnis.art == "melder"
        assert by["S8"].ergebnis.erfuellt is False, by["S8"].ergebnis.text

        print("Selbsttest bestanden (Pflichtfaelle a-e plus Datei-ohne-Schalter).")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--plan-dir", type=Path, default=WURZEL / "docs")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return 0

    zeilen = _erhebe(args.plan_dir)
    _drucke(zeilen)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
