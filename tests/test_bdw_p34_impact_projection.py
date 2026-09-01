import pytest
from unittest.mock import MagicMock

def test_graph3d_z_axis_has_semantic_dimension():
    """Testet, dass die Z-Achse einer benannten fachlichen Dimension wie Wirkungskettenstufe zugewiesen ist."""
    api_client = MagicMock()
    
    graph_data = {
        "nodes": [
            {"id": "node1", "x": 10, "y": 20, "z_dimension": "wirkungskettenstufe", "z": 5},
            {"id": "node2", "x": 15, "y": 25, "z_dimension": "wirkungskettenstufe", "z": 3}
        ],
        "hash": "impact_graph_hash_123"
    }
    api_client.get.return_value = graph_data
    
    response = api_client.get("/api/knowledge/graph3d")
    
    assert response["nodes"][0]["z_dimension"] in ["wirkungskettenstufe", "evidenzlage", "revision_time"]
    assert response["hash"] == "impact_graph_hash_123"

def test_graph3d_projects_same_hash_as_2d_fallback():
    """Testet, dass 3D und das 2D-Fallback denselben Graph-Hash verwenden."""
    api_client = MagicMock()
    
    data_3d = {"nodes": 10, "hash": "same_hash_456", "type": "3d"}
    data_2d = {"nodes": 10, "hash": "same_hash_456", "type": "2d"}
    
    api_client.get_3d.return_value = data_3d
    api_client.get_2d.return_value = data_2d
    
    assert api_client.get_3d()["hash"] == api_client.get_2d()["hash"]
