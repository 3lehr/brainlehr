#!/usr/bin/env python3
"""Entscheidungsmessung fuer docs/PLAN_KALIBRIERBREMSE_2026-08-13.md.

Ersetzt messungen/kalibrierbremse_wirkung.py (2026-08-12): jene Messung
belegte, dass die Bremse HEUTE folgenlos ist (project_id hartcodiert None,
Uebersteuerungstabelle leer). Diese Messung beantwortet die Folgefrage aus
dem Plan, die ueber Verdrahten (A) oder Ausbauen (B) entscheidet:

    Laesst sich der Schwellenwert je Projekt aus dem vorhandenen Bestand
    MESSEN, oder muesste er GERATEN werden?

Zwei Groessen dafuer noetig, beide hier gemessen:
1. Rohbestand je project_id (Knotenzahl) -- ob ein Projekt ueberhaupt die
   PROJECT_CALIBRATION_MIN_SAMPLES-Schwelle (50) reisst.
2. ETIKETTIERTE Abruf-Faelle je Projekt (Prompt -> bekanntes Zielobjekt) aus
   den echten Korpora unter runs/echtkorpus*.json -- das ist die Groesse, die
   eine echte Eichung des Rauschmultiplikators braucht (ein Schwellenwert
   wird gegen bekannte Treffer/Fehlgriffe gemessen, nicht gegen rohe
   Knotenzahl). Ohne genug etikettierte Faelle waere jeder Zahlenwert
   geraten, auch wenn die Knotenzahl hoch ist.

Aufruf:
    python3 messungen/kalibrierbremse_messung_2026-08-13.py
    python3 messungen/kalibrierbremse_messung_2026-08-13.py --selftest
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w), str(_w / "kern")]

from kern import speicher  # noqa: E402 -- Naht statt eigener Verbindung

WURZEL = _w
PROJECT_CALIBRATION_MIN_SAMPLES = 50  # muss mit haken/knowledge_recall_hook.py uebereinstimmen


def knoten_je_projekt(conn) -> dict[str, int]:
    rows = conn.execute(
        "SELECT project_id, COUNT(*) FROM knowledge_nodes GROUP BY project_id"
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def etikettierte_faelle_je_projekt(conn) -> dict[str, int]:
    """Zaehlt, fuer wie viele echte Korpus-Faelle (runs/echtkorpus*.json,
    keine .gegenprobe.json/.rasterblick.json-Ableitungen) ein Knoten-Ziel
    einem project_id zugeordnet werden kann. Dedupliziert ueber die ersten
    80 Zeichen des Prompts, weil dieselben Faelle in mehreren Korpus-
    Schnappschuessen wiederkehren."""
    rows = conn.execute("SELECT path, project_id FROM knowledge_nodes").fetchall()
    pfad_zu_projekt = {p: proj for p, proj in rows}

    dateien = sorted(
        f for f in glob.glob(str(WURZEL / "runs" / "echtkorpus*.json"))
        if ".gegenprobe.json" not in f and ".rasterblick.json" not in f
    )
    gesehen: set[str] = set()
    zaehler: dict[str, int] = {}
    for datei in dateien:
        try:
            daten = json.loads(Path(datei).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        faelle = daten.get("faelle") if isinstance(daten, dict) else daten
        if not isinstance(faelle, list):
            continue
        for fall in faelle:
            if not isinstance(fall, dict):
                continue
            schluessel = fall.get("prompt", "")[:80]
            if schluessel in gesehen:
                continue
            gesehen.add(schluessel)
            for ziel in fall.get("ziele", []):
                if not isinstance(ziel, dict) or ziel.get("art") != "knoten":
                    continue
                projekt = pfad_zu_projekt.get(ziel.get("id"))
                if projekt:
                    zaehler[projekt] = zaehler.get(projekt, 0) + 1
    return zaehler


def messen() -> dict:
    with speicher.lesen() as conn:
        knoten = knoten_je_projekt(conn)
        faelle = etikettierte_faelle_je_projekt(conn)

    ueber_knotenschwelle = sorted(
        p for p, n in knoten.items() if n >= PROJECT_CALIBRATION_MIN_SAMPLES)
    gesamt_projekte = len(knoten)
    gesamt_faelle = sum(faelle.values())

    return {
        "project_calibration_min_samples": PROJECT_CALIBRATION_MIN_SAMPLES,
        "knoten_je_projekt": knoten,
        "projekte_gesamt": gesamt_projekte,
        "projekte_ueber_knotenschwelle": ueber_knotenschwelle,
        "anteil_ueber_knotenschwelle": f"{len(ueber_knotenschwelle)}/{gesamt_projekte}",
        "etikettierte_faelle_je_projekt": faelle,
        "etikettierte_faelle_gesamt": gesamt_faelle,
        "befund": (
            "Rohbestand allein reicht nicht: 3 von "
            f"{gesamt_projekte} Projekten reissen die Knotenschwelle "
            f"({', '.join(ueber_knotenschwelle)}), aber selbst das groesste "
            "davon (shared) traegt nur "
            f"{faelle.get('shared', 0)} etikettierte Abruf-Faelle im echten "
            "Korpus -- ADR-035 kalibrierte den GEMEINSAMEN Wert schon mit 24 "
            "Aufgaben und markierte selbst DAS als Grenze einer "
            "Parametersuche. Ein Bruchteil davon je Projekt waere Ueberan"
            "passung an Einzelfaelle, keine Eichung. Der Schwellenwert je "
            "Projekt ist damit nicht messbar, sondern nur zu raten -- "
            "Entscheidung B (ausbauen) nach der Regel im Plan."
        ),
    }


def demo() -> None:
    ergebnis = messen()
    assert ergebnis["projekte_gesamt"] > 0
    assert set(ergebnis["projekte_ueber_knotenschwelle"]) <= set(ergebnis["knoten_je_projekt"])
    # Rot-vor-gruen-Anker: solange kein Projekt (ausser den dokumentierten,
    # nicht-eichbaren) zugleich die Knotenschwelle UND eine im ADR-035-
    # Massstab tragfaehige Fallzahl (>=24, siehe Befund oben) erreicht, bleibt
    # B die richtige Antwort. Bricht dieser Assert kuenftig, ist genau der
    # Zeitpunkt gekommen, an dem A neu zu pruefen ist.
    tragfaehig = [
        p for p in ergebnis["projekte_ueber_knotenschwelle"]
        if ergebnis["etikettierte_faelle_je_projekt"].get(p, 0) >= 24
    ]
    assert tragfaehig == [], (
        "Ein Projekt erreicht jetzt sowohl die Knotenschwelle als auch eine "
        "tragfaehige Fallzahl -- A neu pruefen", tragfaehig)
    print("demo ok:", json.dumps(ergebnis, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
        sys.exit(0)
    print(json.dumps(messen(), ensure_ascii=False, indent=2))
