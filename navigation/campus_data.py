"""Module 1 - Campus and Building Data Management.

Campus information is kept as *data*, not code, so the same engine can be pointed
at another building or another college by supplying a new JSON file that follows
this generic schema:

    campus      : {id, name, note?}
    buildings[] : {id, name, floors[], connections[]}
    floors[]    : {level, name, locations[]}
    locations[] : {id, kind, name, x, y, category?}
                  kind in {entrance, junction, lift, stairs, ramp, room}
                  category is required for kind == "room"
                  (e.g. Classroom, Laboratory, Auditorium, Seminar Hall, Office, Shop / Facility)
    connections[]: {from, to, type, distance_m, turns, note?, draw_path?}
                  type in {corridor, door, lift, stairs, ramp}
                  draw_path: optional [[x, y], ...] waypoints (from -> to) used only to
                  draw a corridor that is not a straight line; routing ignores it.

Coordinates are metres in a per-building floor-plan frame. Only one sample
VIT-style building has been entered so far (prototype data).
"""
import json
from pathlib import Path

LOCATION_KINDS = {"entrance", "junction", "lift", "stairs", "ramp", "room"}
CONNECTION_TYPES = {"corridor", "door", "lift", "stairs", "ramp"}

DEFAULT_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "vit_sample_building.json"


class CampusDataError(ValueError):
    """Raised when a campus data file does not follow the schema."""


def load_campus(path=DEFAULT_DATA_FILE):
    """Read a campus data file and validate it. Returns the parsed dict."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    validate_campus(data)
    return data


def validate_campus(data):
    """Check the structure and cross-references of a campus data dict."""
    if "campus" not in data or "buildings" not in data:
        raise CampusDataError("campus data needs 'campus' and 'buildings' keys")
    seen = {}
    for b in data["buildings"]:
        for f in b["floors"]:
            for loc in f["locations"]:
                for key in ("id", "kind", "name", "x", "y"):
                    if key not in loc:
                        raise CampusDataError(f"location {loc} is missing '{key}'")
                if loc["kind"] not in LOCATION_KINDS:
                    raise CampusDataError(f"{loc['id']}: unknown kind '{loc['kind']}'")
                if loc["kind"] == "room" and "category" not in loc:
                    raise CampusDataError(f"room {loc['id']} needs a 'category'")
                if loc["id"] in seen:
                    raise CampusDataError(f"duplicate location id '{loc['id']}'")
                seen[loc["id"]] = f["level"]
        for c in b["connections"]:
            for end in ("from", "to"):
                if c[end] not in seen:
                    raise CampusDataError(f"connection refers to unknown location '{c[end]}'")
            if c["type"] not in CONNECTION_TYPES:
                raise CampusDataError(f"unknown connection type '{c['type']}'")
            wp = c.get("draw_path")
            if wp is not None and not (isinstance(wp, list) and all(
                    isinstance(pt, list) and len(pt) == 2 for pt in wp)):
                raise CampusDataError(f"draw_path on {c['from']}-{c['to']} must be [[x, y], ...]")
            if c["distance_m"] <= 0 or c["turns"] < 0:
                raise CampusDataError(f"bad distance/turns on {c['from']}-{c['to']}")
            same_floor = seen[c["from"]] == seen[c["to"]]
            if c["type"] in ("lift", "stairs") and same_floor:
                raise CampusDataError(f"{c['type']} edge {c['from']}-{c['to']} must change floor")
            if c["type"] not in ("lift", "stairs") and not same_floor:
                raise CampusDataError(f"{c['type']} edge {c['from']}-{c['to']} cannot change floor")
    return True


def destinations(data):
    """All selectable destinations (rooms), grouped for the interface."""
    out = []
    for b in data["buildings"]:
        for f in b["floors"]:
            for loc in f["locations"]:
                if loc["kind"] == "room":
                    out.append({"id": loc["id"], "name": loc["name"], "category": loc["category"],
                                "floor": f["level"], "building": b["id"]})
    return sorted(out, key=lambda d: (d["floor"], d["id"]))
