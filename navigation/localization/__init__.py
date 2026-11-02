"""Module 3 - Indoor Localization.

Three smartphone-style sources, combined by a deterministic confidence-weighted rule:
    wifi.py          Wi-Fi RSSI fingerprinting (nearest-neighbour matching)
    qr_landmarks.py  QR-code landmarks at surveyed positions (exact fix when scanned)
    pdr.py           IMU pedestrian dead reckoning (step detection + gyro heading)
    fusion.py        confidence-weighted combination -> single (x, y, floor) estimate

In this prototype Wi-Fi and IMU run on SIMULATED data (no live VIT Wi-Fi survey or
phone sensor feed yet). QR generation/decoding runs end to end on rendered images.
None of this is machine learning; it is conventional matching and arithmetic.
"""
