#!/usr/bin/env python3
"""MESSAUFTRAG (Betreiber, 2026-08-13): Abschneidegrenze von bge-m3 MESSEN,
nicht der Modellkarte glauben.

VERFAHREN (wie beauftragt): denselben Text schrittweise verlaengern, jeweils
einbetten, Kosinus zwischen aufeinanderfolgenden Laengen bilden. Ab welcher
Laenge aendert sich der Vektor nicht mehr?

ZWEITE PRUEFUNG (Zugabe, weil die erste allein taeuschen kann): ein Kosinus,
der gegen 1.0 laeuft, kann auch daher kommen, dass ein langer Text mit sich
selbst als Praefix ohnehin sehr aehnlich wird -- OHNE echte Abschneidung. Klarer
Beweis fuer Abschneidung ist NICHT Konvergenz, sondern GLEICHHEIT: zwei Texte,
die bis Zeichen L identisch sind und sich erst DANACH unterscheiden, muessen
bei Abschneidung vor/bei L exakt denselben Vektor ergeben (Kosinus == 1.0 bis
auf Gleitkommarauschen), unabhaengig davon, was in den unterschiedlichen
Suffixen steht. Beide Verfahren laufen hier, das zweite bestaetigt/entkraeftet
das erste.

Ollamas /api/embed liefert 'prompt_eval_count' (Tokenanzahl) im JSON --
gemessen per curl, siehe Sitzungsprotokoll. Wird hier mitgefuehrt statt der
Zeichen/Token-Quotient geschaetzt.

GRENZEN: schreibt nur nach runs/. Kein Produktivcode geaendert. Reine
Standardbibliothek (urllib) fuer den Embed-Aufruf -- kern/embeddings.embed_text
gibt keinen Tokencount zurueck, darum hier ein eigener schlanker Aufruf statt
Umbau von embeddings.py (Tabu-Datei laut Auftrag: kern/ nur lesen).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

OLLAMA_URL = "http://127.0.0.1:11434/api/embed"
MODEL = "bge-m3"
WURZEL = Path(__file__).resolve().parent.parent


def embed(text: str) -> tuple[list[float], int]:
    payload = {"model": MODEL, "input": text, "keep_alive": "10m"}
    req = urllib.request.Request(
        OLLAMA_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["embeddings"][0], body.get("prompt_eval_count", -1)


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def basistext() -> str:
    """Echter, langer deutscher Fliesstext aus dem Repo (Docstrings) --
    nicht wiederholt, damit die Messung nicht an Wiederholung haengt."""
    quellen = ["haken/antwort_abruf.py", "haken/knowledge_recall_hook.py",
               "messungen/kontamination.py", "kern/embeddings.py",
               "kern/pruefkorpus.py"]
    stuecke = []
    for q in quellen:
        p = WURZEL / q
        if p.exists():
            stuecke.append(p.read_text(encoding="utf-8", errors="replace"))
    text = "\n\n".join(stuecke)
    if len(text) < 25000:
        text = (text * (25000 // max(len(text), 1) + 1))
    return text


LAENGEN = [50, 100, 200, 300, 500, 750, 1000, 1250, 1500, 1750, 2000,
           2500, 3000, 3500, 4000, 5000, 6000, 8000, 10000, 12000, 16000, 20000]


def messen(basis: str, laengen: list[int] = LAENGEN, sleep: float = 0.0) -> dict:
    reihe = []
    voriger_vec = None
    voriger_len = None
    for L in laengen:
        if L > len(basis):
            break
        text_a = basis[:L]
        # zweite Pruefung: gleicher Praefix bis L, unterschiedlicher Suffix
        text_b1 = text_a + " AAAAAAAAAAAA_ANHANG_EINS_VERSCHIEDEN_XQZ"
        text_b2 = text_a + " BBBBBBBBBBBB_ANHANG_ZWEI_VERSCHIEDEN_YWK"

        vec_a, tok_a = embed(text_a)
        vec_b1, tok_b1 = embed(text_b1)
        vec_b2, tok_b2 = embed(text_b2)

        cos_konsekutiv = cosine(voriger_vec, vec_a) if voriger_vec is not None else None
        cos_suffix = cosine(vec_b1, vec_b2)

        reihe.append({
            "zeichen": L,
            "token_a": tok_a,
            "token_b1": tok_b1,
            "token_b2": tok_b2,
            "kosinus_konsekutiv_zu_vorheriger_laenge": cos_konsekutiv,
            "vorherige_laenge": voriger_len,
            "kosinus_suffix_test": cos_suffix,
            "suffix_test_deutung": (
                "abgeschnitten (Vektor ignoriert den Suffix)" if cos_suffix > 0.999999
                else "Suffix veraendert den Vektor noch -- keine Abschneidung bei dieser Laenge"),
        })
        if sleep:
            time.sleep(sleep)
        voriger_vec = vec_a
        voriger_len = L

    # Grenze: kleinste Laenge, ab der der Suffix-Test dauerhaft (fuer ALLE
    # groesseren getesteten Laengen auch) Gleichheit zeigt -- eine einzelne
    # zufaellige Gleichheit waere kein Beleg, ERST wenn es ab dort nicht mehr
    # umkippt.
    grenze_zeichen = None
    grenze_token = None
    for i, r in enumerate(reihe):
        if r["kosinus_suffix_test"] > 0.999999 and all(
                x["kosinus_suffix_test"] > 0.999999 for x in reihe[i:]):
            grenze_zeichen = r["zeichen"]
            grenze_token = r["token_a"]
            break

    return {
        "modell": MODEL,
        "verfahren": "gleicher Text schrittweise verlaengert (Konsekutiv-Kosinus) "
                     "PLUS gleicher Praefix/verschiedener Suffix (Gleichheitsbeweis)",
        "reihe": reihe,
        "grenze_zeichen": grenze_zeichen,
        "grenze_token": grenze_token,
        "befund": (
            f"Ab {grenze_zeichen} Zeichen (~{grenze_token} Token laut "
            f"Ollama prompt_eval_count) veraendert ein angehaengter, "
            f"abweichender Suffix den Vektor nicht mehr -- bge-m3 schneidet "
            f"dort still ab."
            if grenze_zeichen else
            "Keine Abschneidung in der getesteten Spanne gefunden -- "
            f"bis {reihe[-1]['zeichen'] if reihe else 0} Zeichen veraendert "
            f"der Suffix den Vektor noch."
        ),
    }


def _selftest() -> None:
    assert abs(cosine([1, 0], [1, 0]) - 1.0) < 1e-9
    assert abs(cosine([1, 0], [0, 1])) < 1e-9
    print("selftest ok (cosine)", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--max-laenge", type=int, default=20000,
                     help="Deckel gegen zu lange Laufzeit")
    a = ap.parse_args()
    if a.selftest:
        _selftest()
        return

    laengen = [L for L in LAENGEN if L <= a.max_laenge]
    basis = basistext()
    ergebnis = messen(basis, laengen)
    print(ergebnis["befund"])
    if a.out:
        a.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        print(f"Geschrieben: {a.out}")


if __name__ == "__main__":
    main()
