"""Simulated localization scenarios used by the dashboard and the demo script.

Each scenario places a (simulated) user at a known true position, runs the three
localization sources on simulated/rendered input, fuses them, and snaps the result
to the nearest graph node so Module 4 can route from it.
"""
import math
import tempfile

import numpy as np

from . import pdr, qr_landmarks, wifi
from .fusion import fuse

SCENARIOS = {
    "walk_entrance_to_mid": {
        "label": "Walked 26 steps east from the entrance (Wi-Fi + IMU)",
        "true": (18.2, 0.0, 1), "pdr_from": ("ENTRANCE", 0.0, [(0, 26)]), "qr": None,
    },
    "scan_qr_at_lift": {
        "label": "Scanned the QR code at the floor-1 lift lobby (QR + Wi-Fi)",
        "true": (22.0, 0.0, 1), "pdr_from": None, "qr": "LIFT_1",
    },
    "standing_floor2_lobby": {
        "label": "Standing in the floor-2 lobby (Wi-Fi only)",
        "true": (6.0, 0.0, 2), "pdr_from": None, "qr": None,
    },
}

_DB = None


def _db():
    global _DB
    if _DB is None:
        _DB = wifi.FingerprintDatabase.survey_grid()
    return _DB


def run(scenario_id, navigator, campus_id, seed=7):
    sc = SCENARIOS[scenario_id]
    rng = np.random.default_rng(seed)
    tx, ty, tf = sc["true"]
    estimates = [_db().locate(wifi.simulate_rssi(tx, ty, tf, rng))]

    if sc["pdr_from"]:
        start, heading, segments = sc["pdr_from"]
        s = navigator.g.nodes[start]
        est = pdr.track(s["x"], s["y"], s["floor"], pdr.simulate_walk(segments, rng=rng), heading)
        est.pop("trajectory")
        estimates.append(est)

    if sc["qr"]:
        with tempfile.TemporaryDirectory() as tmp:
            files = qr_landmarks.generate_codes(navigator.g, campus_id, tmp, [sc["qr"]])
            estimates.append(qr_landmarks.locate_from_image(files[sc["qr"]], navigator.g, campus_id))

    fused = fuse(estimates)
    node = navigator.snap_to_node(fused["x"], fused["y"], fused["floor"])
    return {
        "scenario": scenario_id, "label": sc["label"],
        "true_position": {"x": tx, "y": ty, "floor": tf},
        "estimates": estimates, "fused": fused,
        "error_m": round(math.hypot(fused["x"] - tx, fused["y"] - ty), 2),
        "floor_correct": fused["floor"] == tf,
        "snapped_node": node, "snapped_node_name": navigator.g.nodes[node]["name"],
        "note": "Wi-Fi and IMU inputs are simulated; QR is decoded from a rendered image.",
    }
