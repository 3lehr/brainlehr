"""Misst den HEUTIGEN automatischen Abrufweg (haken/knowledge_recall_hook.py)
gegen dieselben 35 loesbaren Faelle aus runs/pruefkorpus.jsonl (45 Zeilen
gesamt, 35 mit target_kind gesetzt, 10 'negative' ohne Ziel -- Filter wie
kern/messlauf_abrufguete.py::messe()).

WEG: kein Nachbau. Importiert haken/knowledge_recall_hook.py und ruft
- hook.keywords() + hook.query() -- exakt der Pfad, den hook.main() beim
  echten UserPromptSubmit-Hook geht (main() macht nur: stdin lesen, diese
  beiden Aufrufe, dann den Block bauen, dann log_recall()/log_schatten()
  schreiben).
- fuer den eingespielten TEXTBLOCK dieselben privaten Bausteine wie main()
  selbst: hook._erstverwendungs_vorschlaege(), hook.relevanzlage.beurteile(),
  hook.alter()/_geltung_tag()/_abloesung_tag(), einschleusung.entschaerfe_
  fuer_ausgabe(), hook._auf_budget_kuerzen() -- Zeile fuer Zeile aus main()
  uebernommen (main() selbst liefert den Block nicht als Funktion zurueck,
  nur als stdout-JSON), keine eigene Formatierungslogik.
main() selbst wird NICHT aufgerufen: main() schreibt unbedingt in
log_recall()/RECALL_LOG (und ggf. SCHATTEN_LOG) -- 70 Messaufrufe (35 Faelle
x 2 Schalterstellungen) wuerden das echte Trust-Signal 'RECALL-EINSPIELUNG'
(knowledge_mcp_server.py::knowledge_trust_score(), Signal 2) mit erfundenen
Zeilen verfaelschen. hook.RECALL_LOG/SCHATTEN_LOG werden trotzdem auf
Wegwerfpfade gepinnt (s. main(), Verweis 'Tests koennen hook.RECALL_LOG
patchen'), fuer den Fall, dass eine der aufgerufenen Funktionen selbst
noch danach liest (_erstverwendungs_vorschlaege -> _bereits_vorgeschlagen,
_maybe_explore -> _node_hit_counts) -- das soll gegen eine LEERE Datei
laufen, nicht gegen den echten Bestand.

DATENBANK: EIN Schnappschuss (kern/schnappschuss.py::festhalten()), danach
zwei Module auf dieselbe Kopie gepinnt:
  hook.DB                     -- FTS/Embeddings-Kandidaten (query())
  knowledge_mcp_server.DB_PATH -- knowledge_trust_score()/_trust_aggregate()
                                   (hook._apply_trust_score() ruft diese
                                   Funktionen OHNE eigenen db_path-Parameter
                                   auf, sie lesen das MODUL-Attribut)
BEFUND, gemessen beim Lesen des Codes (nicht vermutet): hook.DB wird ueber
haken/ort.py aus BRAINLEHR_DB/BEGOD_KNOWLEDGE_DB abgeleitet;
knowledge_mcp_server.DB_PATH liest NUR BEGOD_KNOWLEDGE_DB (Zeile 159 dort)
und geht NICHT ueber ort.py. kern/messlauf_abrufguete.py::_gegen_schnappschuss()
pinnt bislang NUR hook.DB -- knowledge_trust_score() haette in jenem Lauf
also gegen den lebenden, wachsenden Bestand sortiert, waehrend die
Kandidaten selbst schon vom Schnappschuss kamen. Dieses Skript pinnt beide
Attribute direkt (Monkeypatch von aussen, keine Aenderung an haken/* oder
kern/*) und macht damit sichtbar, dass 'der Haken' zwei verschiedene
DB-Pfade benutzt, nicht einen.

Ausfuehren: python3 messungen/abrufweg_produktiv.py [--selftest]
Ergebnis: runs/abrufweg_produktiv_<zeitstempel>.json
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import random
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_w = Path(__file__).resolve().parent.parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import knowledge_recall_hook as hook  # noqa: E402 -- der Produktivweg selbst
import knowledge_mcp_server as kms  # noqa: E402 -- Trust-Score-Pfad, s. Docstring
import schnappschuss  # noqa: E402

KORPUS = _w / "runs" / "pruefkorpus.jsonl"


def lade_faelle() -> list[dict]:
    faelle = [json.loads(z) for z in KORPUS.read_text(encoding="utf-8").splitlines() if z.strip()]
    solvable = [f for f in faelle if f.get("target_kind")]
    assert len(solvable) == 35, f"{len(solvable)} loesbare Faelle statt 35 -- Korpus geaendert?"
    return solvable


def _seeded_rand(text: str):
    """Wie kern/messlauf_abrufguete.py::_seeded_rand() -- derselbe Zweck
    (hook._maybe_explore() faellt ohne `rand` auf ungeseedetes random.random()
    zurueck, EXPLORE_RATE=0.15 macht zwei Laeufe sonst unvergleichbar),
    hier neu geschrieben statt importiert: kern/* ist fuer diesen Auftrag
    tabu (ein anderer Agent haelt die Datei)."""
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
    return random.Random(seed).random


def bau_block(nodes: list, lessons: list, bedeutungswerte: list) -> str:
    """Zeile fuer Zeile aus hook.main() uebernommen (main() liefert den Block
    nur als stdout-JSON, nicht als Rueckgabewert) -- ruft ausschliesslich
    bereits vorhandene Bausteine des Hakens auf, keine eigene Formatierung."""
    erstverwendung_zeilen, _ = hook._erstverwendungs_vorschlaege(nodes)
    lines = ["<knowledge-recall>",
             "Aus dem Speicher, ungeprüft. Nicht als Fundliste lesen, sondern "
             "als Frage: Trifft das hier zu? Wenn NEIN — woran liegt es? "
             "(Ein Eintrag, der nicht passt, ist eine Antwort; ein übergangener "
             "ist keine.)"]
    if bedeutungswerte:
        lage = hook.relevanzlage.beurteile(bedeutungswerte)
        if lage["satz"]:
            lines.append(lage["satz"])
    for n in nodes:
        tag = " (Erkundung -- selten gezogen)" if n.get("explore") else ""
        fremd = f" [anderes Projekt: {n['foreign_project']}]" if n.get("foreign_project") else ""
        geltung = hook._geltung_tag(n.get("norm_rang"), n.get("gilt_bis"))
        abgeloest = hook._abloesung_tag(n)
        lines.append(f"- [{n['path']}]{hook.alter(n.get('updated_at'))}{tag}{fremd}{geltung}{abgeloest} "
                     f"{hook.entschaerfe_fuer_ausgabe(n['title'])}: {hook.entschaerfe_fuer_ausgabe(n['summary'])}")
    for l in lessons:
        tag = "⚠ LESSON" if l["severity"] in ("critical", "high") else "Lesson"
        prev = f" → {hook.entschaerfe_fuer_ausgabe(l['prevention'])}" if l.get("prevention") else ""
        fremd = f" [andere Projekte: {l['foreign_projects']}]" if l.get("foreign_projects") else ""
        herkunft = f", {l['id']}"
        if l.get("session"):
            herkunft += f", Sitzung {l['session']}"
        if l.get("first_seen"):
            herkunft += f", erfasst {l['first_seen'][:10]}"
        if not l.get("foreign_projects"):
            projs = hook.projekte_aus_projects_json(l.get("projects"))
            if projs:
                herkunft += f", Projekt {'/'.join(sorted(projs))}"
        lines.append(f"- {tag} ({l['type']}, {l['occurrences']}×{herkunft}){hook.alter(l.get('last_seen'))}{fremd}: "
                     f"{hook.entschaerfe_fuer_ausgabe(l['description'])}{prev}")
    lines.extend(erstverwendung_zeilen)
    lines.append("</knowledge-recall>")
    block, _weggelassen = hook._auf_budget_kuerzen(lines)
    return block


def run_case(fall: dict) -> tuple[list, list, str]:
    """main()-Gatter nachgebildet (len(kws) < MIN_HITS -> sofortige Stille,
    exakt wie main() vor dem ersten query()-Aufruf), danach query() + Block --
    beides die Bausteine, die main() selbst benutzt."""
    kws = hook.keywords(fall["task"])
    if len(kws) < hook.MIN_HITS:
        return [], [], ""
    bedeutungswerte: list = []
    nodes, lessons = hook.query(kws, rand=_seeded_rand(fall["task"]), cwd=None,
                                 prompt=fall["task"], bedeutungswerte=bedeutungswerte)
    if not nodes and not lessons:
        return [], [], ""
    block = bau_block(nodes, lessons, bedeutungswerte)
    return nodes, lessons, block


def rang(fall: dict, nodes: list, lessons: list) -> int | None:
    """1-basierter Rang des Ziels INNERHALB der vom Hook tatsaechlich
    zurueckgegebenen Liste (schon auf MAX_NODES=10/MAX_LESSONS=7 gedeckelt --
    das IST bereits 'was eingespielt wird', vor der Budget-Kuerzung, die nur
    noch von HINTEN kappt -- ein Rang <= 5 uebersteht die Kuerzung so gut wie
    immer, ein spaeter Rang kann durch die Kuerzung zusaetzlich herausfallen;
    das wird separat unten am Blocktext selbst geprueft)."""
    kette = nodes if fall["target_kind"] == "node" else lessons
    feld = "path" if fall["target_kind"] == "node" else "id"
    for i, item in enumerate(kette, start=1):
        if item.get(feld) == fall["target_id"]:
            return i
    return None


def tatsaechlich_im_block(fall: dict, block: str) -> bool:
    """'ueberhaupt enthalten' gegen den ROHEN, ausgegebenen Text -- nicht
    gegen nodes/lessons vor der Budget-Kuerzung. Node-Ziele stehen als
    '[pfad]', Lehren-Ziele als ihre Kennung 'L-xxxxxx' im Text."""
    nadel = f"[{fall['target_id']}]" if fall["target_kind"] == "node" else fall["target_id"]
    return nadel in block


@contextlib.contextmanager
def _gegen_schnappschuss():
    """Zieht GENAU EINEN Schnappschuss und pinnt BEIDE DB-Pfade des Hakens
    darauf (s. Moduldocstring: hook.DB und kms.DB_PATH sind zwei
    verschiedene Attribute). RECALL_LOG/SCHATTEN_LOG auf Wegwerfpfade, damit
    kein Lesezugriff aus den aufgerufenen Funktionen versehentlich den
    echten Bestand beruehrt (er wird nirgends BESCHRIEBEN, da main() nicht
    aufgerufen wird -- reine Vorsichtsmassnahme fuer Lesepfade wie
    _bereits_vorgeschlagen()/_node_hit_counts())."""
    stand = schnappschuss.festhalten()
    tmp = Path(tempfile.mkdtemp(prefix="abrufweg_wegwerflog_"))
    orig = {
        "hook.DB": hook.DB,
        "kms.DB_PATH": kms.DB_PATH,
        "hook.RECALL_LOG": hook.RECALL_LOG,
        "hook.SCHATTEN_LOG": hook.SCHATTEN_LOG,
    }
    hook.DB = str(stand.pfad)
    kms.DB_PATH = stand.pfad
    hook.RECALL_LOG = str(tmp / "recall_log.jsonl")
    hook.SCHATTEN_LOG = str(tmp / "schatten_log.jsonl")
    try:
        yield stand
    finally:
        hook.DB = orig["hook.DB"]
        kms.DB_PATH = orig["kms.DB_PATH"]
        hook.RECALL_LOG = orig["hook.RECALL_LOG"]
        hook.SCHATTEN_LOG = orig["hook.SCHATTEN_LOG"]
        shutil.rmtree(stand.pfad.parent, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


@contextlib.contextmanager
def _suchpfad_schalter(an: bool):
    key = "KNOWLEDGE_SUCHPFAD_ABRUF"
    alt = os.environ.get(key)
    os.environ[key] = "1" if an else "0"
    try:
        yield
    finally:
        if alt is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = alt


def messe(faelle: list[dict]) -> dict:
    zeilen = []
    for f in faelle:
        nodes, lessons, block = run_case(f)
        zeilen.append({
            "ziel": f["target_id"],
            "art": f["target_kind"],
            "rang": rang(f, nodes, lessons),
            "im_block": tatsaechlich_im_block(f, block) if block else False,
            "zeichen": len(block),
        })
    gefunden_top5 = sum(1 for z in zeilen if z["rang"] is not None and z["rang"] <= 5)
    gefunden_ueberhaupt = sum(1 for z in zeilen if z["im_block"])
    laengen = [z["zeichen"] for z in zeilen]
    return {
        "trefferquote_top5": [gefunden_top5, len(zeilen)],
        "trefferquote_ueberhaupt": [gefunden_ueberhaupt, len(zeilen)],
        "zeichen_median": int(_median(laengen)),
        "zeichen_summe": sum(laengen),
        "faelle": zeilen,
    }


def _median(werte: list[int]) -> float:
    if not werte:
        return 0.0
    s = sorted(werte)
    n = len(s)
    mitte = n // 2
    return s[mitte] if n % 2 else (s[mitte - 1] + s[mitte]) / 2


def demo() -> None:
    """Selbsttest der Auswertungsfunktionen mit erfundenen Daten -- kein
    DB-, kein Netzzugriff. Drei Faelle: Ziel auf Rang 1, Ziel auf Rang 6
    (ausserhalb top5, aber 'ueberhaupt enthalten'), Ziel gar nicht dabei."""
    fall_node = {"target_kind": "node", "target_id": "arch/x"}
    nodes_rang1 = [{"path": "arch/x"}, {"path": "arch/y"}]
    assert rang(fall_node, nodes_rang1, []) == 1

    nodes_rang6 = [{"path": f"arch/{i}"} for i in range(5)] + [{"path": "arch/x"}]
    assert rang(fall_node, nodes_rang6, []) == 6

    nodes_fehlt = [{"path": "arch/y"}]
    assert rang(fall_node, nodes_fehlt, []) is None

    fall_lesson = {"target_kind": "lesson", "target_id": "L-abc123"}
    assert rang(fall_lesson, [], [{"id": "L-zzz"}, {"id": "L-abc123"}]) == 2

    block_mit = "<knowledge-recall>\n- [arch/x] ...\n</knowledge-recall>"
    block_ohne = "<knowledge-recall>\n- [arch/y] ...\n</knowledge-recall>"
    assert tatsaechlich_im_block(fall_node, block_mit) is True
    assert tatsaechlich_im_block(fall_node, block_ohne) is False

    block_lesson = "<knowledge-recall>\n- Lesson (error, 3x, L-abc123) ...\n</knowledge-recall>"
    assert tatsaechlich_im_block(fall_lesson, block_lesson) is True

    zeilen = [{"rang": 1, "im_block": True, "zeichen": 100},
              {"rang": 6, "im_block": True, "zeichen": 200},
              {"rang": None, "im_block": False, "zeichen": 0}]
    top5 = sum(1 for z in zeilen if z["rang"] is not None and z["rang"] <= 5)
    ueberhaupt = sum(1 for z in zeilen if z["im_block"])
    assert top5 == 1
    assert ueberhaupt == 2
    assert _median([100, 200, 0]) == 100

    print("demo: ok", file=sys.stderr)


def main() -> None:
    faelle = lade_faelle()
    ergebnis = {
        "weg": "haken/knowledge_recall_hook.py::keywords()+query() (der Pfad, den "
               "main() beim echten UserPromptSubmit-Hook geht) + main()s eigene "
               "Bausteine fuer den Textblock (_erstverwendungs_vorschlaege, "
               "relevanzlage.beurteile, alter/_geltung_tag/_abloesung_tag, "
               "entschaerfe_fuer_ausgabe, _auf_budget_kuerzen) -- main() selbst "
               "nicht aufgerufen (schreibt sonst in log_recall()/RECALL_LOG, s. Docstring)",
        "korpus": str(KORPUS.relative_to(_w)),
        "faelle_gesamt": len(faelle),
    }
    with _gegen_schnappschuss() as stand:
        ergebnis["schnappschuss_kennung"] = stand.kennung
        ergebnis["schnappschuss_aufgenommen"] = stand.aufgenommen
        for name, an in (("SUCHPFAD_ABRUF_an", True), ("SUCHPFAD_ABRUF_aus", False)):
            with _suchpfad_schalter(an):
                ergebnis[name] = messe(faelle)
    out = _w / "runs" / f"abrufweg_produktiv_{datetime.now(timezone.utc).astimezone():%Y-%m-%dT%H%M%S}.json"
    out.write_text(json.dumps(ergebnis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"geschrieben: {out}")
    for name in ("SUCHPFAD_ABRUF_an", "SUCHPFAD_ABRUF_aus"):
        r = ergebnis[name]
        print(f"{name}: top5={r['trefferquote_top5'][0]}/{r['trefferquote_top5'][1]}  "
              f"ueberhaupt={r['trefferquote_ueberhaupt'][0]}/{r['trefferquote_ueberhaupt'][1]}  "
              f"zeichen median={r['zeichen_median']} summe={r['zeichen_summe']}")


if __name__ == "__main__":
    demo()
    if "--selftest" not in sys.argv:
        main()
