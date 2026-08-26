from __future__ import annotations
import sqlite3
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "kern")]
import relation_endpoints as endpoints


def _db(tmp_path):
    c = sqlite3.connect(tmp_path / "p69.db"); c.row_factory = sqlite3.Row
    c.executescript((ROOT / "schema.sql").read_text())
    c.execute("insert into knowledge_nodes(id,path,title,summary,source,norm_entscheidung,norm_entschieden_von,norm_entschieden_grund,norm_entschieden_am,anlass) values ('n1','/n1','n1','s','test','keine_norm','test','fixture','2026-01-01T00:00:00Z','skript')")
    c.execute("insert into lessons_learned(id,type,description,first_seen,last_seen) values ('L-000001','insight','x','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')")
    return c


def test_typed_endpoint_triggers_accept_valid_and_reject_invalid(tmp_path):
    c = _db(tmp_path)
    c.execute("insert into knowledge_relations(id,source_path,target_path,source_kind,target_kind,relation_type,created_at,updated_at) values ('r1','/n1','L-000001','node','lesson','derived','x','x')")
    c.execute("insert into knowledge_relations(id,source_path,target_path,source_kind,target_kind,relation_type,created_at,updated_at) values ('r2','L-000001','files/a.py','lesson','file','mentions','x','x')")
    with pytest.raises(sqlite3.IntegrityError): c.execute("insert into knowledge_relations(id,source_path,target_path,source_kind,target_kind,relation_type,created_at,updated_at) values ('bad','/missing','/n1','node','node','x','x','x')")
    with pytest.raises(sqlite3.IntegrityError): c.execute("insert into knowledge_relations(id,source_path,target_path,source_kind,target_kind,relation_type,created_at,updated_at) values ('bad2','L-000001','../secret','lesson','file','x','x','x')")
    installed = {row[0] for row in c.execute("select name from sqlite_master where type='trigger'")}
    assert {'knowledge_relations_endpoints_bi', 'knowledge_relations_endpoints_bu'} <= installed


def test_legacy_migration_preserves_ids_and_is_idempotent(tmp_path):
    c = _db(tmp_path)
    c.execute("drop table knowledge_relations")
    c.execute("create table knowledge_relations(id text primary key,source_path text,target_path text,relation_type text,confidence real,weight real,evidence text,source text,creator text,model text,session text,created_at text,updated_at text,hinsicht text,unique(source_path,target_path,relation_type),foreign key(source_path) references knowledge_nodes(path),foreign key(target_path) references knowledge_nodes(path))")
    c.execute("insert into knowledge_relations values ('a','/n1','L-000001','abgeleitet_von',1,1,null,null,null,null,null,'x','x',null)")
    c.execute("insert into knowledge_relations values ('b','L-000001','files/a.py','lesson_mentions_file',1,1,null,null,null,null,null,'x','x',null)")
    c.commit()
    result = endpoints.migrate(c)
    assert result == {'node_node': 0, 'node_lesson': 1, 'lesson_file': 1}
    assert c.execute('pragma foreign_key_check').fetchall() == []
    assert tuple(c.execute("select source_kind,target_kind from knowledge_relations where id='b'").fetchone()) == ('lesson','file')
    assert endpoints.migrate(c)['unchanged'] == 1
