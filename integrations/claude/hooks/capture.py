#!/usr/bin/env python3
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from knowledge_mcp_server import lesson_record

def main():
    try: text = json.load(sys.stdin).get("learning", "").strip()
    except Exception: return
    if text: lesson_record("insight", text, projects=[], anlass="hook")
if __name__ == "__main__": main()
