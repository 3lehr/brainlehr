"""Schreiblauf gegen ein lokales gemma (Plan C2,
docs/PLAN_SCHREIBPRUEFSTAND_2026-08-05.md).

Je Rohmaterial-Stueck (demo_db.RAW_MATERIAL) EIN Aufruf gegen ein lokales
Ollama-Modell. Der Prompt zeigt dem Modell die knowledge_add-Werkzeugbe-
schreibung 1:1 aus knowledge_mcp_server.py::TOOLS (wie ein Agent sie via MCP
saehe) und den aktuellen Baumzustand der Demo-DB -- sonst nur das
Rohmaterial-Stueck und "halte das fest". Kein Pfad, kein Titel wird
vorgegeben.

Die strukturierte JSON-Antwort des Modells wird UNVERAENDERT an
knowledge_mcp_server.knowledge_add() durchgereicht (nur auf die Parameter
der Funktion projiziert -- Python kennt keine unbekannten Kwargs). Kein
Nachbessern von Werten, keine Korrektur einer schlechten Ablage.

geaenderte Dateien ausserhalb dieses Verzeichnisses: KEINE.
shared-knowledge/knowledge_mcp_server.py wird nur importiert; sein
Modulattribut DB_PATH wird zur Laufzeit dieses Prozesses auf die Demo-DB
umgebogen (exakt das Muster aus pruefstand/messlauf.py). Kein
Schreibzugriff auf shared-knowledge/knowledge.db.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
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

DEFAULT_MODEL = "gemma4:12b"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"

# Erzeugung ist austauschbar (Ollama lokal <-> Gemini gehostet), Einbettungen
# bleiben lokal (embeddings.py, hier nicht angefasst) -- Einbettungen sind
# billig und muessen zum lokalen Bestand passen, Erzeugung ist teuer (~150s/
# Aufruf bei gemma4:12b) und damit der Hebel, den ein Vergleich braucht.
DEFAULT_BACKEND = "ollama"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
_GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_gemini_key_cache: str | None = None


def _gemini_api_key() -> str:
    """Liest GEMINI_API_KEY aus ~/.begod.env (gleiche Quelle wie
    begod/scripts/benchmark_gaia2.py) -- gecacht pro Prozess."""
    global _gemini_key_cache
    if _gemini_key_cache is not None:
        return _gemini_key_cache
    env_path = Path.home() / ".begod.env"
    key = ""
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("GEMINI_API_KEY="):
                key = line.split("=", 1)[1].strip()
                break
    _gemini_key_cache = key
    return key

# Hergeleitet aus runs/lauf2.json (23 Aufrufe, gemma4:12b): Mittelwert 90,4s,
# Standardabweichung 16,7s -> Mittelwert+3*Stdabw = 140,5s, aufgerundet.
# Beleg dass das alte Limit (120s) zu knapp war, nicht dass einzelne Aufrufe
# pathologisch lang liefen: der laengste ERFOLGREICHE Aufruf brauchte 117,5s
# (M-16), direkt unter dem alten Limit, und alle 5 Ausfaelle liefen exakt
# bis 120,00s -- das alte Limit schnitt normale Antworten ab.
CALL_TIMEOUT = 150.0

# OLLAMA_KEEP_ALIVE als Umgebungsvariable wirkt nur als Server-Vorgabewert;
# ein Anfrage-Koerper ohne eigenes keep_alive kann ihn je nach Ollama-Fassung
# ueberschreiben -- deshalb hier ausdruecklich mitgesendet statt sich auf die
# Umgebungsvariable zu verlassen.
# Muss eine JSON-Zahl sein, kein String -- eine neuere Ollama-Fassung lehnt
# "-1" als String ab ("time: missing unit in duration \"-1\"", HTTP 400),
# geprueft per curl am 2026-08-06 gegen den lokalen Server.
KEEP_ALIVE = -1

# Parameter, die knowledge_add() tatsaechlich entgegennimmt -- Auswahl ist
# eine Signaturgrenze, kein inhaltliches Nachbessern des Modellwerts.
_KNOWLEDGE_ADD_FIELDS = {"parent_path", "title", "summary", "content", "project_id", "tags", "source", "neuer_ast"}

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_FIRST_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _current_tree(db_path: Path) -> list[dict]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT path, title, project_id FROM knowledge_nodes ORDER BY path").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def build_prompt(raw_text: str, tree: list[dict]) -> str:
    tool = kms.TOOLS["knowledge_add"]
    tree_lines = "\n".join(f"- {n['path']} ({n['title']}, project_id={n['project_id']})" for n in tree)
    return f"""Du bist ein Agent mit Zugriff auf ein Werkzeug, das Wissen in einer \
Baumstruktur-Datenbank ablegt.

Werkzeug: knowledge_add
Beschreibung: {tool["description"]}
Parameter (JSON Schema): {json.dumps(tool["inputSchema"], ensure_ascii=False)}

Vorhandene Knoten im Baum (parent_path muss einer dieser Pfade sein, ausser \
du setzt neuer_ast=true):
{tree_lines}

Rohmaterial:
\"\"\"{raw_text}\"\"\"

Halte das fest. Antworte AUSSCHLIESSLICH mit einem einzelnen JSON-Objekt, \
das die Parameter von knowledge_add enthaelt (mindestens parent_path, \
title, summary). Kein Fliesstext davor oder danach."""


def _call_ollama(prompt: str, *, model: str, base_url: str, timeout: float) -> tuple[str | None, str | None]:
    """Gibt (rohtext, fehler) zurueck -- best effort, kein format=json
    erzwungen (das wuerde genau den haerteren Fall wegkonstruieren, den der
    Lauf messen soll)."""
    payload = {"model": model, "prompt": prompt, "stream": False, "keep_alive": KEEP_ALIVE}
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return None, f"Ollama-Aufruf fehlgeschlagen: {exc}"
    return body.get("response", ""), None


def _call_gemini(prompt: str, *, model: str, timeout: float) -> tuple[str | None, str | None]:
    """Gibt (rohtext, fehler) zurueck, gleiche Form wie _call_ollama --
    austauschbare Stelle fuer die Erzeugung, kein Einfluss auf Einbettungen."""
    key = _gemini_api_key()
    if not key:
        return None, "Gemini-Aufruf fehlgeschlagen: GEMINI_API_KEY fehlt in ~/.begod.env"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    url = _GEMINI_ENDPOINT.format(model=model) + f"?key={key}"
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return None, f"Gemini-Aufruf fehlgeschlagen: {exc}"
    try:
        text = body["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return None, f"Gemini-Aufruf fehlgeschlagen: unerwartete Antwortform {body!r}"
    return text, None


def _call_generate(prompt: str, *, backend: str, model: str, base_url: str,
                    timeout: float) -> tuple[str | None, str | None]:
    """Austauschbare Stelle: Erzeugung wahlweise gegen Ollama (lokal) oder
    Gemini (gehostet, schnell). Einbettungen (embeddings.py) sind davon
    nicht betroffen und bleiben lokal."""
    if backend == "gemini":
        return _call_gemini(prompt, model=model, timeout=timeout)
    if backend == "ollama":
        return _call_ollama(prompt, model=model, base_url=base_url, timeout=timeout)
    raise ValueError(f"unbekanntes backend: {backend!r} (erlaubt: ollama, gemini)")


def _call_with_retry(prompt: str, *, model: str, base_url: str, timeout: float,
                      backend: str = DEFAULT_BACKEND) -> tuple[str | None, str | None, int]:
    """Ein Werkzeugausfall (Timeout/Verbindung) darf EINMAL wiederholt werden,
    kein stilles Endlos-Retry -- sonst verschwindet die Ausfallquote, die der
    Lauf gerade messen soll. Gibt (rohtext, fehler, retry_count) zurueck."""
    raw_response, call_error = _call_generate(prompt, backend=backend, model=model, base_url=base_url, timeout=timeout)
    if call_error is None:
        return raw_response, call_error, 0
    raw_response, call_error = _call_generate(prompt, backend=backend, model=model, base_url=base_url, timeout=timeout)
    return raw_response, call_error, 1


def _parse_model_json(raw_text: str) -> dict | None:
    """Best-effort JSON-Extraktion aus einer Modellantwort: erst direkt,
    dann ```json-Fence, dann erstes {...}-Objekt im Text. Liefert None, wenn
    nichts davon ein JSON-Objekt ergibt -- das ist die eigene Kategorie
    'unbrauchbare Modellantwort', kein Fehler des Schreibpfads."""
    candidates = [raw_text.strip()]
    fence = _JSON_FENCE_RE.search(raw_text)
    if fence:
        candidates.append(fence.group(1))
    obj = _FIRST_OBJECT_RE.search(raw_text)
    if obj:
        candidates.append(obj.group(0))
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def run(*, model: str = DEFAULT_MODEL, base_url: str = DEFAULT_OLLAMA_URL,
        timeout: float = CALL_TIMEOUT, session: str | None = None,
        pieces: list[str] | None = None, backend: str = DEFAULT_BACKEND) -> dict:
    session = session or f"schreibpruefstand-{uuid.uuid4().hex[:8]}"
    raw_pieces = pieces if pieces is not None else demo_db.RAW_MATERIAL
    db_path = demo_db.build_demo_db()
    kms.DB_PATH = db_path  # Muster aus pruefstand/messlauf.py: Modulattribut umbiegen

    protocol: list[dict] = []
    started = time.perf_counter()

    for idx, raw_text in enumerate(raw_pieces):
        material_id = f"M-{idx:02d}"
        tree = _current_tree(db_path)
        prompt = build_prompt(raw_text, tree)

        call_started = time.perf_counter()
        raw_response, call_error, retry_count = _call_with_retry(
            prompt, model=model, base_url=base_url, timeout=timeout, backend=backend)
        call_seconds = time.perf_counter() - call_started

        record: dict = {
            "material_id": material_id,
            "model": model,
            "backend": backend,
            "raw_material": raw_text,
            "model_response_raw": raw_response,
            "call_error": call_error,
            "call_seconds": call_seconds,
            "retry_count": retry_count,
        }

        if call_error is not None:
            # Werkzeugausfall (Timeout/Verbindung) -- KEINE Ablehnung durch
            # eine Sperre, eigene Kategorie, damit die Auswertung beides
            # nicht vermischt.
            record.update(category="ollama_fehler", accepted=False, reason=call_error)
            protocol.append(record)
            continue

        parsed = _parse_model_json(raw_response)
        record["model_wanted"] = parsed
        if parsed is None:
            record.update(category="unbrauchbare_antwort_kein_json", accepted=False,
                          reason="Modellantwort enthaelt kein valides JSON-Objekt")
            protocol.append(record)
            continue

        call_kwargs = {k: v for k, v in parsed.items() if k in _KNOWLEDGE_ADD_FIELDS}
        try:
            system_response = kms.knowledge_add(
                **call_kwargs, actor="schreibpruefstand-C2", model=model, session=session,
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

    # WAL in die Hauptdatei einholen, sonst liest ein spaeterer mode=ro-Zugriff
    # (knowledge_lint.py in C3) einen unvollstaendigen Stand.
    checkpoint_conn = sqlite3.connect(str(db_path))
    checkpoint_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    checkpoint_conn.close()

    runtime = time.perf_counter() - started
    return {
        "model": model,
        "backend": backend,
        "session": session,
        "db_path": str(db_path),
        "runtime_seconds": runtime,
        "n_pieces": len(raw_pieces),
        "protocol": protocol,
    }


def summarize(result: dict) -> dict:
    """Werkzeugausfall (category 'ollama_fehler') und Ablehnung durch eine
    Sperre (category 'abgelehnt') sind zwei verschiedene Dinge und werden
    hier NICHT in einen gemeinsamen Topf geworfen -- ein Timeout ist keine
    Ablehnung."""
    protocol = result["protocol"]
    n = len(protocol)
    accepted = sum(1 for r in protocol if r.get("accepted"))
    by_category: dict[str, int] = {}
    gate_rejection_reasons: dict[str, int] = {}   # nur category=="abgelehnt"
    tool_failure_reasons: dict[str, int] = {}      # nur category=="ollama_fehler"
    for r in protocol:
        by_category[r["category"]] = by_category.get(r["category"], 0) + 1
        if r["category"] == "abgelehnt" and r.get("reason"):
            key = r["reason"][:80]
            gate_rejection_reasons[key] = gate_rejection_reasons.get(key, 0) + 1
        elif r["category"] == "ollama_fehler" and r.get("reason"):
            key = r["reason"][:80]
            tool_failure_reasons[key] = tool_failure_reasons.get(key, 0) + 1
    return {
        "model": result["model"],
        "n_pieces": n,
        "n_accepted": accepted,
        "n_tool_failure": by_category.get("ollama_fehler", 0),
        "n_gate_rejected": by_category.get("abgelehnt", 0),
        "acceptance_rate": accepted / n if n else None,
        "by_category": by_category,
        "gate_rejection_reasons": gate_rejection_reasons,
        "tool_failure_reasons": tool_failure_reasons,
        "runtime_seconds": result["runtime_seconds"],
    }


def _selftest() -> None:
    """Netzlos: prueft Retry-Mechanik und die Trennung Werkzeugausfall vs.
    Sperren-Ablehnung. Kein Ollama-Aufruf, kein demo_db/kms-Import-Pfad."""
    import unittest.mock as mock

    module = sys.modules[__name__]

    # 1) Erster Aufruf schlaegt fehl, zweiter klappt -> genau ein Retry, dann Erfolg.
    calls: list[int] = []

    def fake_fail_then_ok(prompt, *, model, base_url, timeout):
        calls.append(1)
        if len(calls) == 1:
            return None, "Ollama-Aufruf fehlgeschlagen: timed out"
        return '{"parent_path": "/x", "title": "t", "summary": "s"}', None

    with mock.patch.object(module, "_call_ollama", fake_fail_then_ok):
        _, err, retries = _call_with_retry("p", model="m", base_url="u", timeout=1.0)
    assert err is None and retries == 1 and len(calls) == 2, \
        f"Retry griff nicht wie erwartet: err={err!r} retries={retries} calls={len(calls)}"

    # 2) Beide Aufrufe schlagen fehl -> Ausfall bleibt Ausfall, KEIN dritter Versuch.
    calls2: list[int] = []

    def fake_always_fail(prompt, *, model, base_url, timeout):
        calls2.append(1)
        return None, "Ollama-Aufruf fehlgeschlagen: timed out"

    with mock.patch.object(module, "_call_ollama", fake_always_fail):
        _, err, retries = _call_with_retry("p", model="m", base_url="u", timeout=1.0)
    assert err is not None and retries == 1 and len(calls2) == 2, \
        f"kein stilles Endlos-Retry erwartet: err={err!r} retries={retries} calls={len(calls2)}"

    # 3) Kategorisierung in summarize(): Werkzeugausfall != Sperren-Ablehnung, beide Richtungen.
    fake_protocol = [
        {"category": "ollama_fehler", "accepted": False, "reason": "Ollama-Aufruf fehlgeschlagen: timed out"},
        {"category": "abgelehnt", "accepted": False, "reason": "Sperre: XY verletzt"},
        {"category": "angenommen", "accepted": True, "reason": None},
    ]
    summary = summarize({"model": "x", "protocol": fake_protocol, "runtime_seconds": 1.0})
    assert summary["n_tool_failure"] == 1, "Werkzeugausfall falsch gezaehlt"
    assert summary["n_gate_rejected"] == 1, "Sperren-Ablehnung falsch gezaehlt"
    assert summary["n_accepted"] == 1, "Annahme falsch gezaehlt"
    assert "Sperre: XY verletzt" in summary["gate_rejection_reasons"], "Sperren-Grund fehlt in gate_rejection_reasons"
    assert "Sperre: XY verletzt" not in summary["tool_failure_reasons"], "Sperren-Grund faelschlich als Werkzeugausfall gezaehlt"
    assert "Ollama-Aufruf fehlgeschlagen: timed out" in summary["tool_failure_reasons"], \
        "Werkzeugausfall-Grund fehlt in tool_failure_reasons"
    assert "Ollama-Aufruf fehlgeschlagen: timed out" not in summary["gate_rejection_reasons"], \
        "Werkzeugausfall faelschlich als Sperren-Ablehnung gezaehlt"

    print("selftest ok: Retry-Mechanik + Werkzeugausfall/Sperren-Trennung", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backend", choices=["ollama", "gemini"], default=DEFAULT_BACKEND)
    ap.add_argument("--model", default=None,
                     help=f"Default backend-abhaengig: ollama->{DEFAULT_MODEL}, gemini->{DEFAULT_GEMINI_MODEL}")
    ap.add_argument("--base-url", default=DEFAULT_OLLAMA_URL)
    ap.add_argument("--timeout", type=float, default=CALL_TIMEOUT)
    ap.add_argument("--out", type=str, default=None, help="Protokoll als JSON schreiben")
    ap.add_argument("--selftest", action="store_true",
                     help="Netzloser Selbsttest (Retry-Mechanik, Werkzeugausfall/Sperren-Trennung), kein Ollama-Aufruf")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return

    model = args.model or (DEFAULT_MODEL if args.backend == "ollama" else DEFAULT_GEMINI_MODEL)
    result = run(model=model, base_url=args.base_url, timeout=args.timeout, backend=args.backend)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Protokoll geschrieben: {args.out}")
    else:
        print(text)
    print(json.dumps(summarize(result), ensure_ascii=False, indent=2), file=sys.stderr)


if __name__ == "__main__":
    main()
