"""Review-2 demo: runs every scenario reported in the Review-2 report and prints the results.

Usage:  python scripts/demo_scenarios.py
"""
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from navigation.campus_data import DEFAULT_DATA_FILE, destinations, load_campus  # noqa: E402
from navigation.graph_builder import build_graph                      # noqa: E402
from navigation.localization import pdr, qr_landmarks, scenarios, wifi  # noqa: E402
from navigation.routing import Navigator                              # noqa: E402


def show(title, r):
    print(f"\n--- {title}")
    if r["route_found"]:
        print(f"    path      : {' -> '.join(r['path'])}")
        print(f"    distance  : {r['distance_m']} m   turns: {r['turns']}   "
              f"stairs: {r['uses_stairs']}   lift: {r['uses_lift']}   ({r['algorithm']}, {r['computation_time_ms']} ms)")
    else:
        print(f"    NO ROUTE  : {r['message']}")


def main():
    campus = load_campus(os.environ.get("UINS_CAMPUS_DATA", DEFAULT_DATA_FILE))
    nav = Navigator(build_graph(campus))
    cid = campus["campus"]["id"]

    print("=" * 72)
    print("MODULES 1-2  Campus data + indoor graph")
    print(f"    {nav.g.number_of_nodes()} nodes, {nav.g.number_of_edges()} edges, floors "
          f"{sorted({d['floor'] for _, d in nav.g.nodes(data=True)})}")
    print("    destinations:", ", ".join(d["name"] for d in destinations(campus)))

    print("=" * 72)
    print("MODULES 4-5  Route computation, accessibility, dynamic re-routing")
    show("Entrance -> Classroom C101 (general)", nav.route("ENTRANCE", "R101"))
    show("Entrance -> Shop/Facility F204 (general, lift available)", nav.route("ENTRANCE", "R204"))
    nav.block_edge("LIFT_1", "LIFT_2")
    show("Lift out of service -> F204 (general mode)", nav.route("ENTRANCE", "R204", "general"))
    show("Lift out of service -> F204 (wheelchair mode)", nav.route("ENTRANCE", "R204", "accessibility"))
    nav.clear_blocks()
    show("Entrance -> Laboratory L102 (wheelchair, all open)", nav.route("ENTRANCE", "R102", "accessibility"))
    nav.block_edge("J1_LOBBY", "J1_MID")
    show("Corridor J1_LOBBY--J1_MID closed -> L102 (wheelchair, detour)",
         nav.route("ENTRANCE", "R102", "accessibility"))
    nav.clear_blocks()
    d = nav.route("ENTRANCE", "R204", "general", "dijkstra")
    a = nav.route("ENTRANCE", "R204", "general", "astar")
    print(f"\n    Dijkstra vs A* to F204 -> same route: {d['path'] == a['path']}")

    print("=" * 72)
    print("MODULE 3  Indoor localization (simulated Wi-Fi/IMU, rendered QR images)")
    out = ROOT / "qr_codes"
    files = qr_landmarks.generate_codes(nav.g, cid, out)
    ok = sum(qr_landmarks.locate_from_image(p, nav.g, cid) is not None for p in files.values())
    print(f"    QR landmarks decoded: {ok} of {len(files)}  (PNGs saved in {out.name}/)")

    db = wifi.FingerprintDatabase.survey_grid()
    rng = np.random.default_rng(42)
    errs, floors = [], 0
    for _ in range(100):
        x, y, f = rng.uniform(0, 26), rng.uniform(-5, 5), int(rng.integers(1, 3))
        e = db.locate(wifi.simulate_rssi(x, y, f, rng))
        errs.append(np.hypot(e["x"] - x, e["y"] - y)); floors += e["floor"] == f
    print(f"    Wi-Fi fingerprinting (100 simulated scans): mean error {np.mean(errs):.2f} m, "
          f"floor correct {floors}%")

    s = pdr.simulate_walk([(0, 20), (90, 10)])
    t = pdr.track(0, 0, 1, s)
    print(f"    IMU/PDR: {t['steps_detected']} steps detected of {s['true_steps']}; "
          f"end position ({t['x']:.1f}, {t['y']:.1f}) vs true (14.0, 7.0)")

    for sid in scenarios.SCENARIOS:
        r = scenarios.run(sid, nav, cid)
        print(f"    [{sid}] fused ({r['fused']['x']:.1f}, {r['fused']['y']:.1f}, F{r['fused']['floor']}) "
              f"error {r['error_m']} m -> start node {r['snapped_node']}  weights {r['fused']['weights']}")
    print("=" * 72)


if __name__ == "__main__":
    main()
