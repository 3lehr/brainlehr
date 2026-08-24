from pathlib import Path

import knowledge_mcp_server as server


def _node(title):
    return server.knowledge_add(
        "/", title, "Synthetic test node", source="tests/synthetic.md",
        neuer_ast=True, norm_entscheidung="keine_norm",
        norm_entschieden_grund="Synthetic test fixture",
    )


def test_relation_lifecycle_and_assumption_decision(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "DB_PATH", Path(tmp_path) / "store.sqlite")
    first, second = _node("One"), _node("Two")
    relation = server.knowledge_relation_add(first["id"], second["id"], "supports")
    assert server.knowledge_relation_update(relation["id"], relation_type="references")["status"] == "updated"
    assert server.knowledge_relation_remove(relation["id"])["status"] == "removed"
    assumption = server.annahme_erfassen("Synthetic assumption", "Synthetic cost")
    decision = server.annahme_entscheiden(assumption["id"], "bestaetigt", "Synthetic evidence", "test")
    assert decision["status"] == "bestaetigt"
    assert server.annahme_liste("bestaetigt")["results"][0]["id"] == assumption["id"]
