"""Modules 1-2: campus data schema and indoor graph."""
import copy
import math

import pytest

from navigation.campus_data import CampusDataError, destinations, validate_campus


def test_sample_building_size(nav):
    assert nav.g.number_of_nodes() == 19
    assert nav.g.number_of_edges() == 21
    assert sorted({d["floor"] for _, d in nav.g.nodes(data=True)}) == [1, 2]


def test_eight_categorised_destinations(campus):
    dests = destinations(campus)
    assert len(dests) == 8
    assert {d["category"] for d in dests} >= {"Classroom", "Laboratory", "Auditorium",
                                              "Seminar Hall", "Office", "Shop / Facility"}


def test_stairs_are_not_accessible(nav):
    for _, _, d in nav.g.edges(data=True):
        assert d["accessible"] == (d["type"] != "stairs")


def test_edge_lengths_support_admissible_astar(nav):
    for u, v, d in nav.g.edges(data=True):
        a, b = nav.g.nodes[u], nav.g.nodes[v]
        assert d["distance"] >= math.hypot(a["x"] - b["x"], a["y"] - b["y"]) - 1e-9


def test_schema_rejects_bad_reference(campus):
    bad = copy.deepcopy(campus)
    bad["buildings"][0]["connections"].append(
        {"from": "R101", "to": "NOWHERE", "type": "corridor", "distance_m": 3, "turns": 0})
    with pytest.raises(CampusDataError):
        validate_campus(bad)


def test_schema_rejects_same_floor_lift(campus):
    bad = copy.deepcopy(campus)
    bad["buildings"][0]["connections"].append(
        {"from": "J1_LOBBY", "to": "J1_MID", "type": "lift", "distance_m": 3, "turns": 0})
    with pytest.raises(CampusDataError):
        validate_campus(bad)


def test_schema_rejects_malformed_draw_path(campus):
    bad = copy.deepcopy(campus)
    bad["buildings"][0]["connections"][0]["draw_path"] = [[1, 2, 3]]
    with pytest.raises(CampusDataError):
        validate_campus(bad)


def test_draw_path_does_not_change_distances(nav):
    assert nav.g.edges["J1_LOBBY", "J1_END"]["distance"] == 24
    assert nav.g.edges["J1_LOBBY", "J1_END"]["draw_path"] == [[6, -12], [31, -12], [31, 0]]
