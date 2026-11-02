"""Modules 4-5: route computation, accessibility mode, dynamic re-routing.
Expected values are the ones reported in the Review-2 report."""
import pytest


@pytest.mark.parametrize("algo", ["dijkstra", "astar"])
def test_entrance_to_c101(nav, algo):
    r = nav.route("ENTRANCE", "R101", "general", algo)
    assert r["path"] == ["ENTRANCE", "J1_LOBBY", "R101"]
    assert r["distance_m"] == 11 and r["turns"] == 1
    assert r["uses_stairs"] is False and r["uses_lift"] is False


def test_dijkstra_and_astar_agree_everywhere(nav):
    nodes = list(nav.g.nodes)
    for mode in ("general", "accessibility"):
        for s in nodes:
            for t in nodes:
                a = nav.route(s, t, mode, "dijkstra")
                b = nav.route(s, t, mode, "astar")
                assert a["cost"] == b["cost"]


def test_general_mode_uses_lift_when_available(nav):
    r = nav.route("ENTRANCE", "R204", "general")
    assert r["uses_lift"] and not r["uses_stairs"]


def test_lift_out_general_mode_takes_stairs(nav):
    nav.block_edge("LIFT_1", "LIFT_2")
    r = nav.route("ENTRANCE", "R204", "general")
    assert r["route_found"] and r["uses_stairs"] and not r["uses_lift"]
    assert r["distance_m"] == 47.0 and r["turns"] == 5


def test_lift_out_accessibility_mode_reports_no_route(nav):
    nav.block_edge("LIFT_1", "LIFT_2")
    r = nav.route("ENTRANCE", "R204", "accessibility")
    assert r["route_found"] is False and r["accessible_route_found"] is False
    assert r["path"] is None and "No accessible route" in r["message"]


def test_accessibility_route_never_uses_stairs(nav):
    for t in nav.g.nodes:
        r = nav.route("ENTRANCE", t, "accessibility")
        assert r["route_found"] and not r["uses_stairs"]


def test_blocked_corridor_recoverable_detour(nav):
    before = nav.route("ENTRANCE", "R102", "accessibility")
    nav.block_edge("J1_LOBBY", "J1_MID")
    after = nav.route("ENTRANCE", "R102", "accessibility")
    assert after["route_found"]
    assert ("J1_LOBBY", "J1_MID") not in list(zip(after["path"], after["path"][1:]))
    assert after["distance_m"] > before["distance_m"]


def test_clear_blocks_restores_route(nav):
    nav.block_edge("LIFT_1", "LIFT_2")
    nav.clear_blocks()
    assert nav.route("ENTRANCE", "R204", "accessibility")["route_found"]


def test_snap_to_node(nav):
    assert nav.snap_to_node(17.4, 0.6, 1) == "J1_MID"
    assert nav.snap_to_node(6.3, 0.2, 2) == "J2_LOBBY"
