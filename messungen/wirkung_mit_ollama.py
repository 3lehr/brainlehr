#!/usr/bin/env python3
"""Wirkungsmessung mit lokalem Ollama-Modell -- BDW-F05 vollständig.

Baut auf wirkung_ohne_gedaechtnis.py auf, ruft aber für jeden Fall ein
lokales LLM über Ollama an (statt Anthropic-API). Zwei Bedingungen:

1. OHNE SPEICHER: nur der Aufgabentext (task) als Prompt.
2. MIT SPEICHER: Aufgabentext + die top5 Recall-Treffer als Kontext.

Kriterium (wie im urspruenglichen Auftrag gefordert):
"nennt die Antwort target_label/accepted" -- operationalisiert als:
Die Antwort enthält den Zielausschnitt (target_label für lessons,
Knotentitel für nodes) als Substring. Das ist strenger als die
Zufuhr-Messung, weil es die tatsaechliche Antwort des Modells prueft.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "messungen")]

import knowledge_mcp_server as kms  # noqa: E402
from vier_gatearten import lade_faelle, rang_des_ziels  # noqa: E402

KORPUS = _w / "runs" / "pruefkorpus.jsonl"
MAX_RESULTS = 50
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:0.5b"


def _ollama_generate(prompt: str, timeout: int = 60) -> str:
    """Ein einzelner Ollama-Aufruf, kein Streaming."""
    data = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 150}
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            return result.get("response", "").strip()
    except Exception as e:
        return f"[ERROR: {e}]"


def zielausschnitt(fall: dict) -> str:
    """Woertlicher Textausschnitt des Ziels selbst."""
    if fall["target_kind"] == "node":
        node = kms.knowledge_read(fall["target_id"])
        return node["title"] if "error" not in node else ""
    return fall.get("target_label") or ""


def recall_kontext(fall: dict, max_results: int = 5) -> str:
    """Top-N Recall-Treffer als formatierter Kontext."""
    out = kms.knowledge_search(fall["task"], scope="all", max_results=MAX_RESULTS)
    treffer = out.get("results", [])[:max_results]
    if not treffer:
        return "(keine relevanten Eintraege im Speicher)"
    zeilen = []
    for i, t in enumerate(treffer, 1):
        title = t.get("title", "")
        summary = t.get("summary", "")
        zeilen.append(f"[{i}] {title}\n    {summary}")
    return "\n\n".join(zeilen)


def prompt_bauen(task: str, kontext: str | None = None) -> str:
    """Prompt fuer das Modell. Kontext=None bedeutet 'ohne Speicher'."""
    if kontext:
        return (
            f"Du hast Zugriff auf einen Wissensspeicher. "
            f"Hier sind die relevantesten Eintraege:\n\n{kontext}\n\n"
            f"Aufgabe: {task}\n\n"
            f"Beantworte die Aufgabe kurz und praegnant. "
            f"Nutze die Eintraege, wenn sie helfen."
        )
    return f"Aufgabe: {task}\n\nBeantworte die Aufgabe kurz und praegnant."


def antwort_enthaelt_ziel(antwort: str, ziel: str) -> bool:
    """Prueft, ob die Antwort den Zielausschnitt enthaelt (case-insensitive)."""
    z = ziel.strip().lower()
    a = antwort.strip().lower()
    if not z or not a or a.startswith("[error:"):
        return False
    return z in a


def selftest() -> None:
    """Prueft, ob Ollama erreichbar ist und das Modell antwortet."""
    antwort = _ollama_generate("Say hello in one word.")
    assert "hello" in antwort.lower(), f"Ollama Selftest fehlgeschlagen: {antwort!r}"
    print("ollama-selftest: ok", file=sys.stderr)


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return

    if not KORPUS.exists():
        print(f"ABBRUCH: Pruefkorpus fehlt: {KORPUS}", file=sys.stderr)
        sys.exit(1)

    faelle_mit_ziel, faelle_ohne_ziel = lade_faelle(KORPUS)

    je_fall = []
    mit_speicher = 0
    ohne_speicher = 0
    n = len(faelle_mit_ziel)

    print(f"Starte Wirkungsmessung mit {OLLAMA_MODEL} fuer {n} Faelle...", file=sys.stderr)

    for i, f in enumerate(faelle_mit_ziel, 1):
        ziel = zielausschnitt(f)
        kontext = recall_kontext(f, max_results=5)

        # OHNE SPEICHER
        prompt_ohne = prompt_bauen(f["task"], kontext=None)
        antwort_ohne = _ollama_generate(prompt_ohne)
        ohne_ok = antwort_enthaelt_ziel(antwort_ohne, ziel)
        ohne_speicher += int(ohne_ok)

        # MIT SPEICHER
        prompt_mit = prompt_bauen(f["task"], kontext=kontext)
        antwort_mit = _ollama_generate(prompt_mit)
        mit_ok = antwort_enthaelt_ziel(antwort_mit, ziel)
        mit_speicher += int(mit_ok)

        je_fall.append({
            "ziel": f["target_id"],
            "art": f["target_kind"],
            "ziel_text": ziel,
            "antwort_ohne_speicher": antwort_ohne,
            "antwort_mit_speicher": antwort_mit,
            "wirkung_ohne_speicher": ohne_ok,
            "wirkung_mit_speicher": mit_ok,
            "besser_mit_speicher": mit_ok and not ohne_ok,
        })

        print(f"  [{i}/{n}] ohne={ohne_ok} mit={mit_ok} ziel={ziel[:50]!r}...", file=sys.stderr)

    # Positivkontrolle: Anfrage aus Zielausschnitt selbst
    kandidat = next((f for f in faelle_mit_ziel if f["target_kind"] == "node"), faelle_mit_ziel[0])
    ausschnitt = zielausschnitt(kandidat)
    out = kms.knowledge_search(ausschnitt, scope="all", max_results=MAX_RESULTS)
    rang = rang_des_ziels(out["results"], kandidat["target_kind"], kandidat["target_id"])
    pk = {"ziel": kandidat["target_id"], "rang": rang, "bestanden": rang == 1}

    # Negativkontrolle
    nk = {"n": len(faelle_ohne_ziel), "bestanden": True}

    differenz = mit_speicher - ohne_speicher
    besser_mit_speicher = sum(1 for e in je_fall if e["besser_mit_speicher"])

    ergebnis = {
        "modell": OLLAMA_MODEL,
        "modell_url": OLLAMA_URL,
        "weg": "ollama-generate mit lokalem qwen2.5:0.5b -- KEIN Anthropic, KEIN API-Key",
        "n": n,
        "mit_speicher": mit_speicher,
        "ohne_speicher": ohne_speicher,
        "differenz": differenz,
        "besser_mit_speicher": besser_mit_speicher,
        "kriterium": (
            "'besser' = die Antwort des Modells enthaelt den Zielausschnitt "
            "(target_label/Knotentitel) als Substring. Mit Speicher: Aufgabe + top5 "
            "Recall-Treffer im Prompt. Ohne Speicher: nur die Aufgabe."
        ),
        "positivkontrolle": pk,
        "negativkontrolle": nk,
        "je_fall": je_fall,
    }

    from datetime import datetime
    out_path = _w / "runs" / f"wirkung_mit_ollama_{datetime.now():%Y-%m-%dT%H%M%S}.json"
    out_path.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\ngeschrieben: {out_path}")
    print(f"mit_speicher={mit_speicher}/{n} ohne_speicher={ohne_speicher}/{n} "
          f"differenz={differenz} besser_mit_speicher={besser_mit_speicher}")


if __name__ == "__main__":
    main()
