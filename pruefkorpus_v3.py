"""Pruefkorpus V3 -- erfundene Gegenstaende mit Zahlenwerten, Aufgaben die
RECHNEN (Betreiber-Entwurf 2026-08-07). Ueberschreibt pruefkorpus.py und
pruefkorpus_v2.py NICHT -- die bleiben als gescheiterte Vorstufen stehen.

WARUM DIESE FORM (vs. v1/v2, die an Formulierungsermessen/Zirkularitaet
scheiterten, siehe deren eigene Docstrings und L-352afa):
  Wissen:   "Ein Glimberg hat 7 Zacken."
  Aufgabe:  "Wie viele Zacken haben drei Glimberge zusammen?"
  Pruefung: Antwort enthaelt "21" -- kein Ermessen, keine Prueffunktion
            strenger als das Wissen selbst.
  ohne Wissen -> unmoeglich zu erraten, faellt garantiert durch.
  mit Wissen  -> reine Rechnung, erzwingt BENUTZUNG (wer nur "7" wiederkaeut,
                 statt 7*3 zu rechnen, faellt durch -- Nutzungsnachweis).

ECHTER ABRUFWEG (Auflage 1): dieselbe Funktion, die im Betrieb vor jedem
Prompt feuert -- knowledge_recall_hook.query()/keywords()/hits() --,
importiert und unveraendert aufgerufen. Kein Wissen wird in den Prompt
kopiert; die erfundenen Knoten liegen als echte Zeilen in knowledge.db
zwischen dem echten Bestand.

RESTLOS ENTFERNBAR (Auflage 2): alle erfundenen Knoten tragen
project_id='pruefkorpus_v3' und Tag TAG -- delete_nodes() loescht exakt und
nur diese (WHERE project_id=?), FTS raeumt sich per Trigger (schema.sql)
automatisch mit.

KEYWORD-UEBERLAPP IST HIER ABSICHT, nicht Zirkularitaet: anders als v1/v2
(dort ging es um FORMULIERUNGS-Vermeidung bei echten, im Bestand bereits
vorhandenen Lehren/Fakten) ist hier das Wissen selbst erfunden -- es gibt
keine "eigene Formulierung" zu umgehen. Aufgabe und Knotentext teilen
absichtlich Name(+Plural)/Einheit/"zusammen", damit der reale bm25-Kanal
(MIN_HITS=3 verschiedene Substring-Treffer in Pfad+Titel+Summary, siehe
knowledge_recall_hook.hits()) ueberhaupt greifen KANN -- geprueft wird die
Rechnung, nicht die Tarnung der Formulierung.

Laufzeit-Modell: gemma4:e4b (NICHT gemma4:12b -- 140s/Aufruf waere bei
30 Faellen x 2 Aufrufen Stunden lang und stirbt mit dem Zug, Betreiber-
Auflage). Aufgaben/Pruefungen liegen als Daten (CASES) vor, answer() ist
austauschbar -- der Hauptfaden kann die Beantwortung spaeter ueber
Haiku-Subagenten fahren, ohne dieses Modul zu aendern.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parent
HUB = SHARED_KNOWLEDGE.parent
sys.path.insert(0, str(HUB / "scripts"))
sys.path.insert(0, str(SHARED_KNOWLEDGE / "schreibpruefstand"))
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_recall_hook as hook  # noqa: E402 -- echter Abrufweg
import schreiblauf as sl  # noqa: E402 -- _call_with_retry fuer die Eichung/Vollauf

PROJECT_ID = "pruefkorpus_v3"
TAG = "pruefkorpus_v3_erfunden"
CAL_MODEL = "gemma4:e4b"  # schneller als gemma4:12b -- s. Moduldoc
CAL_TIMEOUT = 90.0
BANNED_RESULTS = {0, 1, 2, 10, 100}

OUT_JSON = SHARED_KNOWLEDGE / "runs" / "pruefkorpus_v3.json"

ZAHLWORT = {1: "ein", 2: "zwei", 3: "drei", 4: "vier", 5: "fuenf", 6: "sechs"}

# ---------------------------------------------------------------------------
# Erfundene Gegenstaende -- werden als echte Knoten eingespielt.
# (slug, name, einheit, wert)
GEGENSTAENDE = [
    ("glimberg", "Glimberg", "Zacken", 7),
    ("trebolit", "Trebolit", "Ringe", 9),
    ("fasnerkel", "Fasnerkel", "Noppen", 6),
    ("quandtor", "Quandtor", "Facetten", 11),
    ("bilkrone", "Bilkrone", "Zaehne", 13),
    ("snarwal", "Snarwal", "Kerben", 8),
    ("worbel", "Worbel", "Streben", 12),
    ("kessnitt", "Kessnitt", "Rippen", 14),
    ("dromfeld", "Dromfeld", "Falten", 17),
    ("miglor", "Miglor", "Speichen", 16),
    ("pentrusch", "Pentrusch", "Dornen", 19),
    ("halbsted", "Halbsted", "Kanten", 18),
    ("orbeling", "Orbeling", "Waben", 23),
    ("tuckram", "Tuckram", "Stege", 22),
    # aehnlich benannte Paare (unterscheiden sich im letzten Buchstaben) --
    # pruefen, ob der Abruf den RICHTIGEN zieht statt irgendeinen.
    ("velunit", "Velunit", "Klammern", 21),
    ("velunip", "Velunip", "Klammern", 15),
    ("frastek", "Frastek", "Naehte", 5),
    ("frastel", "Frastel", "Naehte", 24),
]
_G = {slug: (name, einheit, wert) for slug, name, einheit, wert in GEGENSTAENDE}

# Nicht eingespielte Fantasiewoerter fuer die Eichfaelle ohne Wissen.
EICHFALL_WOERTER = [
    ("Fluxnorbel", "Ecken"), ("Krispatur", "Zapfen"), ("Dellwark", "Haken"),
    ("Tangvolk", "Bogen"), ("Orsprint", "Riegel"), ("Halmquin", "Spangen"),
]


def node_text(name: str, einheit: str, wert: int) -> str:
    """Summary/Content eines Knotens -- enthaelt Singular UND Plural(+e) des
    Namens sowie 'zusammen', damit hook.hits() (Substring-Match) bei
    MIN_HITS=3 mit ueblicher Aufgaben-Phrasierung ueberhaupt greifen kann."""
    return (f"Ein {name} hat {wert} {einheit}. Mehrere {name}e zusammen "
            f"ergeben entsprechend mehr {einheit}.")


# ---------------------------------------------------------------------------
# Aufgaben -- Kennung, Kategorie, Aufgabentext, Ziel-Pfade, erwartete Zahl.

def _task_einzelwert(slug: str, anzahl: int) -> tuple[str, int]:
    name, einheit, wert = _G[slug]
    return (f"Wie viele {einheit} haben {ZAHLWORT[anzahl]} {name}e zusammen?", wert * anzahl)


def _task_kombiniert(slug1: str, anzahl1: int, slug2: str, anzahl2: int) -> tuple[str, int]:
    name1, einheit1, wert1 = _G[slug1]
    name2, einheit2, wert2 = _G[slug2]
    task = (f"{ZAHLWORT[anzahl1]} {name1}e haben zusammen wie viele {einheit1}? "
            f"Und {ZAHLWORT[anzahl2]} {name2}e haben zusammen wie viele {einheit2}? "
            f"Nenne die Gesamtsumme aus beiden Werten ({einheit1} der {name1}e plus "
            f"{einheit2} der {name2}e).")
    return task, wert1 * anzahl1 + wert2 * anzahl2


def _task_aehnlich(slug_ziel: str, anzahl: int, slug_ablenker: str) -> tuple[str, int]:
    name, einheit, wert = _G[slug_ziel]
    name_ablenker = _G[slug_ablenker][0]
    task = (f"Wie viele {einheit} haben {ZAHLWORT[anzahl]} {name}e zusammen "
            f"(nicht zu verwechseln mit {name_ablenker})?")
    return task, wert * anzahl


def _task_eichfall(name: str, einheit: str, anzahl: int) -> str:
    return f"Wie viele {einheit} haben {ZAHLWORT[anzahl]} {name} zusammen?"


def build_cases() -> list[dict]:
    cases: list[dict] = []
    n = 0

    def add(kategorie: str, task: str, erwartete_zahl: int | None, ziel_slugs: list[str]):
        nonlocal n
        n += 1
        cases.append({
            "kennung": f"v3-{n:02d}", "kategorie": kategorie, "task": task,
            "erwartete_zahl": erwartete_zahl,
            "ziel_pfade": [f"/{PROJECT_ID}/{s}" for s in ziel_slugs],
        })

    # einfache Rechnung: ein Wert, eine Operation (14 Faelle)
    for slug, anzahl in [
        ("glimberg", 3), ("trebolit", 4), ("fasnerkel", 5), ("quandtor", 3),
        ("bilkrone", 2), ("snarwal", 6), ("worbel", 5), ("kessnitt", 3),
        ("dromfeld", 2), ("miglor", 5), ("pentrusch", 2), ("halbsted", 3),
        ("orbeling", 2), ("tuckram", 3),
    ]:
        task, zahl = _task_einzelwert(slug, anzahl)
        add("einzelwert", task, zahl, [slug])

    # mehrere Werte aus verschiedenen Knoten kombinieren (8 Faelle)
    for slug1, a1, slug2, a2 in [
        ("glimberg", 1, "trebolit", 2), ("fasnerkel", 1, "quandtor", 3),
        ("bilkrone", 1, "snarwal", 4), ("worbel", 1, "kessnitt", 2),
        ("dromfeld", 1, "miglor", 2), ("pentrusch", 1, "halbsted", 2),
        ("orbeling", 1, "tuckram", 2), ("glimberg", 2, "kessnitt", 1),
    ]:
        task, zahl = _task_kombiniert(slug1, a1, slug2, a2)
        add("kombiniert", task, zahl, [slug1, slug2])

    # aehnlich benannte Gegenstaende -- Abruf muss den richtigen ziehen (2 Faelle)
    task, zahl = _task_aehnlich("velunit", 3, "velunip")
    add("aehnlich", task, zahl, ["velunit"])
    task, zahl = _task_aehnlich("frastek", 4, "frastel")
    add("aehnlich", task, zahl, ["frastek"])

    # Eichfaelle ohne passendes Wissen -- richtige Antwort ist "weiss ich nicht" (6 Faelle)
    for (wort, einheit), anzahl in zip(EICHFALL_WOERTER, [2, 3, 4, 2, 3, 4]):
        task = _task_eichfall(wort, einheit, anzahl)
        add("eichfall", task, None, [])

    return cases


CASES = build_cases()


# ---------------------------------------------------------------------------
# DB: einspielen / entfernen (echter Bestand, restlos loeschbar ueber project_id)

def insert_nodes(conn: sqlite3.Connection) -> None:
    for slug, name, einheit, wert in GEGENSTAENDE:
        text = node_text(name, einheit, wert)
        conn.execute(
            "INSERT INTO knowledge_nodes "
            "(id, path, parent_path, project_id, title, summary, content, level, "
            " tags, source, confidence, anlass) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"pk3-{slug}", f"/{PROJECT_ID}/{slug}", None, PROJECT_ID, name, text, text,
             0, json.dumps([TAG]), f"{PROJECT_ID} (erfunden, restlos loeschbar via delete_nodes())",
             0.8, "skript"),
        )
    conn.commit()


def delete_nodes(conn: sqlite3.Connection) -> int:
    """Loeschbefehl (Auflage 2/Abnahme 4): trifft NUR project_id='pruefkorpus_v3'.
    FTS raeumt sich per AFTER-DELETE-Trigger (schema.sql) automatisch mit."""
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM knowledge_nodes WHERE project_id=?", (PROJECT_ID,)).fetchall()]
    if ids:
        placeholders = ",".join("?" * len(ids))
        conn.execute(
            f"DELETE FROM knowledge_embeddings WHERE kind='node' AND ref_id IN ({placeholders})", ids)
    cur = conn.execute("DELETE FROM knowledge_nodes WHERE project_id=?", (PROJECT_ID,))
    conn.commit()
    return cur.rowcount


# ---------------------------------------------------------------------------
# Abruf (echter Weg) + Beantwortung (austauschbar)

def retrieve(task: str) -> tuple[str | None, list]:
    kws = hook.keywords(task)
    if len(kws) < hook.MIN_HITS:
        return None, []
    nodes, lessons = hook.query(kws, cwd=None, prompt=task)
    if not nodes:
        return None, nodes
    context = "\n".join(f"- {n['title']}: {n['summary']}" for n in nodes)
    return context, nodes


def answer(task: str, context: str | None, model: str = CAL_MODEL) -> str:
    """Austauschbar (Docstring-Auflage): spaeter per Haiku-Subagent aufrufbar,
    hier per lokalem Ollama fuer Eichung/Vollauf."""
    if context:
        prompt = (f"Bekanntes Wissen:\n{context}\n\nFrage: {task}\n"
                   "Antworte NUR mit der Zahl, keine Erklaerung. Wenn du sie nicht "
                   "berechnen kannst, antworte 'weiss ich nicht'.")
    else:
        prompt = (f"Frage: {task}\nAntworte NUR mit der Zahl, keine Erklaerung. "
                   "Wenn du sie nicht weisst, antworte 'weiss ich nicht'.")
    raw, err, _retries = sl._call_with_retry(prompt, model=model, base_url=sl.DEFAULT_OLLAMA_URL, timeout=CAL_TIMEOUT)
    return (raw or f"[FEHLER: {err}]").strip()


def check(raw: str, erwartete_zahl: int | None) -> bool:
    if erwartete_zahl is None:
        return str(erwartete_zahl) not in raw  # Platzhalter, siehe run_all() Zeilenausgabe
    return str(erwartete_zahl) in raw


def target_hit(case: dict, nodes: list) -> bool:
    gefunden = {n["path"] for n in nodes}
    return all(p in gefunden for p in case["ziel_pfade"]) if case["ziel_pfade"] else False


# ---------------------------------------------------------------------------
# Eichung (Abnahme 1) + Vollauf (Abnahme 2-4)

def eichung(conn: sqlite3.Connection, model: str = CAL_MODEL) -> dict:
    """EIN Fall (v3-01, Glimberg -- das Entwurfsbeispiel), VOR dem Rest:
    ohne Abruf muss durchfallen, mit Abruf bestehen. Rohe Ausgabe beider Laeufe."""
    case = CASES[0]
    ohne = answer(case["task"], None, model=model)
    context, nodes = retrieve(case["task"])
    mit = answer(case["task"], context, model=model)
    result = {
        "kennung": case["kennung"], "task": case["task"], "erwartete_zahl": case["erwartete_zahl"],
        "ohne_abruf_roh": ohne, "ohne_abruf_bestanden": check(ohne, case["erwartete_zahl"]),
        "mit_abruf_roh": mit, "mit_abruf_bestanden": check(mit, case["erwartete_zahl"]),
        "ziel_gefunden": target_hit(case, nodes),
    }
    ok = (not result["ohne_abruf_bestanden"]) and result["mit_abruf_bestanden"] and result["ziel_gefunden"]
    result["eichung_ok"] = ok
    return result


def run_all(model: str = CAL_MODEL, out_path: Path = OUT_JSON) -> dict:
    conn = sqlite3.connect(hook.DB)
    conn.row_factory = sqlite3.Row
    vorher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    insert_nodes(conn)
    print(f"Bestand vorher: {vorher}. {len(GEGENSTAENDE)} erfundene Knoten eingespielt.", flush=True)

    eich = eichung(conn, model=model)
    print(f"\nEICHUNG {eich['kennung']}  erwartet={eich['erwartete_zahl']}", flush=True)
    print(f"  ohne Abruf: {eich['ohne_abruf_roh']!r}  bestanden={eich['ohne_abruf_bestanden']}", flush=True)
    print(f"  mit  Abruf: {eich['mit_abruf_roh']!r}  bestanden={eich['mit_abruf_bestanden']}  "
          f"ziel_gefunden={eich['ziel_gefunden']}", flush=True)
    if not eich["eichung_ok"]:
        print("\nEICHUNG FEHLGESCHLAGEN -- Entwurf ist falsch, Abbruch VOR Vollauf. "
              "Erfundene Knoten werden trotzdem entfernt.", flush=True)
        n_entfernt = delete_nodes(conn)
        nachher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        conn.close()
        out = {"eichung": eich, "aborted": True, "vorher": vorher, "entfernt": n_entfernt, "nachher": nachher}
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        return out

    print(f"\nEICHUNG OK -- Vollauf ueber {len(CASES)} Faelle:", flush=True)
    rows = [{"kennung": eich["kennung"], "kategorie": CASES[0]["kategorie"],
             "erwartete_zahl": eich["erwartete_zahl"],
             "ohne_abruf": eich["ohne_abruf_roh"], "mit_abruf": eich["mit_abruf_roh"],
             "ohne_bestanden": eich["ohne_abruf_bestanden"], "mit_bestanden": eich["mit_abruf_bestanden"],
             "ziel_gefunden": eich["ziel_gefunden"]}]
    print(f"  {rows[0]['kennung']}  erwartet={rows[0]['erwartete_zahl']}  "
          f"ohne={rows[0]['ohne_abruf']!r}  mit={rows[0]['mit_abruf']!r}", flush=True)

    for case in CASES[1:]:
        context, nodes = retrieve(case["task"])
        ohne = answer(case["task"], None, model=model)
        mit = answer(case["task"], context, model=model)
        row = {
            "kennung": case["kennung"], "kategorie": case["kategorie"],
            "erwartete_zahl": case["erwartete_zahl"], "ohne_abruf": ohne, "mit_abruf": mit,
            "ohne_bestanden": check(ohne, case["erwartete_zahl"]),
            "mit_bestanden": check(mit, case["erwartete_zahl"]),
            "ziel_gefunden": target_hit(case, nodes),
        }
        rows.append(row)
        print(f"  {row['kennung']}  erwartet={row['erwartete_zahl']}  "
              f"ohne={row['ohne_abruf']!r}  mit={row['mit_abruf']!r}", flush=True)

    n_vor_delete = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    n_entfernt = delete_nodes(conn)
    nachher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()
    print(f"\nLoeschbefehl: vorher={n_vor_delete}  entfernt={n_entfernt}  nachher={nachher}  "
          f"(Original-Bestand vor Einspielen war {vorher} -> {'unveraendert' if nachher == vorher else 'ABWEICHUNG!'})",
          flush=True)

    out = {
        "eichung": eich, "aborted": False, "model": model,
        "vorher": vorher, "vor_delete": n_vor_delete, "entfernt": n_entfernt, "nachher": nachher,
        "n_cases": len(CASES), "rows": rows,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGeschrieben: {out_path}", flush=True)
    return out


# ---------------------------------------------------------------------------
# Selbsttest -- netzlos, DB-los: prueft das Korpus-DESIGN, nicht den Abruf live.

def _selftest() -> None:
    assert 30 <= len(CASES) <= 40, f"{len(CASES)} Faelle ausserhalb 30..40"

    kategorien = {}
    for c in CASES:
        kategorien[c["kategorie"]] = kategorien.get(c["kategorie"], 0) + 1
    assert kategorien.get("einzelwert", 0) >= 1
    assert kategorien.get("kombiniert", 0) >= 1
    assert kategorien.get("aehnlich", 0) >= 1
    assert kategorien.get("eichfall", 0) >= 1
    print(f"  Streuung ok: {kategorien}")

    solvable = [c for c in CASES if c["erwartete_zahl"] is not None]
    zahlen = [c["erwartete_zahl"] for c in solvable]
    assert len(zahlen) == len(set(zahlen)), "erwartete Zahlen nicht paarweise verschieden"
    assert not (set(zahlen) & BANNED_RESULTS), f"verbotener trivialer Wert dabei: {set(zahlen) & BANNED_RESULTS}"
    print(f"  {len(zahlen)} loesbare Faelle, alle Ergebnisse paarweise verschieden, keins in {BANNED_RESULTS}")

    eichfaelle = [c for c in CASES if c["kategorie"] == "eichfall"]
    assert all(c["erwartete_zahl"] is None and not c["ziel_pfade"] for c in eichfaelle)
    print(f"  {len(eichfaelle)} Eichfaelle ohne Ziel-Knoten: ok")

    # Kernpruefung: MIN_HITS=3 wird fuer jeden Ziel-Knoten durch die eigene
    # Aufgaben-Phrasierung tatsaechlich erreicht (Substring-Match wie hook.hits()
    # ihn live gegen path+title+summary anwendet) -- rein textuell, keine DB.
    for c in CASES:
        if not c["ziel_pfade"]:
            continue
        kws = hook.keywords(c["task"])
        assert len(kws) >= hook.MIN_HITS, f"{c['kennung']}: zu wenige Keywords ({kws})"
        for slug in [p.rsplit("/", 1)[-1] for p in c["ziel_pfade"]]:
            name, einheit, wert = _G[slug]
            text = f"/{PROJECT_ID}/{slug} {name} {node_text(name, einheit, wert)}"
            n_hits = hook.hits(text, kws)
            assert n_hits >= hook.MIN_HITS, (
                f"{c['kennung']}/{slug}: nur {n_hits} Treffer < MIN_HITS={hook.MIN_HITS} "
                f"(kws={kws})")
    print("  MIN_HITS-Vorbedingung fuer jeden Ziel-Knoten offline bestaetigt (kein DB-Zugriff)")

    # Aehnlich-Faelle: Ablenker-Name darf NICHT als Substring im Zieltext
    # stecken (sonst waere das kein sauberer Unterscheidungstest).
    aehnlich = [c for c in CASES if c["kategorie"] == "aehnlich"]
    assert len(aehnlich) >= 1
    for c in aehnlich:
        ziel_slug = c["ziel_pfade"][0].rsplit("/", 1)[-1]
        name_ziel = _G[ziel_slug][0]
        for slug, name, *_r in GEGENSTAENDE:
            if slug != ziel_slug and name.lower() != name_ziel.lower() and name.lower().startswith(name_ziel.lower()[:6]):
                assert hook.fold_de(name) not in hook.fold_de(name_ziel), \
                    f"{c['kennung']}: Ablenkername {name} steckt im Zielnamen {name_ziel}"
    print(f"  {len(aehnlich)} Aehnlich-Faelle: Ablenkername != Substring des Zielnamens: ok")

    print(f"selftest ok ({len(CASES)} Faelle)", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true", help="netzlos, DB-los")
    ap.add_argument("--eichung-only", action="store_true",
                     help="nur der Eichfall (v3-01), erfundene Knoten danach entfernt")
    ap.add_argument("--model", default=CAL_MODEL)
    ap.add_argument("--delete", action="store_true",
                     help="nur Loeschbefehl vorfuehren (falls Knoten aus vorigem Lauf uebrig sind)")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return

    if args.delete:
        conn = sqlite3.connect(hook.DB)
        vorher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        n = delete_nodes(conn)
        nachher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        conn.close()
        print(f"vorher={vorher}  entfernt={n}  nachher={nachher}")
        return

    if args.eichung_only:
        conn = sqlite3.connect(hook.DB)
        vorher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        insert_nodes(conn)
        eich = eichung(conn, model=args.model)
        print(json.dumps(eich, ensure_ascii=False, indent=2))
        n = delete_nodes(conn)
        nachher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
        conn.close()
        print(f"vorher={vorher}  entfernt={n}  nachher={nachher}")
        return

    run_all(model=args.model)


if __name__ == "__main__":
    main()
