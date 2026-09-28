"""Unit tests for Layer 4: Interactive Visual Interface & REST API."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from graphite.api.app import create_app


@pytest.fixture(scope="module")
def api_client():
    app = create_app()
    return TestClient(app)


def test_health_endpoint(api_client):
    response = api_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["total_nodes"] > 0
    assert data["total_edges"] > 0
    assert data["total_subsystems"] > 0


def test_blueprint_topology_endpoint(api_client):
    response = api_client.get("/api/blueprint")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert "subsystems" in data
    assert len(data["nodes"]) > 0

    sample_node = data["nodes"][0]
    assert "id" in sample_node
    assert "label" in sample_node
    assert "cx" in sample_node
    assert "cy" in sample_node


def test_node_details_endpoint(api_client):
    response = api_client.get("/api/node/general13")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "general13"
    assert "downstream" in data
    assert "upstream" in data
    assert "isolation_valves" in data
    assert "specs" in data


def test_query_endpoint(api_client):
    payload = {
        "query": "What is downstream from pump P-101 (general13)?",
        "mode": "auto",
        "k_hop": 2,
    }
    response = api_client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["retrieval_mode"] == "local"
    assert "general13" in data["grounded_answer"]
    assert len(data["visual_citations"]) > 0
    assert len(data["highlighted_node_ids"]) > 0


def test_multi_turn_chat_dialogue(api_client):
    session_id = "test_turn_session_42"

    # Turn 1
    req1 = {"message": "How to isolate valve99?", "session_id": session_id}
    res1 = api_client.post("/api/chat", json=req1)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["session_id"] == session_id
    assert len(data1["history"]) == 2  # 1 user + 1 assistant
    assert "highlighted_edge_ids" in data1
    assert "highlighted_node_ids" in data1

    # Turn 2
    req2 = {"message": "Give me an overview of plant subsystems", "session_id": session_id}
    res2 = api_client.post("/api/chat", json=req2)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["session_id"] == session_id
    assert len(data2["history"]) == 4  # 2 user + 2 assistant
    assert data2["retrieval_mode"] == "global"


def test_plant_hierarchy_and_compliance(api_client):
    res_sub = api_client.get("/api/subsystems")
    assert res_sub.status_code == 200
    data_sub = res_sub.json()
    assert "domains" in data_sub

    res_comp = api_client.get("/api/compliance")
    assert res_comp.status_code == 200
    data_comp = res_comp.json()
    assert "anomalies" in data_comp
    assert "total_components_checked" in data_comp


def test_valve_simulation_endpoint(api_client):
    payload = {
        "closed_valve_ids": ["valve99"],
        "origin_node": "general13",
    }
    res = api_client.post("/api/simulate/valve", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["origin_node"] == "general13"
    assert "valve99" in data["closed_valves"]
    assert "reachable_nodes" in data
    assert "isolated_nodes" in data
    assert "traversed_edges" in data


def test_blueprint_image_endpoint(api_client):
    res = api_client.get("/api/blueprint/image")
    assert res.status_code == 200
    assert res.headers["content-type"] in ["image/png", "image/jpeg"]


def test_viewer_html_endpoint(api_client):
    response = api_client.get("/")
    assert response.status_code == 200
    assert "GRAPHITE" in response.text
    assert "overlay-svg" in response.text
    assert "chat-panel" in response.text
    assert "label-group" in response.text
    assert "node-label" in response.text
    assert "toggle-labels" in response.text
