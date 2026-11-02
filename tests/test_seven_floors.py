from pathlib import Path
import networkx as nx
import pytest
from navigation.campus_data import load_campus, destinations
from navigation.graph_builder import build_graph
from navigation.routing import Navigator

@pytest.fixture
def seven():
    return load_campus(Path(__file__).resolve().parents[1] / 'data/vit_seven_floor_building.json')

@pytest.fixture
def seven_nav(seven):
    return Navigator(build_graph(seven))

def test_integrity(seven,seven_nav):
    assert len(seven['buildings'][0]['floors']) == 7
    ds=destinations(seven)
    assert len(ds)==224
    assert len({d['id'] for d in ds})==224
    assert nx.is_connected(seven_nav.g)

def test_all_rooms_accessible(seven_nav,seven):
    for d in destinations(seven):
        r=seven_nav.route('ENTRANCE',d['id'],'accessibility')
        assert r['route_found'] and not r['uses_stairs']

def test_seventh_floor(seven_nav):
    r=seven_nav.route('ENTRANCE','F6_N01')
    assert r['route_found'] and r['uses_lift'] and r['floors'][-1]==6
    assert seven_nav.route('F1_N02','F4_N01')['route_found']

def test_lift_outage(seven_nav):
    for u,v,d in seven_nav.g.edges(data=True):
        if d['type']=='lift':seven_nav.block_edge(u,v)
    assert not seven_nav.route('ENTRANCE','F6_N01','accessibility')['route_found']
    assert seven_nav.route('ENTRANCE','F6_N01')['uses_stairs']

def test_closed_corridor(seven_nav):
    seven_nav.block_edge('F0_C00','F0_C01')
    assert seven_nav.route('ENTRANCE','F0_N16')['route_found']
    seven_nav.clear_blocks()
    assert seven_nav.route('ENTRANCE','F0_N16')['route_found']

def test_dijkstra_astar_agree(seven_nav):
    a=seven_nav.route('F0_S01','F6_N16',algorithm='astar')
    b=seven_nav.route('F0_S01','F6_N16',algorithm='dijkstra')
    assert a['cost']==b['cost']
