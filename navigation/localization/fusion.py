"""Deterministic confidence-weighted combination of localization estimates.

Floor: the floor with the largest total confidence among the available estimates.
Position: confidence-weighted average of the estimates on that floor. A freshly
scanned QR code (confidence 1.0) therefore dominates, a close Wi-Fi fingerprint
match gets more say than a poor one, and IMU trust decays with steps walked.
Plain arithmetic - not a machine-learning model.
"""


def fuse(estimates):
    ests = [e for e in estimates if e is not None and e.get("confidence", 0) > 0]
    if not ests:
        return None
    by_floor = {}
    for e in ests:
        by_floor[e["floor"]] = by_floor.get(e["floor"], 0.0) + e["confidence"]
    floor = max(by_floor, key=by_floor.get)
    same = [e for e in ests if e["floor"] == floor]
    w = sum(e["confidence"] for e in same)
    return {
        "source": "fused",
        "x": sum(e["x"] * e["confidence"] for e in same) / w,
        "y": sum(e["y"] * e["confidence"] for e in same) / w,
        "floor": floor,
        "confidence": round(min(1.0, w / len(same)), 3),
        "weights": {e["source"]: round(e["confidence"] / w, 3) for e in same},
        "sources_used": [e["source"] for e in same],
    }
