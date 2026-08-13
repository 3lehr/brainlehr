#!/usr/bin/env python3
"""Pruefkorpus mit erzwungenen Rivalinnen (AUFGABE 68) -- deterministisch,
kein Modellaufruf, kein Zufall.

ZUERST GEMESSEN (Teil dieses Auftrags, nicht nur diese eine Zeile):
  runs/pruefkorpus_v2.jsonl entsteht ueber messungen/pruefkorpus_v2.py ->
    ruft ein Ollama-Modell fuer JEDEN Aufgabentext (sl._call_with_retry,
    _GEN_TEMPLATE). SEED steuert nur, WELCHE Zieleintraege gezogen werden
    (pk1.pick_candidates) -- der Aufgabentext selbst ist Modellausgabe,
    also bei zwei Laeufen nicht byteweise gleich. NICHT deterministisch.
  runs/echtkorpus_2026-08-12T1000.json entsteht ueber messungen/
    echtkorpus.py -- kein random-Import, kein Modellaufruf im Sammelweg
    (Aufgabentext ist eine ECHTE Nachricht aus recall_log.jsonl/Sitzungen,
    Ziel ueber Pfad-/Kennung-/Lese-Kanal). Bei GLEICHEM Log-Bestand ist der
    Lauf reproduzierbar -- die Datei waechst aber mit jeder neuen Sitzung,
    weil recall_log.jsonl selbst waechst. Insofern schon "deterministisch
    ueber dem Bestand", nur ist der Bestand hier ein Protokoll, das nie
    stillsteht. Die Aufgabe ist an dieser Stelle kleiner als sie klingt:
    ein Erzeuger ohne Zufall/Modellaufruf existiert schon.

WAS FEHLT UND HIER GEBAUT WIRD: erzwungene Rivalinnen. Keiner der beiden
Korpora traegt zu einem Ziel einen ausgewiesenen, thematisch nahen aber
falschen Ablenker.

ENTWURFSFRAGE -- Woher kommen die Rivalinnen? NACHBESSERUNG (dieser Auftrag):
zuerst per Jaccard-Wortueberlappung gebaut, dann selbst gemessen ueber alle
202 Faelle -- Median-Aehnlichkeit 0,108, nur 1/202 ueber 0,40. Ursache im
Code: naechster_nachbar() (siehe unten) waehlt ueber Wortmengen -- das ist
der STICHWORTKANAL, nicht der Bedeutungskanal, der Name dort war falsch.
Belegt an drei Knoten desselben Bestands (dd367fd1, b6305304, 6e0f0395,
selber Gedanke): Kosinus 0,61-0,77, Jaccard 0,03-0,09 -- Stichwort- und
Bedeutungskanal sind sich in DIESEM Bestand nicht einig, und der echte
Abrufweg gewichtet Kosinus. Ein per Jaccard gewaehlter Ablenker ist deshalb
kein Rivale im entscheidenden Kanal.

ENTSCHEIDUNG JETZT: naechster_nachbar_bedeutung() unten waehlt ueber den
bge-m3-Einbettungs-Kosinus (dieselben Vektoren in knowledge_embeddings, die
der Abrufweg selbst nutzt) statt ueber Wortueberlappung. Bauform von
kanten_aus_bedeutung.py uebernommen (numpy-Matrixmultiplikation, reiner
Python-Rueckfall via embeddings.cosine_similarity) -- keine dritte Bauform
erfunden, embeddings.py selbst bleibt unveraendert (nur importiert).
naechster_nachbar() (Jaccard) bleibt stehen (nicht geloescht, siehe
Auftrag), Docstring dort jetzt ehrlich als Stichwortkanal benannt -- baue()
ruft sie nicht mehr fuer die Ablenkerwahl.

WIEDERVERWENDET (Ponytail-Leiter): pruefkorpus.py (load_bestand, node_text,
lesson_text, tokenize, fold_de, DB) fuer den Bestand: kein zweiter Bestands-
lader. Die AUFGABENTEXTE kommen NICHT neu aus einem Modell, sondern aus dem
schon vorhandenen echten Korpus (runs/echtkorpus_*.json) -- der hat die
Realismus-Frage (echte Nachricht statt erfundener Formulierung) bereits
geloest, sie hier zu wiederholen waere Doppelarbeit. Diese Datei fuegt nur
die neue Achse hinzu: den Ablenker.

AUSGABEFORMAT bewusst identisch zu runs/pruefkorpus.jsonl (task, target_kind
"node"/"lesson", target_id): kern/abrufguete.py liest es unveraendert ein
(`python3 kern/abrufguete.py --korpus runs/pruefkorpus_rivalen.jsonl`) --
kein zweites Messskript noetig, das ist die Abnahme fuer die Schwierigkeit.

GATTUNG 'nachschlagewerk': bleibt Heuhaufen, wird NIE Ziel (Knoten 096669de,
L-051d71) -- als ABLENKER darf sie vorkommen (das ist ihre Rolle), als
target_kind/target_id nie; siehe _ziel_zulaessig().

Aufruf:
    python3 pruefkorpus_rivalen.py --bauen
    python3 pruefkorpus_rivalen.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import json
import sys
from pathlib import Path

WURZEL = _w
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "kern"))

import pruefkorpus as pk1  # noqa: E402 -- load_bestand/node_text/lesson_text/tokenize wiederverwendet
import codestand  # noqa: E402 -- fuer die Ergebnisdatei der Messung, nicht fuer den Korpus selbst
import speicher  # noqa: E402 -- nur-lesender Zugang fuer die Embeddings, kein fest verdrahteter DB-Name
from embeddings import cosine_similarity, unpack_embedding  # noqa: E402 -- Vorbild kanten_aus_bedeutung.py, embeddings.py selbst unveraendert

try:
    import numpy as _np  # weicher Import -- Frischinstallation ohne numpy
except ImportError:  # pragma: no cover -- siehe test_naechster_nachbar_bedeutung_numpy_und_python_gleich
    _np = None

DB = pk1.DB
EMBED_MODEL = "bge-m3"
QUELL_KORPUS = WURZEL / "runs" / "echtkorpus_2026-08-12T1000.json"
OUT_PATH = WURZEL / "runs" / "pruefkorpus_rivalen.jsonl"

ART_ZU_KIND = {"knoten": "node", "lehre": "lesson"}


def _pools(nodes: list[dict], lessons: list[dict]) -> tuple[dict, dict]:
    """Tokenmengen je Eintrag, getrennt nach Art -- Grundlage der
    Rivalinnen-Auswahl."""
    node_tok = {n["path"]: pk1.tokenize(pk1.node_text(n)) for n in nodes}
    lesson_tok = {l["id"]: pk1.tokenize(pk1.lesson_text(l)) for l in lessons}
    return node_tok, lesson_tok


def naechster_nachbar(ziel_id: str, pool: dict[str, set], ausschluss: set) -> tuple[str | None, float]:
    """STICHWORTKANAL, nicht Bedeutungskanal -- Docstring hier war falsch
    benannt (Nachbesserung dieses Auftrags, siehe Modulkopf). Deterministischer
    naechster Nachbar ueber hoechste Jaccard-WORTUEBERLAPPUNG zu ziel_id unter
    allen anderen Eintraegen desselben Pools. Gleichstand -> kleinste id
    (Iteration ueber sorted()), also reproduzierbar ohne jede Zufallsquelle.
    Leere Schnittmenge ueberall -> kein Ablenker (None, 0.0), das wird
    gezaehlt statt erzwungen. NICHT mehr von baue() aufgerufen (die
    Ablenkerwahl laeuft jetzt ueber naechster_nachbar_bedeutung() unten, echter
    Einbettungs-Kosinus statt Wortueberlappung) -- hier belassen, nicht
    geloescht, weil der Auftrag das ausdruecklich verlangt."""
    ziel_tokens = pool.get(ziel_id)
    if not ziel_tokens:
        return None, 0.0
    beste_id, beste_score = None, -1.0
    for kandidat_id, tokens in sorted(pool.items()):
        if kandidat_id == ziel_id or kandidat_id in ausschluss or not tokens:
            continue
        schnitt = ziel_tokens & tokens
        if not schnitt:
            continue
        score = len(schnitt) / len(ziel_tokens | tokens)
        if score > beste_score:
            beste_score, beste_id = score, kandidat_id
    return (beste_id, beste_score) if beste_id else (None, 0.0)


def _kosinus_gegen_pool_numpy(ziel_vec: list[float], kandidaten_vek: list[list[float]]) -> list[float]:
    """Kosinus-Aehnlichkeit eines Zielvektors gegen mehrere Kandidaten in
    einer Matrixmultiplikation statt einer Python-Schleife -- dieselbe
    Bauform wie kern/kanten_aus_bedeutung.py._paare_numpy (Zeilen normieren,
    dann Skalarprodukt), hier nur auf einen einzelnen Zielvektor statt auf
    alle Paare angewandt. Nullvektor -> 0.0 (nicht NaN), gleiche Regel wie
    embeddings.cosine_similarity()."""
    ziel = _np.asarray(ziel_vec, dtype=_np.float64)
    ziel_norm = _np.linalg.norm(ziel)
    arr = _np.asarray(kandidaten_vek, dtype=_np.float64)
    if ziel_norm == 0.0:
        return [0.0] * len(kandidaten_vek)
    normen = _np.linalg.norm(arr, axis=1)
    sichere = _np.where(normen == 0.0, 1.0, normen)
    sims = (arr @ ziel) / (sichere * ziel_norm)
    sims = _np.where(normen == 0.0, 0.0, sims)
    return sims.tolist()


def naechster_nachbar_bedeutung(
    ziel_id: str, vektoren: dict[str, list[float]], ausschluss: set
) -> tuple[str | None, float]:
    """Der ECHTE Bedeutungskanal: hoechste Kosinus-Aehnlichkeit der
    bge-m3-Einbettung (dieselben Vektoren, die der Abrufweg selbst nutzt) zu
    ziel_id unter allen anderen Eintraegen desselben Pools. Gleichstand ->
    kleinste id (sortierte Kandidatenliste, erster Treffer gewinnt bei
    striktem >), reproduzierbar ohne Zufallsquelle. Kein Vektor fuer
    ziel_id, oder kein anderer Eintrag mit Vektor -> kein Ablenker
    (None, 0.0), gezaehlt statt erzwungen (Abnahme 3 der Nachbesserung).
    numpy-Matrixmultiplikation wenn vorhanden, sonst reiner Python-Rueckfall
    ueber embeddings.cosine_similarity -- Bauform aus kanten_aus_bedeutung.py
    uebernommen, keine dritte erfunden."""
    ziel_vec = vektoren.get(ziel_id)
    if not ziel_vec:
        return None, 0.0

    kandidaten_ids = sorted(k for k in vektoren if k != ziel_id and k not in ausschluss)
    if not kandidaten_ids:
        return None, 0.0

    if _np is not None:
        scores = _kosinus_gegen_pool_numpy(ziel_vec, [vektoren[k] for k in kandidaten_ids])
    else:
        scores = [cosine_similarity(ziel_vec, vektoren[k]) for k in kandidaten_ids]

    beste_id, beste_score = None, -1.0
    for kandidat_id, score in zip(kandidaten_ids, scores):
        if score > beste_score:
            beste_score, beste_id = score, kandidat_id
    return (beste_id, beste_score) if beste_id is not None else (None, 0.0)


def lade_embeddings(
    nodes: list[dict], lessons: list[dict], db: str | None = None
) -> tuple[dict[str, list[float]], dict[str, list[float]]]:
    """Liest vorhandene bge-m3-Vektoren fuer genau die aktiven Knoten/Lehren,
    die load_bestand() geliefert hat -- Knoten-Pool bleibt PFADbasiert (wie
    node_tok), obwohl knowledge_embeddings.ref_id die Knoten-ID ist: hier ueber
    id_zu_path aufgeloest. Lehren-Pool ist ID-basiert (lessons_learned.id ==
    knowledge_embeddings.ref_id direkt). Dedup je ref_id (erste Zeile
    gewinnt): eine Lehre mit mehreren Bereichen traegt mehrere Zeilen mit
    demselben Vektor (siehe kanten_aus_bedeutung.lade_knoten_vektoren) --
    fuer die Ablenkerwahl reicht ein Vektor je Eintrag. speicher.lesen()
    statt eigener Verbindung: kein fest verdrahteter DB-Name (Auflage)."""
    id_zu_path = {n["id"]: n["path"] for n in nodes}
    lesson_ids = {l["id"] for l in lessons}
    node_vek: dict[str, list[float]] = {}
    lesson_vek: dict[str, list[float]] = {}
    with speicher.lesen(db) as conn:
        cur = conn.execute(
            "SELECT kind, ref_id, vector FROM knowledge_embeddings WHERE model = ?",
            (EMBED_MODEL,),
        )
        for row in cur.fetchall():
            if row["kind"] == "node":
                pfad = id_zu_path.get(row["ref_id"])
                if pfad is not None and pfad not in node_vek:
                    node_vek[pfad] = unpack_embedding(row["vector"])
            elif row["kind"] == "lesson" and row["ref_id"] in lesson_ids:
                if row["ref_id"] not in lesson_vek:
                    lesson_vek[row["ref_id"]] = unpack_embedding(row["vector"])
    return node_vek, lesson_vek


def _ziel_zulaessig(kind: str, zid: str, node_by_path: dict, lesson_by_id: dict) -> bool:
    if kind == "node":
        node = node_by_path.get(zid)
        return node is not None and node.get("gattung") != "nachschlagewerk"
    return zid in lesson_by_id


def baue(
    nodes: list[dict],
    lessons: list[dict],
    quelle: dict,
    node_vek: dict[str, list[float]] | None = None,
    lesson_vek: dict[str, list[float]] | None = None,
) -> tuple[list[dict], int]:
    """Reine Funktion (Bestand + Quellkorpus + Vektoren rein, Faelle raus) --
    macht den Selftest ohne echte DB moeglich und ist der Kern der
    Determinismus-Zusicherung: gleiche Eingaben, gleiche Ausgabe, kein
    Seiteneffekt. node_vek/lesson_vek default auf {} (kein Eintrag hat einen
    Vektor) statt None-Sonderfall in der Schleife -- ein Ziel ohne Vektor
    bekommt dann ganz regulaer (None, 0.0) von naechster_nachbar_bedeutung()."""
    node_vek = node_vek or {}
    lesson_vek = lesson_vek or {}
    node_by_path = {n["path"]: n for n in nodes}
    lesson_by_id = {l["id"]: l for l in lessons}

    faelle: list[dict] = []
    uebersprungen = 0
    for i, fall in enumerate(quelle.get("faelle", [])):
        task = fall["prompt"]
        ziele = fall.get("ziele", [])
        ziele_ids_im_fall = {z["id"] for z in ziele}
        for z in ziele:
            kind = ART_ZU_KIND.get(z.get("art"))
            zid = z.get("id")
            if kind is None or not _ziel_zulaessig(kind, zid, node_by_path, lesson_by_id):
                uebersprungen += 1
                continue
            vektoren = node_vek if kind == "node" else lesson_vek
            ablenker_id, score = naechster_nachbar_bedeutung(zid, vektoren, ziele_ids_im_fall)
            faelle.append({
                "kennung": f"{i:03d}_{kind}_{zid}",
                "task": task,
                "task_quelle": "echtkorpus",
                "fall_index": i,
                "target_kind": kind,
                "target_id": zid,
                "ablenker_kind": kind if ablenker_id else None,
                "ablenker_id": ablenker_id,
                "ablenker_aehnlichkeit": round(score, 6),
            })
    faelle.sort(key=lambda f: f["kennung"])
    return faelle, uebersprungen


def schreiben(faelle: list[dict], out_path: Path = OUT_PATH) -> None:
    with out_path.open("w", encoding="utf-8") as f:
        for fall in faelle:
            f.write(json.dumps(fall, ensure_ascii=True, sort_keys=True))
            f.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bauen", action="store_true")
    parser.add_argument("--quelle", type=Path, default=QUELL_KORPUS)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--messen", action="store_true",
                         help="Trefferquote des echten Abrufwegs auf --out messen, "
                              "Ergebnis nach runs/ mit Codestand schreiben")
    args = parser.parse_args()

    if args.selftest:
        _selftest()
        return

    if args.bauen:
        with args.quelle.open(encoding="utf-8") as f:
            quelle = json.load(f)
        nodes, lessons = pk1.load_bestand(DB)
        node_vek, lesson_vek = lade_embeddings(nodes, lessons, DB)
        faelle, uebersprungen = baue(nodes, lessons, quelle, node_vek, lesson_vek)
        schreiben(faelle, args.out)
        mit_ablenker = sum(1 for f in faelle if f["ablenker_id"])
        print(f"Faelle geschrieben: {len(faelle)} nach {args.out}")
        print(f"  davon mit Ablenker: {mit_ablenker}/{len(faelle)}")
        print(f"  uebersprungen (kein zulaessiges Ziel): {uebersprungen}")

    if args.messen:
        _messen(args.out)


# --- Messung (Abnahme 4) ----------------------------------------------------
# Kein neues Messskript: kern/abrufguete.py liest exakt dieses JSONL-Format
# (task/target_kind/target_id) schon ein und ruft den echten Abrufweg (haken/
# knowledge_recall_hook.py) unveraendert auf -- hier nur importiert, um das
# Gesamtergebnis in eine Ergebnisdatei MIT Codestand zu schreiben (Auflage:
# "ohne Codestand ist eine Messung spaeter nicht zuordenbar").

def _messen(korpus_path: Path) -> dict:
    import abrufguete as ag  # noqa: E402 -- echter Abrufweg, hier nur aufgerufen

    faelle, dubletten = ag.lade_korpus([korpus_path])
    # Ueber kern/speicher statt eigener sqlite3-Verbindung: die Naht-Ratsche
    # (tests/test_naht_ratsche.py) zaehlt Dateien mit eigener Verbindung, und
    # sie darf nur SINKEN. Fuer einen reinen Lesezugriff gibt es speicher.lesen()
    # genau dafuer -- eine Ausnahme waere hier nicht begruendbar, anders als bei
    # kanten_aus_lehren.py, wo der Fremdschluessel das Schreiben verhindert.
    with speicher.lesen() as conn:
        ergebnis = ag.messe(faelle, conn)
    treffer_gesamt = sum(v[0] for k, v in ergebnis.items()
                          if k in ("LESSON", "NODE") and v[0] is not None)
    nenner_gesamt = sum(v[1] for k, v in ergebnis.items() if k in ("LESSON", "NODE"))
    ausgabe = {
        "korpus": korpus_path.name,
        "faelle_gesamt": len(faelle),
        "dubletten_verworfen": dubletten,
        "treffer_je_gruppe": {k: v for k, v in ergebnis.items() if k != "_einzel"},
        "treffer_gesamt": treffer_gesamt,
        "nenner_gesamt": nenner_gesamt,
        "trefferquote_prozent": round(100.0 * treffer_gesamt / nenner_gesamt, 1) if nenner_gesamt else None,
        "codestand": codestand.ermitteln(WURZEL),
    }
    out = WURZEL / "runs" / f"messung_{korpus_path.stem}.json"
    out.write_text(json.dumps(ausgabe, ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Treffer gesamt: {treffer_gesamt}/{nenner_gesamt} "
          f"({ausgabe['trefferquote_prozent']}%) -- geschrieben nach {out}")
    return ausgabe


# --- Selftest --------------------------------------------------------------

def _fake_bestand():
    nodes = [
        {"path": "/a/stroke", "title": "Schlaganfall-Symptome",
         "summary": "Sprachstoerung und haengender Mundwinkel, sofort 112.",
         "content": "", "gattung": "arbeitsbestand"},
        {"path": "/a/stroke-nachbar", "title": "TIA Vorbote",
         "summary": "Sprachstoerung kurzzeitig, haengender Mundwinkel, Notarzt rufen.",
         "content": "", "gattung": "arbeitsbestand"},
        {"path": "/a/pizza", "title": "Pizzateig",
         "summary": "Hefeteig ansetzen, 24 Stunden gehen lassen.",
         "content": "", "gattung": "arbeitsbestand"},
        {"path": "/a/nachschlage", "title": "NASA Verfahren",
         "summary": "Sprachstoerung kommt hier nicht vor, reines Rauschen Grounding.",
         "content": "", "gattung": "nachschlagewerk"},
    ]
    lessons = [
        {"id": "L-000001", "description": "Timeout nach Telefonanruf verloren.",
         "root_cause": "kein Retry", "prevention": "Retry einbauen"},
        {"id": "L-000002", "description": "Telefonanruf haengt nach Timeout, Retry fehlt.",
         "root_cause": "kein Retry gleich", "prevention": "Retry einbauen gleich"},
    ]
    return nodes, lessons


def _fake_vektoren():
    """Kunstvektoren, keine unit-Norm noetig -- cosine_similarity normiert
    selbst. Reihenfolge der Naehe bewusst gesetzt: stroke-nachbar naeher an
    stroke als pizza/nachschlage, L-000002 naeher an L-000001 als leer."""
    node_vek = {
        "/a/stroke": [1.0, 0.0, 0.0],
        "/a/stroke-nachbar": [10.0, 3.0, 0.0],       # cos ~0.958
        "/a/pizza": [0.0, 0.0, 5.0],                 # cos 0.0
        "/a/nachschlage": [1.0, 1.0, 3.0],            # cos ~0.301
    }
    lesson_vek = {
        "L-000001": [1.0, 0.0],
        "L-000002": [10.0, 1.0],                      # cos ~0.995
    }
    return node_vek, lesson_vek


def _fake_quelle():
    return {"faelle": [
        {"prompt": "Jemand fragt: Sprachstoerung und haengender Mundwinkel, "
                    "erst Hausarzt oder direkt Notruf?",
         "ziele": [{"art": "knoten", "id": "/a/stroke"}]},
        {"prompt": "Der Anruf haengt seit dem Timeout, keiner meldet sich zurueck.",
         "ziele": [{"art": "lehre", "id": "L-000001"}]},
        {"prompt": "Ziel zeigt auf einen Heuhaufen-Eintrag, muss uebersprungen werden.",
         "ziele": [{"art": "knoten", "id": "/a/nachschlage"}]},
    ]}


def _selftest() -> None:
    nodes, lessons = _fake_bestand()
    quelle = _fake_quelle()
    node_vek, lesson_vek = _fake_vektoren()

    # 1) Determinismus: zweimal bauen aus denselben Eingaben ergibt
    #    identische Ausgabe (Abnahme 1).
    a, ua = baue(nodes, lessons, quelle, node_vek, lesson_vek)
    b, ub = baue(nodes, lessons, quelle, node_vek, lesson_vek)
    assert a == b and ua == ub, "gleiche Eingaben ergaben verschiedene Ausgabe"
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    print("  Determinismus (gleiche Eingaben -> gleiche Ausgabe): ok")

    # 2) Negativfall: veraendertes Bestand -> anderer Korpus (Abnahme 2).
    nodes_veraendert = nodes + [{
        "path": "/a/stroke-naeher", "title": "Akuter Schlaganfall",
        "summary": "Sprachstoerung und haengender Mundwinkel akut, Notruf 112 sofort.",
        "content": "", "gattung": "arbeitsbestand"}]
    node_vek_veraendert = dict(node_vek, **{"/a/stroke-naeher": [20.0, 1.0, 0.0]})  # cos ~0.999, naeher als stroke-nachbar
    c, _ = baue(nodes_veraendert, lessons, quelle, node_vek_veraendert, lesson_vek)
    assert c != a, "veraendertes Bestand ergab denselben Korpus -- eingefroren, nicht deterministisch"
    stroke_fall_a = next(f for f in a if f["target_id"] == "/a/stroke")
    stroke_fall_c = next(f for f in c if f["target_id"] == "/a/stroke")
    assert stroke_fall_a["ablenker_id"] != stroke_fall_c["ablenker_id"], \
        "neuer naeherer Nachbar wurde nicht als Ablenker gewaehlt"
    assert stroke_fall_c["ablenker_id"] == "/a/stroke-naeher"
    print("  Negativfall (veraendertes Bestand -> anderer Korpus): ok")

    # 3) Rivalinnen belegt: mindestens ein Fall mit Ablenker und plausiblem
    #    Aehnlichkeitswert (Abnahme 3).
    mit_ablenker = [f for f in a if f["ablenker_id"]]
    assert mit_ablenker, "kein einziger Fall hat einen Ablenker gefunden"
    for f in mit_ablenker:
        assert 0.0 < f["ablenker_aehnlichkeit"] <= 1.0
    print(f"  Rivalinnen belegt: {len(mit_ablenker)}/{len(a)} Faelle mit Ablenker, "
          f"Aehnlichkeitswerte in (0,1]: ok")

    # 3b) Negativfall Einbettung: Ziel ohne Vektor bekommt keinen Ablenker,
    #     wird aber ganz normal als Fall gezaehlt, nicht uebersprungen
    #     (Abnahme 3 der Nachbesserung -- "gezaehlt statt erzwungen").
    ohne_vektor, _ = baue(nodes, lessons, quelle)  # node_vek/lesson_vek default {}
    stroke_ohne_vektor = next(f for f in ohne_vektor if f["target_id"] == "/a/stroke")
    assert stroke_ohne_vektor["ablenker_id"] is None
    assert stroke_ohne_vektor["ablenker_kind"] is None
    assert stroke_ohne_vektor["ablenker_aehnlichkeit"] == 0.0
    assert len(ohne_vektor) == len(a), "Fall ohne Vektor wurde nicht gezaehlt"
    print("  Negativfall Einbettung (kein Vektor -> kein Ablenker, trotzdem gezaehlt): ok")

    # 4) nachschlagewerk niemals Ziel.
    ziele_kinds = {f["target_id"] for f in a}
    assert "/a/nachschlage" not in ziele_kinds, "nachschlagewerk-Knoten als Ziel durchgerutscht"
    print("  kein nachschlagewerk-Knoten als Ziel: ok")

    print("selftest ok")


if __name__ == "__main__":
    main()
