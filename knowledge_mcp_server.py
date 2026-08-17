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
    db.executescript("""CREATE TABLE IF NOT EXISTS nodes (id TEXT PRIMARY KEY, path TEXT UNIQUE, title TEXT, summary TEXT, content TEXT, withdrawn INTEGER DEFAULT 0, created_at TEXT); CREATE TABLE IF NOT EXISTS relations (id INTEGER PRIMARY KEY, source_id TEXT, target_id TEXT, relation_type TEXT, UNIQUE(source_id,target_id,relation_type)); CREATE TABLE IF NOT EXISTS lessons (id TEXT PRIMARY KEY, type TEXT, description TEXT, projects TEXT, created_at TEXT); CREATE TABLE IF NOT EXISTS assumptions (id TEXT PRIMARY KEY, statement TEXT, cost TEXT, evidence TEXT, status TEXT, created_at TEXT); CREATE TABLE IF NOT EXISTS approvals (node_id TEXT PRIMARY KEY, level TEXT, note TEXT);""")
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
    if name == "freigabe_setzen": db.execute("INSERT OR REPLACE INTO approvals VALUES (?,?,?)",(args["node_id"],args["stufe"],args.get("note",""))); db.commit(); return {"status":"approved"}
    if name == "kettenerklaerung_erklaeren": return {"status":"recorded","reason":args["grund"]}
    if name == "kurator_lauf": return {"withdrawn":db.execute("SELECT count(*) FROM nodes WHERE withdrawn").fetchone()[0],"empty":db.execute("SELECT count(*) FROM nodes WHERE trim(summary)='' ").fetchone()[0]}
    if name == "knowledge_relation_add": db.execute("INSERT OR IGNORE INTO relations(source_id,target_id,relation_type) VALUES (?,?,?)",(args["source_id"],args["target_id"],args["relation_type"])); db.commit(); return {"id":db.execute("SELECT id FROM relations WHERE source_id=? AND target_id=? AND relation_type=?",(args["source_id"],args["target_id"],args["relation_type"])).fetchone()[0],"status":"created"}
    if name == "knowledge_relation_list": return rows(db.execute("SELECT * FROM relations WHERE source_id=? OR target_id=?",(args["node_id"],args["node_id"])))
    if name == "knowledge_relation_update": db.execute("UPDATE relations SET relation_type=? WHERE id=?",(args["relation_type"],args["relation_id"])); db.commit(); return {"status":"updated"}
    if name == "knowledge_relation_remove": db.execute("DELETE FROM relations WHERE id=?",(args["relation_id"],)); db.commit(); return {"status":"removed"}
    if name == "annahme_erfassen":
        ident=f"assumption-{db.execute('SELECT count(*) FROM assumptions').fetchone()[0]+1:04d}"; db.execute("INSERT INTO assumptions VALUES (?,?,?,?,?,?)",(ident,args["annahme"],args["kosten_wenn_falsch"],args.get("beleg",""),"open",stamp())); db.commit(); return {"id":ident,"status":"open"}
    if name == "annahme_entscheiden": db.execute("UPDATE assumptions SET status=?,evidence=? WHERE id=?",(args["status"],args["beleg"],args["annahme_id"])); db.commit(); return {"status":"updated"}
    if name == "annahme_liste": return rows(db.execute("SELECT * FROM assumptions WHERE status=?",(args.get("status","open"),)))
    if name == "lesson_record":
        ident=f"lesson-{db.execute('SELECT count(*) FROM lessons').fetchone()[0]+1:04d}"; db.execute("INSERT INTO lessons VALUES (?,?,?,?,?)",(ident,args.get("type","insight"),args["description"],json.dumps(args.get("projects",[])),stamp())); db.commit(); return {"id":ident,"status":"recorded"}
    if name == "lesson_query": return rows(db.execute("SELECT * FROM lessons"))
    if name == "knowledge_stats": return {table:db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in ("nodes","relations","lessons")}
    raise ValueError("unknown tool")
TOOLS=("knowledge_add","knowledge_search","knowledge_read","knowledge_browse","knowledge_update","freigabe_setzen","knowledge_zurueckziehen","knowledge_freigeben","kettenerklaerung_erklaeren","kurator_lauf","knowledge_relation_add","knowledge_relation_list","knowledge_relation_update","knowledge_relation_remove","annahme_erfassen","annahme_entscheiden","annahme_liste","lesson_record","lesson_query","knowledge_stats")
def main():
    db=open_db()
    for line in sys.stdin:
        request=json.loads(line); ident=request.get("id")
        try:
            method=request.get("method")
            if method=="initialize": result={"protocolVersion":"2024-11-05","serverInfo":{"name":"brainlehr","version":"0.2.0"}}
            elif method=="tools/list": result={"tools":[{"name":tool,"inputSchema":{"type":"object","additionalProperties":True}} for tool in TOOLS]}
            elif method=="tools/call": result={"content":[{"type":"text","text":json.dumps(call(db,request["params"]["name"],request["params"].get("arguments",{})))}]}
            else: raise ValueError("unknown method")
            response={"jsonrpc":"2.0","id":ident,"result":result}
        except (KeyError,ValueError,sqlite3.Error) as error: response={"jsonrpc":"2.0","id":ident,"error":{"code":-32602,"message":str(error)}}
        print(json.dumps(response),flush=True)
if __name__=="__main__": main()
