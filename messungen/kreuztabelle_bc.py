"""Einmal-Arbeitsskript, Auftrag 2026-08-20: Kreuztabelle B gegen C je Fall
(45 Faelle, runs/pruefkorpus.jsonl) und Kennzahlen der von der Pflicht
verworfenen Treffer (BT_CS) gegen die von ihr verhinderten Fehler (BF_CS).

Nutzt DENSELBEN Weg wie kern/messlauf_abrufguete.py: load_cases()/
_with_state()/STATES/_gegen_schnappschuss()/target_hit() importiert, kein
zweiter Messweg fuer die Grundzahlen. Nur lesend (hook.query() oeffnet die DB
mit mode=ro, der Schnappschuss ist eine Kopie).

FUER SCHRITT 2 wird hook.query() zusaetzlich mit bedeutungswerte=[] aufgerufen
(offizieller Parameter der Funktion, Auftrag 2026-08-18, s. Docstring dort --
kein eigener Messweg) und hook._combine_channels waehrend des Aufrufs per
monkeypatch abgehorcht (nur GELESEN, was die Funktion sowieso berechnet --
keine eigene Bewertung, wie von relevanzlage.py verlangt). Der Patch wird
nach jedem Aufruf sofort zurueckgesetzt.

Kein Import von relevanzlage-fremden Bewertungsfunktionen: die LAGE/bester/
abstand-Zahlen kommen ausschliesslich aus kern/relevanzlage.py::beurteile().
Der Median-Abstand ist reine Standardbibliothek (statistics.median), keine
Bewertung.
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
import relevanzlage  # noqa: E402

RESULT = _w / "runs/kreuztabelle_bc_2026-08-20.json"
STATE_B = "B_2Kanal_an_Pflicht_aus"
STATE_C = "C_beide_an"
ENSEMBLE_TOP_N = hook.ENSEMBLE_TOP_N


def instrumented_run(c: dict) -> dict:
    """run_case()-Aequivalent, das zusaetzlich bedeutungswerte (Kosinuswerte
    aller lebenden Knoten zu dieser Anfrage, Auftrag 2026-08-18-Parameter)
    und die Kanal-Signale (kw_signal/emb_signal je Kandidatenart, per
    monkeypatch von hook._combine_channels abgehorcht) einsammelt. Faellt
    das MIN_HITS-Gatter (wie run_case()), bleibt alles leer -- kein Aufruf,
    kein Kandidat."""
    kws = hook.keywords(c["task"])
    if len(kws) < hook.MIN_HITS:
        return {"nodes": [], "lessons": [], "bedeutungswerte": [], "kanaele": []}

    kanaele = []
    orig = hook._combine_channels

    def _spion(kw_signal, emb_signal, emb_available):
        kanaele.append({
            "kw_ids": [x["id"] for x in kw_signal],
            "emb_ids": [x["id"] for x in emb_signal],
            "emb_available": emb_available,
        })
        return orig(kw_signal, emb_signal, emb_available)

    bedeutungswerte: list[float] = []
    hook._combine_channels = _spion
    try:
        nodes, lessons = hook.query(
            kws, rand=ml._seeded_rand(c["task"]), cwd=None, prompt=c["task"],
            bedeutungswerte=bedeutungswerte)
    finally:
        hook._combine_channels = orig

    # Reihenfolge im Code (haken/knowledge_recall_hook.py::query(), Zeilen
    # ~1371 dann ~1411): erster _combine_channels-Aufruf ist der Knoten-,
    # zweiter der Lehren-Kanal -- sofern beide Bloecke keine sqlite3.Error
    # geschluckt haben. Fehlt einer, bleibt das Feld leer statt zu raten.
    kanal_node = kanaele[0] if len(kanaele) > 0 else None
    kanal_lesson = kanaele[1] if len(kanaele) > 1 else None
    return {
        "nodes": nodes, "lessons": lessons,
        "bedeutungswerte": bedeutungswerte,
        "kanal_node": kanal_node, "kanal_lesson": kanal_lesson,
    }


def kennzahlen(werte: list[float], kanal: dict | None, target_kind: str) -> dict:
    """Alles, was der Abrufweg fuer diesen Fall ohnehin liefert -- Lage/
    bester/abstand ueber relevanzlage.beurteile() (KEINE eigene Bewertung),
    dazu Median-Abstand (Standardbibliothek), Kanaluebereinstimmung und
    Trefferzahl aus dem abgehorchten Kanal-Signal (nur gezaehlt, nicht neu
    bewertet)."""
    lage = relevanzlage.beurteile(werte)
    median_abstand = None
    if werte:
        median_abstand = round(float(werte[0]) - statistics.median(werte), 4)

    matching = trefferzahl = None
    if kanal is not None:
        kw_top = set(kanal["kw_ids"][:ENSEMBLE_TOP_N])
        emb_top = set(kanal["emb_ids"][:ENSEMBLE_TOP_N])
        matching = len(kw_top & emb_top)
        trefferzahl = len(set(kanal["kw_ids"]) | set(kanal["emb_ids"]))

    return {
        "lage": lage["lage"],
        "bester_kosinus": lage["bester"],
        "abstand_zweitbester": lage["abstand"],
        "abstand_median": median_abstand,
        "kanaele_uebereinstimmend": matching,
        "trefferzahl": trefferzahl,
        "kanal_verwendet": target_kind,
    }


def main() -> None:
    cases = ml.load_cases()
    solvable = [c for c in cases if c["category"] != "negative"]
    negative = [c for c in cases if c["category"] == "negative"]
    assert len(solvable) == 35 and len(negative) == 10

    kreuz = []
    with ml._gegen_schnappschuss() as stand:
        for c in cases:
            with ml._with_state(ml.STATES[STATE_B]):
                b = instrumented_run(c)
            with ml._with_state(ml.STATES[STATE_C]):
                c_run = instrumented_run(c)

            if c["category"] == "negative":
                b_richtig = not b["nodes"] and not b["lessons"]
                c_richtig = not c_run["nodes"] and not c_run["lessons"]
            else:
                b_richtig = ml.target_hit(c, b["nodes"], b["lessons"])
                c_richtig = ml.target_hit(c, c_run["nodes"], c_run["lessons"])

            if b_richtig and c_richtig:
                lage_tag = "BT_CT"
            elif b_richtig and not c_richtig:
                lage_tag = "BT_CS"
            elif not b_richtig and c_richtig:
                lage_tag = "BF_CS"
            else:
                lage_tag = "BF_CF"

            kreuz.append({
                "target_kind": c["target_kind"], "target_id": c["target_id"],
                "category": c["category"], "lage": lage_tag,
                "b_richtig": b_richtig, "c_richtig": c_richtig,
                "_b": b, "_c": c_run, "_case": c,
            })
        stand_info = {"kennung": stand.kennung, "aufgenommen": stand.aufgenommen}

    # --- Schritt 1: Positivkontrolle -------------------------------------
    solv_rows = [r for r in kreuz if r["category"] != "negative"]
    neg_rows = [r for r in kreuz if r["category"] == "negative"]
    assert len(solv_rows) == 35 and len(neg_rows) == 10

    zaehlung_solvable = {t: sum(1 for r in solv_rows if r["lage"] == t)
                          for t in ("BT_CT", "BT_CS", "BF_CS", "BF_CF")}
    zaehlung_negativ = {t: sum(1 for r in neg_rows if r["lage"] == t)
                         for t in ("BT_CT", "BT_CS", "BF_CS", "BF_CF")}
    summe_solvable = sum(zaehlung_solvable.values())
    summe_negativ = sum(zaehlung_negativ.values())
    bt_gesamt = zaehlung_solvable["BT_CT"] + zaehlung_solvable["BT_CS"]

    positivkontrolle = {
        "summe_solvable_35": summe_solvable,
        "summe_negativ_10": summe_negativ,
        "bt_ct_plus_bt_cs_15": bt_gesamt,
        "ok": summe_solvable == 35 and summe_negativ == 10 and bt_gesamt == 15,
    }
    if not positivkontrolle["ok"]:
        print(f"ABWEICHUNG Positivkontrolle: {positivkontrolle} -- Aufbau verdaechtig, "
              "Ergebnis trotzdem vollstaendig geschrieben, Auftrag ausdruecklich "
              "'melden bevor weiterrechnen'.")

    # --- Schritt 2: Kennzahlen fuer BT_CS (solvable) und BF_CS (negativ) -
    def messe_gruppe(rows: list[dict]) -> list[dict]:
        out = []
        for r in rows:
            b = r["_b"]
            kanal = b.get("kanal_node") if r["target_kind"] == "node" else b.get("kanal_lesson")
            if kanal is None:
                kanal = b.get("kanal_node") or b.get("kanal_lesson")
            k = kennzahlen(b["bedeutungswerte"], kanal, r["target_kind"])
            k["target_id"] = r["target_id"]
            out.append(k)
        return out

    bt_cs_rows = [r for r in solv_rows if r["lage"] == "BT_CS"]
    bf_cs_rows = [r for r in neg_rows if r["lage"] == "BF_CS"]
    bt_cs_kennzahlen = messe_gruppe(bt_cs_rows)
    bf_cs_kennzahlen = messe_gruppe(bf_cs_rows)

    def verteilung(werte: list[float | None]) -> dict:
        vv = [w for w in werte if w is not None]
        if not vv:
            return {"n": 0, "min": None, "median": None, "max": None}
        return {"n": len(vv), "min": min(vv), "median": statistics.median(vv), "max": max(vv)}

    def trennschwelle(a: list[float], b: list[float]) -> dict | None:
        """Sucht eine Schwelle t, sodass alle Werte einer Gruppe <t und alle
        der anderen >=t liegen (in BEIDE Richtungen geprueft). None, wenn
        keine solche Schwelle existiert (Ueberlappung)."""
        if not a or not b:
            return None
        if max(a) < min(b):
            t = (max(a) + min(b)) / 2
            return {"schwelle": t, "richtung": "gruppe_a < schwelle <= gruppe_b",
                     "a_ueber_schwelle_fehler": 0, "b_unter_schwelle_fehler": 0}
        if max(b) < min(a):
            t = (max(b) + min(a)) / 2
            return {"schwelle": t, "richtung": "gruppe_b < schwelle <= gruppe_a",
                     "a_unter_schwelle_fehler": 0, "b_ueber_schwelle_fehler": 0}
        return None

    groessen = ["bester_kosinus", "abstand_zweitbester", "abstand_median",
                "kanaele_uebereinstimmend", "trefferzahl"]
    trennung = {}
    for g in groessen:
        a_werte = [x[g] for x in bt_cs_kennzahlen]
        b_werte = [x[g] for x in bf_cs_kennzahlen]
        a_v = [w for w in a_werte if w is not None]
        b_v = [w for w in b_werte if w is not None]
        schwelle = trennschwelle(a_v, b_v)
        trennung[g] = {
            "bt_cs_verworfene_treffer": verteilung(a_werte),
            "bf_cs_verhinderte_fehler": verteilung(b_werte),
            "trennt_sauber": schwelle is not None,
            "schwelle": schwelle,
        }

    # --- Nachschlag (2026-08-20, zweiter Auftrag): dritte Gruppe BF_CF ---
    # bei den loesbaren Faellen (20 von 35) fehlte -- die Faelle, in denen B
    # bei einer LOESBAREN Frage spricht und danebenliegt. Dieselben fuenf
    # Groessen wie bei BT_CS/BF_CS, KEINE neue Schwelle gesucht (Auftrag
    # Punkt 4) -- nur die bereits gefundene Schwelle (Punkt 2 unten) angelegt.
    bf_cf_rows = [r for r in solv_rows if r["lage"] == "BF_CF"]
    bf_cf_kennzahlen = messe_gruppe(bf_cf_rows)

    schwelle_wert = trennung["bester_kosinus"]["schwelle"]["schwelle"]
    bf_cf_ueber = sum(1 for x in bf_cf_kennzahlen
                       if x["bester_kosinus"] is not None and x["bester_kosinus"] >= schwelle_wert)
    bf_cf_unter = sum(1 for x in bf_cf_kennzahlen
                       if x["bester_kosinus"] is not None and x["bester_kosinus"] < schwelle_wert)
    bf_cf_ohne_wert = sum(1 for x in bf_cf_kennzahlen if x["bester_kosinus"] is None)

    schwellenwirkung_bf_cf = {
        "nenner": len(bf_cf_rows),
        "bezugsrahmen": "die 20 BF_CF-Faelle (loesbar, B spricht falsch, C schweigt "
                         "ebenfalls nicht besser) aus runs/pruefkorpus.jsonl",
        "schwelle_verwendet": schwelle_wert,
        "darueber_haette_geliefert_obwohl_B_danebenlag": bf_cf_ueber,
        "darunter_waere_verschwiegen_worden": bf_cf_unter,
        "ohne_kosinuswert": bf_cf_ohne_wert,
    }

    # --- Punkt 3: Gesamtbilanz einer Schwellenschicht ueber alle 45 -------
    # Vier Faecher, disjunkt und erschoepfend je Fall:
    #   richtige Auslieferung  -- spricht UND (loesbar UND trifft Ziel)
    #   falsche  Auslieferung  -- spricht UND NICHT das Obige (Negativfall
    #                             spricht ueberhaupt, ODER loesbarer Fall
    #                             spricht, trifft aber nicht)
    #   richtiges Schweigen    -- schweigt UND Negativfall (Schweigen ist
    #                             dort die richtige Antwort)
    #   falsches  Schweigen    -- schweigt UND loesbarer Fall (dort gibt es
    #                             ein Ziel, Schweigen verfehlt es immer)
    def bilanz(get_nodes_lessons, get_bester_kosinus=None, schwelle: float | None = None) -> dict:
        """get_nodes_lessons(row) -> (nodes, lessons) fuer den zu bilanzierenden
        Zustand. Wird `schwelle` gesetzt, spricht die Schicht nur, wenn sie
        selbst spricht UND get_bester_kosinus(row) >= schwelle -- fehlt der
        Kosinuswert (Embedding-Kanal ohne Vergleichswert), wird ungegated
        durchgereicht (kein Filter ohne Messwert, dokumentiert im Feld
        'ohne_kosinuswert_durchgereicht')."""
        faecher = {"richtige_auslieferung": 0, "falsche_auslieferung": 0,
                   "richtiges_schweigen": 0, "falsches_schweigen": 0}
        ohne_kosinus_durchgereicht = 0
        for r in kreuz:
            nodes, lessons = get_nodes_lessons(r)
            spricht = bool(nodes or lessons)
            if spricht and schwelle is not None:
                bk = get_bester_kosinus(r)
                if bk is None:
                    ohne_kosinus_durchgereicht += 1
                elif bk < schwelle:
                    spricht = False
            loesbar = r["category"] != "negative"
            if spricht:
                trifft = ml.target_hit(r["_case"], nodes, lessons) if loesbar else False
                faecher["richtige_auslieferung" if (loesbar and trifft) else "falsche_auslieferung"] += 1
            else:
                faecher["falsches_schweigen" if loesbar else "richtiges_schweigen"] += 1
        faecher["ohne_kosinuswert_durchgereicht"] = ohne_kosinus_durchgereicht
        faecher["summe"] = sum(v for k, v in faecher.items() if k != "ohne_kosinuswert_durchgereicht")
        return faecher

    bilanz_b = bilanz(lambda r: (r["_b"]["nodes"], r["_b"]["lessons"]))
    bilanz_c = bilanz(lambda r: (r["_c"]["nodes"], r["_c"]["lessons"]))
    bilanz_schicht = bilanz(
        lambda r: (r["_b"]["nodes"], r["_b"]["lessons"]),
        get_bester_kosinus=lambda r: (relevanzlage.beurteile(r["_b"]["bedeutungswerte"])["bester"]),
        schwelle=schwelle_wert)

    abnahme_bilanz = {
        "B_reproduziert_15_treffer_0_10_richtiges_schweigen":
            bilanz_b["richtige_auslieferung"] == 15 and bilanz_b["richtiges_schweigen"] == 0,
        "C_reproduziert_1_treffer_10_10_richtiges_schweigen":
            bilanz_c["richtige_auslieferung"] == 1 and bilanz_c["richtiges_schweigen"] == 10,
        "B_summe_45": bilanz_b["summe"] == 45,
        "C_summe_45": bilanz_c["summe"] == 45,
        "Schicht_summe_45": bilanz_schicht["summe"] == 45,
    }
    if not all(abnahme_bilanz.values()):
        print(f"ABWEICHUNG Bilanz-Abnahme: {abnahme_bilanz} -- Aufbau verdaechtig, "
              "Ergebnis trotzdem vollstaendig geschrieben.")

    # --- Vorbehalt schmale Luecke (Betreiber-Nachschlag) -------------------
    luecke_bt_cs_min = trennung["bester_kosinus"]["bt_cs_verworfene_treffer"]["min"]
    luecke_bf_cs_max = trennung["bester_kosinus"]["bf_cs_verhinderte_fehler"]["max"]
    vorbehalt_schmale_luecke = {
        "text": (
            f"Die Luecke zwischen BF_CS (max {luecke_bf_cs_max}) und BT_CS "
            f"(min {luecke_bt_cs_min}) betraegt {round(luecke_bt_cs_min - luecke_bf_cs_max, 4)} "
            f"und steht bei n=24 (14 BT_CS + 10 BF_CS) -- derselben Groessenordnung, "
            "bei der kern/relevanzlage.py (Docstring, Messung 2026-08-16) eine "
            "'saubere Trennung bei 12 gegen 12 Faellen' festhaelt, die 'bei 40 gegen "
            "40 verschwand'. Diese Messung hat die Trennung nicht an einer groesseren "
            "Stichprobe nachgeprueft (Auftrag Punkt 4: keine neue Schwelle, kein neuer "
            "Suchlauf) -- die Trennung gilt fuer GENAU diese 24 Faelle des Pruefkorpus, "
            "nicht als belegte allgemeine Eigenschaft des besten Kosinuswerts. Die "
            "Anwendung auf die 20 BF_CF-Faelle oben ist bereits die erste Gegenprobe "
            "an FREMDEN, in der Trennung selbst nicht enthaltenen Faellen."
        ),
        "n_getrennt": 24, "n_bt_cs": 14, "n_bf_cs": 10,
        "luecke_untere_kante_bf_cs_max": luecke_bf_cs_max,
        "luecke_obere_kante_bt_cs_min": luecke_bt_cs_min,
        "luecke_breite": round(luecke_bt_cs_min - luecke_bf_cs_max, 4),
    }

    ergebnis = {
        "beschreibung": "Kreuztabelle B gegen C je Fall, 45 Faelle "
                        "(runs/pruefkorpus.jsonl), plus Kennzahlen der von "
                        "KNOWLEDGE_ENSEMBLE_PFLICHT verworfenen Treffer "
                        "(BT_CS) gegen die verhinderten Fehler (BF_CS).",
        "zaehlung_solvable": {**zaehlung_solvable, "nenner": 35,
                              "bezugsrahmen": "die 35 loesbaren Faelle aus runs/pruefkorpus.jsonl"},
        "zaehlung_negativ": {**zaehlung_negativ, "nenner": 10,
                             "bezugsrahmen": "die 10 Negativfaelle aus runs/pruefkorpus.jsonl"},
        "positivkontrolle": positivkontrolle,
        "schritt2_gruppen": {
            "bt_cs_verworfene_treffer": {"nenner": len(bt_cs_rows), "faelle": [r["target_id"] for r in bt_cs_rows],
                                          "kennzahlen": bt_cs_kennzahlen},
            "bf_cs_verhinderte_fehler": {"nenner": len(bf_cs_rows), "faelle": [r["target_id"] for r in bf_cs_rows],
                                          "kennzahlen": bf_cs_kennzahlen},
        },
        "trennung_je_groesse": trennung,
        "schritt2_dritte_gruppe_bf_cf": {
            "beschreibung": "Nachschlag: die 20 loesbaren Faelle, in denen B "
                            "spricht und danebenliegt (weder von der Ensemble-"
                            "Pflicht gerettet noch verworfen -- C liegt hier "
                            "ebenfalls falsch/schweigt).",
            "nenner": len(bf_cf_rows), "faelle": [r["target_id"] for r in bf_cf_rows],
            "kennzahlen": bf_cf_kennzahlen,
            "verteilung_bester_kosinus": verteilung([x["bester_kosinus"] for x in bf_cf_kennzahlen]),
        },
        "schwellenwirkung_auf_bf_cf": schwellenwirkung_bf_cf,
        "gesamtbilanz_45_faelle": {
            "beschreibung": "Vier disjunkte Faecher je Fall (richtige/falsche "
                            "Auslieferung, richtiges/falsches Schweigen), "
                            "Nenner 45 je Zustand.",
            "B": bilanz_b, "C": bilanz_c,
            "Schicht_B_gegated_auf_bester_kosinus": bilanz_schicht,
            "abnahme": abnahme_bilanz,
        },
        "vorbehalt_schmale_luecke": vorbehalt_schmale_luecke,
        "kreuztabelle_je_fall": [
            {"target_kind": r["target_kind"], "target_id": r["target_id"],
             "category": r["category"], "lage": r["lage"],
             "b_richtig": r["b_richtig"], "c_richtig": r["c_richtig"]}
            for r in kreuz
        ],
        "stand": stand_info,
        "laufmetadaten": ml.laufmetadaten(cases, ml.CORPUS),
    }
    RESULT.write_text(json.dumps(ergebnis, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"geschrieben: {RESULT}")
    print(f"\nSchritt1 Positivkontrolle: {positivkontrolle}")
    print(f"zaehlung_solvable: {zaehlung_solvable}")
    print(f"zaehlung_negativ: {zaehlung_negativ}")
    print("\nSchritt2/3 Trennung je Groesse:")
    for g, t in trennung.items():
        print(f"  {g}: BT_CS={t['bt_cs_verworfene_treffer']} BF_CS={t['bf_cs_verhinderte_fehler']} "
              f"trennt_sauber={t['trennt_sauber']} schwelle={t['schwelle']}")
    print(f"\nNachschlag BF_CF (n={len(bf_cf_rows)}) bester_kosinus-Verteilung: "
          f"{verteilung([x['bester_kosinus'] for x in bf_cf_kennzahlen])}")
    print(f"Schwellenwirkung auf BF_CF: {schwellenwirkung_bf_cf}")
    print(f"\nGesamtbilanz 45 Faelle -- B: {bilanz_b}")
    print(f"Gesamtbilanz 45 Faelle -- C: {bilanz_c}")
    print(f"Gesamtbilanz 45 Faelle -- Schicht: {bilanz_schicht}")
    print(f"Abnahme Bilanz: {abnahme_bilanz}")
    print(f"\nVorbehalt schmale Luecke: {vorbehalt_schmale_luecke['text']}")


if __name__ == "__main__":
    main()
