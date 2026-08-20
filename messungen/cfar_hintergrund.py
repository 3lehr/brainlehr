"""Einmal-Arbeitsskript, Auftrag 2026-08-20 Schritt S3 (docs/PLAN_ZWEITES_SIGNAL_2026-08-20.md):
klaert den Messfehler in messungen/kreuztabelle_bc.py (nur GELESEN, nicht
geaendert -- Tabu laut Auftrag). Dort wurde "Abstand zum Median" ueber die
KANDIDATENLISTE einer Anfrage gerechnet (statistics.median(werte) in
kennzahlen()) -- das ist keine Rauschschaetzung. Eine echte CFAR-Groesse
braucht den Median ueber den HINTERGRUND (alle lebenden Knoten), nicht ueber
die schon ausgewaehlten Kandidaten.

Existenzprobe (vor dem Bauen, siehe Bericht): haken/knowledge_recall_hook.py
berechnet genau diese Hintergrundverteilung bereits -- der offizielle
Parameter `bedeutungswerte` von query() (Auftrag 2026-08-18) sammelt
_embedding_scores(conn, "node", query_vec).values() ueber ALLE lebenden
Knoten, bevor irgendein Kandidaten-Vorfilter greift (Kommentar in query(),
Zeile ~1370: "Ueber ALLE lebenden Knoten (nicht nur die Kandidaten dieser
Anfrage)"). Dieses Skript ruft NUR diesen vorhandenen Weg auf -- kein
zweiter Messweg, keine eigene Kosinusberechnung.

Die Gruppenzugehoerigkeit (BT_CT/BT_CS/BF_CS/BF_CF) wird NICHT neu bestimmt
(das waere ein zweiter, moeglicherweise abweichender Messweg gegenueber
messungen/kreuztabelle_bc.py) -- sie wird aus runs/kreuztabelle_bc_2026-08-20.json
uebernommen (Feld "kreuztabelle_je_fall", key target_kind+target_id).
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent.parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "melder", "migrationen")]

import messlauf_abrufguete as ml  # noqa: E402
import knowledge_recall_hook as hook  # noqa: E402

RESULT = _w / "runs/cfar_hintergrund_2026-08-20.json"
GRUPPEN_QUELLE = _w / "runs/kreuztabelle_bc_2026-08-20.json"
MAD_TO_SIGMA = hook.MAD_TO_SIGMA  # dieselbe Konstante wie im Betrieb, keine eigene
STATE_C = "C_beide_an"  # heutiger Auslieferungszustand -- bedeutungswerte
# haengen nur an query_vec/DB, nicht am Zustand (s. query()-Code: der Block
# laeuft VOR der _suchpfad_aktiv()-Verzweigung) -- C gewaehlt, weil es der
# Zustand ist, gegen den auch die Gruppentags in kreuztabelle_bc.py stehen.


def lade_gruppen() -> dict[tuple[str, str], str]:
    d = json.loads(GRUPPEN_QUELLE.read_text(encoding="utf-8"))
    out = {}
    for row in d["kreuztabelle_je_fall"]:
        out[(row["target_kind"], row["target_id"])] = row["lage"]
    return out


def hintergrund_kennzahlen(bedeutungswerte: list[float]) -> dict:
    """bedeutungswerte kommt bereits absteigend sortiert aus hook.query()
    (s. dortiger Kommentar: bedeutungswerte.extend(sorted(_scores.values(),
    reverse=True))) -- bedeutungswerte[0] ist damit der beste Kosinuswert
    ueber ALLE lebenden Knoten dieser Anfrage."""
    n = len(bedeutungswerte)
    if n == 0:
        return {"n": 0, "bester": None, "median_hg": None, "mad_hg": None, "z_robust": None}
    bester = bedeutungswerte[0]
    median_hg = statistics.median(bedeutungswerte)
    mad_hg = statistics.median(abs(w - median_hg) for w in bedeutungswerte)
    z_robust = None
    if mad_hg > 1e-12:
        z_robust = (bester - median_hg) / (MAD_TO_SIGMA * mad_hg)
    return {"n": n, "bester": bester, "median_hg": median_hg, "mad_hg": mad_hg,
            "z_robust": z_robust}


def verteilung(werte: list[float | None]) -> dict:
    vv = [w for w in werte if w is not None]
    if not vv:
        return {"n": 0, "min": None, "median": None, "max": None}
    return {"n": len(vv), "min": min(vv), "median": statistics.median(vv), "max": max(vv)}


def main() -> None:
    cases = ml.load_cases()
    gruppen = lade_gruppen()

    je_fall = []
    with ml._gegen_schnappschuss() as stand:
        with ml._with_state(ml.STATES[STATE_C]):
            for c in cases:
                key = (c["target_kind"], c["target_id"])
                lage = gruppen.get(key)
                kws = hook.keywords(c["task"])
                bw: list[float] = []
                if len(kws) >= hook.MIN_HITS:
                    hook.query(kws, rand=ml._seeded_rand(c["task"]), cwd=None,
                               prompt=c["task"], bedeutungswerte=bw)
                k = hintergrund_kennzahlen(bw)
                je_fall.append({
                    "target_kind": c["target_kind"], "target_id": c["target_id"],
                    "category": c["category"], "lage": lage, **k,
                })
        stand_info = {"kennung": stand.kennung, "aufgenommen": stand.aufgenommen}

    fehlend_lage = [r for r in je_fall if r["lage"] is None]

    gruppennamen = ("BT_CT", "BT_CS", "BF_CS", "BF_CF")
    je_gruppe = {}
    for g in gruppennamen:
        rows = [r for r in je_fall if r["lage"] == g]
        je_gruppe[g] = {
            "n": len(rows),
            "n_hintergrund": verteilung([r["n"] for r in rows]),
            "bester_kosinus": verteilung([r["bester"] for r in rows]),
            "z_robust": verteilung([r["z_robust"] for r in rows]),
        }

    summe = sum(je_gruppe[g]["n"] for g in gruppennamen)

    # Trennschwelle nur melden, wenn sie ohne Ueberlappung existiert (wie
    # messungen/kreuztabelle_bc.py::trennschwelle() -- hier eigenstaendig
    # nachgebaut, weil aus der Tabu-Datei nichts importiert werden darf,
    # aber dieselbe Pruefung: beide Richtungen, kein Ueberlappungsfall
    # nachtraeglich weggerundet).
    def trennschwelle(a: list[float], b: list[float]) -> dict | None:
        if not a or not b:
            return None
        if max(a) < min(b):
            return {"schwelle": (max(a) + min(b)) / 2, "richtung": "a < schwelle <= b"}
        if max(b) < min(a):
            return {"schwelle": (max(b) + min(a)) / 2, "richtung": "b < schwelle <= a"}
        return None

    bt_cs_z = [r["z_robust"] for r in je_fall if r["lage"] == "BT_CS" and r["z_robust"] is not None]
    bf_cf_z = [r["z_robust"] for r in je_fall if r["lage"] == "BF_CF" and r["z_robust"] is not None]
    bt_ct_z = [r["z_robust"] for r in je_fall if r["lage"] == "BT_CT" and r["z_robust"] is not None]
    bf_cs_z = [r["z_robust"] for r in je_fall if r["lage"] == "BF_CS" and r["z_robust"] is not None]

    trennung_bt_cs_gegen_bf_cf = trennschwelle(bt_cs_z, bf_cf_z)
    # Auftragspunkt 4: ALLE vier Gruppen gegen eine gefundene Schwelle pruefen,
    # nicht nur die zwei, die sie hervorgebracht haben.
    schwellenwirkung_alle_gruppen = None
    if trennung_bt_cs_gegen_bf_cf is not None:
        t = trennung_bt_cs_gegen_bf_cf["schwelle"]
        schwellenwirkung_alle_gruppen = {
            g: {"unter_schwelle": sum(1 for r in je_fall if r["lage"] == g and r["z_robust"] is not None and r["z_robust"] < t),
                "ab_schwelle": sum(1 for r in je_fall if r["lage"] == g and r["z_robust"] is not None and r["z_robust"] >= t),
                "z_fehlend": sum(1 for r in je_fall if r["lage"] == g and r["z_robust"] is None)}
            for g in gruppennamen
        }

    channel_discrimination_befund = (
        "BESTAETIGT (Code gelesen, kern/embeddings.py::channel_discrimination, "
        "Zeilen 243-273): top=max(vals), lo=min(vals), spread=top-lo, "
        "median=Median(vals); Rueckgabe (top-median)/spread == (top-median)/(top-lo). "
        "min ist die im Bestand varianzreichste Ordnungsstatistik (ein einzelner "
        "Ausreisser nach unten stauchtden Nenner), top steht in Zaehler UND Nenner "
        "(kein Selbstkuerzen, aber ein gemeinsamer Faktor, der die Kennzahl an den "
        "TOP-Wert koppelt statt an eine stabile Hintergrundstreuung). Das ist NICHT "
        "das hier gemessene CFAR-Mass: channel_discrimination() rechnet innerhalb der "
        "Kandidatenliste EINES Kanals (Docstring: 'Wirkt NUR innerhalb eines Kanals'), "
        "nicht gegen die Hintergrundverteilung aller 5215 lebenden Knoten. Beide Groessen "
        "sind also verschiedene Verfahren; channel_discrimination() ist selbst keine "
        "Hintergrundschaetzung und wurde hier nicht als Ersatz fuer den Median-Test "
        "verwendet."
    )

    tau_domaene = 0.10  # Fachgebiets-Richtwert score-basierter CFAR-Verfahren
    # auf Einbettungssuche (s. Auftrag Punkt 5) -- NICHT an den Daten kalibriert,
    # nur zum Abgleich mitgefuehrt.
    ueberschreitet_tau = {
        g: (je_gruppe[g]["z_robust"]["median"] is not None and
            je_gruppe[g]["z_robust"]["median"] >= tau_domaene)
        for g in gruppennamen
    }

    ergebnis = {
        "beschreibung": "S3: CFAR-Hintergrundschaetzung (Median+MAD ueber ALLE "
                         "lebenden Knoten je Anfrage) gegen die vier Kreuztabelle-"
                         "Gruppen, ueber denselben Weg wie der Betrieb "
                         "(hook.query(bedeutungswerte=...) -> _embedding_scores).",
        "positivkontrolle_hintergrundgroesse": verteilung([r["n"] for r in je_fall]),
        "fehlende_gruppenzuordnung": [f"{r['target_kind']}:{r['target_id']}" for r in fehlend_lage],
        "gruppengroessen_summe_45": summe,
        "je_gruppe": je_gruppe,
        "trennschwelle_bt_cs_gegen_bf_cf": trennung_bt_cs_gegen_bf_cf,
        "schwellenwirkung_auf_alle_vier_gruppen": schwellenwirkung_alle_gruppen,
        "tau_domaene_score_cfar": tau_domaene,
        "median_z_robust_ab_tau_domaene": ueberschreitet_tau,
        "channel_discrimination_befund": channel_discrimination_befund,
        "je_fall": je_fall,
        "stand": stand_info,
    }
    RESULT.write_text(json.dumps(ergebnis, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"geschrieben: {RESULT}")
    print(f"Hintergrundgroesse (median ueber 45 Faelle): {ergebnis['positivkontrolle_hintergrundgroesse']}")
    print(f"Gruppengroessen: { {g: je_gruppe[g]['n'] for g in gruppennamen} } summe={summe}")
    print(f"Trennschwelle BT_CS/BF_CF: {trennung_bt_cs_gegen_bf_cf}")


def demo() -> None:
    """Ponytail-Selbstcheck: hintergrund_kennzahlen() auf synthetischen
    Werten, keine DB noetig."""
    k = hintergrund_kennzahlen([0.9, 0.5, 0.5, 0.5, 0.5, 0.1])
    assert k["n"] == 6
    assert k["bester"] == 0.9
    assert k["median_hg"] == 0.5
    assert k["mad_hg"] == 0.0  # >=4 gleiche Werte -> MAD 0
    assert k["z_robust"] is None  # MAD==0 -> kein z, wie im Betrieb (Radar-Kommentar)
    k2 = hintergrund_kennzahlen([1.0, 0.6, 0.4, 0.2, 0.0])
    assert k2["median_hg"] == 0.4
    assert abs(k2["mad_hg"] - 0.2) < 1e-9
    assert k2["z_robust"] is not None and k2["z_robust"] > 0
    assert hintergrund_kennzahlen([])["n"] == 0
    print("demo ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo()
    else:
        main()
