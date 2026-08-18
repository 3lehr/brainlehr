#!/usr/bin/env python3
"""BEFUND vor der Messung: kein Paket 'anthropic', kein ANTHROPIC_API_KEY in
dieser Umgebung (gemessen 2026-08-18, gleicher Befund wie in
messungen/anfrageumschrift_produktivweg.py). L-a69129 verlangt Haiku ueber
die Anthropic-API fuer Modellvergleiche -- das faellt damit aus. Gemessen
wird deshalb NICHT die Antwortguete, sondern nur die ZUFUHR: was ein Modell
mit vs. ohne Speicher im Prompt saehe. Das ist ausdruecklich weniger als
"Wirkung" (Auftrag, woertlich: "dann ausdruecklich, dass die Wirkung NICHT
gemessen ist, sondern nur die Zufuhr").

WEG: knowledge_mcp_server.knowledge_search() -- derselbe Aufruf wie
messungen/vier_gatearten.py, kein Nachbau. lade_faelle/rang_des_ziels von
dort importiert (dieselbe Logik, keine zweite Kopie).

KRITERIUM ("besser"), samt Verwerfung des Auftragsvorschlags:
Der Auftrag schlaegt vor: "nennt die Antwort target_label/accepted". Ohne
Modellaufruf gibt es keine Antwort zu bewerten -- das Kriterium ist auf
dieser Stufe nicht pruefbar. Ersatzkriterium, EINE Stufe vor der Antwort:
"enthaelt die ZUFUHR (das, was dem Modell vor der Antwort vorliegt) die
Kernaussage des Ziels?" Fuer die Speicher-Zufuhr operationalisiert als: Ziel
liegt unter den top5 von knowledge_search(task) -- identisch zu Gate 1 aus
messungen/vier_gatearten.py (top5, keine neue Zahl). Fuer die
Ohne-Speicher-Zufuhr: enthaelt der Aufgabentext (`task`) selbst schon woert-
lich den Zielausschnitt (target_label bzw. Knotentitel)? Wenn ja, kann
"besser" nicht am Speicher liegen, weil die Aussage schon ohne ihn vorlag.

POSITIVKONTROLLE: wie in vier_gatearten.py -- Anfrage aus einem woertlichen
Ausschnitt DES ZIELS SELBST. Muss Rang 1 liefern, sonst ist "mit Speicher
hilft" mit diesem Aufbau nicht herstellbar.

NEGATIVKONTROLLE: die 10 category=negative-Faelle (ziellos, fremde
Sachgebiete). Fuer sie gibt es kein target_label -- "besser" ist nicht
definierbar, mit_speicher/ohne_speicher zaehlen dort NICHT. Geprueft wird
stattdessen, ob die Speicher-Zufuhr dort faelschlich als "passend" auftritt
(Gate 2 aus vier_gatearten.py, gleicher Mechanismus) -- wenn ja, wuerde ein
Kriterium, das nur auf "System liefert etwas" abstellt, faelschlich Wirkung
zeigen. Bleibt sie 0 (bzw. auf dem dortigen Schwellenwert), misst das
Kriterium hier tatsaechlich Zielbezug und nicht Geschwaetzigkeit.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "messungen")]

import knowledge_mcp_server as kms  # noqa: E402 -- Produktivweg, kein Nachbau
from vier_gatearten import lade_faelle, rang_des_ziels  # noqa: E402 -- wiederverwendet, nicht kopiert

KORPUS = _w / "runs" / "pruefkorpus.jsonl"
K_SPEICHER = 5  # dieselbe Grenze wie Gate 1 (top5) in vier_gatearten.py
MAX_RESULTS = 50  # deckt top50 ab, Rang jenseits davon zaehlt als kein Treffer

try:
    import anthropic  # noqa: F401
    _HAT_ANTHROPIC = True
except ImportError:
    _HAT_ANTHROPIC = False
import os
_HAT_SCHLUESSEL = bool(os.environ.get("ANTHROPIC_API_KEY"))
_MODELL_VERFUEGBAR = _HAT_ANTHROPIC and _HAT_SCHLUESSEL


def zielausschnitt(fall: dict) -> str:
    """Woertlicher Textausschnitt des Ziels selbst -- fuer node der Titel
    (ueber knowledge_read), fuer lesson bereits target_label."""
    if fall["target_kind"] == "node":
        node = kms.knowledge_read(fall["target_id"])
        return node["title"] if "error" not in node else ""
    return fall.get("target_label") or ""


def ohne_speicher_enthaelt_ziel(fall: dict, ausschnitt: str) -> bool:
    """Prueft, ob der Aufgabentext selbst (einzige Zufuhr ohne Speicher)
    bereits woertlich den Zielausschnitt traegt -- grobe, aber transparente
    Substring-Pruefung, keine Fuzzy-Bewertung, weil hier keine Falschmeldung
    zugunsten von 'besser' entstehen darf."""
    a = ausschnitt.strip().lower()
    if not a:
        return False
    return a in fall["task"].strip().lower()


def mit_speicher_enthaelt_ziel(fall: dict) -> tuple[bool, int | None]:
    out = kms.knowledge_search(fall["task"], scope="all", max_results=MAX_RESULTS)
    rang = rang_des_ziels(out["results"], fall["target_kind"], fall["target_id"])
    return (rang is not None and rang <= K_SPEICHER), rang


def positivkontrolle(faelle_mit_ziel: list[dict]) -> dict:
    kandidat = next((f for f in faelle_mit_ziel if f["target_kind"] == "node"), faelle_mit_ziel[0])
    ausschnitt = zielausschnitt(kandidat)
    out = kms.knowledge_search(ausschnitt, scope="all", max_results=MAX_RESULTS)
    rang = rang_des_ziels(out["results"], kandidat["target_kind"], kandidat["target_id"])
    return {"ziel": kandidat["target_id"], "anfrage_ausschnitt": ausschnitt,
            "rang": rang, "bestanden": rang == 1}


def negativkontrolle(faelle_ohne_ziel: list[dict]) -> dict:
    zeilen = []
    for f in faelle_ohne_ziel:
        out = kms.knowledge_search(f["task"], scope="all", max_results=10)
        lage = out.get("bestandslage", {}).get("lage") if out["results"] else "leer"
        zeilen.append({"frage": f["task"], "lage": lage, "faelschlich_passend": lage == "passend"})
    n_verletzt = sum(1 for z in zeilen if z["faelschlich_passend"])
    return {"n": len(zeilen), "faelschlich_passend": n_verletzt,
            "bestanden": n_verletzt == 0, "je_frage": zeilen}


def selftest() -> None:
    f_node = {"target_kind": "node", "task": "Wie gehen wir mit Zeitgrenzen bei Sitzungen um?"}
    assert ohne_speicher_enthaelt_ziel(f_node, "Zeitgrenzen") is True
    assert ohne_speicher_enthaelt_ziel(f_node, "nicht enthaltener Text xyz") is False
    assert ohne_speicher_enthaelt_ziel(f_node, "") is False
    print("selftest: ok", file=sys.stderr)


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return

    if not KORPUS.exists():
        print(f"ABBRUCH: Pruefkorpus fehlt: {KORPUS}", file=sys.stderr)
        sys.exit(1)

    faelle_mit_ziel, faelle_ohne_ziel = lade_faelle(KORPUS)

    pk = positivkontrolle(faelle_mit_ziel)
    nk = negativkontrolle(faelle_ohne_ziel)

    je_fall = []
    mit_speicher = 0
    ohne_speicher = 0
    for f in faelle_mit_ziel:
        ausschnitt = zielausschnitt(f)
        ohne = ohne_speicher_enthaelt_ziel(f, ausschnitt)
        mit, rang = mit_speicher_enthaelt_ziel(f)
        mit_speicher += int(mit)
        ohne_speicher += int(ohne)
        je_fall.append({"ziel": f["target_id"], "art": f["target_kind"],
                         "rang_mit_speicher": rang, "zufuhr_ohne_speicher_enthaelt_ziel": ohne,
                         "zufuhr_mit_speicher_enthaelt_ziel": mit})

    n = len(faelle_mit_ziel)
    ergebnis = {
        "weg": "knowledge_mcp_server.knowledge_search() -- echter Produktivweg (identisch zu "
               "messungen/vier_gatearten.py), kein Modellaufruf in dieser Messung",
        "modell_verfuegbar": _MODELL_VERFUEGBAR,
        "befund_modell": (
            "Modellvergleich (Haiku ueber Anthropic-API, L-a69129) nicht durchfuehrbar: "
            f"Paket 'anthropic' installiert={_HAT_ANTHROPIC}, ANTHROPIC_API_KEY gesetzt="
            f"{_HAT_SCHLUESSEL}. Gemessen wird deshalb NICHT die Antwortguete/Wirkung, "
            "sondern nur die ZUFUHR (was dem Modell mit vs. ohne Speicher vorlaege)."
        ),
        "kriterium": (
            "'besser' = die Zufuhr enthaelt die Kernaussage des Ziels, BEVOR ein Modell "
            "antwortet. Ohne Speicher: der Aufgabentext (task) selbst enthaelt bereits "
            "woertlich den Zielausschnitt (target_label/Knotentitel). Mit Speicher: das Ziel "
            "liegt unter den top5 von knowledge_search(task) -- dieselbe Grenze wie Gate 1 in "
            "vier_gatearten.py, keine neu erfundene Schwelle. Der im Auftrag vorgeschlagene "
            "Massstab ('nennt die Antwort target_label/accepted') ist ohne Modellaufruf nicht "
            "pruefbar und wurde deshalb auf die Stufe VOR der Antwort zurueckgezogen."
        ),
        "n": n,
        "mit_speicher": mit_speicher,
        "ohne_speicher": ohne_speicher,
        "differenz": mit_speicher - ohne_speicher,
        "grenze": [
            "Gemessen ist die Zufuhr, nicht die Wirkung -- kein Modell hat je eine Antwort "
            "erzeugt, siehe befund_modell.",
            "Ohne-Speicher-Kriterium ist eine Substring-Pruefung (task enthaelt Zielausschnitt "
            "woertlich) -- unterschaetzt moegliches Weltwissen des Modells (z.B. wenn es die "
            "Kernaussage OHNE Speicher und OHNE woertliche Erwaehnung im Prompt selbst wuesste).",
            "Mit-Speicher-Kriterium unterstellt, dass ein unter top5 gelisteter Treffer auch "
            "tatsaechlich in den Prompt injiziert wuerde -- das haengt vom echten Recall-Hook "
            "ab (haken/knowledge_recall_hook.py), der hier nicht mitlaeuft.",
            "35 Faelle sind klein, ein knapper Unterschied ist kein Ergebnis.",
            "Gilt fuer einen Zeitpunkt (2026-08-18) gegen den aktuell laufenden Bestand.",
        ],
        "positivkontrolle": pk,
        "negativkontrolle": nk,
        "je_fall": je_fall,
    }

    if not pk["bestanden"]:
        print("BEFUND: Positivkontrolle NICHT bestanden -- Aufbau verdaechtig.", file=sys.stderr)
    if not nk["bestanden"]:
        print(f"BEFUND: Negativkontrolle verletzt -- {nk['faelschlich_passend']} von "
              f"{nk['n']} zielosen Faellen faelschlich 'passend'.", file=sys.stderr)
    referenz_top5 = sum(1 for e in je_fall if e["rang_mit_speicher"] is not None and e["rang_mit_speicher"] <= 5)
    if referenz_top5 != 7 or n != 35:
        print(f"BEFUND: Abweichung von der Referenzmessung (top5=7/35 erwartet, hier "
              f"top5={referenz_top5}/{n}).", file=sys.stderr)

    out_path = _w / "runs" / f"wirkung_ohne_gedaechtnis_{__import__('datetime').datetime.now():%Y-%m-%dT%H%M%S}.json"
    out_path.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"geschrieben: {out_path}")
    print(f"mit_speicher={mit_speicher}/{n} ohne_speicher={ohne_speicher}/{n} "
          f"differenz={mit_speicher - ohne_speicher} positivkontrolle={pk['bestanden']} "
          f"negativkontrolle={nk['bestanden']}")


if __name__ == "__main__":
    main()
