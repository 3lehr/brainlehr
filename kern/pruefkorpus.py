"""Pruefkorpus fuer Abrufguete (Plan hub/docs/PLAN_ABRUFGUETE_2026-08-07.md,
Schritt 1). Baut 40-60 Faelle aus dem echten Bestand: je Fall eine realistische
AUFGABE (von einem lokalen Ollama-Modell erzeugt) + die Kennung des Eintrags,
der dafuer der richtige waere. Ersetzt die bisherige Messung (Titel als
Anfrage, 20/20 -- misst nichts, siehe Plan).

ANTI-ZIRKULARITAET (Kern des Auftrags, deterministisch, KEIN Modellurteil):
    seltene Begriffe(Aufgabentext) ∩ seltene Begriffe(Zieleintrag) = leer
"selten" = IDF ueber den ganzen Bestand (Nodes + aktive Lessons, siehe
build_idf()) oberhalb einer Dokumenthaeufigkeits-Schwelle. RARE_MAX_DF=3 ist
GERATEN (nicht gemessen) -- Begruendung siehe dort. Teilt eine erzeugte
Aufgabe seltene Begriffe mit ihrem Ziel, wird sie verworfen und mit einer
Vermeidungs-Anweisung neu erzeugt (MAX_ATTEMPTS Versuche, danach Eintrag
uebersprungen und gezaehlt -- ein Eintrag ohne erzeugbare nicht-zirkulaere
Aufgabe ist selbst ein Befund).

STREUUNG ueber Sorten (CATEGORY_TARGETS): vorschreibende Lehren (type
pattern/antipattern), Fakten (knowledge_nodes.norm_rang IS NULL -- laut
schema.sql die "zentrale Unterscheidung", Fakt statt Norm), Normknoten mit
Geltungszeitraum (norm_rang NOT NULL, gilt_ab gesetzt), und Faelle OHNE
passendes Wissen als Eichung (target_id=None, feste Themenliste ausserhalb
jeder Projekt-Domaene -- Eichung braucht keine Zirkularitaetspruefung, es
gibt nichts, womit sie zirkulaer sein koennte).

ZIELGROESSE 40-60 Faelle: GERATEN (Plan §1, "Darunter bleibt die Streuung
groesser als jeder Effekt").

Wiederverwendet, nicht neu gebaut (Ponytail-Leiter): schreibpruefstand/
schreiblauf.py::_call_with_retry (Ollama-Aufruf, ein Retry bei Ausfall) --
derselbe Weg wie wissensnutzen.py/wissensnutzen_blind.py/fenstergroesse.py.
Fortschritt sofort als JSONL weggeschrieben (ein Fall je Zeile), Muster aus
fenstergroesse.py._append_jsonl (Auftrag Punkt 5: "seit heute").

Geaenderte Dateien ausserhalb dieser einen: KEINE. Nur diese Datei + eine
Testdatei (tests/test_pruefkorpus.py). knowledge_recall_hook.py, wissens-
nutzen*.py, wirkung.py, fenstergroesse.py, werkzeugabdeckung.py: nur
gelesen. Liest die echte knowledge.db read-only (mode=ro), schreibt nichts
hinein.
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
import json
import math
import random
import re
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

SHARED_KNOWLEDGE = _w
sys.path.insert(0, str(SHARED_KNOWLEDGE / "schreibpruefstand"))
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import schreiblauf as sl  # noqa: E402  -- _call_with_retry + DEFAULT_MODEL wiederverwendet

DB = str(SHARED_KNOWLEDGE / "knowledge.db")
MODEL = sl.DEFAULT_MODEL
TIMEOUT = 180.0
OUT_PATH = SHARED_KNOWLEDGE / "runs" / "pruefkorpus.json"
JSONL_PATH = OUT_PATH.with_suffix(".jsonl")

SEED = 20260807  # GERATEN (heutiges Datum als Seed, wie DEFAULT_SEED in pruefstand/korpus.py)

# GERATEN, nicht gemessen (Auftrag Punkt 2 verlangt, das zu kennzeichnen).
# Ein Begriff, der in hoechstens RARE_MAX_DF von ~880 Dokumenten vorkommt,
# gilt als "selten". Bei N~880 entspricht das idf >= log(880/3) ~= 5.68.
# Begruendung fuer 3 statt 1 oder 10: 1 waere zu eng (fast jedes Fachwort
# mit zwei Vorkommen faellt raus, die Pruefung wuerde nie mehr anschlagen);
# 10 waere zu locker (allgemeine Fachbegriffe wie "Flutter" oder "Ollama"
# kommen in > 10 Dokumenten vor und wuerden trotzdem als "selten" durchgehen,
# die Pruefung liesse dann echte Ueberschneidungen unbeanstandet). 3 ist ein
# Mittelwert, keine Messung -- wenn Schritt 3 (Optuna) je diese Zahl braucht,
# ist sie hier der Anschlusspunkt.
RARE_MAX_DF = 3

MAX_ATTEMPTS = 4  # GERATEN ("mehrere Fehlversuche", Auftrag Punkt 2)

# Aufnahmegrenze fuer die Wortueberlappung Aufgabe->Ziel, in Prozent.
# HERLEITUNG (gemessen 2026-08-09, NICHT gegen die Trefferquote geeicht):
# exaktes MAXIMUM des alten Pruefkorpus runs/pruefkorpus.jsonl (35 Faelle mit
# Ziel; Quartile 0 / 7,1 / 8,7 / 13,6 / 27,8). Diese Grenze laesst also alle
# 35 alten Faelle durch (der groesste davon liegt GENAU auf ihr) und
# verwirft beim neuen Haiku-Korpus (55 Faelle, mittlere Ueberlappung 34,1 %)
# den leichteren Teil. Waere sie gegen die Trefferquote (16/35 vs. 51/55)
# geeicht, waere sie zirkulaer -- die Grenze soll die Schwierigkeit messen,
# nicht das Ergebnis rechtfertigen.
AUFNAHMEGRENZE_PROZENT = 27.8


def wortueberlappung(task_text: str, target_text: str) -> float:
    """Wortueberlappung Aufgabe->Ziel in Prozent: |tokenize(task) ∩
    tokenize(target)| / |tokenize(task)| * 100. Nenner ist die AUFGABE, nicht
    das Ziel (siehe FAKTEN des Auftrags) -- eine kurze Aufgabe, die das Ziel
    komplett zitiert, waere sonst milder bewertet als eine lange."""
    task_tokens = tokenize(task_text)
    if not task_tokens:
        return 0.0
    target_tokens = tokenize(target_text)
    return len(task_tokens & target_tokens) / len(task_tokens) * 100.0


def erfuellt_aufnahmegrenze(overlap_prozent: float, grenze: float = AUFNAHMEGRENZE_PROZENT) -> bool:
    """Inklusiv (<=): die Grenze ist der exakte Maximalwert des alten
    Korpus, also gehoert der Fall, der sie definiert, selbst noch dazu --
    eine exklusive Grenze wuerde sonst den eigenen Ableitungsfall verwerfen
    und "laesst alle 35 alten Faelle durch" waere falsch."""
    return overlap_prozent <= grenze

# Wieviele Faelle je Sorte -- Summe 45, innerhalb der geratenen Zielgroesse 40-60.
CATEGORY_TARGETS = {"lesson": 15, "fact": 12, "norm": 8, "negative": 10}

# Kurze Stopwortliste, identisch zur Absicht von scripts/knowledge_recall_hook.py
# STOP (dort nicht importiert -- dieser Pruefstand liest die DB direkt und
# braucht keine sonstige Hook-Logik, ein Reimport waere die einzige Kopplung
# an eine Datei, die laut Grenzen tabu ist).
STOP = {
    "und", "oder", "der", "die", "das", "den", "dem", "ein", "eine", "einen", "einem",
    "ist", "sind", "war", "wird", "werden", "kann", "soll", "muss", "für", "mit", "von",
    "auf", "aus", "bei", "zum", "zur", "des", "als", "auch", "nicht", "noch", "wie", "was",
    "wenn", "dann", "aber", "nur", "mir", "mich", "dir", "dich", "ich", "wir", "ihr", "sie",
    "the", "and", "for", "that", "this", "with", "from", "have", "has", "was", "are", "you",
    "sowie", "diese", "dieser", "dieses", "einem", "einer", "sein", "seine", "ihre",
}

_FOLD_TABLE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def fold_de(text: str) -> str:
    return text.lower().translate(_FOLD_TABLE)


def tokenize(text: str) -> set[str]:
    """Alle Woerter ab 4 Zeichen, gefaltet, ohne Stopwoerter -- anders als
    knowledge_recall_hook.keywords() KEIN [:8]-Deckel: fuer die IDF-Ermittlung
    und die Zirkularitaetspruefung zaehlt jedes Wort, nicht nur die ersten acht."""
    words = re.findall(r"[A-Za-zÄÖÜäöüß0-9]{4,}", fold_de(text))
    return {w for w in words if w not in STOP}


# --- Bestand lesen -----------------------------------------------------

def load_bestand(db_path: str = DB) -> tuple[list[dict], list[dict]]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5.0)
    conn.row_factory = sqlite3.Row
    nodes = [dict(r) for r in conn.execute(
        "SELECT id, path, title, summary, content, norm_rang, gilt_ab, gattung "
        "FROM knowledge_nodes WHERE zurueckgezogen = 0"
    )]
    lessons = [dict(r) for r in conn.execute(
        "SELECT id, type, description, root_cause, prevention, severity "
        "FROM lessons_learned WHERE status != 'resolved'"
    )]
    conn.close()
    return nodes, lessons


def node_text(n: dict) -> str:
    return f"{n['title']}\n{n['summary']}\n{(n.get('content') or '')[:800]}"


def lesson_text(l: dict) -> str:
    return f"{l['description']}\n{l.get('root_cause') or ''}\n{l.get('prevention') or ''}"


def build_idf(nodes: list[dict], lessons: list[dict]) -> dict[str, float]:
    """IDF ueber den ganzen Bestand (Nodes + aktive Lessons), ein Dokument =
    eine Zeile. df = wieviele Dokumente ein Wort mindestens einmal enthalten."""
    df: Counter[str] = Counter()
    n_docs = 0
    for n in nodes:
        df.update(tokenize(node_text(n)))
        n_docs += 1
    for l in lessons:
        df.update(tokenize(lesson_text(l)))
        n_docs += 1
    return {w: math.log(n_docs / c) for w, c in df.items()}, n_docs, df


def rare_terms(text: str, idf: dict[str, float], df: Counter, rare_max_df: int = RARE_MAX_DF) -> set[str]:
    return {w for w in tokenize(text) if df.get(w, 0) <= rare_max_df and w in idf}


def is_circular(task_text: str, target_text: str, idf: dict, df: Counter) -> set[str]:
    """Gibt die geteilten seltenen Begriffe zurueck (leer = nicht zirkulaer)."""
    return rare_terms(task_text, idf, df) & rare_terms(target_text, idf, df)


# --- Erzeugung -----------------------------------------------------------

_GEN_TEMPLATE = """Ausgangswissen (wird NICHT direkt zitiert oder umschrieben):
{quelle}

Schreibe EINE realistische Alltags- oder Arbeitssituation (2-4 Saetze, \
deutsch), in der genau dieses Wissen gebraucht wuerde. Beschreibe eine \
konkrete Lage/ein Problem, KEINE Frage nach dem Eintrag selbst. Verwende \
andere Woerter als der Ausgangstext -- keine Fachbegriffe oder Eigennamen \
von dort wiederholen.{vermeiden}
Antworte NUR mit dem Aufgabentext, kein Vorwort, keine Ueberschrift."""

_NEGATIVE_TOPICS = [
    "Nenne den kubectl-Befehl, um alle Pods im Namespace default aufzulisten.",
    "Beschreibe in 2 Saetzen, wie man einen Hefeteig fuer Pizza ansetzt.",
    "Welche Excel-Formel summiert Spalte B, wenn Spalte A 'ja' enthaelt?",
    "Wie lautet der Befehl, um in git einen Branch umzubenennen (lokal + remote)?",
    "Nenne drei Faustregeln fuer Rosenschnitt im Fruehjahr.",
    "Wie berechnet man die Umlaufbahnperiode eines Satelliten aus der Bahnhoehe?",
    "Welches Papier braucht ein Restaurant fuer die Anmeldung beim Ordnungsamt?",
    "Erklaere kurz den Unterschied zwischen TCP und UDP.",
    "Wie stellt man in macOS die Bildschirmaufloesung per Terminal-Befehl ein?",
    "Nenne die Zutaten fuer einen klassischen Bechamel.",
    "Wie kuendigt man in Deutschland einen Handyvertrag fristgerecht?",
    "Welcher Knoten eignet sich zum schnellen, loesbaren Verzurren einer Plane?",
]


def _generate(prompt: str, model: str = MODEL, timeout: float = TIMEOUT) -> tuple[str | None, str | None, int]:
    return sl._call_with_retry(prompt, model=model, base_url=sl.DEFAULT_OLLAMA_URL, timeout=timeout)


def generate_task(target_text: str, idf: dict, df: Counter, rng: random.Random,
                   model: str = MODEL) -> dict:
    """Erzeugt eine Aufgabe zu target_text, prueft Zirkularitaet UND
    Wortueberlappung (Auftrag Punkt 3 -- dieselbe Wiederholungsmechanik,
    keine zweite), versucht bei Verstoss bis zu MAX_ATTEMPTS mal neu (mit
    Vermeidungshinweis). Gibt {"accepted": bool, "task": str|None,
    "attempts": [...], "error": str|None, "ueberlappung": float|None}."""
    attempts = []
    vermeiden = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = _GEN_TEMPLATE.format(quelle=target_text[:1200], vermeiden=vermeiden)
        raw, err, retries = _generate(prompt, model=model)
        if err or not raw or not raw.strip():
            attempts.append({"attempt": attempt, "text": None, "error": err,
                              "collision": None, "ueberlappung": None})
            continue
        task_text = raw.strip()
        collision = is_circular(task_text, target_text, idf, df)
        overlap = wortueberlappung(task_text, target_text)
        zu_aehnlich = not erfuellt_aufnahmegrenze(overlap)
        attempts.append({
            "attempt": attempt, "text": task_text, "error": None,
            "collision": sorted(collision) if collision else [],
            "ueberlappung": round(overlap, 1),
        })
        if not collision and not zu_aehnlich:
            return {"accepted": True, "task": task_text, "attempts": attempts,
                     "error": None, "ueberlappung": round(overlap, 1)}
        if collision:
            vermeiden = f" Vermeide zusaetzlich diese Woerter: {', '.join(sorted(collision))}."
        else:
            vermeiden = (" Formuliere deutlich freier -- die Ueberschneidung mit dem "
                         "Ausgangswissen war zu hoch, benutze andere Woerter und Saetze.")
    return {"accepted": False, "task": None, "attempts": attempts, "ueberlappung": None,
            "error": "kein zulaessiger Fall (unzirkulaer und unter Aufnahmegrenze) "
                     "nach MAX_ATTEMPTS Versuchen"}


# --- Auswahl je Sorte -----------------------------------------------------

def pick_candidates(nodes: list[dict], lessons: list[dict], rng: random.Random) -> dict[str, list[dict]]:
    # gattung='nachschlagewerk' (z.B. NASA-Import) ist laut Wissensknoten
    # 096669de ausdruecklich Heuhaufen -- darf als Ablenkung im Bestand liegen
    # (bleibt in load_bestand()/IDF unberuehrt), aber nie ZIEL eines Prueffalls.
    lesson_pool = [l for l in lessons if l["type"] in ("pattern", "antipattern")]
    fact_pool = [n for n in nodes if n["norm_rang"] is None and n["summary"]
                 and n["gattung"] != "nachschlagewerk"]
    norm_pool = [n for n in nodes if n["norm_rang"] is not None and n["gilt_ab"]
                 and n["gattung"] != "nachschlagewerk"]
    picks = {}
    for key, pool in (("lesson", lesson_pool), ("fact", fact_pool), ("norm", norm_pool)):
        k = min(CATEGORY_TARGETS[key], len(pool))
        picks[key] = rng.sample(pool, k) if pool else []
    return picks


# --- Lauf ------------------------------------------------------------------

def _append_jsonl(record: dict, path: Path = JSONL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()


def run(out_path: Path = OUT_PATH, seed: int = SEED, model: str = MODEL) -> dict:
    # _append_jsonl()'s Vorgabewert (path: Path = JSONL_PATH) wird nur
    # ausgewertet, wenn NICHTS uebergeben wird -- er kennt out_path nicht und
    # kann es nicht kennen. Genau das geschah hier: run(out_path=...) reichte
    # den gewaehlten Pfad nie weiter, jeder Aufruf traf also immer JSONL_PATH,
    # unabhaengig von --out. Ein Vorgabewert fuer einen Ausgabepfad ist
    # deshalb gefaehrlich, sobald es einen zweiten, von aussen wählbaren
    # Ausgabepfad gibt: er wird zur stillen Rueckfallkonstante, die den
    # eigentlich gewaehlten Wert ueberstimmt. Fix: EIN aus out_path
    # abgeleiteter jsonl_path, explizit an jeden _append_jsonl()-Aufruf
    # durchgereicht -- derselbe Bezug wie OUT_PATH/JSONL_PATH oben.
    jsonl_path = out_path.with_suffix(".jsonl")
    rng = random.Random(seed)
    nodes, lessons = load_bestand()
    idf, n_docs, df = build_idf(nodes, lessons)
    print(f"Bestand: {len(nodes)} Nodes + {len(lessons)} Lessons = {n_docs} Dokumente, "
          f"{len(idf)} Vokabeln, RARE_MAX_DF={RARE_MAX_DF}", flush=True)

    picks = pick_candidates(nodes, lessons, rng)
    cases: list[dict] = []
    skipped: list[dict] = []

    for category in ("lesson", "fact", "norm"):
        for entry in picks[category]:
            if category == "lesson":
                target_id, label, text = entry["id"], entry["description"][:80], lesson_text(entry)
            else:
                target_id, label, text = entry["path"], entry["title"], node_text(entry)
            result = generate_task(text, idf, df, rng, model=model)
            record = {
                "category": category, "target_kind": "lesson" if category == "lesson" else "node",
                "target_id": target_id, "target_label": label,
                "accepted": result["accepted"], "task": result["task"],
                "attempts": result["attempts"], "ueberlappung": result.get("ueberlappung"),
            }
            _append_jsonl(record, path=jsonl_path)
            if result["accepted"]:
                cases.append({"category": category, "target_kind": record["target_kind"],
                               "target_id": target_id, "target_label": label, "prompt": result["task"],
                               "ueberlappung": result.get("ueberlappung")})
                print(f"  {category} {target_id}: ok nach {len(result['attempts'])} Versuch(en)", flush=True)
            else:
                skipped.append({"category": category, "target_id": target_id, "target_label": label,
                                 "reason": result["error"]})
                print(f"  {category} {target_id}: UEBERSPRUNGEN ({result['error']})", flush=True)

    # Negativfaelle sind bereits fertig formulierte Aufgaben (siehe
    # _NEGATIVE_TOPICS, Stil wie PROMPT_C in wissensnutzen_blind.py) -- KEIN
    # Ollama-Aufruf hier. Fund beim Berichten (vor Abschluss korrigiert):
    # die vorherige Fassung schickte die Topic-FRAGE an Ollama und speicherte
    # dessen ANTWORT als "task" -- Rollentausch, die Aufgabe waere die
    # Modellantwort gewesen statt die Frage selbst.
    topics = rng.sample(_NEGATIVE_TOPICS, min(CATEGORY_TARGETS["negative"], len(_NEGATIVE_TOPICS)))
    for topic in topics:
        # Kein Ziel -> keine Wortueberlappung berechenbar, ueberlappung bleibt
        # None (nicht 0.0 -- 0.0 waere "gemessen und leer", None ist "nicht
        # anwendbar", ein Unterschied fuer spaetere Auswertung).
        record = {"category": "negative", "target_kind": None, "target_id": None,
                   "target_label": None, "accepted": True,
                   "task": topic, "attempts": [{"attempt": 1, "text": topic, "error": None}],
                   "ueberlappung": None}
        _append_jsonl(record, path=jsonl_path)
        cases.append({"category": "negative", "target_kind": None, "target_id": None,
                       "target_label": None, "prompt": topic, "ueberlappung": None})
        print(f"  negative: ok ({topic[:40]}...)", flush=True)

    verteilung = Counter(c["category"] for c in cases)
    output = {
        "seed": seed, "model": model, "rare_max_df": RARE_MAX_DF, "max_attempts": MAX_ATTEMPTS,
        "n_docs": n_docs, "n_vocab": len(idf),
        "n_cases": len(cases), "n_skipped": len(skipped),
        "verteilung": dict(verteilung), "cases": cases, "skipped": skipped,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGeschrieben: {out_path}", flush=True)
    print(f"Erzeugt: {len(cases)}  Uebersprungen: {len(skipped)}  Verteilung: {dict(verteilung)}", flush=True)
    return output


def _resolve_target_text(rec: dict, node_by_path: dict, lesson_by_id: dict) -> str | None:
    """Loest target_id eines JSONL-Falls gegen den aktuellen Bestand auf.
    target_kind=='node' -> target_id ist ein PFAD (nicht die id, siehe
    FAKTEN); target_kind=='lesson' -> target_id ist die id. Gibt None, wenn
    das Ziel im aktuellen Bestand nicht (mehr) existiert."""
    if rec.get("target_kind") == "node":
        node = node_by_path.get(rec["target_id"])
        return node_text(node) if node else None
    if rec.get("target_kind") == "lesson":
        lesson = lesson_by_id.get(rec["target_id"])
        return lesson_text(lesson) if lesson else None
    return None


def filter_bestehenden_korpus(in_path: Path, out_path: Path,
                               grenze: float = AUFNAHMEGRENZE_PROZENT,
                               nodes: list[dict] | None = None,
                               lessons: list[dict] | None = None) -> dict:
    """Filtert eine VOR Einfuehrung der Aufnahmegrenze erzeugte JSONL-Datei
    nachtraeglich: berechnet je Fall die Wortueberlappung gegen den
    aktuellen Bestand und schreibt nur die Faelle bis einschliesslich
    `grenze` nach out_path, jeweils mit eigenem "ueberlappung"-Feld. Liest
    in_path nur (oeffnet es nie zum Schreiben) -- die Ursprungsdatei bleibt
    unveraendert. nodes/lessons injizierbar fuer Tests (Walkthrough-Doktrin);
    None -> live aus load_bestand()."""
    if nodes is None or lessons is None:
        nodes, lessons = load_bestand()
    node_by_path = {n["path"]: n for n in nodes}
    lesson_by_id = {l["id"]: l for l in lessons}

    gelesen = 0
    ohne_ziel = 0
    ziel_nicht_gefunden = 0
    behalten = []
    verworfen = []
    with in_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            gelesen += 1
            rec = json.loads(line)
            if not rec.get("target_id"):
                ohne_ziel += 1
                continue
            target_text = _resolve_target_text(rec, node_by_path, lesson_by_id)
            if target_text is None:
                ziel_nicht_gefunden += 1
                continue
            overlap = round(wortueberlappung(rec["task"], target_text), 1)
            rec_out = dict(rec, ueberlappung=overlap)
            if erfuellt_aufnahmegrenze(overlap, grenze):
                behalten.append(rec_out)
            else:
                verworfen.append(rec_out)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for rec_out in behalten:
            f.write(json.dumps(rec_out, ensure_ascii=False) + "\n")

    return {"gelesen": gelesen, "behalten": len(behalten), "verworfen": len(verworfen),
            "ohne_ziel_uebersprungen": ohne_ziel, "ziel_nicht_gefunden": ziel_nicht_gefunden,
            "verworfene_faelle": verworfen}


def _selftest() -> None:
    """Netzloser Selbsttest: IDF/Tokenize/Zirkularitaetspruefung, kein Ollama."""
    nodes = [
        {"id": "n1", "path": "/a/x", "title": "Existenzgruender Broschuere",
         "summary": "Amtliche Beschreibung fuer Existenzgruender in Niedersachsen.",
         "content": "", "norm_rang": None, "gilt_ab": None, "gattung": "arbeitsbestand"},
        {"id": "n2", "path": "/a/y", "title": "Allgemeiner Hinweis",
         "summary": "Ein Text ueber irgendetwas Allgemeines mit vielen ueblichen Woertern.",
         "content": "", "norm_rang": 1, "gilt_ab": "2026-01-01", "gattung": "arbeitsbestand"},
    ]
    lessons = [
        {"id": "L-1", "type": "antipattern", "severity": "high",
         "description": "AlertDialog showDialog erzeugt Vollbild-Weissraum in ActionScreen.",
         "root_cause": "Globaler Shim faengt showDialog ab.",
         "prevention": "ActionScreen(expandPrimaryAction:true) verwenden."},
    ]
    idf, n_docs, df = build_idf(nodes, lessons)
    assert n_docs == 3
    assert "existenzgruender" in idf  # gefaltet, in Node n1
    assert df["existenzgruender"] == 1

    # Zirkularitaetspruefung MUSS anschlagen, wenn die Aufgabe den Zieltitel
    # woertlich enthaelt (Abnahme-Vorgabe: "bau probeweise einen Fall ...").
    target_text = lesson_text(lessons[0])
    zirkulaer_task = "Ich habe ein Problem mit ActionScreen und showDialog in meiner App."
    collision = is_circular(zirkulaer_task, target_text, idf, df)
    assert collision, "Woertliche Titel-Uebernahme haette erkannt werden muessen"
    print(f"  Zirkularitaet erkannt: geteilte seltene Begriffe = {sorted(collision)}")

    # Gegenprobe: eine Aufgabe, die dasselbe Wissen braucht, aber andere
    # Woerter benutzt, darf NICHT als zirkulaer gelten.
    freie_task = ("Im Auto-Werkstattbuch soll eine Bestaetigung erscheinen, bevor "
                  "eine Fahrt beendet wird, ohne den Bildschirm mit weissem Rand zu zeigen.")
    collision2 = is_circular(freie_task, target_text, idf, df)
    assert not collision2, f"Frei formulierte Aufgabe faelschlich als zirkulaer erkannt: {collision2}"
    print("  Frei formulierte Aufgabe (andere Woerter) NICHT als zirkulaer erkannt: ok")

    # rare_terms: ein Wort, das in > RARE_MAX_DF Dokumenten vorkommt, gilt
    # NICHT als selten -- Allerweltswort darf keine Kollision ausloesen.
    haeufig_idf, haeufig_n, haeufig_df = build_idf(
        [{"id": f"n{i}", "path": f"/x{i}", "title": "Uebersicht", "summary": "Uebersicht ueber alles",
          "content": "", "norm_rang": None, "gilt_ab": None} for i in range(6)],
        [],
    )
    assert haeufig_df["uebersicht"] == 6 > RARE_MAX_DF
    assert rare_terms("Uebersicht", haeufig_idf, haeufig_df) == set()
    print("  Haeufiges Wort ueber RARE_MAX_DF gilt nicht als selten: ok")

    # pick_candidates: Kategorien liefern nur passende Eintraege, nie mehr
    # als angefordert, und respektieren einen leeren Pool.
    picks = pick_candidates(nodes, lessons, random.Random(1))
    assert picks["lesson"] and picks["lesson"][0]["id"] == "L-1"
    assert all(n["norm_rang"] is None for n in picks["fact"])
    assert all(n["norm_rang"] is not None and n["gilt_ab"] for n in picks["norm"])
    print("  pick_candidates: Kategorien-Filter ok")

    print(f"selftest ok ({len(idf)} Vokabeln im Mini-Bestand, RARE_MAX_DF={RARE_MAX_DF})", file=sys.stderr)

    _selftest_wortueberlappung()
    _selftest_run_routing_und_gattung()
    _selftest_filter_bestehenden_korpus()


def _selftest_wortueberlappung() -> None:
    """(a)/(b)/(c) der Abnahme: knapp unter/ueber/exakt auf der Aufnahmegrenze.
    Rechnet direkt mit der Grenze als Wert -- vermeidet, einen Aufgaben/Ziel-
    Text so zu konstruieren, dass float-Rundung zufaellig genau 27.8 ergibt."""
    assert erfuellt_aufnahmegrenze(AUFNAHMEGRENZE_PROZENT - 0.1) is True, (
        "(a) knapp unter der Grenze haette angenommen werden muessen")
    print("  (a) knapp unter der Aufnahmegrenze: angenommen -- ok")

    assert erfuellt_aufnahmegrenze(AUFNAHMEGRENZE_PROZENT + 0.1) is False, (
        "(b) knapp ueber der Grenze haette verworfen werden muessen")
    print("  (b) knapp ueber der Aufnahmegrenze: verworfen -- ok")

    assert erfuellt_aufnahmegrenze(AUFNAHMEGRENZE_PROZENT) is True, (
        "(c) exakt auf der Grenze haette angenommen werden muessen (inklusiv, siehe Kommentar)")
    print("  (c) exakt auf der Aufnahmegrenze: angenommen (inklusiv) -- ok")

    # wortueberlappung(): 4 von 5 Aufgaben-Token stecken auch im Ziel -> 80%.
    task = "Katze Hund Baum Wolke Regen"
    target = "Katze Hund Baum Wolke Sonne"
    overlap = wortueberlappung(task, target)
    assert abs(overlap - 80.0) < 0.01, f"erwartet 80.0, war {overlap}"
    print(f"  wortueberlappung() Grundrechnung: {overlap}% -- ok")

    # (d) generate_task() liefert das Ueberlappungsfeld mit -- sowohl im
    # akzeptierten Fall als auch, wenn MAX_ATTEMPTS wegen zu hoher
    # Ueberlappung ausgeschoepft wird (nie zirkulaer, aber immer zu aehnlich).
    idf, n_docs, df = build_idf([], [])
    zu_aehnliche_antwort = "Katze Hund Baum Wolke Regen"  # exakt = target, 100% Ueberlappung

    def _fake_generate_immer_zu_aehnlich(prompt, model=MODEL, timeout=TIMEOUT):
        return zu_aehnliche_antwort, None, 0

    global _generate
    orig_generate = _generate
    try:
        _generate = _fake_generate_immer_zu_aehnlich
        result = generate_task("Katze Hund Baum Wolke Regen", idf, df, random.Random(1))
    finally:
        _generate = orig_generate
    assert result["accepted"] is False, "haette nach MAX_ATTEMPTS als zu aehnlich verworfen werden muessen"
    assert result["ueberlappung"] is None
    assert len(result["attempts"]) == MAX_ATTEMPTS
    assert all(a["ueberlappung"] == 100.0 for a in result["attempts"])
    print("  (d) generate_task() traegt ueberlappung in jedem Versuch mit, "
          "verwirft bei Dauer-Ueberschreitung nach MAX_ATTEMPTS -- ok")

    def _fake_generate_frei(prompt, model=MODEL, timeout=TIMEOUT):
        return "Ein voellig anderer Satz ohne jede Beruehrung mit dem Ziel.", None, 0

    try:
        _generate = _fake_generate_frei
        result2 = generate_task("Katze Hund Baum Wolke Regen", idf, df, random.Random(1))
    finally:
        _generate = orig_generate
    assert result2["accepted"] is True
    assert result2["ueberlappung"] is not None and result2["ueberlappung"] < AUFNAHMEGRENZE_PROZENT
    print(f"  (d) frei formulierter Fall angenommen, ueberlappung={result2['ueberlappung']}% -- ok")


def _selftest_filter_bestehenden_korpus() -> None:
    """(e): filter_bestehenden_korpus() liest die Eingabedatei nur -- Inhalt
    vor/nach dem Lauf identisch. Zusaetzlich: ein Fall unter der Grenze
    bleibt, einer darueber faellt weg, beide tragen ein ueberlappung-Feld."""
    import tempfile
    nodes = [{"id": "n1", "path": "/p/ziel", "title": "Katze Hund Baum Wolke Regen",
               "summary": "", "content": "", "norm_rang": None, "gilt_ab": None, "gattung": "arbeitsbestand"}]
    lessons: list[dict] = []
    tmpdir = Path(tempfile.mkdtemp(prefix="pruefkorpus_filter_selftest_"))
    in_path = tmpdir / "in.jsonl"
    out_path = tmpdir / "out.jsonl"
    faelle = [
        {"target_kind": "node", "target_id": "/p/ziel",
         "task": "Katze Hund Baum Wolke Sonne"},  # 4/5 Token treffen -> 80%, ueber der Grenze
        {"target_kind": "node", "target_id": "/p/ziel",
         "task": "Ein Text ohne jede Beruehrung ueberhaupt"},  # 0% -> unter der Grenze
    ]
    inhalt_vorher = "\n".join(json.dumps(f, ensure_ascii=False) for f in faelle) + "\n"
    in_path.write_text(inhalt_vorher, encoding="utf-8")

    ergebnis = filter_bestehenden_korpus(in_path, out_path, nodes=nodes, lessons=lessons)

    inhalt_nachher = in_path.read_text(encoding="utf-8")
    assert inhalt_nachher == inhalt_vorher, "(e) Ursprungsdatei wurde durch das Filtern veraendert"
    print("  (e) Ursprungsdatei beim Filtern unveraendert -- ok")

    assert ergebnis["gelesen"] == 2 and ergebnis["behalten"] == 1 and ergebnis["verworfen"] == 1
    behaltene = [json.loads(l) for l in out_path.read_text(encoding="utf-8").splitlines()]
    assert len(behaltene) == 1
    assert behaltene[0]["task"].startswith("Ein Text")
    assert "ueberlappung" in behaltene[0] and behaltene[0]["ueberlappung"] < AUFNAHMEGRENZE_PROZENT
    print(f"  Filterlauf: gelesen={ergebnis['gelesen']} behalten={ergebnis['behalten']} "
          f"verworfen={ergebnis['verworfen']} -- ok")

    for p in (in_path, out_path):
        if p.exists():
            p.unlink()
    tmpdir.rmdir()


def _fake_load_bestand(db_path: str = DB) -> tuple[list[dict], list[dict]]:
    """Ersatz fuer load_bestand() im Selbsttest -- kein DB-Zugriff noetig,
    liefert je Kategorie einen arbeitsbestand- und einen nachschlagewerk-
    Eintrag, damit die Ausschluss-Pruefung etwas zum Ausschliessen hat."""
    nodes = [
        {"id": "n1", "path": "/f/1", "title": "Fakt eins", "summary": "s1", "content": "",
         "norm_rang": None, "gilt_ab": None, "gattung": "arbeitsbestand"},
        {"id": "n2", "path": "/f/2", "title": "Nachschlage-Fakt", "summary": "s2", "content": "",
         "norm_rang": None, "gilt_ab": None, "gattung": "nachschlagewerk"},
        {"id": "n3", "path": "/n/1", "title": "Norm eins", "summary": "s3", "content": "",
         "norm_rang": 1, "gilt_ab": "2026-01-01", "gattung": "arbeitsbestand"},
        {"id": "n4", "path": "/n/2", "title": "Nachschlage-Norm", "summary": "s4", "content": "",
         "norm_rang": 1, "gilt_ab": "2026-01-01", "gattung": "nachschlagewerk"},
    ]
    lessons = [
        {"id": "L-1", "type": "pattern", "description": "d1", "root_cause": "", "prevention": "",
         "severity": "low"},
    ]
    return nodes, lessons


def _fake_generate_task(target_text: str, idf: dict, df: Counter, rng: random.Random,
                         model: str = MODEL) -> dict:
    """Ersatz fuer generate_task() im Selbsttest -- KEIN Ollama-Aufruf, liefert
    sofort einen akzeptierten Fall. So bleibt run() im Selbsttest netzlos
    durchlaufbar (Abnahme-Vorgabe: kein Modellaufruf)."""
    return {"accepted": True, "task": f"Testaufgabe zu {target_text[:20]}", "attempts": [],
            "error": None, "ueberlappung": 1.2}


def _selftest_run_routing_und_gattung() -> None:
    """(a) run(out_path=...) darf JSONL_PATH (die Vorgabedatei) nicht anfassen
    -- die Zeilenzahl vor/nach dem Lauf muss gleich bleiben.
    (b) Kein erzeugter Fall hat ein Ziel mit gattung='nachschlagewerk'.
    load_bestand/generate_task werden durch netzlose Fakes ersetzt (Modul-
    globale Umschaltung mit Wiederherstellung im finally) -- kein Ollama,
    keine Netzverbindung."""
    import tempfile
    global load_bestand, generate_task
    orig_load_bestand, orig_generate_task = load_bestand, generate_task
    tmpdir = Path(tempfile.mkdtemp(prefix="pruefkorpus_selftest_"))
    custom_out = tmpdir / "custom_run.json"
    custom_jsonl = custom_out.with_suffix(".jsonl")
    vor = JSONL_PATH.read_text(encoding="utf-8").count("\n") if JSONL_PATH.exists() else -1
    try:
        load_bestand = _fake_load_bestand
        generate_task = _fake_generate_task
        output = run(out_path=custom_out, seed=1, model="fake-model")
    finally:
        load_bestand, generate_task = orig_load_bestand, orig_generate_task

    nach = JSONL_PATH.read_text(encoding="utf-8").count("\n") if JSONL_PATH.exists() else -1
    assert vor == nach, (
        f"run(out_path=...) hat die Vorgabedatei {JSONL_PATH} veraendert "
        f"({vor} -> {nach} Zeilen)"
    )
    print(f"  Vorgabedatei {JSONL_PATH.name} unveraendert ({vor} Zeilen): ok")

    assert custom_jsonl.exists() and custom_jsonl.read_text(encoding="utf-8").strip(), (
        f"eigene JSONL {custom_jsonl} wurde nicht befuellt"
    )
    print(f"  eigener Ausgabepfad {custom_jsonl.name} befuellt: ok")

    nachschlagewerk_ziele = [
        c for c in output["cases"]
        if c["target_kind"] == "node" and c["target_id"] in ("/f/2", "/n/2")
    ]
    assert not nachschlagewerk_ziele, f"nachschlagewerk-Knoten als Ziel gewaehlt: {nachschlagewerk_ziele}"
    print("  kein nachschlagewerk-Knoten als Ziel: ok")

    for p in (custom_out, custom_jsonl):
        if p.exists():
            p.unlink()
    tmpdir.rmdir()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT_PATH))
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--selftest", action="store_true",
                     help="Netzloser Selbsttest von IDF/Zirkularitaetspruefung, kein Ollama-Aufruf")
    args = ap.parse_args()
    if args.selftest:
        _selftest()
        return
    run(out_path=Path(args.out), seed=args.seed, model=args.model)


if __name__ == "__main__":
    main()
