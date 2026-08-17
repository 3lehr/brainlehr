#!/usr/bin/env python3
"""Portable, local knowledge store with a small JSON-RPC tool surface."""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("BRAINLEHR_DB", "knowledge.db"))

def open_db(path=DB_PATH):
    db = sqlite3.connect(path); db.row_factory = sqlite3.Row
    db.executescript("""CREATE TABLE IF NOT EXISTS nodes (id TEXT PRIMARY KEY, path TEXT UNIQUE, title TEXT, summary TEXT, content TEXT, withdrawn INTEGER DEFAULT 0, created_at TEXT); CREATE TABLE IF NOT EXISTS relations (source_id TEXT, target_id TEXT, relation_type TEXT, UNIQUE(source_id,target_id,relation_type)); CREATE TABLE IF NOT EXISTS lessons (id TEXT PRIMARY KEY, type TEXT, description TEXT, projects TEXT, created_at TEXT);""")
    return db
def stamp(): return datetime.now(timezone.utc).isoformat()
def rows(cursor): return [dict(row) for row in cursor]
def add_node(db, title, summary, content="", path=None):
    ident = f"n-{db.execute('SELECT count(*) FROM nodes').fetchone()[0]+1:04d}"; path = path or "/" + "-".join(title.lower().split())
    db.execute("INSERT INTO nodes VALUES (?,?,?,?,?,?,?)", (ident,path,title,summary,content,0,stamp())); db.commit(); return {"id":ident,"path":path,"status":"created"}
def call(db, name, args):
    if name == "knowledge_add": return add_node(db,args["title"],args["summary"],args.get("content",""),args.get("path"))
    if name == "knowledge_search":
        q="%"+args.get("query","")+"%"; return rows(db.execute("SELECT id,path,title,summary FROM nodes WHERE NOT withdrawn AND (title LIKE ? OR summary LIKE ? OR content LIKE ?)",(q,q,q)))
    if name == "knowledge_read": return dict(db.execute("SELECT * FROM nodes WHERE id=?",(args["node_id"],)).fetchone() or {})
    if name == "knowledge_browse": return rows(db.execute("SELECT id,path,title,summary FROM nodes WHERE NOT withdrawn AND path LIKE ?",(args.get("path","/")+"%",)))
    if name == "knowledge_update": db.execute("UPDATE nodes SET summary=COALESCE(?,summary),content=COALESCE(?,content) WHERE id=?",(args.get("summary"),args.get("content"),args["node_id"])); db.commit(); return {"status":"updated"}
    if name in {"knowledge_zurueckziehen","knowledge_freigeben"}: db.execute("UPDATE nodes SET withdrawn=? WHERE id=?",(name=="knowledge_zurueckziehen",args["node_id"])); db.commit(); return {"status":name}
    if name == "knowledge_relation_add": db.execute("INSERT OR IGNORE INTO relations VALUES (?,?,?)",(args["source_id"],args["target_id"],args["relation_type"])); db.commit(); return {"status":"created"}
    if name == "knowledge_relation_list": return rows(db.execute("SELECT * FROM relations WHERE source_id=? OR target_id=?",(args["node_id"],args["node_id"])))
    if name == "lesson_record":
        ident=f"lesson-{db.execute('SELECT count(*) FROM lessons').fetchone()[0]+1:04d}"; db.execute("INSERT INTO lessons VALUES (?,?,?,?,?)",(ident,args.get("type","insight"),args["description"],json.dumps(args.get("projects",[])),stamp())); db.commit(); return {"id":ident,"status":"recorded"}
    if name == "lesson_query": return rows(db.execute("SELECT * FROM lessons"))
    if name == "knowledge_stats": return {table:db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in ("nodes","relations","lessons")}
    raise ValueError("unknown tool")
TOOLS=("knowledge_add","knowledge_search","knowledge_read","knowledge_browse","knowledge_update","knowledge_zurueckziehen","knowledge_freigeben","knowledge_relation_add","knowledge_relation_list","lesson_record","lesson_query","knowledge_stats")
def main():
    db=open_db()
    for line in sys.stdin:
        request=json.loads(line); ident=request.get("id")
        try:
            method=request.get("method")
            if method=="initialize": result={"protocolVersion":"2024-11-05","serverInfo":{"name":"brainlehr","version":"0.2.0"}}
            elif method=="tools/list": result={"tools":[{"name":tool} for tool in TOOLS]}
            elif method=="tools/call": result={"content":[{"type":"text","text":json.dumps(call(db,request["params"]["name"],request["params"].get("arguments",{})))}]}
            else: raise ValueError("unknown method")
            response={"jsonrpc":"2.0","id":ident,"result":result}
        except (KeyError,ValueError,sqlite3.Error) as error: response={"jsonrpc":"2.0","id":ident,"error":{"code":-32602,"message":str(error)}}
        print(json.dumps(response),flush=True)
if __name__=="__main__": main()
