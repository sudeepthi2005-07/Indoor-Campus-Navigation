"""Wi-Fi RSSI fingerprinting (simulated signals).

Signals are simulated with the standard log-distance path-loss model:
    RSSI(d) = P0 - 10 * n * log10(d / d0) - floor_attenuation * |floor difference| + noise
A reference fingerprint table is built over a grid of surveyed points, and a live
scan is located by nearest-neighbour matching in signal space (k nearest points,
averaged). This is a conventional matching rule, not a learned model.
"""
import math

import numpy as np

P0_DBM = -40.0            # RSSI at d0 = 1 m
PATH_LOSS_EXPONENT = 3.0  # typical indoor value
FLOOR_ATTENUATION_DB = 15.0
MIN_RSSI = -100.0

# Simulated access points for the sample building: (id, x, y, floor)
ACCESS_POINTS = [
    ("AP1", 2, 3, 1), ("AP2", 20, -3, 1), ("AP3", 26, 4, 1),
    ("AP4", 8, -3, 2), ("AP5", 22, 3, 2),
]


def simulate_rssi(x, y, floor, rng=None, noise_std=2.0):
    """One simulated Wi-Fi scan at (x, y, floor): {ap_id: rssi_dBm}."""
    rng = rng or np.random.default_rng()
    scan = {}
    for ap, ax, ay, af in ACCESS_POINTS:
        d = max(math.hypot(x - ax, y - ay), 1.0)
        rssi = P0_DBM - 10 * PATH_LOSS_EXPONENT * math.log10(d) - FLOOR_ATTENUATION_DB * abs(floor - af)
        rssi += rng.normal(0, noise_std)
        scan[ap] = max(rssi, MIN_RSSI)
    return scan


def _vector(scan):
    return np.array([scan.get(ap, MIN_RSSI) for ap, *_ in ACCESS_POINTS])


class FingerprintDatabase:
    """Reference table of surveyed points -> mean RSSI vector."""

    def __init__(self, points, samples_per_point=10, rng=None):
        rng = rng or np.random.default_rng(0)
        self.points = list(points)  # [(x, y, floor)]
        self.table = np.array([
            np.mean([_vector(simulate_rssi(x, y, f, rng)) for _ in range(samples_per_point)], axis=0)
            for x, y, f in self.points
        ])

    @classmethod
    def survey_grid(cls, floors=(1, 2), x_range=(0, 26), y_range=(-5, 5), step=2.0, **kw):
        xs = np.arange(x_range[0], x_range[1] + 1e-9, step)
        ys = np.arange(y_range[0], y_range[1] + 1e-9, step)
        return cls([(float(x), float(y), f) for f in floors for x in xs for y in ys], **kw)

    def locate(self, scan, k=3):
        """Nearest-neighbour match. Returns an estimate dict with a confidence in [0, 1]."""
        dists = np.linalg.norm(self.table - _vector(scan), axis=1)
        order = np.argsort(dists)[:k]
        floors = [self.points[i][2] for i in order]
        floor = max(set(floors), key=floors.count)
        same = [i for i in order if self.points[i][2] == floor]
        x = float(np.mean([self.points[i][0] for i in same]))
        y = float(np.mean([self.points[i][1] for i in same]))
        best = float(dists[order[0]])
        confidence = 1.0 / (1.0 + best / 5.0)   # closer fingerprint match -> more trust
        return {"source": "wifi", "x": x, "y": y, "floor": floor,
                "confidence": round(confidence, 3), "match_distance_db": round(best, 2)}
