#!/usr/bin/env python3
"""
Knowledge MCP Server — Shared Knowledge Database Access for AI Agents.

Erstellt: 2026-03-25T16:30:00+01:00
Transport: stdio (JSON-RPC 2.0)
DB: SQLite + FTS5 Baumstruktur

Tools:
  - knowledge_browse(path)        → Kinder-Knoten (nur Titel+Summary)
  - knowledge_read(node_id)       → Volltext eines Knotens
  - knowledge_search(query, scope)→ Hybrid-Suche (FTS5 + optional lokale Embeddings, RRF-fusioniert), gibt Summaries zurück
  - knowledge_add(parent_path, title, summary, content, project_id, tags)
  - knowledge_update(node_id, summary, content)
  - lesson_record(type, description, root_cause, resolution, prevention, severity, projects, same_as)
  - lesson_update(lesson_id, description, root_cause, resolution, prevention, severity, projects, status, delete)
  - lesson_query(type, project, status)
  - knowledge_stats()             → Übersichts-Statistiken
"""

import json
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import embeddings  # lokale Embeddings + RRF-Fusion, siehe embeddings.py

DB_PATH = Path(__file__).parent / "knowledge.db"
CET = timezone(timedelta(hours=1))


def now_iso() -> str:
    return datetime.now(CET).strftime("%Y-%m-%dT%H:%M:%S+01:00")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def log_access(conn: sqlite3.Connection, node_path: str | None, action: str,
               query: str | None = None, project_id: str | None = None):
    conn.execute(
        "INSERT INTO access_log (node_path, action, query, project_id, timestamp) VALUES (?,?,?,?,?)",
        (node_path, action, query, project_id, now_iso())
    )
    conn.commit()


# ─── MCP Tool Implementations ────────────────────────────────────────────

def knowledge_browse(path: str = "/", project_filter: str | None = None) -> dict:
    """Browse children of a knowledge tree node. Returns titles and summaries only (token-efficient)."""
    conn = get_db()
    log_access(conn, path, "browse", project_id=project_filter)

    if path == "/":
        query = "SELECT id, path, title, summary, project_id, level, access_count FROM knowledge_nodes WHERE level = 0 ORDER BY path"
        params: tuple = ()
    else:
        normalized = path.rstrip("/")
        query = "SELECT id, path, title, summary, project_id, level, access_count FROM knowledge_nodes WHERE parent_path = ? ORDER BY path"
        params = (normalized,)

    if project_filter:
        query = query.replace("ORDER BY", f"AND project_id IN ('shared', ?) ORDER BY")
        params = (*params, project_filter)

    rows = conn.execute(query, params).fetchall()
    children_count_q = "SELECT COUNT(*) FROM knowledge_nodes WHERE parent_path = ?"

    results = []
    for r in rows:
        child_count = conn.execute(children_count_q, (r["path"],)).fetchone()[0]
        results.append({
            "id": r["id"],
            "path": r["path"],
            "title": r["title"],
            "summary": r["summary"],
            "project": r["project_id"],
            "has_children": child_count > 0,
            "children_count": child_count
        })

    conn.close()
    return {"path": path, "children": results, "count": len(results)}


def knowledge_read(node_id: str) -> dict:
    """Read full content of a knowledge node. Use browse first to find the right node."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM knowledge_nodes WHERE id = ? OR path = ?",
        (node_id, node_id)
    ).fetchone()
    if not row:
        conn.close()
        return {"error": f"Node not found: {node_id}"}

    conn.execute("UPDATE knowledge_nodes SET access_count = access_count + 1 WHERE id = ?", (row["id"],))
    log_access(conn, row["path"], "read")
    conn.commit()

    result = {
        "id": row["id"],
        "path": row["path"],
        "title": row["title"],
        "summary": row["summary"],
        "content": row["content"] or "(kein Volltext)",
        "project": row["project_id"],
        "tags": json.loads(row["tags"]) if row["tags"] else [],
        "source": row["source"],
        "confidence": row["confidence"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"]
    }
    conn.close()
    return result


def _embedding_ranking(conn: sqlite3.Connection, kind: str, query_vec: list[float],
                        allowed_ids: set | None) -> list[str]:
    """Cosine-Ranking ueber die additive knowledge_embeddings-Tabelle. Fehlt die
    Tabelle (aeltere DB-Kopie ohne AP "Wissenssuche nach Bedeutung"), liefert
    leere Liste statt zu werfen -- Aufrufer faellt dann automatisch auf reines
    FTS5/LIKE-Matching zurueck."""
    try:
        rows = conn.execute(
            "SELECT ref_id, vector FROM knowledge_embeddings WHERE kind = ?", (kind,)
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    scored = []
    for r in rows:
        if allowed_ids is not None and r["ref_id"] not in allowed_ids:
            continue
        vec = embeddings.unpack_embedding(r["vector"])
        scored.append((embeddings.cosine_similarity(query_vec, vec), r["ref_id"]))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [ref_id for _, ref_id in scored]


def _fuse_with_keyword_floor(keyword_ordered_ids: list, embedding_ordered_ids: list,
                              max_results: int) -> list:
    """RRF-Fusion, aber mit garantiertem Stichwort-Sockel: jede der Top-
    max_results Stichworttreffer-IDs bleibt im Ergebnis, egal wie das
    Embedding-Ranking ausfaellt (Abnahme-Kriterium "kein Stichworttreffer geht
    verloren"). Ohne Embedding-Treffer (leere Liste, z.B. Ollama nicht
    erreichbar oder Tabelle fehlt) reproduziert das exakt die bisherige
    Stichwort-Reihenfolge, da dict.fromkeys() den Sockel unveraendert vorn
    haelt und `fused` in diesem Fall ohnehin identisch mit
    keyword_ordered_ids ist."""
    weight = embeddings.hybrid_retrieval_weight()
    fused = embeddings.rrf_fuse(keyword_ordered_ids, embedding_ordered_ids, embedding_weight=weight)
    floor = keyword_ordered_ids[:max_results]
    return list(dict.fromkeys(floor + fused))[:max(max_results, len(floor))]


# Deutsche Umlaut-Faltung: ae/oe/ue/ss-Schreibung UND ä/ö/ü/ß treffen sich.
# Dieselbe Abbildung wie der SQL-Ausdruck in schema.sql (Trigger
# knowledge_ai/ad/au) -- SQLite-Trigger koennen keine Python-Funktion
# aufrufen, ohne sie auf jeder schreibenden Verbindung zu registrieren
# (migrate_knowledge.py/build_embeddings.py/_add_phase2_nodes.py oeffnen die
# DB roh, ohne durch dieses Modul zu gehen), darum zwei Implementierungen.
# Gleichheit ist von
# tests/test_knowledge_hybrid_search.py::test_fold_de_matches_sql_fold belegt.
_FOLD_TABLE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def fold_de(text: str) -> str:
    """'Gründer' und 'Gruender' werden beide zu 'gruender'."""
    return text.lower().translate(_FOLD_TABLE)


_QUERY_WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüß0-9]+")


def _fts_phrase(word: str) -> str:
    """Ein Wort als FTS5-Phrase quoten (Anfuehrungszeichen verdoppelt escaped) --
    verhindert, dass ein Wort wie 'NOT' oder ein Bindestrich als FTS5-Operator
    statt als Suchtext interpretiert wird."""
    return '"' + word.replace('"', '""') + '"'


def _or_query(query: str) -> str:
    """Baut aus einer Anfrage eine FTS5-ODER-Verknuepfung ueber die einzelnen,
    gefalteten Woerter. Vorher lief MATCH mit mehreren Woertern als implizites
    UND -- ein einziges Wort, das nirgends vorkommt, killte die ganze Anfrage
    (gemessen: 4 von 6 Anfragen 0 Treffer trotz vorhandenem Knoten). Bei OR
    sortiert bm25/rank Dokumente mit mehr uebereinstimmenden Woertern weiter
    oben ein -- kein zusaetzliches Ranking noetig."""
    words = [fold_de(w) for w in _QUERY_WORD_RE.findall(query)]
    return " OR ".join(_fts_phrase(w) for w in words if w)


ZERO_HIT_LOG = Path(__file__).parent / "zero_hit_log.jsonl"
ZERO_HIT_LOG_MAX_BYTES = 200_000  # klein halten, gleiche Kappung wie recall_log.jsonl


def _log_zero_hit(query: str) -> None:
    """Haelt fest, welche Suchanfragen nichts fanden: Zeitpunkt, Anfragetext,
    Trefferzahl (=0) -- mehr nicht. Grundlage fuer eine spaetere, an echten
    Ausfaellen gemessene Entscheidung ueber Synonyme, statt das zu vermuten.
    Nie ein Grund, die Suche scheitern zu lassen -- Fehler werden verschluckt,
    wie beim analogen Recall-Log (knowledge_recall_hook.py::log_recall)."""
    try:
        entry = json.dumps({"ts": now_iso(), "query": query, "hits": 0}, ensure_ascii=False)
        if ZERO_HIT_LOG.exists() and ZERO_HIT_LOG.stat().st_size > ZERO_HIT_LOG_MAX_BYTES:
            lines = ZERO_HIT_LOG.read_text(encoding="utf-8").splitlines(keepends=True)
            ZERO_HIT_LOG.write_text("".join(lines[len(lines) // 2:]), encoding="utf-8")
        with ZERO_HIT_LOG.open("a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:
        pass


def knowledge_search(query: str, scope: str = "all", max_results: int = 10) -> dict:
    """Hybrid-Suche ueber Wissensknoten: FTS5-Stichwortmatching (Woerter ODER-
    verknuepft, deutsch gefaltet) plus optionale Bedeutungs-Suche ueber lokale
    Embeddings (RRF-fusioniert). Ohne Vektoren (Tabelle fehlt oder leer) oder
    ohne erreichbares Ollama identisch zum reinen FTS5-Verhalten. Returns
    summaries (not full content) for token efficiency."""
    conn = get_db()
    log_access(conn, None, "search", query=query)

    fts_query = _or_query(query)
    if not fts_query:
        conn.close()
        return {"query": query, "scope": scope, "results": [], "count": 0}

    if scope == "all":
        fts_rows = conn.execute(
            """SELECT n.id, n.path, n.title, n.summary, n.project_id
               FROM knowledge_fts f
               JOIN knowledge_nodes n ON f.rowid = n.rowid
               WHERE knowledge_fts MATCH ?
               ORDER BY rank""",
            (fts_query,)
        ).fetchall()
        allowed_ids = None
    else:
        fts_rows = conn.execute(
            """SELECT n.id, n.path, n.title, n.summary, n.project_id
               FROM knowledge_fts f
               JOIN knowledge_nodes n ON f.rowid = n.rowid
               WHERE knowledge_fts MATCH ? AND n.project_id IN ('shared', ?)
               ORDER BY rank""",
            (fts_query, scope)
        ).fetchall()
        allowed_ids = {r["id"] for r in conn.execute(
            "SELECT id FROM knowledge_nodes WHERE project_id IN ('shared', ?)", (scope,)
        )}

    by_id = {r["id"]: r for r in fts_rows}
    fts_ordered_ids = [r["id"] for r in fts_rows]

    query_vec = embeddings.embed_text(query)
    embedding_ordered_ids = (
        _embedding_ranking(conn, "node", query_vec, allowed_ids) if query_vec else []
    )
    final_ids = _fuse_with_keyword_floor(fts_ordered_ids, embedding_ordered_ids, max_results)

    missing = [i for i in final_ids if i not in by_id]
    if missing:
        placeholders = ",".join("?" for _ in missing)
        for r in conn.execute(
            f"SELECT id, path, title, summary, project_id FROM knowledge_nodes WHERE id IN ({placeholders})",
            missing
        ):
            by_id[r["id"]] = r

    results = [{"id": by_id[i]["id"], "path": by_id[i]["path"], "title": by_id[i]["title"],
                "summary": by_id[i]["summary"], "project": by_id[i]["project_id"]}
               for i in final_ids if i in by_id]
    if not results:
        _log_zero_hit(query)
    conn.close()
    return {"query": query, "scope": scope, "results": results, "count": len(results)}


def knowledge_add(parent_path: str, title: str, summary: str,
                  content: str = "", project_id: str = "shared",
                  tags: list | None = None, source: str = "") -> dict:
    """Add a new knowledge node to the tree."""
    fixed = unmangle_knowledge_fields({
        "title": title, "summary": summary, "content": content, "tags": tags, "source": source,
    })
    title, summary = fixed["title"], fixed["summary"]
    content, tags, source = fixed["content"], fixed["tags"], fixed["source"]

    conn = get_db()
    parent_path = parent_path.rstrip("/")

    # Derive path from parent + slugified title
    slug = title.lower().replace(" ", "-").replace("/", "-")[:40]
    node_path = f"{parent_path}/{slug}" if parent_path != "/" else f"/{slug}"

    # Check for duplicates
    existing = conn.execute("SELECT id FROM knowledge_nodes WHERE path = ?", (node_path,)).fetchone()
    if existing:
        conn.close()
        return {"error": f"Node already exists at path: {node_path}", "existing_id": existing["id"]}

    # Calculate level
    level = node_path.count("/") - 1

    node_id = str(uuid.uuid4())[:8]
    conn.execute(
        """INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, content, level, tags, source, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (node_id, node_path, parent_path, project_id, title, summary, content,
         level, json.dumps(tags or []), source, now_iso(), now_iso())
    )
    log_access(conn, node_path, "add", project_id=project_id)
    conn.commit()
    conn.close()
    return {"id": node_id, "path": node_path, "status": "created"}


def knowledge_update(node_id: str, summary: str | None = None,
                     content: str | None = None, tags: list | None = None) -> dict:
    """Update an existing knowledge node."""
    conn = get_db()
    row = conn.execute("SELECT * FROM knowledge_nodes WHERE id = ? OR path = ?", (node_id, node_id)).fetchone()
    if not row:
        conn.close()
        return {"error": f"Node not found: {node_id}"}

    # Derselbe Aufrufer-Fehler wie bei knowledge_add moeglich (Parametergrenze
    # verrutscht ins Textfeld) -- nur uebergebene Felder unmangeln.
    given = {k: v for k, v in {"summary": summary, "content": content, "tags": tags}.items()
             if v is not None}
    if given:
        fixed = unmangle_knowledge_fields(given)
        summary = fixed.get("summary", summary)
        content = fixed.get("content", content)
        tags = fixed.get("tags", tags)

    updates = []
    params = []
    if summary is not None:
        updates.append("summary = ?")
        params.append(summary)
    if content is not None:
        updates.append("content = ?")
        params.append(content)
    if tags is not None:
        updates.append("tags = ?")
        params.append(json.dumps(tags))

    updates.append("updated_at = ?")
    params.append(now_iso())
    params.append(row["id"])

    conn.execute(f"UPDATE knowledge_nodes SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return {"id": row["id"], "status": "updated"}


def _build_field_tag_re(fields: tuple) -> re.Pattern:
    """Baut die Feldgrenzen-Regex fuer eine gegebene Feldnamen-Menge.

    Zwei Tag-Stile kommen in der Wildnis vor: plain `<root_cause>...</root_cause>`
    und der antml-Tool-Call-Stil `<parameter name="root_cause">...</parameter>`
    (Schliesser dort ist generisch `</parameter>`, traegt keinen Feldnamen).
    Gemeinsame Engine fuer lesson_record UND knowledge_add -- beide leiden am
    selben Aufrufer-Fehler (Parametergrenze rutscht in den vorherigen Textwert),
    nur mit unterschiedlichen Feldnamen.
    """
    alt = "|".join(fields)
    return re.compile(
        r'<parameter\s+name="(?P<pname>' + alt + r')"\s*>'
        r"|</parameter>"
        r"|<(?P<oname>" + alt + r")>"
        r"|</(?P<cname>" + alt + r")>"
    )


LESSON_TEXT_FIELDS = ("description", "root_cause", "resolution", "prevention",
                      "severity", "projects", "node_path", "type")
_FIELD_TAG = _build_field_tag_re(LESSON_TEXT_FIELDS)

KNOWLEDGE_TEXT_FIELDS = ("content", "tags", "source", "summary", "title")
_KNOWLEDGE_FIELD_TAG = _build_field_tag_re(KNOWLEDGE_TEXT_FIELDS)

# "parameter" bewusst NICHT hier: ein `<parameter name="root_cause">` kann auch
# ein Zitat im Fliesstext sein (z.B. eine Lesson, die diesen Bug beschreibt).
# Echte, an einer Feldgrenze stehende parameter-Tags werden bereits von
# _split_tagged konsumiert und tauchen danach gar nicht mehr auf; ein
# uebrigbleibender parameter-Tag ist also so gut wie sicher ein Zitat und
# muss stehen bleiben. invoke/function_calls/antml:* sind dagegen reines
# Aufruf-Rauschen, das nie sinnvoll zitiert wird.
_CALL_NOISE = re.compile(r"</?(invoke|function_calls|antml:\w+)[^>]*>")


def _is_boundary_tag(value: str, m: re.Match) -> bool:
    """Nur Tags an einer echten Feldgrenze zaehlen, nicht als Zitat im Fliesstext.

    Eine echte verrutschte Feldgrenze steht immer isoliert: der Aufrufer
    schliesst einen Parameter und oeffnet sofort den naechsten, nie mitten in
    einem Satz. Ein oeffnender Tag zaehlt daher nur, wenn direkt davor (nur
    Leerraum dazwischen) Zeilenanfang/Stringanfang ODER das Ende eines anderen
    Tags (`>`) steht; ein schliessender Tag nur, wenn direkt danach
    Zeilenende/Stringende ODER der Anfang eines anderen Tags (`<`) folgt. Das
    deckt sowohl "jeder Tag auf eigener Zeile" als auch "Tags ohne Trenner
    aneinandergereiht" ab, verwirft aber einen Tag, der als Beispiel mitten in
    einem Satz zitiert wird (z.B. eine Lesson, die den Bug selbst beschreibt)
    — dort steht vor UND nach dem Tag echter Satztext auf derselben Zeile.
    """
    is_open = m.group("pname") is not None or m.group("oname") is not None
    if is_open:
        j = m.start()
        while j > 0 and value[j - 1] in " \t":
            j -= 1
        return j == 0 or value[j - 1] in "\n>"
    j = m.end()
    while j < len(value) and value[j] in " \t":
        j += 1
    return j == len(value) or value[j] in "\n<"


def _split_tagged(value: str, field_tag_re: re.Pattern = _FIELD_TAG) -> dict:
    """Zerlegt einen Wert an echten Feld-Tag-Grenzen (siehe _is_boundary_tag).

    Kein Zeichen NUTZTEXT geht verloren: jeder Textanteil, der keiner erkannten
    Feldgrenze zugeordnet werden kann (z.B. weil das Zielfeld gerade `current`
    None ist — etwa bei einem verwaisten schliessenden Tag), landet unter
    "_head" statt verworfen zu werden. Einzige Ausnahme: ein Anteil, der
    zwischen zwei Tags liegt UND nur aus Leerraum besteht, ist der
    Formatierungs-Zwischenraum der Tags selbst (kein Inhalt) und wird nicht
    extra angehaengt — sonst haeuften sich bei mehreren aufeinanderfolgenden
    Tags leere Zeilen im Ursprungsfeld an.

    field_tag_re: welche Feldnamen als Grenze zaehlen -- default die Lesson-
    Felder (_FIELD_TAG), knowledge_add nutzt _KNOWLEDGE_FIELD_TAG (siehe
    unmangle_knowledge_fields).
    """
    matches = [m for m in field_tag_re.finditer(value) if _is_boundary_tag(value, m)]
    out: dict[str, str] = {}
    current: str | None = None
    pos = 0
    head_parts: list[str] = []
    for m in matches:
        segment = value[pos:m.start()]
        if current is None:
            if segment.strip():
                head_parts.append(segment)
        else:
            out[current] = out.get(current, "") + segment
        pname, oname, cname = m.group("pname"), m.group("oname"), m.group("cname")
        is_open = pname is not None or oname is not None
        name = pname or oname or cname  # cname/name may be None for bare </parameter>
        current = name if is_open else None
        pos = m.end()
    tail = value[pos:]
    if current is None:
        if tail.strip():
            head_parts.append(tail)
    else:
        out[current] = out.get(current, "") + tail
    out["_head"] = "".join(head_parts)
    return out


def unmangle_lesson_fields(fields: dict) -> dict:
    """Repariert verrutschte Parametergrenzen in Lesson-Aufrufen.

    Schreibt ein Aufrufer einen langen mehrzeiligen Wert, rutscht die Grenze zum
    naechsten Parameter gelegentlich ins Textfeld — dann steht z.B. der komplette
    `root_cause` als `<root_cause>…</root_cause>` im `description`-Wert. 21 der
    218 Lessons waren so verstuemmelt, ausgerechnet die laengsten. Hier werden die
    Tags erkannt und die Anteile auf die richtigen Spalten verteilt; nur leere
    Zielfelder werden befuellt, ein echter Wert gewinnt immer. Kein Zeichen geht
    verloren: Text, dessen Zielfeld schon belegt ist oder der sich keinem Feld
    zuordnen laesst, bleibt im Ursprungsfeld erhalten statt geloescht zu werden.
    """
    out = dict(fields)
    for name in LESSON_TEXT_FIELDS:
        val = out.get(name)
        if not isinstance(val, str) or not _FIELD_TAG.search(val):
            continue
        parts = _split_tagged(val)
        head = parts.pop("_head", "")
        if not parts:
            continue  # keine echte Feldgrenze gefunden (z.B. nur ein Zitat im Fliesstext)
        leftover = []
        for key, text in parts.items():
            stripped = text.strip()
            if not stripped:
                continue
            current_val = str(out.get(key) or "").strip()
            # severity traegt immer den Schema-Default "medium", auch wenn nie explizit
            # gesetzt — von einem echten Wert nicht unterscheidbar. Ein aus dem Tag
            # extrahierter gueltiger Enum-Wert gewinnt deshalb hier gegen den Default.
            beats_default = (key == "severity" and current_val == "medium"
                             and stripped in ("critical", "high", "medium", "low"))
            if key != name and (not current_val or beats_default):
                out[key] = stripped if key == "severity" else text
            else:
                leftover.append(text)
        out[name] = head + ("\n" + "\n".join(leftover) if leftover else "")
    for name in LESSON_TEXT_FIELDS:
        if isinstance(out.get(name), str):
            out[name] = _CALL_NOISE.sub("", out[name]).strip()
    if isinstance(out.get("projects"), str):
        try:
            out["projects"] = json.loads(out["projects"])
        except (ValueError, TypeError):
            out["projects"] = [p.strip(' "\'') for p in out["projects"].strip('[]').split(",") if p.strip(' "\'')]
    return out


def unmangle_knowledge_fields(fields: dict) -> dict:
    """Repariert verrutschte Parametergrenzen in knowledge_add/knowledge_update-
    Aufrufen -- derselbe Aufrufer-Fehler wie bei unmangle_lesson_fields, nur mit
    Knowledge-Feldnamen: der komplette content/tags/source landet dann als
    `<content>...</content>` etc. im summary-Wert (gemessen an efa1f597,
    7781dea1, 2a6098d1, c60b1b46, 3a978881, 5d899304). Nur leere Zielfelder
    werden befuellt, ein echter Wert gewinnt immer; kein Zeichen geht verloren.
    """
    out = dict(fields)
    for name in KNOWLEDGE_TEXT_FIELDS:
        val = out.get(name)
        if not isinstance(val, str) or not _KNOWLEDGE_FIELD_TAG.search(val):
            continue
        parts = _split_tagged(val, _KNOWLEDGE_FIELD_TAG)
        head = parts.pop("_head", "")
        if not parts:
            continue  # keine echte Feldgrenze gefunden (z.B. nur ein Zitat im Fliesstext)
        leftover = []
        for key, text in parts.items():
            stripped = text.strip()
            if not stripped:
                continue
            current_val = out.get(key)
            has_value = bool(current_val) if isinstance(current_val, list) else bool(str(current_val or "").strip())
            if key != name and not has_value:
                out[key] = stripped if key == "tags" else text
            else:
                leftover.append(text)
        out[name] = head + ("\n" + "\n".join(leftover) if leftover else "")
    for name in KNOWLEDGE_TEXT_FIELDS:
        if isinstance(out.get(name), str):
            out[name] = _CALL_NOISE.sub("", out[name]).strip()
    if isinstance(out.get("tags"), str):
        try:
            out["tags"] = json.loads(out["tags"])
        except (ValueError, TypeError):
            out["tags"] = [p.strip(' "\'') for p in out["tags"].strip("[]").split(",") if p.strip(' "\'')]
    return out


MAX_REPEAT_PARAGRAPHS = 5
_REPEAT_MARKER_RE = re.compile(r"\n\n--- Wiederholung ([0-9T:+\-]+) ---\n")


def _append_repetition(base_description: str, new_text: str, when: str,
                       cap: int = MAX_REPEAT_PARAGRAPHS) -> str:
    """Haengt einen datierten Wiederholungs-Absatz an eine bestehende Beschreibung an.

    Gedeckelt auf die `cap` juengsten Wiederholungen — sonst waechst ein Eintrag
    unbegrenzt und wird unlesbar. Der urspruengliche Beschreibungstext (vor der
    ersten Wiederholung) bleibt immer erhalten, nur ueberzaehlige Wiederholungen
    fallen von vorne heraus.
    """
    parts = _REPEAT_MARKER_RE.split(base_description)
    head = parts[0]
    reps = list(zip(parts[1::2], parts[2::2]))
    reps.append((when, new_text.strip()))
    reps = reps[-cap:]
    out = head
    for date, text in reps:
        out += f"\n\n--- Wiederholung {date} ---\n{text}"
    return out


_STOPWORDS_DE = {
    "der", "die", "das", "und", "oder", "ein", "eine", "einer", "eines", "einem",
    "einen", "ist", "sind", "war", "waren", "im", "in", "am", "an", "auf", "zu",
    "von", "mit", "fuer", "für", "den", "dem", "des", "als", "auch", "nicht",
    "sich", "es", "bei", "aus", "wurde", "wurden", "werden", "sein", "seine",
    "seiner", "seinem", "je", "jede", "jeder", "jedes", "noch", "nur", "schon",
    "dann", "aber", "wenn", "hat", "hatte", "haben", "kann", "koennen", "können",
    "muss", "muessen", "müssen", "wird", "wo", "was", "wie", "so", "um", "ueber",
    "über", "nach", "vor", "durch",
}
_WORD_RE = re.compile(r"[a-zA-ZäöüÄÖÜß]+")
SIMILARITY_THRESHOLD = 0.18  # kalibriert gegen den Bestand, siehe PLAN/Bericht


def _tokenize(text: str) -> set:
    return {w for w in (m.lower() for m in _WORD_RE.findall(text))
            if w not in _STOPWORDS_DE and len(w) > 2}


def _find_similar_lesson(conn: sqlite3.Connection, type_: str, description: str,
                         threshold: float = SIMILARITY_THRESHOLD) -> dict | None:
    """Wortmengen-Jaccard-Vergleich gegen aktive Lessons desselben Typs.

    Reiner Hinweis fuer die Antwort, kein automatisches Verschmelzen (siehe
    lesson_record Docstring: zwei Lessons faelschlich zusammenzuziehen ist
    teurer als eine Dublette).
    """
    needle = _tokenize(description)
    if not needle:
        return None
    best = None
    for row in conn.execute(
        "SELECT id, occurrences, description FROM lessons_learned WHERE type = ? AND status = 'active'",
        (type_,)
    ):
        hay = _tokenize(row["description"])
        if not hay:
            continue
        score = len(needle & hay) / len(needle | hay)
        if score >= threshold and (best is None or score > best["score"]):
            best = {
                "id": row["id"],
                "occurrences": row["occurrences"],
                "score": round(score, 2),
                "description_first_line": row["description"].splitlines()[0][:200],
            }
    return best


def _bump_lesson(conn: sqlite3.Connection, lesson_id: str, node_path: str,
                 log_query: str, new_description: str | None = None) -> dict:
    """Erhoeht occurrences einer bestehenden Lesson um eins, eskaliert ab 3.

    Gemeinsamer Pfad fuer den exakten Dublettentreffer und den expliziten
    same_as-Bezug — nur die Frage, ob dabei auch die description ersetzt wird
    (Wiederholungs-Anhang), unterscheidet die beiden Aufrufer.
    """
    row = conn.execute("SELECT occurrences FROM lessons_learned WHERE id = ?", (lesson_id,)).fetchone()
    new_count = row["occurrences"] + 1
    if new_description is not None:
        conn.execute(
            "UPDATE lessons_learned SET occurrences = ?, description = ?, last_seen = ? WHERE id = ?",
            (new_count, new_description, now_iso(), lesson_id)
        )
    else:
        conn.execute(
            "UPDATE lessons_learned SET occurrences = ?, last_seen = ? WHERE id = ?",
            (new_count, now_iso(), lesson_id)
        )
    log_access(conn, node_path or None, "lesson", query=log_query)
    conn.commit()

    escalated = new_count >= 3
    if escalated:
        conn.execute(
            "UPDATE lessons_learned SET status = 'escalated_to_rule' WHERE id = ?",
            (lesson_id,)
        )
        conn.commit()

    return {
        "id": lesson_id,
        "status": "incremented",
        "occurrences": new_count,
        "escalated": escalated,
        "message": f"Lesson seen {new_count}x. {'ESCALATED: Should become a rule in .instructions.md!' if escalated else ''}"
    }


def lesson_record(type_: str, description: str, root_cause: str = "",
                  resolution: str = "", prevention: str = "",
                  severity: str = "medium", projects: list | None = None,
                  node_path: str = "", same_as: str = "") -> dict:
    """Record a lesson learned.

    same_as gesetzt: erhoeht occurrences der referenzierten Lesson, haengt
    diese Beschreibung als datierten Wiederholungs-Absatz an (gedeckelt),
    legt KEINEN neuen Eintrag an. Zeigt same_as ins Leere: Fehler, kein
    stiller Fallback.

    same_as leer: bisheriges Verhalten (exakte Dublette gleichen Typs +
    gleicher Beschreibung erhoeht occurrences; sonst neuer Eintrag). Bei
    neuem Eintrag zusaetzlich ein Aehnlichkeits-Hinweis in der Antwort
    (similar_lesson_hint), falls eine inhaltlich nahe aktive Lesson
    gleichen Typs existiert — ohne automatisches Verschmelzen.

    Ab 3 Vorkommen (same_as-Pfad wie bisheriger Exact-Match-Pfad) wird die
    Lesson auf status='escalated_to_rule' gesetzt.
    """
    fixed = unmangle_lesson_fields({
        "type": type_, "description": description, "root_cause": root_cause,
        "resolution": resolution, "prevention": prevention, "severity": severity,
        "projects": projects, "node_path": node_path,
    })
    type_, description = fixed["type"], fixed["description"]
    root_cause, resolution = fixed["root_cause"], fixed["resolution"]
    prevention, severity = fixed["prevention"], fixed["severity"] or "medium"
    projects, node_path = fixed["projects"], fixed["node_path"]

    if not description.strip():
        return {"status": "rejected",
                "error": "description ist leer — Lesson nicht gespeichert."}

    conn = get_db()

    if same_as:
        target = conn.execute(
            "SELECT id, occurrences, description FROM lessons_learned WHERE id = ?",
            (same_as,)
        ).fetchone()
        if not target:
            conn.close()
            return {"status": "rejected",
                    "error": f"same_as verweist auf keine bestehende Lesson: {same_as}"}
        merged_description = _append_repetition(target["description"], description, now_iso())
        result = _bump_lesson(conn, target["id"], node_path, description,
                              new_description=merged_description)
        conn.close()
        return result

    # Check for exact-duplicate existing lesson (same type + same description)
    existing = conn.execute(
        "SELECT id, occurrences FROM lessons_learned WHERE type = ? AND description = ? AND status = 'active'",
        (type_, description)
    ).fetchone()

    if existing:
        result = _bump_lesson(conn, existing["id"], node_path, description)
        conn.close()
        return result

    similar = _find_similar_lesson(conn, type_, description)

    lesson_id = f"L-{str(uuid.uuid4())[:6]}"
    conn.execute(
        """INSERT INTO lessons_learned (id, node_path, type, severity, description, root_cause, resolution, prevention, occurrences, projects, first_seen, last_seen)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)""",
        (lesson_id, node_path or None, type_, severity, description, root_cause,
         resolution, prevention, json.dumps(projects or []), now_iso(), now_iso())
    )
    log_access(conn, node_path or None, "lesson", query=description)
    conn.commit()
    conn.close()
    result = {"id": lesson_id, "status": "recorded", "occurrences": 1}
    if similar:
        result["similar_lesson_hint"] = similar
    return result


def lesson_update(lesson_id: str, description: str | None = None,
                  root_cause: str | None = None, resolution: str | None = None,
                  prevention: str | None = None, severity: str | None = None,
                  projects: list | None = None, status: str | None = None,
                  delete: bool = False) -> dict:
    """Correct or delete a recorded lesson. Only fields given are changed; the rest is left untouched."""
    conn = get_db()
    row = conn.execute("SELECT id FROM lessons_learned WHERE id = ?", (lesson_id,)).fetchone()
    if not row:
        conn.close()
        return {"error": f"Lesson not found: {lesson_id}"}

    if delete:
        conn.execute("DELETE FROM lessons_learned WHERE id = ?", (lesson_id,))
        log_access(conn, None, "lesson_delete", query=lesson_id)
        conn.commit()
        conn.close()
        return {"id": lesson_id, "status": "deleted"}

    raw = {
        "description": description, "root_cause": root_cause, "resolution": resolution,
        "prevention": prevention, "severity": severity, "projects": projects,
    }
    # Nur uebergebene Felder unmangeln/schreiben — derselbe Aufrufer-Fehler wie bei
    # lesson_record (Parametergrenze verrutscht ins Textfeld) kann hier genauso passieren.
    given = {k: v for k, v in raw.items() if v is not None}
    if given:
        fixed = unmangle_lesson_fields(given)
        given.update(fixed)

    updates = []
    params = []
    for col in ("description", "root_cause", "resolution", "prevention", "severity"):
        if col in given:
            updates.append(f"{col} = ?")
            params.append(given[col])
    if "projects" in given:
        updates.append("projects = ?")
        params.append(json.dumps(given["projects"] or []))
    if status is not None:
        updates.append("status = ?")
        params.append(status)

    if not updates:
        conn.close()
        return {"id": lesson_id, "status": "unchanged", "message": "Keine Felder uebergeben."}

    updates.append("last_seen = ?")
    params.append(now_iso())
    params.append(lesson_id)

    conn.execute(f"UPDATE lessons_learned SET {', '.join(updates)} WHERE id = ?", params)
    log_access(conn, None, "lesson_update", query=lesson_id)
    conn.commit()
    conn.close()
    return {"id": lesson_id, "status": "updated"}


def lesson_query(type_: str | None = None, project: str | None = None,
                 status: str = "active", max_results: int = 10,
                 query: str | None = None) -> dict:
    """Query lessons learned by type, project, or status. Optional `query`:
    Bedeutungs-/Stichwortsuche in description/root_cause/prevention (LIKE als
    Stichwort-Basis + optionale Embedding-Fusion, RRF wie knowledge_search).
    Ohne `query` unveraendertes Altverhalten (reine Filter, sortiert nach
    occurrences/last_seen)."""
    conn = get_db()
    conditions = []
    params = []

    if type_:
        conditions.append("type = ?")
        params.append(type_)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if project:
        conditions.append("projects LIKE ?")
        params.append(f'%"{project}"%')

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    if not query:
        rows = conn.execute(
            f"SELECT * FROM lessons_learned {where} ORDER BY occurrences DESC, last_seen DESC LIMIT ?",
            (*params, max_results)
        ).fetchall()
        results = [dict(r) for r in rows]
        conn.close()
        return {"results": results, "count": len(results)}

    all_rows = conn.execute(f"SELECT * FROM lessons_learned {where}", tuple(params)).fetchall()
    by_id = {r["id"]: r for r in all_rows}
    # Mindestlaenge 4 + Stopwortfilter wie knowledge_recall_hook.py's STOP-Liste
    # (hier dupliziert, nicht importiert -- der Hook selbst bleibt unangetastet,
    # siehe Auftrag). Ohne Filter matchen 3-Buchstaben-Fuellwoerter ("die",
    # "und", "ist") als Substring in fast jedem Lesson-Text und ertraenken das
    # eigentliche Signal.
    _stop = {
        "und", "oder", "der", "die", "das", "den", "dem", "ein", "eine", "einen", "einem",
        "ist", "sind", "war", "wird", "werden", "kann", "soll", "muss", "für", "mit", "von",
        "auf", "aus", "bei", "zum", "zur", "des", "als", "auch", "nicht", "noch", "wie", "was",
        "wenn", "dann", "aber", "nur", "mir", "mich", "dir", "dich", "ich", "wir", "ihr", "sie",
        "sich", "durch", "the", "and", "for", "that", "this", "with", "from", "have", "has",
        "was", "are", "you", "can", "should", "must", "not", "how", "what", "when", "then",
    }
    keywords = [w for w in re.findall(r"[A-Za-zÄÖÜäöüß0-9]{4,}", query.lower()) if w not in _stop]

    def kw_hits(row: sqlite3.Row) -> int:
        text = f"{row['description']} {row['root_cause']} {row['prevention']}".lower()
        return sum(1 for k in keywords if k in text)

    keyword_ordered_ids = sorted((i for i in by_id if kw_hits(by_id[i]) > 0),
                                  key=lambda i: kw_hits(by_id[i]), reverse=True)

    query_vec = embeddings.embed_text(query)
    embedding_ordered_ids = (
        _embedding_ranking(conn, "lesson", query_vec, set(by_id.keys())) if query_vec else []
    )
    final_ids = _fuse_with_keyword_floor(keyword_ordered_ids, embedding_ordered_ids, max_results)

    results = [dict(by_id[i]) for i in final_ids if i in by_id]
    conn.close()
    return {"results": results, "count": len(results)}


def knowledge_stats() -> dict:
    """Overview statistics of the knowledge database."""
    conn = get_db()
    total_nodes = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    by_project = dict(conn.execute(
        "SELECT project_id, COUNT(*) FROM knowledge_nodes GROUP BY project_id"
    ).fetchall())
    by_level = dict(conn.execute(
        "SELECT level, COUNT(*) FROM knowledge_nodes GROUP BY level"
    ).fetchall())
    total_lessons = conn.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
    active_lessons = conn.execute("SELECT COUNT(*) FROM lessons_learned WHERE status = 'active'").fetchone()[0]
    escalated = conn.execute("SELECT COUNT(*) FROM lessons_learned WHERE status = 'escalated_to_rule'").fetchone()[0]
    recent_access = conn.execute(
        "SELECT action, COUNT(*) as cnt FROM access_log GROUP BY action"
    ).fetchall()
    conn.close()

    return {
        "nodes_total": total_nodes,
        "nodes_by_project": by_project,
        "nodes_by_level": by_level,
        "lessons_total": total_lessons,
        "lessons_active": active_lessons,
        "lessons_escalated": escalated,
        "access_patterns": dict(recent_access),
        "db_path": str(DB_PATH),
        "timestamp": now_iso()
    }


# ─── MCP Server Protocol (stdio JSON-RPC 2.0) ───────────────────────────

TOOLS = {
    "knowledge_browse": {
        "description": "Browse children of a knowledge tree node. Returns titles+summaries only (token-efficient). Use '/' for root.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Tree path to browse, e.g. '/' or '/shared/arch'", "default": "/"},
                "project_filter": {"type": "string", "description": "Filter by project: shared|begod|aka|bebetter"}
            }
        },
        "handler": lambda args: knowledge_browse(args.get("path", "/"), args.get("project_filter"))
    },
    "knowledge_read": {
        "description": "Read full content of a knowledge node (by ID or path). Use browse/search first to find the right node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "Node ID or full path"}
            },
            "required": ["node_id"]
        },
        "handler": lambda args: knowledge_read(args["node_id"])
    },
    "knowledge_search": {
        "description": "Full-text search across knowledge. Returns summaries (not full content) for token efficiency.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (FTS5 syntax supported: AND, OR, NOT, phrases). Hybrid: fuses keyword matches with local-embedding meaning search when vectors exist."},
                "scope": {"type": "string", "description": "Scope: 'all' or project name", "default": "all"},
                "max_results": {"type": "integer", "description": "Max results (default 10)", "default": 10}
            },
            "required": ["query"]
        },
        "handler": lambda args: knowledge_search(args["query"], args.get("scope", "all"), args.get("max_results", 10))
    },
    "knowledge_add": {
        "description": "Add a new knowledge node to the tree. Specify parent_path to place it in the hierarchy.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "parent_path": {"type": "string", "description": "Parent node path, e.g. '/shared/arch'"},
                "title": {"type": "string"},
                "summary": {"type": "string", "description": "1-2 sentences summary (token-efficient)"},
                "content": {"type": "string", "description": "Full content (loaded only on read)"},
                "project_id": {"type": "string", "description": "shared|begod|aka|bebetter", "default": "shared"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "source": {"type": "string", "description": "Origin: file path, konsil ID, or research ID"}
            },
            "required": ["parent_path", "title", "summary"]
        },
        "handler": lambda args: knowledge_add(
            args["parent_path"], args["title"], args["summary"],
            args.get("content", ""), args.get("project_id", "shared"),
            args.get("tags"), args.get("source", "")
        )
    },
    "knowledge_update": {
        "description": "Update an existing knowledge node (summary, content, or tags).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "Node ID or path"},
                "summary": {"type": "string"},
                "content": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["node_id"]
        },
        "handler": lambda args: knowledge_update(
            args["node_id"], args.get("summary"), args.get("content"), args.get("tags")
        )
    },
    "lesson_record": {
        "description": (
            "Record a lesson learned. Pass same_as=<lesson id> when this is a repeat of an "
            "already-recorded lesson: increments that lesson's occurrences, appends this "
            "description to it as a dated, capped repetition note, and creates no new row "
            "(unknown same_as id is an error, never a silent new entry). Escalates to rule "
            "at 3+ occurrences. Without same_as: increments occurrences only on an exact "
            "duplicate (same type + byte-identical description); otherwise creates a new "
            "lesson and, if an active lesson of the same type looks similar, returns it as "
            "similar_lesson_hint (a hint only — never auto-merged; re-record with same_as to merge)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["error", "insight", "pattern", "antipattern"]},
                "description": {"type": "string"},
                "root_cause": {"type": "string"},
                "resolution": {"type": "string"},
                "prevention": {"type": "string"},
                "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"], "default": "medium"},
                "projects": {"type": "array", "items": {"type": "string"}, "description": "Affected projects"},
                "node_path": {"type": "string", "description": "Related knowledge node path"},
                "same_as": {"type": "string", "description": "ID of an existing lesson this is a repeat of, e.g. 'L-6e48a9'"}
            },
            "required": ["type", "description"]
        },
        "handler": lambda args: lesson_record(
            args["type"], args["description"], args.get("root_cause", ""),
            args.get("resolution", ""), args.get("prevention", ""),
            args.get("severity", "medium"), args.get("projects"), args.get("node_path", ""),
            args.get("same_as", "")
        )
    },
    "lesson_update": {
        "description": "Correct or delete a recorded lesson. Only given fields are changed; unmangles field-tag corruption in the same way lesson_record does. Use delete:true to remove a bad entry.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lesson_id": {"type": "string", "description": "Lesson ID, e.g. 'L-6e48a9'"},
                "description": {"type": "string"},
                "root_cause": {"type": "string"},
                "resolution": {"type": "string"},
                "prevention": {"type": "string"},
                "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                "projects": {"type": "array", "items": {"type": "string"}},
                "status": {"type": "string", "enum": ["active", "resolved", "escalated_to_rule"]},
                "delete": {"type": "boolean", "description": "Delete the lesson instead of updating it", "default": False}
            },
            "required": ["lesson_id"]
        },
        "handler": lambda args: lesson_update(
            args["lesson_id"], args.get("description"), args.get("root_cause"),
            args.get("resolution"), args.get("prevention"), args.get("severity"),
            args.get("projects"), args.get("status"), args.get("delete", False)
        )
    },
    "lesson_query": {
        "description": "Query lessons learned. Filter by type, project, or status. Optional 'query' searches description/root_cause/prevention by keyword and meaning (hybrid).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["error", "insight", "pattern", "antipattern"]},
                "project": {"type": "string"},
                "status": {"type": "string", "enum": ["active", "resolved", "escalated_to_rule"], "default": "active"},
                "max_results": {"type": "integer", "default": 10},
                "query": {"type": "string", "description": "Optional: Stichwort-/Bedeutungssuche in description/root_cause/prevention"}
            }
        },
        "handler": lambda args: lesson_query(
            args.get("type"), args.get("project"), args.get("status", "active"),
            args.get("max_results", 10), args.get("query")
        )
    },
    "knowledge_stats": {
        "description": "Overview statistics of the knowledge database (node counts, lesson counts, access patterns).",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda args: knowledge_stats()
    }
}


def handle_request(req: dict) -> dict:
    method = req.get("method", "")
    req_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "knowledge-mcp", "version": "1.0.0"}
            }
        }

    if method == "notifications/initialized":
        return None  # No response for notifications

    if method == "tools/list":
        tool_list = []
        for name, spec in TOOLS.items():
            tool_list.append({
                "name": name,
                "description": spec["description"],
                "inputSchema": spec["inputSchema"]
            })
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tool_list}}

    if method == "tools/call":
        tool_name = req.get("params", {}).get("name", "")
        arguments = req.get("params", {}).get("arguments", {})

        if tool_name not in TOOLS:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps({"error": f"Unknown tool: {tool_name}"})}], "isError": True}
            }

        try:
            result = TOOLS[tool_name]["handler"](arguments)
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps({"error": str(e)})}], "isError": True}
            }

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def main():
    """stdio MCP server — reads JSON-RPC from stdin, writes to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        response = handle_request(req)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
