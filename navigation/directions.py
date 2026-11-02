"""User-facing turn-by-turn directions, derived from a computed route.

This does not change routing. It takes the node path returned by Module 4 and
describes it the way a navigation app would ("Walk 6 m along the corridor",
"Turn left and walk 5 m to Classroom C101", "Take the lift to Floor 2"),
so the interface never has to show graph node IDs to the user.

Geometry: headings come from node coordinates (and an edge's optional
`draw_path` waypoints). Each edge's drawn length is scaled to the edge's stored
distance, so the step distances always add up to the route distance.
"""
import math

TRANSITION_TYPES = {"lift", "stairs"}
STRAIGHT_TOLERANCE_DEG = 20      # heading changes smaller than this count as "straight on"
U_TURN_DEG = 150


def _edge_polyline(g, u, v):
    """Planar points from u to v, including any drawing waypoints, in travel order."""
    d = g.edges[u, v]
    a = (g.nodes[u]["x"], g.nodes[u]["y"])
    b = (g.nodes[v]["x"], g.nodes[v]["y"])
    waypoints = [tuple(p) for p in (d.get("draw_path") or [])]
    # draw_path is stored in data order (from -> to); reverse it when walking the other way
    if waypoints and d.get("draw_from") == v:
        waypoints.reverse()
    return [a, *waypoints, b]


def _segments(g, u, v):
    """(length_m, heading_rad, start_pt, end_pt) pieces of an edge, scaled to its real distance."""
    pts = _edge_polyline(g, u, v)
    raw = [(p, q, math.hypot(q[0] - p[0], q[1] - p[1])) for p, q in zip(pts, pts[1:])]
    total = sum(r[2] for r in raw)
    dist = g.edges[u, v]["distance"]
    if total == 0:
        return []
    scale = dist / total
    return [(length * scale, math.atan2(q[1] - p[1], q[0] - p[0]), p, q) for p, q, length in raw if length > 0]


def _turn(prev_heading, heading):
    diff = math.degrees(heading - prev_heading)
    diff = (diff + 180) % 360 - 180          # normalise to [-180, 180)
    if abs(diff) < STRAIGHT_TOLERANCE_DEG:
        return None
    if abs(diff) >= U_TURN_DEG:
        return "around"
    return "left" if diff > 0 else "right"   # y axis points "up" on the plan


def _landmark(g, node, destination):
    d = g.nodes[node]
    if node == destination:
        return d["name"]
    if d["kind"] == "lift":
        return "the lift"
    if d["kind"] == "stairs":
        return "the stairs"
    if d["kind"] == "entrance":
        return "the entrance"
    return None


def build_directions(g, path):
    """Return a list of step dicts: {kind, text, floor, distance_m?, points}."""
    if not path:
        return []
    source, destination = path[0], path[-1]
    steps = [{"kind": "start", "text": f"Start at {g.nodes[source]['name']}",
              "floor": g.nodes[source]["floor"], "points": []}]
    if len(path) == 1:
        steps.append({"kind": "arrive", "text": f"You are at {g.nodes[destination]['name']}",
                      "floor": g.nodes[destination]["floor"], "points": []})
        return steps

    i = 0
    first_leg = True
    arrived_by = None
    while i < len(path) - 1:
        u, v = path[i], path[i + 1]
        etype = g.edges[u, v]["type"]

        if etype in TRANSITION_TYPES:
            # merge consecutive lift/stairs edges of the same kind (multi-floor jumps)
            j = i
            while j < len(path) - 1 and g.edges[path[j], path[j + 1]]["type"] == etype:
                j += 1
            from_floor, to_floor = g.nodes[u]["floor"], g.nodes[path[j]]["floor"]
            direction = "up" if to_floor > from_floor else "down"
            if etype == "lift":
                text = f"Take the lift to Floor {to_floor}"
            else:
                text = f"Take the stairs {direction} to Floor {to_floor}"
            steps.append({"kind": etype, "text": text, "floor": from_floor, "to_floor": to_floor,
                          "points": [], "node_floor_change": [from_floor, to_floor]})
            arrived_by = etype
            i = j
            continue

        # walking leg: consecutive same-floor edges until a transition or the end
        j = i
        segs = []
        while j < len(path) - 1 and g.edges[path[j], path[j + 1]]["type"] not in TRANSITION_TYPES:
            segs += _segments(g, path[j], path[j + 1])
            j += 1
        floor = g.nodes[u]["floor"]
        leg_end = path[j]

        # merge straight pieces into runs separated by turns
        runs = []   # [turn, length, points]
        for length, heading, p, q in segs:
            if runs and _turn(runs[-1][3], heading) is None:
                runs[-1][1] += length
                runs[-1][2].append(q)
                runs[-1][3] = heading
            else:
                turn = _turn(runs[-1][3], heading) if runs else None
                runs.append([turn, length, [p, q], heading])

        target = _landmark(g, leg_end, destination)
        for k, (turn, length, pts, _) in enumerate(runs):
            metres = max(1, round(length))
            last = k == len(runs) - 1
            suffix = f" to {target}" if last and target else ""
            if turn is None:
                if k == 0 and first_leg:
                    text = f"Walk {metres} m along the corridor{suffix}"
                elif k == 0 and arrived_by:
                    exit_word = "lift" if arrived_by == "lift" else "stairs"
                    text = f"Leave the {exit_word} and walk {metres} m{suffix}"
                else:
                    text = f"Continue {metres} m{suffix}"
                kind = "straight"
            elif turn == "around":
                text, kind = f"Turn around and walk {metres} m{suffix}", "around"
            else:
                text, kind = f"Turn {turn} and walk {metres} m{suffix}", f"turn-{turn}"
            steps.append({"kind": kind, "text": text, "floor": floor, "distance_m": metres,
                          "points": [list(p) for p in pts]})
        first_leg = False
        arrived_by = None
        i = j

    steps.append({"kind": "arrive", "text": f"Arrive at {g.nodes[destination]['name']}",
                  "floor": g.nodes[destination]["floor"], "points": []})
    return steps
