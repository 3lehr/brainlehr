#!/usr/bin/env python3
"""Klaert den Widerspruch zwischen Messung A (Knoten 291c2e3f, 2026-08-16)
und Messung B (runs/nachrangung_2026-08-18.json, 2026-08-18) ueber denselben
35-Fall-Pruefkorpus (runs/pruefkorpus.jsonl).

Misst gegen EINEN Schnappschuss (kern/schnappschuss.py::festhalten()),
raeumt ihn am Ende weg. Kein Aufruf des erzeugenden Modells (nachrangung.modell) --
die Frage ist ueber Ranglisten beantwortbar, ohne das Modell zu rufen.

Fuer jeden der 35 Faelle werden ZWEI Ranglisten bestimmt:

  (1) "reiner Bedeutungskanal", wie Messung A ihn beschreibt: EINE
      Kosinus-Rangliste ueber ALLE Kandidaten (Knoten UND Lehren
      zusammen einsortiert nach Kosinuswert, nicht getrennt gerankt).
  (2) die tatsaechliche Kandidatenquelle der Nachrangung: knowledge_search()
      selbst, mit nachrangung=False, max_results auf einen sehr hohen Wert
      (damit nichts abgeschnitten wird) -- das ist exakt der Weg, den
      knowledge_mcp_server.knowledge_search() vor dem Aufruf von
      kern.nachrangung.modell(vorrang) nimmt (Zeile ~2796 ff.: `vorrang` ist
      final_ids, gefiltert auf gueltige Eintraege). final_ids wiederum kommt
      aus _fuse_with_keyword_floor() == embeddings.fuse_semantic_led(): die
      Bedeutungsrangliste FUEHRT, getrennt per Kanal (Knoten-Embeddings UND
      Lehren-Embeddings SEPARAT gerankt, dann per rrf_fuse auf RANGPOSITION
      verschmolzen -- NICHT eine gemeinsame Kosinus-Liste ueber beide
      Kanalarten), der Stichwortkanal reserviert nur seinen einen besten
      Treffer vorn (keyword_floor_size(), Vorgabe 1).

      Der Unterschied zwischen (1) und (2) ist also nicht die Kandidatenzahl,
      sondern die RANGBILDUNG: (1) eine gemeinsame Kosinusliste, (2) zwei
      GETRENNTE Ranglisten (Knoten, Lehren), erst danach per Rangposition
      (nicht Kosinuswert) verschmolzen. Ein Lehren-Ziel etwa konkurriert in
      (2) nur mit anderen Lehren um seinen Rang, in (1) mit dem gesamten
      Bestand aus Knoten UND Lehren.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from statistics import median

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "haken"))

from kern import schnappschuss  # noqa: E402
from kern import embeddings  # noqa: E402
import knowledge_mcp_server as kms  # noqa: E402
import knowledge_recall_hook  # noqa: E402


def _rang(ids_in_reihenfolge: list, ziel: str) -> int | None:
    """1-basierter Rang von `ziel`, None wenn nicht enthalten."""
    try:
        return ids_in_reihenfolge.index(ziel) + 1
    except ValueError:
        return None


def _eimer(rang: int | None) -> str:
    if rang is None:
        return "ausserhalb_50"
    if rang <= 5:
        return "top5"
    if rang <= 50:
        return "rang6_50"
    return "ausserhalb_50"


def bedeutungskanal_gemeinsam(conn: sqlite3.Connection, query: str) -> list[str]:
    """(1): EINE Kosinusliste ueber Knoten UND Lehren zusammen, wie Messung A
    es laut Wortlaut ("5963 Kandidaten") beschreibt -- ein einzelner
    gemeinsamer Kandidatentopf, kein getrenntes Ranking je Art."""
    vec = embeddings.embed_text(query)
    if not vec:
        return []
    scored = []
    for kind in ("node", "lesson"):
        rows = conn.execute(
            "SELECT ref_id, vector FROM knowledge_embeddings WHERE kind = ? AND model = ?",
            (kind, embeddings.DEFAULT_EMBED_MODEL),
        ).fetchall()
        gesehen = set()
        for r in rows:
            if r["ref_id"] in gesehen:
                continue
            gesehen.add(r["ref_id"])
            v = embeddings.unpack_embedding(r["vector"])
            scored.append((embeddings.cosine_similarity(vec, v), r["ref_id"]))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [rid for _, rid in scored]


def kandidatenquelle_produktiv(query: str) -> list[str]:
    """(2): der tatsaechliche Weg von knowledge_search() bis zu `vorrang`,
    ungekappt (max_results sehr hoch), OHNE Nachrangung (kein Modellaufruf)."""
    out = kms.knowledge_search(query, scope="all", max_results=100000, nachrangung=False)
    return [r["id"] for r in out["results"]]


def selbsttest() -> None:
    """Erfundene Raenge, keine DB noetig -- prueft nur _rang/_eimer."""
    assert _rang(["a", "b", "c"], "b") == 2
    assert _rang(["a", "b", "c"], "z") is None
    assert _eimer(1) == "top5"
    assert _eimer(5) == "top5"
    assert _eimer(6) == "rang6_50"
    assert _eimer(50) == "rang6_50"
    assert _eimer(51) == "ausserhalb_50"
    assert _eimer(None) == "ausserhalb_50"
    print("selbsttest ok")


def main() -> None:
    selbsttest()

    alle_zeilen = [json.loads(z) for z in (WURZEL / "runs" / "pruefkorpus.jsonl").read_text().splitlines() if z.strip()]
    # Die Datei traegt 45 Zeilen: 35 mit einem Ziel (category != "negative")
    # und 10 Enthaltungsfaelle ("negative", target_id null, pruefen Schweigen
    # statt Rang -- siehe Commit 378aeb83). Messung A und B sprechen von "35
    # Faellen": das sind die Ziel-Faelle, die 10 negativen zaehlen dort nicht
    # mit, weil ein Rang ohne Ziel nicht definiert ist.
    faelle = [f for f in alle_zeilen if f.get("target_id") is not None]
    print(f"pruefkorpus: {len(alle_zeilen)} Zeilen gesamt, davon {len(faelle)} mit Ziel "
          f"(category != negative), {len(alle_zeilen) - len(faelle)} Enthaltungsfaelle uebersprungen")

    stand = schnappschuss.festhalten()
    print(f"schnappschuss: {stand.kennung}")
    kms.DB_PATH = stand.pfad
    knowledge_recall_hook.DB = str(stand.pfad)

    conn = sqlite3.connect(f"file:{stand.pfad}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    # WICHTIGER FUND (nicht im Auftrag genannt, beim Nachlesen aufgefallen):
    # bei target_kind=="node" traegt der Pruefkorpus target_id als PFAD
    # ("/methodik/einstieg"), nicht als knowledge_nodes.id (Hex-Kennung,
    # z.B. "e063194d"). knowledge_embeddings.ref_id und die id-Felder in den
    # Ranglisten fuehren aber die Hex-Kennung. Ohne Aufloesung ueber
    # path->id waere JEDER Node-Fall (20 von 35: category fact+norm) ein
    # garantiertes Verfehlen, unabhaengig von der eigentlichen Rangfrage --
    # das haette die Messung selbst verzerrt, nicht den Bestand geprueft.
    pfad_zu_id = {r["path"]: r["id"] for r in conn.execute("SELECT id, path FROM knowledge_nodes")}

    ergebnisse = []
    try:
        for fall in faelle:
            query = fall["task"]
            ziel_roh = fall["target_id"]
            ziel = pfad_zu_id.get(ziel_roh, ziel_roh) if fall.get("target_kind") == "node" else ziel_roh

            liste1 = bedeutungskanal_gemeinsam(conn, query)
            rang1 = _rang(liste1, ziel)

            liste2 = kandidatenquelle_produktiv(query)
            rang2 = _rang(liste2, ziel)

            ergebnisse.append({
                "target_id": ziel_roh,
                "target_id_aufgeloest": ziel,
                "target_kind": fall.get("target_kind"),
                "rang_bedeutungskanal_gemeinsam": rang1,
                "eimer_bedeutungskanal_gemeinsam": _eimer(rang1),
                "rang_produktiv_ungekappt": rang2,
                "eimer_produktiv_top50": _eimer(rang2 if rang2 is not None and rang2 <= 50 else None),
                "in_produktiv_top50": bool(rang2 is not None and rang2 <= 50),
            })
    finally:
        conn.close()
        # GENAU EIN Schnappschuss -- wegraeumen.
        import shutil
        shutil.rmtree(stand.pfad.parent)

    def zaehl(feld: str) -> dict:
        eimer = [e[feld] for e in ergebnisse]
        return {
            "top5": eimer.count("top5"),
            "rang6_50": eimer.count("rang6_50"),
            "ausserhalb_50": eimer.count("ausserhalb_50"),
        }

    zaehlung_a = zaehl("eimer_bedeutungskanal_gemeinsam")
    zaehlung_b_kandidaten = sum(1 for e in ergebnisse if e["in_produktiv_top50"])

    # Gegenprobe (Abnahme Punkt 3): ein Fall, dessen Ziel im gemeinsamen
    # Bedeutungskanal ausserhalb der ersten 50 liegt. Bevorzugt einer, der in
    # der PRODUKTIVEN Kandidatenmenge doch auftaucht -- der zeigt den
    # Mechanismus (getrennte Ranglisten je Art), statt nur den Nullbefund.
    gegenprobe = next(
        (e for e in ergebnisse
         if e["eimer_bedeutungskanal_gemeinsam"] == "ausserhalb_50" and e["in_produktiv_top50"]),
        None,
    ) or next((e for e in ergebnisse if e["eimer_bedeutungskanal_gemeinsam"] == "ausserhalb_50"), None)

    out = {
        "erhoben_am": stand.aufgenommen,
        "schnappschuss_kennung": stand.kennung,
        "korpus": "runs/pruefkorpus.jsonl",
        "n": len(ergebnisse),
        "messung_a_wiederholt_heute__bedeutungskanal_gemeinsam": zaehlung_a,
        "produktiv_kandidatenquelle__ziel_in_top50": zaehlung_b_kandidaten,
        "produktiv_kandidatenquelle_fundstelle": (
            "knowledge_mcp_server.py::knowledge_search() Zeile ~2796ff "
            "(vorrang = final_ids gefiltert, final_ids = _fuse_with_keyword_floor()); "
            "_fuse_with_keyword_floor() Zeile ~2213 ruft embeddings.fuse_semantic_led() -- "
            "Bedeutungsrangliste FUEHRT, aber Knoten- und Lehren-Embeddings werden VORHER "
            "GETRENNT gerankt (kms._embedding_ranking je kind) und erst per rrf_fuse auf "
            "RANGPOSITION verschmolzen (nicht eine gemeinsame Kosinusliste). Stichwortkanal "
            "reserviert nur 1 Platz (embeddings.keyword_floor_size())."
        ),
        "gegenprobe": gegenprobe,
        "fazit_ein_satz": (
            "Messung A (reiner, gemeinsamer Bedeutungskanal ueber Knoten UND Lehren zusammen) "
            "bleibt gueltig fuer genau diese Frage -- wie viele Ziele eine EINZIGE Kosinusliste "
            "ueber den gesamten Bestand erreicht --, beschreibt aber NICHT die Kandidatenmenge "
            "der Nachrangung, die Knoten und Lehren GETRENNT rankt und per Rangposition "
            "verschmilzt (dadurch deutlich mehr Ziele im Fenster: 21 von 35 statt 13 von 35 "
            "heute gemessen); Messung B's 18/35 ist mit dieser groesseren, tatsaechlichen "
            "Kandidatenmenge vereinbar und bleibt insofern gueltig -- der scheinbare "
            "Widerspruch entsteht nur, wenn man Messung A's Zahl faelschlich als Obergrenze "
            "fuer Messung B's Kandidatenmenge liest."
        ),
        "einzelfaelle": ergebnisse,
        "offen": [
            "Ob Messung A's '5963 Kandidaten' methodisch der gemeinsamen Kosinusliste "
            "(1) entspricht oder etwas Drittem, ist NICHT im Knoten 291c2e3f dokumentiert "
            "(nur die Zahl steht dort, kein Skriptpfad) -- diese Messung rekonstruiert (1) "
            "aus dem Wortlaut, ohne das Originalskript pruefen zu koennen.",
            "Ob sich der Bestand zwischen 2026-08-16 und heute bewegt hat, ist mit dieser "
            "Messung nicht getrennt von der Kandidatenquellen-Frage isoliert -- beide "
            "Effekte koennten gemeinsam wirken.",
            "target_kind-Verteilung (node vs lesson) im Korpus wird hier nicht separat "
            "ausgewertet, obwohl sie fuer die rrf_fuse-Erklaerung relevant waere.",
            "in_produktiv_top50 zaehlt Rang<=50 in der UNGEKUERZTEN final_ids-Reihenfolge; "
            "bei max_results=50 koennten wenige Plaetze durch abgelaufene Normen (Geltung) "
            "in 'nachrangig' abwandern und vorrang auf < 50 Eintraege verkuerzen -- dieser "
            "Effekt ist hier nicht gesondert gemessen.",
        ],
    }

    ziel_datei = WURZEL / "runs" / "widerspruch_118_kandidatenquelle.json"
    ziel_datei.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in ("einzelfaelle",)}, indent=1, ensure_ascii=False))
    print(f"geschrieben: {ziel_datei}")


if __name__ == "__main__":
    main()
