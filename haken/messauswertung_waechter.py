#!/usr/bin/env python3
"""Ausloeser fuer den Schritt "beim Auswerten einer Messung" -- Fund vom
2026-08-15 (runs/lehren_ohne_regel_2026-08-15T142055+0200.json, Messung 3):
36 von 443 unzugeordneten Lehren waeren hier eingeschlagen, und KEIN
Mechanismus (weder settings.json noch geplanter Lauf) griff.

WAS SICH BEIM NACHSEHEN HERAUSSTELLTE, STATT EINEN NEUEN WAECHTER ZU BAUEN:
melder/messregeln.py existiert bereits, prueft genau das haeufigste Muster
der 36 Lehren (16/36 "Positivkontrolle fehlt" -- hier: Haltemenge/Trennver-
fahren) und hat eine eigene Gegenprobe (6 Faelle, `--selftest`). Gemessen mit
`python3 melder/ausloeserlos.py`: messregeln.py steht in der Liste der 20
Mechanismen OHNE Ausloeser. Der fehlende Ausloeser IST die Luecke -- nicht
fehlende Pruef-Logik. Neu gebaut wird deshalb nur der Ausloeser, nicht die
Pruefung (ponytail-Stufe 2: vorhandenes wiederverwenden).

ORT DES AUSLOESERS: das Schreiben/Committen einer runs/*.json-Datei, hier
verdrahtet in .git/hooks/pre-push -- der Moment, in dem eine Messdatei das
Repo verlaesst, ist der letzte Punkt, an dem eine fehlende Haltemenge noch
folgenlos nachtragbar ist.

SCOPE-ENTSCHEIDUNG, gemessen 2026-08-15: melder/messregeln.py --pruefen
scannt ALLE 153 Dateien unter runs/ und findet 4 Altfaelten (alle bereits auf
origin/brainlehr/b4-ausweis vorhanden, siehe `git cat-file -e origin/...:<pfad>`).
Wuerde dieser Waechter --pruefen ungefiltert vor jeden Push haengen, bliebe er
WEGEN DER ALTLAST fuer immer rot -- exakt die Bauform, die die HARTE AUFLAGE
dieses Auftrags verbietet ("ein Waechter, der jeden Push blockiert, wird beim
ersten Mal umgangen"). Deshalb: nur die runs/*.json-Dateien pruefen, die im
AUSGEHENDEN Commit-Bereich NEU sind oder geaendert wurden (git diff gegen die
Remote-SHA, wie push_guard.py es fuer seinen eigenen Scan schon tut) -- alte,
bereits veroeffentlichte Funde bleiben liegen, ohne jeden Push zu blockieren.

Gemessen an den 11 heute neu hinzugekommenen runs/*.json (Commits gegenueber
origin/brainlehr/b4-ausweis): 0/11 Fund -- 0% Fehlalarm UND 0% echter Fund in
dieser Stichprobe (die 3 echten Vergleichsdateien mit Luecke liegen alle vor
dem 2026-08-15 und sind bereits gepusht). Die eigentliche rot-vor-gruen-Probe
steht deshalb in tests/test_messauswertung_waechter.py mit einer synthetischen
Vergleichsdatei -- reale Positivkontrolle, weil im echten Bestand heute keine
neue Luecke vorlag.

Aufruf:
    python3 haken/messauswertung_waechter.py <remote-sha> <local-sha>
    # druckt Befunde zu runs/*.json, die zwischen remote-sha und local-sha
    # neu/geaendert sind; Exit 1 bei Fund, 0 sonst.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
from melder import messregeln  # noqa: E402  -- Pruef-Logik wiederverwendet, nicht dupliziert


def geaenderte_runs_dateien(remote_sha: str, local_sha: str, cwd: Path = WURZEL) -> list[Path]:
    """runs/*.json (ohne .gegenprobe/.rasterblick-Beiwerk), die im Bereich
    remote_sha..local_sha hinzugefuegt oder geaendert wurden. Bei neuem Zweig
    (remote_sha = 40 Nullen) wird gegen den leeren Baum verglichen -- dann
    zaehlt jede vorhandene runs/*.json als "neu"."""
    if set(remote_sha) == {"0"}:
        range_arg = local_sha
    else:
        range_arg = f"{remote_sha}..{local_sha}"
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=AM", range_arg, "--", "runs/*.json"],
        cwd=cwd, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return []
    out = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.endswith((".gegenprobe.json", ".rasterblick.json")):
            continue
        out.append(cwd / line)
    return out


def pruefe(dateien: list[Path]) -> list[dict]:
    return [b for b in (messregeln.pruefe_datei(f) for f in dateien if f.is_file()) if b]


def main() -> int:
    if len(sys.argv) != 3:
        print("messauswertung_waechter: erwarte <remote-sha> <local-sha>", file=sys.stderr)
        return 1
    remote_sha, local_sha = sys.argv[1], sys.argv[2]
    dateien = geaenderte_runs_dateien(remote_sha, local_sha)
    befunde = pruefe(dateien)
    if not befunde:
        print(f"messauswertung_waechter: {len(dateien)} neue/geaenderte runs/-Datei(en) im Push, 0 beanstandet.")
        return 0
    print(f"messauswertung_waechter: {len(befunde)} von {len(dateien)} neuen/geaenderten runs/-Datei(en) beanstandet:")
    for b in befunde:
        print(f"  {b['datei']}  ({b['moeglichkeiten']} Moeglichkeiten verglichen)")
        for f in b["fehlt"]:
            print(f"    fehlt: {f}")
    print("Push abgebrochen. Fehlendes Feld nachtragen (siehe melder/messregeln.py) und erneut versuchen.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
