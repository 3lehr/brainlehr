"""Parameterblock fuer Ergebnisdateien unter runs/ (Auftrag 2026-08-07,
Knoten 557ab47f, Punkt 2 "Konfiguration im Ergebnis"): eine Ergebnisdatei
ohne Methodenteil ist nicht wiederholbar. schnappschuss() liest die
Stellschrauben aus knowledge_recall_hook.py (nur gelesen, nicht importiert
veraendert) plus Embedding-Modell und Bestandsgroessen aus knowledge.db.

Aufruf in einem Messskript, das nach runs/ schreibt:
    from messparameter import schnappschuss
    ergebnis["konfiguration"] = schnappschuss()
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parent
HUB = SHARED_KNOWLEDGE.parent
DB = SHARED_KNOWLEDGE / "knowledge.db"

if str(HUB / "scripts") not in sys.path:
    sys.path.insert(0, str(HUB / "scripts"))
import knowledge_recall_hook as hook  # noqa: E402


def schnappschuss() -> dict:
    """Stellschrauben + Embedding-Modell + Bestandsgroessen zum Zeitpunkt
    des Aufrufs. Kein Platzhalter fuer Fehlendes -- fehlt ein Wert, wird der
    Schluessel weggelassen statt mit None/"?" gefuellt."""
    block: dict = {
        "min_hits": hook.MIN_HITS,
        "explore_rate": hook.EXPLORE_RATE,
        "trust_weight": hook.TRUST_WEIGHT,
        "max_nodes": hook.MAX_NODES,
        "max_lessons": hook.MAX_LESSONS,
        "noise_floor_mad_mult": hook.NOISE_FLOOR_MAD_MULT,
        "radar_min_sample_n": hook.RADAR_MIN_SAMPLE_N,
        "full_scan_row_cap": hook.FULL_SCAN_ROW_CAP,
        "project_calibration_min_samples": hook.PROJECT_CALIBRATION_MIN_SAMPLES,
        "ensemble_top_n": hook.ENSEMBLE_TOP_N,
        "zweiter_kanal": hook._zweiter_kanal_aktiv(),
        "ensemble_pflicht": hook._ensemble_pflicht_aktiv(),
    }

    try:
        con = sqlite3.connect(str(DB))
        try:
            row = con.execute(
                "SELECT value FROM knowledge_config WHERE key = 'embed_model'"
            ).fetchone()
            if row:
                block["embed_model"] = row[0]
            block["bestand_knowledge_nodes"] = con.execute(
                "SELECT COUNT(*) FROM knowledge_nodes"
            ).fetchone()[0]
            block["bestand_lessons_learned"] = con.execute(
                "SELECT COUNT(*) FROM lessons_learned"
            ).fetchone()[0]
            block["bestand_knowledge_embeddings"] = con.execute(
                "SELECT COUNT(*) FROM knowledge_embeddings"
            ).fetchone()[0]
        finally:
            con.close()
    except sqlite3.Error:
        pass  # Stellschrauben (Modul-Import) sind das Wichtigere, DB optional

    return block


def demo() -> None:
    b = schnappschuss()
    assert b["min_hits"] == hook.MIN_HITS
    assert isinstance(b["zweiter_kanal"], bool)
    assert "embed_model" in b or "bestand_knowledge_nodes" not in b
    print("demo ok:", b)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
        sys.exit(0)
    import json
    print(json.dumps(schnappschuss(), indent=2, ensure_ascii=False))
