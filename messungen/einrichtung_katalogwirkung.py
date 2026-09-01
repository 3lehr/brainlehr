#!/usr/bin/env python3
"""BDW-P11-AC2: Senkt ein eingelesener Katalog die eigene Trefferquote?

GEGEN DIESELBE NULLLINIE wie vorher gemessen, also gegen denselben
Fragensatz (runs/pruefkorpus.jsonl) und denselben Abrufweg
(kern/abrufguete.py -> haken/knowledge_recall_hook.py). Kein zweiter
Messweg -- ein eigener waere ein zweiter Begriff von 'Treffer'.

DREI LAEUFE, und der dritte ist der Punkt:

  A NULLLINIE          gewachsener Bestand, unveraendert
  B NACHSCHLAGEWERK    derselbe Bestand + Katalog als `nachschlagewerk`
  C POSITIVKONTROLLE   derselbe Bestand + derselbe Katalog als `arbeitsbestand`

Ohne C belegt B nichts. Bliebe die Zahl in beiden Laeufen gleich, waere die
naheliegende Erklaerung nicht 'die Gattung wirkt', sondern 'die Messung
bewegt sich nicht' -- genau die Fehlklasse, vor der die Hausregel zum
Pruefstand warnt (eine Zahl, ueber die sich niemand wundert).

Gemessen wird auf KOPIEN. Der Betriebsbestand wird gelesen und einmal
kopiert, nie beschrieben.

Aufruf:
    python3 messungen/einrichtung_katalogwirkung.py --ziel runs/einrichtung_2026-08-21.json
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken", "melder")]

import argparse  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
from pathlib import Path  # noqa: E402

import ort  # noqa: E402
import speicher  # noqa: E402
import zeitmarke  # noqa: E402

WURZEL = _w

# Der Messlauf selbst laeuft in einem EIGENEN Prozess je Bestand: der
# Abrufweg (haken/knowledge_recall_hook.py) liest den Datenbankpfad beim
# Import einmal aus haken/ort.py. Ihn im laufenden Prozess umzubiegen waere
# genau die Sorte Pruefstandsabweichung, die die Zahl still verfaelscht.
_MESSKIND = r'''
import json, sys
sys.path[:0] = [{wurzel!r}] + [{wurzel!r} + "/" + o for o in ("kern", "haken")]
import abrufguete as ag
import speicher
wurzel = {katalogwurzel!r}
gesehen = []
_abrufen = ag.abrufen
def abrufen(task):
    nodes, lessons = _abrufen(task)
    gesehen.extend(n["path"] for n in nodes if n["path"].startswith(wurzel))
    return nodes, lessons
ag.abrufen = abrufen
faelle, dubletten = ag.lade_korpus()
with speicher.lesen(ag.rh.DB) as conn:
    q = ag.messe(faelle, conn)
einzel = q.pop("_einzel", {{}})
print(json.dumps({{"bestand": str(ag.rh.DB), "faelle": len(faelle),
                   "dubletten": dubletten,
                   "quote": {{k: list(v) for k, v in q.items()}},
                   "je_fall": einzel,
                   "katalogtreffer_in_ergebnissen": len(gesehen)}}))
'''


def _kopie(ziel: Path) -> Path:
    """WAL-Checkpoint, dann Dateikopie -- dieselbe Form wie
    kern/betriebsprofil.py::_sicherung. Ohne Checkpoint fehlte der Kopie
    alles, was noch im Write-Ahead-Log steht."""
    conn = speicher.verbinde_bestand(ort.DB)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()
    shutil.copy2(ort.DB, ziel)
    return ziel


def _messen(db: Path, katalogwurzel: str = "/bsi-sdt") -> dict:
    umgebung = dict(os.environ, BRAINLEHR_DB=str(db))
    umgebung.pop("BEGOD_KNOWLEDGE_DB", None)
    fertig = subprocess.run(
        [_sys.executable, "-c",
         _MESSKIND.format(wurzel=str(WURZEL), katalogwurzel=katalogwurzel)],
        capture_output=True, text=True, env=umgebung, cwd=str(WURZEL))
    if fertig.returncode != 0:
        raise RuntimeError(f"Messlauf gescheitert:\n{fertig.stderr[-2000:]}")
    return json.loads(fertig.stdout.strip().splitlines()[-1])


def lauf(katalog: str = "bsi", ziel: Path | None = None) -> dict:
    import einrichtung  # noqa: PLC0415 -- erst nach der Pfadsetzung importierbar

    arbeitsort = Path(tempfile.mkdtemp(prefix="katalogwirkung-"))
    a = _kopie(arbeitsort / "A_nulllinie.db")
    b = shutil.copy2(a, arbeitsort / "B_nachschlagewerk.db")
    c = shutil.copy2(a, arbeitsort / "C_positivkontrolle.db")
    # Nulllinie ZWEIMAL, auf identischen Kopien: ohne diese Kontrolle waere
    # jede Abweichung zwischen A und B genauso gut Rauschen des Messwegs.
    a2 = shutil.copy2(a, arbeitsort / "A2_wiederholung.db")

    ergebnis: dict = {
        "erhoben_am": zeitmarke.jetzt(),
        "auftrag": "BDW-P11-AC2 (docs/PLAN_BETRIEBSPROFILE_2026-08-20.md, Abschnitt C)",
        "katalog": katalog,
        "arbeitsort": str(arbeitsort),
        "messweg": "kern/abrufguete.py::messe ueber haken/knowledge_recall_hook.py, "
                   "Korpus runs/pruefkorpus.jsonl -- derselbe Weg und derselbe "
                   "Fragensatz wie in den frueheren Abrufmessungen",
    }

    wurzel_kat = next(k["wurzel"] for k in einrichtung.kataloge() if k["name"] == katalog)
    ergebnis["A_nulllinie"] = _messen(a, wurzel_kat)
    ergebnis["import_nachschlagewerk"] = einrichtung.katalog_einlesen(
        katalog, db=Path(b), gattung="nachschlagewerk")
    ergebnis["B_nachschlagewerk"] = _messen(Path(b), wurzel_kat)
    ergebnis["import_arbeitsbestand"] = einrichtung.katalog_einlesen(
        katalog, db=Path(c), gattung="arbeitsbestand")
    ergebnis["C_positivkontrolle"] = _messen(Path(c), wurzel_kat)
    ergebnis["A2_wiederholung"] = _messen(Path(a2), wurzel_kat)

    gruppen = ("NODE", "LESSON", "MIT_KANTE", "OHNE_KANTE")
    a_q = ergebnis["A_nulllinie"]["quote"]
    b_q = ergebnis["B_nachschlagewerk"]["quote"]
    c_q = ergebnis["C_positivkontrolle"]["quote"]
    a2_q = ergebnis["A2_wiederholung"]["quote"]
    a_f, b_f = ergebnis["A_nulllinie"]["je_fall"], ergebnis["B_nachschlagewerk"]["je_fall"]
    c_f = ergebnis["C_positivkontrolle"]["je_fall"]
    ergebnis["befund"] = {
        "messung_stabil": all(a_q[g] == a2_q[g] for g in gruppen),
        "nachschlagewerk_senkt_nicht": all(a_q[g] == b_q[g] for g in gruppen),
        "positivkontrolle_bewegt_sich": any(a_q[g] != c_q[g] for g in gruppen),
        "gattung_macht_unterschied": any(b_q[g] != c_q[g] for g in gruppen),
        "vergleich": {g: {"A": a_q[g], "A2": a2_q[g], "B": b_q[g], "C": c_q[g]}
                      for g in gruppen},
        "gekippt_A_zu_B": sorted(k for k in a_f if a_f[k] != b_f.get(k)),
        "gekippt_A_zu_C": sorted(k for k in a_f if a_f[k] != c_f.get(k)),
        "katalogknoten_in_ergebnissen": {
            "B": ergebnis["B_nachschlagewerk"]["katalogtreffer_in_ergebnissen"],
            "C": ergebnis["C_positivkontrolle"]["katalogtreffer_in_ergebnissen"]},
    }
    if ziel:
        ziel.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    return ergebnis


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--katalog", default="bsi")
    p.add_argument("--ziel", type=Path, default=None)
    a = p.parse_args()
    print(json.dumps(lauf(a.katalog, a.ziel), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
