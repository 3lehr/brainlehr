import tempfile
from knowledge_mcp_server import add_node, call, open_db
def test_governance_lifecycle():
 with tempfile.NamedTemporaryFile(suffix='.sqlite') as f:
  db=open_db(f.name); n=add_node(db,'Synthetic','Synthetic')
  assert call(db,'freigabe_setzen',{'node_id':n['id'],'stufe':'public'})['status']=='approved'
  call(db,'knowledge_zurueckziehen',{'node_id':n['id']}); assert call(db,'kurator_lauf',{})['withdrawn']==1
  assert call(db,'knowledge_freigeben',{'node_id':n['id']})['status']=='knowledge_freigeben'
