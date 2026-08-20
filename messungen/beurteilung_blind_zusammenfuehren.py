"""Fuegt die BLIND vom Menschen/Agenten getroffenen Urteile (Datei ausserhalb
des Repos, urteile.json: lfd -> [klasse, begruendung]) mit der Aufloesung und
der ersten (nicht-blinden) Beurteilung zusammen -- Schritt 5 aus
docs/PLAN_ZWEITES_SIGNAL_2026-08-20.md, S4. Schreibt runs/beurteilung_blind_2026-08-20.json.
NUR LESEN von Produktivcode/DB, keine Aenderung."""
from __future__ import annotations

import json
from pathlib import Path

W = Path("/Volumes/daten/Begod2026/brainlehr")
URTEILE = W / "runs/beurteilung_blind_urteile_roh_2026-08-20.json"

blind = json.load(open(W / "runs/beurteilung_blind_faelle_2026-08-20.json"))["faelle"]
auf = json.load(open(W / "runs/beurteilung_blind_aufloesung_2026-08-20.json"))["faelle"]
urteile = json.load(open(URTEILE))
orig = json.load(open(W / "runs/beurteilung_bf_cf_2026-08-20.json"))
orig_by_id = {f["target_id"]: f for f in orig["faelle"]}

auf_by_lfd = {f["lfd"]: f for f in auf}

faelle = []
for b in blind:
    lfd = b["lfd"]
    a = auf_by_lfd[lfd]
    klasse, begr = urteile[str(lfd)]
    orig_f = orig_by_id.get(a["target_id"])
    faelle.append({
        "lfd": lfd,
        "anfrage_gekuerzt": b["anfrage"][:220],
        "ausgeliefert_top3": [f"({it['art']}) {it['titel']}" for it in b["ausgeliefert_top3"]],
        "blindes_urteil": {"klasse": klasse, "begruendung": begr},
        "aufloesung": {
            "category": a["category"],
            "target_kind": a["target_kind"],
            "target_id": a["target_id"],
            "target_label": a.get("target_label"),
            "gruppe": "TREFFER" if a["b_richtig_treffer"] else "FEHLGRIFF",
        },
        "erste_beurteilung_2026-08-20": (
            {"klasse": orig_f["klasse"], "begruendung": orig_f["begruendung"]}
            if orig_f is not None else None
        ),
    })

# --- Kennzahlen -------------------------------------------------------
n = len(faelle)
klassen_zaehlung = {}
for f in faelle:
    k = f["blindes_urteil"]["klasse"]
    klassen_zaehlung[k] = klassen_zaehlung.get(k, 0) + 1
for k in ("BEANTWORTET", "TEILWEISE", "DANEBEN", "ANFRAGE_UNKLAR"):
    klassen_zaehlung.setdefault(k, 0)

treffer = [f for f in faelle if f["aufloesung"]["gruppe"] == "TREFFER"]
fehlgriff = [f for f in faelle if f["aufloesung"]["gruppe"] == "FEHLGRIFF"]

zu_mild = [f for f in treffer if f["blindes_urteil"]["klasse"] in ("DANEBEN", "TEILWEISE")]
zu_streng = [f for f in fehlgriff if f["blindes_urteil"]["klasse"] == "BEANTWORTET"]
uebereinstimmung = sum(
    1 for f in faelle
    if (f["aufloesung"]["gruppe"] == "TREFFER") == (f["blindes_urteil"]["klasse"] == "BEANTWORTET")
)

# Vergleich mit erster (nicht-blinder) Beurteilung -- nur die 20 damals
# beurteilten Fehlgriffe haben ein Gegenstueck.
vergleich_erste = []
for f in fehlgriff:
    orig_klasse = f["erste_beurteilung_2026-08-20"]["klasse"] if f["erste_beurteilung_2026-08-20"] else None
    if orig_klasse is None:
        continue
    vergleich_erste.append({
        "target_id": f["aufloesung"]["target_id"],
        "blind_jetzt": f["blindes_urteil"]["klasse"],
        "unverblindet_2026-08-20": orig_klasse,
        "gleich": f["blindes_urteil"]["klasse"] == orig_klasse,
    })
abweichungen_erste = [v for v in vergleich_erste if not v["gleich"]]

ergebnis = {
    "hinweis": "S4 aus docs/PLAN_ZWEITES_SIGNAL_2026-08-20.md -- blinde und "
               "beidseitige Wiederholung der Handbeurteilung, Zustand "
               "B_2Kanal_an_Pflicht_aus, alle 35 loesbaren Faelle aus "
               "runs/pruefkorpus.jsonl.",
    "nenner_gesamt_35": n,
    "verblindung_gehalten": {
        "aussage": "Ja. Bis zum Schreiben von messungen/beurteilung_blind.py wurde "
                    "kein Kosinuswert, keine Gruppenzugehoerigkeit und kein Korpusziel "
                    "gelesen. Die Urteile in diesem Ergebnis wurden VOR dem Oeffnen von "
                    "runs/beurteilung_blind_aufloesung_2026-08-20.json und "
                    "runs/beurteilung_bf_cf_2026-08-20.json (Schritt 5) fixiert -- die "
                    "Blindliste runs/beurteilung_blind_faelle_2026-08-20.json enthaelt "
                    "ausschliesslich Anfrage, ausgelieferte Titel/Zusammenfassungen und eine "
                    "nach Hash der target_id gemischte laufende Nummer.",
        "einschraenkung": "Die Reihenfolge Anfrage->Urteil lief in einem einzigen "
                    "Lesedurchgang durch alle 35 Faelle (kein randomisierter Uebertrag "
                    "in eine separate Sitzung je Fall) -- ein Erinnerungseffekt ueber "
                    "Faelle hinweg (etwa 'dieses Thema kam schon vor') ist nicht "
                    "ausgeschlossen, ist aber nicht dasselbe wie das gerueugte "
                    "Kosinus-/Gruppen-Leck."
    },
    "klassen_verteilung": klassen_zaehlung,
    "aufloesung_vergleich": {
        "treffer_gesamt_lt_messlauf": len(treffer),
        "fehlgriff_gesamt_lt_messlauf": len(fehlgriff),
        "uebereinstimmung_gesamt": f"{uebereinstimmung}/{n}",
        "korpus_zu_mild": {
            "definition": "Messlauf zaehlt TREFFER, blindes Urteil DANEBEN oder TEILWEISE",
            "anzahl": f"{len(zu_mild)}/{len(treffer)} der Treffer",
            "faelle": [f["aufloesung"]["target_id"] for f in zu_mild],
        },
        "korpus_zu_streng": {
            "definition": "Messlauf zaehlt FEHLGRIFF, blindes Urteil BEANTWORTET",
            "anzahl": f"{len(zu_streng)}/{len(fehlgriff)} der Fehlgriffe",
            "faelle": [f["aufloesung"]["target_id"] for f in zu_streng],
        },
    },
    "vergleich_mit_erster_beurteilung_2026-08-20": {
        "nenner": f"{len(vergleich_erste)}/20 (nur die damals als Fehlgriff gezaehlten Faelle "
                  "hatten dort ein Urteil)",
        "gleich": len(vergleich_erste) - len(abweichungen_erste),
        "abweichend": len(abweichungen_erste),
        "abweichungen": abweichungen_erste,
        "methodischer_befund": "runs/beurteilung_bf_cf_2026-08-20.json zeigte als "
            "'top3_ausgeliefert' bei lesson-Zielen ausschliesslich Lesson-Eintraege "
            "(runs/roh_bf_cf_2026-08-20.json::ausgeliefert_lessons), obwohl "
            "haken/knowledge_recall_hook.py::format_recall() im echten Weg IMMER "
            "erst alle Knoten und danach erst die Lehren listet (Zeilen ~1876-1900). "
            "Bei einem Fall mit >=3 Knoten-Treffern sah die erste Beurteilung damit "
            "nicht die tatsaechlichen ersten drei ausgelieferten Zeilen, sondern eine "
            "nach Zielart gefilterte Teilmenge -- ein zweiter Befund neben der "
            "fehlenden Verblindung, unabhaengig davon.",
    },
    "faelle": faelle,
}

out = W / "runs/beurteilung_blind_2026-08-20.json"
out.write_text(json.dumps(ergebnis, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"geschrieben: {out}")
print("klassen:", klassen_zaehlung, "summe", sum(klassen_zaehlung.values()))
print("korpus_zu_mild:", len(zu_mild), "korpus_zu_streng:", len(zu_streng))
print("uebereinstimmung gesamt:", uebereinstimmung, "/", n)
print("vergleich erste Beurteilung: gleich", len(vergleich_erste) - len(abweichungen_erste),
      "abweichend", len(abweichungen_erste), "von", len(vergleich_erste))
