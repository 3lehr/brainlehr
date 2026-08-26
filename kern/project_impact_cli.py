"""Render a revision-bound impact graph from the same typed JSON used by MCP."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

try:
    import project_context
    from evidence_projections import metroviz_projection, otel_trace_projection
except ModuleNotFoundError:  # installed wheel keeps core modules in ./kern
    sys.path.insert(0, str(Path(__file__).resolve().parent / "kern"))
    import project_context
    from evidence_projections import metroviz_projection, otel_trace_projection


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--format", choices=("json", "mermaid", "cytoscape", "metroviz", "otel"), default="json")
    parser.add_argument("--output", help="write a Cytoscape HTML artifact and its local asset")
    parser.add_argument("--trace", type=Path, help="sanitized OTLP-derived trace JSON for --format otel")
    parser.add_argument("--tree-hash", help="working-tree hash bound to --trace for --format otel")
    args = parser.parse_args()
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
