#!/usr/bin/env python3
"""Knowledge-Lint — rein lesende Bestandsprüfung von shared-knowledge/knowledge.db.

Plan docs/PLAN_WISSENSSYSTEM_2026-08-05.md, Maßnahme P6. Ändert nichts,
schreibt nichts in die DB (Verbindung immer mode=ro). Meldet sechs
Kategorien von Befunden -- ein späterer Schritt entscheidet, was damit
geschieht (aufräumen, zusammenführen, neu einbetten). Insbesondere die
Near-Dubletten-Kategorie liefert nur Kandidatenpaare zur Prüfung, nie ein
Urteil "ist dasselbe".

Wiederverwendet statt neu gebaut:
  - fold_de()                      aus knowledge_mcp_server.py
  - SLUG_MAX_LEN                   aus knowledge_mcp_server.py (P1)
  - unpack_embedding()/cosine_similarity() aus embeddings.py
  - das "nie gezogen"-Muster       aus scripts/knowledge_recall_hook.py::report()
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).parent
sys.path.insert(0, str(SHARED_KNOWLEDGE))
sys.path.insert(0, str(SHARED_KNOWLEDGE.parent / "scripts"))

import embeddings  # noqa: E402
from knowledge_mcp_server import fold_de, SLUG_MAX_LEN  # noqa: E402

DB_PATH = SHARED_KNOWLEDGE / "knowledge.db"
RECALL_LOG = SHARED_KNOWLEDGE / "recall_log.jsonl"

STALE_DAYS = 90
NEAR_DUPLICATE_THRESHOLD = 0.90  # gilt fuer Kosinus- UND SequenceMatcher-Score
MAX_SHOWN = 15
_PATH_PUNCT_RE = re.compile(r"[^A-Za-z0-9/\-]")

# nomic-embed-text (embeddings.DEFAULT_EMBED_MODEL) hat ein Kontextfenster
# von 2048 Token und kappt laengeren Text still -- kein Fehler, keine
# Warnung. Gemessen 2026-08-05 (Lehre L-312bd7): ab ~2100 Token Vorlauf
# liefern zwei sich nur am Ende unterscheidende Texte den identischen Vektor.
EMBED_CONTEXT_TOKENS = 2048
# Grobe Schaetzung Zeichen->Token fuer deutschen Text, KEINE echte
# Tokenisierung -- der Lint ruft absichtlich kein Modell/Ollama auf.
CHARS_PER_TOKEN_ESTIMATE = 3.5

# Mittlerer Grad 1 = Riesencluster-Schwelle im Erdos-Renyi-Zufallsgraphen
# G(n,p) (Erdos/Renyi 1960: bei np=1 kippt das Graphenwachstum von vielen
# kleinen Komponenten zu einer dominanten). Gilt beweisbar nur fuer
# Zufallsgraphen -- der Wissensgraph ist keiner (Kanten entstehen gezielt,
# nicht unabhaengig-zufaellig). Die Kennzahl ist eine Groessenordnung zur
# Orientierung, KEINE Vorhersage fuer diesen Graphen.
PERCOLATION_THRESHOLD_AVG_DEGREE = 1


def get_ro_conn(db_path: Path | str) -> sqlite3.Connection:
    """mode=ro -- ein Schreibversuch ueber diese Verbindung scheitert hart
    (sqlite3.OperationalError: attempt to write a readonly database), statt
    sich auf Disziplin im Aufrufer zu verlassen."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)
    conn.row_factory = sqlite3.Row
    return conn


# ─── 1. Waisen ────────────────────────────────────────────────────────────

def find_orphans(conn: sqlite3.Connection) -> list[dict]:
    paths = {r[0] for r in conn.execute("SELECT path FROM knowledge_nodes")}
    out = []
    for r in conn.execute("SELECT path, parent_path FROM knowledge_nodes"):
        pp = r["parent_path"]
        if pp is None or pp == "/":
            continue
        if pp not in paths:
            out.append({"path": r["path"], "parent_path": pp})
    return out


# ─── 2. Karteileichen ───────────────────────────────────────────────────────

def _age_days(ts: str, now: datetime) -> float:
    return (now - datetime.fromisoformat(ts)).total_seconds() / 86400.0


def find_stale(conn: sqlite3.Connection, now: datetime, days: int = STALE_DAYS) -> list[dict]:
    out = []
    for r in conn.execute("SELECT path, updated_at FROM knowledge_nodes"):
        age = _age_days(r["updated_at"], now)
        if age > days:
            out.append({"kind": "node", "ref": r["path"], "updated_at": r["updated_at"],
                        "age_days": round(age, 1)})
    for r in conn.execute("SELECT id, last_seen FROM lessons_learned WHERE status = 'active'"):
        age = _age_days(r["last_seen"], now)
        if age > days:
            out.append({"kind": "lesson", "ref": r["id"], "updated_at": r["last_seen"],
                        "age_days": round(age, 1)})
    return out


# ─── 3. Nie gezogen ─────────────────────────────────────────────────────────

def _recall_hits(log_path: Path | str) -> tuple[set, set]:
    """Gleiches Muster wie knowledge_recall_hook.py::report(): jede Zeile
    traegt die an diesem Abruf beteiligten node-Pfade und lesson-IDs."""
    node_hits: set = set()
    lesson_hits: set = set()
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                node_hits.update(e.get("nodes", []))
                lesson_hits.update(e.get("lessons", []))
    except FileNotFoundError:
        pass
    return node_hits, lesson_hits


def find_never_pulled(conn: sqlite3.Connection, log_path: Path | str = RECALL_LOG) -> dict:
    node_hits, lesson_hits = _recall_hits(log_path)
    all_nodes = {r[0] for r in conn.execute("SELECT path FROM knowledge_nodes")}
    all_lessons = {r[0] for r in conn.execute(
        "SELECT id FROM lessons_learned WHERE status != 'resolved'")}
    return {
        "nodes": sorted(all_nodes - node_hits),
        "lessons": sorted(all_lessons - lesson_hits),
    }


# ─── 4. Vektor fehlt/veraltet ───────────────────────────────────────────────

def find_vector_gaps(conn: sqlite3.Connection) -> list[dict]:
    out = []
    vec_updated = {(r["kind"], r["ref_id"]): r["updated_at"]
                    for r in conn.execute("SELECT kind, ref_id, updated_at FROM knowledge_embeddings")}
    for r in conn.execute("SELECT id, path, updated_at FROM knowledge_nodes"):
        vec_at = vec_updated.get(("node", r["id"]))
        if vec_at is None or vec_at < r["updated_at"]:
            out.append({"kind": "node", "ref": r["path"], "vector": "fehlt" if vec_at is None else "veraltet"})
    for r in conn.execute("SELECT id, last_seen FROM lessons_learned WHERE status = 'active'"):
        vec_at = vec_updated.get(("lesson", r["id"]))
        if vec_at is None or vec_at < r["last_seen"]:
            out.append({"kind": "lesson", "ref": r["id"], "vector": "fehlt" if vec_at is None else "veraltet"})
    return out


# ─── 5. Near-Dubletten unter den Lessons ────────────────────────────────────
# ponytail: O(n^2) Paarvergleich -- bei Hunderten aktiven Lessons in
# Sekunden gerechnet, kein Problem. Ab niedriger vierstelliger Lesson-Zahl
# waere ein Blocking-Schritt (z.B. nur je Typ vergleichen) noetig.

def _is_near_duplicate(score: float, threshold: float = NEAR_DUPLICATE_THRESHOLD) -> bool:
    return score >= threshold


def find_near_duplicate_lessons(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, description FROM lessons_learned WHERE status = 'active'"
    ).fetchall()
    vectors = {r["ref_id"]: embeddings.unpack_embedding(r["vector"])
               for r in conn.execute("SELECT ref_id, vector FROM knowledge_embeddings WHERE kind = 'lesson'")}
    folded = {r["id"]: fold_de(r["description"]) for r in rows}

    out = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            if a["id"] in vectors and b["id"] in vectors:
                score = embeddings.cosine_similarity(vectors[a["id"]], vectors[b["id"]])
                method = "cosine"
            else:
                score = difflib.SequenceMatcher(None, folded[a["id"]], folded[b["id"]]).ratio()
                method = "sequence_matcher"
            if _is_near_duplicate(score):
                out.append({"a": a["id"], "b": b["id"], "score": round(score, 3), "method": method})
    return out


# ─── 6. Pfad-Hygiene ─────────────────────────────────────────────────────────

def find_path_hygiene(conn: sqlite3.Connection) -> list[dict]:
    out = []
    for r in conn.execute("SELECT path FROM knowledge_nodes"):
        path = r["path"]
        problems = []
        if _PATH_PUNCT_RE.search(path):
            problems.append("satzzeichen")
        last_segment = path.rsplit("/", 1)[-1]
        if len(last_segment) == SLUG_MAX_LEN:
            problems.append(f"letztes-segment-genau-{SLUG_MAX_LEN}-zeichen")
        if problems:
            out.append({"path": path, "problems": problems})
    return out


# ─── 7. Einbettung abgeschnitten ─────────────────────────────────────────────
# Text-Zusammensetzung 1:1 aus build_embeddings.py gespiegelt (dort nicht
# geaendert, hier nur nachgemessen) -- sonst zaehlt der Lint etwas anderes
# als das, was tatsaechlich eingebettet wird.

def _estimated_tokens(text: str) -> float:
    return len(text) / CHARS_PER_TOKEN_ESTIMATE


def find_truncated_embeddings(conn: sqlite3.Connection) -> list[dict]:
    out = []
    for r in conn.execute("SELECT path, title, summary, content FROM knowledge_nodes"):
        text = f"{r['path']}\n{r['title']}\n{r['summary']}\n{r['content'] or ''}"
        tokens = _estimated_tokens(text)
        if tokens > EMBED_CONTEXT_TOKENS:
            out.append({"kind": "node", "ref": r["path"],
                        "estimated_tokens": round(tokens),
                        "over_by": round(tokens - EMBED_CONTEXT_TOKENS)})
    for r in conn.execute(
        "SELECT id, node_path, projects, description, root_cause, prevention FROM lessons_learned"
    ):
        zuordnung = r["node_path"] or r["projects"] or ""
        text = f"{zuordnung}\n{r['description']}\n{r['root_cause'] or ''}\n{r['prevention'] or ''}"
        tokens = _estimated_tokens(text)
        if tokens > EMBED_CONTEXT_TOKENS:
            out.append({"kind": "lesson", "ref": r["id"],
                        "estimated_tokens": round(tokens),
                        "over_by": round(tokens - EMBED_CONTEXT_TOKENS)})
    return out


# ─── Struktur-Kennzahlen (kein Befund, Zustand des Bestands als Ganzes) ────
# Getrennt von den sieben Befund-Kategorien oben: keine beanstandet einen
# einzelnen Eintrag, sondern beschreibt eine Verteilung ueber den Bestand.

# ─── K1. Abstand zur Perkolationsschwelle ──────────────────────────────────

def find_percolation_distance(conn: sqlite3.Connection) -> dict:
    """Mittlerer Grad des Querkanten-Graphen (knowledge_relations) --
    Hierarchie-Kanten (parent_path) zaehlen bewusst nicht mit, die sind
    trivial vorhanden und wuerden die Zahl bedeutungslos machen."""
    nodes = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    edges = conn.execute("SELECT COUNT(*) FROM knowledge_relations").fetchone()[0]
    avg_degree = (2 * edges / nodes) if nodes else 0.0
    threshold_edges = nodes / 2
    missing_edges = max(0, round(threshold_edges - edges))
    return {
        "nodes": nodes,
        "cross_edges": edges,
        "avg_degree": round(avg_degree, 3),
        "threshold_avg_degree": PERCOLATION_THRESHOLD_AVG_DEGREE,
        "threshold_edges": round(threshold_edges),
        "missing_edges_to_threshold": missing_edges,
        "caveat": "Schwelle gilt fuer Erdos-Renyi-Zufallsgraphen -- unser "
                  "Graph ist keiner, die Zahl ist eine Groessenordnung, "
                  "keine Vorhersage.",
        "sentence": f"mittlerer Grad {round(avg_degree, 3)}, es fehlen "
                    f"{missing_edges} Querkanten bis zur Schwelle "
                    f"(Groessenordnung, keine Vorhersage -- gilt beweisbar "
                    f"nur fuer Zufallsgraphen)",
    }


# ─── K2. Filamente ──────────────────────────────────────────────────────────

def find_filament_distribution(conn: sqlite3.Connection) -> dict:
    """Verteilung der Lessons nach Anzahl zugeordneter Projekte. Zeilen mit
    kaputtem JSON im projects-Feld werden getrennt gezaehlt, nie still
    uebersprungen -- sonst verschwindet ein Datenschaden in der Statistik."""
    by_count: dict[int, int] = {}
    invalid_ids: list[str] = []
    for r in conn.execute("SELECT id, projects FROM lessons_learned"):
        try:
            arr = json.loads(r["projects"])
            if not isinstance(arr, list):
                raise ValueError("projects-Feld ist kein JSON-Array")
        except (json.JSONDecodeError, ValueError):
            invalid_ids.append(r["id"])
            continue
        by_count[len(arr)] = by_count.get(len(arr), 0) + 1
    cross_project = sum(n for count, n in by_count.items() if count >= 2)
    return {
        "by_project_count": dict(sorted(by_count.items())),
        "cross_project_lessons": cross_project,
        "invalid_json_rows": invalid_ids,
        "invalid_json_count": len(invalid_ids),
    }


# ─── K3. Konfidenz-Alter ────────────────────────────────────────────────────

def find_confidence_default_age(conn: sqlite3.Connection) -> dict:
    """Wie viele Knoten tragen unveraendert den Schema-Vorgabewert der
    confidence-Spalte, wie alt ist der aelteste davon. Vorgabewert aus dem
    Schema gelesen (pragma_table_info), nicht fest eingetragen -- sonst
    zeigt die Kennzahl beim naechsten Schemawechsel Unsinn."""
    default_raw = None
    for r in conn.execute("PRAGMA table_info(knowledge_nodes)"):
        if r["name"] == "confidence":
            default_raw = r["dflt_value"]
            break
    if default_raw is None:
        return {"default_value": None, "count": 0, "oldest_updated_at": None, "oldest_ref": None}
    default_value = float(default_raw)

    rows = conn.execute(
        "SELECT path, updated_at FROM knowledge_nodes WHERE confidence = ?", (default_value,)
    ).fetchall()
    oldest = min(rows, key=lambda r: r["updated_at"], default=None)
    return {
        "default_value": default_value,
        "count": len(rows),
        "oldest_updated_at": oldest["updated_at"] if oldest else None,
        "oldest_ref": oldest["path"] if oldest else None,
    }


def find_structure_metrics(conn: sqlite3.Connection) -> dict:
    return {
        "percolation_distance": find_percolation_distance(conn),
        "filaments": find_filament_distribution(conn),
        "confidence_default_age": find_confidence_default_age(conn),
    }


# ─── Bericht ──────────────────────────────────────────────────────────────

def _print_section(title: str, items: list, formatter=str) -> None:
    print(f"\n{title}: {len(items)}")
    for item in items[:MAX_SHOWN]:
        print(f"  - {formatter(item)}")
    if len(items) > MAX_SHOWN:
        print(f"  ... und {len(items) - MAX_SHOWN} weitere nicht gezeigt")


def run(db_path: Path | str = DB_PATH, log_path: Path | str = RECALL_LOG,
       now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    conn = get_ro_conn(db_path)
    try:
        never_pulled = find_never_pulled(conn, log_path)
        result = {
            "orphans": find_orphans(conn),
            "stale": find_stale(conn, now),
            "never_pulled_nodes": never_pulled["nodes"],
            "never_pulled_lessons": never_pulled["lessons"],
            "vector_gaps": find_vector_gaps(conn),
            "near_duplicate_lessons": find_near_duplicate_lessons(conn),
            "path_hygiene": find_path_hygiene(conn),
            "truncated_embeddings": find_truncated_embeddings(conn),
            "structure_metrics": find_structure_metrics(conn),
        }
    finally:
        conn.close()
    return result


def print_report(result: dict) -> None:
    print("Knowledge-Lint -- rein lesend, nichts geaendert.")
    _print_section("Waisen (parent_path zeigt ins Leere)", result["orphans"],
                   lambda i: f"{i['path']} -> {i['parent_path']}")
    _print_section(f"Karteileichen (> {STALE_DAYS} Tage ohne Aktualisierung)", result["stale"],
                   lambda i: f"[{i['kind']}] {i['ref']} ({i['age_days']} Tage)")
    _print_section("Nie gezogene Knoten", result["never_pulled_nodes"])
    _print_section("Nie gezogene Lessons", result["never_pulled_lessons"])
    _print_section("Vektor fehlt oder veraltet", result["vector_gaps"],
                   lambda i: f"[{i['kind']}] {i['ref']}: {i['vector']}")
    _print_section(f"Near-Dubletten-Kandidaten (Score >= {NEAR_DUPLICATE_THRESHOLD})",
                   result["near_duplicate_lessons"],
                   lambda i: f"{i['a']} ~ {i['b']} ({i['method']}, {i['score']})")
    _print_section("Pfad-Hygiene", result["path_hygiene"],
                   lambda i: f"{i['path']}: {', '.join(i['problems'])}")
    _print_section(f"Einbettung abgeschnitten (geschaetzt > {EMBED_CONTEXT_TOKENS} Token)",
                   result["truncated_embeddings"],
                   lambda i: f"[{i['kind']}] {i['ref']}: ~{i['estimated_tokens']} Token "
                             f"(+{i['over_by']} ueber Grenze)")
    print_structure_metrics(result["structure_metrics"])


def print_structure_metrics(m: dict) -> None:
    print("\nStruktur-Kennzahlen (kein Befund -- Zustand des Bestands als Ganzes):")

    perc = m["percolation_distance"]
    print(f"  K1 Perkolationsabstand: {perc['sentence']}")
    print(f"     Knoten={perc['nodes']}, Querkanten={perc['cross_edges']}, "
          f"Schwelle={perc['threshold_edges']} Kanten")

    fil = m["filaments"]
    verteilung = ", ".join(f"{n} mit {k} Projekt(en)" for k, n in fil["by_project_count"].items())
    print(f"  K2 Filamente: {verteilung}")
    print(f"     projektuebergreifende Lessons (>=2 Projekte): {fil['cross_project_lessons']}")
    if fil["invalid_json_count"]:
        print(f"     kaputtes JSON im projects-Feld: {fil['invalid_json_count']} "
              f"({', '.join(fil['invalid_json_rows'])})")
    else:
        print("     kaputtes JSON im projects-Feld: 0")

    conf = m["confidence_default_age"]
    print(f"  K3 Konfidenz-Alter: {conf['count']} Knoten auf Vorgabewert {conf['default_value']}, "
          f"aeltester: {conf['oldest_ref']} ({conf['oldest_updated_at']})")


# ─── Selftest ─────────────────────────────────────────────────────────────

def _selftest_db(tmp_path: Path, now: datetime) -> Path:
    db_path = tmp_path / "lint_selftest.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)

    fmt = "%Y-%m-%dT%H:%M:%S+00:00"
    fresh = now.strftime(fmt)
    just_under = (now - timedelta(days=STALE_DAYS - 1)).strftime(fmt)
    just_over = (now - timedelta(days=STALE_DAYS + 1)).strftime(fmt)

    conn.executemany(
        "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, level, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        [
            ("n_root", "/shared", None, "shared", "Shared", "Wurzel", 0, fresh),
            ("n_ok_parent", "/shared/kind", "/shared", "shared", "Kind", "Gueltiger Elternpfad", 1, fresh),
            ("n_orphan", "/verwaist/knoten", "/nicht/vorhanden", "shared", "Waise", "Zeigt ins Leere", 1, fresh),
            ("n_stale", "/shared/alt", "/shared", "shared", "Alt", "Karteileiche", 1, just_over),
            ("n_fresh", "/shared/neu", "/shared", "shared", "Neu", "Frischer Eintrag", 1, just_under),
            ("n_bad_path", "/shared/adr-—-(vue),-a", "/shared", "shared", "Satzzeichen", "Pfad-Hygiene", 1, fresh),
            ("n_long_slug", "/shared/" + "a" * SLUG_MAX_LEN, "/shared", "shared", "Lang", "Genau Kappungslaenge", 1, fresh),
            ("n_trunc_under", "/shared/trunc/under", "/shared", "shared", "T", "S", 1, fresh),
            ("n_trunc_over", "/shared/trunc/over", "/shared", "shared", "T", "S", 1, fresh),
        ],
    )
    # K3: ein Knoten mit abweichender Konfidenz -- die anderen neun bleiben
    # auf dem Schema-Vorgabewert (0.8), der ueber pragma_table_info gelesen wird.
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, level, confidence, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        ("n_conf_custom", "/shared/geprueft", "/shared", "shared", "Geprueft", "Abweichende Konfidenz", 1, 1.0, fresh),
    )
    # Grenzwert beidseitig: Gesamttext-Laenge (path+title+summary+content, wie
    # in find_truncated_embeddings zusammengesetzt) knapp unter/ueber der
    # geschaetzten Token-Grenze (5 Token Marge, in Zeichen umgerechnet).
    _margin_chars = round(5 * CHARS_PER_TOKEN_ESTIMATE)
    _boundary_chars = round(EMBED_CONTEXT_TOKENS * CHARS_PER_TOKEN_ESTIMATE)

    def _set_content_for_total_length(node_id: str, path: str, title: str, summary: str, total_chars: int) -> None:
        overhead = len(f"{path}\n{title}\n{summary}\n")
        content = "x" * (total_chars - overhead)
        conn.execute("UPDATE knowledge_nodes SET content = ? WHERE id = ?", (content, node_id))

    _set_content_for_total_length("n_trunc_under", "/shared/trunc/under", "T", "S", _boundary_chars - _margin_chars)
    _set_content_for_total_length("n_trunc_over", "/shared/trunc/over", "T", "S", _boundary_chars + _margin_chars)
    conn.executemany(
        "INSERT INTO lessons_learned (id, type, description, status, first_seen, last_seen) "
        "VALUES (?,?,?,?,?,?)",
        [
            ("L-dup-a", "error", "Der Reconnect nach BLE-Abbruch vergisst die Geraete-Bindung.", "active", fresh, fresh),
            ("L-dup-b", "error", "Der Reconnect nach BLE-Abbruch vergisst die Geraete-Bindung!", "active", fresh, fresh),
            ("L-distinct", "insight", "Slugs duerfen nicht mitten im Wort gekappt werden.", "active", fresh, fresh),
        ],
    )
    # K2: je eine Lesson mit ein-, zwei- und dreifach zugeordneten Projekten,
    # plus eine Zeile mit kaputtem JSON im projects-Feld (kein Array).
    conn.executemany(
        "INSERT INTO lessons_learned (id, type, description, status, projects, first_seen, last_seen) "
        "VALUES (?,?,?,?,?,?,?)",
        [
            ("L-proj-1", "insight", "Ein-Projekt-Lesson.", "active", json.dumps(["fahrtenbuch"]), fresh, fresh),
            ("L-proj-2", "insight", "Zwei-Projekt-Lesson.", "active", json.dumps(["fahrtenbuch", "aka"]), fresh, fresh),
            ("L-proj-3", "insight", "Drei-Projekt-Lesson.", "active", json.dumps(["fahrtenbuch", "aka", "begod"]), fresh, fresh),
            ("L-proj-bad", "insight", "Kaputtes JSON im projects-Feld.", "active", "openlehr", fresh, fresh),
        ],
    )
    conn.commit()
    conn.close()
    return db_path


def selftest() -> None:
    import tempfile

    now = datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td)
        db_path = _selftest_db(tmp_path, now)
        log_path = tmp_path / "recall_log.jsonl"
        log_path.write_text(json.dumps({"nodes": ["/shared/kind"], "lessons": []}) + "\n", encoding="utf-8")

        before_hash = _sha256(db_path)
        result = run(db_path, log_path, now)
        after_hash = _sha256(db_path)
        assert before_hash == after_hash, "selftest: DB wurde durch run() veraendert"

        # 1. Waisen: genau die eine gesetzte Waise, der Kind-Knoten mit
        #    gueltigem Elternpfad NICHT dabei.
        orphan_paths = {o["path"] for o in result["orphans"]}
        assert orphan_paths == {"/verwaist/knoten"}, orphan_paths

        # 2. Karteileichen, Grenzwerte beidseitig.
        stale_refs = {s["ref"] for s in result["stale"]}
        assert "/shared/alt" in stale_refs, "Schwelle+1 Tag haette gemeldet werden muessen"
        assert "/shared/neu" not in stale_refs, "Schwelle-1 Tag haette NICHT gemeldet werden duerfen"
        assert _age_days(now.strftime("%Y-%m-%dT%H:%M:%S+00:00"), now) <= STALE_DAYS  # 0 Tage: kein Befund

        # 3. Nie gezogen: /shared/kind wurde im Log gezogen, alle anderen nicht.
        assert "/shared/kind" not in result["never_pulled_nodes"]
        assert "/verwaist/knoten" in result["never_pulled_nodes"]

        # 4. Vektor fehlt: kein einziger Knoten/keine Lesson hat einen
        #    Embedding-Eintrag in dieser Fixture -> alle gelten als "fehlt".
        gap_refs = {(g["kind"], g["ref"]) for g in result["vector_gaps"]}
        assert ("node", "/shared/kind") in gap_refs
        assert all(g["vector"] == "fehlt" for g in result["vector_gaps"])

        # 5. Near-Dubletten: das Dublettenpaar wird gefunden, das eindeutig
        #    verschiedene Paar nicht.
        dup_pairs = {frozenset((d["a"], d["b"])) for d in result["near_duplicate_lessons"]}
        assert frozenset(("L-dup-a", "L-dup-b")) in dup_pairs, dup_pairs
        assert frozenset(("L-dup-a", "L-distinct")) not in dup_pairs
        assert frozenset(("L-dup-b", "L-distinct")) not in dup_pairs
        # Grenzwerte beidseitig auf der reinen Vergleichsfunktion, nicht ueber
        # zufaellig getroffene Textbeispiele erzwungen.
        assert _is_near_duplicate(NEAR_DUPLICATE_THRESHOLD + 0.001)
        assert not _is_near_duplicate(NEAR_DUPLICATE_THRESHOLD - 0.001)

        # 6. Pfad-Hygiene: Satzzeichen-Pfad und exakt gekappter Slug beide
        #    gemeldet, die sauberen Pfade nicht.
        hygiene_paths = {h["path"] for h in result["path_hygiene"]}
        assert "/shared/adr-—-(vue),-a" in hygiene_paths
        assert "/shared/" + "a" * SLUG_MAX_LEN in hygiene_paths
        assert "/shared/kind" not in hygiene_paths
        assert "/shared" not in hygiene_paths

        # 7. Einbettung abgeschnitten: knapp unter der Grenze nicht gemeldet,
        #    knapp darueber schon. Grenzwert beidseitig auf der reinen
        #    Schaetzfunktion zusaetzlich erzwungen.
        trunc_refs = {t["ref"] for t in result["truncated_embeddings"]}
        assert "/shared/trunc/under" not in trunc_refs, "knapp unter Grenze haette NICHT gemeldet werden duerfen"
        assert "/shared/trunc/over" in trunc_refs, "knapp ueber Grenze haette gemeldet werden muessen"
        over_entry = next(t for t in result["truncated_embeddings"] if t["ref"] == "/shared/trunc/over")
        assert over_entry["over_by"] > 0, over_entry
        assert _estimated_tokens("a" * round((EMBED_CONTEXT_TOKENS - 1) * CHARS_PER_TOKEN_ESTIMATE)) <= EMBED_CONTEXT_TOKENS
        assert _estimated_tokens("a" * round((EMBED_CONTEXT_TOKENS + 1) * CHARS_PER_TOKEN_ESTIMATE)) > EMBED_CONTEXT_TOKENS

        # K1 Gegenprobe A: diese Fixture hat keine Querkanten -> Grad 0,
        # fehlende Kanten bis zur Schwelle = Knoten/2.
        perc = result["structure_metrics"]["percolation_distance"]
        assert perc["cross_edges"] == 0
        assert perc["avg_degree"] == 0.0
        assert perc["missing_edges_to_threshold"] == round(perc["nodes"] / 2)

        # K2 Filamente: 3 Lessons ohne Projekt (Default '[]'), je 1 mit
        # 1/2/3 Projekten, 1 kaputte JSON-Zeile -- alle getrennt gezaehlt.
        fil = result["structure_metrics"]["filaments"]
        assert fil["by_project_count"].get(0) == 3, fil["by_project_count"]
        assert fil["by_project_count"].get(1) == 1, fil["by_project_count"]
        assert fil["by_project_count"].get(2) == 1, fil["by_project_count"]
        assert fil["by_project_count"].get(3) == 1, fil["by_project_count"]
        assert fil["cross_project_lessons"] == 2, "2- und 3-Projekt-Lesson zusammen"
        assert fil["invalid_json_count"] == 1
        assert "L-proj-bad" in fil["invalid_json_rows"]

        # K3 Konfidenz-Alter: 9 Knoten auf dem Schema-Vorgabewert (0.8),
        # der abweichende Knoten (1.0) NICHT mitgezaehlt; aeltester der
        # Vorgabewert-Knoten ist n_stale (just_over-Zeitstempel).
        conf = result["structure_metrics"]["confidence_default_age"]
        assert conf["default_value"] == 0.8, conf["default_value"]
        assert conf["count"] == 9, conf["count"]
        assert conf["oldest_ref"] == "/shared/alt", conf["oldest_ref"]

    # K1 Gegenprobe B: Graph mit bekannter Kantenzahl, unabhaengig von der
    # Hauptfixture -- mittlerer Grad exakt nachgerechnet (4 Knoten, 3
    # Querkanten -> Grad 2*3/4 = 1.5).
    with tempfile.TemporaryDirectory() as td2:
        edge_db = Path(td2) / "percolation_selftest.db"
        conn = sqlite3.connect(str(edge_db))
        conn.executescript((SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8"))
        conn.executemany(
            "INSERT INTO knowledge_nodes (id, path, title, summary) VALUES (?,?,?,?)",
            [(f"e{i}", f"/e/{i}", "T", "S") for i in range(4)],
        )
        conn.executemany(
            "INSERT INTO knowledge_relations (id, source_path, target_path, relation_type) VALUES (?,?,?,?)",
            [
                ("r1", "/e/0", "/e/1", "verwandt"),
                ("r2", "/e/1", "/e/2", "verwandt"),
                ("r3", "/e/2", "/e/3", "verwandt"),
            ],
        )
        conn.commit()
        ro = get_ro_conn(edge_db)
        try:
            perc_known = find_percolation_distance(ro)
        finally:
            ro.close()
        conn.close()
        assert perc_known["nodes"] == 4
        assert perc_known["cross_edges"] == 3
        assert perc_known["avg_degree"] == 1.5, perc_known["avg_degree"]
        assert perc_known["missing_edges_to_threshold"] == 0  # 3 Kanten >= Schwelle 2

    print("selftest: alle Kategorien treffen genau die gesetzten Faelle, DB unveraendert. OK")


def _sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Bericht als JSON statt Text")
    parser.add_argument("--selftest", action="store_true", help="Selbsttest gegen temporaere DB, kein Zugriff auf knowledge.db")
    args = parser.parse_args()

    if args.selftest:
        selftest()
        return

    before_hash = _sha256(DB_PATH) if DB_PATH.exists() else None
    result = run()
    after_hash = _sha256(DB_PATH) if DB_PATH.exists() else None
    unchanged = before_hash == after_hash

    if args.json:
        result["db_sha256_before"] = before_hash
        result["db_sha256_after"] = after_hash
        result["db_unchanged"] = unchanged
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_report(result)
        print(f"\nknowledge.db unveraendert: sha256 vorher={before_hash} nachher={after_hash} "
              f"({'gleich' if unchanged else 'ABWEICHUNG -- SOFORT MELDEN'})")


if __name__ == "__main__":
    main()
