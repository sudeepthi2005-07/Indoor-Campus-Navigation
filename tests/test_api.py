"""Module 6: Flask API end to end."""
import importlib

import pytest


@pytest.fixture
def client():
    app_module = importlib.import_module("app")
    from navigation.campus_data import load_campus
    from navigation.graph_builder import build_graph
    from navigation.routing import Navigator
    from pathlib import Path
    app_module.CAMPUS = load_campus(Path(__file__).resolve().parents[1] / "data/vit_sample_building.json")
    app_module.NAV = Navigator(build_graph(app_module.CAMPUS))
    app_module.CAMPUS_ID = app_module.CAMPUS["campus"]["id"]
    app_module.NAV.clear_blocks()
    return app_module.app.test_client()


def test_campus_and_graph(client):
    c = client.get("/api/campus").get_json()
    assert len(c["destinations"]) == 8
    g = client.get("/api/graph").get_json()
    assert g["stats"] == {"nodes": 19, "edges": 21}


def test_route_block_reroute_clear(client):
    r = client.post("/api/route", json={"source": "ENTRANCE", "destination": "R204", "mode": "accessibility"}).get_json()
    assert r["route_found"] and r["uses_lift"]
    client.post("/api/block", json={"u": "LIFT_1", "v": "LIFT_2"})
    r = client.post("/api/route", json={"source": "ENTRANCE", "destination": "R204", "mode": "accessibility"}).get_json()
    assert r["accessible_route_found"] is False
    client.post("/api/clear")
    r = client.post("/api/route", json={"source": "ENTRANCE", "destination": "R204", "mode": "accessibility"}).get_json()
    assert r["route_found"]


def test_bad_input_returns_400(client):
    assert client.post("/api/route", json={"destination": "NOPE"}).status_code == 400
    assert client.post("/api/block", json={"u": "R101", "v": "R204"}).status_code == 400
    assert client.get("/api/localize/unknown").status_code == 400


def test_localize_endpoint(client):
    r = client.get("/api/localize/scan_qr_at_lift").get_json()
    assert r["snapped_node"] == "LIFT_1"


def test_index_has_user_and_demo_views(client):
    html = client.get("/").get_data(as_text=True)
    assert "User view" in html and "Demo / Technical view" in html
    assert "Developer / Demo controls" in html


def test_route_response_includes_directions(client):
    r = client.post("/api/route", json={"source": "ENTRANCE", "destination": "R204"}).get_json()
    assert r["directions"][0]["kind"] == "start" and r["directions"][-1]["kind"] == "arrive"
    assert any(s["kind"] == "lift" for s in r["directions"])
