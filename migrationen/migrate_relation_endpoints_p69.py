#!/usr/bin/env python3
"""P69 explicit copy-first migration; never runs from normal server startup."""
from __future__ import annotations
import argparse, hashlib, sqlite3
from datetime import UTC, datetime
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'kern'))
from relation_endpoints import migrate
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def backup(db, out):
 out.mkdir(parents=True,exist_ok=True); p=out/f"{db.stem}.p69-pre-{datetime.now(UTC):%Y%m%dT%H%M%SZ}{db.suffix}"
 s=sqlite3.connect(f'file:{db}?mode=ro',uri=True); d=sqlite3.connect(p); s.backup(d); d.close(); s.close(); return p,sha(p)
def main(argv=None):
 p=argparse.ArgumentParser(); p.add_argument('--db',type=Path,required=True); p.add_argument('--apply',action='store_true'); p.add_argument('--backup-dir',type=Path); a=p.parse_args(argv)
 if a.apply and not a.backup_dir: p.error('--apply requires --backup-dir')
 c=sqlite3.connect(a.db); c.row_factory=sqlite3.Row
 before=c.execute('select count(*) from knowledge_relations').fetchone()[0]
 if not a.apply: print({'relations':before,'apply_required':True}); return 0
 b,h=backup(a.db,a.backup_dir); result=migrate(c); after=c.execute('select count(*) from knowledge_relations').fetchone()[0]
 print({'backup_sha256':h,'before':before,'after':after,**result,'fk':len(c.execute('pragma foreign_key_check').fetchall())}); return 0
if __name__=='__main__': raise SystemExit(main())
