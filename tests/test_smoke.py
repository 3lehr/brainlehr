import tempfile

from knowledge_mcp_server import add_node, call, open_db


def test_add_and_search():
    with tempfile.NamedTemporaryFile(suffix=".sqlite") as file:
        db = open_db(file.name)
        node = add_node(db, "Alpha", "Synthetischer Testeintrag")
        assert call(db, "knowledge_search", {"query": "Alpha"})[0]["title"] == "Alpha"
        lesson = call(db, "lesson_record", {"description": "Allgemeine Testlehre"})
        call(db, "knowledge_relation_add", {"source_id": node["id"], "target_id": node["id"], "relation_type": "supports"})
        assert lesson["status"] == "recorded" and call(db, "knowledge_stats", {})["relations"] == 1
