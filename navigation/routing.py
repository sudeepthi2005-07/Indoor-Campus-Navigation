"""Module 4 - Route Computation, with Module 5 - Accessibility and Dynamic Routing.

Edge cost used by the search:

    cost(edge) = DISTANCE_WEIGHT * distance + TURN_WEIGHT * turns

Accessibility and blockages are enforced by *removing* edges from the search
rather than adding a soft penalty, which is a stronger guarantee:
  * accessibility mode  -> stairs edges are excluded, so a wheelchair route can
                           never cross a staircase;
  * blocked edges       -> excluded in every mode.
Re-routing after a blockage is simply the same search run again on the updated
graph with the same source, destination and mode. If nothing feasible remains,
an explicit "no route" result is returned instead of an unsuitable route.
"""
import math
import time

import networkx as nx

from .directions import build_directions

DISTANCE_WEIGHT = 1.0
TURN_WEIGHT = 2.0   # one turn "costs" as much as 2 m of extra walking

MODES = {
    "general": "General (shortest path)",
    "accessibility": "Wheelchair (avoid stairs)",
}
ALGORITHMS = ("dijkstra", "astar")


def edge_cost(d):
    return DISTANCE_WEIGHT * d["distance"] + TURN_WEIGHT * d["turns"]


class Navigator:
    """Holds the indoor graph plus its live blocked-edge state."""

    def __init__(self, graph):
        self.g = graph

    # ---- Module 5: live availability -------------------------------------
    def block_edge(self, u, v):
        if not self.g.has_edge(u, v):
            raise KeyError(f"no edge {u}-{v}")
        self.g.edges[u, v]["blocked"] = True

    def unblock_edge(self, u, v):
        self.g.edges[u, v]["blocked"] = False

    def clear_blocks(self):
        for _, _, d in self.g.edges(data=True):
            d["blocked"] = False

    def blocked_edges(self):
        return [(u, v) for u, v, d in self.g.edges(data=True) if d["blocked"]]

    def searchable_graph(self, mode):
        """Sub-graph the search is allowed to use under the given mode."""
        if mode not in MODES:
            raise ValueError(f"unknown mode '{mode}'")

        def allowed(u, v):
            d = self.g.edges[u, v]
            if d["blocked"]:
                return False
            if mode == "accessibility" and not d["accessible"]:
                return False
            return True

        return nx.subgraph_view(self.g, filter_edge=allowed)

    # ---- Module 4: route computation -------------------------------------
    def _heuristic(self, target):
        tx, ty = self.g.nodes[target]["x"], self.g.nodes[target]["y"]

        def h(n, _t=None):
            x, y = self.g.nodes[n]["x"], self.g.nodes[n]["y"]
            return 0.0  # guaranteed admissible across floors and lift shortcuts
        return h

    def route(self, source, destination, mode="general", algorithm="astar"):
        for n in (source, destination):
            if n not in self.g:
                raise KeyError(f"unknown location '{n}'")
        if algorithm not in ALGORITHMS:
            raise ValueError(f"unknown algorithm '{algorithm}'")

        view = self.searchable_graph(mode)
        weight = lambda u, v, d: edge_cost(d)
        t0 = time.perf_counter()
        try:
            if algorithm == "dijkstra":
                path = nx.dijkstra_path(view, source, destination, weight=weight)
            else:
                path = nx.astar_path(view, source, destination,
                                     heuristic=self._heuristic(destination), weight=weight)
        except nx.NetworkXNoPath:
            path = None
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        result = {
            "source": source, "destination": destination,
            "destination_name": self.g.nodes[destination]["name"],
            "mode": mode, "algorithm": algorithm,
            "computation_time_ms": round(elapsed_ms, 4),
            "blocked_edges": [f"{u}--{v}" for u, v in self.blocked_edges()],
        }
        if path is None:
            result.update(route_found=False, path=None, distance_m=None, turns=None, directions=[],
                          cost=None, uses_stairs=None, uses_lift=None,
                          message=self._no_route_message(mode))
        else:
            edges = [self.g.edges[a, b] for a, b in zip(path, path[1:])]
            result.update(
                route_found=True, path=path,
                path_names=[self.g.nodes[n]["name"] for n in path],
                distance_m=sum(e["distance"] for e in edges),
                turns=sum(e["turns"] for e in edges),
                cost=round(sum(edge_cost(e) for e in edges), 2),
                uses_stairs=any(e["type"] == "stairs" for e in edges),
                uses_lift=any(e["type"] == "lift" for e in edges),
                floors=[self.g.nodes[n]["floor"] for n in path],
                directions=build_directions(self.g, path),
                message=None,
            )
        if mode == "accessibility":
            result["accessible_route_found"] = result["route_found"]
        return result

    @staticmethod
    def _no_route_message(mode):
        if mode == "accessibility":
            return ("No accessible route is available to this destination under the "
                    "current mode/graph state.")
        return "No route is available to this destination while the blocked edges remain closed."

    # ---- helper for Module 3 -> Module 4 hand-off ------------------------
    def snap_to_node(self, x, y, floor):
        """Nearest graph node on the same floor to a continuous (x, y, floor) estimate."""
        candidates = [(n, d) for n, d in self.g.nodes(data=True) if d["floor"] == floor]
        if not candidates:
            raise ValueError(f"no nodes on floor {floor}")
        n, _ = min(candidates, key=lambda nd: math.hypot(nd[1]["x"] - x, nd[1]["y"] - y))
        return n
