#!/usr/bin/env python3
"""Misst ALLE VIER Gatearten aus BDW-P04-AC1 (docs/REQUIREMENTS_BRAINLEHR.md:
"Ein versionierter Pruefkorpus misst alle vier Gatearten und weist Schwellen
aus.") ueber den ECHTEN Weg -- knowledge_mcp_server.knowledge_search(),
identischer Aufruf wie messungen/anfrageumschrift_produktivweg.py, kein
Nachbau. kern/kanalguete_messung.py deckt nur 2 von 4 Gatearten UND ueber
einen parallelen Suchpfad (siehe dessen eigener Modulkopf) -- keine Deckung
fuer AC1.

DIE VIER GATEARTEN:
  1. TREFFER      -- Ziel unter den ersten k?
  2. FALSCHMELDUNG -- ziellose Anfrage, System behauptet trotzdem einen Treffer.
  3. ABSTENTION    -- ziellose Anfrage, System schweigt (Gegenstueck zu 2,
                       nicht dasselbe: gemessen wird der Anteil der KORREKTEN
                       Enthaltungen, nicht die Fehlerquote).
  4. AKTION        -- NICHT GEMESSEN. Siehe Begruendung im Ergebnis unter
                       gatearten.aktion. Eine erfundene vierte Zahl waere
                       schlimmer als eine fehlende Gateart (Auftrag, woertlich).

KORPUS: runs/pruefkorpus.jsonl, 35 Faelle mit target_id (category
lesson/fact/norm, accepted=true) fuer Gate 1, dieselbe Teilmenge wie
messungen/anfrageumschrift_produktivweg.py::lade_faelle. 10 Faelle OHNE
target_id (category=negative) fuer Gate 2/3 -- QUELLE dieser 10: bereits im
Korpus vorbereitete Fragen aus fremden Sachgebieten (macOS-Terminal,
Seemannschaft/Knoten, Kubernetes, Gaststaettenrecht, Kochen/Backen,
Astronomie/Orbitalmechanik, Gartenbau, Netzwerktechnik, Git) -- Themen, zu
denen dieser Bestand (Code/Rechtslage/Steuer/Lehre dieses Hauses) keine
Antwort enthaelt. Diese 10 lagen VOR diesem Auftrag schon im Korpus (category
"negative", nicht neu angelegt).

ZIELABGLEICH (L-0e0ab6, wortwoertlich aus der Vorlage uebernommen):
target_kind=="node" -> Vergleich gegen result["path"], NICHT result["id"].
target_kind=="lesson" -> Vergleich gegen result["id"].

GATE 2/3-MECHANISMUS: knowledge_search() filtert nicht hart (kern/
relevanzlage.py, dessen eigener Befund: ein Schwellwert kauft weniger
Falschmeldungen mit verlorenen Treffern -- 8 statt 40 Falschmeldungen, aber
nur noch 32 statt 37 Treffer, gemessen 2026-08-16 an cc458fb3). Es traegt
aber pro Antwort ein "bestandslage.lage" (passend/schwach/uneindeutig/
ohne_bedeutungskanal), aus genau dieser Messung, MIT den beiden dort
gemessenen Schwellen STARK_AB=0.586 / ABSTAND_AB=0.043 (kern/relevanzlage.py,
nicht veraendert, nur gelesen). "passend" heisst: System behauptet einen
Treffer. Alles andere (schwach/uneindeutig/ohne_bedeutungskanal, ODER
count==0) heisst: System enthaelt sich. Diese Studie lieferte selbst schon
einen SCHWELLENWERT fuer die erwartete Falschmeldequote unter "passend":
rund 8 von 40 = 0.20 (dort so benannt) -- diese Messung hier prueft, ob der
heutige Bestand diesen Wert haelt, mit den 10 pruefkorpus-eigenen Faellen
statt den 40 der Ursprungsmessung (andere Stichprobe, siehe Grenze).

POSITIVKONTROLLE (eine, fuer alle drei gemessenen Gatearten gemeinsam
tragfaehig): Anfrage = woertlicher Textausschnitt aus dem ZIEL selbst
(Knotentitel per knowledge_read, oder target_label bei Lehren) -- der Treffer
liegt damit per Konstruktion vor. Muss Rang 1 UND bestandslage.lage=="passend"
liefern. Bestehet sie nicht, ist "passend" als Zustand nicht erreichbar (der
Aufbau ist verdaechtig, nicht das System) -- und dann sind Gate 2/3 nicht
aussagekraeftig, weil "passend" nie feuert.

WEG: knowledge_mcp_server.knowledge_search() -- kein Nachbau."""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "kern")]

import knowledge_mcp_server as kms  # noqa: E402 -- der Produktivweg selbst
import relevanzlage  # noqa: E402 -- nur gelesen: STARK_AB/ABSTAND_AB, hier zitiert

KORPUS = _w / "runs" / "pruefkorpus.jsonl"
MAX_RESULTS = 50  # deckt top50 ab, siehe anfrageumschrift_produktivweg.py

# Aus kern/relevanzlage.py-Docstring, Messung 2026-08-16 (cc458fb3): bei
# "passend" (STARK_AB/ABSTAND_AB) lag die Falschmeldequote bei rund 8/40=0.20,
# die korrekte Enthaltung entsprechend bei rund 32/40=0.80. Keine neu erfundene
# Schwelle -- dieselbe Zahl, dieselbe Quelle wie der Filtermechanismus selbst.
SCHWELLE_FALSCHMELDUNG = 0.20  # bestanden, wenn NICHT ueberschritten
SCHWELLE_ABSTENTION = 0.80  # bestanden, wenn NICHT unterschritten
# Fuer Gate 1 gibt es KEINE dokumentierte Zielzahl im Bestand (Auftrag:
# "Schwelle offen, heutiger Wert X" statt geschoenter Wert) -- siehe Ergebnis.


def lade_faelle(korpus: Path) -> tuple[list[dict], list[dict]]:
    """Wie messungen/anfrageumschrift_produktivweg.py::lade_faelle, aber
    zusaetzlich die target-losen (category=negative) Faelle fuer Gate 2/3."""
    mit_ziel, ohne_ziel = [], []
    with korpus.open(encoding="utf-8") as f:
        for zeile in f:
            zeile = zeile.strip()
            if not zeile:
                continue
            d = json.loads(zeile)
            if not d.get("accepted", True):
                continue
            if d.get("target_kind"):
                mit_ziel.append(d)
            elif d.get("category") == "negative":
                ohne_ziel.append(d)
    return mit_ziel, ohne_ziel


def rang_des_ziels(results: list[dict], target_kind: str, target_id: str) -> int | None:
    feld = "path" if target_kind == "node" else "id"
    for platz, r in enumerate(results, start=1):
        if r.get(feld) == target_id:
            return platz
    return None


def messe_treffer(faelle: list[dict]) -> dict:
    zeilen = []
    for f in faelle:
        out = kms.knowledge_search(f["task"], scope="all", max_results=MAX_RESULTS)
        rang = rang_des_ziels(out["results"], f["target_kind"], f["target_id"])
        zeilen.append({"ziel": f["target_id"], "art": f["target_kind"], "rang": rang})
    n = len(zeilen)
    gefunden = [z["rang"] for z in zeilen if z["rang"] is not None]
    return {
        "n": n,
        "top5": sum(1 for r in gefunden if r <= 5),
        "top50": sum(1 for r in gefunden if r <= 50),
        "median_rang_gefunden": int(st.median(gefunden)) if gefunden else None,
        "totalausfaelle": sum(1 for z in zeilen if z["rang"] is None),
        "je_frage": zeilen,
    }


def messe_falschmeldung_und_abstention(faelle: list[dict]) -> tuple[dict, dict]:
    zeilen = []
    for f in faelle:
        out = kms.knowledge_search(f["task"], scope="all", max_results=10)
        lage = out.get("bestandslage", {}).get("lage") if out["results"] else "leer"
        passend = lage == "passend"
        zeilen.append({"frage": f["task"], "anzahl_treffer": out["count"],
                        "lage": lage, "falschmeldung": passend})
    n = len(zeilen)
    fm_quote = sum(1 for z in zeilen if z["falschmeldung"]) / n
    abst_quote = sum(1 for z in zeilen if not z["falschmeldung"]) / n
    fm = {"n": n, "wert": round(fm_quote, 4), "schwelle": SCHWELLE_FALSCHMELDUNG,
          "bestanden": fm_quote <= SCHWELLE_FALSCHMELDUNG,
          "quelle_faelle": "runs/pruefkorpus.jsonl, category=negative, 10 Faelle aus fremden "
                            "Sachgebieten (macOS, Seemannschaft, Kubernetes, Gaststaettenrecht, "
                            "Kochen, Astronomie, Gartenbau, Netzwerktechnik, Git) -- vor diesem "
                            "Auftrag bereits im Korpus vorbereitet, nicht neu angelegt",
          "je_frage": zeilen}
    abst = {"n": n, "wert": round(abst_quote, 4), "schwelle": SCHWELLE_ABSTENTION,
            "bestanden": abst_quote >= SCHWELLE_ABSTENTION,
            "quelle_faelle": fm["quelle_faelle"], "je_frage": zeilen}
    return fm, abst


def positivkontrolle(faelle_mit_ziel: list[dict]) -> dict:
    """Nimmt den ersten Node-Fall (falls vorhanden, sonst den ersten
    ueberhaupt), formt die Anfrage aus einem woertlichen Ausschnitt DES
    ZIELS SELBST -- Treffer liegt per Konstruktion vor. Fuer node: Titel via
    knowledge_read (target_id ist der Pfad). Fuer lesson: target_label
    (bereits ein woertlicher Ausschnitt der Lehrenbeschreibung, siehe
    Korpus-Erzeugung dieser Datei)."""
    kandidat = next((f for f in faelle_mit_ziel if f["target_kind"] == "node"), faelle_mit_ziel[0])
    if kandidat["target_kind"] == "node":
        node = kms.knowledge_read(kandidat["target_id"])
        if "error" in node:
            return {"bestanden": False, "fehler": node["error"], "ziel": kandidat["target_id"]}
        ausschnitt = node["title"]
    else:
        ausschnitt = kandidat["target_label"]
    out = kms.knowledge_search(ausschnitt, scope="all", max_results=MAX_RESULTS)
    rang = rang_des_ziels(out["results"], kandidat["target_kind"], kandidat["target_id"])
    lage = out.get("bestandslage", {}).get("lage") if out["results"] else "leer"
    return {"ziel": kandidat["target_id"], "art": kandidat["target_kind"],
            "anfrage_ausschnitt": ausschnitt, "rang": rang, "lage": lage,
            "bestanden": rang == 1 and lage == "passend"}


def selftest() -> None:
    ergebnisse = [{"path": "a/b", "kind": "node"}, {"id": "L-x", "kind": "lesson"}]
    assert rang_des_ziels(ergebnisse, "node", "a/b") == 1
    assert rang_des_ziels(ergebnisse, "lesson", "L-x") == 2
    assert rang_des_ziels(ergebnisse, "node", "fehlt") is None
    print("selftest: ok", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return

    if not KORPUS.exists():
        print(f"ABBRUCH: Pruefkorpus fehlt: {KORPUS}", file=sys.stderr)
        sys.exit(1)
    faelle_mit_ziel, faelle_ohne_ziel = lade_faelle(KORPUS)

    pk = positivkontrolle(faelle_mit_ziel)
    treffer = messe_treffer(faelle_mit_ziel)
    fm, abst = messe_falschmeldung_und_abstention(faelle_ohne_ziel)

    treffer_gate = {
        "wert": round(treffer["top5"] / treffer["n"], 4),
        "k": 5,
        "schwelle": None,
        "schwelle_begruendung": "offen -- kein dokumentierter Zielwert fuer Trefferquote im "
                                 "Bestand (siehe brainlehr/CLAUDE.md, Frage 3: 'Was ist ein "
                                 "Treffer wert? -- offen'). Heutiger Wert wird ausgewiesen, "
                                 "nicht geschoent bestanden.",
        "bestanden": None,
        "top5": treffer["top5"], "top50": treffer["top50"], "n": treffer["n"],
        "median_rang_gefunden": treffer["median_rang_gefunden"],
        "totalausfaelle": treffer["totalausfaelle"],
        "quelle_faelle": "runs/pruefkorpus.jsonl, category in (lesson,fact,norm), "
                          "accepted=true, target_kind gesetzt -- 35 Faelle",
        "je_frage": treffer["je_frage"],
    }

    ergebnis = {
        "weg": "knowledge_mcp_server.knowledge_search() -- echter Produktivweg, kein Nachbau "
               "(identischer Aufruf wie messungen/anfrageumschrift_produktivweg.py)",
        "korpus": {
            "datei": "runs/pruefkorpus.jsonl",
            "n_treffer": treffer["n"],
            "n_falschmeldung": fm["n"],
            "n_abstention": abst["n"],
            "n_aktion": 0,
        },
        "positivkontrolle": pk,
        "gatearten": {
            "treffer": treffer_gate,
            "falschmeldung": fm,
            "abstention": abst,
            "aktion": {
                "gemessen": False,
                "grund": (
                    "AKTION verlangt: (a) je Fall die HANDLUNG, die ohne Treffer erfolgen "
                    "wuerde, (b) die Handlung, die MIT Treffer erfolgen soll, (c) einen "
                    "Beobachtungspunkt, der beide unterscheidet. runs/pruefkorpus.jsonl "
                    "traegt 'task' (eine Szenariobeschreibung) und 'target_*', aber KEIN "
                    "Handlungsfeld -- es ist ein Retrieval-, kein Verhaltenskorpus. Eine "
                    "Handlungsaenderung liesse sich nur an echten Agentenlaeufen (mit vs. "
                    "ohne Recall-Treffer, gleicher Prompt, gleicher Stichtag) beobachten, "
                    "nicht an der Suchfunktion allein. Eine erfundene vierte Zahl waere "
                    "schlimmer als eine fehlende Gateart (Auftrag, woertlich)."
                ),
                "was_fehlen_wuerde": [
                    "ein Korpus mit Vorher/Nachher-Handlung je Fall (nicht nur Zieltext)",
                    "ein reproduzierbarer Agentenlauf, der die Handlung protokolliert "
                    "(z.B. haken/knowledge_recall_hook.py-Pfad, injizierbare Zeit/Prompt)",
                    "ein Abgleichskriterium: WELCHE Handlungsaenderung zaehlt als 'richtig "
                    "reagiert' vs. 'Treffer ignoriert' -- heute nicht definiert",
                ],
            },
        },
        "grenze": [
            "Gate 1 (Treffer) hat keinen dokumentierten Zielwert -- nur der heutige Wert "
            "wird gemeldet, kein Bestanden/Nicht-bestanden.",
            "Gate 2/3-Schwellen (0.20 / 0.80) stammen aus einer FRUEHEREN Messung "
            "(kern/relevanzlage.py, 40 Faelle, 2026-08-16) -- hier gegen 10 Faelle desselben "
            "Pruefkorpus geprueft, andere Stichprobe, kein Beleg fuer Uebereinstimmung der "
            "Grundgesamtheit.",
            "Gate 4 (Aktion) ist nicht gemessen, siehe gatearten.aktion.grund.",
            "Alle Zahlen gelten fuer EINEN Zeitpunkt (heutiger Bestand) -- wachsen Bestand "
            "oder Embeddings, ist der Lauf zu wiederholen.",
            "Falschmeldung/Abstention-Schwelle beruht auf relevanzlage.beurteile(), die "
            "selbst NICHT filtert (Docstring dort) -- 'passend' ist eine Kennzeichnung, kein "
            "Ausschluss; ein System ohne diese Kennzeichnung waere hier nicht messbar "
            "gewesen.",
        ],
    }

    if not pk["bestanden"]:
        print("BEFUND: Positivkontrolle NICHT bestanden -- 'passend' ist mit diesem Aufbau "
              "nicht sicher erreichbar, Gate 2/3 sind dadurch fraglich.", file=sys.stderr)
    if treffer["top5"] != 7 or treffer["n"] != 35:
        print(f"BEFUND: Abweichung von der Referenzmessung (top5=7/35 erwartet, hier "
              f"top5={treffer['top5']}/{treffer['n']}) -- das ist ein Befund ueber diesen "
              f"Aufbau, siehe Auftrag.", file=sys.stderr)

    out_path = Path(args.out) if args.out else (
        _w / "runs" / f"vier_gatearten_{__import__('datetime').datetime.now():%Y-%m-%dT%H%M%S}.json"
    )
    out_path.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"geschrieben: {out_path}")
    print(f"treffer(top5)={treffer_gate['wert']} ({treffer['top5']}/{treffer['n']}, top50="
          f"{treffer['top50']}) falschmeldung={fm['wert']} (bestanden={fm['bestanden']}) "
          f"abstention={abst['wert']} (bestanden={abst['bestanden']}) "
          f"positivkontrolle_bestanden={pk['bestanden']}")


if __name__ == "__main__":
    main()
