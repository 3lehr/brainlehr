#!/usr/bin/env python3
"""Minimaler lokaler JSON-RPC-Wissensspeicher ohne externe Abhängigkeiten."""

import json
import sqlite3
import sys
from pathlib import Path


def open_db(path="knowledge.db"):
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS nodes (id INTEGER PRIMARY KEY, title TEXT NOT NULL, summary TEXT NOT NULL)")
    return db


def add_node(db, title, summary):
    db.execute("INSERT INTO nodes(title, summary) VALUES (?, ?)", (title, summary))
    db.commit()


def search(db, query):
    needle = "%" + query + "%"
    rows = db.execute("SELECT id, title, summary FROM nodes WHERE title LIKE ? OR summary LIKE ? ORDER BY id", (needle, needle))
    return [{"id": row[0], "title": row[1], "summary": row[2]} for row in rows]


def handle(request, db):
    method = request.get("method")
    params = request.get("params", {})
    if method == "initialize":
        return {"protocolVersion": "2024-11-05", "serverInfo": {"name": "brainlehr", "version": "0.1.0"}}
    if method == "tools/list":
        return {"tools": [{"name": "knowledge_search", "description": "Durchsucht lokale Wissensknoten."}, {"name": "knowledge_add", "description": "Speichert einen lokalen Wissensknoten."}]}
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        if name == "knowledge_search":
            result = search(db, str(arguments.get("query", "")))
        elif name == "knowledge_add":
            add_node(db, str(arguments["title"]), str(arguments["summary"]))
            result = {"status": "created"}
        else:
            raise ValueError("unknown tool")
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
    raise ValueError("unknown method")


def main():
    db = open_db()
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = {"jsonrpc": "2.0", "id": request.get("id"), "result": handle(request, db)}
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32602, "message": str(error)}}
        print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
