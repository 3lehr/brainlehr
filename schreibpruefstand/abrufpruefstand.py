"""A/B/C-Messung des passiven Abrufs gegen einen Bestand mit BEKANNTER
Wahrheit (Auftrag 2026-08-07). Der Unterschied zu jeder bisherigen Messung
steht in einem Satz: hier ist vorher entschieden, ob eine Aufgabe eine
richtige Antwort hat -- damit zerfaellt "der Abruf lieferte nichts" in die
zwei Faelle, die sich an der echten brainlehr.db nicht trennen lassen
(ER HAT VERSAGT / ES GAB NICHTS).

DREI BETRIEBSARTEN, nicht zwei (Nachtrag des Auftrags):
  A  zweiter Kanal AUS                    (Verhalten vor Commit 4167aef78)
  B  zweiter Kanal AN, Pflicht AUS        (Auslieferungszustand heute)
  C  zweiter Kanal AN, Pflicht AN         (Commit 9fdae2726, per Schalter)

A wird NICHT ueber den Schalter KNOWLEDGE_ZWEITER_KANAL allein hergestellt,
sondern ueber eine zweite Datenbankdatei ohne Zeilen in
knowledge_embeddings. Grund: query() prueft die Tabelle selbst
(_has_embeddings) und faellt dann auf emb_available=False zurueck -- genau
den Zweig, den A messen soll. Damit haengt A nicht an einem Schalter, der
zur Laufzeit dieses Auftrags noch unfertig im Arbeitsbereich lag. Der
Schalter wird zusaetzlich gesetzt, falls vorhanden (beide Wege muessen
dasselbe ergeben; weichen sie ab, ist das ein Befund und keine Messung).

VIER ZAHLEN je Betriebsart, jede mit ihrem Bezugsrahmen im Ergebnis
(Aufgabenzahl, Sorte, seed -- L-352afa: eine Zahl ohne Bezugsrahmen
beantwortet eine engere Frage als der Satz, in dem sie steht):
  trefferguete       Ziel unter den Treffern      / 8 loesbare
  schweigen_loesbar  geschwiegen, obwohl da       / 8 loesbare   (FEHLER)
  schweigen_unloesbar geschwiegen, richtig so     / 8 unloesbare (RICHTIG)
  fehlgriff_verfuehrerisch Cluster-Eintrag geliefert / 8 verfuehrerische

EICHUNG (ohne sie misst der Aufbau nichts): das Ziel EINER loesbaren Aufgabe
wird aus dem Bestand entfernt, danach muss dieselbe Aufgabe zu Schweigen
fuehren. Laeuft in jeder Betriebsart mit.

DER HOOK WIRD NICHT GEAENDERT. Er wird importiert, sein Modul-DB-Pfad auf
die Pruefstands-Datei gebogen (dieselbe Stelle, die auch sein eigener
selftest biegt) und sein Dateihash ins Ergebnis geschrieben -- die Datei lag
waehrend dieses Auftrags im Arbeitsbereich eines anderen Agenten, ohne den
Hash waere nicht belegbar, welche Fassung gemessen wurde.

Kein Modellaufruf ausser Einbettungen (nomic-embed-text ueber Ollama, lokal).
Die Einbettungen der Aufgabentexte werden EINMAL berechnet und per embed_fn
in query() injiziert -- sonst waere derselbe Text dreimal (je Betriebsart)
neu berechnet und die drei Zahlen nicht mehr am selben Vektor gemessen.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import hashlib
import json
import os
import random
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

SCHREIBPRUEFSTAND = Path(__file__).resolve().parent
SHARED_KNOWLEDGE = SCHREIBPRUEFSTAND.parent
HUB = SHARED_KNOWLEDGE.parent
sys.path.insert(0, str(SCHREIBPRUEFSTAND))
sys.path.insert(0, str(SHARED_KNOWLEDGE))

DEMO_DIR = SCHREIBPRUEFSTAND / "demo"
DB_MIT = DEMO_DIR / "abrufpruefstand-mit-kanal2.db"
DB_OHNE = DEMO_DIR / "abrufpruefstand-ohne-kanal2.db"
RECALL_LOG = DEMO_DIR / "abrufpruefstand-recall.jsonl"
OUT_PATH = SCHREIBPRUEFSTAND / "runs" / "abrufpruefstand-2026-08-07.json"
SEED = 20260807

# Eigener Bestand, bevor irgendein Modul die echte DB aufloest. knowledge_
# mcp_server.DB_PATH liest genau diese Variable (dort Zeile mit
# os.environ.get("BEGOD_KNOWLEDGE_DB")); der Hook hat sie nicht und wird
# unten am Modulwert gebogen.
os.environ["BEGOD_KNOWLEDGE_DB"] = str(DB_MIT)

import embeddings  # noqa: E402
import stadtwerke_korpus as korpus  # noqa: E402

sys.path.insert(0, str(HUB / "scripts"))
import knowledge_recall_hook as rh  # noqa: E402

ECHTE_DB = SHARED_KNOWLEDGE / "brainlehr.db"


def _sicherheitsnetz(pfad: Path) -> None:
    """Wie demo_db._assert_not_real_db: Zusicherung als Pruefung, nicht als
    Kommentar. Bricht ab, bevor irgendein Schreibversuch die echte Datenbank
    erreichen koennte."""
    if pfad.resolve() == ECHTE_DB.resolve():
        raise RuntimeError(f"Abbruch: {pfad} ist die echte Wissensdatenbank.")


# --- Bestand aufbauen -----------------------------------------------------

def baue_db(eintraege: list[dict], db_path: Path, mit_embeddings: bool,
            vektoren: dict[str, list[float]] | None) -> Path:
    _sicherheitsnetz(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-shm", "-wal"):
        p = Path(str(db_path) + suffix)
        if p.exists():
            p.unlink()
    conn = sqlite3.connect(str(db_path))
    conn.executescript((SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8"))
    conn.executescript((SHARED_KNOWLEDGE / "build_embeddings.py").read_text(encoding="utf-8")
                       .split('CREATE_TABLE_SQL = """')[1].split('"""')[0])
    jetzt = "2026-08-07T00:00:00Z"
    for i, e in enumerate(eintraege):
        if e["kind"] == "node":
            pfad = korpus.kennung(e)
            conn.execute(
                "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, "
                "content, level, tags, source, created_at, updated_at, "
                "norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'keine_norm','skript:abrufpruefstand.py','synthetischer Pruefkorpus, kein Normtraeger')",
                (f"N-{i:03d}", pfad, None, e["abteilung"], e["title"], e["summary"],
                 e["content"], pfad.count("/") - 1, "[]", "abrufpruefstand", jetzt, jetzt))
        else:
            conn.execute(
                "INSERT INTO lessons_learned (id, type, severity, description, root_cause, "
                "prevention, occurrences, projects, status, first_seen, last_seen) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (e["id"], e["typ"], e["severity"], e["description"], e["root_cause"],
                 e["prevention"], 1, json.dumps([e["abteilung"]]), "active", jetzt, jetzt))
    if mit_embeddings and vektoren:
        for e in eintraege:
            k = korpus.kennung(e)
            vec = vektoren.get(k)
            if vec is None:
                continue
            ref = conn.execute("SELECT id FROM knowledge_nodes WHERE path = ?", (k,)).fetchone() \
                if e["kind"] == "node" else (k,)
            conn.execute(
                "INSERT INTO knowledge_embeddings (kind, ref_id, project_id, model, vector, updated_at) "
                "VALUES (?,?,?,?,?,?)",
                (e["kind"], ref[0], e["abteilung"], embeddings.DEFAULT_EMBED_MODEL,
                 embeddings.pack_embedding(vec), jetzt))
    conn.commit()
    conn.close()
    return db_path


def berechne_vektoren(texte: dict[str, str]) -> dict[str, list[float]]:
    """Einmal je Text, nicht je Betriebsart. Faellt ein Vektor aus (Ollama
    weg), wird er ausgelassen und im Ergebnis gezaehlt -- ein stiller
    Teilausfall wuerde Betriebsart A und B ununterscheidbar machen."""
    out: dict[str, list[float]] = {}
    for i, (k, text) in enumerate(texte.items(), 1):
        vec = embeddings.embed_text(text)
        if vec is not None:
            out[k] = vec
        if i % 25 == 0:
            print(f"  eingebettet {i}/{len(texte)}", flush=True)
    return out


# --- Ein Lauf -------------------------------------------------------------

BETRIEBSARTEN = {
    "A": {"zweiter_kanal": False, "pflicht": False,
          "beschreibung": "zweiter Kanal AUS (Stand vor 4167aef78)"},
    "B": {"zweiter_kanal": True, "pflicht": False,
          "beschreibung": "zweiter Kanal AN, Ensemble-Pflicht AUS (Auslieferung heute)"},
    "C": {"zweiter_kanal": True, "pflicht": True,
          "beschreibung": "zweiter Kanal AN, Ensemble-Pflicht AN"},
}


def _ids_der_treffer(nodes: list, lessons: list) -> list[str]:
    return [n["path"] for n in nodes] + [l["id"] for l in lessons]


def _text_der_treffer(nodes: list, lessons: list) -> str:
    teile = [f"{n.get('title','')} {n.get('summary','')}" for n in nodes]
    teile += [f"{l.get('description','')} {l.get('root_cause','')} {l.get('prevention','')}"
              for l in lessons]
    return " ".join(teile)


def _gattertext(e: dict) -> str:
    """Genau der Text, gegen den query() MIN_HITS prueft -- bei Knoten
    path+title+summary (NICHT content), bei Lehren description+root_cause+
    prevention. Wer hier content mitzaehlt, misst eine andere Schwelle als
    die, die im Abruf wirkt."""
    if e["kind"] == "node":
        return f"{korpus.kennung(e)} {e['title']} {e['summary']}"
    return f"{e['description']} {e['root_cause']} {e['prevention']}"


def _abteilung_von(kennung_: str, nach_kennung: dict) -> str | None:
    e = nach_kennung.get(kennung_)
    return e["abteilung"] if e else None


def lauf_betriebsart(art: str, db_path: Path, aufgaben: list[dict],
                     nach_kennung: dict, prompt_vektoren: dict[str, list[float]],
                     seed: int) -> list[dict]:
    cfg = BETRIEBSARTEN[art]
    rh.DB = str(db_path)
    os.environ["BEGOD_KNOWLEDGE_DB"] = str(db_path)
    os.environ["KNOWLEDGE_ENSEMBLE_PFLICHT"] = "1" if cfg["pflicht"] else "0"
    if hasattr(rh, "_zweiter_kanal_aktiv"):
        os.environ["KNOWLEDGE_ZWEITER_KANAL"] = "1" if cfg["zweiter_kanal"] else "0"
    ergebnisse = []
    for a in aufgaben:
        os.environ["BEGOD_KNOWLEDGE_PROJECT"] = a["abteilung"]
        kws = rh.keywords(a["prompt"])
        vec = prompt_vektoren.get(a["id"])
        nodes, lessons = rh.query(
            # rand ist eine FUNKTION (_maybe_explore ruft roll()), nicht ein
            # Random-Objekt. Je Aufgabe frisch aus demselben seed -- sonst
            # haengt der Erkundungswurf von der Reihenfolge der Aufgaben ab
            # und die drei Betriebsarten waeren nicht mehr am selben Wurf
            # gemessen.
            kws, rand=random.Random(seed).random, log_path=str(RECALL_LOG),
            cwd="/pruefstand", prompt=a["prompt"], embed_fn=lambda _t, _v=vec: _v)
        treffer = _ids_der_treffer(nodes, lessons)
        cluster_ids = [korpus.kennung(e) for e in korpus.CLUSTER.get(a.get("cluster") or "", [])]
        ergebnisse.append({
            "aufgabe": a["id"], "sorte": a["sorte"], "abteilung": a["abteilung"],
            "cluster": a.get("cluster"), "ziel": a["ziel"],
            "n_keywords": len(kws),
            # Warum eine loesbare Aufgabe verfehlt wurde, ist ohne diese Zahl
            # nicht entscheidbar: hits_am_ziel < MIN_HITS heisst, der
            # Stichwort-Kanal hat den Zieleintrag schon vor jeder Bewertung
            # ausgeschlossen -- das ist ein Befund ueber MIN_HITS, nicht
            # ueber Radar, Fusion oder Ensemble.
            "hits_am_ziel": (rh.hits(_gattertext(nach_kennung[a["ziel"]]), kws)
                             if a["ziel"] else None),
            "treffer": treffer,
            "schweigen": not treffer,
            "ziel_getroffen": bool(a["ziel"]) and a["ziel"] in treffer,
            "ziel_rang": treffer.index(a["ziel"]) + 1 if a["ziel"] in treffer else None,
            "fehlgriff": [t for t in treffer if t in cluster_ids] if a["sorte"] == "verfuehrerisch" else [],
            "fremdprojekt": [t for t in treffer
                             if _abteilung_von(t, nach_kennung) not in (None, a["abteilung"])],
            "koeder_aufgetaucht": korpus.KOEDER_NAME in _text_der_treffer(nodes, lessons),
        })
    os.environ.pop("BEGOD_KNOWLEDGE_PROJECT", None)
    return ergebnisse


def kennzahlen(ergebnisse: list[dict]) -> dict:
    nach_sorte = {s: [e for e in ergebnisse if e["sorte"] == s]
                  for s in ("loesbar", "unloesbar", "verfuehrerisch")}
    lb, ul, vf = nach_sorte["loesbar"], nach_sorte["unloesbar"], nach_sorte["verfuehrerisch"]
    return {
        "trefferguete": {"zaehler": sum(1 for e in lb if e["ziel_getroffen"]),
                         "nenner": len(lb), "sorte": "loesbar"},
        "schweigen_loesbar_FEHLER": {"zaehler": sum(1 for e in lb if e["schweigen"]),
                                     "nenner": len(lb), "sorte": "loesbar"},
        "schweigen_unloesbar_RICHTIG": {"zaehler": sum(1 for e in ul if e["schweigen"]),
                                        "nenner": len(ul), "sorte": "unloesbar"},
        "fehlgriff_verfuehrerisch": {"zaehler": sum(1 for e in vf if e["fehlgriff"]),
                                     "nenner": len(vf), "sorte": "verfuehrerisch"},
        "schweigen_gesamt": {"zaehler": sum(1 for e in ergebnisse if e["schweigen"]),
                             "nenner": len(ergebnisse), "sorte": "alle"},
        "koeder_ausserhalb_personal": {
            "zaehler": sum(1 for e in ergebnisse
                           if e["koeder_aufgetaucht"] and e["abteilung"] != korpus.KOEDER_ABTEILUNG),
            "nenner": sum(1 for e in ergebnisse if e["abteilung"] != korpus.KOEDER_ABTEILUNG),
            "sorte": "alle ausser Abteilung personal"},
        "fremdprojekt_uebertritt": {
            "zaehler": sum(1 for e in ergebnisse if e["fremdprojekt"]),
            "nenner": len(ergebnisse), "sorte": "alle"},
    }


# --- Gesamtlauf -----------------------------------------------------------

def run(out_path: Path = OUT_PATH, seed: int = SEED) -> dict:
    t0 = time.time()
    eintraege = korpus.alle_eintraege()
    nach_kennung = {korpus.kennung(e): e for e in eintraege}
    zirk = korpus.pruefe_zirkularitaet(eintraege)
    if zirk["zirkulaer"]:
        raise RuntimeError(f"Abbruch: zirkulaere Aufgaben {zirk['zirkulaer']}")

    print(f"Bestand: {len(eintraege)} Eintraege, {len(korpus.AUFGABEN)} Aufgaben", flush=True)
    texte = {korpus.kennung(e): korpus.volltext(e) for e in eintraege}
    texte.update({a["id"]: a["prompt"] for a in korpus.AUFGABEN})
    vektoren = berechne_vektoren(texte)
    fehlend = [k for k in texte if k not in vektoren]
    if fehlend:
        raise RuntimeError(f"Einbettung fehlgeschlagen fuer {len(fehlend)} Texte "
                           f"(Ollama erreichbar?) -- ohne vollstaendige Vektoren sind "
                           f"A und B nicht vergleichbar. Erste: {fehlend[:3]}")
    prompt_vektoren = {a["id"]: vektoren[a["id"]] for a in korpus.AUFGABEN}

    RECALL_LOG.parent.mkdir(parents=True, exist_ok=True)
    RECALL_LOG.write_text("", encoding="utf-8")

    baue_db(eintraege, DB_MIT, True, vektoren)
    baue_db(eintraege, DB_OHNE, False, None)

    # Eichlauf: derselbe Bestand OHNE das Ziel einer loesbaren Aufgabe.
    eich_aufgabe = next(a for a in korpus.AUFGABEN if a["id"] == korpus.EICHUNG_AUFGABE_ID)
    ohne_ziel = [e for e in eintraege if korpus.kennung(e) != eich_aufgabe["ziel"]]
    eich_vektoren = {k: v for k, v in vektoren.items() if k != eich_aufgabe["ziel"]}
    db_eich_mit = baue_db(ohne_ziel, DEMO_DIR / "abrufpruefstand-eich-mit.db", True, eich_vektoren)
    db_eich_ohne = baue_db(ohne_ziel, DEMO_DIR / "abrufpruefstand-eich-ohne.db", False, None)

    ergebnis = {
        "zeitpunkt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "seed": seed,
        "hub_head": os.popen(f"git -C {HUB} rev-parse HEAD").read().strip(),
        "hook_datei": str(HUB / "scripts" / "knowledge_recall_hook.py"),
        "hook_sha256": hashlib.sha256(
            (HUB / "scripts" / "knowledge_recall_hook.py").read_bytes()).hexdigest(),
        "hook_hat_zweiter_kanal_schalter": hasattr(rh, "_zweiter_kanal_aktiv"),
        "hook_parameter": {n: getattr(rh, n) for n in
                           ("MIN_HITS", "MAX_NODES", "MAX_LESSONS", "EXPLORE_RATE",
                            "TRUST_WEIGHT", "NOISE_FLOOR_MAD_MULT", "RADAR_MIN_SAMPLE_N",
                            "ENSEMBLE_TOP_N") if hasattr(rh, n)},
        "bestand": {"n_eintraege": len(eintraege),
                    "n_knoten": sum(1 for e in eintraege if e["kind"] == "node"),
                    "n_lehren": sum(1 for e in eintraege if e["kind"] == "lesson"),
                    "n_cluster_eintraege": sum(1 for e in eintraege if e["rolle"] == "cluster"),
                    "n_fuellmaterial": sum(1 for e in eintraege if e["rolle"] == "fuell"),
                    "abteilungen": dict(Counter(e["abteilung"] for e in eintraege))},
        "aufgaben": {"gesamt": len(korpus.AUFGABEN),
                     "je_sorte": dict(Counter(a["sorte"] for a in korpus.AUFGABEN))},
        "zirkularitaet": zirk,
        "eichung": {"aufgabe": eich_aufgabe["id"], "entferntes_ziel": eich_aufgabe["ziel"],
                     "aufbau_kann_schweigen": None},  # unten gesetzt
        "betriebsarten": {},
    }

    for art, cfg in BETRIEBSARTEN.items():
        db = DB_MIT if cfg["zweiter_kanal"] else DB_OHNE
        einzeln = lauf_betriebsart(art, db, korpus.AUFGABEN, nach_kennung, prompt_vektoren, seed)
        db_e = db_eich_mit if cfg["zweiter_kanal"] else db_eich_ohne
        eich = lauf_betriebsart(art, db_e, [eich_aufgabe], nach_kennung, prompt_vektoren, seed)[0]
        ergebnis["betriebsarten"][art] = {
            "beschreibung": cfg["beschreibung"],
            "zweiter_kanal": cfg["zweiter_kanal"], "ensemble_pflicht": cfg["pflicht"],
            "kennzahlen": kennzahlen(einzeln),
            "eichung_schweigt": eich["schweigen"],
            "eichung_treffer": eich["treffer"],
            "einzeln": einzeln,
        }
        k = ergebnis["betriebsarten"][art]["kennzahlen"]
        print(f"\n{art}  {cfg['beschreibung']}", flush=True)
        for name in ("trefferguete", "schweigen_loesbar_FEHLER", "schweigen_unloesbar_RICHTIG",
                     "fehlgriff_verfuehrerisch"):
            print(f"    {name:28s} {k[name]['zaehler']}/{k[name]['nenner']}", flush=True)
        # Die Eichung prueft ZWEI Dinge auf einmal, und sie sind nicht
        # dasselbe. (1) Kann dieser Aufbau ueberhaupt Schweigen erzeugen?
        # Das ist beantwortet, sobald IRGENDEINE Betriebsart nach dem
        # Entfernen des Ziels schweigt -- danach ist ein lautes Ergebnis
        # einer anderen Betriebsart eine Aussage ueber SIE, kein Mangel des
        # Aufbaus. (2) Spricht eine Betriebsart, obwohl die Antwort
        # nachweislich nicht mehr im Bestand liegt? Das ist ein Befund ueber
        # die Betriebsart. Der Satz unten haette beides verwechselt; die
        # Gesamtbewertung steht darum unter "eichung" im Ergebnis, nicht hier.
        print(f"    {'eichung schweigt':28s} {eich['schweigen']}"
              f"{'' if eich['schweigen'] else '  <-- spricht ohne vorhandene Antwort'}", flush=True)

    # Abnahme des Aufbaus selbst: schweigt WENIGSTENS EINE Betriebsart nach
    # dem Entfernen des Ziels, ist bewiesen, dass Schweigen in diesem Aufbau
    # erreichbar ist -- erst danach ist "spricht trotzdem" eine Aussage ueber
    # die Betriebsart und nicht ueber den Pruefstand.
    ergebnis["eichung"]["aufbau_kann_schweigen"] = any(
        v["eichung_schweigt"] for v in ergebnis["betriebsarten"].values())
    ergebnis["eichung"]["betriebsarten_die_schweigen"] = sorted(
        a for a, v in ergebnis["betriebsarten"].items() if v["eichung_schweigt"])
    if not ergebnis["eichung"]["aufbau_kann_schweigen"]:
        raise RuntimeError("Eichung fehlgeschlagen: keine einzige Betriebsart schweigt, "
                           "obwohl das Ziel entfernt wurde -- der Aufbau misst nichts.")

    ergebnis["laufzeit_s"] = round(time.time() - t0, 1)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGeschrieben: {out_path}", flush=True)
    return ergebnis


def selftest() -> None:
    """Netzlos. Prueft die zwei Stellen, an denen dieser Aufbau lautlos
    falsch messen koennte: (1) das Sicherheitsnetz gegen die echte DB,
    (2) dass kennzahlen() Schweigen bei loesbar und bei unloesbar
    GEGENLAEUFIG zaehlt -- verwechselt man sie, sieht die schlechteste
    Betriebsart wie die beste aus."""
    try:
        _sicherheitsnetz(ECHTE_DB)
        raise AssertionError("Sicherheitsnetz hat die echte DB durchgelassen")
    except RuntimeError:
        pass
    _sicherheitsnetz(DB_MIT)

    muster = [
        {"sorte": "loesbar", "schweigen": True, "ziel_getroffen": False, "fehlgriff": [],
         "abteilung": "netzbetrieb", "koeder_aufgetaucht": False, "fremdprojekt": []},
        {"sorte": "loesbar", "schweigen": False, "ziel_getroffen": True, "fehlgriff": [],
         "abteilung": "netzbetrieb", "koeder_aufgetaucht": False, "fremdprojekt": []},
        {"sorte": "unloesbar", "schweigen": True, "ziel_getroffen": False, "fehlgriff": [],
         "abteilung": "netzbetrieb", "koeder_aufgetaucht": False, "fremdprojekt": []},
        {"sorte": "verfuehrerisch", "schweigen": False, "ziel_getroffen": False,
         "fehlgriff": ["/apps/x/y"], "abteilung": "netzbetrieb",
         "koeder_aufgetaucht": True, "fremdprojekt": ["/apps/personal/z"]},
    ]
    k = kennzahlen(muster)
    assert k["trefferguete"] == {"zaehler": 1, "nenner": 2, "sorte": "loesbar"}, k["trefferguete"]
    assert k["schweigen_loesbar_FEHLER"]["zaehler"] == 1
    assert k["schweigen_unloesbar_RICHTIG"]["zaehler"] == 1
    assert k["fehlgriff_verfuehrerisch"]["zaehler"] == 1
    assert k["koeder_ausserhalb_personal"]["zaehler"] == 1
    assert k["fremdprojekt_uebertritt"]["zaehler"] == 1
    # Gegenprobe in die andere Richtung: schweigt NICHTS, sind beide
    # Schweigenzahlen null -- nicht nur die eine.
    laut = [dict(m, schweigen=False) for m in muster]
    k2 = kennzahlen(laut)
    assert k2["schweigen_loesbar_FEHLER"]["zaehler"] == 0
    assert k2["schweigen_unloesbar_RICHTIG"]["zaehler"] == 0
    print("selftest ok (Sicherheitsnetz + gegenlaeufige Schweigenzaehlung)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT_PATH))
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    run(out_path=Path(args.out), seed=args.seed)


if __name__ == "__main__":
    main()
