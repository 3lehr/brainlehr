#!/usr/bin/env python3
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from knowledge_mcp_server import call, open_db

def main():
    try: prompt = json.load(sys.stdin).get("prompt", "")
    except Exception: return
    db = open_db()
    hits = call(db, "knowledge_search", {"query": prompt})[:3]
    lessons = [x for x in call(db, "lesson_query", {}) if prompt.lower() in x["description"].lower()][:3]
    text = [x["summary"] for x in hits] + [x["description"] for x in lessons]
    if text: print(json.dumps({"additionalContext": "\n".join(text)}))
if __name__ == "__main__": main()
