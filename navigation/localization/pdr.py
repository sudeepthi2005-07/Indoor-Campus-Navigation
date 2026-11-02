"""IMU pedestrian dead reckoning (simulated sensor stream).

Steps are detected as peaks in the accelerometer magnitude (scipy.signal.find_peaks);
heading is tracked by integrating the gyroscope yaw rate. Each step advances the
position by a fixed step length along the current heading. Heading convention:
0 deg = +x (east), 90 deg = +y (north).
"""
import math

import numpy as np
from scipy.integrate import cumulative_trapezoid
from scipy.signal import find_peaks

G = 9.81
SAMPLE_RATE_HZ = 50
STEP_FREQ_HZ = 1.8
STEP_LENGTH_M = 0.7


def simulate_walk(segments, fs=SAMPLE_RATE_HZ, rng=None, turn_duration_s=1.0):
    """Simulate a phone carried while walking.

    segments: list of (turn_before_deg, n_steps). A turn is performed in place over
    `turn_duration_s`, then n_steps are walked in the new direction.
    Returns dict(acc_norm, gyro_z_dps, fs, true_steps).
    """
    rng = rng or np.random.default_rng(1)
    acc, gyro = [], []
    true_steps = 0
    for turn_deg, n_steps in segments:
        if turn_deg:
            n = int(turn_duration_s * fs)
            acc += list(G + rng.normal(0, 0.15, n))
            gyro += list(np.full(n, turn_deg / turn_duration_s) + rng.normal(0, 1.0, n))
        n = int(n_steps / STEP_FREQ_HZ * fs)
        t = np.arange(n) / fs
        bounce = 2.5 * np.maximum(0, np.sin(2 * np.pi * STEP_FREQ_HZ * t)) ** 2
        acc += list(G + bounce + rng.normal(0, 0.15, n))
        gyro += list(rng.normal(0, 1.0, n))
        true_steps += n_steps
    return {"acc_norm": np.array(acc), "gyro_z_dps": np.array(gyro), "fs": fs, "true_steps": true_steps}


def detect_steps(acc_norm, fs=SAMPLE_RATE_HZ, min_height=G + 1.0, min_gap_s=0.3):
    peaks, _ = find_peaks(acc_norm, height=min_height, distance=int(min_gap_s * fs))
    return peaks


def integrate_heading(gyro_z_dps, fs=SAMPLE_RATE_HZ, initial_deg=0.0):
    return initial_deg + cumulative_trapezoid(gyro_z_dps, dx=1.0 / fs, initial=0.0)


def track(start_x, start_y, floor, sensors, initial_heading_deg=0.0, step_length=STEP_LENGTH_M):
    """Dead-reckon from a known start. Returns final estimate + per-step trajectory."""
    fs = sensors["fs"]
    steps = detect_steps(sensors["acc_norm"], fs)
    heading = integrate_heading(sensors["gyro_z_dps"], fs, initial_heading_deg)
    x, y = float(start_x), float(start_y)
    traj = [(x, y)]
    for idx in steps:
        h = math.radians(heading[idx])
        x += step_length * math.cos(h)
        y += step_length * math.sin(h)
        traj.append((x, y))
    # drift grows with distance walked since the last absolute fix
    confidence = max(0.2, 1.0 - 0.02 * len(steps))
    return {"source": "imu", "x": x, "y": y, "floor": floor, "confidence": round(confidence, 3),
            "steps_detected": int(len(steps)), "heading_deg": float(heading[-1]) if len(heading) else initial_heading_deg,
            "trajectory": traj}
