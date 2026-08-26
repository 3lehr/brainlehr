from __future__ import annotations
import sqlite3, sys, threading
from pathlib import Path
ROOT=Path(__file__).parents[1]; sys.path[:0]=[str(ROOT),str(ROOT/'kern')]
import knowledge_mcp_server as kms
import audit_segment
def test_anchor_keeps_legacy_count_separate(tmp_path):
 p=tmp_path/'x.db'; c=sqlite3.connect(p); c.row_factory=sqlite3.Row; c.executescript((ROOT/'schema.sql').read_text()); kms.log_access(c,'/x','read',query='q'); c.commit()
 a=audit_segment.create(c,unresolved={'model+timestamp':list(range(19)),'missing_pre':list(range(31))},actor='test',reason='cutover')
 assert a['historical_unresolved']==50
 assert audit_segment.validate(c,a['id'])['current_segment_healthy'] is True
 assert audit_segment.create(c,unresolved={'model+timestamp':list(range(19)),'missing_pre':list(range(31))},actor='test',reason='cutover')['status']=='already_recorded'
 kms.log_access(c,'/x','read',query='later'); c.commit()
 assert audit_segment.validate(c,a['id'])['profile_matches'] is True
 assert audit_segment.validate(c,a['id'])['current_segment_healthy'] is True
 c.execute("update access_log set query='tampered' where id=(select max(id) from access_log)"); c.commit()
 assert audit_segment.validate(c,a['id'])['current_segment_healthy'] is False
 c.execute("update audit_segment_anchors set unresolved_count=49 where id=?",(a['id'],)); c.commit()
 assert audit_segment.validate(c,a['id'])['anchor_matches'] is False

def test_concurrent_create_is_one_idempotent_anchor(tmp_path):
 p=tmp_path/'x.db'; setup=sqlite3.connect(p); setup.row_factory=sqlite3.Row
 setup.executescript((ROOT/'schema.sql').read_text()); kms.log_access(setup,'/x','read',query='q'); setup.commit(); setup.close()
 barrier=threading.Barrier(2); out=[]; errors=[]
 def writer():
  try:
   c=sqlite3.connect(p,timeout=2); c.row_factory=sqlite3.Row; barrier.wait()
   out.append(audit_segment.create(c,unresolved={'model+timestamp':[7],'missing_pre':[8]},actor='test',reason='cutover')); c.close()
  except Exception as exc: errors.append(exc)
 threads=[threading.Thread(target=writer) for _ in range(2)]
 [t.start() for t in threads]; [t.join() for t in threads]
 assert not errors
 assert {x['status'] for x in out} == {'recorded','already_recorded'}
 assert len({x['id'] for x in out}) == 1
