#!/usr/bin/env python3
# ausloeser: auf-abruf -- beantwortet, ob zwei verschiedene Abschnitte in docs/ dieselbe Kennung tragen
"""Traegt in `docs/` eine Kennung (S12, B4.3, §4, 104.1.2) zwei VERSCHIEDENE
Abschnitte? Dann verweist jeder Auftrag, jede ADR und jeder Agentenbericht,
der sie nennt, auf zwei Stellen.

ANLASS: `docs/PLAN_GESAMT_2026-08-13.md` fuehrt unter Aufgabe `110` die Zahl
**12 Kennungskollisionen** -- ohne Ergebnisdatei, ohne Skript, ohne
nachfahrbaren Befehl. Eine Zahl, die niemand nachrechnen kann, ist eine
Behauptung. Dieses Skript ist der fehlende Befehl.

DER FEHLER, DEN DIESES SKRIPT SELBST FAST GEMACHT HAETTE, und er ist der
Grund fuer die Reihenfolge in KODE: Bei `[SPGKB]\\d+` VOR `B4\\.\\d+` schluckt
die kuerzere Alternative das `B4` aus `B4.1` -- Python-Regex nimmt die ERSTE
passende Alternative, nicht die laengste. Sechs verschiedene Abschnitte
`B4.1` bis `B4.6` erscheinen dann als sechs Kollisionen derselben Kennung
`B4`, und `104.1.1`/`104.1.2`/`104.1.3` als drei von `104.1`. Der erste Lauf
meldete so 6 Kollisionen, davon 5 erfunden. Wer eine hierarchische Kennung
mit `|` zerlegt, ordnet die laengste Form zuerst -- sonst misst er seine
Regex, nicht den Bestand.

ZWEI LAGEN, getrennt gezaehlt, weil sie Verschiedenes bedeuten:
  kollision       -- zwei verschiedene Abschnitte, dieselbe Kennung. Befund.
  wiederaufgreifen -- derselbe Abschnitt spaeter noch einmal aufgegriffen
                     ("§4 gegengerechnet", "S12 ist kein Forschungsschritt
                     mehr"). Das ist gewollte Fortschreibung und KEIN Fehler;
                     es als Kollision zu zaehlen wuerde genau die Arbeitsweise
                     bestrafen, die dieses Haus verlangt.

HINWEISRECHT, KEIN VETO: immer exit 0.

Aufruf:
    python3 melder/kennungskollision.py
    python3 melder/kennungskollision.py --selftest
"""
from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent

# LAENGSTE Alternative zuerst -- siehe Modulkopf.
KODE = re.compile(
    r"^(#{2,4})\s+(?:Aufgabe\s+)?("
    r"B4\.\d+[a-z]?|\d+\.\d+(?:\.\d+)*|§\d+|Linie\s+\w+|[SPGKB]\d+[a-z]?)\b"
)
# Wortmarken des Wiederaufgreifens -- irgendwo im Resttitel, nicht nur an
# zweiter Stelle: die Trenner sind uneinheitlich ("·", "—", ":").
WIEDER = re.compile(
    r"\b(ist|wird|bleibt|gegengerechnet|erneut|weiterhin|wieder|nachgetragen|"
    r"konkreter|nachtrag)\b", re.I
)


def sammle(ordner: Path) -> dict[str, dict[str, list[tuple[int, str]]]]:
    je_datei: dict[str, dict[str, list[tuple[int, str]]]] = collections.defaultdict(
        lambda: collections.defaultdict(list))
    for pfad in sorted(ordner.glob("*.md")):
        for nr, zeile in enumerate(pfad.read_text(encoding="utf-8").splitlines(), 1):
            m = KODE.match(zeile)
            if m:
                je_datei[pfad.name][m.group(2).strip()].append((nr, zeile[m.end(1):].strip()))
    return je_datei


def beurteile(je_datei) -> dict:
    kollisionen, wiederaufgreifen = [], []
    for datei, kodes in sorted(je_datei.items()):
        for kennung, vorkommen in sorted(kodes.items()):
            if len(vorkommen) < 2:
                continue
            eintrag = {"datei": datei, "kennung": kennung,
                       "stellen": [f"{datei}:{nr}" for nr, _ in vorkommen],
                       "titel": [t for _, t in vorkommen]}
            # Traegt EIN spaeteres Vorkommen eine Wortmarke, ist es
            # Fortschreibung desselben Abschnitts.
            if any(WIEDER.search(t) for _, t in vorkommen[1:]):
                wiederaufgreifen.append(eintrag)
            else:
                kollisionen.append(eintrag)
    return {"kollisionen": kollisionen, "wiederaufgreifen": wiederaufgreifen}


def _selftest() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        # DER FALL, DER DIE REGEX-REIHENFOLGE PRUEFT: sechs verschiedene
        # Abschnitte unter B4.x duerfen NICHT als eine Kennung B4 gelten.
        (d / "a.md").write_text(
            "### B4.1 — erstes\n### B4.2 — zweites\n### B4.3 — drittes\n"
            "## 104.1 Ist-Stand\n### 104.1.1 Spaltung\n### 104.1.2 Stichprobe\n",
            encoding="utf-8")
        # Echte Kollision: zwei verschiedene Abschnitte, dieselbe Kennung.
        (d / "b.md").write_text("## S7 — Der Abruf\n## S7 — Die Ablage\n", encoding="utf-8")
        # Wiederaufgreifen: derselbe Abschnitt, spaeter fortgeschrieben.
        (d / "c.md").write_text("## §4 Erfolgsmass\n### §4 gegengerechnet\n", encoding="utf-8")
        e = beurteile(sammle(d))

        assert not any(k["datei"] == "a.md" for k in e["kollisionen"]), \
            f"B4.x/104.1.x als Kollision gemeldet -- Regex-Reihenfolge kaputt: {e['kollisionen']}"
        assert [k["kennung"] for k in e["kollisionen"]] == ["S7"], e["kollisionen"]
        assert [w["kennung"] for w in e["wiederaufgreifen"]] == ["§4"], e["wiederaufgreifen"]
    print("kennungskollision: Selbsttest gruen (1 echte Kollision, 1 Wiederaufgreifen, "
          "B4.1-B4.3 und 104.1.x NICHT als Kollision gemeldet)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    e = beurteile(sammle(WURZEL / "docs"))
    print(f"docs/: {len(e['kollisionen'])} Kennungskollision(en), "
          f"{len(e['wiederaufgreifen'])} spaeteres Wiederaufgreifen (kein Befund)")
    for k in e["kollisionen"]:
        print(f"  KOLLISION {k['kennung']}: " + " · ".join(k["stellen"]))
        for t in k["titel"]:
            print(f"      {t[:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
