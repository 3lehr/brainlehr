import tempfile

from knowledge_mcp_server import add_node, open_db, search


def test_add_and_search():
    with tempfile.NamedTemporaryFile(suffix=".sqlite") as file:
        db = open_db(file.name)
        add_node(db, "Alpha", "Synthetischer Testeintrag")
        assert search(db, "Alpha")[0]["title"] == "Alpha"
