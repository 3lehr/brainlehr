import tempfile
from knowledge_mcp_server import add_node, call, open_db

def test_relation_lifecycle_and_assumption_decision():
    with tempfile.NamedTemporaryFile(suffix=".sqlite") as f:
        db=open_db(f.name); a=add_node(db,"One","Synthetic"); b=add_node(db,"Two","Synthetic")
        relation=call(db,"knowledge_relation_add",{"source_id":a["id"],"target_id":b["id"],"relation_type":"supports"})
        assert call(db,"knowledge_relation_update",{"relation_id":relation["id"],"relation_type":"references"})["status"]=="updated"
        assert call(db,"knowledge_relation_remove",{"relation_id":relation["id"]})["status"]=="removed"
        assumption=call(db,"annahme_erfassen",{"annahme":"Synthetic assumption","kosten_wenn_falsch":"Synthetic cost"})
        call(db,"annahme_entscheiden",{"annahme_id":assumption["id"],"status":"accepted","beleg":"Synthetic evidence"})
        assert call(db,"annahme_liste",{"status":"accepted"})[0]["id"]==assumption["id"]
