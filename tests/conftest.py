import pytest
from navigation.campus_data import load_campus
from navigation.graph_builder import build_graph
from navigation.routing import Navigator
from pathlib import Path

@pytest.fixture
def campus():
    return load_campus(Path(__file__).resolve().parents[1] / 'data/vit_sample_building.json')

@pytest.fixture
def nav(campus):
    return Navigator(build_graph(campus))
