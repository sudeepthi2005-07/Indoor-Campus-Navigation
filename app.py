"""Module 6 - Navigation Interface (Flask backend + browser dashboard).

Run:  python app.py      then open http://127.0.0.1:5000
"""
import os

from flask import Flask, jsonify, request, send_from_directory

from navigation.campus_data import DEFAULT_DATA_FILE, destinations, load_campus
from navigation.graph_builder import build_graph, graph_to_json
from navigation.localization import scenarios
from navigation.routing import ALGORITHMS, MODES, Navigator

app = Flask(__name__, static_folder="static")

# Which building to serve is data, not code: point UINS_CAMPUS_DATA at any
# schema-conformant campus JSON (e.g. data/vit_sjt_building.json) to switch
# buildings with no code changes. Unset, it falls back to the Review-2
# sample building so the existing test suite and demo script are unaffected.
CAMPUS = load_campus(os.environ.get("UINS_CAMPUS_DATA", os.path.join(os.path.dirname(__file__), "data", "vit_seven_floor_building.json")))
NAV = Navigator(build_graph(CAMPUS))
CAMPUS_ID = CAMPUS["campus"]["id"]


def bad_request(msg):
    return jsonify({"error": msg}), 400


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/campus")
def campus_info():
    starts = [{"id": n, "name": d["name"], "floor": d["floor"]}
              for n, d in NAV.g.nodes(data=True) if d["kind"] != "room"]
    return jsonify({
        "campus": CAMPUS["campus"],
        "building": CAMPUS["buildings"][0]["name"],
        "destinations": destinations(CAMPUS),
        "start_points": sorted(starts, key=lambda s: (s["floor"], s["id"] != "ENTRANCE", s["id"])),
        "modes": [[k, v] for k, v in MODES.items()],          # list keeps display order
        "algorithms": list(ALGORITHMS),
        "scenarios": [[k, v["label"]] for k, v in scenarios.SCENARIOS.items()],
    })


@app.get("/api/facilities/nearest")
def nearest_facility():
    source = request.args.get("source", "ENTRANCE")
    category = request.args.get("category", "Washroom").lower()
    mode = request.args.get("mode", "general")
    if source not in NAV.g or mode not in MODES:
        return bad_request("Unknown source or mode")
    matches = []
    for d in destinations(CAMPUS):
        if category in d["category"].lower():
            r = NAV.route(source, d["id"], mode)
            if r["route_found"]: matches.append((r["distance_m"], d, r))
    if not matches: return jsonify({"route_found": False, "message": "No reachable matching facility"})
    _, dest, route = min(matches, key=lambda x: x[0])
    return jsonify({"destination": dest, "route": route, "route_found": True})

@app.get("/api/graph")
def graph():
    return jsonify(graph_to_json(NAV.g))


@app.post("/api/route")
def route():
    body = request.get_json(force=True, silent=True) or {}
    try:
        return jsonify(NAV.route(body.get("source", "ENTRANCE"), body["destination"],
                                 body.get("mode", "general"), body.get("algorithm", "astar")))
    except (KeyError, ValueError) as exc:
        return bad_request(str(exc))


@app.post("/api/block")
def block():
    body = request.get_json(force=True, silent=True) or {}
    try:
        NAV.block_edge(body["u"], body["v"])
    except KeyError as exc:
        return bad_request(str(exc))
    return jsonify({"blocked_edges": [f"{u}--{v}" for u, v in NAV.blocked_edges()]})


@app.post("/api/clear")
def clear():
    NAV.clear_blocks()
    return jsonify({"blocked_edges": []})


@app.get("/api/localize/<scenario_id>")
def localize(scenario_id):
    if scenario_id not in scenarios.SCENARIOS:
        return bad_request(f"unknown scenario '{scenario_id}'")
    # Legacy localization scenarios were surveyed for the original sample graph.
    # Keep them available as explicitly simulated demonstrations, not live fixes.
    from navigation.routing import Navigator as SampleNavigator
    sample = SampleNavigator(build_graph(load_campus(DEFAULT_DATA_FILE)))
    result = scenarios.run(scenario_id, sample, CAMPUS_ID)
    result["simulated"] = True
    result["message"] = "Legacy sample-building simulation; not a live position in the seven-floor map."
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=False, port=5000)
