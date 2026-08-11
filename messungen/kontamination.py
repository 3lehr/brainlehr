#!/usr/bin/env python3
"""Hat der Antwortende die Loesung schon gekannt, bevor er die Aufgabe las?

ANLASS, gemessen am 2026-08-11 und der Grund, warum es dieses Werkzeug gibt:
Der dreigeteilte Antwortlauf (wissensnutzen_blind.py) lieferte fuer Aufgabe A
eine Verbesserung von 0,00 auf 0,67 -- bei Trefferguete FALSE, die Ziel-Lehre
L-c0e910 war also gar nicht im gemessenen Block. Die Erklaerung stand in den
Subagenten-Protokollen: der UserPromptSubmit-Haken (knowledge_recall_hook)
feuerte auf MEINEN Auftragstext an die Subagenten und spielte ihnen dabei
genau diese Lehre ein -- woertlich, samt "Stattdessen ActionScreen(...)".
Alle drei Antwortenden hatten die Loesung im Kontext, bevor sie die Datei mit
den Aufgaben ueberhaupt oeffneten.

Das Wort 'ActionScreen' kommt im gemessenen Block NICHT vor (geprueft: 0
Treffer im A|MIT-Prompt). Die 0,67 messen also den Haken, nicht den Block.

WARUM PRUEFEN STATT VERHINDERN: Der Haken laesst sich hier nicht abschalten --
er steht in den globalen Einstellungen des Betreibers, und ein Messwerkzeug,
das fremde Einstellungen umlegt, waere ein schlechterer Tausch. Ausserdem ist
Verhindern nie nachweisbar: dass etwas NICHT eingespielt wurde, sieht man
einer Zahl nicht an. Ein Befund am Protokoll dagegen ist ein Artefakt.

WAS GEPRUEFT WIRD: taucht ein TRAEGER der richtigen Antwort (das Wort, an dem
die check-Funktion die Antwort erkennt) im Kontext des Antwortenden auf, OHNE
im gestellten Prompt zu stehen? Dann ist die Zelle kontaminiert und zaehlt
nicht -- nicht "vermutlich", sondern nachweisbar an der Fundstelle.

WAS NICHT GEPRUEFT WIRD, und das ist die Decke: ob der Antwortende die Loesung
aus seinem Training kennt. Dagegen hilft kein Protokoll, nur eine Aufgabe, die
im Bestand steht und sonst nirgends. Zweite Decke: geprueft wird der TRAEGER,
nicht der Sinn -- eine Umschreibung derselben Regel ohne das Wort rutscht
durch.

Aufruf:
    python3 kontamination.py --protokolle <verzeichnis> --aufgaben <datei>
    python3 kontamination.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Traeger je Aufgabe: das Wort, an dem die check-Funktion in wissensnutzen.py
# die richtige Antwort erkennt. Bewusst hier wiederholt statt importiert -- die
# check-Funktionen sind Lambdas, aus denen sich das Wort nicht auslesen laesst,
# und ein Import zoege den ganzen Messaufbau samt Modellsperre mit herein.
# Preis: laeuft der check dort auseinander, merkt es dieses Modul nicht. Darum
# prueft der Selbsttest beide Richtungen gegen dieselben Woerter.
TRAEGER = {
    "A": ["ActionScreen"],
    "B": ["DEBUG_STATE_API"],
    "C": [],  # kein Ziel im Bestand -- eine Kontamination ist hier nicht definiert
}


def protokolltexte(verzeichnis: Path) -> dict[str, list[str]]:
    """Je Protokolldatei die Texte aller Nachrichten, die NICHT vom
    Antwortenden selbst stammen -- also das, was ihm zugetragen wurde."""
    texte: dict[str, list[str]] = {}
    for datei in sorted(verzeichnis.glob("agent-*.jsonl")):
        gesammelt: list[str] = []
        for zeile in datei.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                satz = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            if satz.get("type") != "user":
                continue
            gesammelt.append(json.dumps(satz, ensure_ascii=False))
        texte[datei.name] = gesammelt
    return texte


def pruefen(aufgaben: dict, protokolle: dict[str, list[str]]) -> dict:
    """Je Aufgabe: steht ein Traeger im zugetragenen Kontext, ohne im
    gestellten Prompt zu stehen?"""
    prompts = {z["key"]: z["prompt"] for z in aufgaben["zellen"]}
    befunde: list[dict] = []

    for key, prompt in prompts.items():
        task = key.split("|")[0]
        for wort in TRAEGER.get(task, []):
            im_prompt = wort in prompt
            fundstellen = [
                (name, i) for name, saetze in protokolle.items()
                for i, s in enumerate(saetze) if wort in s
            ]
            if fundstellen and not im_prompt:
                befunde.append({
                    "zelle": key, "traeger": wort,
                    "im_prompt": False,
                    "protokolle": sorted({n for n, _ in fundstellen}),
                    "urteil": "kontaminiert",
                })
            elif fundstellen and im_prompt:
                befunde.append({
                    "zelle": key, "traeger": wort, "im_prompt": True,
                    "protokolle": sorted({n for n, _ in fundstellen}),
                    "urteil": "erwartet -- der Traeger stand in der Aufgabe selbst",
                })

    kontaminiert = sorted({b["zelle"] for b in befunde if b["urteil"] == "kontaminiert"})
    return {
        "kontaminierte_zellen": kontaminiert,
        "befunde": befunde,
        "gepruefte_protokolle": sorted(protokolle),
        "urteil": ("Messung unbrauchbar fuer diese Zellen" if kontaminiert
                    else "keine Kontamination am Protokoll nachweisbar"),
    }


def _selftest() -> None:
    aufgaben = {"zellen": [
        {"key": "A|OHNE", "prompt": "Schreibe einen Bestaetigungsdialog."},
        {"key": "A|MIT", "prompt": "Schreibe einen Bestaetigungsdialog.\n<knowledge-recall>irgendwas</knowledge-recall>"},
        {"key": "B|MIT", "prompt": "Nenne den Befehl. Hinweis: DEBUG_STATE_API noetig."},
    ]}

    # 1) Traeger im zugetragenen Kontext, nicht im Prompt -> kontaminiert.
    ergebnis = pruefen(aufgaben, {"agent-1.jsonl": ['{"type":"user","x":"nutze ActionScreen(...)"}']})
    assert ergebnis["kontaminierte_zellen"] == ["A|MIT", "A|OHNE"], ergebnis["kontaminierte_zellen"]

    # 2) Gegenprobe: derselbe Traeger, aber IM Prompt -> kein Befund, sonst
    #    schluege die Pruefung bei jeder Aufgabe an, die ihre Loesung nennt.
    ergebnis2 = pruefen(aufgaben, {"agent-1.jsonl": ['{"type":"user","x":"DEBUG_STATE_API"}']})
    assert "B|MIT" not in ergebnis2["kontaminierte_zellen"], "Traeger aus dem Prompt ist keine Kontamination"
    assert any(b["im_prompt"] for b in ergebnis2["befunde"]), "der erwartete Fall muss trotzdem sichtbar sein"

    # 3) Negativfall: sauberes Protokoll -> gar kein Befund.
    ergebnis3 = pruefen(aufgaben, {"agent-1.jsonl": ['{"type":"user","x":"nichts davon"}']})
    assert ergebnis3["kontaminierte_zellen"] == [] and ergebnis3["befunde"] == []
    assert "keine Kontamination" in ergebnis3["urteil"]

    # 4) Nur Nachrichten des Antwortenden selbst zaehlen nicht als Zutrag --
    #    sonst waere jede richtige Antwort ihr eigener Kontaminationsbeweis.
    ergebnis4 = pruefen(aufgaben, {"agent-1.jsonl": []})
    assert ergebnis4["kontaminierte_zellen"] == []

    # 5) Aufgabe C hat kein Ziel -- dort ist Kontamination nicht definiert.
    aufg_c = {"zellen": [{"key": "C|MIT", "prompt": "kubectl?"}]}
    assert pruefen(aufg_c, {"a.jsonl": ['{"type":"user","x":"ActionScreen"}']})["befunde"] == []

    print("selftest ok (5 Faelle, Gegenprobe in beide Richtungen)", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--protokolle", type=Path, help="Verzeichnis mit agent-*.jsonl")
    p.add_argument("--aufgaben", type=Path, help="Aufgabendatei des Laufs")
    p.add_argument("--out", type=Path, help="Befund als JSON ablegen")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return
    if not (a.protokolle and a.aufgaben):
        p.error("--protokolle und --aufgaben werden beide gebraucht")

    aufgaben = json.loads(a.aufgaben.read_text(encoding="utf-8"))
    ergebnis = pruefen(aufgaben, protokolltexte(a.protokolle))

    print(ergebnis["urteil"])
    for b in ergebnis["befunde"]:
        print(f"  {b['zelle']:8s} {b['traeger']:18s} {b['urteil']} "
              f"({', '.join(b['protokolle'])})")
    if a.out:
        a.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        print(f"\nGeschrieben: {a.out}")


if __name__ == "__main__":
    main()
