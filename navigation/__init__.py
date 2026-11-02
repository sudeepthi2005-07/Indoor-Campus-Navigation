"""Universal Indoor Navigation System (UINS) - Review-2 prototype.

Modules (numbering follows the Review-2 report):
    1  campus_data      - configurable campus/building data (generic schema)
    2  graph_builder    - converts campus data into a weighted NetworkX graph
    3  localization     - Wi-Fi RSSI, QR landmarks, IMU/PDR, confidence-weighted fusion
    4  routing          - Dijkstra / A* minimum-cost feasible route
    5  routing          - accessibility mode + blocked edges + re-routing (inside Module 4)
    6  ../app.py        - Flask API + browser navigation interface
"""
