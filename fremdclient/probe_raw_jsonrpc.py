#!/usr/bin/env python3
"""Fremdclient-Probe ohne unser eigenes SDK/Wrapper: spricht rohes
JSON-RPC 2.0 ueber stdio mit knowledge_mcp_server.py, genau wie ein
MCP-Client (z.B. LM Studio) es tun wuerde -- kein Import des Servermoduls,
kein Umweg ueber unsere eigenen Python-Handler.

Laeuft NUR gegen BEGOD_KNOWLEDGE_DB (Testkopie). Bricht ab, wenn die
Variable fehlt oder auf die echte brainlehr.db zeigt.
"""

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
import json
import os
import subprocess
import sys
from pathlib import Path

FREMDCLIENT = Path(__file__).parent
SHARED_KNOWLEDGE = FREMDCLIENT.parent
REAL_DB = SHARED_KNOWLEDGE / "brainlehr.db"
SERVER = SHARED_KNOWLEDGE / "knowledge_mcp_server.py"


def guard_env() -> Path:
    db = os.environ.get("BEGOD_KNOWLEDGE_DB")
    if not db:
        sys.exit("BEGOD_KNOWLEDGE_DB nicht gesetzt -- Probe abgebrochen.")
    db_path = Path(db).resolve()
    if db_path == REAL_DB.resolve():
        sys.exit(f"BEGOD_KNOWLEDGE_DB zeigt auf die echte Datenbank ({REAL_DB}) -- Probe abgebrochen.")
    return db_path


def send(proc, obj):
    proc.stdin.write(json.dumps(obj) + "\n")
    proc.stdin.flush()


def recv(proc):
    line = proc.stdout.readline()
    return json.loads(line) if line.strip() else None


def main():
    db_path = guard_env()
    env = dict(os.environ)  # BEGOD_KNOWLEDGE_DB bereits gesetzt (Vorbedingung)

    proc = subprocess.Popen(
        [sys.executable, str(SERVER)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env=env,
    )

    findings = {}

    send(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    findings["initialize"] = recv(proc)

    send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools_resp = recv(proc)
    tool_names = sorted(t["name"] for t in tools_resp["result"]["tools"])
    findings["tools_list_count"] = len(tool_names)
    findings["tools_list_names"] = tool_names
    ka = next(t for t in tools_resp["result"]["tools"] if t["name"] == "knowledge_add")
    findings["knowledge_add_required"] = ka["inputSchema"].get("required")
    findings["knowledge_add_has_source_in_schema_required"] = "source" in ka["inputSchema"].get("required", [])

    # Pflichtfeld source fehlt (nicht im JSON-Schema "required", nur zur Laufzeit geprueft)
    send(proc, {
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "knowledge_add", "arguments": {
            "parent_path": "/", "title": "fremdclient-probe ohne source", "summary": "s",
        }},
    })
    resp = recv(proc)
    body = json.loads(resp["result"]["content"][0]["text"])
    findings["missing_source_rejected"] = "error" in body and "source" in body.get("error", "")
    findings["missing_source_error_text"] = body.get("error")

    # Gueltiger Schreibvorgang OHNE actor/model/session (fremder Client setzt sie nicht)
    send(proc, {
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "knowledge_add", "arguments": {
            "parent_path": "/", "title": "fremdclient-probe raw-jsonrpc",
            "summary": "Testeintrag der raw-JSONRPC-Probe, keine actor/model/session-Angabe.",
            "source": "fremdclient/probe_raw_jsonrpc.py (raw JSON-RPC stdio, kein eigenes SDK)",
        }},
    })
    resp = recv(proc)
    body = json.loads(resp["result"]["content"][0]["text"])
    findings["write_result"] = body

    proc.stdin.close()
    proc.terminate()
    proc.wait(timeout=5)

    print(json.dumps(findings, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
