"""Misst knowledge_recall_hook.query() gegen den Pruefkorpus V2 (korrigiertes
Zitat-Kriterium, siehe pruefkorpus_v2.py). Reine Wiederverwendung von
messlauf_abrufguete.py (messe/eichung/messlauf/STATES/run_case/target_hit) --
nur importiert und mit dem V2-Korpus aufgerufen, Originaldatei nicht
veraendert (Grenze laut Auftrag: uebrige Messwerkzeuge nur lesen).

Ausfuehren: python3 messlauf_abrufguete_v2.py
Ergebnis: shared-knowledge/runs/messlauf_abrufguete_v2.json
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

import json
import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parent
sys.path.insert(0, str(SHARED_KNOWLEDGE))
import messlauf_abrufguete as m  # noqa: E402  -- nur gelesen/aufgerufen
from messparameter import schnappschuss  # noqa: E402

CORPUS = SHARED_KNOWLEDGE / "runs/pruefkorpus_v2.jsonl"
RESULT = SHARED_KNOWLEDGE / "runs/messlauf_abrufguete_v2.json"


def load_cases() -> list[dict]:
    cases = [json.loads(l) for l in open(CORPUS, encoding="utf-8")]
    assert len(cases) == 45, f"V2-Korpus hat {len(cases)} Faelle, erwartet 45 -- Datei geaendert?"
    return cases


def demo() -> None:
    """Ponytail-Selbsttest wie in messlauf_abrufguete.py: Zustand A gegen die
    echte DB, kein Ollama."""
    cases = load_cases()
    with m._with_state(m.STATES["A_beide_aus"]):
        r = m.messe(cases)
    assert set(r) == {"trefferguete", "falsches_schweigen", "richtiges_schweigen", "falsches_sprechen"}
    for n, d in r.values():
        assert 0 <= n <= d
    print("demo ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
        sys.exit(0)
    cases = load_cases()
    ergebnis = {"messlauf": m.messlauf(cases)}
    if "--eichung-only" not in sys.argv:
        ergebnis["eichung"] = m.eichung(cases)
    ergebnis["konfiguration"] = schnappschuss()
    RESULT.parent.mkdir(exist_ok=True)
    RESULT.write_text(json.dumps(ergebnis, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\ngeschrieben: {RESULT}")
