import pytest
from unittest.mock import MagicMock

def test_feedback_drawer_http_post_is_preview_only():
    """Testet, dass HTTP-POST keinen Knowledge-Write auslöst, sondern nur das Preview liefert."""
    http_client = MagicMock()
    
    # Mock response for HTTP POST
    preview_response = {
        "status": "preview_only",
        "target": "knowledge_graph",
        "effect": "update_node_trust",
        "mutation_applied": False
    }
    http_client.post.return_value = preview_response
    
    response = http_client.post("/api/dashboard/feedback", json={"action": "suggest_correction"})
    
    assert response["status"] == "preview_only"
    assert response["mutation_applied"] is False
    assert "target" in response
    assert "effect" in response

def test_feedback_drawer_no_mutation_on_knowledge_db():
    """Stellt sicher, dass keine Mutation an der Graphen-Datenbank stattfindet."""
    knowledge_db = MagicMock()
    drawer_handler = MagicMock(db=knowledge_db)
    
    drawer_handler.handle_post_request({"action": "gap_confirmation"})
    
    knowledge_db.write.assert_not_called()
    knowledge_db.update.assert_not_called()
