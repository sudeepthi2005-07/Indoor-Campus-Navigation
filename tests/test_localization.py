"""Module 3: Wi-Fi fingerprinting, QR landmarks, IMU/PDR and fusion."""
import numpy as np

from navigation.localization import pdr, qr_landmarks, scenarios, wifi
from navigation.localization.fusion import fuse


def test_qr_generate_and_decode_all_five(nav, campus, tmp_path):
    files = qr_landmarks.generate_codes(nav.g, campus["campus"]["id"], tmp_path)
    assert len(files) == 5
    decoded = [qr_landmarks.locate_from_image(p, nav.g, campus["campus"]["id"]) for p in files.values()]
    assert all(d is not None for d in decoded)
    for node, fix in zip(files, decoded):
        assert fix["node"] == node and fix["confidence"] == 1.0


def test_qr_rejects_foreign_payload(nav):
    assert qr_landmarks.fix_from_payload("SOMEONE|ELSE|X", nav.g, "VIT_VELLORE") is None


def test_wifi_fingerprint_accuracy_on_simulated_data():
    db = wifi.FingerprintDatabase.survey_grid()
    rng = np.random.default_rng(42)
    errors, floor_ok = [], 0
    for _ in range(100):
        x, y, f = rng.uniform(0, 26), rng.uniform(-5, 5), int(rng.integers(1, 3))
        est = db.locate(wifi.simulate_rssi(x, y, f, rng))
        errors.append(np.hypot(est["x"] - x, est["y"] - y))
        floor_ok += est["floor"] == f
    assert floor_ok >= 95          # floor identified in >= 95 % of scans
    assert np.mean(errors) < 3.0   # mean horizontal error under 3 m (simulated)


def test_pdr_counts_steps_and_turns():
    sensors = pdr.simulate_walk([(0, 20), (90, 10)])
    est = pdr.track(0, 0, 1, sensors)
    assert abs(est["steps_detected"] - sensors["true_steps"]) <= 1
    # 20 steps east then 10 north with 0.7 m steps -> about (14, 7)
    assert abs(est["x"] - 14) < 1.5 and abs(est["y"] - 7) < 1.5


def test_fusion_prefers_confident_source():
    f = fuse([{"source": "wifi", "x": 10, "y": 0, "floor": 1, "confidence": 0.5},
              {"source": "qr", "x": 12, "y": 0, "floor": 1, "confidence": 1.0}])
    assert 11 < f["x"] < 12 and f["floor"] == 1


def test_fusion_floor_vote():
    f = fuse([{"source": "wifi", "x": 5, "y": 0, "floor": 2, "confidence": 0.3},
              {"source": "qr", "x": 6, "y": 0, "floor": 1, "confidence": 1.0}])
    assert f["floor"] == 1 and f["sources_used"] == ["qr"]


def test_all_scenarios_snap_to_expected_node(nav, campus):
    expected = {"walk_entrance_to_mid": "J1_MID", "scan_qr_at_lift": "LIFT_1",
                "standing_floor2_lobby": "J2_LOBBY"}
    for sid, node in expected.items():
        r = scenarios.run(sid, nav, campus["campus"]["id"])
        assert r["floor_correct"] and r["snapped_node"] == node
