#!/usr/bin/env python3
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from knowledge_mcp_server import call, open_db

def main():
    try: text = json.load(sys.stdin).get("learning", "").strip()
    except Exception: return
    if text: call(open_db(), "lesson_record", {"type": "insight", "description": text, "projects": []})
if __name__ == "__main__": main()
