"""QR-code landmarks at surveyed positions.

Each landmark QR encodes "UINS|<campus_id>|<node_id>". When the camera decodes one,
its known surveyed position is looked up, giving an exact fix (confidence 1.0).
Generation uses the `qrcode` library; decoding uses OpenCV's QRCodeDetector.
"""
from pathlib import Path

import cv2
import numpy as np
import qrcode

PREFIX = "UINS"

# Landmark node ids that carry a printed QR code in the sample building
DEFAULT_LANDMARKS = ["ENTRANCE", "J1_MID", "LIFT_1", "J2_LOBBY", "STAIRS_2"]


def payload_for(campus_id, node_id):
    return f"{PREFIX}|{campus_id}|{node_id}"


def generate_codes(graph, campus_id, out_dir, landmarks=DEFAULT_LANDMARKS):
    """Render one PNG per landmark. Returns {node_id: file_path}."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    for node in landmarks:
        if node not in graph:
            raise KeyError(f"landmark '{node}' is not in the graph")
        img = qrcode.make(payload_for(campus_id, node), box_size=8, border=4)
        path = out / f"qr_{node}.png"
        img.save(path)
        files[node] = str(path)
    return files


def decode_image(image):
    """Decode a QR landmark from a file path or BGR/grey numpy image. Returns payload or None."""
    if isinstance(image, (str, Path)):
        image = cv2.imread(str(image))
    if image is None:
        return None
    text, _, _ = cv2.QRCodeDetector().detectAndDecode(image)
    return text or None


def fix_from_payload(payload, graph, campus_id):
    """Turn a decoded payload into an exact position estimate, or None if not ours."""
    if not payload:
        return None
    parts = payload.split("|")
    if len(parts) != 3 or parts[0] != PREFIX or parts[1] != campus_id or parts[2] not in graph:
        return None
    d = graph.nodes[parts[2]]
    return {"source": "qr", "node": parts[2], "x": float(d["x"]), "y": float(d["y"]),
            "floor": d["floor"], "confidence": 1.0}


def locate_from_image(image, graph, campus_id):
    return fix_from_payload(decode_image(image), graph, campus_id)


def degrade(image_path, rng=None):
    """Light blur + noise, used only to sanity-check decoding robustness in tests."""
    rng = rng or np.random.default_rng(0)
    img = cv2.imread(str(image_path))
    img = cv2.GaussianBlur(img, (3, 3), 0)
    noise = rng.normal(0, 8, img.shape)
    return np.clip(img.astype(float) + noise, 0, 255).astype(np.uint8)
