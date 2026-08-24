from pathlib import Path

import knowledge_mcp_server as server


def test_governance_lifecycle_uses_current_api(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "DB_PATH", Path(tmp_path) / "store.sqlite")
    node = server.knowledge_add(
        "/", "Synthetic", "Synthetic test node", source="tests/synthetic.md",
        neuer_ast=True, norm_entscheidung="keine_norm",
        norm_entschieden_grund="Synthetic test fixture",
    )
    assert server.freigabe_setzen(node["id"], "gesperrt")["status"] == "gesetzt"
    assert server.knowledge_zurueckziehen(node["id"], "Synthetic reason")["status"] == "zurueckgezogen"
    assert server.knowledge_freigeben(node["id"])["status"] == "freigegeben"
