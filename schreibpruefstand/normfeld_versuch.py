"""Kontrollversuch: wirkt num_ctx, deutsche Feldbeschreibung oder ein
Beispiel auf die Ausbeute von norm_rang/gilt_ab bei gemma4:e4b?

Weg fuer Prompt-Bau und Ollama-Aufruf: aus schreiblauf.py IMPORTIERT
(build_prompt, DEFAULT_OLLAMA_URL, KEEP_ALIVE, _parse_model_json) --
schreiblauf.py bleibt unveraendert (Auftragsgrenze: nur diese eine neue
Datei). Nur der eigentliche HTTP-Aufruf ist hier lokal nachgebaut, weil
schreiblauf._call_ollama kein "options"-Feld (num_ctx) kennt und Variante V2
einen eigenen Prompt braucht (deutsche Feldbeschreibung) -- beides liesse
sich nicht durch reinen Import erreichen, ohne schreiblauf.py anzufassen.

Gemessen wird NUR Prompt+Modellantwort, kein knowledge_add()-Aufruf: der
Auftrag verlangt "wie oft norm_rang/gilt_ab gesetzt", das steht schon im
rohen JSON der Modellantwort, ein Schreibversuch in die Demo-DB liefert dazu
nichts. demo_db.build_demo_db() liefert nur den Baumzustand fuer den Prompt
(wie in schreiblauf.build_prompt gefordert), es wird kein zweites Mal
geschrieben.

ABWEICHUNG vom Auftrag (Code vor Annahme gelesen, siehe Vorgabe "halte dich
an den Code"): stadtwerke_material.py hat AKTUELL 7 Normstuecke (Index 0-6,
STADTWERKE_ERWARTUNG beginnt 7x mit "norm_"), nicht 6 wie im Auftrag
angenommen. runs/stadtwerke-gemma-e4b.json (vorhandener Lauf, Modell
gemma4:e4b) zeigt fuer genau diese 7 Stuecke norm_rang 3x, gilt_ab 4x
gesetzt -- nicht 1x/3x wie im Auftrag vermutet. Diese Diskrepanz wird unten
in main() ausgegeben statt verschwiegen; V0 wird trotzdem gefahren und roh
berichtet, ein Abbruch wegen der Mengendifferenz waere keine Pruefung mehr.
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

import argparse
import copy
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SCHREIBPRUEFSTAND_DIR = Path(__file__).resolve().parent
SHARED_KNOWLEDGE = SCHREIBPRUEFSTAND_DIR.parent
sys.path.insert(0, str(SCHREIBPRUEFSTAND_DIR))
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import demo_db  # noqa: E402
import knowledge_mcp_server as kms  # noqa: E402
import schreiblauf  # noqa: E402
import stadtwerke_material as swm  # noqa: E402

MODEL = "gemma4:e4b"
N_RUNS = 3
FIELDS_OF_INTEREST = ("norm_rang", "gilt_ab")

# Norm-Teilmenge: alles, dessen erwartete Sorte mit "norm_" beginnt.
NORM_INDICES = [i for i, sorte in enumerate(swm.STADTWERKE_ERWARTUNG) if sorte.startswith("norm_")]
NORM_STUECKE = [swm.STADTWERKE_MATERIAL[i] for i in NORM_INDICES]

_BEISPIEL_STUECK = (
    "Sozialtarif-Zuschlag entfaellt zum 01.03.2027 vollstaendig, loest die "
    "Uebergangsregelung von 2022 ab."
)
_BEISPIEL_ANTWORT = {
    "parent_path": "/wissensnetz-pflegeverbund",
    "title": "Sozialtarif-Zuschlag entfaellt 01.03.2027",
    "summary": "Sozialtarif-Zuschlag entfaellt zum 01.03.2027, loest Regelung von 2022 ab.",
    "norm_rang": 2,
    "gilt_ab": "2027-03-01",
    "source": "erzeugt aus Rohmaterial (Beispiel)",
}


def _build_prompt_v2_deutsch(raw_text: str, tree: list[dict]) -> str:
    """Wie schreiblauf.build_prompt, aber norm_rang/gilt_ab/gilt_bis im
    Schema mit deutscher description -- alles andere (Werkzeugtext, Ablauf)
    unveraendert, sonst waere nicht mehr EINE Sache geaendert."""
    tool = copy.deepcopy(kms.TOOLS["knowledge_add"])
    props = tool["inputSchema"]["properties"]
    props["norm_rang"]["description"] = "Optional: Rang einer Norm (1=globale Direktive, 2=Hub-Direktive, 3=ADR). Bei einem reinen Fakt weglassen."
    props["gilt_ab"]["description"] = "Optional: ISO-8601-Datum/Zeitstempel, ab dem die Norm gilt"
    props["gilt_bis"]["description"] = "Optional: ISO-8601-Datum/Zeitstempel, bis zu dem die Norm gilt; bei unbefristet weglassen. Darf nicht vor gilt_ab liegen."
    tree_lines = "\n".join(f"- {n['path']} ({n['title']}, project_id={n['project_id']})" for n in tree)
    return f"""Du bist ein Agent mit Zugriff auf ein Werkzeug, das Wissen in einer \
Baumstruktur-Datenbank ablegt.

Werkzeug: knowledge_add
Beschreibung: {tool["description"]}
Parameter (JSON Schema): {json.dumps(tool["inputSchema"], ensure_ascii=False)}

Vorhandene Knoten im Baum (parent_path muss einer dieser Pfade sein, ausser \
du setzt neuer_ast=true):
{tree_lines}

Rohmaterial:
\"\"\"{raw_text}\"\"\"

Halte das fest. Antworte AUSSCHLIESSLICH mit einem einzelnen JSON-Objekt, \
das die Parameter von knowledge_add enthaelt (mindestens parent_path, \
title, summary). Kein Fliesstext davor oder danach."""


def _build_prompt_v3_beispiel(raw_text: str, tree: list[dict]) -> str:
    """Wie schreiblauf.build_prompt, plus EIN ausgearbeitetes Beispiel
    (Normstueck -> JSON mit norm_rang/gilt_ab) vor dem eigentlichen
    Rohmaterial."""
    base = schreiblauf.build_prompt(raw_text, tree)
    beispiel = (
        f'Beispiel -- Rohmaterial: "{_BEISPIEL_STUECK}"\n'
        f"Beispiel -- richtige Antwort: {json.dumps(_BEISPIEL_ANTWORT, ensure_ascii=False)}\n\n"
    )
    marker = "Rohmaterial:\n"
    idx = base.index(marker)
    return base[:idx] + beispiel + base[idx:]


def _call_ollama(prompt: str, *, model: str, base_url: str, timeout: float,
                  options: dict | None = None) -> tuple[str | None, str | None]:
    """Wie schreiblauf._call_ollama, zusaetzlich optionales 'options'-Feld
    (fuer num_ctx in V1) -- Kopie statt Import, weil das Original kein
    options-Feld hat und schreiblauf.py laut Auftrag nicht geaendert wird."""
    payload = {"model": model, "prompt": prompt, "stream": False, "keep_alive": schreiblauf.KEEP_ALIVE}
    if options:
        payload["options"] = options
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return None, f"Ollama-Aufruf fehlgeschlagen: {exc}"
    return body.get("response", ""), None


VARIANTEN = {
    "V0_unveraendert": {"prompt_fn": schreiblauf.build_prompt, "options": None},
    "V1_num_ctx_8192": {"prompt_fn": schreiblauf.build_prompt, "options": {"num_ctx": 8192}},
    "V2_deutsche_feldbeschreibung": {"prompt_fn": _build_prompt_v2_deutsch, "options": None},
    "V3_ein_beispiel": {"prompt_fn": _build_prompt_v3_beispiel, "options": None},
}


def _one_lauf(variante: str, *, model: str, base_url: str, timeout: float,
              tree: list[dict]) -> dict:
    """Ein Durchlauf ueber alle NORM_STUECKE mit einer Variante. Gibt
    Rohzahlen zurueck: je Feld wie oft gesetzt, wie oft unbrauchbar."""
    cfg = VARIANTEN[variante]
    n_norm_rang = 0
    n_gilt_ab = 0
    n_unbrauchbar = 0
    per_stueck = []
    for idx, raw_text in zip(NORM_INDICES, NORM_STUECKE):
        prompt = cfg["prompt_fn"](raw_text, tree)
        raw_response, call_error = _call_ollama(
            prompt, model=model, base_url=base_url, timeout=timeout, options=cfg["options"])
        if call_error is not None:
            n_unbrauchbar += 1
            per_stueck.append({"index": idx, "unbrauchbar": True, "grund": call_error})
            continue
        parsed = schreiblauf._parse_model_json(raw_response)
        if parsed is None:
            n_unbrauchbar += 1
            per_stueck.append({"index": idx, "unbrauchbar": True, "grund": "kein valides JSON"})
            continue
        hat_norm_rang = "norm_rang" in parsed and parsed["norm_rang"] not in (None, "")
        hat_gilt_ab = "gilt_ab" in parsed and parsed["gilt_ab"] not in (None, "")
        n_norm_rang += int(hat_norm_rang)
        n_gilt_ab += int(hat_gilt_ab)
        per_stueck.append({
            "index": idx, "unbrauchbar": False,
            "norm_rang": parsed.get("norm_rang"), "gilt_ab": parsed.get("gilt_ab"),
        })
    return {
        "variante": variante, "n_stuecke": len(NORM_STUECKE),
        "norm_rang": n_norm_rang, "gilt_ab": n_gilt_ab, "unbrauchbar": n_unbrauchbar,
        "per_stueck": per_stueck,
    }


def run(*, model: str = MODEL, base_url: str = schreiblauf.DEFAULT_OLLAMA_URL,
        timeout: float = schreiblauf.CALL_TIMEOUT, n_runs: int = N_RUNS) -> dict:
    db_path = demo_db.build_demo_db()
    kms.DB_PATH = db_path
    tree = schreiblauf._current_tree(db_path)

    started = time.perf_counter()
    laeufe: dict[str, list[dict]] = {v: [] for v in VARIANTEN}
    for variante in VARIANTEN:
        for lauf_nr in range(n_runs):
            ergebnis = _one_lauf(variante, model=model, base_url=base_url, timeout=timeout, tree=tree)
            ergebnis["lauf_nr"] = lauf_nr
            laeufe[variante].append(ergebnis)
    runtime = time.perf_counter() - started

    tabelle = {}
    for variante, ergebnisse in laeufe.items():
        for feld in ("norm_rang", "gilt_ab", "unbrauchbar"):
            werte = [e[feld] for e in ergebnisse]
            tabelle.setdefault(variante, {})[feld] = {
                "werte": werte,
                "mittelwert": statistics.mean(werte),
                "spannweite": max(werte) - min(werte),
            }

    return {
        "model": model,
        "n_runs_je_variante": n_runs,
        "n_stuecke": len(NORM_STUECKE),
        "norm_indices": NORM_INDICES,
        "runtime_seconds": runtime,
        "laeufe": laeufe,
        "tabelle": tabelle,
    }


def _selftest() -> None:
    """Netzlos: prueft Feld-Erkennung und Prompt-Varianten ohne Ollama."""
    assert len(NORM_STUECKE) >= 1, "keine Normstuecke gefunden"

    tree = [{"path": "/", "title": "Wurzel", "project_id": "shared"}]
    p0 = schreiblauf.build_prompt(NORM_STUECKE[0], tree)
    p2 = _build_prompt_v2_deutsch(NORM_STUECKE[0], tree)
    p3 = _build_prompt_v3_beispiel(NORM_STUECKE[0], tree)
    assert "Rang einer Norm" in p2 and "Rang einer Norm" not in p0, \
        "V2 muss deutsche Feldbeschreibung enthalten, V0 nicht"
    # Nachtrag Auftrag 2026-08-06: V0 zieht jetzt live kms.TOOLS["knowledge_add"]
    # (schreiblauf.build_prompt liest die Werkzeugbeschreibung 1:1), und genau
    # dorthinein wanderte das V3-Beispiel -- p0 enthaelt es seitdem ABSICHTLICH
    # auch. Nur noch pruefen, dass V3 es enthaelt (die eigentliche Bedingung
    # fuer den V3-Lauf), das alte "V0 nicht" waere jetzt ein Falschbefund.
    assert _BEISPIEL_STUECK in p3, "V3 muss das Beispielstueck enthalten"
    assert p3.index(_BEISPIEL_STUECK) < p3.index(NORM_STUECKE[0]), \
        "Beispiel muss vor dem eigentlichen Rohmaterial stehen"

    class _Modul:
        pass

    fake_module = sys.modules[__name__]
    orig = fake_module._call_ollama
    try:
        fake_module._call_ollama = lambda *a, **k: (
            '{"norm_rang": 2, "gilt_ab": "2027-01-01"}', None)
        r = _one_lauf("V0_unveraendert", model="m", base_url="u", timeout=1.0, tree=tree)
        assert r["norm_rang"] == len(NORM_STUECKE) and r["gilt_ab"] == len(NORM_STUECKE), \
            f"Felderkennung falsch bei Volltreffer: {r}"

        fake_module._call_ollama = lambda *a, **k: (None, "Ollama-Aufruf fehlgeschlagen: timed out")
        r2 = _one_lauf("V0_unveraendert", model="m", base_url="u", timeout=1.0, tree=tree)
        assert r2["unbrauchbar"] == len(NORM_STUECKE) and r2["norm_rang"] == 0, \
            f"Ausfall muss unbrauchbar zaehlen, nicht norm_rang: {r2}"
    finally:
        fake_module._call_ollama = orig

    print(f"selftest ok: {len(NORM_STUECKE)} Normstuecke (Index {NORM_INDICES}), "
          f"Feld-/Prompt-Erkennung korrekt", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--base-url", default=schreiblauf.DEFAULT_OLLAMA_URL)
    ap.add_argument("--timeout", type=float, default=schreiblauf.CALL_TIMEOUT)
    ap.add_argument("--n-runs", type=int, default=N_RUNS)
    ap.add_argument("--out", default=str(SCHREIBPRUEFSTAND_DIR / "runs" / "normfeld-versuch.json"))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return

    print(f"Abweichung vom Auftrag: {len(NORM_STUECKE)} Normstuecke im Code "
          f"(Index {NORM_INDICES}), nicht 6 wie angenommen.", file=sys.stderr)

    result = run(model=args.model, base_url=args.base_url, timeout=args.timeout, n_runs=args.n_runs)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Ergebnis geschrieben: {args.out}", file=sys.stderr)
    print(json.dumps(result["tabelle"], ensure_ascii=False, indent=2))
    print(f"Laufzeit gesamt: {result['runtime_seconds']:.1f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
