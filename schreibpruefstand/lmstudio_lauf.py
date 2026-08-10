"""Zweiter Treiber: gleiche Aufgabe wie schreiblauf.py, aber gegen ein
lokales LM Studio (OpenAI-kompatibel, /v1/chat/completions, echter
Werkzeugaufruf statt Text-Prompt mit JSON-Schema drin). Ollama's
/api/generate kennt kein natives tool-calling -- schreiblauf.py bettet das
knowledge_add-Schema deshalb als Text in den Prompt. LM Studio bietet
tools=[...] nativ -- das ist der interessante Unterschied, den dieser
Treiber misst: traegt die Werkzeugbeschreibung auch als ECHTER Funktionsaufruf.

Reuse statt Duplikat: build_prompt/_current_tree/_parse_model_json/
_KNOWLEDGE_ADD_FIELDS/summarize kommen unveraendert aus schreiblauf.py.
Nur der Transport (Ollama /api/generate vs. LM Studio /v1/chat/completions
mit tools=) unterscheidet sich.

geaenderte Dateien ausserhalb dieses Verzeichnisses: KEINE. Kein
Schreibzugriff auf shared-knowledge/knowledge.db.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

SCHREIBPRUEFSTAND_DIR = Path(__file__).resolve().parent
SHARED_KNOWLEDGE = SCHREIBPRUEFSTAND_DIR.parent
sys.path.insert(0, str(SCHREIBPRUEFSTAND_DIR))
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import demo_db  # noqa: E402
import knowledge_mcp_server as kms  # noqa: E402
import schreiblauf as sl  # noqa: E402  -- Wiederverwendung, keine Kopie

DEFAULT_MODEL = "qwen/qwen3-coder-30b"
DEFAULT_BASE_URL = "http://127.0.0.1:1234"
# gleiches Limit wie schreiblauf.py (CALL_TIMEOUT), hergeleitet aus lauf2.json
CALL_TIMEOUT = sl.CALL_TIMEOUT

# LM Studio verlangt seit einer neueren Fassung einen Bearer-Token
# (Developer-Einstellung "Require API key" im GUI). Kein Token hier
# hinterlegt -- Zugangsdaten tippt der Betreiber selbst, siehe CLAUDE.md.
# Env-Var statt Quellcode (BSI DEV.2.5).
API_KEY = os.environ.get("LM_STUDIO_API_KEY", "")


def _tool_schema() -> dict:
    tool = kms.TOOLS["knowledge_add"]
    return {
        "type": "function",
        "function": {
            "name": "knowledge_add",
            "description": tool["description"],
            "parameters": tool["inputSchema"],
        },
    }


def build_messages(raw_text: str, tree: list[dict]) -> list[dict]:
    tree_lines = "\n".join(f"- {n['path']} ({n['title']}, project_id={n['project_id']})" for n in tree)
    system = (
        "Du bist ein Agent mit Zugriff auf das Werkzeug knowledge_add, das Wissen in "
        "einer Baumstruktur-Datenbank ablegt. Halte das folgende Rohmaterial fest, "
        "indem du knowledge_add mit passenden Parametern aufrufst (mindestens "
        "parent_path, title, summary). parent_path muss einer der vorhandenen Pfade "
        "sein, ausser du setzt neuer_ast=true."
    )
    user = f"Vorhandene Knoten im Baum:\n{tree_lines}\n\nRohmaterial:\n\"\"\"{raw_text}\"\"\""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _call_lmstudio(messages: list[dict], *, model: str, base_url: str,
                    timeout: float) -> tuple[str | None, str | None]:
    """Gibt (rohtext_der_tool_call_argumente_oder_content, fehler) zurueck."""
    payload = {
        "model": model,
        "messages": messages,
        "tools": [_tool_schema()],
        "tool_choice": "auto",
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return None, f"LM-Studio-Aufruf fehlgeschlagen: HTTP {exc.code}: {detail[:300]}"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return None, f"LM-Studio-Aufruf fehlgeschlagen: {exc}"

    try:
        message = body["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        return None, f"LM-Studio-Aufruf fehlgeschlagen: unerwartete Antwortform: {body!r:.300}"

    tool_calls = message.get("tool_calls") or []
    for call in tool_calls:
        if call.get("function", {}).get("name") == "knowledge_add":
            return call["function"].get("arguments", ""), None
    # Kein Werkzeugaufruf -- Modell hat stattdessen Freitext geliefert. Kein
    # Fehler des Transports, sondern eine eigene Kategorie weiter unten.
    return message.get("content") or "", None


def _call_with_retry(messages: list[dict], *, model: str, base_url: str,
                      timeout: float) -> tuple[str | None, str | None, int]:
    raw_response, call_error = _call_lmstudio(messages, model=model, base_url=base_url, timeout=timeout)
    if call_error is None:
        return raw_response, call_error, 0
    raw_response, call_error = _call_lmstudio(messages, model=model, base_url=base_url, timeout=timeout)
    return raw_response, call_error, 1


def run(*, model: str = DEFAULT_MODEL, base_url: str = DEFAULT_BASE_URL,
        timeout: float = CALL_TIMEOUT, session: str | None = None,
        pieces: list[str] | None = None) -> dict:
    session = session or f"schreibpruefstand-lms-{uuid.uuid4().hex[:8]}"
    raw_pieces = pieces if pieces is not None else demo_db.RAW_MATERIAL
    db_path = demo_db.build_demo_db()
    kms.DB_PATH = db_path

    protocol: list[dict] = []
    started = time.perf_counter()

    for idx, raw_text in enumerate(raw_pieces):
        material_id = f"M-{idx:02d}"
        tree = sl._current_tree(db_path)
        messages = build_messages(raw_text, tree)

        call_started = time.perf_counter()
        raw_response, call_error, retry_count = _call_with_retry(
            messages, model=model, base_url=base_url, timeout=timeout)
        call_seconds = time.perf_counter() - call_started

        record: dict = {
            "material_id": material_id,
            "raw_material": raw_text,
            "model_response_raw": raw_response,
            "call_error": call_error,
            "call_seconds": call_seconds,
            "retry_count": retry_count,
        }

        if call_error is not None:
            record.update(category="ollama_fehler", accepted=False, reason=call_error)
            protocol.append(record)
            continue

        parsed = sl._parse_model_json(raw_response or "")
        record["model_wanted"] = parsed
        if parsed is None:
            record.update(category="unbrauchbare_antwort_kein_json", accepted=False,
                          reason="Modellantwort enthaelt keinen brauchbaren Werkzeugaufruf")
            protocol.append(record)
            continue

        call_kwargs = {k: v for k, v in parsed.items() if k in sl._KNOWLEDGE_ADD_FIELDS}
        try:
            system_response = kms.knowledge_add(
                **call_kwargs, actor="schreibpruefstand-C2-lmstudio", model=model, session=session,
            )
        except TypeError as exc:
            record.update(category="unbrauchbare_antwort_falsche_felder", accepted=False,
                          reason=str(exc))
            protocol.append(record)
            continue

        record["system_response"] = system_response
        if "error" in system_response:
            record.update(category="abgelehnt", accepted=False, reason=system_response["error"])
        else:
            record.update(category="angenommen", accepted=True, reason=None)
        protocol.append(record)

    checkpoint_conn = __import__("sqlite3").connect(str(db_path))
    checkpoint_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    checkpoint_conn.close()

    runtime = time.perf_counter() - started
    return {
        "model": model,
        "session": session,
        "db_path": str(db_path),
        "runtime_seconds": runtime,
        "n_pieces": len(raw_pieces),
        "protocol": protocol,
    }


# summarize() ist transportunabhaengig -- Wiederverwendung aus schreiblauf.py.
summarize = sl.summarize


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--timeout", type=float, default=CALL_TIMEOUT)
    ap.add_argument("--n-pieces", type=int, default=None, help="nur die ersten N Rohmaterial-Stuecke")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    pieces = demo_db.RAW_MATERIAL[:args.n_pieces] if args.n_pieces else None
    result = run(model=args.model, base_url=args.base_url, timeout=args.timeout, pieces=pieces)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Protokoll geschrieben: {args.out}")
    else:
        print(text)
    print(json.dumps(summarize(result), ensure_ascii=False, indent=2), file=sys.stderr)


if __name__ == "__main__":
    main()
