#!/usr/bin/env python3
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from knowledge_mcp_server import knowledge_search, lesson_query

def main():
    try: prompt = json.load(sys.stdin).get("prompt", "")
    except Exception: return
    hits = knowledge_search(prompt).get("results", [])[:3]
    lessons = lesson_query(query=prompt).get("results", [])[:3]
    text = [x["summary"] for x in hits] + [x["description"] for x in lessons]
    if text: print(json.dumps({"additionalContext": "\n".join(text)}))
if __name__ == "__main__": main()
