#!/usr/bin/env python3
"""Messskript zum Auftrag "warum greifen unsere Regeln nicht?" (2026-08-12).

NUR LESEN/MESSEN, kein Bauauftrag. Zaehlt und prueft, was in der Textantwort
(runs/regelgriff_2026-08-12.json) als Zahl steht -- damit jede Zahl hier
nachvollziehbar bleibt statt nur behauptet zu sein. Kein Zugriff auf
tabuierte Dateien, keine Schreibaenderung an app/, kern/, migrationen/ usw.

Aufruf: python3 messungen/regelgriff_2026-08-12.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "kern"))
import speicher  # noqa: E402

GLOBAL_CLAUDE = Path.home() / ".claude" / "CLAUDE.md"
SETTINGS = Path.home() / ".claude" / "settings.json"


def zaehle_claude_abschnitte(pfad: Path) -> int:
    """Eine Regel = ein '## '-Abschnitt. Grobe, aber im Haus schon einmal
    benutzte Zaehlweise (siehe kern/regelpaket.py: '18 global + 17 hub,
    beide Zahlen mit grep -c "^## " nachgezaehlt')."""
    text = pfad.read_text(encoding="utf-8")
    return len(re.findall(r"^## ", text, flags=re.MULTILINE))


def zaehle_hook_skripte(settings_pfad: Path) -> set[str]:
    d = json.loads(settings_pfad.read_text(encoding="utf-8"))
    skripte = set()
    for _, gruppen in d.get("hooks", {}).items():
        for g in gruppen:
            for hk in g.get("hooks", []):
                for m in re.findall(r"(\S+\.(?:py|sh))", hk.get("command", "")):
                    skripte.add(m)
    return skripte


def norm_rang_knoten() -> dict:
    """Fall (a), keine Ausnahme: reiner Lesezugriff auf den gemeinsamen
    Bestand (SELECT count) -- genau der Fall, fuer den speicher.lesen()
    gebaut wurde. Kein Grund, an haken.ort vorbeizulesen."""
    with speicher.lesen() as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM knowledge_nodes WHERE norm_rang IS NOT NULL")
        gesamt = cur.fetchone()[0]
        cur.execute(
            "SELECT norm_entscheidung, count(*) FROM knowledge_nodes GROUP BY norm_entscheidung"
        )
        entscheidung = dict(cur.fetchall())
    return {"knoten_mit_norm_rang": gesamt, "norm_entscheidung": entscheidung}


def pre_push_installiert(repos: list[str]) -> dict:
    out = {}
    for r in repos:
        p = Path("/Volumes/daten/Begod2026") / r / ".git" / "hooks" / "pre-push"
        out[r] = p.is_file()
    return out


def main() -> None:
    befund = {}
    befund["claude_md_global_abschnitte"] = zaehle_claude_abschnitte(GLOBAL_CLAUDE)
    hub_claude = Path("/Volumes/daten/Begod2026/hub/CLAUDE.md")
    if hub_claude.exists():
        befund["claude_md_hub_abschnitte"] = zaehle_claude_abschnitte(hub_claude)
    befund["projekt_claude_md_vorhanden"] = (WURZEL / "CLAUDE.md").exists()
    skripte = zaehle_hook_skripte(SETTINGS)
    befund["hook_skripte_gesamt"] = len(skripte)
    befund["hook_skripte"] = sorted(skripte)
    befund["knowledge_norm"] = norm_rang_knoten()
    befund["pre_push_hook_je_repo"] = pre_push_installiert(
        ["brainlehr", "hub", "fahrtenbuch", "openlehr", "wohlair",
         "buckeberg", "sigmaforge", "schnaeppvalid"]
    )
    print(json.dumps(befund, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
