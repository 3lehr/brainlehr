#!/usr/bin/env python3
"""Hebbsche Kanten: recall_log.jsonl -> knowledge_relations.

Zwei Knoten, die wiederholt im selben Recall-Abruf gemeinsam auftauchen,
bekommen eine abgeleitete Kante (relation_type=analogous_to, source="hebb_kanten.py").
Ein einmaliges Zusammentreffen ist blosse Stichwortueberschneidung (BM25 zieht
beide fuer dieselben Woerter); erst ein wiederholtes Zusammentreffen ueber
verschiedene Abrufe hinweg ist ein Hinweis auf Verwandtschaft -- daher
Schwelle 2, nicht 1.

Schreibt ausschliesslich ueber knowledge_mcp_server.knowledge_relation_add()
(Wissensvertrag: kein direktes INSERT). Kanten zwischen/mit Lessons entfallen:
knowledge_relations hat FOREIGN KEY auf knowledge_nodes.path fuer beide Enden
(schema.sql:152-153), lessons_learned ist kein gueltiges Ende.

Nutzung:
    python3 hebb_kanten.py --dry-run          # Vorgabe, schreibt nichts
    python3 hebb_kanten.py --apply            # schreibt, legt vorher Sicherung an
    python3 hebb_kanten.py --schwelle 3 --dry-run
    python3 hebb_kanten.py --selftest
"""
from __future__ import annotations

import argparse
import itertools
import json
import shutil
import sqlite3
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import knowledge_mcp_server as kms  # nur ueber diese Funktion schreiben

HERE = Path(__file__).parent
RECALL_LOG = HERE / "recall_log.jsonl"
CET = timezone(timedelta(hours=1))

# Schwelle: 1 gemeinsamer Abruf = geteilte BM25-Suchworte, kein Hinweis.
# Ab 2 verschiedenen Abrufen ist es ein wiederholtes Muster -> Kante.
SCHWELLE_DEFAULT = 2

RELATION_TYPE = "analogous_to"  # naechstliegender Typ fuer eine unbelegte, undirektionale Assoziation
SOURCE_TAG = "hebb_kanten.py"    # macht die Kante als abgeleitet erkennbar (Feld "source" in knowledge_relations)


def _backup(db_path: Path) -> Path:
    stamp = datetime.now(CET).strftime("%Y%m%dT%H%M%S")
    dest = db_path.parent / f"knowledge.db.bak-{stamp}"
    shutil.copy2(db_path, dest)
    return dest


def paar_zaehlung(log_path: Path) -> tuple[Counter, Counter, int]:
    """Zaehlt je Paar (ueber Knoten UND Lessons gemeinsam, wie im Protokoll),
    ueber wie viele Abrufe (Zeilen) es gemeinsam auftrat.

    Ein Paar zaehlt pro Zeile hoechstens einmal, auch wenn 3+ Eintraege in
    derselben Zeile stehen (sonst wuerden grosse Abrufe ueberproportional
    gewichten). Getrennt zurueckgegeben: reine Knoten-Knoten-Paare (koennen
    zu Kanten werden) und Paare, an denen mindestens eine Lesson beteiligt
    ist (schema-bedingt nie eine Kante, siehe Modulkommentar).

    Gibt (knoten_paare, lesson_beteiligte_paare, Zeilenzahl) zurueck.
    """
    knoten_paare: Counter = Counter()
    lesson_paare: Counter = Counter()
    zeilen = 0
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            zeilen += 1
            eintrag = json.loads(line)
            nodes = set(eintrag.get("nodes") or [])
            lessons = set(eintrag.get("lessons") or [])
            for a, b in itertools.combinations(sorted(nodes | lessons), 2):
                if a in lessons or b in lessons:
                    lesson_paare[(a, b)] += 1
                else:
                    knoten_paare[(a, b)] += 1
    return knoten_paare, lesson_paare, zeilen


def existierende_pfade(conn: sqlite3.Connection) -> set[str]:
    return {row[0] for row in conn.execute("SELECT path FROM knowledge_nodes")}


def bestehende_kanten(conn: sqlite3.Connection) -> set[tuple[str, str]]:
    rows = conn.execute(
        "SELECT source_path, target_path FROM knowledge_relations WHERE relation_type=? AND source=?",
        (RELATION_TYPE, SOURCE_TAG),
    ).fetchall()
    return {(r[0], r[1]) for r in rows}


def plane(zaehler: Counter, schwelle: int, gueltige_pfade: set[str],
          vorhandene_kanten: set[tuple[str, str]]) -> tuple[list[tuple[str, str, int]], int]:
    """Liefert (anzulegende Kanten [a,b,gewicht], Zahl uebersprungener Paare wegen fehlendem Knoten)."""
    anzulegen = []
    uebersprungen_fehlend = 0
    for (a, b), n in zaehler.items():
        if n < schwelle:
            continue
        if a not in gueltige_pfade or b not in gueltige_pfade:
            uebersprungen_fehlend += 1
            continue
        if (a, b) in vorhandene_kanten or (b, a) in vorhandene_kanten:
            continue
        anzulegen.append((a, b, n))
    return anzulegen, uebersprungen_fehlend


def wende_an(conn: sqlite3.Connection, kanten: list[tuple[str, str, int]]) -> int:
    angelegt = 0
    for a, b, n in kanten:
        kms.knowledge_relation_add(
            source_node=a, target_node=b, relation_type=RELATION_TYPE,
            confidence=0.5,  # abgeleitet, nicht belegt -- bewusst unter dem Default 0.8
            weight=float(n),
            evidence=f"{n} gemeinsame Abrufe in recall_log.jsonl (Schwelle-Muster, kein Einzelfund)",
            source=SOURCE_TAG,
            creator=SOURCE_TAG,
        )
        angelegt += 1
    return angelegt


def bericht(knoten_paare: Counter, lesson_paare: Counter, zeilen: int, schwelle: int,
            kanten: list[tuple[str, str, int]], uebersprungen: int) -> None:
    gesamt = Counter(knoten_paare)
    gesamt.update(lesson_paare)
    print(f"recall_log.jsonl: {zeilen} Zeilen, {len(gesamt)} verschiedene Ko-Abruf-Paare insgesamt "
          f"(Knoten+Lessons zusammen, wie im Protokoll)")
    for s in (1, 2):
        n = sum(1 for c in gesamt.values() if c >= s)
        print(f"  Paare mit >= {s} gemeinsamen Abrufen: {n}")
    print(f"  davon reine Knoten-Knoten-Paare (einzige moegliche Kanten): "
          f"{len(knoten_paare)} insgesamt, {sum(1 for c in knoten_paare.values() if c >= schwelle)} ab Schwelle {schwelle}")
    print(f"  davon Paare mit Lesson-Beteiligung (nie eine Kante -- knowledge_relations.source_path/"
          f"target_path referenziert nur knowledge_nodes, siehe schema.sql): {len(lesson_paare)}")
    print(f"Schwelle={schwelle} -> {len(kanten)} anzulegende Kanten (neu, nicht bereits vorhanden)")
    print(f"  uebersprungen (Knoten-Knoten-Paar ab Schwelle, aber ein Pfad existiert nicht mehr): {uebersprungen}")


def lauf(log_path: Path, db_path: Path, schwelle: int, apply: bool) -> dict:
    knoten_paare, lesson_paare, zeilen = paar_zaehlung(log_path)
    conn = sqlite3.connect(str(db_path))
    gueltige_pfade = existierende_pfade(conn)
    vorhandene = bestehende_kanten(conn)
    kanten, uebersprungen = plane(knoten_paare, schwelle, gueltige_pfade, vorhandene)
    bericht(knoten_paare, lesson_paare, zeilen, schwelle, kanten, uebersprungen)

    if not apply:
        conn.close()
        print("(--dry-run, nichts geschrieben. --apply zum Schreiben.)")
        return {"geplant": len(kanten), "uebersprungen": uebersprungen}

    conn.close()  # kms.knowledge_relation_add oeffnet seine eigene Verbindung
    sicherung = _backup(db_path)
    print(f"Sicherung: {sicherung}")
    angelegt = wende_an(sqlite3.connect(str(db_path)), kanten)
    print(f"Angelegt: {angelegt} Kanten.")
    return {"angelegt": angelegt, "sicherung": str(sicherung)}


# ─── Selbsttest ──────────────────────────────────────────────────────────

def _selftest() -> int:
    tmp_dir = Path(tempfile.mkdtemp(prefix="hebb_selftest_"))
    db_path = tmp_dir / "knowledge.db"
    log_path = tmp_dir / "recall_log.jsonl"

    conn = sqlite3.connect(str(db_path))
    conn.executescript(Path(HERE / "schema.sql").read_text(encoding="utf-8"))
    now = datetime.now(CET).strftime("%Y-%m-%dT%H:%M:%S+01:00")
    knoten = ["/a", "/b", "/c", "/d"]
    for i, p in enumerate(knoten):
        conn.execute(
            "INSERT INTO knowledge_nodes (id,path,title,summary,created_at,updated_at) VALUES (?,?,?,?,?,?)",
            (f"N-{i}", p, p, "Test", now, now),
        )
    conn.commit()
    conn.close()

    # Faelle:
    # /a-/b: 1x gemeinsam -> darf NICHT angelegt werden
    # /b-/c: 2x gemeinsam -> muss angelegt werden
    # /c-/d: 3x gemeinsam -> muss angelegt werden, hoeheres Gewicht
    # /a-/fehlt: nicht-existenter Knoten -> uebersprungen, gezaehlt
    # /a-/a (Selbstpaar, gleicher Pfad zweimal in einer Zeile) -> nie (combinations auf set liefert kein Selbstpaar)
    zeilen = [
        {"nodes": ["/a", "/b"], "lessons": []},
        {"nodes": ["/b", "/c"], "lessons": []},
        {"nodes": ["/b", "/c"], "lessons": []},
        {"nodes": ["/c", "/d"], "lessons": []},
        {"nodes": ["/c", "/d"], "lessons": []},
        {"nodes": ["/c", "/d"], "lessons": []},
        {"nodes": ["/a", "/fehlt-nicht-vorhanden"], "lessons": []},
        {"nodes": ["/a", "/fehlt-nicht-vorhanden"], "lessons": []},  # 2x, sonst faellt Paar schon an der Schwelle raus
        {"nodes": ["/a", "/a"], "lessons": []},  # Selbstpaar in einer Zeile
        {"nodes": [], "lessons": ["L-1", "L-2"]},  # Lesson-Paar, muss uebersprungen werden
    ]
    with open(log_path, "w", encoding="utf-8") as f:
        for z in zeilen:
            f.write(json.dumps(z) + "\n")

    kms.DB_PATH = db_path  # knowledge_relation_add nutzt kms.get_db() -> DB_PATH

    ok = True

    def check(bedingung: bool, text: str) -> None:
        nonlocal ok
        status = "OK" if bedingung else "FEHLER"
        print(f"  [{status}] {text}")
        if not bedingung:
            ok = False

    # Lauf 1: dry-run darf nichts schreiben
    ergebnis = lauf(log_path, db_path, SCHWELLE_DEFAULT, apply=False)
    conn = sqlite3.connect(str(db_path))
    n_vor = conn.execute("SELECT COUNT(*) FROM knowledge_relations").fetchone()[0]
    conn.close()
    check(n_vor == 0, "dry-run schreibt nichts")
    check(ergebnis["geplant"] == 2, f"2 Kanten geplant (b-c, c-d), war {ergebnis['geplant']}")
    check(ergebnis["uebersprungen"] == 1, f"1 Paar wegen fehlendem Knoten uebersprungen, war {ergebnis['uebersprungen']}")

    # Lauf 2: apply
    ergebnis2 = lauf(log_path, db_path, SCHWELLE_DEFAULT, apply=True)
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        "SELECT source_path,target_path,weight FROM knowledge_relations ORDER BY source_path"
    ).fetchall()
    conn.close()
    check(len(rows) == 2, f"2 Kanten in DB nach apply, war {len(rows)}")
    gewicht_bc = next((r[2] for r in rows if {r[0], r[1]} == {"/b", "/c"}), None)
    gewicht_cd = next((r[2] for r in rows if {r[0], r[1]} == {"/c", "/d"}), None)
    check(gewicht_bc == 2.0, f"/b-/c Gewicht 2, war {gewicht_bc}")
    check(gewicht_cd == 3.0, f"/c-/d Gewicht 3 (haeufiger), war {gewicht_cd}")
    check(not any({r[0], r[1]} == {"/a", "/b"} for r in rows), "/a-/b (nur 1x) wurde NICHT angelegt")

    # Lauf 3: zweiter apply-Lauf legt nichts doppelt an
    lauf(log_path, db_path, SCHWELLE_DEFAULT, apply=True)
    conn = sqlite3.connect(str(db_path))
    n_nach = conn.execute("SELECT COUNT(*) FROM knowledge_relations").fetchone()[0]
    conn.close()
    check(n_nach == 2, f"zweiter apply-Lauf idempotent, weiter 2 Kanten, war {n_nach}")

    shutil.rmtree(tmp_dir, ignore_errors=True)
    print("SELFTEST " + ("BESTANDEN" if ok else "FEHLGESCHLAGEN"))
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--schwelle", type=int, default=SCHWELLE_DEFAULT,
                   help=f"Mindestzahl gemeinsamer Abrufe (Vorgabe {SCHWELLE_DEFAULT})")
    p.add_argument("--apply", action="store_true", help="Schreibt Kanten (Vorgabe: nur --dry-run)")
    p.add_argument("--dry-run", action="store_true", help="Nur planen, nichts schreiben (Vorgabe)")
    p.add_argument("--selftest", action="store_true", help="Selbsttest mit temporaerer DB/Log")
    p.add_argument("--log", type=Path, default=RECALL_LOG)
    p.add_argument("--db", type=Path, default=kms.DB_PATH)
    args = p.parse_args()

    if args.selftest:
        return _selftest()

    apply = args.apply and not args.dry_run
    if not args.db.exists():
        print(f"FEHLER: {args.db} nicht gefunden.")
        return 1
    if not args.log.exists():
        print(f"FEHLER: {args.log} nicht gefunden.")
        return 1

    lauf(args.log, args.db, args.schwelle, apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
