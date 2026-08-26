"""P70: explicitly bounded healthy audit segment after unresolved legacy."""
from __future__ import annotations
import hashlib, json, sqlite3, uuid
from knowledge_mcp_server import compute_ketten_hash, now_iso

def _profile(conn, through_id=None):
    sql="SELECT id,ketten_hash FROM access_log WHERE ketten_hash IS NOT NULL"; args=()
    if through_id is not None: sql += " AND id<=?"; args=(through_id,)
    rows=conn.execute(sql+" ORDER BY id",args).fetchall()
    return hashlib.sha256("\n".join(f"{r[0]}|{r[1]}" for r in rows).encode()).hexdigest()

def _anchor_hash(*, tail_id, tail_hash, count, classes, manifest, profile, created_at, actor, reason):
    """Detect accidental/local anchor-row alteration; it is not an external TSA."""
    payload = {
        "actor": actor, "classes": classes, "count": count,
        "created_at": created_at, "manifest": manifest, "profile": profile,
        "reason": reason, "tail_hash": tail_hash, "tail_id": tail_id,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def create(conn, *, unresolved: dict[str,list[int]], actor: str, reason: str):
    if not actor or not reason: raise ValueError("actor and reason required")
    own_tx = not conn.in_transaction
    if own_tx:
        conn.execute("BEGIN IMMEDIATE")
    try:
        tail=conn.execute("SELECT id,ketten_hash FROM access_log WHERE ketten_hash IS NOT NULL ORDER BY id DESC LIMIT 1").fetchone()
        if not tail: raise ValueError("no chained tail")
        manifest=hashlib.sha256(json.dumps(unresolved,sort_keys=True,separators=(',',':')).encode()).hexdigest(); count=sum(map(len,unresolved.values()))
        old=conn.execute("SELECT * FROM audit_segment_anchors WHERE previous_tail_id=? AND previous_tail_hash=? AND unresolved_manifest_hash=?",(tail[0],tail[1],manifest)).fetchone()
        if old:
            if own_tx: conn.commit()
            return {"status":"already_recorded","id":old[0]}
        classes=json.dumps({k:len(v) for k,v in unresolved.items()},sort_keys=True,separators=(',',':'))
        profile = _profile(conn, tail[0]); created = now_iso()
        aid=str(uuid.uuid4())
        digest = _anchor_hash(tail_id=tail[0], tail_hash=tail[1], count=count, classes=classes,
                              manifest=manifest, profile=profile, created_at=created,
                              actor=actor, reason=reason)
        conn.execute("INSERT INTO audit_segment_anchors VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                     (aid,tail[0],tail[1],count,classes,manifest,profile,created,actor,reason,digest))
        if own_tx: conn.commit()
        return {"status":"recorded","id":aid,"historical_unresolved":count}
    except Exception:
        if own_tx: conn.rollback()
        raise
def validate(conn, anchor_id):
    a=conn.execute("SELECT * FROM audit_segment_anchors WHERE id=?",(anchor_id,)).fetchone()
    if not a: raise ValueError("anchor missing")
    anchor_digest = _anchor_hash(tail_id=a[1], tail_hash=a[2], count=a[3], classes=a[4],
                                 manifest=a[5], profile=a[6], created_at=a[7], actor=a[8], reason=a[9])
    classes=json.loads(a[4])
    tail = conn.execute("SELECT ketten_hash FROM access_log WHERE id=?", (a[1],)).fetchone()
    tail_matches = tail is not None and tail[0] == a[2]
    manifest_count_matches = sum(classes.values()) == a[3]
    prev=a[2]; healthy=tail_matches and manifest_count_matches and anchor_digest == a[10]; checked=0
    for r in conn.execute("SELECT id,node_path,action,query,project_id,actor,model,session,status,timestamp,zeilen_hash,ketten_hash FROM access_log WHERE id>? AND ketten_hash IS NOT NULL ORDER BY id",(a[1],)):
        expected=compute_ketten_hash(prev,node_path=r[1],action=r[2],query=r[3],project_id=r[4],actor=r[5],model=r[6],session=r[7],status=r[8],timestamp=r[9],zeilen_hash=r[10]); checked+=1
        if expected!=r[11]: healthy=False; break
        prev=r[11]
    return {"historical_unresolved":a[3],"historical_classes":classes,"current_segment_healthy":healthy,
            "checked":checked,"profile_matches":_profile(conn,a[1])==a[6],
            "tail_matches":tail_matches,"manifest_count_matches":manifest_count_matches,
            "anchor_matches":anchor_digest == a[10]}
