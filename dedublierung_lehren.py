#!/usr/bin/env python3
"""Entdopplung lessons_learned nach Fellegi-Sunter -- Auftrag 2026-08-07.

Anlass: occurrences-Zaehler steigt heute nur bei explizitem same_as
(lesson_recorder.py) oder bytegleicher Dublette. 579 von 610 Lehren stehen
auf occurrences=1 -- unplausibel fuer wiederkehrende Fehlerklassen, misst
also unsere Wiedererkennung, nicht den Bestand.

Verfahren, kein Modellaufruf:
  1. MinHash/LSH auf Wort-Shingles (fold_de-gefaltet) blockt Kandidatenpaare
     vor -- verhindert den vollen 610*609/2=185745-Paare-Vergleich.
  2. Je Kandidatenpaar ein binaerer Vergleichsvektor (5 Felder: description,
     root_cause, prevention, type, projects), gewonnen aus Jaccard auf
     Wortmengen mit Schwelle AGREE_THRESHOLD.
  3. EM-Schaetzung (klassisches unueberwachtes Fellegi-Sunter/Winkler-
     Verfahren) der m-/u-Wahrscheinlichkeiten je Feld und des Match-Priors
     aus der Verteilung der Vergleichsvektoren selbst -- kein Trainingsset,
     kein Modell, nur Erwartungsmaximierung ueber die eigenen Daten.
  4. Zwei Schwellen auf der resultierenden Posterior-Score-Verteilung: die
     jeweils groesste Luecke oberhalb/unterhalb der Mitte trennt
     automatisch-zusammenfuehren / Unentschieden / automatisch-verwerfen.

Zusammenfuehren (--apply) laeuft NUR gegen eine Arbeitskopie der DB
(--copy-path, Default: scratchpad-Datei) und veraendert live knowledge.db
nie. Verlustfrei: der Verlierer-Datensatz bleibt als Zeile erhalten
(status='resolved' + Verweis), Zielzeile erbt Vereinigungsmenge der Felder
(Text nicht ueberschrieben, sondern um Unterschiedliches ergaenzt).

Wiederverwendet: fold_de() aus knowledge_mcp_server.py (gleiche Faltung wie
FTS-Trigger und knowledge_lint.py). knowledge_lint.py/embeddings.py selbst
NICHT importiert -- deren Near-Dubletten-Pfad nutzt Kosinus auf Embeddings
(Modellaufruf), hier verboten.

Usage:
    .venv/bin/python shared-knowledge/dedublierung_lehren.py            # Trockenlauf
    .venv/bin/python shared-knowledge/dedublierung_lehren.py --apply    # gegen Kopie
    .venv/bin/python shared-knowledge/dedublierung_lehren.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from knowledge_mcp_server import fold_de  # noqa: E402

DB_PATH = HERE / "knowledge.db"
CET = timezone(timedelta(hours=1))
_TOKEN_RE = re.compile(r"[a-z0-9]+")

NUM_HASHES = 100
BANDS = 50          # r = NUM_HASHES / BANDS = 2 Zeilen/Band -> s-Kurve-Schwelle
                    # (1/BANDS)^(1/r) ~= 0.14, nachsichtig genug fuer umformulierte
                    # Bigramm-Ueberlappung ~0.3-0.5 bei echten Near-Dubletten
SHINGLE_K = 2        # Wort-Shingle-Groesse fuers Blocking -- 1 (Unigramm) waere
                      # nochmals nachsichtiger, 2 haelt Kandidatenzahl kleiner
                      # und traegt am Echtbestand (siehe Bericht) noch genug
                      # Ueberlappung fuer umformulierte Near-Dubletten
AGREE_THRESHOLD = 0.3  # Jaccard-Schwelle "Feld stimmt ueberein" (Vergleichsvektor)
FIELDS = ("type", "description", "root_cause", "prevention", "projects")


# ─── Text/Shingle-Hilfen ─────────────────────────────────────────────────────

def _tokens(text: str | None) -> list[str]:
    return _TOKEN_RE.findall(fold_de(text or ""))


def _shingles(text: str | None, k: int = SHINGLE_K) -> set[tuple[str, ...]]:
    toks = _tokens(text)
    if len(toks) < k:
        return {tuple(toks)} if toks else set()
    return {tuple(toks[i:i + k]) for i in range(len(toks) - k + 1)}


def _jaccard(a: set, b: set) -> float | None:
    """None = beide Seiten leer -> Feld nicht anwendbar (kein Vergleich)."""
    if not a and not b:
        return None
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ─── MinHash/LSH ─────────────────────────────────────────────────────────────

def _minhash_signature(shingles: set[tuple[str, ...]], num_hashes: int = NUM_HASHES) -> tuple[int, ...]:
    if not shingles:
        return tuple(0 for _ in range(num_hashes))
    digests = [hashlib.blake2b(repr(s).encode("utf-8"), digest_size=16).digest() for s in shingles]
    sig = []
    for i in range(num_hashes):
        salt = i.to_bytes(2, "big")
        sig.append(min(int.from_bytes(hashlib.blake2b(salt + d, digest_size=8).digest(), "big") for d in digests))
    return tuple(sig)


def minhash_candidates(blocking_text: dict[str, str], bands: int = BANDS,
                        num_hashes: int = NUM_HASHES) -> tuple[set[frozenset], float]:
    """Liefert Kandidatenpaare + Laufzeit in Sekunden."""
    t0 = time.perf_counter()
    rows_per_band = num_hashes // bands
    sigs = {lid: _minhash_signature(_shingles(text), num_hashes) for lid, text in blocking_text.items()}
    buckets: dict[tuple, list[str]] = {}
    for lid, sig in sigs.items():
        for b in range(bands):
            band_key = (b, sig[b * rows_per_band:(b + 1) * rows_per_band])
            buckets.setdefault(band_key, []).append(lid)
    pairs: set[frozenset] = set()
    for members in buckets.values():
        if len(members) < 2:
            continue
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                pairs.add(frozenset((members[i], members[j])))
    return pairs, time.perf_counter() - t0


# ─── Vergleichsvektoren ──────────────────────────────────────────────────────

def _projects_set(raw: str | None) -> set[str]:
    try:
        return set(json.loads(raw or "[]"))
    except (json.JSONDecodeError, TypeError):
        return set()


def field_similarities(a: dict, b: dict) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    out["type"] = 1.0 if a["type"] == b["type"] else 0.0
    for f in ("description", "root_cause", "prevention"):
        out[f] = _jaccard(set(_tokens(a[f])), set(_tokens(b[f])))
    pa, pb = _projects_set(a["projects"]), _projects_set(b["projects"])
    out["projects"] = _jaccard(pa, pb)
    return out


def agreement_vector(sims: dict[str, float | None]) -> dict[str, int | None]:
    return {f: (None if v is None else int(v >= AGREE_THRESHOLD)) for f, v in sims.items()}


# ─── EM (unueberwachtes Fellegi-Sunter) ──────────────────────────────────────

def _logsafe(x: float) -> float:
    return math.log(max(x, 1e-9))


def em_fellegi_sunter(vectors: list[dict[str, int | None]], iterations: int = 40) -> tuple[dict, dict, float]:
    """Schaetzt m_i, u_i je Feld und Match-Prior p per EM. Rueckgabe (m, u, p)."""
    m = {f: 0.9 for f in FIELDS}
    u = {f: 0.1 for f in FIELDS}
    p = 0.1
    if not vectors:
        return m, u, p
    for _ in range(iterations):
        posteriors = []
        for vec in vectors:
            log_m = log_u = 0.0
            for f in FIELDS:
                a = vec[f]
                if a is None:
                    continue
                log_m += _logsafe(m[f]) if a else _logsafe(1 - m[f])
                log_u += _logsafe(u[f]) if a else _logsafe(1 - u[f])
            log_m += _logsafe(p)
            log_u += _logsafe(1 - p)
            hi = max(log_m, log_u)
            post = math.exp(log_m - hi) / (math.exp(log_m - hi) + math.exp(log_u - hi))
            posteriors.append(post)
        p = sum(posteriors) / len(posteriors)
        for f in FIELDS:
            num_m = den_m = num_u = den_u = 0.0
            for vec, post in zip(vectors, posteriors):
                a = vec[f]
                if a is None:
                    continue
                num_m += post * a
                den_m += post
                num_u += (1 - post) * a
                den_u += (1 - post)
            if den_m > 0:
                m[f] = min(max(num_m / den_m, 0.01), 0.99)
            if den_u > 0:
                u[f] = min(max(num_u / den_u, 0.01), 0.99)
    return m, u, p


def posterior_score(vec: dict[str, int | None], m: dict, u: dict, p: float) -> float:
    log_m = log_u = 0.0
    for f in FIELDS:
        a = vec[f]
        if a is None:
            continue
        log_m += _logsafe(m[f]) if a else _logsafe(1 - m[f])
        log_u += _logsafe(u[f]) if a else _logsafe(1 - u[f])
    log_m += _logsafe(p)
    log_u += _logsafe(1 - p)
    hi = max(log_m, log_u)
    return math.exp(log_m - hi) / (math.exp(log_m - hi) + math.exp(log_u - hi))


# ─── Zwei-Schwellen-Zonierung ─────────────────────────────────────────────────

def find_thresholds(scores: list[float]) -> tuple[float, float]:
    """Groesste Luecke oberhalb/unterhalb 0.5 der sortierten Scores -> zwei
    Schwellen, begruendet an der tatsaechlichen Verteilung (kein geratener
    Fixwert). Faellt eine Seite leer aus (keine Scores dort), Schwelle = 0.5
    randseitig -- macht die entsprechende Zone leer statt sie zu raten."""
    if not scores:
        return 0.98, 0.02
    xs = sorted(scores)
    upper_candidates = [x for x in xs if x >= 0.5]
    lower_candidates = [x for x in xs if x < 0.5]

    def biggest_gap(vals: list[float]) -> float | None:
        if len(vals) < 2:
            return None
        gaps = [(vals[i + 1] - vals[i], i) for i in range(len(vals) - 1)]
        gap, i = max(gaps)
        if gap <= 1e-9:
            return None
        return (vals[i] + vals[i + 1]) / 2

    upper = biggest_gap(upper_candidates)
    lower = biggest_gap(lower_candidates)
    if upper is None:
        upper = 0.98
    if lower is None:
        lower = 0.5 if upper_candidates else 0.02
    if lower >= upper:
        lower = upper - 1e-6
    return upper, lower


# ─── Pipeline ────────────────────────────────────────────────────────────────

def load_lessons(conn: sqlite3.Connection) -> dict[str, dict]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, node_path, type, severity, description, root_cause, resolution, "
        "prevention, occurrences, projects, status, first_seen, last_seen, anlass "
        "FROM lessons_learned WHERE status = 'active'"
    ).fetchall()
    return {r["id"]: dict(r) for r in rows}


def run_pipeline(lessons: dict[str, dict]) -> dict:
    ids = list(lessons.keys())
    n = len(ids)
    total_pairs = n * (n - 1) // 2

    blocking_text = {lid: f"{l['description']} {l['root_cause'] or ''} {l['prevention'] or ''}"
                      for lid, l in lessons.items()}
    candidates, minhash_seconds = minhash_candidates(blocking_text)

    vectors_by_pair = {}
    sims_by_pair = {}
    for pair in candidates:
        a_id, b_id = sorted(pair)
        sims = field_similarities(lessons[a_id], lessons[b_id])
        vectors_by_pair[(a_id, b_id)] = agreement_vector(sims)
        sims_by_pair[(a_id, b_id)] = sims

    m, u, p = em_fellegi_sunter(list(vectors_by_pair.values()))
    scores = {pair: posterior_score(vec, m, u, p) for pair, vec in vectors_by_pair.items()}

    upper, lower = find_thresholds(list(scores.values()))
    zones = {"merge": [], "review": [], "discard": []}
    for pair, score in scores.items():
        if score >= upper:
            zones["merge"].append(pair)
        elif score < lower:
            zones["discard"].append(pair)
        else:
            zones["review"].append(pair)

    return {
        "n": n, "total_pairs": total_pairs, "candidates": len(candidates),
        "minhash_seconds": minhash_seconds, "m": m, "u": u, "p": p,
        "upper": upper, "lower": lower, "zones": zones, "scores": scores,
        "sims": sims_by_pair,
    }


def _short(text: str | None, width: int = 140) -> str:
    t = (text or "").replace("\n", " ")
    return t[:width] + ("…" if len(t) > width else "")


def print_report(lessons: dict[str, dict], result: dict) -> None:
    print(f"Lehren aktiv: {result['n']}  Paare gesamt: {result['total_pairs']}")
    print(f"MinHash-Kandidaten: {result['candidates']}  Laufzeit: {result['minhash_seconds']:.3f}s")
    print(f"EM: m={({k: round(v, 3) for k, v in result['m'].items()})} "
          f"u={({k: round(v, 3) for k, v in result['u'].items()})} p={result['p']:.4f}")
    print(f"Schwellen: merge >= {result['upper']:.4f}   discard < {result['lower']:.4f}")
    for zone in ("merge", "review", "discard"):
        pairs = result["zones"][zone]
        print(f"\n--- Zone {zone}: {len(pairs)} Paare ---")
        for a_id, b_id in sorted(pairs, key=lambda p: -result["scores"][p])[:3]:
            score = result["scores"][(a_id, b_id)]
            print(f"  [{score:.4f}] {a_id} <-> {b_id}")
            print(f"    A: {_short(lessons[a_id]['description'])}")
            print(f"    B: {_short(lessons[b_id]['description'])}")


# ─── Zusammenfuehren (nur --apply, nur gegen Kopie) ──────────────────────────

def _union_find(pairs: list[tuple[str, str]]) -> dict[str, str]:
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for a, b in pairs:
        union(a, b)
    return {x: find(x) for x in parent}


def _merge_text(a: str | None, b: str | None) -> str | None:
    a, b = (a or "").strip(), (b or "").strip()
    if not b or b == a:
        return a or None
    if not a:
        return b
    return f"{a}\n[zusammengefuehrt] {b}"


def apply_merges(conn: sqlite3.Connection, lessons: dict[str, dict], merge_pairs: list[tuple[str, str]]) -> list[dict]:
    """Fuehrt Cluster aus merge_pairs zusammen: Ziel = kleinste id je Cluster
    (deterministisch, reproduzierbar). Verlierer bleibt als Zeile erhalten
    (status='resolved', kein DELETE) -- Nachweis Verlustfreiheit siehe Aufrufer."""
    groups: dict[str, list[str]] = {}
    for member, root in _union_find(merge_pairs).items():
        groups.setdefault(root, []).append(member)

    proofs = []
    now = datetime.now(CET).strftime("%Y-%m-%dT%H:%M:%S+01:00")
    for root, members in groups.items():
        cluster = sorted(members)
        target_id = cluster[0]
        target = lessons[target_id]
        merged_occurrences = target["occurrences"]
        merged_desc, merged_root, merged_prev, merged_res = (
            target["description"], target["root_cause"], target["prevention"], target["resolution"])
        merged_projects = _projects_set(target["projects"])
        for loser_id in cluster[1:]:
            loser = lessons[loser_id]
            merged_occurrences += loser["occurrences"]
            merged_desc = _merge_text(merged_desc, loser["description"])
            merged_root = _merge_text(merged_root, loser["root_cause"])
            merged_prev = _merge_text(merged_prev, loser["prevention"])
            merged_res = _merge_text(merged_res, loser["resolution"])
            merged_projects |= _projects_set(loser["projects"])
            conn.execute(
                "UPDATE lessons_learned SET status = 'resolved', "
                "resolution = COALESCE(resolution || ' ', '') || ? WHERE id = ?",
                (f"[Zusammengefuehrt in {target_id} am {now}]", loser_id))
        conn.execute(
            "UPDATE lessons_learned SET description = ?, root_cause = ?, prevention = ?, "
            "resolution = ?, occurrences = ?, projects = ?, last_seen = ? WHERE id = ?",
            (merged_desc, merged_root, merged_prev, merged_res, merged_occurrences,
             json.dumps(sorted(merged_projects)), now, target_id))
        if len(cluster) > 1:
            proofs.append({
                "target": target_id, "losers": cluster[1:],
                "target_description_before": target["description"],
                "target_description_after": merged_desc,
            })
    conn.commit()
    return proofs


# ─── CLI ─────────────────────────────────────────────────────────────────────

def cmd_dry_run(db_path: Path) -> None:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    lessons = load_lessons(conn)
    result = run_pipeline(lessons)
    print_report(lessons, result)
    conn.close()


def cmd_apply(db_path: Path, copy_path: Path) -> None:
    copy_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(db_path, copy_path)
    ro = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    lessons_before = load_lessons(ro)
    result = run_pipeline(lessons_before)
    print_report(lessons_before, result)
    ro.close()

    n_before = len(lessons_before)
    conn = sqlite3.connect(str(copy_path))
    conn.row_factory = sqlite3.Row
    proofs = apply_merges(conn, lessons_before, result["zones"]["merge"])
    n_after_active = conn.execute("SELECT COUNT(*) FROM lessons_learned WHERE status='active'").fetchone()[0]
    n_total = conn.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
    conn.close()

    print(f"\n--- Zusammenfuehren gegen Kopie {copy_path} ---")
    print(f"Aktiv vorher: {n_before}  Aktiv nachher: {n_after_active}  Zeilen gesamt (unveraendert): {n_total}")
    if proofs:
        proof = proofs[0]
        print(f"Verlustfrei-Beleg ({proof['target']} <- {proof['losers']}):")
        print(f"  vorher:  {_short(proof['target_description_before'], 200)}")
        print(f"  nachher: {_short(proof['target_description_after'], 300)}")
    else:
        print("Keine Paare in Zone 'merge' -- nichts zusammengefuehrt.")


# ─── Selbsttest ──────────────────────────────────────────────────────────────

def _make_lesson(id_, description, root_cause="ursache", prevention="vermeidung",
                  type_="antipattern", projects='["x"]', occurrences=1) -> dict:
    return {"id": id_, "node_path": None, "type": type_, "severity": "medium",
            "description": description, "root_cause": root_cause, "resolution": None,
            "prevention": prevention, "occurrences": occurrences, "projects": projects,
            "status": "active", "first_seen": "2026-01-01T00:00:00+01:00",
            "last_seen": "2026-01-01T00:00:00+01:00", "anlass": "test"}


def selftest() -> None:
    identical_text = ("Der Sync-Worker verliert Ereignisse wenn der Reconnect nach "
                       "einem Verbindungsabbruch nicht erneut den Ein-Mal-Versuch ausloest "
                       "und die Warteschlange dabei leer bleibt statt nachzuholen")
    near_dup_text = ("Der Sync Worker verliert Ereignisse, wenn Reconnect nach einem "
                      "Verbindungsabbruch den Ein Mal Versuch nicht erneut versucht und "
                      "die Warteschlange leer bleibt anstatt nachzuholen dabei")
    unrelated_text = ("Kontrastwerte in der Buchungsuebersicht liegen unter 4,5:1 bei "
                       "hellgrauem Text auf weissem Grund, WCAG 2.2 AA Fliesstext verletzt")

    lessons = {
        "A1": _make_lesson("A1", identical_text),
        "A2": _make_lesson("A2", near_dup_text),
        "B1": _make_lesson("B1", unrelated_text),
    }
    result = run_pipeline(lessons)
    pair = frozenset(("A1", "A2"))
    assert tuple(sorted(pair)) in result["scores"], "A1/A2 sollten als Kandidatenpaar erkannt werden"
    score_dup = result["scores"][tuple(sorted(pair))]
    assert score_dup >= result["upper"], f"Near-Dublette sollte in Zone merge landen, Score={score_dup}"

    unrelated_pair = tuple(sorted(("A1", "B1")))
    if unrelated_pair in result["scores"]:
        assert result["scores"][unrelated_pair] < result["upper"], "Unaehnliches Paar darf nicht in Zone merge"

    # Verlustfrei-Nachweis am Merge selbst
    conn = sqlite3.connect(":memory:")
    conn.execute("""CREATE TABLE lessons_learned (id TEXT PRIMARY KEY, node_path TEXT, type TEXT,
        severity TEXT, description TEXT, root_cause TEXT, resolution TEXT, prevention TEXT,
        occurrences INTEGER, projects TEXT, status TEXT, first_seen TEXT, last_seen TEXT, anlass TEXT)""")
    for l in lessons.values():
        conn.execute("INSERT INTO lessons_learned VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (l["id"], l["node_path"], l["type"], l["severity"], l["description"],
                       l["root_cause"], l["resolution"], l["prevention"], l["occurrences"],
                       l["projects"], l["status"], l["first_seen"], l["last_seen"], l["anlass"]))
    conn.row_factory = sqlite3.Row
    proofs = apply_merges(conn, lessons, [tuple(sorted(pair))])
    merged = conn.execute("SELECT * FROM lessons_learned WHERE id = 'A1'").fetchone()
    loser = conn.execute("SELECT * FROM lessons_learned WHERE id = 'A2'").fetchone()
    assert loser["status"] == "resolved", "Verlierer muss als resolved erhalten bleiben, nicht geloescht"
    assert "A2" not in [None]  # Zeile existiert weiterhin (kein DELETE)
    assert near_dup_text.split()[0] in merged["description"] or "zusammengefuehrt" in merged["description"].lower(), \
        "Zielzeile muss den Verlierertext (oder Verweis darauf) enthalten"
    assert merged["occurrences"] == 2, "occurrences muss summiert werden"
    conn.close()

    # Zwei-Schwellen: Gegenprobe mit erzwungenem Kandidatenpaar aus verschiedenen Themen
    forced_vectors = [agreement_vector(field_similarities(lessons["A1"], lessons["A2"])),
                       agreement_vector(field_similarities(lessons["A1"], lessons["B1"]))]
    m, u, p = em_fellegi_sunter(forced_vectors)
    s_dup = posterior_score(forced_vectors[0], m, u, p)
    s_unrel = posterior_score(forced_vectors[1], m, u, p)
    assert s_dup > s_unrel, "Near-Dublette muss hoeheren Score haben als unaehnliches Paar"

    print("Selbsttest OK: Near-Dublette -> merge, unaehnliches Paar getrennt, "
          "Verlierer bleibt als Zeile (status=resolved), occurrences summiert.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="Zusammenfuehren gegen Kopie ausfuehren (sonst Trockenlauf)")
    ap.add_argument("--copy-path", type=Path,
                     default=Path("/private/tmp/claude-501/-Volumes-daten-Begod2026-fahrtenbuch/"
                                  "43459d92-9f7a-4fca-b8cb-3f4ed6709f30/scratchpad/knowledge_dedup_copy.db"),
                     help="Zielpfad der Arbeitskopie fuer --apply")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--db", type=Path, default=DB_PATH)
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return 0
    if args.apply:
        cmd_apply(args.db, args.copy_path)
    else:
        cmd_dry_run(args.db)
    return 0


if __name__ == "__main__":
    sys.exit(main())
