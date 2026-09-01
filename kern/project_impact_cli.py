"""Render a revision-bound impact graph from the same typed JSON used by MCP."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import webbrowser
from pathlib import Path

try:
    import project_context
    from evidence_projections import metroviz_projection, otel_trace_projection
    from impact_dashboard import start_for_mode
except ModuleNotFoundError:  # installed wheel keeps core modules in ./kern
    sys.path.insert(0, str(Path(__file__).resolve().parent / "kern"))
    import project_context
    from evidence_projections import metroviz_projection, otel_trace_projection
    from impact_dashboard import start_for_mode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--base")
    parser.add_argument("--format", choices=("json", "mermaid", "cytoscape", "metroviz", "otel"), default="json")
    parser.add_argument("--output", help="write a Cytoscape HTML artifact and its local asset")
    parser.add_argument("--trace", type=Path, help="sanitized OTLP-derived trace JSON for --format otel")
    parser.add_argument("--tree-hash", help="working-tree hash bound to --trace for --format otel")
    parser.add_argument("--serve", action="store_true", help="serve a local read-only dashboard")
    parser.add_argument("--watch", action="store_true", help="poll graph hash in the local dashboard")
    parser.add_argument("--open", action="store_true", help="open the local dashboard")
    parser.add_argument("--mode", default="code", choices=("knowledge", "code", "mixed"))
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    if args.serve:
        root = project_context.project_root(args.project_root)
        base = args.base or project_context._git(root, "rev-parse", "HEAD^")
        dashboard = start_for_mode(args.mode, root, base, port=args.port)
        if dashboard is None:
            print(json.dumps({"status": "disabled", "mode": "knowledge"}, sort_keys=True)); return 0
        if args.open: webbrowser.open(f"http://127.0.0.1:{dashboard.port}/")
        print(json.dumps({"status": "serving", "url": f"http://127.0.0.1:{dashboard.port}/", "watch": args.watch}, sort_keys=True))
        dashboard.serve_forever(); return 0
    if not args.base:
        parser.error("--base is required unless --serve is used")
    impact = project_context.impact_chain(args.project_root, args.base)
    graph = project_context.impact_graph(args.project_root, impact, [])
    if args.output and args.format != "cytoscape":
        parser.error("--output is only supported for --format cytoscape")
    if args.format == "otel":
        if not args.trace or not args.tree_hash:
            parser.error("--format otel requires --trace and --tree-hash")
        trace = json.loads(args.trace.read_text(encoding="utf-8"))
        print(json.dumps(otel_trace_projection(trace, source_revision=graph["source_revision"],
                                                tree_hash=args.tree_hash, graph=graph),
                         ensure_ascii=False, sort_keys=True))
    elif args.format == "metroviz":
        print(json.dumps(metroviz_projection(graph), ensure_ascii=False, sort_keys=True))
    elif args.format == "mermaid":
        print(project_context.impact_mermaid(graph), end="")
    elif args.format == "cytoscape":
        rendered = project_context.impact_cytoscape_html(graph)
        if not args.output:
            print(rendered, end="")
            return 0
        destination = Path(args.output).resolve()
        source = Path(os.environ.get(
            "BRAINLEHR_CYTOSCAPE_ASSET",
            "/Volumes/daten/brainlehr-tool-cache/node_modules/cytoscape/dist/cytoscape.min.js",
        ))
        if not source.is_file():
            parser.error("local Cytoscape asset is unavailable; no artifact was written")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
        shutil.copyfile(source, destination.with_name("cytoscape.min.js"))
        print(json.dumps({"artifact": str(destination), "asset": "cytoscape.min.js",
                          "source_revision": graph["source_revision"],
                          "content_hash": graph["content_hash"]}, sort_keys=True))
    else:
        print(json.dumps(graph, ensure_ascii=False, sort_keys=True))
    return 0
