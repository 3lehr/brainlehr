#!/usr/bin/env python3
"""Findet absolute Pfade in knowledge_nodes/lessons_learned. NUR LESEND.
Schreibt runs/absolute_pfade_rohfund.json -- keine DB-Schreibung hier.

Muster: /Volumes/daten/Begod2026, /Volumes/daten/be_old, /Volumes/daten/videoki,
/Users/lehrmacbook -- gefolgt von Nicht-Leerraum (Pfadrest).

Bewusst NICHT per Wortsuche (z.B. blosses "Begod2026"): das traf auch reine
Projektnamen-Erwaehnungen und einen Regex-Literal im Fliesstext (Beleg in
runs/absolute_pfade_vorschlag.md), die keinen echten Dateipfad tragen.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kern import speicher

MUSTER = re.compile(
    r"/(?:Volumes/daten/(?:Begod2026|be_old|videoki)|Users/lehrmacbook)[^\s`'\")]*"
)

NODE_FELDER = ["title", "summary", "content"]
LESSON_FELDER = ["description", "root_cause", "resolution", "prevention", "pruefstelle"]


def funde(text: str) -> list[str]:
    if not isinstance(text, str):
        return []
    return sorted(set(MUSTER.findall(text)))


def kontext(text: str, pfad: str, radius: int = 70) -> str:
    idx = text.find(pfad)
    if idx < 0:
        return ""
    return text[max(0, idx - radius):idx + len(pfad) + radius].replace("\n", " ")


def main() -> None:
    ergebnisse = []
    with speicher.lesen() as conn:
        for row in conn.execute(
            "SELECT id, freigabe, title, summary, content FROM knowledge_nodes"
        ):
            for feld in NODE_FELDER:
                text = row[feld]
                for pfad in funde(text):
                    ergebnisse.append({
                        "tabelle": "knowledge_nodes",
                        "id": row["id"],
                        "feld": feld,
                        "freigabe": row["freigabe"],
                        "pfad": pfad,
                        "kontext": kontext(text, pfad),
                    })
        for row in conn.execute(
            "SELECT id, freigabe, description, root_cause, resolution, prevention, "
            "pruefstelle FROM lessons_learned"
        ):
            for feld in LESSON_FELDER:
                text = row[feld]
                for pfad in funde(text):
                    ergebnisse.append({
                        "tabelle": "lessons_learned",
                        "id": row["id"],
                        "feld": feld,
                        "freigabe": row["freigabe"],
                        "pfad": pfad,
                        "kontext": kontext(text, pfad),
                    })

    knoten_ids = sorted({e["id"] for e in ergebnisse if e["tabelle"] == "knowledge_nodes"})
    lehren_ids = sorted({e["id"] for e in ergebnisse if e["tabelle"] == "lessons_learned"})
    print(f"knowledge_nodes betroffen: {len(knoten_ids)}")
    print(f"lessons_learned betroffen: {len(lehren_ids)}")

    out = Path(__file__).resolve().parent / "absolute_pfade_rohfund.json"
    out.write_text(json.dumps(ergebnisse, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"geschrieben: {out} ({len(ergebnisse)} Fund-Zeilen)")


if __name__ == "__main__":
    main()
