"""Local, read-only revision dashboard for canonical impact graphs."""
from __future__ import annotations

import hashlib
import html
import json
import os
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlparse

import project_context


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                            timeout=15, check=False)
    if result.returncode:
        raise ValueError("revision is not readable in this Git project")
    return result.stdout.strip()


def _state_path(root: Path) -> Path:
    key = hashlib.sha256(str(root).encode()).hexdigest()[:16]
    base = Path(os.environ.get("BRAINLEHR_DASHBOARD_STATE_DIR", "/Volumes/daten/brainlehr-tool-cache/impact-dashboard"))
    return base / f"{key}.json"


def _short(value: str, limit: int = 42) -> str:
    return value if len(value) <= limit else "…" + value[-(limit - 1):]


def _timeline(root: Path, proposal_file: Path | None = None) -> list[dict]:
    """Use only revision/time/source; never show commit subjects or receipt reasons."""
    rows: list[dict] = []
    for line in _git(root, "log", "--format=%H%x1f%cI").splitlines():
        revision, observed_at = line.split("\x1f", 1)
        rows.append({"source": "git", "revision": revision, "observed_at": observed_at,
                     "content_hash": None})
    ack_file = root / project_context.COMMIT_ACKS
    if ack_file.is_file():
        for line in ack_file.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                rows.append({"source": "commit_ack", "revision": str(row["base"]),
                             "observed_at": str(row["observed_at"]),
                             "content_hash": str(row.get("tree_hash", ""))})
            except (KeyError, TypeError, ValueError):
                continue
    if proposal_file and proposal_file.is_file():
        for line in proposal_file.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                rows.append({"source": "feedback_proposal", "revision": str(row["revision"]),
                             "observed_at": str(row["submitted_at"]),
                             "content_hash": str(row["request_hash"]), "status": str(row["status"])})
            except (KeyError, TypeError, ValueError):
                continue
    return sorted(rows, key=lambda row: (row["observed_at"], row["source"], row["revision"]), reverse=True)


def _project_id(root: Path) -> str:
    """Stable, display-safe ID; dashboard never discovers projects implicitly."""
    return f"{root.name}-{hashlib.sha256(str(root).encode()).hexdigest()[:8]}"


def _configured_projects(root: Path) -> dict[str, Path]:
    """Only explicit local Git roots may enter the portfolio."""
    raw = [str(root), *filter(None, os.environ.get("BRAINLEHR_DASHBOARD_PROJECTS", "").split(os.pathsep))]
    result: dict[str, Path] = {}
    for item in raw:
        candidate = Path(item).expanduser().resolve()
        try:
            _git(candidate, "rev-parse", "--is-inside-work-tree")
        except ValueError:
            continue
        result.setdefault(_project_id(candidate), candidate)
    return result


_FEEDBACK_ACTIONS = {
    "recall_outcome": None, "stale_flag": None, "correction": "knowledge_update",
    "coverage_confirm": None, "project_note": "knowledge_add",
}
_FEEDBACK_FIELDS = frozenset({"action", "project_id", "target_ref", "outcome", "old_summary",
                              "new_summary", "source_ref", "reason"})


def _feedback_text(value: object, *, required: bool = False) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str) or not value or len(value) > 500 or "\n" in value or "`" in value:
        raise ValueError("feedback fields must be short single-line summaries, never raw payload")
    return value


def _validate_feedback(payload: object, *, project_id: str) -> dict:
    if not isinstance(payload, dict) or set(payload) - _FEEDBACK_FIELDS:
        raise ValueError("feedback schema is not accepted")
    if payload.get("project_id") != project_id or payload.get("action") not in _FEEDBACK_ACTIONS:
        raise ValueError("feedback project/action is not accepted")
    action = str(payload["action"])
    target = _feedback_text(payload.get("target_ref"), required=True)
    result = {"action": action, "target_ref": target,
              "outcome": _feedback_text(payload.get("outcome")),
              "old_summary": _feedback_text(payload.get("old_summary")),
              "new_summary": _feedback_text(payload.get("new_summary")),
              "source_ref": _feedback_text(payload.get("source_ref")),
              "reason": _feedback_text(payload.get("reason"), required=True)}
    if action == "recall_outcome" and result["outcome"] not in {"used", "ignored", "disproved"}:
        raise ValueError("recall outcome must be used, ignored, or disproved")
    if action != "recall_outcome" and result["outcome"]:
        raise ValueError("outcome belongs only to recall feedback")
    if action == "correction" and not (result["old_summary"] and result["new_summary"] and result["source_ref"]):
        raise ValueError("correction requires old/new/source preview")
    return {key: value for key, value in result.items() if value}


def _graph(root: Path, base: str, revision: str | None = None) -> dict:
    if revision:
        selected = _git(root, "rev-parse", "--verify", f"{revision}^{{commit}}")
        try:
            parent = _git(root, "rev-parse", f"{selected}^")
        except ValueError:  # root commit: valid empty delta, still revision-bound.
            parent = selected
        impact = project_context.impact_chain(root, parent, head=selected)
    else:
        impact = project_context.impact_chain(root, base)
    return project_context.impact_graph(root, impact, [])


def _working_overlay(root: Path, head: str) -> dict | None:
    """Non-durable view of tracked diff plus explicitly allowlisted untracked paths."""
    diff = _git(root, "diff", "--binary", "HEAD")
    changed = [line for line in _git(root, "diff", "--name-only", "HEAD").splitlines() if line]
    allowed = {item for item in os.environ.get("BRAINLEHR_AGENT_OWNED_UNTRACKED", "").split(os.pathsep) if item}
    actual_untracked = set(_git(root, "ls-files", "--others", "--exclude-standard").splitlines())
    owned = sorted(allowed & actual_untracked)
    digest = hashlib.sha256(diff.encode())
    for name in owned:
        file = root / name
        if file.is_file():
            digest.update(name.encode()); digest.update(file.read_bytes())
            changed.append(name)
    if not changed:
        return None
    changed = sorted(set(changed))
    predicted = sorted({f"tests/test_{Path(name).stem}.py" for name in changed
                        if (root / "tests" / f"test_{Path(name).stem}.py").is_file()})
    return {"base_revision": head, "overlay_hash": digest.hexdigest(), "changed_files": changed,
            "owned_untracked_files": owned, "predicted_tests": predicted}


def _overlay_graph(overlay: dict) -> dict:
    graph = {"schema": 2, "analyzer": "working-overlay-v1",
             "base_revision": overlay["base_revision"], "source_revision": overlay["base_revision"],
             "nodes": [{"id": name, "kind": "working_change", "distance": 0}
                       for name in overlay["changed_files"]], "edges": [], "evidence": [],
             "coverage_gaps": ["working overlay: static impact pending committed revision"],
             "verification": overlay["predicted_tests"]}
    graph["content_hash"] = hashlib.sha256(json.dumps(graph, sort_keys=True).encode()).hexdigest()
    return graph


def dashboard_html() -> str:
    """Small approved wireframe: compact graph, controls, timeline, selected/current."""
    return '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; connect-src 'self'; style-src 'unsafe-inline'; script-src 'self' 'unsafe-inline'">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Brainlehr impact</title>
<style>
body{font:16px system-ui;margin:0;color:#17202a;background:#f8fafc}header,main{max-width:1440px;margin:auto;padding:1rem}header{display:flex;gap:1rem;flex-wrap:wrap;align-items:center;background:#fff;border-bottom:1px solid #ccd}code{font-size:.85em}.grid{display:grid;grid-template-columns:minmax(190px,1fr) minmax(420px,2fr) minmax(240px,1fr);gap:1rem}.card{background:#fff;border:1px solid #ccd;border-radius:.5rem;padding:1rem}#graph{min-height:360px;overflow:auto}svg{width:100%;min-width:500px;height:340px}button,select,input,textarea{font:inherit;padding:.35rem}textarea{box-sizing:border-box;min-height:3.5rem;width:100%}li{margin:.35rem 0}.muted{color:#52606d}.gap{color:#9b1c1c}.node{cursor:default}.node text{font-size:12px;fill:#102a43}.node rect{fill:#d9eaf7;stroke:#486581}.edge{stroke:#627d98;stroke-width:1.4}.selected{font-weight:700}.feedback{border-top:1px solid #ccd;margin-top:1rem;padding-top:1rem}.feedback[open]{background:#f4f8fc}@media(max-width:900px){.grid{grid-template-columns:1fr 1fr}.detail{grid-column:1/-1}}@media(max-width:700px){.grid{grid-template-columns:1fr}#graph{min-height:280px}svg{min-width:420px;height:270px}header{position:sticky;top:0}.detail{grid-column:auto}}
</style><header><strong>Brainlehr evidence portfolio</strong><code id="provenance">loading</code><label>Project <select id="project"></select></label><label>Filter <input id="filter" autocomplete="off"></label><label>Revision <select id="revision"></select></label></header>
<main class="grid"><aside class="card"><h1>Portfolio</h1><ul id="portfolio"></ul><h2>Attention queue</h2><ul id="attention"></ul></aside><section class="card detail"><h1>Project detail</h1><p class="muted" id="summary"></p><label>Renderer <select id="renderer"><option value="compact">compact</option><option value="cytoscape">Cytoscape</option></select></label><div id="graph" role="img" aria-label="Revision-bound impact subgraph"></div><h2>Coverage gaps</h2><ul id="gaps"></ul></section><aside class="card"><h1>Evidence inspector</h1><h2>Selected vs current</h2><p id="compare"></p><h2>Consumers</h2><ul id="consumers"></ul><h2>Timeline</h2><ol id="timeline"></ol><button id="older" hidden>Load older</button><details class="feedback" id="feedback"><summary>Feedback (opt-in)</summary><p class="muted">Submits an append-only proposal only. An authenticated MCP reviewer must apply or reject it.</p><label>Type <select id="feedback-action"><option value="stale_flag">Flag stale / verify</option><option value="recall_outcome">Recall outcome</option><option value="correction">Propose correction</option><option value="coverage_confirm">Confirm coverage gap</option><option value="project_note">Project note / decision</option></select></label><label>Target <input id="feedback-target" maxlength="256"></label><label>Outcome <select id="feedback-outcome"><option value="used">used</option><option value="ignored">ignored</option><option value="disproved">disproved</option></select></label><label>Old summary <textarea id="feedback-old" maxlength="500"></textarea></label><label>New summary <textarea id="feedback-new" maxlength="500"></textarea></label><label>Source reference <input id="feedback-source" maxlength="500"></label><label>Reason <textarea id="feedback-reason" maxlength="500"></textarea></label><button id="feedback-submit">Preview and submit proposal</button><p id="feedback-result" role="status"></p></details></aside></main>
<script src="/cytoscape.min.js"></script>
<script>
let currentHash='', autoFollow=true;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const label=s=>s.length>42?'…'+s.slice(-41):s;
function graph(g){const q=document.querySelector('#filter').value.toLowerCase();const nodes=g.nodes.filter(n=>n.id.toLowerCase().includes(q));const ids=new Set(nodes.map(n=>n.id));if(document.querySelector('#renderer').value==='cytoscape'&&window.cytoscape){const el=document.querySelector('#graph');el.innerHTML='';cytoscape({container:el,elements:[...nodes.map(n=>({data:{id:n.id,label:label(n.id),title:n.id}})),...g.edges.filter(e=>ids.has(e.from)&&ids.has(e.to)).map((e,i)=>({data:{id:'e'+i,source:e.from,target:e.to,label:e.edge_type}}))],style:[{selector:'node',style:{label:'data(label)','font-size':11,'text-wrap':'wrap','text-max-width':120,width:135,height:38,'background-color':'#d9eaf7'}},{selector:'edge',style:{label:'data(label)','font-size':9,width:1.5,'line-color':'#627d98'}}],layout:{name:'breadthfirst',directed:true,padding:25}});return;}const w=760,h=300;let out=`<svg viewBox="0 0 ${w} ${h}" aria-label="${esc(g.source_revision)} impact graph">`;nodes.forEach((n,i)=>{const x=55+(i%4)*190,y=50+Math.floor(i/4)*90;out+=`<g class="node"><title>${esc(n.id)}</title><rect x="${x}" y="${y}" width="155" height="42" rx="5"/><text x="${x+8}" y="${y+18}">${esc(label(n.id))}</text><text x="${x+8}" y="${y+34}">${esc(n.kind)} · d${n.distance}</text></g>`});document.querySelector('#graph').innerHTML=out+'</svg>';}
let selectedProject='', feedbackCapability='';
function items(rows,append=false){const list=document.querySelector('#timeline');if(!append)list.innerHTML='';list.insertAdjacentHTML('beforeend',rows.slice(0,20).map(x=>`<li><code>${esc(x.observed_at)}</code><br>${esc(x.source)}${x.status?` · ${esc(x.status)}`:''} · <button data-revision="${esc(x.revision)}">${esc(x.revision.slice(0,12))}</button></li>`).join(''));document.querySelectorAll('[data-revision]').forEach(b=>b.onclick=()=>load(b.dataset.revision,false));}
function portfolio(rows){const sel=document.querySelector('#project');sel.innerHTML=rows.map(x=>`<option value="${esc(x.id)}" ${x.selected?'selected':''}>${esc(x.label)} · ${esc(x.revision.slice(0,12))}</option>`).join('');document.querySelector('#portfolio').innerHTML=rows.map(x=>`<li class="${x.selected?'selected':''}">${esc(x.label)}<br><code>${esc(x.revision.slice(0,12))}</code>${x.feedback_pending?` · ${x.feedback_pending} review`:''}</li>`).join('');sel.onchange=()=>load(null,true,sel.value);}
function render(data){const g=data.graph;currentHash=g.content_hash;selectedProject=data.project_id;feedbackCapability=data.feedback_capability;const o=data.working_overlay;document.querySelector('#provenance').textContent=o?`WORKING · ${o.overlay_hash.slice(0,12)} · base ${o.base_revision.slice(0,12)}`:`${data.project_label} · ${g.source_revision.slice(0,12)} · ${g.content_hash.slice(0,12)}`;document.querySelector('#summary').textContent=`${g.nodes.length} nodes · ${g.edges.length} proven edges · schema ${g.schema}`+(o?` · ${o.predicted_tests.length} predicted tests`:'');portfolio(data.portfolio);graph(g);document.querySelector('#gaps').innerHTML=(g.coverage_gaps||[]).map(x=>`<li class="gap">${esc(x)}</li>`).join('')||'<li>None reported</li>';document.querySelector('#attention').innerHTML=(g.coverage_gaps||[]).slice(0,8).map(x=>`<li class="gap">${esc(x)}</li>`).join('')||'<li>None</li>';document.querySelector('#consumers').innerHTML=g.nodes.filter(x=>(x.distance||0)>0).slice(0,12).map(x=>`<li><code>d${x.distance}</code> ${esc(x.id)}</li>`).join('')||'<li>No direct or transitive consumer evidence.</li>';document.querySelector('#compare').textContent=o?'WORKING overlay; immutable HEAD history remains below.':data.comparison.current?'Selected revision is current.':`Selected ${data.comparison.selected.slice(0,12)}; current ${data.comparison.current_revision.slice(0,12)}.`;const sel=document.querySelector('#revision');sel.innerHTML=data.timeline.map(x=>`<option value="${esc(x.revision)}" ${x.revision===g.source_revision?'selected':''}>${esc(x.source)} ${esc(x.revision.slice(0,12))}</option>`).join('');items(data.timeline);const older=document.querySelector('#older');older.hidden=!data.next_cursor;older.dataset.cursor=data.next_cursor||'';sel.onchange=()=>load(sel.value,false);}
async function load(revision,follow=true,project=selectedProject){autoFollow=follow;const q=new URLSearchParams();if(revision)q.set('revision',revision);if(project)q.set('project',project);const r=await fetch('/state?'+q);if(r.ok)render(await r.json());}
document.querySelector('#filter').oninput=()=>load(autoFollow?null:document.querySelector('#revision').value,autoFollow);document.querySelector('#renderer').onchange=()=>load(autoFollow?null:document.querySelector('#revision').value,autoFollow);document.querySelector('#older').onclick=async e=>{const r=await fetch('/timeline?cursor='+e.target.dataset.cursor+'&project='+encodeURIComponent(selectedProject));const d=await r.json();items(d.timeline,true);e.target.hidden=!d.next_cursor;e.target.dataset.cursor=d.next_cursor||''};document.querySelector('#feedback-submit').onclick=async()=>{const pick=id=>document.querySelector(id).value;const body={project_id:selectedProject,action:pick('#feedback-action'),target_ref:pick('#feedback-target'),outcome:pick('#feedback-outcome'),old_summary:pick('#feedback-old'),new_summary:pick('#feedback-new'),source_ref:pick('#feedback-source'),reason:pick('#feedback-reason')};const r=await fetch('/feedback',{method:'POST',headers:{'Content-Type':'application/json','Origin':location.origin,'X-Brainlehr-Capability':feedbackCapability},body:JSON.stringify(body)});const d=await r.json();document.querySelector('#feedback-result').textContent=r.ok?`Submitted ${d.proposal_id}: ${d.status}; ${d.effect}. ${d.mcp_handoff||'Manual authenticated MCP review required.'}`:`Rejected: ${d.error}`;if(r.ok)load(null,true)};setInterval(()=>load(autoFollow?null:document.querySelector('#revision').value,autoFollow),1200);load();
</script></html>'''


class ImpactDashboard:
    def __init__(self, project_root: str | Path, base: str, *, host: str = "127.0.0.1",
                 port: int = 0, graph_builder: Callable[[Path, str, str | None], dict] = _graph):
        if host != "127.0.0.1":
            raise ValueError("dashboard binds only 127.0.0.1")
        self.root = project_context.project_root(project_root)
        self.base, self.host, self.port, self.graph_builder = base, host, port, graph_builder
        self.projects = _configured_projects(self.root)
        self.default_project_id = _project_id(self.root)
        self.state_path = _state_path(self.root)
        self.feedback_capability = uuid.uuid4().hex
        self._feedback_lock = threading.Lock()
        self._last_hash = ""
        self._last_key: tuple[str, ...] | None = None
        self._last_refresh = 0.0
        self._graphs: dict[tuple[str, ...], dict] = {}
        self._cached_timeline: list[dict] = []
        self._timeline_key: tuple[str, str, int] | None = None
        self.server: ThreadingHTTPServer | None = None
        self._serving = False

    def _write_instance(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        if self.state_path.exists():
            try:
                row = json.loads(self.state_path.read_text(encoding="utf-8"))
                os.kill(int(row["pid"]), 0)
                raise RuntimeError("dashboard instance already running for this project")
            except ProcessLookupError:
                pass
            except (KeyError, TypeError, ValueError):
                pass
        self.state_path.write_text(json.dumps({"pid": os.getpid(), "host": self.host, "port": self.port,
                                                "project": str(self.root)}, sort_keys=True), encoding="utf-8")

    def _project(self, project_id: str | None) -> tuple[str, Path]:
        project_id = project_id or self.default_project_id
        root = self.projects.get(project_id)
        if root is None:
            raise ValueError("project is not in the explicit dashboard allowlist")
        return project_id, root

    def _base_for(self, root: Path) -> str:
        if root == self.root:
            return self.base
        try:
            return _git(root, "rev-parse", "HEAD^")
        except ValueError:
            return _git(root, "rev-parse", "HEAD")

    def _feedback_path(self, root: Path) -> Path:
        return _state_path(root).with_suffix(".feedback.jsonl")

    def _portfolio(self, selected_id: str) -> list[dict]:
        rows = []
        for project_id, root in self.projects.items():
            head = _git(root, "rev-parse", "HEAD")
            rows.append({"id": project_id, "label": root.name, "revision": head,
                         "selected": project_id == selected_id,
                         "feedback_pending": sum(1 for row in _timeline(root, self._feedback_path(root))
                                                 if row["source"] == "feedback_proposal" and row.get("status") == "pending_review")})
        return sorted(rows, key=lambda row: row["label"])

    def state(self, revision: str | None = None, required_hash: str | None = None,
              project_id: str | None = None) -> dict:
        selected_id, root = self._project(project_id)
        head = _git(root, "rev-parse", "HEAD")
        overlay = _working_overlay(root, head) if revision is None else None
        if overlay:
            selected, key, graph = head, (str(root), "WORKING", overlay["overlay_hash"]), _overlay_graph(overlay)
        else:
            selected = _git(self.root, "rev-parse", "--verify", f"{revision or head}^{{commit}}")
            key = (str(root), selected, self._base_for(root))
            graph = self._graphs.get(key)
            if graph is None:
                graph = self.graph_builder(root, self._base_for(root), revision)
                self._graphs[key] = graph
        if required_hash and required_hash != graph["content_hash"]:
            return {"status": "stale", "current_hash": graph["content_hash"]}
        now = time.monotonic()
        if key == self._last_key and graph["content_hash"] != self._last_hash and now - self._last_refresh < 0.2:
            return {"status": "debounced", "current_hash": self._last_hash}
        self._last_hash, self._last_key, self._last_refresh = graph["content_hash"], key, now
        ack = root / project_context.COMMIT_ACKS
        proposal_file = self._feedback_path(root)
        timeline_key = (str(root), head, max(ack.stat().st_mtime_ns if ack.exists() else 0,
                                             proposal_file.stat().st_mtime_ns if proposal_file.exists() else 0))
        if timeline_key != self._timeline_key:
            self._cached_timeline, self._timeline_key = _timeline(root, proposal_file), timeline_key
        return {"status": "current", "project_id": selected_id, "project_label": root.name,
                "portfolio": self._portfolio(selected_id), "feedback_capability": self.feedback_capability,
                "graph": graph, "timeline": self._cached_timeline[:100],
                "next_cursor": 100 if len(self._cached_timeline) > 100 else None,
                "comparison": {"selected": graph["source_revision"], "current_revision": head,
                               "current": graph["source_revision"] == head}, "working_overlay": overlay}

    def timeline_page(self, cursor: int, project_id: str | None = None) -> dict:
        _selected_id, root = self._project(project_id)
        head = _git(root, "rev-parse", "HEAD")
        ack = root / project_context.COMMIT_ACKS
        proposal_file = self._feedback_path(root)
        key = (str(root), head, max(ack.stat().st_mtime_ns if ack.exists() else 0,
                                    proposal_file.stat().st_mtime_ns if proposal_file.exists() else 0))
        if key != self._timeline_key:
            self._cached_timeline, self._timeline_key = _timeline(root, self._feedback_path(root)), key
        page = self._cached_timeline[cursor:cursor + 100]
        next_cursor = cursor + 100 if cursor + 100 < len(self._cached_timeline) else None
        return {"status": "current", "timeline": page, "next_cursor": next_cursor}

    def submit_feedback(self, payload: object, *, origin: str, capability: str) -> dict:
        expected_origin = f"http://127.0.0.1:{self.port}"
        if origin != expected_origin or capability != self.feedback_capability:
            raise PermissionError("same-origin capability check failed")
        project_id = payload.get("project_id") if isinstance(payload, dict) else None
        selected_id, root = self._project(project_id if isinstance(project_id, str) else None)
        request = _validate_feedback(payload, project_id=selected_id)
        submitted_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        request_hash = hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        proposal = {"proposal_id": f"feedback-{request_hash[:12]}", "project_id": selected_id,
                    "revision": _git(root, "rev-parse", "HEAD"), "submitted_at": submitted_at,
                    "request_hash": request_hash, "status": "pending_review", "request": request,
                    "mcp_handoff": _FEEDBACK_ACTIONS[request["action"]],
                    "role_capability": "not_attested_by_dashboard", "effect": "no canonical write"}
        target = self._feedback_path(root)
        with self._feedback_lock:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(proposal, sort_keys=True, separators=(",", ":")) + "\n")
                handle.flush(); os.fsync(handle.fileno())
        return {key: proposal[key] for key in ("proposal_id", "status", "revision", "request_hash",
                                                 "mcp_handoff", "role_capability", "effect")}

    def start(self) -> "ImpactDashboard":
        # Build before accepting requests: clients never see a half-ready graph.
        self.state()
        dashboard = self
        class Handler(BaseHTTPRequestHandler):
            def _json(self, status: int, body: dict) -> None:
                encoded = json.dumps(body, sort_keys=True).encode()
                self.send_response(status); self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(encoded)))
                self.end_headers(); self.wfile.write(encoded)

            def do_GET(self):  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path == "/":
                    body = dashboard_html().encode()
                    self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                elif parsed.path == "/cytoscape.min.js":
                    asset = Path(os.environ.get("BRAINLEHR_CYTOSCAPE_ASSET", "/Volumes/daten/brainlehr-tool-cache/node_modules/cytoscape/dist/cytoscape.min.js"))
                    if not asset.is_file(): self.send_error(404); return
                    body = asset.read_bytes(); self.send_response(200); self.send_header("Content-Type", "application/javascript")
                elif parsed.path == "/state":
                    query = parse_qs(parsed.query)
                    body = json.dumps(dashboard.state(query.get("revision", [None])[0], query.get("hash", [None])[0],
                                                      query.get("project", [None])[0]),
                                      sort_keys=True).encode()
                    self.send_response(409 if b'"status": "stale"' in body else 200)
                    self.send_header("Content-Type", "application/json")
                elif parsed.path == "/timeline":
                    query = parse_qs(parsed.query)
                    try: cursor = max(0, int(query.get("cursor", ["0"])[0]))
                    except ValueError: self.send_error(400); return
                    body = json.dumps(dashboard.timeline_page(cursor, query.get("project", [None])[0]), sort_keys=True).encode()
                    self.send_response(200); self.send_header("Content-Type", "application/json")
                else:
                    self.send_error(404); return
                self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

            def do_POST(self):  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path != "/feedback": self.send_error(404); return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 2 <= length <= 4096: raise ValueError("feedback body size is not accepted")
                    payload = json.loads(self.rfile.read(length))
                    result = dashboard.submit_feedback(payload, origin=self.headers.get("Origin", ""),
                                                       capability=self.headers.get("X-Brainlehr-Capability", ""))
                except PermissionError as error:
                    self._json(403, {"status": "rejected", "error": str(error)}); return
                except (ValueError, TypeError, json.JSONDecodeError) as error:
                    self._json(400, {"status": "rejected", "error": str(error)}); return
                self._json(202, result)

            def log_message(self, *_args): pass
        self.server = ThreadingHTTPServer((self.host, self.port), Handler)
        self.port = int(self.server.server_address[1])
        self._write_instance()
        return self

    def serve_forever(self) -> None:
        if self.server is None: self.start()
        assert self.server is not None
        self._serving = True
        try: self.server.serve_forever(poll_interval=0.2)
        finally: self.shutdown()

    def shutdown(self) -> None:
        if self.server:
            if self._serving: self.server.shutdown()
            self.server.server_close(); self.server = None; self._serving = False
        try:
            if self.state_path.exists() and json.loads(self.state_path.read_text())["pid"] == os.getpid():
                self.state_path.unlink(missing_ok=True)
        except (KeyError, TypeError, ValueError, OSError):
            pass


def start_for_mode(mode: str, project_root: str | Path, base: str, **kwargs) -> ImpactDashboard | None:
    """Client-neutral mode gate; callers decide lifecycle, this module never starts for knowledge."""
    if mode == "knowledge": return None
    if mode not in {"code", "mixed"}: raise ValueError("dashboard mode must be knowledge, code, or mixed")
    return ImpactDashboard(project_root, base, **kwargs).start()
