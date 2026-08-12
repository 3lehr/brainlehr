#!/usr/bin/env python3
"""zahlenbezug_fehlalarm.py -- Fehlalarmquote von kern/zahlenbezug.py an
echtem Sitzungsmaterial (Auftrag 2026-08-12, ABNAHME-Punkt "Fehlalarmquote").

QUELLE: die Sitzungsprotokolle unter ~/.claude/projects/*brainlehr*/*.jsonl --
dieselbe Quelle, die tests/test_normbezug_verdrahtung.py und die Doktrin als
"Transkripte" nennen. antwort_treffer.json/recall_log.jsonl (im Repo, aber
tabu und ohnehin ohne Volltext, nur Kennungen) sind dafuer nicht geeignet.

MASSSTAB: jede Assistant-Textnachricht ab MIN_LEN Zeichen zaehlt als EIN
Antworttext (gleicher Schwellwert wie antwort_abruf.py::MIN_LEN, damit die
Messung dieselbe Grundgesamtheit sieht wie der Hook im Betrieb). Meldet
kern/zahlenbezug.py dazu einen Treffer, gilt das hier als Alarm -- ob er
richtig oder falsch ist, kann diese Messung nicht wissen (kein Programm kann
das, siehe Docstring von zahlenbezug.py); gemessen wird nur die ANSCHLAGRATE,
die als Fehlalarm-Obergrenze gelesen wird, sofern echte Modellwissen-
Bekenntnisse in diesem Material selten sind (plausibel: es sind normale
Coding-Sitzungen, keine Wetterdoku-Sitzungen).

Aufruf: python3 messungen/zahlenbezug_fehlalarm.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path.insert(0, str(_w / "kern"))
import zahlenbezug  # noqa: E402

MIN_LEN = 400  # wie antwort_abruf.py::MIN_LEN
PROJEKTE = Path.home() / ".claude" / "projects"


def antworttexte() -> list[str]:
    texte = []
    for d in sorted(PROJEKTE.glob("*brainlehr*")):
        for datei in sorted(d.glob("*.jsonl")):
            try:
                with datei.open(encoding="utf-8", errors="replace") as f:
                    for zeile in f:
                        try:
                            z = json.loads(zeile)
                        except Exception:
                            continue
                        if z.get("type") != "assistant":
                            continue
                        inhalt = (z.get("message") or {}).get("content") or []
                        stuecke = [t.get("text", "") for t in inhalt
                                   if isinstance(t, dict) and t.get("type") == "text"]
                        text = "\n".join(stuecke)
                        if len(text) >= MIN_LEN:
                            texte.append(text)
            except OSError:
                continue
    return texte


def main() -> None:
    texte = antworttexte()
    treffer = [(i, zahlenbezug.treffer(t)) for i, t in enumerate(texte)]
    anschlaege = [(i, t) for i, t in treffer if t]
    n = len(texte)
    k = len(anschlaege)
    quote = (k / n * 100) if n else 0.0
    print(f"Antworttexte >= {MIN_LEN} Zeichen: {n}")
    print(f"Davon mit Anschlag: {k} ({quote:.1f} %)")
    for i, saetze in anschlaege:
        for s in saetze:
            print(f"  [{i}] {s[:160]}")
    if n:
        urteil = "UNBRAUCHBAR (> 10%)" if quote > 10 else "im Rahmen (<= 10%)"
        print(f"Urteil: {urteil}")


if __name__ == "__main__":
    main()
