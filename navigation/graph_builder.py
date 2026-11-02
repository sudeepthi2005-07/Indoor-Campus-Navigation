"""Module 2 - Indoor Map and Graph.

Every location becomes a node (floor + coordinates); every walkable connection
becomes an undirected edge carrying:
    distance  - metres
    turns     - turn cost of traversing the edge (e.g. 1 for turning into a door,
                2 for a switchback stair flight)
    type      - corridor / door / lift / stairs / ramp
    accessible- False for stairs (wheelchair users cannot use them)
    blocked   - live availability flag, toggled at run time (Module 5)
    draw_path - optional drawing waypoints for non-straight corridors (display only)
"""
import networkx as nx

NOT_WHEELCHAIR_ACCESSIBLE = {"stairs"}


def build_graph(campus):
    g = nx.Graph()
    for b in campus["buildings"]:
        for f in b["floors"]:
            for loc in f["locations"]:
                g.add_node(loc["id"], floor=f["level"], x=loc["x"], y=loc["y"],
                           kind=loc["kind"], name=loc["name"],
                           category=loc.get("category"), building=b["id"])
        for c in b["connections"]:
            g.add_edge(c["from"], c["to"], distance=float(c["distance_m"]), turns=int(c["turns"]),
                       type=c["type"], accessible=c["type"] not in NOT_WHEELCHAIR_ACCESSIBLE,
                       blocked=False, draw_path=c.get("draw_path"), draw_from=c["from"])
    return g


def graph_to_json(g):
    """JSON form served to the navigation interface for drawing the map."""
    return {
        "nodes": [{"id": n, **d} for n, d in g.nodes(data=True)],
        "edges": [{"u": u, "v": v, **d} for u, v, d in g.edges(data=True)],
        "floors": sorted({d["floor"] for _, d in g.nodes(data=True)}),
        "stats": {"nodes": g.number_of_nodes(), "edges": g.number_of_edges()},
    }
